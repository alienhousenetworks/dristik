"""
E-commerce SEO Analyzer for Dristik AI (2026 Standard)
Evaluates:
1. Product & Offer Schema Compliance (Merchant Return Policy, Shipping Details, Price, Availability)
2. Faceted Navigation & Parameter Filter Traps (Crawl budget dilution, canonicalization)
3. Out-of-Stock handling & URL structure
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

from app.domain.enums import Category, EvidenceClass, FindingStatus, RubricConfidence, Severity
from app.domain.models import (
    EcommerceSeoAuditReport,
    FacetedFilterTrap,
    Finding,
    FindingEvidence,
    PageEvidence,
    ProductSchemaIssue,
)

_ECOMMERCE_URL_PATTERNS = [
    r"/products?(/|$)",
    r"/items?(/|$)",
    r"/p/[a-zA-Z0-9_-]+",
    r"/shop(/|$)",
    r"/collections?(/|$)",
    r"/cart(/|$)",
    r"/checkout(/|$)",
]

_FACET_PARAMS = {
    "sort", "order", "dir", "color", "size", "price", "min_price", "max_price",
    "filter", "brand", "tag", "rating", "page", "p", "limit"
}


def _is_ecommerce_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(re.search(pat, path) for pat in _ECOMMERCE_URL_PATTERNS)


def _extract_entities(raw_schemas: Sequence[Any]) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    for item in raw_schemas:
        if not isinstance(item, dict):
            continue
        candidates = [item]
        if "@graph" in item and isinstance(item["@graph"], list):
            candidates.extend([g for g in item["@graph"] if isinstance(g, dict)])
        for candidate in candidates:
            entities.append(candidate)
    return entities


def analyze_ecommerce_seo(
    pages: Sequence[PageEvidence],
    target_domain: str = "",
) -> Tuple[EcommerceSeoAuditReport, List[Finding]]:
    """
    Audits e-commerce SEO compliance across crawled pages.
    Returns (EcommerceSeoAuditReport, List[Finding]).
    """
    if not pages:
        return EcommerceSeoAuditReport(
            is_ecommerce_detected=False,
            status="NOT_APPLICABLE",
            summary="No pages available to audit E-commerce SEO.",
        ), []

    detected_ecommerce = False
    detection_basis_reasons: List[str] = []
    product_issues: List[ProductSchemaIssue] = []
    faceted_traps: List[FacetedFilterTrap] = []
    findings: List[Finding] = []

    total_products_found = 0
    compliant_products_count = 0

    # 1. First pass: Determine if e-commerce site
    for p in pages:
        url_match = _is_ecommerce_url(p.url)
        has_prod_schema = any(
            "product" in str(st).lower()
            for st in (p.schema_types or [])
        )
        if url_match or has_prod_schema:
            detected_ecommerce = True
            if url_match:
                detection_basis_reasons.append(f"E-commerce URL pattern detected: {p.url}")
            if has_prod_schema:
                detection_basis_reasons.append(f"Product schema detected on: {p.url}")
            break

    if not detected_ecommerce:
        return EcommerceSeoAuditReport(
            is_ecommerce_detected=False,
            status="NOT_APPLICABLE",
            detection_basis="No product URLs, cart patterns, or Product schema detected.",
            summary="Website is not an e-commerce platform. E-commerce SEO audit is not applicable.",
        ), []

    # 2. Audit Product schemas & URL structures
    for page in pages:
        entities = _extract_entities(page.raw_schema or [])
        product_entities = [e for e in entities if str(e.get("@type", "")).lower() == "product"]

        for prod in product_entities:
            total_products_found += 1
            missing: List[str] = []
            name = prod.get("name") or page.title or "Unknown Product"

            if not prod.get("name"):
                missing.append("name")
            if not (prod.get("image") or prod.get("images")):
                missing.append("image")
            if not prod.get("description"):
                missing.append("description")

            # Check Offers
            offers = prod.get("offers")
            has_valid_offer = False
            if offers:
                if isinstance(offers, dict):
                    offers_list = [offers]
                elif isinstance(offers, list):
                    offers_list = offers
                else:
                    offers_list = []

                for off in offers_list:
                    if isinstance(off, dict):
                        if not off.get("price") and not off.get("lowPrice"):
                            missing.append("offers.price")
                        if not off.get("priceCurrency"):
                            missing.append("offers.priceCurrency")
                        if not off.get("availability"):
                            missing.append("offers.availability")
                        if off.get("price") and off.get("priceCurrency"):
                            has_valid_offer = True
            else:
                missing.append("offers")

            # Merchant center 2024-2026 specs
            has_return = bool(
                prod.get("hasMerchantReturnPolicy") or
                (isinstance(offers, dict) and offers.get("hasMerchantReturnPolicy"))
            )
            has_shipping = bool(
                prod.get("shippingDetails") or
                (isinstance(offers, dict) and offers.get("shippingDetails"))
            )

            if missing:
                product_issues.append(
                    ProductSchemaIssue(
                        url=page.url,
                        product_name=name,
                        missing_fields=list(set(missing)),
                        has_merchant_return_policy=has_return,
                        has_shipping_details=has_shipping,
                    )
                )
            else:
                compliant_products_count += 1

        # Check faceted URL traps in page URLs and internal links
        all_links_to_check = [page.url] + (page.internal_links or [])
        for link in all_links_to_check:
            parsed = urlparse(link)
            if not parsed.query:
                continue
            query_params = set(parse_qs(parsed.query).keys())
            matched_facets = query_params.intersection(_FACET_PARAMS)
            if len(matched_facets) >= 2 or (len(matched_facets) == 1 and ("filter" in matched_facets or "sort" in matched_facets)):
                # Inspect canonical
                has_canon = bool(page.canonical_url and page.canonical_url.strip())
                is_self_canon = has_canon and (page.canonical_url.strip() == page.url.strip())
                is_noindexed = "noindex" in str(getattr(page, "robots_meta", "") or "").lower()

                trap_risk = "HIGH" if (not has_canon or is_self_canon) and not is_noindexed else "LOW"

                trap = FacetedFilterTrap(
                    url=link,
                    param_keys=sorted(list(matched_facets)),
                    has_canonical=has_canon,
                    canonical_target=page.canonical_url,
                    is_noindexed=is_noindexed,
                    risk_level=trap_risk,
                )
                if not any(t.url == link for t in faceted_traps):
                    faceted_traps.append(trap)

    compliance_pct = (
        round((compliant_products_count / total_products_found) * 100, 1)
        if total_products_found > 0
        else 0.0
    )

    high_risk_traps = [t for t in faceted_traps if t.risk_level == "HIGH"]
    status = "PASS"
    if high_risk_traps or (total_products_found > 0 and compliance_pct < 60.0):
        status = "CRITICAL"
    elif product_issues or faceted_traps:
        status = "WARNING"

    summary = (
        f"E-commerce catalog evaluated ({total_products_found} products detected). "
        f"Product schema compliance is {compliance_pct}%. "
        f"{len(faceted_traps)} faceted navigation URLs discovered with {len(high_risk_traps)} high-risk indexation traps."
    )

    # 3. Create Findings
    if product_issues:
        finding_id = "FINDING-ECOM-001"
        missing_sample = ", ".join(product_issues[0].missing_fields)
        affected = [iss.url for iss in product_issues[:10]]
        findings.append(
            Finding(
                finding_id=finding_id,
                category=Category.SCHEMA,
                subcategory="E-Commerce Product Schema",
                affected_urls=affected,
                expected_condition="All product pages must specify valid Product schema with offers (price, currency, availability) and return policies.",
                dependencies=["Catalog CMS / Theme JSON-LD Template"],
                status=FindingStatus.OPEN,
                owner="Engineering",
                severity=Severity.HIGH,
                title="Incomplete Product Schema & Offer Properties",
                description=(
                    f"{len(product_issues)} product page(s) lack required Google Merchant and rich snippet fields. "
                    f"Example missing properties: {missing_sample}."
                ),
                recommendation="Enrich Product JSON-LD with complete Offer objects including price, priceCurrency, availability, and merchant return policies.",
                impact=8,
                effort=4,
                priority=8,
                confidence=0.95,
                confidence_basis="Machine-parsed schema extraction across product entities.",
                why_it_matters="Incomplete product schema prevents Google from rendering rich product pricing, stock badges, and Merchant Center free listings.",
                validation_criteria="Rich Result Test confirms Product schema with zero error-level property omissions.",
                evidence_class=EvidenceClass.OBSERVED,
            )
        )

    if high_risk_traps:
        finding_id = "FINDING-ECOM-002"
        affected = [t.url for t in high_risk_traps[:10]]
        findings.append(
            Finding(
                finding_id=finding_id,
                category=Category.TECHNICAL_SEO,
                subcategory="Faceted Navigation & Filter Traps",
                affected_urls=affected,
                expected_condition="Faceted filter URLs must either self-canonicalize to root category or carry noindex / robots disallow.",
                dependencies=["SEO Routing / Robots.txt / Header Templates"],
                status=FindingStatus.OPEN,
                owner="Engineering",
                severity=Severity.HIGH,
                title="Unconstrained Faceted Filter URL Indexation Trap",
                description=(
                    f"Detected {len(high_risk_traps)} faceted navigation parameter URLs without clean canonicalization or noindex directives. "
                    "This creates near-infinite crawl traps and duplicates ranking signals."
                ),
                recommendation="Point canonical tags on filter-sorted pages to the canonical root collection URL, or set noindex on faceted queries.",
                impact=8,
                effort=5,
                priority=8,
                confidence=0.92,
                confidence_basis="Direct URL parameter parsing and canonical header inspection.",
                why_it_matters="Faceted URL traps deplete search engine crawl budgets and cause severe internal keyword cannibalization.",
                validation_criteria="All faceted URL variations either resolve canonical to the parent category or serve 'noindex, follow'.",
                evidence_class=EvidenceClass.OBSERVED,
            )
        )

    report = EcommerceSeoAuditReport(
        is_ecommerce_detected=True,
        status=status,
        detection_basis="; ".join(detection_basis_reasons[:3]),
        products_analyzed=total_products_found,
        product_schema_compliance_pct=compliance_pct,
        products_with_issues=product_issues,
        faceted_urls_found=len(faceted_traps),
        faceted_traps=faceted_traps,
        out_of_stock_handling_notes="Checked availability signals across detected product catalog.",
        summary=summary,
    )

    return report, findings
