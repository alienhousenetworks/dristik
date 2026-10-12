"""Unit & Integration Tests for Enterprise Edition GEO Audit Book (50 Chapters + 15 Appendices).
"""
from pathlib import Path
import pytest

from app.reports.section_exports import section_report_generator
from app.reports.geo_audit_book import geo_cover_figure, render_geo_audit_book
from app.agents.runtime.registry import list_geo_specialists, get_agent_definition
from app.domain.models import (
    ExecutiveReport,
    BusinessProfile,
    OverallScoreResult,
    Finding,
    PageReport,
    GeoReadinessReport,
    AiVisibilityScorecard,
    ThreeWayComparison,
)

def _mock_geo_report() -> ExecutiveReport:
    page = PageReport(
        url="https://example.com",
        title="Example Cloud Platform",
        meta_description="Enterprise cloud data platform.",
        status_code=200,
        word_count=1200,
        h1_tags=["Enterprise Cloud Data Platform"],
        schema_types=["Organization", "SoftwareApplication", "FAQPage"],
        ttfb_ms=180.0,
    )
    return ExecutiveReport(
        report_id="rep_geo_001",
        analysis_id="analysis_geo_001",
        website_url="https://example.com",
        domain="example.com",
        generated_at="2026-10-12T12:00:00Z",
        business_profile=BusinessProfile(business_name="Example Corp", industry="Cloud Data"),
        page_reports=[page],
        scores=OverallScoreResult(
            overall_score=78.0,
            overall_grade="B",
            grade="B",
            health_label="FAIR",
            geo_score=82,
        ),
        geo_readiness=GeoReadinessReport(
            entity_name="Example Corp",
            headline="Strong technical extractability with comparison passage opportunities.",
            extractability_score=82.0,
            questions_total=10,
            questions_supported=7,
            questions_partial=2,
            questions_unsupported=1,
            schema_types=["Organization", "SoftwareApplication", "FAQPage"],
        ),
        ai_visibility_scorecard=AiVisibilityScorecard(
            status="MEASURED",
            successful_runs=5,
            engines_queried=["ChatGPT Search", "Perplexity", "Google AI Overviews"],
            surfaces_not_queried=["Bing Copilot", "Claude"],
            mention_rate_pct=80.0,
            citation_rate_pct=60.0,
            competitor_visibility_pct=40.0,
            hallucination_rate_pct=0.0,
        ),
        story_summary="Comprehensive Generative Engine Optimization intelligence audit.",
        what_site_gets_right=["Clean server rendering and valid JSON-LD entity graph."],
        what_is_holding_it_back=["Direct tabular comparison passages on commercial prompts."],
        primary_strategic_opportunity="Publish objective head-to-head comparison matrices.",
        consultant_advice_what_to_ignore="Ignore vanity keyword volume without conversational intent.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition.",
            search_engine_perspective="Valid crawl structure.",
            ai_answer_engine_perspective="Citable definitions.",
        ),
        findings=[
            Finding(
                finding_id="GEO-001",
                category="CONTENT",
                severity="HIGH",
                title="Missing Tabular Comparison Matrix on Pricing Page",
                description="The pricing page lacks structured HTML tables comparing tier features.",
                recommendation="Deploy semantic HTML <table> element with machine-readable feature rows.",
                affected_urls=["https://example.com/pricing"],
            ),
            Finding(
                finding_id="GEO-002",
                category="AI_SEARCH",
                severity="MEDIUM",
                title="Low Third-Party Corroboration on High-Intent Solution Queries",
                description="Perplexity cites competitor G2 profiles rather than brand references.",
                recommendation="Accelerate G2 and Trustpilot review collection campaigns.",
                affected_urls=["https://example.com"],
            ),
        ],
    )

def test_geo_specialist_agents_registered():
    specialists = list_geo_specialists()
    assert len(specialists) == 18
    expected_ids = [
        "geo.benchmark_orchestrator.v3",
        "geo.prompt_discovery.v3",
        "geo.brand_mention.v3",
        "geo.recommendation_intelligence.v3",
        "geo.citation_intelligence.v3",
        "geo.citation_gap.v3",
        "geo.brand_hallucination.v3",
        "geo.entity_consistency.v3",
        "geo.technical_auditor.v3",
        "geo.crawler_diagnostics.v3",
        "geo.offsite_evidence.v3",
        "geo.competitive_analyst.v3",
        "geo.measurement_analyst.v3",
        "geo.referral_analyst.v3",
        "geo.remediation_planner.v3",
        "geo.verification_engine.v3",
    ]
    for agent_id in expected_ids:
        defn = get_agent_definition(agent_id)
        assert defn is not None
        assert defn.domain == "GEO"
        assert len(defn.capabilities) > 0

def test_catalog_json_parity():
    backend_catalog = Path(__file__).resolve().parents[1] / "app/reports/geo_audit_index.json"
    frontend_catalog = Path(__file__).resolve().parents[2] / "frontend/src/report/geoIndex/catalog.json"
    assert backend_catalog.exists()
    assert frontend_catalog.exists()
    assert backend_catalog.read_text(encoding="utf-8") == frontend_catalog.read_text(encoding="utf-8")

def test_render_geo_audit_book_contains_all_50_sections_and_15_appendices():
    report = _mock_geo_report()
    html = render_geo_audit_book(report)

    # All 50 numbered sections
    for i in range(1, 51):
        num_str = f"{i:02d}."
        assert num_str in html, f"Section {num_str} missing in rendered GEO audit book"

    # All 15 Appendices A-O
    for letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"]:
        sec_str = f"{letter}."
        assert sec_str in html, f"Appendix {sec_str} missing in rendered GEO audit book"

    # Key architectural assertions
    assert "2026 ENTERPRISE GEO MASTER STANDARD" in html
    assert "agent-consulting-dossier" in html
    assert "SPECIALIST AGENT // geo." in html
    assert "Authoritative Diagnostic Review &amp; Strategy" in html
    assert "Architecture Breakdown &amp; Retrieval Mechanics" in html
    assert "Prescriptive Engineering &amp; Content Fix" in html
    assert "Post-Fix Verification &amp; Regression Testing" in html
    assert "Sub-Index Evidence &amp; Verification Ledger" in html
    assert "Multi-Dimensional GEO Assessment" in html
    assert "Master Table of Contents" in html
    assert "Page " in html

    # Finding cards
    assert "GEO-001" in html
    assert "Missing Tabular Comparison Matrix on Pricing Page" in html

def test_section_report_generator_wires_geo_book():
    report = _mock_geo_report()
    html = section_report_generator.render_section_html(report, "geo")
    assert "example.com" in html
    assert "FULL GEO INDEX // SECTIONS 01–50 AND APPENDICES A–O" in html
    assert "01. Executive GEO Summary" in html
    assert "50. Continuous Monitoring and Governance" in html
    assert "O. Change history and audit reproducibility manifest" in html
    assert "SPECIALIST AGENT" in html

def test_geo_cover_figure():
    report = _mock_geo_report()
    assert geo_cover_figure(report) == 82
