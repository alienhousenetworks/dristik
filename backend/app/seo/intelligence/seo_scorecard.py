"""
Versioned 9-Dimension SEO Scorecard — Phase 3.11

Computes the canonical 9-dimension weighted SEO score:
1. Crawlability & Indexability: 15%
2. Technical Infrastructure: 10%
3. Performance (Core Web Vitals): 15%
4. On-Page SEO: 15%
5. Content & Search Intent: 15%
6. Structured Data: 10%
7. Internal Linking: 10%
8. Mobile Experience: 5%
9. External Authority: 5%
Total: 100%

STRICT GUARDRAIL:
If external authority (or any dimension) is missing, the engine does NOT silently
redistribute weights to pretend 100% coverage was measured. It issues a PARTIAL_ASSESSMENT
status and explicitly highlights unmeasured dimensions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    dimension_name: str
    weight: float  # e.g. 0.15
    is_measured: bool
    score: Optional[float] = None  # 0.0 to 100.0
    status_label: str  # "MEASURED", "PARTIAL", "UNMEASURED"
    findings_count: int = 0
    grade: str = "N/A"  # A, B, C, D, F, N/A


class SeoScorecardReport(BaseModel):
    overall_score: float  # Weighted score across measured dimensions
    overall_grade: str
    assessment_status: str  # "FULL_ASSESSMENT", "PARTIAL_ASSESSMENT"
    coverage_percentage: float  # e.g. 95.0%
    dimension_breakdown: List[DimensionScore] = Field(default_factory=list)
    measured_dimensions_count: int
    unmeasured_dimensions: List[str] = Field(default_factory=list)
    limitations_disclosure: str


class SeoScorecardEngine:
    """
    Evaluates versioned SEO scores across the 9 canonical dimensions.
    """

    DIMENSION_WEIGHTS: Dict[str, float] = {
        "Crawlability & Indexability": 0.15,
        "Technical Infrastructure": 0.10,
        "Performance (Core Web Vitals)": 0.15,
        "On-Page SEO": 0.15,
        "Content & Search Intent": 0.15,
        "Structured Data": 0.10,
        "Internal Linking": 0.10,
        "Mobile Experience": 0.05,
        "External Authority": 0.05,
    }

    @classmethod
    def _grade_for_score(cls, s: Optional[float]) -> str:
        if s is None:
            return "N/A"
        if s >= 90:
            return "A"
        elif s >= 80:
            return "B"
        elif s >= 70:
            return "C"
        elif s >= 60:
            return "D"
        else:
            return "F"

    @classmethod
    def calculate_scorecard(
        cls,
        dimension_scores: Dict[str, Optional[float]],
        findings_counts: Optional[Dict[str, int]] = None,
    ) -> SeoScorecardReport:
        f_counts = findings_counts or {}
        breakdown: List[DimensionScore] = []
        measured_weight = 0.0
        weighted_sum = 0.0
        unmeasured: List[str] = []

        for dim, weight in cls.DIMENSION_WEIGHTS.items():
            val = dimension_scores.get(dim)
            cnt = f_counts.get(dim, 0)
            if val is not None and 0.0 <= val <= 100.0:
                measured_weight += weight
                weighted_sum += (val * weight)
                breakdown.append(
                    DimensionScore(
                        dimension_name=dim,
                        weight=weight,
                        is_measured=True,
                        score=round(val, 1),
                        status_label="MEASURED",
                        findings_count=cnt,
                        grade=cls._grade_for_score(val),
                    )
                )
            else:
                unmeasured.append(dim)
                breakdown.append(
                    DimensionScore(
                        dimension_name=dim,
                        weight=weight,
                        is_measured=False,
                        score=None,
                        status_label="UNMEASURED",
                        findings_count=cnt,
                        grade="N/A",
                    )
                )

        if measured_weight > 0:
            normalized_score = round(weighted_sum / measured_weight, 1)
        else:
            normalized_score = 0.0

        coverage_pct = round(measured_weight * 100, 1)
        is_full = len(unmeasured) == 0
        status = "FULL_ASSESSMENT" if is_full else "PARTIAL_ASSESSMENT"

        if is_full:
            disclosure = "Full 100% technical assessment completed across all 9 canonical SEO dimensions."
        else:
            disclosure = (
                f"Partial assessment: {coverage_pct}% of weighting evaluated. "
                f"Unmeasured dimension(s): {', '.join(unmeasured)}. Weights were not silently redistributed."
            )

        return SeoScorecardReport(
            overall_score=normalized_score,
            overall_grade=cls._grade_for_score(normalized_score),
            assessment_status=status,
            coverage_percentage=coverage_pct,
            dimension_breakdown=breakdown,
            measured_dimensions_count=len(breakdown) - len(unmeasured),
            unmeasured_dimensions=unmeasured,
            limitations_disclosure=disclosure,
        )
