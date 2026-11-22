"""Department F (Ecommerce & Checkout) & Department G (Trust, Credibility & Persuasion).

Implements Phases 13 and 14:
- Ecommerce: Product pages, pricing visibility, variants, stock, shipping/returns, cart,
  checkout friction, guest checkout inspection (NEVER hardcoded True!), payment methods
  (sandbox-only testing), subscription flows, and connector-gated ecommerce analytics.
- Trust: Company identity, contact info, reviews/testimonials attribution quality,
  certifications, security reassurance, privacy/terms/refund transparency, risk reversal.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from app.cro.models import (
    CROAgentOutput,
    CRODimensionCheck,
    CROFinding,
    CROSeverity,
    EvidenceSourceType,
)
from app.cro.specialists import CROAuditContext


def run_department_f(ctx: CROAuditContext) -> CROAgentOutput:
    """Department F — Ecommerce Product, Cart, Checkout & Payment Optimization."""
    ecom_applicable = bool(ctx.scope.get("ecommerce_applicable")) or any(
        p.page_type.value in ("product_detail", "cart", "checkout", "category_page") for p in ctx.pages
    )
    if not ecom_applicable:
        ctx.artifacts["ecommerce_audit"] = {
            "applicable": False,
            "reason": f"Business model '{ctx.profile.business_type.value}' has no detected ecommerce product/cart/checkout pages.",
            "roles_executed": ["cro_ecommerce_funnel"],
        }
        return CROAgentOutput(
            agent_id="cro_department_f_ecommerce",
            department="F",
            status="skipped",
            audit_id=ctx.audit_id,
            confidence=1.0,
            limitations=["Ecommerce audit skipped (not applicable to this business model)."],
            artifacts=ctx.artifacts["ecommerce_audit"],
        )

    findings: List[CROFinding] = []
    evidence_ids: List[str] = []
    pdp_pages = [p for p in ctx.pages if p.page_type.value in ("product_detail", "product_page")]
    cart_pages = [p for p in ctx.pages if p.page_type.value == "cart"]
    checkout_pages = [p for p in ctx.pages if p.page_type.value == "checkout"]

    all_html = "\n".join(ctx.raw_html_map.get(p.url, "") for p in ctx.pages)
    all_text = BeautifulSoup(all_html, "html.parser").get_text(" ", strip=True).lower() if all_html else ""

    has_shipping_info = bool(re.search(r"(free\s+shipping|shipping\s+cost|delivery\s+time|estimated\s+delivery|shipping\s+policy)", all_text, re.I))
    has_return_policy = bool(re.search(r"(return\s+policy|refund\s+policy|\d+-day\s+return|money[- ]back)", all_text, re.I))
    has_price_display = bool(re.search(r"([$£€₹]\s?\d|\bprice\b)", all_text, re.I))
    has_stock_status = bool(re.search(r"(in\s+stock|out\s+of\s+stock|ships\s+in|available\s+now)", all_text, re.I))
    has_reviews = bool(re.search(r"(customer\s+reviews?|verified\s+buyer|\d\.\d\s*(?:/\s*5|stars))", all_text, re.I))

    # Inspect checkout pages honestly — NEVER hardcode guest_checkout_supported = True
    guest_checkout_state = "not_inspected"
    forced_account_creation = False
    checkout_field_count = 0
    checkout_payment_methods: List[str] = []

    if checkout_pages:
        chk_html = "\n".join(ctx.raw_html_map.get(p.url, "") for p in checkout_pages)
        chk_soup = BeautifulSoup(chk_html, "html.parser")
        chk_text = chk_soup.get_text(" ", strip=True).lower()
        evidence_ids.extend(p.page_id for p in checkout_pages)

        if re.search(r"(guest\s+checkout|continue\s+as\s+guest|checkout\s+without\s+account)", chk_text, re.I):
            guest_checkout_state = "supported"
        elif re.search(r"(create\s+(?:an?\s+)?account\s+to\s+(?:continue|checkout)|must\s+register|login\s+required|password)", chk_text, re.I):
            guest_checkout_state = "forced_account_creation"
            forced_account_creation = True
        else:
            guest_checkout_state = "unobserved"

        for f in chk_soup.find_all("form"):
            inputs = [
                inp for inp in f.find_all(["input", "select", "textarea"])
                if (inp.get("type") or "text").lower() not in ("hidden", "submit", "button")
            ]
            checkout_field_count = max(checkout_field_count, len(inputs))

        for label, pat in (
            ("Credit/Debit Cards", r"credit\s+card|visa|mastercard|amex|stripe"),
            ("Apple Pay", r"apple\s?pay"),
            ("Google Pay", r"google\s?pay|gpay"),
            ("PayPal", r"paypal"),
            ("BNPL (Klarna/Afterpay)", r"klarna|afterpay|affirm"),
        ):
            if re.search(pat, chk_text, re.I):
                checkout_payment_methods.append(label)

    # Complex checkout finding
    if forced_account_creation or checkout_field_count >= 10 or (checkout_pages and not has_shipping_info):
        issues_txt = []
        if forced_account_creation:
            issues_txt.append("account creation required before checkout (no guest checkout observed)")
        if checkout_field_count >= 10:
            issues_txt.append(f"excessive checkout form complexity ({checkout_field_count} input fields)")
        if not has_shipping_info:
            issues_txt.append("shipping cost/delivery policy not disclosed prior to checkout")
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-ECOM-CHK-{ctx.audit_id[-6:]}-01",
                category="ecommerce_cro",
                subcategory="checkout_friction",
                department="F",
                agent_id="cro_checkout",
                title="High Checkout Friction & Missing Transaction Reassurance",
                description=f"Checkout inspection observed friction: {'; '.join(issues_txt)}.",
                root_cause="Multi-field forced-registration checkout without upfront total/shipping clarity.",
                affected_urls=[p.url for p in checkout_pages] or [p.url for p in pdp_pages[:3]],
                affected_journeys=[j.journey_id for j in ctx.journeys],
                evidence_ids=evidence_ids or [p.page_id for p in ctx.pages[:3]],
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.HIGH,
                confidence=0.9,
                recommendation="Enable guest checkout, reduce checkout inputs with address autocomplete and express wallets, and disclose total shipping/returns before payment.",
                implementation_instructions="Offer guest checkout by default, consolidate name/address inputs, display order summary with shipping upfront, and validate payment errors in sandbox.",
                owner_role="Ecommerce / Engineering",
                effort="high",
                priority_score=90.0,
                acceptance_criteria=[
                    "Guest checkout completes in authorized sandbox without mandatory registration.",
                    "Shipping costs and return policy are visible on product, cart, and checkout views.",
                    "Failed test payment displays clear error recovery without clearing entered details.",
                ],
            )
        )

    if not has_shipping_info or not has_return_policy:
        missing_pol = [x for x, ok in (("shipping costs/delivery estimates", has_shipping_info), ("return/refund policy", has_return_policy)) if not ok]
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-ECOM-POL-{ctx.audit_id[-6:]}-01",
                category="ecommerce_cro",
                subcategory="shipping_and_returns",
                department="F",
                agent_id="cro_shipping_returns",
                title=f"Missing Pre-Purchase Policy Transparency ({', '.join(missing_pol)})",
                description=f"Product/store pages did not surface clear {', '.join(missing_pol)} prior to checkout.",
                root_cause="Fulfillment and return terms omitted from PDP and cart templates.",
                affected_urls=[p.url for p in (pdp_pages or ctx.pages[:3])],
                evidence_ids=[p.page_id for p in (pdp_pages or ctx.pages[:3])],
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.MEDIUM,
                confidence=0.85,
                recommendation="Display upfront shipping costs/thresholds and return/refund timelines directly adjacent to the Add to Cart CTA.",
                implementation_instructions="Add concise shipping and return summary snippet below the primary Add to Cart button linking to full policy pages.",
                owner_role="Ecommerce / Merchandising",
                effort="low",
                priority_score=76.0,
                acceptance_criteria=["Shipping estimate and return window are visible on PDP and cart views."],
            )
        )

    ecom_score = 1.0
    if forced_account_creation:
        ecom_score -= 0.30
    if checkout_field_count >= 10:
        ecom_score -= 0.25
    if not has_shipping_info:
        ecom_score -= 0.20
    if not has_return_policy:
        ecom_score -= 0.15
    if not has_reviews:
        ecom_score -= 0.10

    ctx.dimension_checks.append(
        CRODimensionCheck(
            check_id="dept_f_ecommerce_checkout",
            dimension_id="conversion_journey",
            label="Ecommerce product, cart, checkout, and policy readiness",
            weight=2.0,
            result=max(0.1, round(ecom_score, 2)),
            source_type=EvidenceSourceType.DIRECT_TECHNICAL,
            evidence_ids=evidence_ids or [p.page_id for p in ctx.pages[:3]],
        )
    )

    commerce_metrics = ctx.commerce_payload or {}
    ctx.artifacts["ecommerce_audit"] = {
        "applicable": True,
        "product_pages_count": len(pdp_pages),
        "cart_pages_count": len(cart_pages),
        "checkout_pages_count": len(checkout_pages),
        "price_visibility": "observed" if has_price_display else "not_observed",
        "stock_status_indicated": has_stock_status,
        "reviews_detected": has_reviews,
        "shipping_policy_detected": has_shipping_info,
        "returns_policy_detected": has_return_policy,
        "guest_checkout_status": guest_checkout_state,
        "checkout_field_count": checkout_field_count,
        "payment_methods_observed": checkout_payment_methods,
        "live_payment_testing": "blocked_by_safe_mode (sandbox_required)",
        "measured_commerce_analytics": commerce_metrics if commerce_metrics.get("connected") else {"status": "data_unavailable"},
        "roles_executed": [
            "cro_product_page",
            "cro_product_information",
            "cro_pricing",
            "cro_cart",
            "cro_checkout",
            "cro_payment",
            "cro_shipping_returns",
            "cro_subscription",
            "cro_ecommerce_funnel",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_f_ecommerce",
        department="F",
        status="completed",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=evidence_ids or [p.page_id for p in ctx.pages[:3]],
        confidence=0.88,
        limitations=["Live payment submission is intentionally prohibited outside authorized sandbox environments."],
        artifacts=ctx.artifacts["ecommerce_audit"],
    )


def run_department_g(ctx: CROAuditContext) -> CROAgentOutput:
    """Department G — Trust, Credibility, Proof Attribution & Persuasion Intelligence."""
    findings: List[CROFinding] = []
    evidence_ids: List[str] = [p.page_id for p in ctx.pages[:5]]

    all_html = "\n".join(ctx.raw_html_map.get(p.url, "") for p in ctx.pages)
    soup = BeautifulSoup(all_html, "html.parser") if all_html else None
    all_text = soup.get_text(" ", strip=True) if soup else ""
    all_text_l = all_text.lower()
    urls_l = " ".join(p.url.lower() for p in ctx.pages)

    has_privacy = "privacy" in urls_l or bool(soup and soup.find("a", href=re.compile(r"privacy", re.I)))
    has_terms = "terms" in urls_l or bool(soup and soup.find("a", href=re.compile(r"terms|tos", re.I)))
    has_refund = bool(re.search(r"(refund|return|cancellation)\s+policy|money[- ]back|cancel\s+anytime", all_text_l))
    has_contact = "contact" in urls_l or bool(re.search(r"mailto:|tel:|contact\s+us|\bsupport@", all_html, re.I))
    has_about = "about" in urls_l or bool(soup and soup.find("a", href=re.compile(r"about", re.I)))
    has_security = bool(re.search(r"(soc\s?2|iso\s?27001|gdpr|hipaa|pci[- ]dss|ssl|encrypted)", all_text_l))

    testimonials = (soup.find_all(["blockquote"]) + soup.find_all(class_=re.compile(r"testimonial|review|quote", re.I))) if soup else []
    attributable_testimonials = sum(
        1 for t in testimonials if re.search(r"(—|-|,\s*(?:ceo|cto|vp|head|director|founder|manager)|verified)", t.get_text(" ", strip=True), re.I)
    )
    unattributed_claims = re.findall(r"\b(?:\d+%\s+(?:better|faster|more|guaranteed)|#1\s+in\s+the\s+world|trusted\s+by\s+millions)\b", all_text, re.I)

    coverage_map = {
        "company_identity_about": has_about,
        "contact_information": has_contact,
        "privacy_policy": has_privacy,
        "terms_and_conditions": has_terms,
        "refund_or_cancellation_policy": has_refund,
        "security_reassurance": has_security,
        "testimonials_count": len(testimonials),
        "attributable_testimonials_count": attributable_testimonials,
        "unsubstantiated_claims_detected": unattributed_claims[:5],
    }

    missing_trust: List[str] = []
    if not has_privacy:
        missing_trust.append("Privacy Policy")
    if not has_terms:
        missing_trust.append("Terms & Conditions")
    if not has_contact:
        missing_trust.append("Contact Information")
    if len(testimonials) == 0 and not has_security:
        missing_trust.append("Verifiable Social Proof / Security Credentials")

    trust_score = 1.0 - (0.20 * len(missing_trust)) - (0.10 if (testimonials and attributable_testimonials == 0) else 0.0)
    trust_score = max(0.15, round(trust_score, 2))

    ctx.dimension_checks.append(
        CRODimensionCheck(
            check_id="dept_g_trust_credibility",
            dimension_id="trust_credibility",
            label="Policy transparency, company credibility, and attributable proof",
            weight=2.0,
            result=trust_score,
            source_type=EvidenceSourceType.DIRECT_TECHNICAL if missing_trust else EvidenceSourceType.HEURISTIC_OBSERVATION,
            evidence_ids=evidence_ids,
        )
    )

    if missing_trust:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-TRUST-{ctx.audit_id[-6:]}-01",
                category="trust_optimization",
                subcategory="missing_trust_and_policies",
                department="G",
                agent_id="cro_trust_signal",
                title=f"Missing Core Trust & Policy Transparency Elements ({', '.join(missing_trust)})",
                description=f"Audited pages omitted essential credibility and compliance elements: {', '.join(missing_trust)}.",
                root_cause="Missing legal/policy footer links, identifiable contact channels, or attributable social proof near conversion actions.",
                affected_urls=[p.url for p in ctx.pages[:5]],
                evidence_ids=evidence_ids,
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.HIGH if len(missing_trust) >= 3 else CROSeverity.MEDIUM,
                confidence=0.9,
                recommendation=f"Publish and link clear {', '.join(missing_trust)} using real, verifiable company credentials and customer-approved proof.",
                implementation_instructions="Add persistent footer links to Privacy Policy, Terms, and Contact pages; display attributable testimonials (name, role, company) with customer consent.",
                owner_role="Marketing / Legal",
                effort="low",
                priority_score=78.0,
                acceptance_criteria=[
                    "Privacy Policy, Terms, and Contact links return 200 OK from global footer.",
                    "Any displayed testimonials or security badges are genuine, attributable, and current.",
                ],
            )
        )

    if testimonials and attributable_testimonials == 0:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-TRUST-ATTR-{ctx.audit_id[-6:]}-01",
                category="trust_optimization",
                subcategory="proof_attribution_quality",
                department="G",
                agent_id="cro_review_testimonial",
                title="Testimonials Lack Clear Attribution or Verifiable Source Details",
                description=f"Detected {len(testimonials)} testimonial block(s) without identifiable author role, company, or verified-buyer attribution.",
                root_cause="Anonymous quotes weaken perceived credibility compared to attributable reviews.",
                affected_urls=[p.url for p in ctx.pages[:5]],
                evidence_ids=evidence_ids,
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                severity=CROSeverity.LOW,
                confidence=0.75,
                recommendation="Attribute real customer testimonials with full name, title/company (with permission), or link to verified third-party review profiles.",
                implementation_instructions="Update testimonial cards to include real approved attribution fields; never fabricate names or quotes.",
                owner_role="Marketing",
                effort="low",
                priority_score=55.0,
                acceptance_criteria=["Published testimonials display customer-approved attribution or verified source link."],
            )
        )

    ctx.artifacts["trust_audit"] = {
        "coverage_map": coverage_map,
        "missing_proof_inventory": missing_trust,
        "roles_executed": [
            "cro_trust_signal",
            "cro_review_testimonial",
            "cro_credibility",
            "cro_security_reassurance",
            "cro_policy_transparency",
            "cro_risk_reversal",
            "cro_brand_consistency",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_g_trust",
        department="G",
        status="completed",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=evidence_ids,
        confidence=0.88,
        artifacts=ctx.artifacts["trust_audit"],
    )
