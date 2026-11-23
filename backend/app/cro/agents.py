"""
CRO (Conversion Rate Optimization) & UX Specialist Agents.

Upgraded from deterministic stubs to Layer-0 DOM measurements + Frontier AI
behavioral/UX/CTA/trust/form/pricing reasoning over structured PageSections,
while preserving strict `UNKNOWN (Requires GA4)` boundaries for unmeasured analytics.

Consolidates:
1. CroConversionAgent (value proposition, primary CTA visibility, conversion pathways)
2. VisualUxFrictionAgent (visual ergonomics, mobile viewport scaling, layout distraction)
3. FormAbandonmentAgent (input count, required friction, form abandonment triggers)
4. PricingTrustAgent (pricing layout, packaging psychology, guarantee terms, trust badges)
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, VerificationStatus
from app.domain.models import Claim

logger = logging.getLogger("dristik.cro.agents")

_CRO_OUTPUT_SCHEMA = json.dumps(
    {
        "summary": "string",
        "claims": [
            {
                "statement": "string (specific observed CRO/UX issue anchored to real page sections)",
                "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
                "confidence": 0.85,
                "evidence_refs": ["ev_id_from_context"],
                "recommendation": "string (concrete copy/layout/UX fix)",
                "business_impact": "string (directional conversion effect — never invent conversion %)",
            }
        ],
    },
    indent=2,
)

_ANALYTICS_BOUNDARIES = {
    "actual_conversion_rate": "UNKNOWN (Requires GA4 connector)",
    "cta_click_through_rate": "UNKNOWN (Requires GA4 / PostHog events)",
    "form_abandonment_rate": "UNKNOWN (Requires GA4 / CRM funnel tracking)",
}


def _build_cro_section_dossier(pages: List[Any], max_pages: int = 12) -> List[Dict[str, Any]]:
    dossier: List[Dict[str, Any]] = []
    for p in pages[:max_pages]:
        sections_brief = []
        for sec in (getattr(p, "sections", None) or [])[:8]:
            sections_brief.append({
                "section_id": getattr(sec, "section_id", ""),
                "role": getattr(sec, "section_role", ""),
                "heading": (getattr(sec, "heading_text", "") or "")[:120],
                "excerpt": (getattr(sec, "body_text", "") or "")[:360],
                "ctas": (getattr(sec, "ctas", None) or [])[:5],
                "forms_count": len(getattr(sec, "forms", None) or []),
            })
        footer = getattr(p, "footer_info", None) or {}
        dossier.append({
            "url": getattr(p, "url", ""),
            "page_type": getattr(p, "page_type", "general"),
            "title": (getattr(p, "title", "") or "")[:140],
            "h1": (getattr(p, "h1", None) or [])[:3],
            "ctas": (getattr(p, "ctas", None) or [])[:10],
            "forms_count": len(getattr(p, "forms", None) or []),
            "word_count": getattr(p, "word_count", 0),
            "viewport_meta": bool(getattr(p, "viewport_meta", None) or getattr(p, "viewport", None)),
            "footer_trust_links": (footer.get("legal_links") if isinstance(footer, dict) else []) or [],
            "sections": sections_brief,
        })
    return dossier


def _parse_severity(raw: Any) -> Severity:
    val = str(raw or "MEDIUM").strip().upper()
    for s in Severity:
        if s.value == val or s.name == val:
            return s
    return Severity.MEDIUM


async def _run_cro_frontier_reasoning(
    *,
    agent_id: str,
    specialty: str,
    role_title: str,
    focus_instructions: str,
    model_router: Any,
    blackboard: CognitiveBlackboard,
    observations: Dict[str, Any],
    pages: List[Any],
) -> Dict[str, Any]:
    """Run Frontier AI CRO reasoning over structured PageSections + deterministic observations."""
    if not pages:
        return {"ai_status": "unmeasured", "claims": [], "summary": ""}
    if model_router is None or not hasattr(model_router, "generate_structured"):
        return {"ai_status": "unavailable", "claims": [], "summary": ""}

    bp = getattr(blackboard, "business_profile", None)
    biz_summary = (
        f"Business: {getattr(bp, 'business_name', None) or blackboard.website_url} | "
        f"Model: {getattr(bp, 'business_model', None) or 'Unknown'} | "
        f"Industry: {getattr(bp, 'industry', None) or 'Unknown'} | "
        f"Audience: {getattr(bp, 'target_audience', None) or 'Unknown'}"
    )
    dossier = _build_cro_section_dossier(pages)
    store = getattr(blackboard, "evidence_store", None)
    ev_list = []
    if store is not None:
        all_ev = store.get_all()
        preferred = [
            ev for ev in all_ev
            if getattr(ev, "source_type", "") in ("page_section", "form", "footer", "nav", "dom", "html")
        ]
        ev_list = (preferred or all_ev)[:35]
    valid_ev_ids = {ev.id for ev in ev_list if getattr(ev, "id", None)}

    task_contract = (
        f"CRO SPECIALIST: {role_title} ({agent_id})\n"
        f"{biz_summary}\n"
        f"FOCUS: {focus_instructions}\n\n"
        f"DETERMINISTIC LAYER-0 OBSERVATIONS:\n{json.dumps(observations, default=str, indent=2)}\n\n"
        f"STRUCTURED PAGE SECTIONS & CTA/FORM DOSSIER:\n{json.dumps(dossier, default=str, indent=2)[:7000]}\n\n"
        "EPISTEMIC RULES:\n"
        "1. Anchor every claim to observed DOM sections, CTAs, forms, or copy above and cite exact evidence_refs.\n"
        "2. NEVER invent conversion rates, bounce rates, abandonment percentages, or revenue lift figures. "
        "Analytics metrics are UNKNOWN (Requires GA4) unless explicitly measured in evidence.\n"
        "3. Provide concrete, page-specific conversion fixes tied to real URLs and sections."
    )

    try:
        raw = await model_router.generate_structured(
            capability="cro_analysis",
            agent_role=role_title,
            task_contract=task_contract,
            evidence_list=ev_list,
            output_schema_desc=_CRO_OUTPUT_SCHEMA,
            site_facts=getattr(blackboard, "site_facts", None),
            max_claims=6,
            allow_fallback=False,
            model_tier="reasoning_model",
        )
    except Exception as exc:
        logger.warning("CRO Frontier AI reasoning failed for %s: %s", agent_id, exc)
        return {"ai_status": "unavailable", "claims": [], "summary": ""}

    if not isinstance(raw, dict) or str(raw.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
        return {"ai_status": "unavailable", "claims": [], "summary": ""}

    registered_statements: List[str] = []
    fallback_ref = next(iter(valid_ev_ids), None)
    for item in (raw.get("claims") or [])[:6]:
        if not isinstance(item, dict):
            continue
        stmt = str(item.get("statement") or "").strip()
        if len(stmt) < 12:
            continue
        refs = [str(r) for r in (item.get("evidence_refs") or []) if str(r) in valid_ev_ids]
        if not refs and fallback_ref:
            refs = [fallback_ref]
        if not refs:
            continue
        biz_impact = str(item.get("business_impact") or "").strip()
        rec_text = str(item.get("recommendation") or "").strip()
        if biz_impact and biz_impact not in rec_text:
            rec_text = f"{rec_text} (Business impact: {biz_impact})".strip() if rec_text else f"Business impact: {biz_impact}"
        claim_obj = Claim(
            id=f"clm_cro_{uuid.uuid4().hex[:10]}",
            agent_id=agent_id,
            category=Category.UX_CONVERSION,
            severity=_parse_severity(item.get("severity")),
            statement=stmt,
            evidence_refs=refs,
            confidence=max(0.4, min(0.95, float(item.get("confidence") or 0.80))),
            recommendation=rec_text or None,
            verification_status=VerificationStatus.PENDING_VERIFICATION,
        )
        if getattr(blackboard, "claim_registry", None) is not None:
            blackboard.claim_registry.add_claim(claim_obj)
        registered_statements.append(stmt)

    return {
        "ai_status": "completed",
        "claims": registered_statements,
        "summary": str(raw.get("summary") or "").strip(),
    }


class CroConversionAgent(BaseAgent):
    """Audits conversion funnel efficiency, CTA prominence, and above-the-fold value proposition."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.conversion.v3",
            capability="cro_analysis",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        all_ctas = [cta for p in pages for cta in (getattr(p, "ctas", None) or [])]
        hero_sections = [
            sec for p in pages for sec in (getattr(p, "sections", None) or [])
            if getattr(sec, "section_role", "") == "hero"
        ]
        has_primary_cta = bool(all_ctas) or any(
            any("get" in h.lower() or "start" in h.lower() or "book" in h.lower() or "buy" in h.lower() for h in (p.h1 or []))
            for p in pages
        )

        observations: Dict[str, Any] = {
            "funnel_pages_count": len(pages),
            "hero_sections_analyzed": len(hero_sections),
            "observed_ctas_count": len(all_ctas),
            "sample_ctas": all_ctas[:10],
            "primary_cta_detected": has_primary_cta,
            "requires_analytics": _ANALYTICS_BOUNDARIES,
        }

        ai_res = await _run_cro_frontier_reasoning(
            agent_id=self.agent_id,
            specialty="conversion_pathways",
            role_title="Principal CRO & Above-the-Fold Conversion Strategist",
            focus_instructions=(
                "Evaluate hero value proposition clarity (5-second comprehension), primary vs secondary CTA hierarchy, "
                "message match across landing/product/pricing sections, and conversion path friction."
            ),
            model_router=self.model_router,
            blackboard=blackboard,
            observations=observations,
            pages=pages,
        )
        observations["ai_summary"] = ai_res["summary"]
        observations["ai_status"] = ai_res["ai_status"]

        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "conversion_pathways",
            "status": "completed" if pages else "UNMEASURED",
            "observations": observations,
            "claims": ai_res["claims"],
        }


class VisualUxFrictionAgent(BaseAgent):
    """Audits visual ergonomics, viewport scaling, scannability, and interactive friction."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.visual_ux.v3",
            capability="cro_analysis",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        viewport_pages = sum(
            1 for p in pages if bool(getattr(p, "viewport_meta", None) or getattr(p, "viewport", None))
        )
        render_failures = sum(
            1 for p in pages if getattr(p, "render_status", None) in ("failed", "timeout")
        )
        total_sections = sum(len(getattr(p, "sections", None) or []) for p in pages)
        observations: Dict[str, Any] = {
            "pages_audited": len(pages),
            "mobile_viewport_configured": (viewport_pages > 0) if pages else None,
            "pages_with_viewport": viewport_pages,
            "ux_friction_points_count": 0 if viewport_pages > 0 else (1 if pages else 0),
            "js_render_failures": render_failures,
            "structured_sections_audited": total_sections,
            "requires_analytics": _ANALYTICS_BOUNDARIES,
        }

        ai_res = await _run_cro_frontier_reasoning(
            agent_id=self.agent_id,
            specialty="visual_ux_friction",
            role_title="Senior UX Ergonomics & Information Architecture Auditor",
            focus_instructions=(
                "Audit page structure scannability, section hierarchy, cognitive load, navigation clarity, "
                "mobile ergonomics, and layout friction from the observed DOM sections and viewport metadata."
            ),
            model_router=self.model_router,
            blackboard=blackboard,
            observations=observations,
            pages=pages,
        )
        observations["ai_summary"] = ai_res["summary"]
        observations["ai_status"] = ai_res["ai_status"]

        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "visual_ux_friction",
            "status": "completed" if pages else "UNMEASURED",
            "observations": observations,
            "claims": ai_res["claims"],
        }


class FormAbandonmentAgent(BaseAgent):
    """Audits input count, required vs optional friction, and form abandonment triggers via real DOM + Frontier AI."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.form_friction.v3",
            capability="cro_analysis",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        from app.cro.form_analyzer import FormAccessibilityAnalyzer
        pages = getattr(blackboard, "pages", []) or []
        report = FormAccessibilityAnalyzer.analyze_forms(pages)
        total_forms = report.total_forms_detected
        avg_fields = (
            round(sum(f.input_count for f in report.forms) / total_forms, 1)
            if total_forms > 0
            else None
        )
        friction_rating = (
            "NOT_MEASURED"
            if total_forms == 0
            else ("HIGH" if report.friction_score >= 60 else ("MEDIUM" if report.friction_score >= 30 else "LOW"))
        )
        observations: Dict[str, Any] = {
            "detected_forms": total_forms,
            "average_field_count": avg_fields,
            "forms_with_missing_labels": report.forms_with_missing_labels,
            "form_friction_score": report.friction_score if total_forms > 0 else None,
            "form_friction_rating": friction_rating,
            "requires_analytics": _ANALYTICS_BOUNDARIES,
        }

        ai_res = await _run_cro_frontier_reasoning(
            agent_id=self.agent_id,
            specialty="form_abandonment",
            role_title="Lead Form Ergonomics & Lead-Capture Conversion Specialist",
            focus_instructions=(
                "Analyze lead/checkout/contact form friction, field count, missing labels, submit CTA clarity, "
                "and privacy reassurance next to forms. If zero forms are observed, assess whether the site relies "
                "on external booking/checkout or misses on-page lead capture."
            ),
            model_router=self.model_router,
            blackboard=blackboard,
            observations=observations,
            pages=pages,
        )
        observations["ai_summary"] = ai_res["summary"]
        observations["ai_status"] = ai_res["ai_status"]

        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "form_abandonment",
            "status": "completed" if (total_forms > 0 or ai_res["ai_status"] == "completed") else "UNMEASURED",
            "observations": observations,
            "claims": ai_res["claims"],
        }


class PricingTrustAgent(BaseAgent):
    """Audits pricing layout, packaging psychology, guarantee terms, and institutional trust signals."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.pricing_trust.v3",
            capability="cro_analysis",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        has_pricing = any(
            "pricing" in (p.url or "").lower()
            or "pricing" in (p.title or "").lower()
            or any(getattr(s, "section_role", "") == "pricing" for s in (getattr(p, "sections", None) or []))
            for p in pages
        )
        trust_markers = [
            "iso 27001", "soc 2", "gdpr", "hipaa", "pci dss", "guarantee",
            "money-back", "warranty", "ssl", "certified", "verified reviews", "testimonial",
        ]
        matched_trust = sorted({
            k for p in pages
            for k in trust_markers
            if k in (getattr(p, "body_text", "") or "").lower()
        })
        observations: Dict[str, Any] = {
            "trust_badges_detected": bool(matched_trust),
            "observed_trust_markers": matched_trust,
            "pricing_transparency": "TRANSPARENT" if has_pricing else "UNOBSERVED",
            "pricing_page_detected": has_pricing,
            "requires_analytics": _ANALYTICS_BOUNDARIES,
        }

        ai_res = await _run_cro_frontier_reasoning(
            agent_id=self.agent_id,
            specialty="pricing_trust",
            role_title="Senior Pricing Psychology & Buyer Trust Auditor",
            focus_instructions=(
                "Evaluate pricing transparency, tier/plan comparison clarity, risk-reversal terms (guarantees, "
                "returns, cancellation), and placement of social proof / credentials near conversion points, "
                "adapted strictly to this site's actual business model (B2B vs D2C vs local service)."
            ),
            model_router=self.model_router,
            blackboard=blackboard,
            observations=observations,
            pages=pages,
        )
        observations["ai_summary"] = ai_res["summary"]
        observations["ai_status"] = ai_res["ai_status"]

        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "pricing_trust",
            "status": "completed" if pages else "UNMEASURED",
            "observations": observations,
            "claims": ai_res["claims"],
        }


__all__ = [
    "CroConversionAgent",
    "VisualUxFrictionAgent",
    "FormAbandonmentAgent",
    "PricingTrustAgent",
]
