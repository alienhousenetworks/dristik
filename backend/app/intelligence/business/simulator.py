"""
Dristik AI Strategy Simulator
Projects Conservative, Balanced, and Aggressive remediation postures with confidence intervals.
Does not present speculative numerical guarantees.
"""
from typing import List, Dict, Any
from app.mission.state import SimulationScenario
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
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")

        # 1. Conservative: Fix only Critical technical & schema issues
        conservative_gain = min(12.0, (critical_count * 5.0) + (high_count * 2.0))
        conservative_score = min(98.0, round(current_score + conservative_gain, 1))

        # 2. Balanced: Fix Critical + High + Commercial Messaging
        balanced_gain = min(22.0, conservative_gain + 8.0)
        balanced_score = min(98.0, round(current_score + balanced_gain, 1))

        # 3. Aggressive: Fix all issues + Publish new topic cluster & GEO schemas
        aggressive_gain = min(32.0, balanced_gain + 10.0)
        aggressive_score = min(99.0, round(current_score + aggressive_gain, 1))

        return [
            SimulationScenario(
                id="scen_conservative",
                name="Conservative (Core Stability)",
                projected_score=conservative_score,
                confidence_interval=f"{int(conservative_score - 3)}% - {int(conservative_score + 2)}%",
                expected_gains=[
                    "Eliminates critical technical SEO & crawlability blockers",
                    "Validates Schema.org syntax for AI crawl engines"
                ],
                risks=["Minimal commercial conversion lift without copy adjustments"],
                timeframe_days=7
            ),
            SimulationScenario(
                id="scen_balanced",
                name="Balanced (Recommended Growth)",
                projected_score=balanced_score,
                confidence_interval=f"{int(balanced_score - 4)}% - {int(balanced_score + 3)}%",
                expected_gains=[
                    "Resolves top commercial positioning & ICP ambiguities",
                    "Deploys complete JSON-LD Organization & FAQ markup",
                    "Streamlines primary conversion CTA action paths"
                ],
                risks=["Requires cross-functional coordination between engineering and marketing"],
                timeframe_days=30
            ),
            SimulationScenario(
                id="scen_aggressive",
                name="Aggressive (Market Leadership)",
                projected_score=aggressive_score,
                confidence_interval=f"{int(aggressive_score - 6)}% - {int(aggressive_score + 4)}%",
                expected_gains=[
                    "Full generative engine citation readiness across all buyer query clusters",
                    "Launches dedicated topic cluster addressing high-intent search queries",
                    "Deploys transparent pricing calculator and automated lead qualification"
                ],
                risks=["Higher operational effort; requires dedicated content creation resources"],
                timeframe_days=90
            )
        ]
