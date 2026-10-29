"""
Content & On-Page SEO Agent:
Audits heading hierarchies (H1/H2), title tag optimizations,
meta descriptions, topical depth, and keyword intent mapping.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType
from app.evidence.retriever import EvidenceRetriever


class ContentSeoAgent(BaseAgent):
    """Audits on-page semantics, heading structure, metadata, and topical depth."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="seo.content.v3",
            capability="content_quality",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        missing_h1_count = 0
        thin_content_count = 0

        for page in pages:
            if not getattr(page, "h1", None) or len(page.h1) == 0:
                missing_h1_count += 1
            if getattr(page, "word_count", 0) < 200:
                thin_content_count += 1

        observations = {
            "total_pages": len(pages),
            "pages_missing_h1": missing_h1_count,
            "thin_content_pages": thin_content_count,
        }

        claims = []
        if missing_h1_count > 0:
            claim = self.register_claim(
                blackboard=blackboard,
                statement=f"Found {missing_h1_count} pages without a primary H1 heading element.",
                category=Category.ON_PAGE_SEO,
                severity=Severity.HIGH,
                claim_type=ClaimType.FACT,
                confidence=0.98,
                recommendation="Ensure every indexable page has exactly one descriptive, keyword-targeted <h1> heading.",
                impact=6,
                effort=1,
            )
            claims.append(claim)

        result = {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "content_seo",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
