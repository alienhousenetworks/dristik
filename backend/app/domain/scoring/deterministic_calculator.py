"""
Deterministic Scoring Framework — Enterprise Quality Standard (Phase 0.4)

Enforces transparent, reproducible metric and score evaluations.
Eliminates silent zero penalties for unmeasured dimensions and provides
coverage-adjusted partial scoring when essential inputs are missing.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.domain.enums import (
    EvidenceStatus,
    MetricDirection,
    MissingDataRule,
)
from app.domain.canonical_audit_model import (
    EvidenceRecord,
    MetricResult,
    ScoreResult,
)


class DeterministicMetricCalculator:
    """
    Evaluates individual diagnostic metrics from input evidence records.
    """

    @classmethod
    def evaluate_metric(
        cls,
        audit_run_id: str,
        domain_id: str,
        metric_id: str,
        name: str,
        formula_version: str,
        direction: MetricDirection,
        benchmark_value: float,
        weight: float,
        missing_data_rule: MissingDataRule,
        evidence_records: List[EvidenceRecord],
        extraction_fn: Optional[callable] = None,
    ) -> MetricResult:
        """
        Calculates a normalized 0-100 score from verified evidence records.
        If no evidence records exist, strictly applies the missing data rule without fabricating a zero.
        """
        # Validate that all input evidence records belong to the same audit execution run
        for rec in evidence_records:
            if rec.audit_run_id != audit_run_id:
                raise ValueError(
                    f"Cross-run contamination detected! Evidence {rec.evidence_id} belongs to "
                    f"{rec.audit_run_id}, expected {audit_run_id}."
                )

        input_evidence_ids = [r.evidence_id for r in evidence_records]

        # Check for unmeasured / missing inputs
        if not evidence_records:
            return cls._handle_missing_metric(
                audit_run_id=audit_run_id,
                domain_id=domain_id,
                metric_id=metric_id,
                name=name,
                formula_version=formula_version,
                direction=direction,
                benchmark_value=benchmark_value,
                missing_data_rule=missing_data_rule,
            )

        # Extract numeric values
        values: List[float] = []
        for r in evidence_records:
            val = None
            if extraction_fn:
                val = extraction_fn(r)
            elif isinstance(r.raw_value, (int, float)):
                val = float(r.raw_value)
            elif isinstance(r.raw_value, dict) and "value" in r.raw_value:
                val = float(r.raw_value["value"])
            if val is not None and not math.isnan(val):
                values.append(val)

        if not values:
            return cls._handle_missing_metric(
                audit_run_id=audit_run_id,
                domain_id=domain_id,
                metric_id=metric_id,
                name=name,
                formula_version=formula_version,
                direction=direction,
                benchmark_value=benchmark_value,
                missing_data_rule=missing_data_rule,
            )

        # Compute median/mean observation
        avg_val = sum(values) / len(values)

        # Normalize score against benchmark
        if direction == MetricDirection.HIGHER_IS_BETTER:
            # E.g. Word count, coverage %
            norm_score = min(100.0, (avg_val / benchmark_value) * 100.0) if benchmark_value > 0 else 100.0
        else:
            # Lower is better, e.g. TTFB ms, friction points, errors
            if avg_val <= benchmark_value:
                norm_score = 100.0
            else:
                # Scaled penalty beyond benchmark threshold
                norm_score = max(0.0, 100.0 - ((avg_val - benchmark_value) / benchmark_value) * 50.0)

        norm_score = round(max(0.0, min(100.0, norm_score)), 1)

        return MetricResult(
            audit_run_id=audit_run_id,
            domain_id=domain_id,
            metric_id=metric_id,
            name=name,
            formula_version=formula_version,
            classification=EvidenceStatus.MEASURED,
            direction=direction,
            input_evidence_ids=input_evidence_ids,
            raw_value=round(avg_val, 2),
            normalized_score=norm_score,
            benchmark_value=benchmark_value,
            missing_data_rule=missing_data_rule,
            confidence=1.0,
            coverage_ratio=1.0,
            notes=f"Computed from {len(values)} empirical sample point(s) against benchmark {benchmark_value}.",
        )

    @classmethod
    def _handle_missing_metric(
        cls,
        audit_run_id: str,
        domain_id: str,
        metric_id: str,
        name: str,
        formula_version: str,
        direction: MetricDirection,
        benchmark_value: float,
        missing_data_rule: MissingDataRule,
    ) -> MetricResult:
        if missing_data_rule == MissingDataRule.FAIL_CLOSED:
            score = 0.0
            status = EvidenceStatus.UNAVAILABLE
            notes = "FAIL_CLOSED: Connector unconfigured or required input unavailable."
        elif missing_data_rule == MissingDataRule.NEUTRAL_EXCLUDE:
            score = None
            status = EvidenceStatus.NOT_TESTED
            notes = "NEUTRAL_EXCLUDE: Excluded from composite calculation without penalty."
        else:  # UNMEASURED_FLAG
            score = None
            status = EvidenceStatus.UNAVAILABLE
            notes = "UNMEASURED: Metric was not observed in this audit run."

        return MetricResult(
            audit_run_id=audit_run_id,
            domain_id=domain_id,
            metric_id=metric_id,
            name=name,
            formula_version=formula_version,
            classification=status,
            direction=direction,
            input_evidence_ids=[],
            raw_value=None,
            normalized_score=score,
            benchmark_value=benchmark_value,
            missing_data_rule=missing_data_rule,
            confidence=0.0,
            coverage_ratio=0.0,
            notes=notes,
        )


class DeterministicScoreEngine:
    """
    Assembles versioned, weighted composite scores from validated MetricResults.
    """

    @classmethod
    def assemble_composite_score(
        cls,
        audit_run_id: str,
        domain_id: str,
        metric_results: List[MetricResult],
        category_weights: Dict[str, float],
    ) -> ScoreResult:
        """
        Calculates category scores and overall composite score.
        If essential metrics are unmeasured, marks result as PARTIAL_ASSESSMENT with coverage ratio.
        """
        measured_metrics = [m for m in metric_results if m.normalized_score is not None]
        total_metrics_count = len(metric_results)
        measured_count = len(measured_metrics)

        coverage_ratio = round(measured_count / total_metrics_count, 2) if total_metrics_count > 0 else 0.0
        is_partial = coverage_ratio < 0.85

        category_scores: Dict[str, float] = {}
        weighted_contributions: Dict[str, float] = {}
        audit_trail: List[str] = []

        total_weight_sum = sum(category_weights.values())
        if abs(total_weight_sum - 100.0) > 0.5 and abs(total_weight_sum - 1.0) > 0.01:
            audit_trail.append(f"Warning: Category weights sum to {total_weight_sum}, expected 100.0.")

        running_weighted_sum = 0.0
        active_weight_sum = 0.0

        for cat_name, cat_weight in category_weights.items():
            cat_metrics = [m for m in measured_metrics if m.metric_id.startswith(cat_name) or cat_name in m.name.upper()]
            if cat_metrics:
                cat_avg = sum(m.normalized_score for m in cat_metrics) / len(cat_metrics)
                category_scores[cat_name] = round(cat_avg, 1)
                
                # Weight calculation
                contribution = (cat_avg * (cat_weight / 100.0)) if total_weight_sum > 1.5 else (cat_avg * cat_weight)
                weighted_contributions[cat_name] = round(contribution, 2)
                running_weighted_sum += contribution
                active_weight_sum += cat_weight
                audit_trail.append(f"{cat_name}: score={cat_avg:.1f}, weight={cat_weight}, contribution={contribution:.2f}")
            else:
                audit_trail.append(f"{cat_name}: UNMEASURED — omitted from composite.")

        if is_partial:
            # Adjust score by active weight or mark partial
            overall_score = round(running_weighted_sum * (total_weight_sum / active_weight_sum), 1) if active_weight_sum > 0 else None
            grade = cls._calculate_grade(overall_score) if overall_score is not None else "UNGRADED"
            audit_trail.append(f"PARTIAL ASSESSMENT: Only {measured_count}/{total_metrics_count} metrics available (coverage {coverage_ratio*100:.0f}%).")
        else:
            overall_score = round(running_weighted_sum, 1)
            grade = cls._calculate_grade(overall_score)
            audit_trail.append(f"COMPLETE ASSESSMENT: All essential dimensions evaluated.")

        return ScoreResult(
            audit_run_id=audit_run_id,
            domain_id=domain_id,
            score_id=f"scr_{audit_run_id[-8:]}",
            overall_score=overall_score,
            grade=grade,
            is_partial_assessment=is_partial,
            coverage_score=coverage_ratio,
            category_scores=category_scores,
            weighted_contributions=weighted_contributions,
            formula_audit_trail=audit_trail,
        )

    @staticmethod
    def _calculate_grade(score: Optional[float]) -> str:
        if score is None:
            return "UNGRADED"
        if score >= 90.0:
            return "A"
        if score >= 80.0:
            return "B"
        if score >= 70.0:
            return "C"
        if score >= 60.0:
            return "D"
        return "F"
