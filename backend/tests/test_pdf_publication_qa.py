"""Tests for Phase 3: SVG Vector Charts & Enterprise Adaptive Audit Book HTML/PDF."""
from app.domain.models import BusinessProfile, ExecutiveReport, Finding, OverallScoreResult, ThreeWayComparison
from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
from app.reports.svg_charts import SvgChartRenderer


def test_svg_chart_renderer_generates_radar_and_severity_bars():
    radar = SvgChartRenderer.render_category_radar_svg({
        "TECHNICAL_SEO": 84.0,
        "ON_PAGE_SEO": 72.5,
        "CONTENT": 90.0,
        "GEO": 65.0,
        "AI_SEARCH": 58.0,
        "SCHEMA": 77.0,
        "UX_CONVERSION": 81.0,
        "TRUST_AUTHORITY": 70.0,
    })
    assert "<svg" in radar
    assert "Technical (84)" in radar
    assert "AI Search (58)" in radar

    bars = SvgChartRenderer.render_severity_bar_svg([
        {"severity": "CRITICAL"},
        {"severity": "HIGH"},
        {"severity": "HIGH"},
        {"severity": "MEDIUM"},
    ])
    assert "<svg" in bars
    assert "CRITICAL" in bars
    assert ">2<" in bars


def test_adaptive_audit_book_embeds_vector_charts():
    rep = ExecutiveReport(
        report_id="rep_svg_001",
        analysis_id="analysis_svg_001",
        org_id="org_test",
        website_url="https://acme-analytics.io",
        domain="acme-analytics.io",
        generated_at="2026-10-12T14:30:00Z",
        business_profile=BusinessProfile(business_name="Acme Analytics"),
        scores=OverallScoreResult(
            overall_score=80.0,
            overall_grade="A-",
            grade="A-",
            health_label="STRONG",
            seo_score=85,
            geo_score=78,
            aeo_score=80,
            cro_score=86,
            category_scores={
                "TECHNICAL_SEO": {"category": "TECHNICAL_SEO", "score": 85.0, "weight": 0.15},
                "ON_PAGE_SEO": {"category": "ON_PAGE_SEO", "score": 78.0, "weight": 0.10},
                "CONTENT": {"category": "CONTENT", "score": 82.0, "weight": 0.15},
                "GEO": {"category": "GEO", "score": 76.0, "weight": 0.15},
                "AI_SEARCH": {"category": "AI_SEARCH", "score": 70.0, "weight": 0.15},
                "SCHEMA": {"category": "SCHEMA", "score": 79.0, "weight": 0.10},
                "UX_CONVERSION": {"category": "UX_CONVERSION", "score": 86.0, "weight": 0.10},
                "TRUST_AUTHORITY": {"category": "TRUST_AUTHORITY", "score": 74.0, "weight": 0.10},
            },
        ),
        story_summary="Acme Analytics has strong technical foundations with citation gaps.",
        primary_strategic_opportunity="Deploy Schema.org SoftwareApplication graph.",
        consultant_advice_what_to_ignore="Ignore staging subdomains.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear hero value proposition.",
            search_engine_perspective="200 OK across core pages.",
            ai_answer_engine_perspective="Needs concise FAQ definitions.",
        ),
        findings=[
            Finding(
                finding_id="f_01",
                category="TECHNICAL_SEO",
                severity="CRITICAL",
                title="Missing canonical on /pricing",
                description="No canonical link.",
                evidence_id="ev_001",
                recommendation="Add canonical link.",
            )
        ],
    )
    html_doc = render_adaptive_audit_book_html(rep)
    assert "CANONICAL 8-CATEGORY RADAR" in html_doc
    assert "VERIFIED FINDING SEVERITY DISTRIBUTION" in html_doc
    assert "<svg" in html_doc
