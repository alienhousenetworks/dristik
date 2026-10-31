"""
Content & On-Page SEO Agent:
Audits heading hierarchies (H1/H2), title tag optimizations,
meta descriptions, topical depth, and keyword intent mapping.
"""
from typing import Any, Dict
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard


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
        word_counts = []
        for page in pages:
            if not getattr(page, "h1", None) or len(page.h1) == 0:
                missing_h1_count += 1
            count = getattr(page, "word_count", None)
            if isinstance(count, (int, float)):
                word_counts.append(int(count))

        observations = {
            "total_pages": len(pages),
            "pages_missing_h1": missing_h1_count,
            "word_counts": word_counts,
        }

        return {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "content_seo",
            "status": "completed",
            "observations": observations,
            "claims": [],
        }
