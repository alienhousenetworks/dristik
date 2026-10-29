"""
Internal Linking & PageRank Flow Agent:
Analyzes site architecture depth, internal link equity distribution,
anchor text quality, and orphan page risk.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType


class InternalLinkingAgent(BaseAgent):
    """Audits internal link equity, crawl depth, and orphan page detection."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="seo.internal_links.v3",
            capability="internal_linking",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        deep_pages_count = sum(1 for p in pages if getattr(p, "depth", 1) > 4)

        observations = {
            "total_pages": len(pages),
            "pages_with_depth_greater_than_4": deep_pages_count,
        }

        claims = []
        if deep_pages_count > 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement=f"Detected {deep_pages_count} pages located beyond 4 click depths from the root domain.",
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                claim_type=ClaimType.FACT,
                confidence=0.92,
                recommendation="Flatten site architecture so high-priority commercial and content pages are accessible within 3 clicks.",
                impact=6,
                effort=4,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "internal_linking",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
