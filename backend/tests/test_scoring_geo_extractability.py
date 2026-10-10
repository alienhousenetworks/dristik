"""GEO category score follows measured extractability, not an unmatched rubric pass."""
from types import SimpleNamespace

from app.domain.enums import BusinessIntent, Category
from app.domain.models import BusinessProfile, CategoryScore, OverallScoreResult
from app.scoring.displayed_score import displayed_composite
from app.scoring.engine import ScoringEngine


def _profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Acme Systems",
        industry="Enterprise SaaS",
        value_proposition="Autonomous Edge Security",
        primary_cta="Schedule Demo",
        primary_intent=BusinessIntent.LEAD_GENERATION,
    )


def _scores(weight: float, weighted: float) -> OverallScoreResult:
    return OverallScoreResult(
        overall_score=82.7,
        grade="B",
        health_label="Good",
        category_scores={
            "GEO": CategoryScore(
                category=Category.GEO,
                score=100.0,
                weight=weight,
                weighted_score=weighted,
                summary="100/100 based on rubric checks.",
                status="MEASURED",
            ),
        },
        mathematical_derivation=[{
            "category": "GEO",
            "raw_score": 100.0,
            "weighted_points": weighted,
            "status": "MEASURED",
        }],
    )


def test_extractability_replaces_perfect_geo_and_recomputes_overall():
    engine = ScoringEngine()
    scores = _scores(weight=0.2, weighted=20.0)
    engine.apply_measured_geo_score(scores, 52.7)
    assert scores.category_scores["GEO"].score == 52.7
    assert scores.category_scores["GEO"].weighted_score == 10.54
    assert scores.category_scores["GEO"].provenance == "GEO_EXTRACTABILITY"
    assert scores.overall_score == 73.2
    assert scores.grade == "C"
    assert scores.mathematical_derivation[0]["raw_score"] == 52.7
    engine.apply_measured_geo_score(scores, 52.7)
    assert scores.overall_score == 73.2


def test_percent_weight_uses_the_same_points():
    engine = ScoringEngine()
    scores = _scores(weight=20.0, weighted=20.0)
    engine.apply_measured_geo_score(scores, 52.7)
    assert scores.category_scores["GEO"].weighted_score == 10.54
    assert scores.overall_score == 73.2


def test_honest_readiness_uses_extractability_not_the_rubric_pass():
    engine = ScoringEngine()
    geo = SimpleNamespace(extractability_score=52.7, questions_total=6, questions_supported=3)
    honest = engine.calculate_honest_scores(
        findings=[],
        business_profile=_profile(),
        geo_readiness=geo,
    )
    assert honest.ai_readiness_score == 51.6


def test_displayed_composite_matches_the_dossier_cover():
    composite = displayed_composite({
        "scores": {"overall_score": 82.7, "category_scores": {"GEO": {"score": 100, "status": "MEASURED"}}},
        "honest_scores": {
            "google_score": 79.6,
            "ai_readiness_score": 80,
            "human_score": 76.6,
            "live_ai_citation_score": 0,
            "ai_visibility_status": "MEASURED",
            "ai_visibility_score": 0,
        },
        "geo_readiness": {"extractability_score": 52.7},
    })
    assert composite == 52.4
