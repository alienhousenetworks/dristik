"""Phase 2 — CRO Business Understanding & Audit Configuration Engine.

Supports all 12 enterprise business models, infers primary & secondary conversion
definitions from explicit configuration and crawl evidence, allows partial config
while explicitly marking unknown fields as unknown (zero invention), and outputs a
structured CROBusinessProfile, CROGoal registry, CROAudience list, and audit scope.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from app.cro.models import (
    CROAudience,
    CROBusinessModelType,
    CROBusinessProfile,
    CROGoal,
)

MODEL_CONVERSION_BLUEPRINTS: Dict[CROBusinessModelType, Dict[str, Any]] = {
    CROBusinessModelType.ECOMMERCE: {
        "primary": ("Completed purchase", "purchase", ["transaction_id", "value", "currency", "items"]),
        "secondary": [
            ("Add to cart", "add_to_cart", ["item_id", "value"]),
            ("Begin checkout", "begin_checkout", ["value", "currency"]),
        ],
        "objections": ["Shipping cost & delivery speed", "Return/refund policy", "Product quality & authenticity", "Payment security"],
        "applicable_modules": ["ecommerce", "checkout", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.SAAS: {
        "primary": ("Paid subscription", "purchase", ["plan_id", "value", "billing_cycle"]),
        "secondary": [
            ("Free trial start", "sign_up", ["plan_tier", "source"]),
            ("Demo request", "generate_lead", ["form_id", "company_size"]),
        ],
        "objections": ["Implementation effort & onboarding time", "Pricing transparency", "Security & compliance (SOC 2/GDPR)", "Cancellation terms"],
        "applicable_modules": ["saas", "pricing", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.B2B_LEAD_GEN: {
        "primary": ("Qualified lead", "generate_lead", ["form_id", "page_location", "lead_source"]),
        "secondary": [
            ("Contact form submission", "contact_submit", ["form_id"]),
            ("Consultation booking", "book_consultation", ["calendar_slot"]),
        ],
        "objections": ["Vendor credibility & case studies", "Expected ROI & timeline", "What happens after form submission", "Fit for company size/industry"],
        "applicable_modules": ["lead_generation", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.B2C_LEAD_GEN: {
        "primary": ("Qualified consumer inquiry", "generate_lead", ["form_id", "page_location"]),
        "secondary": [
            ("Quote request", "request_quote", ["service_type"]),
            ("Phone call click", "click_phone", ["tel_href"]),
        ],
        "objections": ["Transparent pricing", "Response speed", "Data privacy / spam concern", "Service guarantee"],
        "applicable_modules": ["lead_generation", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.PROFESSIONAL_SERVICES: {
        "primary": ("Qualified client inquiry", "generate_lead", ["form_id", "practice_area"]),
        "secondary": [
            ("Discovery call booked", "schedule_call", ["service_line"]),
            ("Case study download", "file_download", ["asset_name"]),
        ],
        "objections": ["Team credentials & track record", "Engagement model & fees", "Confidentiality"],
        "applicable_modules": ["lead_generation", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.LOCAL_SERVICES: {
        "primary": ("Qualified inquiry or booking", "generate_lead", ["service_location", "form_id"]),
        "secondary": [
            ("Phone call tap", "click_phone", ["phone_number"]),
            ("Direction request", "click_directions", ["location_id"]),
        ],
        "objections": ["Service area coverage", "Availability & turnaround", "Local reviews & licensing", "Upfront pricing"],
        "applicable_modules": ["lead_generation", "local", "forms", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.MARKETPLACE: {
        "primary": ("Completed marketplace transaction", "purchase", ["listing_id", "value", "currency"]),
        "secondary": [
            ("Buyer/seller registration", "sign_up", ["account_role"]),
            ("Listing inquiry", "generate_lead", ["listing_id"]),
        ],
        "objections": ["Buyer/seller protection", "Verification & trust", "Fees & dispute resolution"],
        "applicable_modules": ["ecommerce", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.SUBSCRIPTION: {
        "primary": ("Active recurring subscription", "subscribe", ["plan_id", "value", "interval"]),
        "secondary": [
            ("Trial activation", "start_trial", ["plan_id"]),
            ("Plan comparison view", "view_pricing", ["page_location"]),
        ],
        "objections": ["Renewal terms & cancellation ease", "Ongoing value justification", "Billing transparency"],
        "applicable_modules": ["ecommerce", "checkout", "pricing", "forms", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.PUBLISHER_CONTENT: {
        "primary": ("Subscription or member registration", "sign_up", ["membership_tier"]),
        "secondary": [
            ("Newsletter signup", "newsletter_signup", ["placement"]),
            ("Engaged article session", "engaged_read", ["scroll_depth"]),
        ],
        "objections": ["Content quality & cadence", "Email frequency & unsubscribe ease", "Paywall clarity"],
        "applicable_modules": ["landing_pages", "forms", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.BOOKING_RESERVATION: {
        "primary": ("Confirmed reservation / booking", "booking_confirmed", ["booking_id", "value"]),
        "secondary": [
            ("Availability search", "search_availability", ["dates"]),
            ("Checkout start", "begin_booking", ["item_id"]),
        ],
        "objections": ["Cancellation & rescheduling policy", "Hidden taxes/fees", "Real-time availability accuracy"],
        "applicable_modules": ["ecommerce", "checkout", "forms", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.EDUCATION_COURSES: {
        "primary": ("Course or program enrollment", "enroll", ["course_id", "value"]),
        "secondary": [
            ("Application start", "begin_application", ["program_id"]),
            ("Syllabus / course inquiry", "generate_lead", ["course_id"]),
        ],
        "objections": ["Curriculum outcomes & accreditation", "Time commitment & format", "Tuition & refund guarantee"],
        "applicable_modules": ["lead_generation", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.FINANCIAL_SERVICES: {
        "primary": ("Qualified application or account opening", "submit_application", ["product_type"]),
        "secondary": [
            ("Eligibility / rate check", "check_eligibility", ["product_type"]),
            ("Advisor consultation", "book_consultation", ["channel"]),
        ],
        "objections": ["Regulatory disclosures & security", "Fee & APR transparency", "Credit-score impact", "Data privacy"],
        "applicable_modules": ["lead_generation", "forms", "landing_pages", "mobile", "trust", "accessibility", "performance"],
    },
    CROBusinessModelType.UNKNOWN: {
        "primary": ("Primary conversion goal (configure explicitly)", "conversion", ["page_location"]),
        "secondary": [("Key CTA engagement", "cta_click", ["cta_text"])],
        "objections": ["Offer clarity", "Pricing transparency", "Company credibility", "Next-step expectation"],
        "applicable_modules": ["landing_pages", "forms", "mobile", "trust", "accessibility", "performance"],
    },
}


def detect_business_model(
    pages: Sequence[Any],
    explicit_type: Optional[str] = None,
    existing_profile: Optional[Any] = None,
) -> Tuple[CROBusinessModelType, str]:
    """Infer business model cleanly from explicit input, profile hints, and crawled content."""
    if explicit_type:
        norm = explicit_type.strip().lower().replace("-", "_").replace(" ", "_")
        for member in CROBusinessModelType:
            if member.value == norm:
                return member, "Explicitly configured by user."

    corpus_parts: List[str] = []
    urls: List[str] = []
    if existing_profile is not None:
        for attr in ("business_model", "industry", "niche", "value_proposition"):
            val = getattr(existing_profile, attr, None) if not isinstance(existing_profile, dict) else existing_profile.get(attr)
            if val:
                corpus_parts.append(str(val))
    for p in pages:
        u = p.get("url", "") if isinstance(p, dict) else getattr(p, "url", "")
        t = p.get("title", "") if isinstance(p, dict) else getattr(p, "title", "")
        b = p.get("body_text", "") if isinstance(p, dict) else getattr(p, "body_text", "")
        h = p.get("raw_html", "") if isinstance(p, dict) else getattr(p, "raw_html", "")
        urls.append(str(u).lower())
        corpus_parts.append(f"{u} {t} {str(b)[:1200]} {str(h)[:1500]}")

    blob = " ".join(corpus_parts).lower()
    url_blob = " ".join(urls)

    # Ranked deterministic evidence scoring
    signals: Dict[CROBusinessModelType, int] = {}
    def _bump(model: CROBusinessModelType, weight: int) -> None:
        signals[model] = signals.get(model, 0) + weight

    if any(k in url_blob for k in ("/cart", "/checkout", "/product", "/shop", "/collections")):
        _bump(CROBusinessModelType.ECOMMERCE, 4)
    if any(k in blob for k in ("add to cart", "shopping cart", "checkout", "free shipping", "in stock")):
        _bump(CROBusinessModelType.ECOMMERCE, 3)

    if any(k in blob for k in ("saas", "free trial", "book a demo", "per month", "/mo", "api access", "soc 2")):
        _bump(CROBusinessModelType.SAAS, 4)
    if any(k in url_blob for k in ("/pricing", "/demo", "/signup", "/app")):
        _bump(CROBusinessModelType.SAAS, 2)

    if any(k in blob for k in ("request a quote", "contact sales", "enterprise solutions", "case studies", "b2b")):
        _bump(CROBusinessModelType.B2B_LEAD_GEN, 3)
    if any(k in blob for k in ("book an appointment", "opening hours", "get directions", "near me", "service area")):
        _bump(CROBusinessModelType.LOCAL_SERVICES, 4)
    if any(k in blob for k in ("enroll now", "curriculum", "syllabus", "online course", "tuition", "cohort")):
        _bump(CROBusinessModelType.EDUCATION_COURSES, 4)
    if any(k in blob for k in ("check availability", "book now", "reservation", "check-in", "nightly rate")):
        _bump(CROBusinessModelType.BOOKING_RESERVATION, 4)
    if any(k in blob for k in ("apr", "fdic", "loan", "mortgage", "wealth management", "brokerage", "credit card")):
        _bump(CROBusinessModelType.FINANCIAL_SERVICES, 4)
    if any(k in blob for k in ("marketplace", "become a seller", "verified sellers", "browse listings")):
        _bump(CROBusinessModelType.MARKETPLACE, 4)
    if any(k in blob for k in ("subscribe to our newsletter", "editorial", "magazine", "subscriber-only")):
        _bump(CROBusinessModelType.PUBLISHER_CONTENT, 3)
    if any(k in blob for k in ("monthly box", "cancel anytime", "recurring delivery", "membership plan")):
        _bump(CROBusinessModelType.SUBSCRIPTION, 3)
    if any(k in blob for k in ("consulting", "advisory", "law firm", "accounting firm", "agency")):
        _bump(CROBusinessModelType.PROFESSIONAL_SERVICES, 3)

    if not signals:
        return CROBusinessModelType.UNKNOWN, "Insufficient site signals to classify business model; marked unknown."

    winner = max(signals.items(), key=lambda item: item[1])
    if winner[1] < 2:
        return CROBusinessModelType.UNKNOWN, "Weak page signals; business model requires user confirmation."
    return winner[0], f"Inferred from observed page URLs and copy ({winner[1]} matched domain signals)."


class BusinessUnderstandingEngine:
    """Builds the canonical CROBusinessProfile, CROGoal registry, CROAudiences, and scope."""

    @classmethod
    def build(
        cls,
        *,
        tenant_id: str,
        audit_id: Optional[str],
        target_url: str,
        pages: Sequence[Any] = (),
        user_config: Optional[Dict[str, Any]] = None,
        existing_profile: Optional[Any] = None,
    ) -> Tuple[CROBusinessProfile, List[CROGoal], List[CROAudience], Dict[str, Any]]:
        cfg = user_config or {}
        parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
        domain = (parsed.netloc or parsed.path).replace("www.", "").strip("/")
        website_url = target_url if "://" in target_url else f"https://{domain}/"

        model_type, basis = detect_business_model(
            pages=pages,
            explicit_type=cfg.get("business_type"),
            existing_profile=existing_profile,
        )
        blueprint = MODEL_CONVERSION_BLUEPRINTS[model_type]

        # Track every unspecified optional input explicitly as unknown rather than fabricating
        unknown_fields: List[str] = []
        def _opt_str(key: str, fallback: Optional[str] = None) -> str:
            val = cfg.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
            if fallback:
                return fallback
            unknown_fields.append(key)
            return "unknown"

        def _opt_list(key: str) -> List[str]:
            val = cfg.get(key)
            if isinstance(val, list) and val:
                return [str(x).strip() for x in val if str(x).strip()]
            unknown_fields.append(key)
            return []

        primary_name, primary_event, primary_params = blueprint["primary"]
        primary_conversion = _opt_str("primary_conversion", primary_name if model_type != CROBusinessModelType.UNKNOWN else None)

        secondary_cfg = cfg.get("secondary_conversions")
        if isinstance(secondary_cfg, list) and secondary_cfg:
            secondary_conversions = [str(s) for s in secondary_cfg]
        else:
            secondary_conversions = [item[0] for item in blueprint["secondary"]]

        aov = cfg.get("average_order_value")
        if aov is None:
            unknown_fields.append("average_order_value")

        products_services = _opt_list("products_and_services")
        target_customers = cfg.get("target_customers")
        if not target_customers:
            unknown_fields.append("target_customers")

        profile = CROBusinessProfile(
            tenant_id=tenant_id,
            audit_id=audit_id,
            domain=domain,
            website_url=website_url,
            url=website_url,
            business_name=cfg.get("business_name") or (getattr(existing_profile, "business_name", None) if existing_profile else None) or domain.split(".")[0].title(),
            business_type=model_type,
            products_and_services=products_services,
            target_customers=str(target_customers) if target_customers else "unknown",
            geographic_markets=_opt_list("geographic_markets"),
            pricing_model=_opt_str("pricing_model"),
            primary_conversion=primary_conversion,
            secondary_conversions=secondary_conversions,
            average_order_value=float(aov) if isinstance(aov, (int, float)) and aov > 0 else None,
            currency=cfg.get("currency"),
            revenue_model=_opt_str("revenue_model"),
            lead_qualification_criteria=_opt_list("lead_qualification_criteria"),
            main_acquisition_channels=_opt_list("main_acquisition_channels"),
            known_competitors=_opt_list("known_competitors"),
            analytics_configuration=cfg.get("analytics_configuration") or {},
            important_pages=cfg.get("important_pages") or [
                (p.get("url") if isinstance(p, dict) else getattr(p, "url", "")) for p in list(pages)[:10] if (p.get("url") if isinstance(p, dict) else getattr(p, "url", ""))
            ],
            known_conversion_problems=cfg.get("known_conversion_problems") or [],
            unknown_fields=sorted(set(unknown_fields)),
            inference_basis=basis,
            confidence=0.95 if cfg.get("business_type") else (0.75 if model_type != CROBusinessModelType.UNKNOWN else 0.3),
        )

        # Build Conversion Goal Registry (supporting user-supplied + blueprint defaults)
        goals: List[CROGoal] = []
        custom_goals = cfg.get("goals") or []
        if isinstance(custom_goals, list) and custom_goals:
            for g in custom_goals:
                goals.append(
                    CROGoal(
                        tenant_id=tenant_id,
                        audit_id=audit_id,
                        profile_id=profile.profile_id,
                        url=website_url,
                        name=g.get("name", primary_conversion),
                        goal_type=g.get("goal_type", "primary"),
                        business_model=model_type,
                        target_action=g.get("target_action", g.get("name", primary_conversion)),
                        target_urls=g.get("target_urls") or [],
                        analytics_event_name=g.get("analytics_event_name"),
                        required_event_params=g.get("required_event_params") or [],
                        value_per_conversion=g.get("value_per_conversion") or profile.average_order_value,
                        qualification_criteria=g.get("qualification_criteria"),
                    )
                )
        else:
            goals.append(
                CROGoal(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    profile_id=profile.profile_id,
                    url=website_url,
                    name=primary_conversion,
                    goal_type="primary",
                    business_model=model_type,
                    target_action=primary_conversion,
                    analytics_event_name=primary_event,
                    required_event_params=list(primary_params),
                    value_per_conversion=profile.average_order_value,
                )
            )
            for sec_name, sec_evt, sec_params in blueprint["secondary"]:
                goals.append(
                    CROGoal(
                        tenant_id=tenant_id,
                        audit_id=audit_id,
                        profile_id=profile.profile_id,
                        url=website_url,
                        name=sec_name,
                        goal_type="secondary",
                        business_model=model_type,
                        target_action=sec_name,
                        analytics_event_name=sec_evt,
                        required_event_params=list(sec_params),
                    )
                )

        # Build Audience definitions
        audiences: List[CROAudience] = []
        raw_auds = cfg.get("audiences") or []
        if isinstance(raw_auds, list) and raw_auds:
            for a in raw_auds:
                audiences.append(
                    CROAudience(
                        tenant_id=tenant_id,
                        audit_id=audit_id,
                        profile_id=profile.profile_id,
                        url=website_url,
                        name=a.get("name", "Primary Visitor Segment"),
                        segment_type=a.get("segment_type", "primary_buyer"),
                        intent_level=a.get("intent_level", "unknown"),
                        key_objections=a.get("key_objections") or list(blueprint["objections"]),
                        decision_drivers=a.get("decision_drivers") or [],
                        channels=a.get("channels") or profile.main_acquisition_channels,
                    )
                )
        else:
            audiences.append(
                CROAudience(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    profile_id=profile.profile_id,
                    url=website_url,
                    name=profile.target_customers if profile.target_customers != "unknown" else "Primary Prospective Buyers (Unconfigured)",
                    segment_type="primary_buyer",
                    intent_level="evaluative",
                    key_objections=list(blueprint["objections"]),
                    channels=profile.main_acquisition_channels,
                )
            )

        scope = {
            "business_model": model_type.value,
            "applicable_modules": list(blueprint["applicable_modules"]),
            "ecommerce_applicable": model_type in (
                CROBusinessModelType.ECOMMERCE,
                CROBusinessModelType.MARKETPLACE,
                CROBusinessModelType.SUBSCRIPTION,
                CROBusinessModelType.BOOKING_RESERVATION,
            ),
            "lead_gen_applicable": model_type in (
                CROBusinessModelType.B2B_LEAD_GEN,
                CROBusinessModelType.B2C_LEAD_GEN,
                CROBusinessModelType.PROFESSIONAL_SERVICES,
                CROBusinessModelType.LOCAL_SERVICES,
                CROBusinessModelType.SAAS,
                CROBusinessModelType.EDUCATION_COURSES,
                CROBusinessModelType.FINANCIAL_SERVICES,
            ),
            "unknown_profile_fields": profile.unknown_fields,
            "goals_count": len(goals),
        }
        return profile, goals, audiences, scope
