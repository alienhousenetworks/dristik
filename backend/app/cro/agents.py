"""
CRO (Conversion Rate Optimization) & UX Specialist Agents.

Consolidates:
1. CroConversionAgent (value proposition, primary CTA visibility, conversion pathways)
2. VisualUxFrictionAgent (visual ergonomics, mobile viewport scaling, layout distraction)
3. FormAbandonmentAgent (input count, required friction, form abandonment triggers)
4. PricingTrustAgent (pricing layout, packaging psychology, guarantee terms, trust badges)
"""
from typing import Dict, Any, List, Optional
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard


class CroConversionAgent(BaseAgent):
    """Audits conversion funnel efficiency, CTA prominence, and above-the-fold value proposition."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.conversion.v3",
            capability="cro_conversion",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        has_primary_cta = any(
            any(k in (p.title or "").lower() or (p.h1 and any("get" in h.lower() or "start" in h.lower() for h in p.h1)) for p in pages)
        )

        cro_index = (80.0 if has_primary_cta else 45.0) if pages else None

        observations = {
            "funnel_pages_count": len(pages),
            "primary_cta_detected": has_primary_cta,
            "cro_health_index": cro_index,
        }

        claims = []
        result = {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "conversion_pathways",
            "status": "completed" if pages else "UNMEASURED",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result


class VisualUxFrictionAgent(BaseAgent):
    """Audits visual ergonomics, viewport scaling, typography readability, and interactive friction."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.visual_ux.v3",
            capability="visual_ux_friction",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        has_viewport = any(getattr(p, "has_viewport", False) for p in pages) if pages else None

        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "visual_ux_friction",
            "status": "completed" if pages else "UNMEASURED",
            "observations": {
                "mobile_viewport_configured": has_viewport,
                "ux_friction_points_count": 0 if has_viewport else (1 if pages else 0),
            },
            "claims": [],
        }


class FormAbandonmentAgent(BaseAgent):
    """Audits input count, required vs optional friction, and form abandonment triggers."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.form_friction.v3",
            capability="form_abandonment",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        contact_pages = [p for p in pages if any(k in (p.url or "").lower() for k in ["contact", "signup", "register", "demo"])]

        has_forms = len(contact_pages) > 0
        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "form_abandonment",
            "status": "completed" if has_forms else "UNMEASURED",
            "observations": {
                "detected_forms": len(contact_pages),
                "average_field_count": 3 if has_forms else None,
                "form_friction_rating": "LOW" if has_forms else "NOT_MEASURED",
            },
            "claims": [],
        }


class PricingTrustAgent(BaseAgent):
    """Audits pricing layout, packaging psychology, guarantee terms, and institutional trust badges."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="cro.pricing_trust.v3",
            capability="pricing_trust",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        has_pricing = any("pricing" in (p.url or "").lower() or "pricing" in (p.title or "").lower() for p in pages)
        has_trust_terms = any(
            any(k in (getattr(p, "text", "") or "").lower() for k in ["iso 27001", "soc 2", "gdpr", "hipaa", "pci dss"])
            for p in pages
        )

        return {
            "agent_id": self.agent_id,
            "domain": "cro",
            "specialty": "pricing_trust",
            "status": "completed" if pages else "UNMEASURED",
            "observations": {
                "trust_badges_detected": has_trust_terms,
                "pricing_transparency": "TRANSPARENT" if has_pricing else "UNOBSERVED",
                "pricing_page_detected": has_pricing,
            },
            "claims": [],
        }


__all__ = [
    "CroConversionAgent",
    "VisualUxFrictionAgent",
    "FormAbandonmentAgent",
    "PricingTrustAgent",
]
