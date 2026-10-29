"""
Tests for Phase 4: Website Digital Twin, Search Intent Graph, and Temporal Timeline.
"""
import pytest
from app.intelligence.business.website_twin import WebsiteDigitalTwin
from app.intelligence.business.intent_graph import SearchIntentGraph
from app.intelligence.monitoring.timeline import WebsiteIntelligenceTimeline
from app.domain.models import BusinessProfile, PageEvidence, OverallScoreResult, Finding, CategoryScore
from app.domain.enums import Category, Severity

def test_digital_twin_update():
    twin = WebsiteDigitalTwin(
        twin_id="twin_01",
        domain="example.com",
        base_url="https://example.com"
    )
    bp = BusinessProfile(
        business_name="Example Inc",
        niche="Cloud AI",
        primary_cta="Start Free Trial"
    )
    pages = [
        PageEvidence(url="https://example.com/", title="Home", schema_types=["Organization"]),
        PageEvidence(url="https://example.com/pricing", title="Pricing", page_type="pricing")
    ]
    findings = [
        Finding(
            finding_id="f1",
            category=Category.TECHNICAL_SEO,
            severity=Severity.MEDIUM,
            title="Title too short",
            description="Fix title",
            recommendation="Add descriptive keywords"
        )
    ]

    scores = OverallScoreResult(
        overall_score=85.0,
        grade="A",
        health_label="Excellent"
    )

    twin.update_from_mission(bp, pages, scores, findings, [])
    assert twin.pages_count == 2
    assert "Organization" in twin.entities
    assert len(twin.conversion_paths) == 2
    assert twin.overall_health.grade == "A"

def test_search_intent_graph_broken_paths():
    intent_graph = SearchIntentGraph()
    bp = BusinessProfile(business_name="Acme", niche="DevOps Tools", primary_cta="Get Started")
    # Website with no pricing page
    pages = [PageEvidence(url="https://acme.com/", title="Home")]

    paths = intent_graph.construct_intent_paths(bp, pages)
    assert len(paths) == 3

    pricing_path = next(p for p in paths if p.path_id == "intent_01_pricing")
    assert pricing_path.status == "BROKEN_NO_PAGE"
    assert pricing_path.revenue_risk == "CRITICAL"

def test_website_timeline_delta():
    timeline = WebsiteIntelligenceTimeline("example.com")
    score1 = OverallScoreResult(overall_score=70.0, grade="C", health_label="Moderate")
    score2 = OverallScoreResult(overall_score=86.0, grade="A", health_label="Excellent")

    f1 = Finding(finding_id="f1", category=Category.SCHEMA, severity=Severity.HIGH, title="Missing Schema", description="", recommendation="")
    f2 = Finding(finding_id="f2", category=Category.TECHNICAL_SEO, severity=Severity.LOW, title="Minor Alt Text", description="", recommendation="")

    timeline.record_audit("audit_01", score1, [f1])
    timeline.record_audit("audit_02", score2, [f2])

    delta = timeline.compute_delta()
    assert delta is not None
    assert delta.score_change == 16.0
    assert "improved" in delta.summary
