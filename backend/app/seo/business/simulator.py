"""
Dristik AI Strategy Simulator
Projects Conservative, Balanced, and Aggressive remediation postures with confidence intervals.
Does not present speculative numerical guarantees.
"""
from typing import List, Dict, Any
from app.orchestration.mission.state import SimulationScenario
from app.domain.models import OverallScoreResult, Finding

class StrategySimulator:
    """
    Simulates projected outcomes of applying different tiers of recommended remediation.
    """

    def simulate_scenarios(
        self,
        current_score: float,
        findings: List[Finding]
    ) -> List[SimulationScenario]:
        def _sev(f: Finding) -> str:
            raw = getattr(f, "severity", "")
            return str(getattr(raw, "value", raw)).upper()

        critical_findings = [f for f in (findings or []) if _sev(f) == "CRITICAL"]
        high_findings = [f for f in (findings or []) if _sev(f) == "HIGH"]
        medium_findings = [f for f in (findings or []) if _sev(f) == "MEDIUM"]
        low_findings = [f for f in (findings or []) if _sev(f) == "LOW"]

        headroom = max(0.0, 100.0 - float(current_score or 0.0))
        # Derive conservative/balanced/aggressive score recovery strictly from open findings.
        # Zero open findings produces +0.0 projected score delta (never unconditional +8/+18).
        conservative_gain = min(headroom, min(12.0, (len(critical_findings) * 4.0) + (len(high_findings) * 1.5)))
        balanced_gain = min(
            headroom,
            min(22.0, conservative_gain + (len(high_findings) * 1.5) + (len(medium_findings) * 1.0)),
        )
        aggressive_gain = min(
            headroom,
            min(32.0, balanced_gain + (len(medium_findings) * 0.8) + (len(low_findings) * 0.5)),
        )

        conservative_score = round(min(100.0, current_score + conservative_gain), 1)
        balanced_score = round(min(100.0, current_score + balanced_gain), 1)
        aggressive_score = round(min(100.0, current_score + aggressive_gain), 1)

        crit_titles = [f.title for f in critical_findings[:2]] or ["No critical blockers identified in sample"]
        high_titles = [f.title for f in (critical_findings + high_findings)[:3]] or ["Maintain existing technical and content posture"]
        all_titles = [f.title for f in (critical_findings + high_findings + medium_findings)[:3]] or ["No open medium/high findings in current sample"]

        return [
            SimulationScenario(
                id="scen_conservative",
                name="Conservative (Core Stability)",
                projected_score=conservative_score,
                confidence_interval=f"{round(max(0.0, conservative_score - 2.0), 1)} - {round(min(100.0, conservative_score + 2.0), 1)} (model estimate; traffic unmeasured without GSC/GA4)",
                expected_gains=crit_titles,
                risks=["Addresses critical blockers only; lower-severity defects remain open"],
                timeframe_days=7
            ),
            SimulationScenario(
                id="scen_balanced",
                name="Balanced (Recommended Growth)",
                projected_score=balanced_score,
                confidence_interval=f"{round(max(0.0, balanced_score - 3.0), 1)} - {round(min(100.0, balanced_score + 3.0), 1)} (model estimate; traffic unmeasured without GSC/GA4)",
                expected_gains=high_titles,
                risks=["Requires coordinated engineering and content verification"],
                timeframe_days=30
            ),
            SimulationScenario(
                id="scen_aggressive",
                name="Aggressive (Full Remediation)",
                projected_score=aggressive_score,
                confidence_interval=f"{round(max(0.0, aggressive_score - 4.0), 1)} - {round(min(100.0, aggressive_score + 4.0), 1)} (model estimate; traffic unmeasured without GSC/GA4)",
                expected_gains=all_titles,
                risks=["Higher implementation scope; commercial lift requires connected analytics verification"],
                timeframe_days=90
            )
        ]
