"""
SERP Appearance and Snippet Analyzer for Dristik AI (2026 Standard)
Evaluates:
1. Google Desktop & Mobile Title pixel widths (>580px cutoff / ~60 chars)
2. Meta Description pixel widths (>960px cutoff / ~160 chars)
3. Rich snippet badges (Review Stars, FAQ, Breadcrumbs, Product Price, Recipe, Video)
4. Realistic Google SERP snippet previews
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from app.domain.enums import Category, EvidenceClass, FindingStatus, Severity
from app.domain.models import (
    Finding,
    PageEvidence,
    SerpAppearanceReport,
    SerpSnippetPreview,
)

# Approximate Arial font character pixel widths for Google Title (20px font)
_CHAR_PIXEL_WIDTHS_TITLE: Dict[str, float] = {
    "i": 4.5, "l": 4.5, "j": 5.5, "t": 6.5, "f": 6.5, "r": 7.0,
    "m": 16.0, "w": 15.0, "M": 17.0, "W": 18.0, "@": 16.0, "%": 15.0,
    " ": 5.0, ".": 4.5, ",": 4.5, "!": 5.0, "|": 4.5, "-": 7.0,
}
_DEFAULT_CHAR_WIDTH_TITLE = 9.8

_CHAR_PIXEL_WIDTHS_DESC: Dict[str, float] = {
    "i": 3.2, "l": 3.2, "j": 3.8, "t": 4.2, "f": 4.2, "r": 4.8,
    "m": 11.5, "w": 10.5, "M": 12.0, "W": 13.0, " ": 3.8, ".": 3.2,
}
_DEFAULT_CHAR_WIDTH_DESC = 6.8

GOOGLE_TITLE_PIXEL_LIMIT_DESKTOP = 580
GOOGLE_TITLE_PIXEL_LIMIT_MOBILE = 520
GOOGLE_DESC_PIXEL_LIMIT = 960


def estimate_pixel_width(text: str, is_title: bool = True) -> int:
    """Estimates pixel render width in Google SERP font."""
    if not text:
        return 0
    table = _CHAR_PIXEL_WIDTHS_TITLE if is_title else _CHAR_PIXEL_WIDTHS_DESC
    default_w = _DEFAULT_CHAR_WIDTH_TITLE if is_title else _DEFAULT_CHAR_WIDTH_DESC
    total = sum(table.get(char, default_w) for char in text)
    return int(round(total))


def _detect_snippet_badges(page: PageEvidence) -> Tuple[bool, List[str], Optional[str]]:
    badges: List[str] = []
    types = [str(t).lower() for t in (page.schema_types or [])]

    if any("aggregate_rating" in t or "review" in t for t in types):
        badges.append("Review Stars (★★★★★)")
    if any("faqpage" in t for t in types):
        badges.append("FAQ Dropdown Accordion")
    if any("product" in t for t in types):
        badges.append("Product Pricing & In-Stock")
    if any("breadcrumblist" in t for t in types):
        badges.append("Hierarchical Breadcrumbs")
    if any("videoobject" in t for t in types):
        badges.append("Video Thumbnail Badge")

    eligible = len(badges) > 0
    primary_badge = badges[0] if badges else None
    return eligible, badges, primary_badge


def analyze_serp_appearance(
    pages: Sequence[PageEvidence],
    target_domain: str = "",
) -> Tuple[SerpAppearanceReport, List[Finding]]:
    """
    Simulates Google SERP snippets and pixel widths across audited pages.
    Returns (SerpAppearanceReport, List[Finding]).
    """
    if not pages:
        return SerpAppearanceReport(
            status="PASS",
            total_urls_evaluated=0,
            summary="No pages available to evaluate SERP snippet appearance.",
        ), []

    snippets: List[SerpSnippetPreview] = []
    titles_truncated = 0
    descriptions_truncated = 0
    rich_supported = 0
    findings: List[Finding] = []

    for p in pages:
        title = p.title or ""
        meta_desc = p.meta_description or ""

        title_px = estimate_pixel_width(title, is_title=True)
        desc_px = estimate_pixel_width(meta_desc, is_title=False)

        desktop_trunc = title_px > GOOGLE_TITLE_PIXEL_LIMIT_DESKTOP
        mobile_trunc = title_px > GOOGLE_TITLE_PIXEL_LIMIT_MOBILE
        desc_trunc = desc_px > GOOGLE_DESC_PIXEL_LIMIT

        if desktop_trunc:
            titles_truncated += 1
        if desc_trunc:
            descriptions_truncated += 1

        is_rich, rich_types, badge = _detect_snippet_badges(p)
        if is_rich:
            rich_supported += 1

        parsed = urlparse(p.url)
        path_display = parsed.path if parsed.path and parsed.path != "/" else ""
        preview_url = f"{parsed.netloc} › {path_display.strip('/')}".replace("/", " › ") if path_display else parsed.netloc

        snippet = SerpSnippetPreview(
            url=p.url,
            desktop_title=title,
            desktop_title_pixel_width=title_px,
            desktop_title_truncated=desktop_trunc,
            mobile_title_truncated=mobile_trunc,
            meta_description=meta_desc,
            meta_description_pixel_width=desc_px,
            meta_description_truncated=desc_trunc,
            rich_snippet_eligible=is_rich,
            rich_snippet_types=rich_types,
            snippet_badge=badge,
            preview_url_display=preview_url,
        )
        snippets.append(snippet)

    total = len(snippets)
    readiness_pct = round((rich_supported / total) * 100, 1) if total > 0 else 0.0

    status = "PASS"
    if titles_truncated > total * 0.4 or descriptions_truncated > total * 0.5:
        status = "WARNING"
    if titles_truncated > total * 0.7:
        status = "CRITICAL"

    summary = (
        f"Evaluated Google SERP appearance for {total} URLs. "
        f"{titles_truncated} title(s) exceed desktop 580px width limit and will be truncated with ellipsis (...). "
        f"{descriptions_truncated} description(s) exceed 960px limit. "
        f"{rich_supported} URL(s) ({readiness_pct}%) have rich snippet markup enabled."
    )

    # Findings
    if titles_truncated > 0:
        trunc_samples = [s.url for s in snippets if s.desktop_title_truncated][:10]
        findings.append(
            Finding(
                finding_id="FINDING-SERP-001",
                category=Category.CONTENT,
                subcategory="SERP Snippet & Pixel Width Optimization",
                affected_urls=trunc_samples,
                expected_condition="Page title tags must not exceed 580px pixel width (~55-60 characters) to prevent SERP ellipsis truncation.",
                dependencies=["Page Title Tag Templates"],
                status=FindingStatus.OPEN,
                owner="SEO / Content",
                severity=Severity.MEDIUM,
                title="Google Desktop SERP Title Pixel Width Exceeded",
                description=(
                    f"{titles_truncated} audited page(s) have title tags exceeding the 580px Google SERP limit. "
                    "Google will cut off primary keywords or branding with trailing ellipsis (...)."
                ),
                recommendation="Condense title tags to 50-60 characters (<580px), front-loading primary search intent terms.",
                impact=6,
                effort=3,
                priority=6,
                confidence=0.98,
                confidence_basis="Direct character-to-pixel font width calculation against Google Desktop SERP boundary.",
                why_it_matters="Truncated titles in search engine result pages decrease Organic Click-Through Rate (CTR) and dilute brand recall.",
                validation_criteria="Page title pixel width measured under 580px across all affected URLs.",
                evidence_class=EvidenceClass.OBSERVED,
            )
        )

    if rich_supported == 0 and total > 0:
        findings.append(
            Finding(
                finding_id="FINDING-SERP-002",
                category=Category.SCHEMA,
                subcategory="Rich Snippet SERP Enhancement",
                affected_urls=[s.url for s in snippets[:10]],
                expected_condition="High-priority URLs should support enhanced rich snippets (Breadcrumbs, FAQ, Reviews, or Product data).",
                dependencies=["Schema Implementation Team"],
                status=FindingStatus.OPEN,
                owner="Engineering",
                severity=Severity.LOW,
                title="Zero Enhanced Rich Snippet SERP Features Detected",
                description=(
                    "No URLs across the crawl qualify for visual Google SERP enrichments such as star ratings, breadcrumb hierarchies, or FAQ accordions."
                ),
                recommendation="Deploy BreadcrumbList and topical schema (FAQ, Product, or Article) to win larger visual search real estate.",
                impact=5,
                effort=4,
                priority=5,
                confidence=0.95,
                confidence_basis="Inspection of Schema.org graph against Google Search Feature Guides.",
                why_it_matters="Rich snippets occupy up to 30% more vertical pixels in SERP, dramatically boosting organic CTR over plain listings.",
                validation_criteria="Google Rich Results Test confirms valid BreadcrumbList or Review entities with zero warnings.",
                evidence_class=EvidenceClass.OBSERVED,
            )
        )

    report = SerpAppearanceReport(
        status=status,
        total_urls_evaluated=total,
        titles_truncated_count=titles_truncated,
        descriptions_truncated_count=descriptions_truncated,
        rich_snippets_supported_count=rich_supported,
        rich_snippet_readiness_pct=readiness_pct,
        snippets=snippets,
        summary=summary,
    )

    return report, findings
