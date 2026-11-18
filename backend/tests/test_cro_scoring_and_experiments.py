"""
Tests for Phase 6.9 & 6.10: Experimentation Engine & 10-Dimension Scorecard.
"""
import pytest
from app.cro.experimentation_engine import ExperimentationEngine
from app.cro.scoring import CroScoringEngine, DimensionEvidenceClass


def test_experimentation_engine_power_calculation():
    # Baseline conversion rate 3%, MDE 15%, alpha 0.05, power 0.80
    sample_size = ExperimentationEngine.calculate_sample_size(
        baseline_cr=0.03,
        relative_mde=0.15,
        alpha=0.05,
        power=0.80,
    )
    assert sample_size > 5000
    assert sample_size < 50000

    experiments = ExperimentationEngine.generate_experiments([], domain="example.com")
    assert len(experiments) >= 3
    assert experiments[0].minimum_duration_days >= 14
    assert "p-value < 0.05" in experiments[0].success_criteria


def test_ten_dimension_scorecard_calibration():
    # 10 Dimensions @ 10% each
    score_res = CroScoringEngine.evaluate(
        value_prop_score=85.0,
        visual_score=90.0,
        cta_score=80.0,
        journey_defects_count=0,
        form_score=85.0,
        mobile_defects_count=0,
        a11y_score=90.0,
        trust_score=80.0,
        checkout_score=85.0,
        analytics_connected=False,
    )

    assert len(score_res.dimensions) == 10
    assert all(d.weight_pct == 10.0 for d in score_res.dimensions)

    # Check evidence classes
    dim_classes = {d.id: d.evidence_class for d in score_res.dimensions}
    assert dim_classes["value_prop"] == DimensionEvidenceClass.HEURISTIC
    assert dim_classes["visual_hierarchy"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["cta_effectiveness"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["nav_journey"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["forms_leadgen"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["mobile_ux"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["accessibility"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["trust_credibility"] == DimensionEvidenceClass.HEURISTIC
    assert dim_classes["checkout_friction"] == DimensionEvidenceClass.AUTOMATED
    assert dim_classes["behavioral_analytics"] == DimensionEvidenceClass.ANALYTICS

    # Analytics is unmeasured
    analytics_card = next(d for d in score_res.dimensions if d.id == "behavioral_analytics")
    assert analytics_card.status == "UNMEASURED"
    assert analytics_card.score is None
    assert score_res.unmeasured_dimensions_count == 1
    assert score_res.measured_dimensions_count == 9
    assert score_res.overall_cro_score >= 80.0
