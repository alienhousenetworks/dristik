"""
Per-Engine Evaluator Agent:
Breaks down citation propensity and answers across Perplexity, ChatGPT Search,
Google AI Overviews, and Claude Artifacts.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard


class PerEngineEvaluatorAgent(BaseAgent):
    """Evaluates per-engine answer generation accuracy, brand sentiment, and citation footprint."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="geo.per_engine.v3",
            capability="per_engine_evaluation",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        ai_evals = getattr(blackboard, "ai_search_evaluations", []) or []
        engine_breakdown: Dict[str, Any] = {}

        if ai_evals:
            for eng in ["perplexity", "chatgpt", "gemini", "claude"]:
                eng_evals = [e for e in ai_evals if getattr(e, "engine_id", "").lower() == eng or eng in getattr(e, "engine", "").lower()]
                if eng_evals:
                    cited = sum(1 for e in eng_evals if getattr(e, "was_cited", False))
                    rate = round(cited / len(eng_evals), 2)
                    engine_breakdown[eng] = {
                        "visibility": "HIGH" if rate >= 0.5 else ("MEDIUM" if rate >= 0.2 else "LOW"),
                        "citation_rate": rate,
                        "queries_evaluated": len(eng_evals),
                    }
            status = "completed" if engine_breakdown else "UNMEASURED"
        else:
            status = "UNMEASURED"

        return {
            "agent_id": self.agent_id,
            "domain": "geo",
            "specialty": "per_engine_evaluator",
            "status": status,
            "observations": {
                "engine_breakdown": engine_breakdown,
                "engine_probes_status": "CONNECTED" if engine_breakdown else "NOT_CONNECTED",
            },
            "claims": [],
        }
