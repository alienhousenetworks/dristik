from pathlib import Path

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


def test_seo_section_pdf_includes_the_full_index():
    html = section_report_generator.render_section_html(_mock_report(), "seo")
    for title in (
        "01. Executive summary",
        "16. Core Web Vitals and page speed",
        "47. AI search visibility and citation intelligence",
        "55. Monitoring, governance and ongoing SEO operations",
        "O. Glossary",
    ):
        assert title in html
    assert "Largest Contentful Paint (LCP)" in html
    assert "Googlebot and other crawler access differences" in html
    assert "Google AI Overviews and AI Mode" in html
    assert "representative sample" in html.lower()
    assert html.count("<h4>") >= 70
    crawl = section_report_generator.render_section_html(_mock_report(), "crawl")
    assert "Complete SEO report index" not in crawl
    frontend_index = Path(__file__).resolve().parents[2] / "frontend/src/report/auditIndex/catalog.json"
    backend_index = Path(__file__).resolve().parents[1] / "app/reports/seo_audit_index.json"
    assert frontend_index.read_text(encoding="utf-8") == backend_index.read_text(encoding="utf-8")


def test_section_pptx_generation():
    rep = _mock_report()
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        pptx_bytes, blueprint = generate_section_pptx_deck(rep, sec)
        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 1000
        assert blueprint.total_slides > 0


def test_section_html_generation_with_category_score_objects():
    from app.domain.models import CategoryScore, Category
    rep = _mock_report()
    rep.scores.category_scores = {
        "TECHNICAL_SEO": CategoryScore(
            category=Category.TECHNICAL_SEO,
            score=82.4,
            summary="Strong technical foundation.",
        ),
        "GEO": CategoryScore(
            category=Category.GEO,
            score=68.0,
            summary="GEO extractability measured.",
        ),
        "UX_CONVERSION": CategoryScore(
            category=Category.UX_CONVERSION,
            score=74.5,
            summary="UX conversion measured.",
        ),
    }
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        html = section_report_generator.render_section_html(rep, sec)
        assert html is not None
        assert "example.com" in html
        assert "<html" in html
        assert "</html>" in html

