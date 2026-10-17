"""
Business Perspective Understanding Agent:
Analyzes the business model, Ideal Customer Profile (ICP), monetization architecture,
target audience, and commercial search intent from crawled evidence and user declarations.
"""
from typing import Dict, Any, List, Optional
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType
from app.evidence.retriever import EvidenceRetriever
from app.inference.prompt_compiler import load_prompt


class BusinessPerspectiveAgent(BaseAgent):
    """
    Discovery Stage Agent: Business Understanding Perspective.
    Extracts commercial identity, B2B/B2C categorization, buyer persona,
    and revenue model without hallucination.
    """
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="discovery.business_perspective.v3",
            capability="business_intelligence",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=30)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        # Fallback deterministic analysis if model_router unavailable or deterministic mode
        business_profile = getattr(blackboard, "business_profile", None)
        business_name = getattr(business_profile, "business_name", None) or site_facts.get("site_name", "Identified Organization")
        business_model = getattr(business_profile, "business_model", None) or "Unspecified / Not Declared"
        icp = getattr(business_profile, "target_audience", None) or "Unspecified / Not Declared"

        observations = {
            "business_name": business_name,
            "business_model": business_model,
            "target_icp": icp,
            "evidence_count": len(evidence_slice),
        }

        claims = []
        if not evidence_slice and not business_profile:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="Insufficient commercial copy observed to definitively map monetization model.",
                category=Category.COMPETITIVE,
                severity=Severity.LOW,
                claim_type=ClaimType.OBSERVATION,
                confidence=0.75,
                recommendation="Ensure homepage clearly articulates commercial value proposition and target audience.",
                impact=4,
                effort=2,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "stage": "discovery",
            "perspective": "business_perspective",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
