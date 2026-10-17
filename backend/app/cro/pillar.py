"""
CRO (Conversion Rate Optimization) Domain Pillar.

Orchestrates conversion, visual UX, forms, and trust specialists,
evaluates interaction friction, and calculates domain pillar scores.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.cro.agents import (
    CroConversionAgent,
    FormAbandonmentAgent,
    PricingTrustAgent,
    VisualUxFrictionAgent,
)
from app.cro.analyzer import CroAnalyzer
from app.analyzers.form_analyzer import analyze_forms
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import Finding, PageEvidence
from app.domain.pillar import PillarId, PillarScoreResult

CRO_SPECIALISTS = {
    "cro_conversion": CroConversionAgent,
    "visual_ux_friction": VisualUxFrictionAgent,
    "form_abandonment": FormAbandonmentAgent,
    "pricing_trust": PricingTrustAgent,
}


def build_cro_agents(model_router: Optional[Any]) -> dict:
    if model_router is None:
        return {agent_id: None for agent_id in CRO_SPECIALISTS}
    return {agent_id: cls(model_router) for agent_id, cls in CRO_SPECIALISTS.items()}


def evaluate_friction(
    pages: List[PageEvidence],
    raw_html_map: Optional[Dict[str, str]] = None,
    business_profile: Optional[Any] = None,
):
    """Return the CRO report, findings, and the form audit already inside that report."""
    report, findings = CroAnalyzer.analyze_cro(pages, raw_html_map, business_profile)
    forms = analyze_forms(pages, raw_html_map)
    return report, findings, forms


class CroPillar:
    pillar_id = PillarId.CRO
    domains: Set[str] = {"EXPERIENCE", "UX_CONVERSION"}

    def __init__(self, model_router: Any = None):
        self.model_router = model_router
        self.agents = build_cro_agents(model_router)

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
        cro_findings = [
            finding for finding in findings
            if getattr(finding, "pillar", None) == "cro" or getattr(finding, "category", "") in self.domains
        ]
        count = len(cro_findings)
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
    "CroPillar",
    "CRO_SPECIALISTS",
    "build_cro_agents",
    "evaluate_friction",
]
