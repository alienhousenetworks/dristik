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
                elif isinstance(res, dict):
                    items = res.get("findings") or res.get("claims") or []
                    if isinstance(items, list):
                        findings.extend(items)
        return findings

    def calculate_pillar_score(
        self,
        findings: List[Finding],
        blackboard: Optional[CognitiveBlackboard] = None,
    ) -> PillarScoreResult:
        from app.domain.scoring.displayed_score import rating_for_displayed

        seo_findings = [
            finding for finding in findings
            if getattr(finding, "pillar", None) == "seo" or getattr(finding, "category", "") in self.domains
        ]
        count = len(seo_findings)
        severity_penalties = {"CRITICAL": 12.0, "HIGH": 7.0, "MEDIUM": 3.5, "LOW": 1.5, "INFO": 0.0}
        pages = getattr(blackboard, "pages", None) if blackboard is not None else None
        if pages is not None and len(pages) == 0 and count == 0:
            return PillarScoreResult(
                pillar_id=self.pillar_id,
                score=None,
                grade="—",
                confidence=0.0,
                measured_findings_count=0,
                metrics={"findings_count": 0},
            )
        penalty = sum(
            severity_penalties.get(
                str(getattr(getattr(f, "severity", None), "value", getattr(f, "severity", "MEDIUM"))).upper(),
                3.5,
            )
            for f in seo_findings
        )
        score = round(max(0.0, 100.0 - min(95.0, penalty)), 1)
        grade, _ = rating_for_displayed(score)
        return PillarScoreResult(
            pillar_id=self.pillar_id,
            score=score,
            grade=grade,
            confidence=0.85 if (pages or count > 0) else 0.5,
            measured_findings_count=count,
            metrics={"findings_count": count},
        )
