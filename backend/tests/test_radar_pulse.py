"""
Unit tests for Dristik AI Radar Service & Monthly Citation Pulse
"""
import pytest
from app.intelligence.monitoring.radar import RadarService, radar_service

def test_create_radar_subscription():
    """Verify subscription creation with domain parsing and default saved prompts."""
    service = RadarService()
    sub = service.create_subscription(
        target_url="https://saascloud.io",
        org_id="org_test",
        plan_id="monthly_pulse"
    )
    assert sub.domain == "saascloud.io"
    assert sub.plan_id == "monthly_pulse"
    assert sub.status == "active"
    assert len(sub.saved_prompts) == 5
    assert "saascloud.io" in sub.saved_prompts[0]
    # Fresh subscription has no fake baseline scores
    assert sub.last_scores == {}

    # Explicit initial scores are preserved when provided
    sub_with_scores = service.create_subscription(
        target_url="https://saascloud.io",
        initial_scores={"human": 68.0}
    )
    assert sub_with_scores.last_scores["human"] == 68.0

def test_run_pulse_check_with_dom_changes_and_score_gains():
    """Verify pulse diff detection when H1 is modified, schema is added, and citation scores jump."""
    service = RadarService()
    sub = service.create_subscription(
        target_url="https://growthexample.com",
        initial_scores={"human": 60.0, "google": 65.0, "ai_citation": 50.0},
        initial_snapshot={
            "h1": "Welcome to GrowthExample",
            "title": "GrowthExample Home",
            "meta_description": "Our software",
            "has_schema": False
        }
    )

    # Run pulse after patch deployment
    diff = service.run_pulse_check(
        subscription_id=sub.subscription_id,
        current_snapshot={
            "h1": "Automated Revenue Attribution for Modern B2B SaaS",
            "title": "GrowthExample | Automated Revenue Attribution",
            "meta_description": "Accurately measure multi-touch marketing pipeline.",
            "has_schema": True
        },
        new_scores={"human": 78.0, "google": 85.0, "ai_citation": 82.0}
    )

    # Check score deltas
    assert diff.score_deltas["human"] == 18.0
    assert diff.score_deltas["google"] == 20.0
    assert diff.score_deltas["ai_citation"] == 32.0

    # Check DOM change-log
    changes = {c["field"]: c for c in diff.dom_changes}
    assert "H1 Heading" in changes
    assert changes["H1 Heading"]["status"] == "MODIFIED"
    assert "Schema.org JSON-LD" in changes
    assert changes["Schema.org JSON-LD"]["status"] == "ADDED"

    # Check digest
    assert "Monthly Citation Pulse Delta for growthexample.com:" in diff.executive_delta_digest
    assert "+32.0%" in diff.executive_delta_digest

def test_detect_citability_regression():
    """Verify detection of negative citability delta and regression alert firing."""
    service = RadarService()
    sub = service.create_subscription(
        target_url="https://regresstest.com",
        initial_scores={"human": 85.0, "google": 88.0, "ai_citation": 80.0},
        initial_snapshot={"h1": "Established Leader", "has_schema": True}
    )

    # Regression scenario: Schema dropped, citation score drops
    diff = service.run_pulse_check(
        subscription_id=sub.subscription_id,
        current_snapshot={"h1": "Established Leader", "has_schema": False},
        new_scores={"human": 85.0, "google": 78.0, "ai_citation": 62.0}
    )

    assert diff.score_deltas["ai_citation"] == -18.0
    assert diff.alert_severity in ("HIGH", "CRITICAL")
    assert any(c["status"] == "REMOVED" for c in diff.dom_changes)
