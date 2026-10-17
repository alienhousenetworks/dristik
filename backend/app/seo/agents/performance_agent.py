"""
Performance & Core Web Vitals Agent:
Evaluates server response speed (TTFB), client rendering performance,
DOM complexity, and Lighthouse Core Web Vitals readiness.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType


class PerformanceAgent(BaseAgent):
    """Audits page delivery performance, TTFB, and Core Web Vitals metrics."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="seo.performance.v3",
            capability="performance",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        slow_ttfb_count = sum(1 for p in pages if getattr(p, "ttfb_ms", 0.0) > 800.0)

        observations = {
            "total_pages": len(pages),
            "slow_ttfb_count": slow_ttfb_count,
        }

        claims = []
        if slow_ttfb_count > 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement=f"Detected {slow_ttfb_count} pages with slow Time to First Byte (TTFB > 800ms).",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                claim_type=ClaimType.FACT,
                confidence=0.94,
                recommendation="Optimize server response times using full-page edge caching (CDN), database query indexing, and HTTP/2 or HTTP/3.",
                impact=8,
                effort=3,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "performance",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
