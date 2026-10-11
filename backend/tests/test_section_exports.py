import pytest
from app.reports.section_exports import section_report_generator
from app.agents.deck.coordinator import generate_section_pptx_deck
from app.domain.models import ExecutiveReport, BusinessProfile, OverallScoreResult, ThreeWayComparison, Finding


def _mock_report() -> ExecutiveReport:
    return ExecutiveReport(
        report_id="rep_test_001",
        analysis_id="run_test_001",
        website_url="https://example.com",
        domain="example.com",
        generated_at="2026-10-11T12:00:00Z",
        business_profile=BusinessProfile(business_name="Example Corp"),
        scores=OverallScoreResult(
            overall_score=75.0,
            overall_grade="B",
            grade="B",
            health_label="FAIR",
            seo_score=78,
            geo_score=70,
            aeo_score=72,
            cro_score=76,
        ),
        story_summary="Comprehensive digital intelligence audit.",
        primary_strategic_opportunity="Optimize structured data.",
        consultant_advice_what_to_ignore="Ignore vanity metrics.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition.",
            search_engine_perspective="Valid crawl structure.",
            ai_answer_engine_perspective="Citable definitions.",
        ),
        findings=[
            Finding(
                finding_id="f_01",
                category="TECHNICAL_SEO",
                severity="HIGH",
                title="Sitemap missing",
                description="XML sitemap was not discovered during crawl.",
                evidence_id="ev_001",
                recommendation="Publish sitemap.xml",
            ),
            Finding(
                finding_id="f_02",
                category="UX_CONVERSION",
                severity="MEDIUM",
                title="CTA above the fold",
                description="Hero fold lacks high-contrast action button.",
                evidence_id="ev_002",
                recommendation="Add CTA button",
            ),
        ],
    )


def test_section_html_generation():
    rep = _mock_report()
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        html = section_report_generator.render_section_html(rep, sec)
        assert html is not None
        assert "example.com" in html
        assert "<html" in html
        assert "</html>" in html


def test_section_pptx_generation():
    rep = _mock_report()
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        pptx_bytes, blueprint = generate_section_pptx_deck(rep, sec)
        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 1000
        assert blueprint.total_slides > 0
