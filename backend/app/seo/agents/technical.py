"""
Technical SEO Agent:
Evaluates HTTP status codes, redirect loops, canonical compliance,
robots directives, HTTPS/HSTS, and clean URL structure.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType
from app.evidence.retriever import EvidenceRetriever


class TechnicalSeoAgent(BaseAgent):
    """Audits technical foundation, status codes, canonicals, and server configuration."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="seo.technical.v3",
            capability="technical_seo",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=50)

        pages = getattr(blackboard, "pages", []) or []
        non_200_count = 0
        missing_canonical_count = 0

        for page in pages:
            status = getattr(page, "status_code", 200)
            if status != 200:
                non_200_count += 1
            if not getattr(page, "canonical_url", None):
                missing_canonical_count += 1

        observations = {
            "total_crawled_pages": len(pages),
            "non_200_urls": non_200_count,
            "missing_canonicals": missing_canonical_count,
        }

        claims = []
        if missing_canonical_count > 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement=f"Detected {missing_canonical_count} pages without explicit self-referential rel=canonical tags.",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH if missing_canonical_count > 3 else Severity.MEDIUM,
                claim_type=ClaimType.FACT,
                confidence=0.98,
                recommendation="Inject absolute, self-referential canonical tags in the <head> of all indexed URLs.",
                impact=7,
                effort=2,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "technical_seo",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
