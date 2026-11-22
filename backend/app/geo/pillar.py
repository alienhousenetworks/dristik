"""GEO pillar: readiness, citations, per-engine review, and information gain."""
from __future__ import annotations

from typing import Any, List, Optional, Set

from app.geo.agents.citation_analyzer import AiSearchCitationAgent
from app.geo.agents.engine_analyzer import PerEngineEvaluatorAgent
from app.geo.agents.information_gain import InformationGainAgent
from app.geo.agents.readiness_analyzer import GeoReadinessAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import Finding
from app.domain.pillar import PillarId, PillarScoreResult

GEO_SPECIALISTS = {
    "geo_readiness": GeoReadinessAgent,
    "ai_search_citation": AiSearchCitationAgent,
    "per_engine_evaluator": PerEngineEvaluatorAgent,
    "information_gain": InformationGainAgent,
}


def build_geo_agents(model_router: Optional[Any]) -> dict:
    if model_router is None:
        return {agent_id: None for agent_id in GEO_SPECIALISTS}
    return {agent_id: cls(model_router) for agent_id, cls in GEO_SPECIALISTS.items()}


class GeoPillar:
    pillar_id = PillarId.GEO
    domains: Set[str] = {"GEO"}

    def __init__(self, model_router: Any = None):
        self.model_router = model_router
        self.agents = build_geo_agents(model_router)

    async def execute_wave(
        self,
        wave_index: int,
        blackboard: CognitiveBlackboard,
        active_agents: Set[str],
    ) -> List[Finding]:
        findings: List[Finding] = []
        for agent_id, agent in self.agents.items():
            if agent and agent_id in active_agents:
                res = await agent.run(blackboard)
                if isinstance(res, list):
                    findings.extend(res)
        return findings

    def calculate_pillar_score(
        self,
        findings: List[Finding],
        blackboard: Optional[CognitiveBlackboard] = None,
    ) -> PillarScoreResult:
        geo_findings = [
            finding for finding in findings
            if getattr(finding, "pillar", None) == "geo" or getattr(finding, "category", "") in self.domains
        ]
        count = len(geo_findings)
        geo_readiness = getattr(blackboard, "geo_readiness", None) if blackboard is not None else None
        measured = getattr(geo_readiness, "extractability_score", None) if geo_readiness is not None else None
        if isinstance(measured, (int, float)):
            score = round(max(0.0, min(100.0, float(measured))), 1)
            grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
            return PillarScoreResult(
                pillar_id=self.pillar_id,
                score=score,
                grade=grade,
                confidence=0.85,
                measured_findings_count=count,
                metrics={"findings_count": count, "score_status": "MEASURED", "source": "geo_readiness.extractability_score"},
            )
        # Finding volume is not a quality measurement; stay NOT_MEASURED until GEO readiness runs.
        return PillarScoreResult(
            pillar_id=self.pillar_id,
            score=0.0,
            grade="N/A",
            confidence=0.0,
            measured_findings_count=count,
            metrics={
                "findings_count": count,
                "score_status": "NOT_MEASURED",
                "score_reason": "GEO score must come from measured extractability/visibility, not finding count.",
            },
        )

    def citation_models(self):
        from app.geo.citation_models import citation_catalog, unqueried_surfaces

        return {
            "engines": citation_catalog(),
            "surfaces_not_queried": unqueried_surfaces(),
        }
