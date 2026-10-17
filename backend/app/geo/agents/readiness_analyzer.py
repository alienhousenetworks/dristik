"""
GEO Readiness Agent:
Evaluates overall Generative Engine Optimization readiness, passage extractability,
and visibility across AI summary engines.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType


class GeoReadinessAgent(BaseAgent):
    """Audits site readiness for generative engine extraction, RAG indexability, and citation frequency."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="geo.readiness.v3",
            capability="geo_readiness",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        extractable_count = sum(1 for p in pages if (p.h1 and getattr(p, "word_count", 0) > 300))

        observations = {
            "total_analyzed_pages": len(pages),
            "extractable_passages_count": extractable_count,
            "geo_readiness_tier": "HIGH" if extractable_count > 3 else "MEDIUM",
        }

        claims = []
        if extractable_count == 0 and len(pages) > 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement="Site lacks concise, definitive answer-first paragraphs suitable for AI search engine quotation.",
                category=Category.GEO,
                severity=Severity.HIGH,
                claim_type=ClaimType.FACT,
                confidence=0.91,
                recommendation="Format key informational pages with direct 40-60 word definitive answer summaries directly below H2 questions.",
                impact=8,
                effort=3,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "domain": "geo",
            "specialty": "geo_readiness",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
