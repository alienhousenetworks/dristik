import pytest
from app.domain.models import ScoreDefinition, ScoreResult, OverallScoreResult, CategoryScore
from app.domain.enums import Category

def test_phase3_score_definition_and_result():
    """Verify standard ScoreDefinition and ScoreResult models."""
    sd = ScoreDefinition(
        metric_id="geo_extractability",
        name="GEO Content Extractability & AI Grounding",
        discipline="GEO",
        formula="weighted_mean(schema_clarity, passage_density, factual_consistency)",
        weights={"schema_clarity": 0.35, "passage_density": 0.35, "factual_consistency": 0.30},
        required_tests=["schema_graph", "passage_extraction"],
        minimum_coverage=0.60,
    )
    assert sd.metric_id == "geo_extractability"
    assert sd.discipline == "GEO"
    assert sd.weights["schema_clarity"] == 0.35

    sr = ScoreResult(
        id="SR_GEO_01",
        audit_run_id="RUN_AF865F8B",
        metric_id="geo_extractability",
        score=66.5,
        status="MEASURED",
        coverage=1.0,
        confidence="HIGH",
        evidence_ids=["ev_101", "ev_102"],
        formula_version="v5.1",
    )
    assert sr.score == 66.5
    assert sr.metric_id == "geo_extractability"
    assert sr.status == "MEASURED"

def test_phase3_separate_geo_aeo_and_ai_visibility_dimensions():
    """Verify GEO extractability, AEO readiness, and Observed AI Visibility are distinct non-blended scores."""
    scores = OverallScoreResult(
        overall_score=75.2,
        website_geo_readiness_score=66.5,     # Internal site extractability
        observed_ai_visibility_score=12.0,    # External live citations/mentions
        aeo_readiness_score=78.0,             # Content question-answer completeness
        cro_score=None,                       # Unmeasured - missing analytics/browser forms
        formula_version="dristik_central_scoring_v5.1",
    )
    # The dimensions MUST NOT be conflated
    assert scores.website_geo_readiness_score == 66.5
    assert scores.observed_ai_visibility_score == 12.0
    assert scores.aeo_readiness_score == 78.0
    assert scores.cro_score is None

def test_phase3_unmeasured_score_policy_never_zeros():
    """Unmeasured score remains None, never replaced with 0.0 without evidence."""
    sr_unmeasured = ScoreResult(
        id="SR_CRO_01",
        audit_run_id="RUN_AF865F8B",
        metric_id="cro_conversion_rate",
        score=None,
        status="UNMEASURED",
        limitations=["GA4 analytics connector not connected."],
    )
    assert sr_unmeasured.score is None
    assert sr_unmeasured.status == "UNMEASURED"
    assert len(sr_unmeasured.limitations) > 0
