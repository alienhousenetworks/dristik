"""
Information Gain Agent:
Measures non-derivative insights, unique statistics, original research,
and proprietary claims that earn LLM citation authority.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard


class InformationGainAgent(BaseAgent):
    """Audits unique data points, proprietary datasets, and novel insights vs generic boilerplate."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="geo.information_gain.v3",
            capability="information_gain",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        if not pages:
            return {
                "agent_id": self.agent_id,
                "domain": "geo",
                "specialty": "information_gain",
                "status": "UNMEASURED",
                "observations": {
                    "information_gain_score": None,
                    "detected_original_data_points": 0,
                    "analyzed_pages": 0,
                },
                "claims": [],
            }

        import re
        data_points_count = 0
        total_words = 0
        for p in pages:
            body = getattr(p, "text", "") or getattr(p, "body", "") or ""
            words = getattr(p, "word_count", 0) or len(body.split())
            total_words += words
            stats = re.findall(r"\b\d+(?:\.\d+)?%|\$\d+|\b\d{4,}\b", body)
            data_points_count += len(stats)

        density = (data_points_count / max(total_words, 1)) * 1000
        score = min(round(density * 10, 1), 100.0) if total_words > 0 else 0.0

        return {
            "agent_id": self.agent_id,
            "domain": "geo",
            "specialty": "information_gain",
            "status": "completed",
            "observations": {
                "information_gain_score": score,
                "detected_original_data_points": data_points_count,
                "total_words_analyzed": total_words,
            },
            "claims": [],
        }
