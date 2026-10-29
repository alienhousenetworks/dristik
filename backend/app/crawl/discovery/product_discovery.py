"""
Product Perspective Understanding Agent:
Analyzes the core product/service offerings, feature catalog, solution hierarchy,
and primary product value propositions from observed content and navigation headers.
"""
from typing import Dict, Any, List, Optional
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType
from app.evidence.retriever import EvidenceRetriever


class ProductPerspectiveAgent(BaseAgent):
    """
    Discovery Stage Agent: Product Understanding Perspective.
    Extracts core solutions, product feature capabilities, pricing tiers,
    and technological or service deliverables.
    """
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="discovery.product_perspective.v3",
            capability="product_intelligence",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=30)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        # Scan pages for product offerings and primary nav cues
        offerings: List[str] = []
        if hasattr(blackboard, "pages") and blackboard.pages:
            for page in blackboard.pages[:10]:
                for h in (page.h1 or []):
                    if len(h.strip()) > 3 and h not in offerings:
                        offerings.append(h.strip())

        observations = {
            "identified_offerings_count": len(offerings),
            "primary_offerings_sample": offerings[:5],
            "has_pricing_page": any("/pricing" in p.url.lower() for p in (blackboard.pages or [])),
        }

        claims = []
        if not observations["has_pricing_page"]:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="No dedicated public pricing or packaging page was detected in the crawled topology.",
                category=Category.COMPETITIVE,
                severity=Severity.LOW,
                claim_type=ClaimType.OBSERVATION,
                confidence=0.80,
                recommendation="If product operates on self-service or transparent tiers, publish a transparent pricing or plan matrix.",
                impact=5,
                effort=3,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "stage": "discovery",
            "perspective": "product_perspective",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
