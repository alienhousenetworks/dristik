"""
E-Commerce & SaaS Conversion Funnel Intelligence (Phase 6.6).

Analyzes commercial transaction ergonomics across store and SaaS flows:
1. Store E-Commerce: Product completeness, imagery, variants, price visibility,
   shipping info, returns policy, stock status, reviews/ratings, cart behavior,
   checkout steps, guest checkout availability, payment options, coupon friction, trust signals.
2. SaaS & B2B: Demo booking, self-serve signup, lead qualification friction, pricing tiers,
   onboarding progression, contract terms.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.domain.models import PageEvidence, Finding
from app.domain.enums import Category, Severity, EvidenceClass


class EcommerceFlowAudit(BaseModel):
    is_ecommerce_site: bool = False
    product_pages_analyzed: int = 0
    has_product_imagery: bool = False
    has_product_variants: bool = False
    price_visibility: str = "NOT_DETECTED" # "PROMINENT", "INFERRED", "HIDDEN"
    shipping_policy_detected: bool = False
    returns_policy_detected: bool = False
    stock_status_indicated: bool = False
    review_stars_or_count_detected: bool = False
    cart_page_detected: bool = False
    checkout_page_detected: bool = False
    guest_checkout_supported: bool = False
    payment_methods_detected: List[str] = Field(default_factory=list) # e.g. "Stripe", "PayPal", "Apple Pay", "Cards"
    coupon_field_friction: str = "NONE" # "COLLAPSED_ACCORDION", "EXPANDED_DISTRACTING", "NONE"
    store_friction_score: float = 75.0


class SaasFlowAudit(BaseModel):
    is_saas_or_b2b: bool = False
    demo_booking_flow_present: bool = False
    self_serve_signup_present: bool = False
    lead_qualification_fields: int = 0 # fields on demo/contact form
    qualification_friction_level: str = "LOW" # "LOW" (<=4), "MEDIUM" (5-7), "HIGH" (>7)
    pricing_tiers_detected: int = 0
    has_free_trial_or_freemium: bool = False
    onboarding_progression_indicated: bool = False
    saas_friction_score: float = 80.0


class CommercialConversionIntelligenceResult(BaseModel):
    business_model: str # "ECOMMERCE", "SAAS_B2B", "HYBRID", "CONTENT_LEADGEN"
    ecommerce_audit: EcommerceFlowAudit = Field(default_factory=EcommerceFlowAudit)
    saas_audit: SaasFlowAudit = Field(default_factory=SaasFlowAudit)
    composite_checkout_score: float = 75.0
    critical_friction_points: List[Dict[str, Any]] = Field(default_factory=list)
    remediation_recommendations: List[str] = Field(default_factory=list)


class EcommerceSaasAnalyzer:
    """Evaluates checkout, transaction, and commercial conversion paths."""

    PAYMENT_PATTERNS = {
        "Apple Pay": re.compile(r"apple\s?pay", re.I),
        "Google Pay": re.compile(r"google\s?pay|gpay", re.I),
        "PayPal": re.compile(r"paypal", re.I),
        "Credit Cards / Stripe": re.compile(r"visa|mastercard|amex|stripe", re.I),
        "Klarna / BNPL": re.compile(r"klarna|afterpay|affirm", re.I),
    }

    @classmethod
    def analyze(
        cls,
        pages: List[PageEvidence],
        raw_html_map: Optional[Dict[str, str]] = None,
        business_profile: Optional[Any] = None,
    ) -> CommercialConversionIntelligenceResult:
        raw_html_map = raw_html_map or {}
        combined_text = ""
        combined_html = ""

        # Aggregate evidence across pages
        has_cart = False
        has_checkout = False
        product_pages = 0
        has_variants = False
        has_reviews = False
        has_stock = False
        shipping_found = False
        returns_found = False
        demo_found = False
        signup_found = False
        pricing_tiers = 0
        max_form_inputs = 0
        payment_methods = []

        for p in pages:
            u = (p.url or "").lower()
            html = raw_html_map.get(p.url) or getattr(p, "raw_html", "") or ""
            soup = BeautifulSoup(html, "html.parser") if html else None

            # Detect E-Commerce signals
            if any(k in u for k in ("/cart", "/basket")):
                has_cart = True
            if any(k in u for k in ("/checkout", "/order/pay")):
                has_checkout = True
            if any(k in u for k in ("/product", "/item", "/shop", "/collection")) or (soup and soup.find(class_=re.compile(r"product|pdp", re.I))):
                product_pages += 1

            if soup:
                txt = soup.get_text().lower()
                combined_text += " " + txt

                if soup.find(class_=re.compile(r"variant|swatch|size-select|color-select", re.I)) or soup.find("select", attrs={"name": re.compile(r"size|color|variant", re.I)}):
                    has_variants = True

                if soup.find(class_=re.compile(r"review|rating|star", re.I)) or "customer reviews" in txt:
                    has_reviews = True

                if any(s in txt for s in ("in stock", "out of stock", "only few left", "units left")):
                    has_stock = True

                if any(s in txt for s in ("free shipping", "standard shipping", "delivery policy", "shipping calculated at checkout")):
                    shipping_found = True

                if any(r in txt for r in ("30-day return", "returns policy", "easy return", "money-back guarantee", "refund policy")):
                    returns_found = True

                # Payments
                for method_name, pat in cls.PAYMENT_PATTERNS.items():
                    if pat.search(txt) and method_name not in payment_methods:
                        payment_methods.append(method_name)

                # SaaS signals
                if any(d in txt for d in ("book a demo", "schedule demo", "request demo", "demo booking")):
                    demo_found = True
                if any(s in txt for s in ("start free trial", "sign up free", "create account")):
                    signup_found = True

                tier_blocks = soup.find_all(class_=re.compile(r"pricing-card|plan-card|price-tier|tier", re.I))
                if tier_blocks:
                    pricing_tiers = max(pricing_tiers, len(tier_blocks))

                # Forms
                for f in soup.find_all("form"):
                    inp_count = len(f.find_all(["input", "select", "textarea"]))
                    max_form_inputs = max(max_form_inputs, inp_count)

        # Classify business model
        is_ecom = bool(has_cart or has_checkout or product_pages > 0 or payment_methods)
        is_saas = bool(demo_found or signup_found or pricing_tiers > 0)

        if is_ecom and is_saas:
            b_model = "HYBRID"
        elif is_ecom:
            b_model = "ECOMMERCE"
        elif is_saas:
            b_model = "SAAS_B2B"
        else:
            b_model = "CONTENT_LEADGEN"

        # Evaluate E-Commerce Audit
        ecom_score = 75.0
        if not shipping_found:
            ecom_score -= 10.0
        if not returns_found:
            ecom_score -= 10.0
        if not has_reviews:
            ecom_score -= 10.0
        if not payment_methods:
            ecom_score -= 10.0
        ecom_score = max(35.0, min(95.0, ecom_score))

        # Inspect guest checkout & coupon friction strictly from observed checkout text (never fabricate)
        guest_checkout_obs = bool(
            has_checkout
            and re.search(r"(guest\s+checkout|continue\s+as\s+guest|checkout\s+without\s+account)", combined_text, re.I)
        )
        coupon_state = "NONE"
        if has_checkout:
            if re.search(r"(promo\s+code|coupon\s+code|discount\s+code)", combined_text, re.I):
                coupon_state = "EXPANDED_DISTRACTING"
            else:
                coupon_state = "NONE"

        ecom_audit = EcommerceFlowAudit(
            is_ecommerce_site=is_ecom,
            product_pages_analyzed=product_pages,
            has_product_imagery=product_pages > 0,
            has_product_variants=has_variants,
            price_visibility="PROMINENT" if (product_pages > 0 or "$" in combined_text or "₹" in combined_text) else "NOT_DETECTED",
            shipping_policy_detected=shipping_found,
            returns_policy_detected=returns_found,
            stock_status_indicated=has_stock,
            review_stars_or_count_detected=has_reviews,
            cart_page_detected=has_cart,
            checkout_page_detected=has_checkout,
            guest_checkout_supported=guest_checkout_obs,
            payment_methods_detected=payment_methods,
            coupon_field_friction=coupon_state,
            store_friction_score=ecom_score,
        )

        # Evaluate SaaS Audit
        saas_score = 80.0
        qual_level = "LOW"
        if max_form_inputs > 7:
            qual_level = "HIGH"
            saas_score -= 15.0
        elif max_form_inputs > 4:
            qual_level = "MEDIUM"
            saas_score -= 8.0

        if not pricing_tiers:
            saas_score -= 10.0
        saas_score = max(40.0, min(95.0, saas_score))

        saas_audit = SaasFlowAudit(
            is_saas_or_b2b=is_saas,
            demo_booking_flow_present=demo_found,
            self_serve_signup_present=signup_found,
            lead_qualification_fields=max_form_inputs,
            qualification_friction_level=qual_level,
            pricing_tiers_detected=pricing_tiers,
            has_free_trial_or_freemium="free trial" in combined_text,
            onboarding_progression_indicated=signup_found,
            saas_friction_score=saas_score,
        )

        # Critical friction points & remedies
        critical_friction: List[Dict[str, Any]] = []
        remedies: List[str] = []

        if is_ecom:
            if not shipping_found:
                critical_friction.append({
                    "flow": "ECOMMERCE",
                    "point": "Hidden Shipping Costs",
                    "severity": "HIGH",
                    "detail": "No explicit shipping policy or free-shipping threshold detected prior to checkout.",
                })
                remedies.append("Display upfront shipping terms or threshold banners ('Free shipping over $50') on product pages to eliminate checkout abandonment.")
            if not returns_found:
                critical_friction.append({
                    "flow": "ECOMMERCE",
                    "point": "Missing Returns Policy",
                    "severity": "MEDIUM",
                    "detail": "Absence of clear 30-day money-back or return terms increases buyer hesitation.",
                })
                remedies.append("Add reassuring return policy microcopy near 'Add to Cart' buttons.")

        if is_saas:
            if qual_level == "HIGH":
                critical_friction.append({
                    "flow": "SAAS",
                    "point": "Excessive Lead Qualification Fields",
                    "severity": "HIGH",
                    "detail": f"Demo/signup forms require {max_form_inputs} input fields, suppressing conversion velocity.",
                })
                remedies.append("Reduce initial demo/signup request to 3 core fields (Work Email, Name, Company Size) and enrich remainder asynchronously.")

        composite_score = ecom_score if is_ecom and not is_saas else (saas_score if is_saas and not is_ecom else (ecom_score + saas_score) / 2.0)

        return CommercialConversionIntelligenceResult(
            business_model=b_model,
            ecommerce_audit=ecom_audit,
            saas_audit=saas_audit,
            composite_checkout_score=round(composite_score, 1),
            critical_friction_points=critical_friction,
            remediation_recommendations=remedies,
        )


ecommerce_saas_analyzer = EcommerceSaasAnalyzer()
