"""Tests for mathematical scoring transparency, scorecard formula breakdowns, and finding deductions."""
import pytest
from app.domain.enums import Category, Severity, BusinessIntent
from app.domain.models import BusinessProfile, Finding
from app.scoring.engine import ScoringEngine


def test_scoring_mathematical_derivation_and_formula_breakdowns():
    engine = ScoringEngine()
    profile = BusinessProfile(
        primary_intent=BusinessIntent.LEAD_GENERATION,
        offering_type="B2B Services",
        target_audience="Enterprise CTOs",
    )

    findings = [
        Finding(
            finding_id="find_001",
            category=Category.CONTENT,
            severity=Severity.HIGH,
            title="Duplicate metadata across landing pages",
            finding="Duplicate metadata detected.",
            description="Duplicate metadata damages SEO.",
            recommendation="Consolidate duplicate meta tags.",
            why_it_matters="Confuses search engines and search crawlers.",
        ),
        Finding(
            finding_id="find_002",
            category=Category.GEO,
            severity=Severity.CRITICAL,
            title="Poor answerability and missing entity schema",
            finding="Missing entity schema and direct answer formats.",
            description="Lacks structured answers.",
            recommendation="Add entity schema markup.",
            why_it_matters="Drastically reduces AI search engine extraction.",
        ),
    ]

    res = engine.calculate_scores(findings=findings, business_profile=profile)

    # 1. Overall score result contains mathematical_derivation
    assert res.mathematical_derivation is not None
    assert len(res.mathematical_derivation) == 8

    total_weighted_points = sum(row["weighted_points"] for row in res.mathematical_derivation)
    # Total weighted points should sum to overall_score
    assert round(total_weighted_points, 1) == round(res.overall_score, 1)

    # 2. Check each category has formula_breakdown and deductions
    for cat_name, cat_score in res.category_scores.items():
        assert cat_score.formula_breakdown is not None
        assert len(cat_score.formula_breakdown) > 0

        # Component points earned must sum to the category raw score
        breakdown_sum = sum(comp["points_earned"] for comp in cat_score.formula_breakdown)
        assert breakdown_sum == round(cat_score.score)

        # Check status field validity
        for comp in cat_score.formula_breakdown:
            assert comp["status"] in ("PASS", "PARTIAL", "DEFICIT", "PROVISIONAL_NEUTRAL")
            assert comp["points_possible"] > 0
            assert comp["points_earned"] <= comp["points_possible"]

    # 3. Check itemized deductions for penalized categories
    content_score = res.category_scores[Category.CONTENT.value]
    assert content_score.deductions is not None
    assert len(content_score.deductions) >= 1
    assert content_score.deductions[0]["finding_id"] == "find_001"
    assert content_score.deductions[0]["points_lost"] > 0
    assert content_score.deductions[0]["severity"] == "HIGH"

    geo_score = res.category_scores[Category.GEO.value]
    assert geo_score.deductions is not None
    assert len(geo_score.deductions) >= 1
    assert geo_score.deductions[0]["finding_id"] == "find_002"
    assert geo_score.deductions[0]["points_lost"] > 0
    assert geo_score.deductions[0]["severity"] == "CRITICAL"
