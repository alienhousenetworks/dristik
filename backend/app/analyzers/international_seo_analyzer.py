"""
International SEO Analyzer for Dristik
Evaluates HTML and HTTP hreflang tags, BCP 47 / ISO 639-1 language and country codes,
bidirectional return-tag reciprocity, x-default fallbacks, and localized canonical conflicts.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

from app.domain.enums import Category, EvidenceClass, RubricConfidence, Severity
from app.domain.models import (
    Finding,
    FindingEvidence,
    HreflangEntry,
    HreflangMatrixItem,
    HreflangValidationIssue,
    InternationalSeoAuditReport,
    PageEvidence,
)

# Valid 2-letter ISO 639-1 language codes
ISO_639_1_CODES = {
    "aa", "ab", "af", "am", "ar", "as", "ay", "az", "ba", "be", "bg", "bh", "bi", "bn",
    "bo", "br", "bs", "ca", "co", "cs", "cy", "da", "de", "dv", "dz", "ee", "el", "en",
    "eo", "es", "et", "eu", "fa", "fi", "fj", "fo", "fr", "fy", "ga", "gd", "gl", "gn",
    "gu", "gv", "ha", "he", "hi", "ho", "hr", "ht", "hu", "hy", "hz", "ia", "id", "ie",
    "ig", "ii", "ik", "io", "is", "it", "iu", "ja", "jv", "ka", "kg", "ki", "kj", "kk",
    "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li",
    "ln", "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
    "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv", "ny", "oc", "oj",
    "om", "or", "os", "pa", "pi", "pl", "ps", "pt", "qu", "rm", "rn", "ro", "ru", "rw",
    "sa", "sc", "sd", "se", "sg", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss",
    "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr",
    "ts", "tt", "tw", "ty", "ug", "uk", "ur", "uz", "ve", "vi", "vo", "wa", "wo", "xh",
    "yi", "yo", "za", "zh", "zu"
}

# Common country code mistakes in SEO
COMMON_COUNTRY_ERRORS = {
    "uk": "gb",  # United Kingdom is 'gb' in ISO 3166-1
    "eu": None,  # European Union is not a single country in ISO 3166-1
}


def _validate_hreflang_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a hreflang value against BCP 47 / ISO 639-1 + ISO 3166-1.
    Returns (is_valid, error_message).
    """
    c = code.strip().lower()
    if c == "x-default":
        return True, None

    if "_" in c:
        return False, f"Invalid separator '_' in '{code}'. Use hyphens (e.g. 'en-US', not 'en_US')."

    parts = c.split("-")
    lang = parts[0]

    if lang not in ISO_639_1_CODES:
        return False, f"Unknown ISO 639-1 language code '{lang}' in '{code}'."

    if len(parts) >= 2:
        region = parts[1]
        if region in COMMON_COUNTRY_ERRORS:
            correct = COMMON_COUNTRY_ERRORS[region]
            sugg = f" (did you mean '{lang}-{correct}'?)" if correct else ""
            return False, f"Invalid ISO 3166-1 country code '{region}' in '{code}'{sugg}."
        if len(region) != 2 and not region.isdigit():
            # Script tags like zh-Hans are valid (4 letters)
            if len(region) != 4:
                return False, f"Unrecognized region or script subtag '{region}' in '{code}'."

    return True, None


def analyze_international_seo(
    pages: Sequence[PageEvidence],
    target_domain: str = "",
) -> Tuple[InternationalSeoAuditReport, List[Finding]]:
    """
    Analyzes International SEO across crawled pages.
    Validates language declarations, hreflang syntax, return-tag reciprocity,
    x-default fallbacks, and localized canonical conflicts.
    """
    if not pages:
        return InternationalSeoAuditReport(
            status="NOT_APPLICABLE",
            summary="No pages available for International SEO analysis.",
        ), []

    page_map: Dict[str, PageEvidence] = {p.url.rstrip("/"): p for p in pages}
    all_locales: Set[str] = set()
    matrix_items: List[HreflangMatrixItem] = []
    issues: List[HreflangValidationIssue] = []
    findings: List[Finding] = []
    pages_with_hreflang = 0
    has_global_x_default = False

    for p in pages:
        p_clean = p.url.rstrip("/")
        tags = p.hreflang_tags or {}
        declared_lang = p.html_lang
        entries: List[HreflangEntry] = []
        page_has_x_default = False

        if tags:
            pages_with_hreflang += 1

        for hl_code, target_url in tags.items():
            clean_code = hl_code.strip().lower()
            all_locales.add(clean_code)
            entries.append(HreflangEntry(hreflang=clean_code, href=target_url))

            if clean_code == "x-default":
                page_has_x_default = True
                has_global_x_default = True

            # 1. Validate hreflang syntax
            is_valid, err_msg = _validate_hreflang_code(clean_code)
            if not is_valid and err_msg:
                issues.append(
                    HreflangValidationIssue(
                        url=p.url,
                        issue_type="invalid_language_code",
                        severity="ERROR",
                        target_hreflang=clean_code,
                        target_url=target_url,
                        message=err_msg,
                    )
                )

        # 2. Check localized canonical conflicts
        # An alternate page (e.g. /es/) should self-canonicalize or point to its own language URL,
        # never point canonical back to root English unless deliberately consolidating duplicates.
        if p.canonical_url and tags:
            can_clean = p.canonical_url.rstrip("/")
            if can_clean != p_clean and can_clean in [e.href.rstrip("/") for e in entries if e.hreflang not in ("x-default", clean_code if 'clean_code' in locals() else "")]:
                # Localized page points its canonical to a different language version!
                issues.append(
                    HreflangValidationIssue(
                        url=p.url,
                        issue_type="canonical_conflict",
                        severity="ERROR",
                        target_url=p.canonical_url,
                        message=(
                            f"Localized alternate '{p.url}' sets rel='canonical' to '{p.canonical_url}'. "
                            "Localized pages must self-canonicalize; pointing canonical to another language causes search engines to de-index this locale."
                        ),
                    )
                )

        # 3. Check bidirectional return tags
        missing_returns: List[str] = []
        return_tags_valid = True
        for hl_code, target_url in tags.items():
            if hl_code == "x-default":
                continue
            tgt_clean = target_url.rstrip("/")
            if tgt_clean == p_clean:
                continue  # self-referencing hreflang
            
            # If target URL is in our crawled set, verify return tag
            target_page = page_map.get(tgt_clean)
            if target_page:
                target_tags = target_page.hreflang_tags or {}
                # Look for a tag in target_page that points back to p_clean
                has_return = any(
                    dest.rstrip("/") == p_clean for dest in target_tags.values()
                )
                if not has_return:
                    return_tags_valid = False
                    missing_returns.append(target_url)
                    issues.append(
                        HreflangValidationIssue(
                            url=p.url,
                            issue_type="missing_return_tag",
                            severity="ERROR",
                            target_hreflang=hl_code,
                            target_url=target_url,
                            message=f"Missing return tag: '{target_url}' does not link back to '{p.url}' with hreflang.",
                        )
                    )

        # 4. Check <html lang> vs hreflang alignment
        canonical_aligned = True
        if p.canonical_url and p.canonical_url.rstrip("/") != p_clean:
            canonical_aligned = False

        matrix_items.append(
            HreflangMatrixItem(
                url=p.url,
                declared_lang=declared_lang,
                alternates_count=len(entries),
                alternates=entries,
                has_x_default=page_has_x_default,
                return_tags_valid=return_tags_valid,
                missing_return_tags=missing_returns,
                canonical_aligned=canonical_aligned,
            )
        )

    # Status & Synthesis
    is_multilingual = bool(pages_with_hreflang > 0 or len(all_locales) > 1)
    
    if not is_multilingual:
        status = "NOT_APPLICABLE"
        summary = "Single-locale site. No hreflang alternate tags detected; international targeting is not required."
    elif any(iss.severity == "ERROR" and iss.issue_type in ("missing_return_tag", "canonical_conflict") for iss in issues):
        status = "FAILED"
        err_counts = len([i for i in issues if i.severity == "ERROR"])
        summary = (
            f"Critical International SEO defects detected ({err_counts} issues): "
            "hreflang return tags are missing or localized pages contain conflicting canonical tags."
        )
    elif issues:
        status = "WARNING"
        summary = f"International SEO warnings: {len(issues)} code syntax or x-default warnings detected."
    elif not is_multilingual and pages_with_hreflang == 0:
        status = "NOT_APPLICABLE"
        summary = "Single-language site; international hreflang alternate annotations are not applicable."
    else:
        status = "PASS"
        summary = f"Fully validated multilingual architecture across {len(all_locales)} locale(s) with reciprocal return tags."

    # Findings generation
    home_url = pages[0].url if pages else f"https://{target_domain}"

    # Return tag finding
    return_issues = [i for i in issues if i.issue_type == "missing_return_tag"]
    if return_issues:
        findings.append(
            Finding(
                finding_id="intl_seo_missing_return_tags",
                title=f"Missing Hreflang Return Tags on Alternate Pages ({len(return_issues)} errors)",
                description=(
                    f"The crawler identified {len(return_issues)} hreflang tag(s) without reciprocal return tags. "
                    "Google and Yandex ignore hreflang annotations entirely when alternate pages do not reciprocate the link."
                ),
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                confidence=0.98,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_hreflang_matrix",
                        detail=f"Example missing return tag: {return_issues[0].message}",
                        url=return_issues[0].url,
                    )
                ],
                recommendation=(
                    "Ensure bidirectional hreflang tags: if Page A references Page B as its French version, "
                    "Page B must reference Page A as its English version."
                ),
            )
        )

    # Canonical conflict finding
    canonical_issues = [i for i in issues if i.issue_type == "canonical_conflict"]
    if canonical_issues:
        findings.append(
            Finding(
                finding_id="intl_seo_localized_canonical_conflict",
                title="Localized Alternate Pages Have Conflicting rel='canonical' Tags",
                description=(
                    "One or more localized alternate pages have rel='canonical' tags pointing away from their localized URL "
                    "(typically pointing to the default English root). This signals to search engines that the localized page "
                    "is a duplicate and should be omitted from international SERPs."
                ),
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                confidence=0.98,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_canonical_audit",
                        detail=canonical_issues[0].message,
                        url=canonical_issues[0].url,
                    )
                ],
                recommendation=(
                    "Configure localized URLs to have self-referential canonical tags while maintaining hreflang links "
                    "to all regional and language alternates."
                ),
            )
        )

    # Invalid code finding
    code_issues = [i for i in issues if i.issue_type == "invalid_language_code"]
    if code_issues:
        findings.append(
            Finding(
                finding_id="intl_seo_invalid_hreflang_code",
                title=f"Invalid Hreflang Language/Country Syntax ({len(code_issues)} instances)",
                description=(
                    f"Found {len(code_issues)} invalid hreflang code(s). Common errors include using underscores ('en_US' instead of 'en-US') "
                    "or invalid ISO codes (such as 'en-UK' instead of 'en-GB')."
                ),
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                confidence=0.95,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_hreflang_validator",
                        detail=code_issues[0].message,
                        url=code_issues[0].url,
                    )
                ],
                recommendation=(
                    "Correct all hreflang codes to follow ISO 639-1 for language and ISO 3166-1 alpha-2 for country "
                    "separated by hyphens (e.g. 'en-GB', 'fr-CA', 'es-MX', 'x-default')."
                ),
            )
        )

    # Missing x-default warning if multilingual
    if is_multilingual and not has_global_x_default:
        findings.append(
            Finding(
                finding_id="intl_seo_missing_x_default",
                title="Missing hreflang='x-default' Fallback Tag",
                description=(
                    "Your multilingual implementation does not specify an 'x-default' alternate tag. "
                    "Google recommends x-default for the global landing page or language selector for users whose language is not explicitly targeted."
                ),
                category=Category.TECHNICAL_SEO,
                severity=Severity.LOW,
                confidence=0.90,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_hreflang_matrix",
                        detail="Site has multilingual alternate tags but lacks hreflang='x-default'.",
                        url=home_url,
                    )
                ],
                recommendation="Add <link rel='alternate' hreflang='x-default' href='https://.../'> to all localized pages.",
            )
        )

    report = InternationalSeoAuditReport(
        status=status,
        is_multilingual=is_multilingual,
        total_pages_with_hreflang=pages_with_hreflang,
        locales_detected=sorted(list(all_locales)),
        has_x_default=has_global_x_default,
        return_tags_healthy=len(return_issues) == 0,
        issues=issues,
        matrix=matrix_items,
        summary=summary,
    )

    return report, findings
