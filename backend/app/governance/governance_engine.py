"""Phase 12: Master Enterprise Scoring & Governance Engine.

Coordinates all governance tiers:
- Metric Registry & Formula Authority (Phase 12.1)
- 6-Category Decoupled Scoring Governance & Algorithm Specification (Phase 12.2)
- Statistical Reliability & Wilson Intervals (Phase 12.3)
- Central 8-Factor Severity & Priority Decoupling (Phase 12.4)
- Independent Adversarial Review Critic (Phase 12.5)
- Permanent 10-Archetype Regression Library & Deterministic Replay (Phase 12.6)
"""
from __future__ import annotations

from typing import Any, Optional

from app.governance.adversarial_critic import IndependentAdversarialCritic
from app.governance.metric_registry import EnterpriseMetricRegistry
from app.governance.models import (
    AdversarialReviewVerdict,
    SampledMetricRecord,
    ScoringAlgorithmSpecification,
    ScoringCategory,
    SeverityEvaluation,
    SeverityFactor,
)
from app.governance.regression_library import RegressionBenchmarkLibrary
from app.governance.scoring_governance import ScoringGovernanceEngine
from app.governance.severity_engine import CentralSeverityEngine
from app.governance.statistical_reliability import StatisticalReliabilityEngine


class EnterpriseGovernanceEngine:
    """Master engine orchestrating enterprise scoring governance and quality assurance."""

    def __init__(self):
        self.metric_registry = EnterpriseMetricRegistry()
        self.scoring_governance = ScoringGovernanceEngine()
        self.statistical_engine = StatisticalReliabilityEngine()
        self.severity_engine = CentralSeverityEngine()
        self.adversarial_critic = IndependentAdversarialCritic()
        self.regression_library = RegressionBenchmarkLibrary()

    def run_full_governance_cycle(
        self,
        domain: str,
        audit_id: str,
        metric_values: dict[str, Optional[float]],
        findings: list[dict[str, Any]],
        evidence_ledger: Optional[dict[str, Any]] = None,
        telemetry: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Executes full governance scoring, statistical checks, and adversarial review."""
        ledger = evidence_ledger or {}
        telem = telemetry or {}

        # 1. Evaluate 6 orthogonal scoring dimensions
        category_evaluations: dict[str, dict[str, Any]] = {}
        for cat in ScoringCategory:
            category_evaluations[cat.value] = self.scoring_governance.evaluate_category_score(
                category=cat,
                metric_values=metric_values,
                findings=findings,
            )

        # 2. Evaluate severity and decoupled remediation priority for findings
        evaluated_findings: list[SeverityEvaluation] = []
        for f in findings:
            f_id = f.get("finding_id", "F-UNKNOWN")
            factors = SeverityFactor(
                defect_scope=f.get("scope", "SINGLE_PAGE"),
                technical_consequence=f.get("technical_consequence", 0.5),
                user_impact=f.get("user_impact", 0.5),
                business_importance=f.get("business_importance", 0.5),
                search_impact=f.get("search_impact", 0.5),
                security_relevance=f.get("security_relevance", 0.0),
                confidence=1.0 if str(f.get("confidence", "")).upper() == "VERIFIED" else 0.7,
            )
            traffic_tier = f.get("traffic_tier", "MEDIUM")
            sev_eval = self.severity_engine.evaluate_severity_and_priority(
                finding_id=f_id,
                factors=factors,
                traffic_tier=traffic_tier,
                title=f.get("title"),
            )
            evaluated_findings.append(sev_eval)

        # 3. Execute Independent Adversarial Review Critic
        critic_verdict: AdversarialReviewVerdict = self.adversarial_critic.review_report(
            report_id=f"rep_{audit_id}",
            audit_id=audit_id,
            findings=findings,
            evidence_ledger=ledger,
            category_scores=category_evaluations,
            telemetry=telem,
        )

        # 4. Generate Scoring Algorithm Specification
        algo_spec: ScoringAlgorithmSpecification = (
            self.scoring_governance.generate_scoring_algorithm_specification()
        )

        return {
            "domain": domain,
            "audit_id": audit_id,
            "category_evaluations": category_evaluations,
            "evaluated_findings": evaluated_findings,
            "critic_verdict": critic_verdict,
            "algorithm_specification": algo_spec,
            "governance_certified": critic_verdict.passed,
        }
