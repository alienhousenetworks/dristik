"""
Dristik Modular Monolith: AEO Domain Pillar.

Orchestrates direct answers, conversational intent, and entity consensus
within the Dristik multi-agent blackboard cognitive loop.
"""
from __future__ import annotations

from typing import Any, List, Optional, Set

from app.aeo.specialists import AEO_SPECIALISTS, build_aeo_agents
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import Finding
from app.domain.pillar import PillarId, PillarScoreResult


class AeoPillar:
    pillar_id = PillarId.AEO
    domains: Set[str] = {"AI_SEARCH", "AEO"}

    def __init__(self, model_router: Any = None):
        self.model_router = model_router
        self.agents = build_aeo_agents(model_router)

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
        aeo_findings = [
            finding for finding in findings
            if getattr(finding, "pillar", None) == "aeo" or getattr(finding, "category", "") in self.domains
        ]
        count = len(aeo_findings)
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


__all__ = [
    "AeoPillar",
    "AEO_SPECIALISTS",
    "build_aeo_agents",
]
