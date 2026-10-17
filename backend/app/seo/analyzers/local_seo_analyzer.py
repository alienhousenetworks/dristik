"""
Local SEO Analyzer for Dristik
Evaluates Google Business Profile (GBP) presence, NAP consistency across crawled pages and schema,
local landing page completeness, LocalBusiness schema depth (address, geo, opening hours, reviews),
and local citation links.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from app.domain.enums import Category, EvidenceClass, RubricConfidence, Severity
from app.domain.models import (
    Finding,
    FindingEvidence,
    LocalLandingPageAudit,
    LocalSeoAuditReport,
    NapRecord,
    PageEvidence,
)

_LOCAL_URL_PATTERNS = [
    r"/locations?(/|$)",
    r"/areas?(/|$)",
    r"/service-areas?(/|$)",
    r"-in-[a-z-]+/?$",
    r"/[a-z-]+-office/?$",
    r"/branches?(/|$)",
]

_PHONE_NORM_RE = re.compile(r"[^\d+]")


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits only or +digits."""
    digits = _PHONE_NORM_RE.sub("", phone)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    return digits


def _normalize_address(addr: str) -> str:
    """Normalize address string by removing punctuation and standardizing whitespace."""
    if not addr:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", addr.lower())
    replacements = {
        r"\bstreet\b": "st",
        r"\bavenue\b": "ave",
        r"\bboulevard\b": "blvd",
        r"\broad\b": "rd",
        r"\bdrive\b": "dr",
        r"\blane\b": "ln",
    }
    for pat, rep in replacements.items():
        cleaned = re.sub(pat, rep, cleaned)
    return " ".join(cleaned.split())


def analyze_local_seo(
    pages: Sequence[PageEvidence],
    target_domain: str = "",
) -> Tuple[LocalSeoAuditReport, List[Finding]]:
    """
    Audits Local SEO signals across all crawled pages.
    Returns (LocalSeoAuditReport, List[Finding]).
    """
    if not pages:
        return LocalSeoAuditReport(
            status="NOT_APPLICABLE",
            summary="No pages available to audit Local SEO.",
        ), []

    nap_records: List[NapRecord] = []
    all_phones: Dict[str, List[str]] = {}  # norm_phone -> list of URLs
    all_addresses: Dict[str, List[str]] = {}  # clean_addr -> list of URLs
    gbp_urls: List[str] = []
    citation_links: List[str] = []
    has_map_embed = False
    local_landing_pages: List[LocalLandingPageAudit] = []
    findings: List[Finding] = []

    # 1. Inspect per-page nap_data
    for p in pages:
        nap = p.nap_data or {}
        p_phones = nap.get("phone_numbers") or []
        p_addrs = nap.get("addresses") or []
        p_map = bool(nap.get("has_map_embed"))
        p_map_urls = nap.get("map_embed_urls") or []
        p_gbp = nap.get("gbp_links") or []
        p_cits = nap.get("citation_links") or []

        if p_map:
            has_map_embed = True

        for g in p_gbp:
            if g not in gbp_urls:
                gbp_urls.append(g)

        for c in p_cits:
            if c not in citation_links:
                citation_links.append(c)

        for ph in p_phones:
            norm = _normalize_phone(ph)
            if len(norm) >= 7:
                all_phones.setdefault(norm, []).append(p.url)

        for addr in p_addrs:
            clean = _normalize_address(addr)
            if len(clean) >= 10:
                all_addresses.setdefault(clean, []).append(p.url)

        record = NapRecord(
            page_url=p.url,
            phone_numbers=p_phones,
            addresses=p_addrs,
            has_map_embed=p_map,
            map_embed_urls=p_map_urls,
            gbp_links=p_gbp,
            citation_links=p_cits,
        )
        nap_records.append(record)

        # Detect local landing pages
        is_local_page = any(re.search(pat, p.url, re.IGNORECASE) for pat in _LOCAL_URL_PATTERNS)
        if is_local_page:
            has_local_schema = any(
                "localbusiness" in str(st).lower() or "store" in str(st).lower()
                for st in (p.schema_types or [])
            )
            has_reviews = bool(
                "review" in (p.body_text or "").lower() or
                "testimonial" in (p.body_text or "").lower()
            )
            local_issues = []
            if not p_phones and not p_addrs:
                local_issues.append("Missing localized NAP (address and phone)")
            if not has_local_schema:
                local_issues.append("Missing LocalBusiness JSON-LD markup")
            if not p_map and not p_gbp:
                local_issues.append("Missing Google Maps embed or GBP direction link")

            page_status = "PASS" if not local_issues else ("CRITICAL" if len(local_issues) >= 2 else "INCOMPLETE")
            local_landing_pages.append(
                LocalLandingPageAudit(
                    url=p.url,
                    target_location=p.url.rstrip("/").split("/")[-1].replace("-", " ").title(),
                    has_unique_nap=bool(p_phones or p_addrs),
                    has_local_schema=has_local_schema,
                    has_map=p_map or bool(p_gbp),
                    has_local_reviews=has_reviews,
                    status=page_status,
                    issues=local_issues,
                )
            )

    # 2. Inspect Schema for LocalBusiness data
    local_schema_found = False
    schema_missing_fields: List[str] = []
    schema_phones: List[str] = []
    schema_addresses: List[str] = []

    for p in pages:
        for entity in (p.raw_schema or []):
            if not isinstance(entity, dict):
                continue
            st = str(entity.get("@type") or "").lower()
            if "localbusiness" in st or any(t in st for t in ["store", "restaurant", "medicalbusiness"]):
                local_schema_found = True
                if entity.get("telephone"):
                    schema_phones.append(str(entity["telephone"]))
                addr = entity.get("address")
                if isinstance(addr, dict):
                    parts = [
                        str(addr.get("streetAddress", "")),
                        str(addr.get("addressLocality", "")),
                        str(addr.get("addressRegion", "")),
                        str(addr.get("postalCode", "")),
                    ]
                    addr_str = " ".join(pt for pt in parts if pt).strip()
                    if addr_str:
                        schema_addresses.append(addr_str)
                elif isinstance(addr, str):
                    schema_addresses.append(addr)

                # Check required/recommended local fields
                if not entity.get("address"):
                    schema_missing_fields.append("address")
                if not entity.get("geo"):
                    schema_missing_fields.append("geo (coordinates)")
                if not (entity.get("openingHours") or entity.get("openingHoursSpecification")):
                    schema_missing_fields.append("openingHours")
                if not entity.get("telephone"):
                    schema_missing_fields.append("telephone")

    # Cross-reference schema phone/address with DOM
    for sp in schema_phones:
        norm = _normalize_phone(sp)
        if len(norm) >= 7:
            all_phones.setdefault(norm, []).append("schema:LocalBusiness")

    for sa in schema_addresses:
        clean = _normalize_address(sa)
        if len(clean) >= 10:
            all_addresses.setdefault(clean, []).append("schema:LocalBusiness")

    # 3. Detect Conflicts
    phone_conflicts: List[Dict[str, Any]] = []
    if len(all_phones) > 1:
        # Multiple differing phone numbers found across site
        phone_conflicts = [
            {"phone": ph, "occurrences": len(urls), "pages": urls[:4]}
            for ph, urls in all_phones.items()
        ]

    address_conflicts: List[Dict[str, Any]] = []
    if len(all_addresses) > 1:
        address_conflicts = [
            {"address": addr[:60], "occurrences": len(urls), "pages": urls[:4]}
            for addr, urls in all_addresses.items()
        ]

    # Calculate NAP Consistency Score
    nap_score = 100.0
    if phone_conflicts:
        nap_score -= min(40.0, len(phone_conflicts) * 15.0)
    if address_conflicts:
        nap_score -= min(40.0, len(address_conflicts) * 15.0)
    if not all_phones and not all_addresses:
        nap_score = 50.0  # Unproven / no local contact declared

    nap_score = max(0.0, round(nap_score, 1))

    # Schema Completeness
    schema_completeness = 100.0
    if local_schema_found:
        deductions = len(set(schema_missing_fields)) * 20.0
        schema_completeness = max(20.0, 100.0 - deductions)
    else:
        schema_completeness = 0.0

    # Determine overall status
    is_local_intent = bool(local_schema_found or local_landing_pages or gbp_urls or has_map_embed or len(all_phones) > 0)
    
    if not is_local_intent:
        overall_status = "NOT_APPLICABLE"
        summary_text = "No local business presence, physical address, or geo-landing pages detected. Local SEO checks not applicable."
    elif nap_score < 60.0 or (local_landing_pages and any(lp.status == "CRITICAL" for lp in local_landing_pages)):
        overall_status = "FAILED"
        summary_text = f"Local SEO deficiencies detected: NAP consistency score is {nap_score}/100 with conflicting contact details across pages."
    elif not gbp_urls or not local_schema_found:
        overall_status = "NEEDS_ATTENTION"
        summary_text = "Local business elements detected, but missing official Google Business Profile linkage or comprehensive LocalBusiness schema."
    else:
        overall_status = "PASS"
        summary_text = f"Healthy Local SEO foundation. NAP consistency score is {nap_score}/100 with verified Google Business Profile and LocalBusiness schema."

    # 4. Generate Findings
    home_url = pages[0].url if pages else f"https://{target_domain}"

    if is_local_intent and phone_conflicts and len(phone_conflicts) > 1:
        findings.append(
            Finding(
                finding_id="local_seo_nap_phone_conflict",
                title=f"Inconsistent Phone Numbers Detected Across Pages ({len(phone_conflicts)} variants)",
                description=(
                    f"The crawler identified {len(phone_conflicts)} differing phone numbers across your crawled pages and schema. "
                    "Inconsistent NAP (Name, Address, Phone) information degrades Google Local Pack rankings and creates consumer confusion."
                ),
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                confidence=0.95,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_nap_extractor",
                        detail=f"Found {len(phone_conflicts)} phone variants: {', '.join(p['phone'] for p in phone_conflicts[:3])}",
                        url=home_url,
                    )
                ],
                recommendation=(
                    "Standardize a single authoritative phone number across your website header, footer, contact page, "
                    "Google Business Profile, and LocalBusiness schema."
                ),
            )
        )

    if is_local_intent and not gbp_urls and not has_map_embed:
        findings.append(
            Finding(
                finding_id="local_seo_missing_gbp_map",
                title="Missing Google Business Profile Link & Google Maps Embed",
                description=(
                    "No links to Google Business Profile (e.g. maps.google.com, g.page) or interactive Google Maps embeds "
                    "were detected on your contact or location pages. This prevents search engines from confidently establishing entity co-reference."
                ),
                category=Category.TRUST_AUTHORITY,
                severity=Severity.MEDIUM,
                confidence=0.90,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_nap_extractor",
                        detail="Checked footer, contact, and header links across crawled pages. Found 0 GBP or Maps embeds.",
                        url=home_url,
                    )
                ],
                recommendation=(
                    "Add an embedded Google Map of your physical location to your /contact page and link directly to your verified Google Business Profile."
                ),
            )
        )

    if local_landing_pages:
        failing_locals = [lp for lp in local_landing_pages if lp.status in ("CRITICAL", "INCOMPLETE")]
        if failing_locals:
            findings.append(
                Finding(
                    finding_id="local_seo_incomplete_landing_pages",
                    title=f"{len(failing_locals)} Local Landing Page(s) Missing Localized NAP or Schema",
                    description=(
                        f"Detected {len(local_landing_pages)} location/geo landing pages, but {len(failing_locals)} of them lack unique local phone numbers, "
                        "physical addresses, or dedicated LocalBusiness structured data."
                    ),
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.HIGH,
                    confidence=0.95,
                    rubric_confidence=RubricConfidence.VERIFIED,
                    evidence_class=EvidenceClass.OBSERVED,
                    evidence=[
                        FindingEvidence(
                            source="crawler_local_landing_audit",
                            detail=f"Incomplete landing pages: {', '.join(lp.url for lp in failing_locals[:3])}",
                            url=failing_locals[0].url,
                        )
                    ],
                    recommendation=(
                        "For each localized landing page, implement distinct NAP coordinates, embedded local maps, customer reviews from that area, "
                        "and page-specific LocalBusiness JSON-LD."
                    ),
                )
            )

    report = LocalSeoAuditReport(
        status=overall_status,
        nap_consistency_score=nap_score,
        detected_company_name=target_domain,
        consistent_phone=list(all_phones.keys())[0] if len(all_phones) == 1 else None,
        consistent_address=list(all_addresses.keys())[0] if len(all_addresses) == 1 else None,
        phone_conflicts=phone_conflicts,
        address_conflicts=address_conflicts,
        has_google_business_profile=bool(gbp_urls),
        gbp_urls=gbp_urls,
        has_google_maps_embed=has_map_embed,
        local_citations_found=citation_links,
        local_business_schema_found=local_schema_found,
        local_schema_completeness_pct=schema_completeness,
        schema_missing_fields=list(set(schema_missing_fields)),
        local_landing_pages=local_landing_pages,
        nap_records=nap_records,
        summary=summary_text,
    )

    return report, findings
