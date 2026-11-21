"""
Mathematical 100-Point SEO Score Engine (2026 Master Standard).
Implements transparent, reproducible scoring across 9 weighted dimensions:
1. Technical SEO and crawlability (20%)
2. Indexation and canonicalization (15%)
3. Content quality and search intent (15%)
4. On-page SEO (10%)
5. Internal linking and site architecture (10%)
6. Structured data and entities (10%)
7. Performance and mobile experience (10%)
8. International/local/ecommerce applicability (5% conditional)
9. Trust and authority signals (5%)

Guarantees:
- Unmeasured or unavailable dimensions are excluded from the denominator without penalty.
- Independent confidence vectors (SEO Health, Audit Coverage, Evidence Confidence, Data Freshness, Connector Completeness).
- Zero manufactured scores.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class ScoreInterpretation(str, Enum):
    EXCELLENT = "Excellent"           # 90–100
    STRONG = "Strong"                 # 80–89
    GOOD = "Good"                     # 70–79
    NEEDS_IMPROVEMENT = "Needs improvement"  # 60–69
    WEAK = "Weak"                     # 40–59
    CRITICAL = "Critical"             # 0–39


def interpret_score(score: Optional[float]) -> ScoreInterpretation:
    if score is None:
        return ScoreInterpretation.CRITICAL
    if score >= 90.0:
        return ScoreInterpretation.EXCELLENT
    if score >= 80.0:
        return ScoreInterpretation.STRONG
    if score >= 70.0:
        return ScoreInterpretation.GOOD
    if score >= 60.0:
        return ScoreInterpretation.NEEDS_IMPROVEMENT
    if score >= 40.0:
        return ScoreInterpretation.WEAK
    return ScoreInterpretation.CRITICAL


class MetricCheck(BaseModel):
    check_id: str
    weight: float = 1.0
    passed: bool
    is_executed: bool = True
    evidence_id: Optional[str] = None


class DimensionResult(BaseModel):
    dimension_id: str
    name: str
    configured_weight: float
    effective_weight: Optional[float] = None
    is_applicable: bool = True
    is_measured: bool = True
    score: Optional[float] = None  # 0.0 to 100.0
    passed_checks_count: int = 0
    executed_checks_count: int = 0
    interpretation: Optional[ScoreInterpretation] = None
    notes: List[str] = Field(default_factory=list)


class ConfidenceBreakdown(BaseModel):
    audit_coverage_pct: float = 0.0          # Tested / eligible URLs
    evidence_confidence_pct: float = 100.0    # Ratio of verified machine observations
    data_freshness_hours: float = 0.0        # Age of underlying evidence
    connector_completeness_pct: float = 0.0  # Percentage of available connectors active
    sampling_status: str = "SAMPLED_AUDIT"


class SeoScorecardReport(BaseModel):
    methodology_version: str = "dristik_seo_v3.0"
    overall_health_score: Optional[float] = None  # S_SEO (0–100)
    overall_interpretation: ScoreInterpretation = ScoreInterpretation.CRITICAL
    dimensions: List[DimensionResult] = Field(default_factory=list)
    measured_dimensions_count: int = 0
    excluded_dimensions_count: int = 0
    active_weight_sum: float = 0.0
    confidence_vectors: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    disclosures: List[str] = Field(default_factory=list)
    sealed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MathematicalScoreEngine:
    """
    Computes mathematically sound, reproducible SEO scores with transparent denominator normalization.
    """

    METHODOLOGY_VERSION = "dristik_seo_v3.0"

    DIMENSION_WEIGHTS: Dict[str, Dict[str, Any]] = {
        "technical_crawlability": {
            "name": "Technical SEO and crawlability",
            "weight": 0.20,
            "is_conditional": False,
        },
        "indexation_canonicalization": {
            "name": "Indexation and canonicalization",
            "weight": 0.15,
            "is_conditional": False,
        },
        "content_quality_intent": {
            "name": "Content quality and search intent",
            "weight": 0.15,
            "is_conditional": False,
        },
        "on_page_seo": {
            "name": "On-page SEO",
            "weight": 0.10,
            "is_conditional": False,
        },
        "internal_linking_architecture": {
            "name": "Internal linking and site architecture",
            "weight": 0.10,
            "is_conditional": False,
        },
        "structured_data_entities": {
            "name": "Structured data and entities",
            "weight": 0.10,
            "is_conditional": False,
        },
        "performance_mobile": {
            "name": "Performance and mobile experience",
            "weight": 0.10,
            "is_conditional": False,
        },
        "specialist_applicability": {
            "name": "International/local/ecommerce applicability",
            "weight": 0.05,
            "is_conditional": True,  # Conditionally excluded if site has no international/local/ecommerce features
        },
        "trust_authority_signals": {
            "name": "Trust and authority signals",
            "weight": 0.05,
            "is_conditional": True,  # Excluded if backlink connector is unmeasured
        },
    }

    def calculate_metric_score(self, checks: List[MetricCheck]) -> Optional[float]:
        """
        S_i = 100 * (Weighted passed checks / Weighted executed checks)
        """
        executed = [c for c in checks if c.is_executed]
        if not executed:
            return None

        weighted_passed = sum(c.weight for c in executed if c.passed)
        weighted_total = sum(c.weight for c in executed)

        if weighted_total <= 0.0:
            return None
        return round(100.0 * (weighted_passed / weighted_total), 2)

    def calculate_dimension_score(
        self,
        dimension_id: str,
        metric_checks: List[MetricCheck],
        is_applicable: bool = True,
    ) -> DimensionResult:
        cfg = self.DIMENSION_WEIGHTS.get(dimension_id, {
            "name": dimension_id,
            "weight": 0.10,
            "is_conditional": False,
        })
        name = cfg["name"]
        configured_weight = cfg["weight"]

        if not is_applicable:
            return DimensionResult(
                dimension_id=dimension_id,
                name=name,
                configured_weight=configured_weight,
                effective_weight=None,
                is_applicable=False,
                is_measured=False,
                score=None,
                interpretation=None,
                notes=["This dimension was determined to be inapplicable to the target site and is excluded without penalty."],
            )

        executed_checks = [c for c in metric_checks if c.is_executed]
        if not executed_checks:
            return DimensionResult(
                dimension_id=dimension_id,
                name=name,
                configured_weight=configured_weight,
                effective_weight=None,
                is_applicable=True,
                is_measured=False,
                score=None,
                interpretation=None,
                notes=["No valid observations were recorded for this applicable dimension (DATA_UNAVAILABLE)."],
            )

        score = self.calculate_metric_score(executed_checks)
        passed_count = sum(1 for c in executed_checks if c.passed)

        return DimensionResult(
            dimension_id=dimension_id,
            name=name,
            configured_weight=configured_weight,
            is_applicable=True,
            is_measured=True,
            score=score,
            passed_checks_count=passed_count,
            executed_checks_count=len(executed_checks),
            interpretation=interpret_score(score),
            notes=[],
        )

    def calculate_scorecard(
        self,
        dimension_results: List[DimensionResult],
        confidence: Optional[ConfidenceBreakdown] = None,
    ) -> SeoScorecardReport:
        """
        Calculates S_SEO = sum(W_d * S_d) / sum(W_d)
        Only applicable dimensions with valid measurements enter the denominator.
        """
        measured = [d for d in dimension_results if d.is_applicable and d.is_measured and d.score is not None]
        excluded = [d for d in dimension_results if not d.is_applicable or not d.is_measured or d.score is None]

        active_weight_sum = sum(d.configured_weight for d in measured)
        disclosures = []

        if active_weight_sum <= 0.0 or not measured:
            overall_score = None
            overall_interp = ScoreInterpretation.CRITICAL
            disclosures.append("No applicable dimensions had sufficient machine evidence to calculate an authoritative SEO score.")
        else:
            weighted_sum = sum(d.configured_weight * (d.score or 0.0) for d in measured)
            overall_score = round(weighted_sum / active_weight_sum, 2)
            overall_interp = interpret_score(overall_score)

            # Assign normalized effective weights
            for d in measured:
                d.effective_weight = round(d.configured_weight / active_weight_sum, 4)

            if active_weight_sum < 1.0:
                disclosures.append(
                    f"Overall score normalized across {len(measured)} measured dimensions "
                    f"representing {round(active_weight_sum * 100, 1)}% of maximum theoretical framework weight. "
                    f"{len(excluded)} dimension(s) were excluded from denominator without penalty."
                )

        return SeoScorecardReport(
            methodology_version=self.METHODOLOGY_VERSION,
            overall_health_score=overall_score,
            overall_interpretation=overall_interp,
            dimensions=dimension_results,
            measured_dimensions_count=len(measured),
            excluded_dimensions_count=len(excluded),
            active_weight_sum=round(active_weight_sum, 4),
            confidence_vectors=confidence or ConfidenceBreakdown(),
            disclosures=disclosures,
        )
