"""
Decoupled 10-Dimension AEO Scorecard — Phase 5.9

Computes versioned AEO scores across 10 canonical dimensions:
Track A: Content Readiness (75% total base):
  1. Question Coverage: 15%
  2. Answer Completeness: 15%
  3. Passage Extractability: 10%
  4. Factual Grounding: 15%
  5. Structured Answer Readiness: 10%
  6. Conversational Coverage: 5%
  7. Source Credibility: 5%

Track B: Live Answer Outcomes (25% total base):
  8. Live Answer Appearance: 10%
  9. Citation Accuracy: 10%
  10. Answer Consistency: 5%

STRICT FIREWALL GUARDRAIL:
Separates content-readiness scores from live-answer outcome scores.
If live tests have not run, the scorecard reports PARTIAL_ASSESSMENT with Track B marked NOT_TESTED.
Never blends or fakes a 100% composite score when live tests are absent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AeoDimensionResult(BaseModel):
    dimension_key: str
    dimension_name: str
    track: str  # "TRACK_A_CONTENT_READINESS" or "TRACK_B_LIVE_OUTCOMES"
    weight: float
    is_measured: bool
    score: Optional[float] = None
    grade: str = "N/A"
    notes: str = ""


class AeoScorecardReport(BaseModel):
    overall_score: Optional[float] = None
    measured_subset_score: Optional[float] = None
    overall_grade: str
    assessment_status: str  # "FULL_ASSESSMENT", "PARTIAL_ASSESSMENT"
    coverage_percentage: float  # e.g. 75.0% or 100.0%
    track_a_readiness_score: Optional[float] = None
    track_b_live_score: Optional[float] = None
    is_live_tested: bool
    dimension_breakdown: List[AeoDimensionResult] = Field(default_factory=list)
    unmeasured_dimensions: List[str] = Field(default_factory=list)
    firewall_disclosure_statement: str


class AeoScorecardEngine:
    """
    Computes versioned AEO scores with strict Track A / Track B decoupling.
    """

    DIMENSION_SPECS: Dict[str, Dict[str, Any]] = {
        # Track A: Content Readiness (75%)
        "question_coverage": {"name": "Question Universe Coverage", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.15},
        "answer_completeness": {"name": "Answer Element Completeness", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.15},
        "passage_extractability": {"name": "Passage Extractability & Density", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.10},
        "factual_grounding": {"name": "Empirical Factual Grounding", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.15},
        "structured_readiness": {"name": "Structured Q&A & FAQ Schema", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.10},
        "conversational_coverage": {"name": "Conversational & Voice Readiness", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.05},
        "source_credibility": {"name": "Third-Party Source Credibility", "track": "TRACK_A_CONTENT_READINESS", "weight": 0.05},
        # Track B: Live Outcomes (25%)
        "live_answer_appearance": {"name": "Direct Answer Appearance", "track": "TRACK_B_LIVE_OUTCOMES", "weight": 0.10},
        "citation_accuracy": {"name": "Canonical Citation Accuracy", "track": "TRACK_B_LIVE_OUTCOMES", "weight": 0.10},
        "answer_consistency": {"name": "Multi-Engine Answer Consistency", "track": "TRACK_B_LIVE_OUTCOMES", "weight": 0.05},
    }

    @classmethod
    def _grade(cls, val: Optional[float]) -> str:
        if val is None:
            return "N/A"
        if val >= 85:
            return "A"
        elif val >= 70:
            return "B"
        elif val >= 55:
            return "C"
        elif val >= 40:
            return "D"
        else:
            return "F"

    @classmethod
    def calculate_scorecard(
        cls,
        dimension_scores: Dict[str, Optional[float]],
        live_testing_ran: bool = False,
    ) -> AeoScorecardReport:
        dim_results: List[AeoDimensionResult] = []
        measured_weight = 0.0
        weighted_sum = 0.0
        unmeasured: List[str] = []

        track_a_weight = 0.0
        track_a_sum = 0.0
        track_b_weight = 0.0
        track_b_sum = 0.0

        for key, spec in cls.DIMENSION_SPECS.items():
            val = dimension_scores.get(key)
            w = spec["weight"]
            track = spec["track"]

            # If track B and live testing did not run, treat as unmeasured
            if track == "TRACK_B_LIVE_OUTCOMES" and not live_testing_ran:
                val = None

            if val is not None and 0.0 <= val <= 100.0:
                measured_weight += w
                weighted_sum += val * w
                dim_results.append(
                    AeoDimensionResult(
                        dimension_key=key,
                        dimension_name=spec["name"],
                        track=track,
                        weight=w,
                        is_measured=True,
                        score=round(val, 1),
                        grade=cls._grade(val),
                        notes="Measured deterministically." if track == "TRACK_A_CONTENT_READINESS" else "Observed in live answer engine telemetry.",
                    )
                )
                if track == "TRACK_A_CONTENT_READINESS":
                    track_a_weight += w
                    track_a_sum += val * w
                else:
                    track_b_weight += w
                    track_b_sum += val * w
            else:
                unmeasured.append(spec["name"])
                dim_results.append(
                    AeoDimensionResult(
                        dimension_key=key,
                        dimension_name=spec["name"],
                        track=track,
                        weight=w,
                        is_measured=False,
                        score=None,
                        grade="N/A",
                        notes="Unmeasured: Live answer testing was not executed." if track == "TRACK_B_LIVE_OUTCOMES" else "Input data unmeasured.",
                    )
                )

        track_a_expected = sum(spec["weight"] for spec in cls.DIMENSION_SPECS.values() if spec["track"] == "TRACK_A_CONTENT_READINESS")
        track_b_expected = sum(spec["weight"] for spec in cls.DIMENSION_SPECS.values() if spec["track"] == "TRACK_B_LIVE_OUTCOMES")
        track_a_complete = abs(track_a_weight - track_a_expected) < 1e-9 and track_a_expected > 0
        track_b_complete = live_testing_ran and abs(track_b_weight - track_b_expected) < 1e-9 and track_b_expected > 0
        track_a_score = round(track_a_sum / track_a_weight, 1) if track_a_complete else None
        track_b_score = round(track_b_sum / track_b_weight, 1) if track_b_complete else None
        measured_subset_score = round(weighted_sum / measured_weight, 1) if measured_weight > 0 else None

        coverage_pct = round(measured_weight * 100, 1)
        is_full = len(unmeasured) == 0
        published_score = round(weighted_sum, 1) if is_full else None

        if is_full:
            status = "FULL_ASSESSMENT"
            stmt = "Full assessment completed across both Content Readiness and Live Answer Outcomes."
        else:
            status = "PARTIAL_ASSESSMENT"
            track_a_text = f"{track_a_score}/100" if track_a_score is not None else "incomplete"
            stmt = (
                f"Partial assessment: {coverage_pct}% of weighting evaluated. "
                f"Track A Content Readiness is {track_a_text}. "
                "Track B Live Answer Outcomes are NOT_TESTED. "
                "The overall grade is withheld."
            )

        return AeoScorecardReport(
            overall_score=published_score,
            measured_subset_score=measured_subset_score,
            overall_grade=cls._grade(published_score),
            assessment_status=status,
            coverage_percentage=coverage_pct,
            track_a_readiness_score=track_a_score,
            track_b_live_score=track_b_score,
            is_live_tested=live_testing_ran,
            dimension_breakdown=dim_results,
            unmeasured_dimensions=unmeasured,
            firewall_disclosure_statement=stmt,
        )
