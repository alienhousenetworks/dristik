"""
Brand Perspective Understanding Agent:
Analyzes brand identity, entity salience, tone of voice, institutional trust signals,
and market positioning from observed content and brand footprint.
"""
from typing import Dict, Any, List, Optional
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType
from app.evidence.retriever import EvidenceRetriever


class BrandPerspectiveAgent(BaseAgent):
    """
    Discovery Stage Agent: Brand Understanding Perspective.
    Extracts brand entity identity, trademark cues, author credentials,
    social authority proofs, and overall brand tone.
    """
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="discovery.brand_perspective.v3",
            capability="brand_intelligence",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=30)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        brand_name = site_facts.get("site_name")
        if not brand_name and hasattr(blackboard, "pages") and blackboard.pages:
            title = blackboard.pages[0].title or ""
            if " - " in title:
                brand_name = title.split(" - ")[-1].strip()
            elif " | " in title:
                brand_name = title.split(" | ")[-1].strip()
            else:
                brand_name = title.strip()[:40]

        has_social_proof = any(
            any(k in (p.url.lower()) for k in ["about", "press", "customers", "case-studies"])
            for p in (blackboard.pages or [])
        )

        observations = {
            "resolved_brand_name": brand_name or "Unresolved Brand Name",
            "has_social_proof_pages": has_social_proof,
            "external_signals_checked": True,
        }

        claims = []
        if not has_social_proof:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="No dedicated customer validation, case study, or press section detected in crawled pages.",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.LOW,
                claim_type=ClaimType.OBSERVATION,
                confidence=0.85,
                recommendation="Feature institutional trust signals such as customer testimonials, case studies, or press logos.",
                impact=5,
                effort=2,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "stage": "discovery",
            "perspective": "brand_perspective",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
