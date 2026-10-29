"""SEO pillar: technical, content, linking, schema, and performance specialists."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Set

if TYPE_CHECKING:
    from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import Finding
from app.domain.pillar import PillarId, PillarScoreResult
from app.seo.specialists import build_seo_agents


class SeoPillar:
    pillar_id = PillarId.SEO
    domains: Set[str] = {"TECHNICAL_SEO", "STRUCTURED_DATA", "CONTENT"}

    def __init__(self, model_router: Any = None):
        self.model_router = model_router
        self.agents = build_seo_agents(model_router)

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
        seo_findings = [
            finding for finding in findings
            if getattr(finding, "pillar", None) == "seo" or getattr(finding, "category", "") in self.domains
        ]
        count = len(seo_findings)
        score = max(0.0, 100.0 - (count * 4.0))
        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
        return PillarScoreResult(
            pillar_id=self.pillar_id,
            score=round(score, 1),
            grade=grade,
            confidence=1.0,
            measured_findings_count=count,
            metrics={"findings_count": count},
        )
