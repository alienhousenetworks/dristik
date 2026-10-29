"""
AI Search Citation Agent:
Monitors domain mentions, source citations, and competitor displacement across
leading AI engines (Perplexity, ChatGPT Search, Gemini, Claude).
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType


class AiSearchCitationAgent(BaseAgent):
    """Tracks direct AI citations and reference links across LLM answer generators."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="geo.ai_search.v3",
            capability="ai_search_citations",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        manifest = getattr(blackboard, "crawl_manifest", None)
        domain = manifest.domain if manifest else getattr(blackboard, "website_url", "target-domain")
        ai_evals = getattr(blackboard, "ai_search_evaluations", []) or []

        if ai_evals:
            cited_count = sum(1 for e in ai_evals if getattr(e, "was_cited", False))
            share_pct = round((cited_count / len(ai_evals)) * 100.0, 1)
            status = "completed"
        else:
            share_pct = None
            status = "UNMEASURED"

        observations = {
            "monitored_domain": domain,
            "ai_engines_tracked": ["ChatGPT", "Perplexity", "Google Gemini", "Claude"],
            "share_of_model_percent": share_pct,
            "measured_evaluations_count": len(ai_evals),
            "engine_probes_status": "CONNECTED" if ai_evals else "NOT_CONNECTED",
        }

        claims = []
        result = {
            "agent_id": self.agent_id,
            "domain": "geo",
            "specialty": "ai_search_citation",
            "status": status,
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
        }
        return result
