"""SEO specialist roster for the SEO pillar."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.seo.agents.content import ContentSeoAgent
from app.seo.agents.internal_linking import InternalLinkingAgent
from app.seo.agents.performance_agent import PerformanceAgent
from app.seo.agents.specialized_seo_agent import SpecializedSeoAgent
from app.seo.agents.structured_data import StructuredDataAgent
from app.seo.agents.technical import TechnicalSeoAgent

SEO_SPECIALISTS = {
    "technical_seo": TechnicalSeoAgent,
    "content_seo": ContentSeoAgent,
    "internal_linking": InternalLinkingAgent,
    "structured_data": StructuredDataAgent,
    "performance": PerformanceAgent,
    "specialized_seo": SpecializedSeoAgent,
}


def build_seo_agents(model_router: Optional[Any]) -> Dict[str, Any]:
    if model_router is None:
        return {agent_id: None for agent_id in SEO_SPECIALISTS}
    return {agent_id: cls(model_router) for agent_id, cls in SEO_SPECIALISTS.items()}
