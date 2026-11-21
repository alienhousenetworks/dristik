"""Phase 5 — Website Discovery, 15-Type Page Inventory & Journey Mapping.

Classifies discovered pages by page type, business purpose, conversion objective,
journey position, and importance, and maps business-model-specific conversion
journeys with strictly separated Technical Status (crawl/browser verified) and
Behavioral Status (measured analytics only; UNMEASURED when analytics absent).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.cro.journey_mapper import JourneyMapper
from app.cro.models import (
    CROBusinessModelType,
    CROBusinessProfile,
    CROGoal,
    CROJourney,
    CROJourneyStep,
    CROPage,
    CROPageType,
)

PAGE_TYPE_RULES: List[Tuple[CROPageType, re.Pattern[str], str, str, str]] = [
    (CROPageType.CHECKOUT, re.compile(r"/(checkout|pay|payment|order-review)", re.I), "Complete purchase transaction", "checkout", "critical"),
    (CROPageType.CART, re.compile(r"/(cart|basket|bag)", re.I), "Review selected items and start checkout", "action", "critical"),
    (CROPageType.PRICING_PAGE, re.compile(r"/(pricing|plans|packages|rates|tuition)", re.I), "Evaluate commercial tiers and pricing", "pricing", "critical"),
    (CROPageType.DEMO_CONSULTATION, re.compile(r"/(demo|consultation|schedule|request-demo|talk-to-sales)", re.I), "Capture high-intent demo or sales inquiry", "action", "critical"),
    (CROPageType.BOOKING, re.compile(r"/(book|booking|reserve|reservation|appointment)", re.I), "Complete service or appointment booking", "action", "critical"),
    (CROPageType.CONTACT, re.compile(r"/(contact|get-in-touch|inquiry|quote)", re.I), "Capture direct lead or support inquiry", "action", "high"),
    (CROPageType.AUTH_REGISTRATION, re.compile(r"/(signup|sign-up|register|login|sign-in|trial|start)", re.I), "Create account or begin free trial", "action", "critical"),
    (CROPageType.PRODUCT_DETAIL, re.compile(r"/(product|products|item|shop)/[^/]+", re.I), "Evaluate specific product and trigger Add to Cart", "evaluation", "critical"),
    (CROPageType.CATEGORY_PAGE, re.compile(r"/(category|categories|collection|collections|catalog|shop)/?$", re.I), "Browse and filter product catalog", "discovery", "high"),
    (CROPageType.PRODUCT_PAGE, re.compile(r"/(product|products|platform|features)", re.I), "Communicate product capabilities and value", "evaluation", "high"),
    (CROPageType.SERVICE_PAGE, re.compile(r"/(service|services|solutions|capabilities|practice)", re.I), "Communicate service offer and qualify buyers", "evaluation", "high"),
    (CROPageType.LANDING_PAGE, re.compile(r"/(lp|landing|offer|promo|campaign|welcome|get-started)", re.I), "Convert campaign or search visitors", "entry", "critical"),
    (CROPageType.TRUST_POLICY, re.compile(r"/(privacy|terms|refund|return|shipping|security|trust|compliance|about|case-stud|testimonials|reviews)", re.I), "Validate credibility, policies, and legal reassurance", "trust", "medium"),
    (CROPageType.SUPPORT_FAQ, re.compile(r"/(faq|support|help|docs|documentation)", re.I), "Resolve objections and pre-purchase questions", "evaluation", "medium"),
]


def classify_cro_page(url: str, title: str = "", html: str = "") -> Tuple[CROPageType, str, str, str]:
    parsed = urlparse(url)
    path = (parsed.path or "/").strip()
    if path in ("", "/"):
        return CROPageType.HOMEPAGE, "Primary brand entry, value proposition, and conversion routing", "entry", "critical"

    for ptype, pattern, purpose, pos, importance in PAGE_TYPE_RULES:
        if pattern.search(path):
            return ptype, purpose, pos, importance

    low = f"{title} {html[:2500]}".lower()
    if "add to cart" in low and ("price" in low or "$" in low or "€" in low or "£" in low or "₹" in low):
        return CROPageType.PRODUCT_DETAIL, "Evaluate specific product and trigger Add to Cart", "evaluation", "critical"
    if "<form" in low and any(k in low for k in ("book a demo", "request a quote", "contact us")):
        return CROPageType.LANDING_PAGE, "Convert visitors through lead-capture form", "entry", "high"
    return CROPageType.GENERAL, "Informational or supporting site page", "discovery", "low"


JOURNEY_TEMPLATES: Dict[CROBusinessModelType, List[Tuple[str, str, List[CROPageType], str, Optional[str]]]] = {
    CROBusinessModelType.ECOMMERCE: [
        ("Landing / Entry", "entry", [CROPageType.HOMEPAGE, CROPageType.LANDING_PAGE], "Understand offer and browse products", "page_view"),
        ("Product Discovery", "discovery", [CROPageType.CATEGORY_PAGE, CROPageType.PRODUCT_PAGE], "Filter/select relevant product", "view_item_list"),
        ("Product Detail", "evaluation", [CROPageType.PRODUCT_DETAIL, CROPageType.PRODUCT_PAGE], "Inspect price, proof, shipping, and click Add to Cart", "view_item"),
        ("Cart Review", "action", [CROPageType.CART], "Verify subtotal, shipping, and proceed to checkout", "add_to_cart"),
        ("Checkout & Payment", "checkout", [CROPageType.CHECKOUT], "Enter shipping/payment details without errors", "begin_checkout"),
        ("Purchase Confirmation", "confirmation", [CROPageType.CHECKOUT], "Receive verified order confirmation and purchase event", "purchase"),
    ],
    CROBusinessModelType.SAAS: [
        ("Landing Page Entry", "entry", [CROPageType.HOMEPAGE, CROPageType.LANDING_PAGE], "Comprehend value proposition and click primary CTA", "page_view"),
        ("Product & Value Evaluation", "evaluation", [CROPageType.PRODUCT_PAGE, CROPageType.SERVICE_PAGE], "Evaluate capabilities and differentiation", "view_product"),
        ("Pricing & Trust Review", "pricing", [CROPageType.PRICING_PAGE, CROPageType.TRUST_POLICY], "Compare plans, security, and risk-reversal policies", "view_pricing"),
        ("Trial Signup / Demo Form", "action", [CROPageType.AUTH_REGISTRATION, CROPageType.DEMO_CONSULTATION, CROPageType.CONTACT], "Complete signup or demo request form cleanly", "form_start"),
        ("Activation / Qualified Conversion", "confirmation", [CROPageType.AUTH_REGISTRATION, CROPageType.DEMO_CONSULTATION], "Confirm account activation or demo booking", "sign_up"),
    ],
}

DEFAULT_LEAD_GEN_TEMPLATE: List[Tuple[str, str, List[CROPageType], str, Optional[str]]] = [
    ("Landing Page Entry", "entry", [CROPageType.HOMEPAGE, CROPageType.LANDING_PAGE], "Match visitor intent and establish offer clarity", "page_view"),
    ("Service / Offer Evaluation", "evaluation", [CROPageType.SERVICE_PAGE, CROPageType.PRODUCT_PAGE, CROPageType.PRICING_PAGE], "Understand deliverables, scope, and pricing", "view_service"),
    ("Trust & Objection Validation", "trust", [CROPageType.TRUST_POLICY, CROPageType.SUPPORT_FAQ], "Verify reviews, credentials, and policies", "view_trust"),
    ("Primary CTA & Contact/Booking Form", "action", [CROPageType.DEMO_CONSULTATION, CROPageType.BOOKING, CROPageType.CONTACT], "Click conversion CTA and complete form without friction", "form_start"),
    ("Submission Success & Qualified Lead", "confirmation", [CROPageType.CONTACT, CROPageType.BOOKING, CROPageType.DEMO_CONSULTATION], "Receive clear confirmation and record lead event", "generate_lead"),
]


class CRODiscoveryEngine:
    """Discovers and classifies pages and maps model-aware conversion journeys."""

    @classmethod
    def build_inventory_and_journeys(
        cls,
        *,
        tenant_id: str,
        audit_id: str,
        profile: CROBusinessProfile,
        goals: Sequence[CROGoal],
        raw_pages: Sequence[Any],
        raw_html_map: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[CROPage], List[CROJourney], Dict[str, Any]]:
        html_map = raw_html_map or {}
        cro_pages: List[CROPage] = []

        for idx, p in enumerate(raw_pages):
            url = (p.get("url") if isinstance(p, dict) else getattr(p, "url", "")) or f"{profile.website_url}#page_{idx}"
            title = (p.get("title") if isinstance(p, dict) else getattr(p, "title", "")) or ""
            html = html_map.get(url) or (p.get("raw_html") if isinstance(p, dict) else getattr(p, "raw_html", "")) or ""
            body_text = (p.get("body_text") if isinstance(p, dict) else getattr(p, "body_text", "")) or ""
            status_code = p.get("status_code") if isinstance(p, dict) else getattr(p, "status_code", 200)
            rendered = bool(p.get("rendered") if isinstance(p, dict) else getattr(p, "rendered", False))

            soup = BeautifulSoup(html, "html.parser") if html else None
            h1_tag = soup.find("h1") if soup else None
            h1_text = h1_tag.get_text(" ", strip=True) if h1_tag else ""
            if not h1_text:
                h1_list = p.get("h1") if isinstance(p, dict) else getattr(p, "h1", None)
                if isinstance(h1_list, list) and h1_list:
                    h1_text = str(h1_list[0])
            subhead = ""
            if h1_tag:
                nxt = h1_tag.find_next_sibling(["p", "h2"])
                if nxt:
                    subhead = nxt.get_text(" ", strip=True)[:240]

            forms_cnt = len(soup.find_all("form")) if soup else int((p.get("forms_count") if isinstance(p, dict) else getattr(p, "forms_count", 0)) or 0)
            buttons = soup.find_all(["button", "a"]) if soup else []
            cta_candidates = [
                el.get_text(" ", strip=True)
                for el in buttons
                if el.get_text(strip=True) and len(el.get_text(strip=True)) <= 45 and (
                    el.name == "button"
                    or any(c in " ".join(el.get("class") or []).lower() for c in ("btn", "button", "cta", "primary"))
                )
            ]
            word_count = len((body_text or (soup.get_text(" ", strip=True) if soup else "")).split())
            ptype, purpose, pos, importance = classify_cro_page(url, title, html)

            cro_pages.append(
                CROPage(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    url=url,
                    page_type=ptype,
                    business_purpose=purpose,
                    conversion_objective=profile.primary_conversion if importance == "critical" else "Support conversion progression",
                    target_audience=profile.target_customers or "unknown",
                    journey_position=pos,
                    importance=importance,
                    http_status=int(status_code) if isinstance(status_code, (int, float)) else None,
                    title=title or None,
                    h1=h1_text or None,
                    subheadline=subhead or None,
                    word_count=word_count,
                    rendered_dom_verified=rendered,
                    primary_cta=cta_candidates[0] if cta_candidates else None,
                    cta_count=len(cta_candidates),
                    forms_count=forms_cnt,
                )
            )

        # Graph analysis reusing JourneyMapper (preserving existing dead-end & loop detection)
        graph_result = None
        try:
            graph_result = JourneyMapper.map_journey(list(raw_pages), html_map, domain=profile.domain)
        except Exception:
            graph_result = None

        # Map canonical business-model journey
        template = JOURNEY_TEMPLATES.get(profile.business_type, DEFAULT_LEAD_GEN_TEMPLATE)
        primary_goal = next((g for g in goals if g.goal_type == "primary"), goals[0] if goals else None)
        journey_id_placeholder = f"cro_jrn_{audit_id[-8:]}"
        steps: List[CROJourneyStep] = []

        for order, (step_name, stage, match_types, expected_interaction, default_evt) in enumerate(template, start=1):
            matched_page = next((pg for pg in cro_pages if pg.page_type in match_types), None)
            if matched_page is None and order == 1 and cro_pages:
                matched_page = cro_pages[0]

            if matched_page:
                tech_status = "passed" if (matched_page.http_status or 200) < 400 else "failed"
                tech_notes = f"Matched {matched_page.page_type.value} page ({matched_page.url})."
                if graph_result and matched_page.url in graph_result.dead_ends:
                    tech_status = "warning"
                    tech_notes += " Page flagged as navigation dead end."
            else:
                tech_status = "not_tested"
                tech_notes = f"No crawled page matched stage '{step_name}' in this audit sample."

            steps.append(
                CROJourneyStep(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    journey_id=journey_id_placeholder,
                    step_order=order,
                    name=step_name,
                    stage=stage,
                    page_id=matched_page.page_id if matched_page else None,
                    url=matched_page.url if matched_page else None,
                    expected_interaction=expected_interaction,
                    possible_failure_states=[
                        "Broken link or HTTP >= 400",
                        "Unclickable or obscured CTA",
                        "Form validation failure or missing confirmation",
                    ],
                    analytics_event_name=default_evt,
                    technical_status=tech_status,
                    technical_notes=tech_notes,
                    behavioral_status="unmeasured",
                    behavioral_metrics={"note": "Requires connected analytics event stream."},
                )
            )

        any_failed = any(s.technical_status == "failed" for s in steps)
        any_warn = any(s.technical_status == "warning" for s in steps)
        any_passed = any(s.technical_status == "passed" for s in steps)
        tech_health = "broken" if any_failed else ("degraded" if any_warn else ("healthy" if any_passed else "not_tested"))

        primary_journey = CROJourney(
            tenant_id=tenant_id,
            audit_id=audit_id,
            url=profile.website_url,
            name=f"Primary {profile.business_type.value.replace('_', ' ').title()} Conversion Journey",
            business_model=profile.business_type,
            goal_id=primary_goal.goal_id if primary_goal else None,
            entry_points=[pg.url for pg in cro_pages if pg.page_type in (CROPageType.HOMEPAGE, CROPageType.LANDING_PAGE)][:5] or ([cro_pages[0].url] if cro_pages else []),
            steps=steps,
            technical_health=tech_health,
            behavioral_health="unmeasured",
        )
        for st in primary_journey.steps:
            st.journey_id = primary_journey.journey_id

        graph_summary = graph_result.model_dump() if graph_result else {
            "dead_ends": [],
            "navigation_loops": [],
            "broken_journeys": [],
            "secondary_paths": [],
        }
        return cro_pages, [primary_journey], graph_summary
