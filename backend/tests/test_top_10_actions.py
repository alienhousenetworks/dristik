"""Tests for Top 10 Actions executive roadmap generation."""
import pytest
from app.domain.enums import Category, Severity, BusinessIntent
from app.domain.models import BusinessProfile, Finding, OverallScoreResult
from app.reports.roadmap import RoadmapBuilder


def test_build_top_10_actions():
    builder = RoadmapBuilder()
    profile = BusinessProfile(
        primary_intent=BusinessIntent.LEAD_GENERATION,
        offering_type="B2B AI Platform",
    )

    findings = [
        Finding(
            finding_id="find_009",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="Homepage H1 does not communicate service category",
            finding="H1 is generic.",
            description="H1 lacks clear category statement.",
            recommendation="Rewrite homepage H1 positioning.",
        ),
        Finding(
            finding_id="find_014",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            title="Missing Service and Organization schema",
            finding="No schema found.",
            description="No structured data found in DOM.",
            recommendation="Add Service schema.",
        ),
    ]

    plan = builder.build_top_10_actions(
        findings=findings,
        business_profile=profile,
        scores=OverallScoreResult(
            overall_score=45.0,
            overall_confidence=0.9,
            evidence_coverage=0.85,
            grade="D",
            health_label="Needs Attention",
        ),
    )

    assert plan is not None
    assert len(plan.actions) == 10

    # Ranks 1 to 10
    ranks = [a.rank for a in plan.actions]
    assert ranks == list(range(1, 11))

    # Priority distribution contains P0, P1, P2
    priorities = {a.priority for a in plan.actions}
    assert "P0" in priorities
    assert "P1" in priorities
    assert "P2" in priorities

    # Check each action has impact, effort, expected outcome, hours, validation
    for action in plan.actions:
        assert action.action
        assert action.impact in ("Very High", "High", "Medium", "Low")
        assert action.effort in ("Low", "Medium", "High")
        assert action.expected_outcome
        assert action.estimated_engineer_hours > 0
        assert action.validation.startswith("Automated retest")

    # Check hours sum matches
    assert plan.total_engineer_hours == sum(a.estimated_engineer_hours for a in plan.actions)
    assert plan.total_engineer_hours > 20

    # Check dependencies flow
    assert "Define service taxonomy" in plan.dependencies_flow
    assert "Create service schema" in plan.dependencies_flow

    # Check finding link association
    positioning_action = next(a for a in plan.actions if "positioning" in a.action.lower())
    assert positioning_action.related_finding_id == "find_009"

    schema_action = next(a for a in plan.actions if "schema" in a.action.lower())
    assert schema_action.related_finding_id == "find_014"
