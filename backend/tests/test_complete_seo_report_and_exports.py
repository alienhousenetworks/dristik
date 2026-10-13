"""
Unit & Integration Tests for Complete SEO Report & CSV Exports (2026 Master Standard)
"""
import pytest
from app.domain.enums import Category, FindingStatus, Severity
from app.domain.models import (
    BusinessProfile,
    EcommerceSeoAuditReport,
    ExecutiveReport,
    Finding,
    OverallScoreResult,
    PageEvidence,
    PageReport,
    SerpAppearanceReport,
    ThreeWayComparison,
)
from app.analyzers.ecommerce_seo import analyze_ecommerce_seo
from app.analyzers.serp_appearance import analyze_serp_appearance
from app.reports.export_service import generate_urls_csv, generate_remediation_tracker_csv
from app.reports.seo_report_generator import seo_report_generator


def _make_dummy_report() -> ExecutiveReport:
    """Helper to build a valid ExecutiveReport fixture."""
    page_1 = PageReport(
        url="https://acme.com",
        title="Acme Corp - Enterprise Cloud & Security Architecture Solutions For Modern Companies",
        meta_description="Acme provides enterprise cloud software, devops tooling, and scalable cybersecurity automation systems for high-growth global teams.",
        status_code=200,
        word_count=850,
        h1_tags=["Enterprise Cloud Architecture Solutions"],
        schema_types=["Organization", "BreadcrumbList"],
        ttfb_ms=210.0,
    )
    page_2 = PageReport(
        url="https://acme.com/products/security-suite",
        title="Security Suite | Acme",
        meta_description="Comprehensive security suite for cloud monitoring.",
        status_code=200,
        word_count=450,
        h1_tags=["Security Suite"],
        schema_types=["Product"],
        ttfb_ms=190.0,
    )

    finding_1 = Finding(
        finding_id="FIND-TECH-001",
        category=Category.SCHEMA,
        subcategory="Product Schema Gaps",
        affected_urls=["https://acme.com/products/security-suite"],
        expected_condition="All product pages must have complete price, currency, and availability schema.",
        dependencies=["Theme JSON-LD Template"],
        status=FindingStatus.OPEN,
        owner="Engineering",
        severity=Severity.HIGH,
        title="Missing Product Offer Schema Properties",
        description="Product is missing priceCurrency and availability fields.",
        recommendation="Add priceCurrency and availability to Product JSON-LD.",
        why_it_matters="Search engines will omit price badges and rich snippet cards.",
        validation_criteria="Google Rich Result test passes with 0 missing properties.",
        priority=8,
        impact=8,
        effort=3,
    )

    return ExecutiveReport(
        report_id="rep_test_001",
        analysis_id="analysis_test_001",
        website_url="https://acme.com",
        domain="acme.com",
        generated_at="October 10, 2026 - 02:00 UTC",
        business_profile=BusinessProfile(business_name="Acme Corp"),
        scores=OverallScoreResult(overall_score=84.5, grade="B", health_label="Good"),
        story_summary="Acme Corp shows strong technical foundations with high-impact schema opportunities.",
        primary_strategic_opportunity="Enrich JSON-LD schemas and optimize title pixel widths.",
        consultant_advice_what_to_ignore="Ignore superficial meta keyword tags.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition.",
            search_engine_perspective="Clean crawl indexability.",
            ai_answer_engine_perspective="Good entity structure.",
        ),
        findings=[finding_1],
        page_reports=[page_1, page_2],
        crawl_summary={"total_pages_crawled": 2, "avg_ttfb_ms": 200.0},
        ecommerce_seo=EcommerceSeoAuditReport(
            is_ecommerce_detected=True,
            status="WARNING",
            products_analyzed=1,
            product_schema_compliance_pct=0.0,
            faceted_urls_found=0,
            summary="1 product analyzed with schema omissions.",
        ),
        serp_appearance=SerpAppearanceReport(
            status="WARNING",
            total_urls_evaluated=2,
            titles_truncated_count=1,
            descriptions_truncated_count=0,
            rich_snippets_supported_count=1,
            rich_snippet_readiness_pct=50.0,
            summary="1 title exceeds desktop 580px boundary.",
        ),
    )


def test_ecommerce_analyzer_non_ecommerce():
    pages = [
        PageEvidence(
            url="https://blog.example.com/about",
            title="About Us",
            body_text="We write tech blogs.",
            schema_types=["AboutPage"],
        )
    ]
    rep, findings = analyze_ecommerce_seo(pages, "blog.example.com")
    assert not rep.is_ecommerce_detected
    assert rep.status == "NOT_APPLICABLE"
    assert len(findings) == 0


def test_ecommerce_analyzer_detects_products_and_faceted_traps():
    pages = [
        PageEvidence(
            url="https://store.example.com/products/shoes",
            title="Running Shoes",
            schema_types=["Product"],
            raw_schema=[
                {
                    "@type": "Product",
                    "name": "Super Running Shoe",
                    # missing offers, price, currency
                }
            ],
            internal_links=[
                "https://store.example.com/products/shoes?sort=price&color=blue"
            ],
        )
    ]
    rep, findings = analyze_ecommerce_seo(pages, "store.example.com")
    assert rep.is_ecommerce_detected
    assert rep.products_analyzed == 1
    assert len(rep.products_with_issues) == 1
    assert "offers" in rep.products_with_issues[0].missing_fields
    assert len(rep.faceted_traps) >= 1
    assert len(findings) >= 1


def test_serp_appearance_analyzer():
    pages = [
        PageEvidence(
            url="https://example.com/very-long-title",
            title="This Is An Extremely Long Title That Definitely Exceeds The Five Hundred And Eighty Pixel Limit On Google Desktop SERP",
            meta_description="A good meta description.",
            schema_types=["BreadcrumbList"],
        ),
        PageEvidence(
            url="https://example.com/short",
            title="Short Title",
            meta_description="A brief description.",
            schema_types=[],
        ),
    ]
    rep, findings = analyze_serp_appearance(pages, "example.com")
    assert rep.total_urls_evaluated == 2
    assert rep.titles_truncated_count >= 1
    assert rep.rich_snippets_supported_count >= 1
    assert len(findings) >= 1
    assert any(f.finding_id == "FINDING-SERP-001" for f in findings)


def test_export_service_csvs():
    rep = _make_dummy_report()
    urls_csv = generate_urls_csv(rep)
    assert "URL,Status Code,Indexability Status,Canonical URL" in urls_csv
    assert "https://acme.com" in urls_csv
    assert "https://acme.com/products/security-suite" in urls_csv

    tracker_csv = generate_remediation_tracker_csv(rep)
    assert "Finding ID,Category,Subcategory,Severity,Status (Lifecycle)" in tracker_csv
    assert "FIND-TECH-001" in tracker_csv
    assert "Theme JSON-LD Template" in tracker_csv
    assert "Google Rich Result test passes" in tracker_csv


def test_complete_seo_report_generator_html():
    rep = _make_dummy_report()
    html_output = seo_report_generator.render_html_report(rep)

    # Check 20-Section Master Index presence
    for i in range(1, 21):
        sec_num = f"{i:02d}."
        assert sec_num in html_output, f"Missing section number {sec_num} in HTML output"

    # Check Key UI Components
    assert "Complete SEO Master Audit: acme.com" in html_output
    assert "Fixed is not the same as Verified" in html_output
    assert "FIND-TECH-001" in html_output
    assert "/api/v1/reports/analysis_test_001/export/urls.csv" in html_output
    assert "/api/v1/reports/analysis_test_001/export/remediation-tracker.csv" in html_output


def test_complete_seo_report_generator_json():
    rep = _make_dummy_report()
    json_output = seo_report_generator.render_json_report(rep)

    assert json_output["report_id"] == "rep_test_001"
    assert json_output["domain"] == "acme.com"
    assert "sections" in json_output
    secs = json_output["sections"]
    assert "01_executive_summary" in secs
    assert "02_methodology_and_scope" in secs
    assert "08_structured_data_and_schema" in secs
    assert "14_ecommerce_seo" in secs
    assert "15_serp_appearance" in secs
    assert "19_prioritized_roadmap" in secs
    assert "20_verification_lifecycle" in secs
    assert secs["20_verification_lifecycle"]["rule"].startswith("Fixed is not the same as Verified")


def test_seo_report_and_exports_api_endpoints():
    """Verify FastAPI router endpoints for seo-report (HTML/JSON) and CSV exports."""
    import sys
    from unittest.mock import MagicMock
    if "bs4" not in sys.modules:
        sys.modules["bs4"] = MagicMock()

    from fastapi.testclient import TestClient
    from app.main import app
    from app.orchestration.orchestrator import orchestrator

    import uuid
    client = TestClient(app)
    signup = client.post("/api/v1/auth/signup", json={
        "full_name": "SEO Owner",
        "email": f"seo_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OwnerPass1",
        "organization_name": "SEO Org",
    })
    assert signup.status_code == 200, signup.text
    mock_run = MagicMock()
    mock_run.report = _make_dummy_report()
    mock_run.org_id = signup.json()["user"]["org_id"]
    mock_run.analysis_id = "analysis_test_001"
    mock_run.created_at = "2026-10-10"
    mock_run.domain = "acme.com"
    mock_run.website_url = "https://acme.com"

    original_get_run = orchestrator.get_run
    orchestrator.get_run = MagicMock(return_value=mock_run)

    try:
        # 1. Complete SEO Report in HTML
        res_html = client.get("/api/v1/reports/analysis_test_001/seo-report")
        assert res_html.status_code == 200
        assert "text/html" in res_html.headers["content-type"]
        assert "01. Executive Summary" in res_html.text
        assert "20. Verification Protocol" in res_html.text
        assert "Fixed is not the same as Verified" in res_html.text

        # 2. Complete SEO Report in JSON
        res_json = client.get("/api/v1/reports/analysis_test_001/seo-report?format=json")
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["report_id"] == "rep_test_001"
        assert "01_executive_summary" in data["sections"]
        assert "20_verification_lifecycle" in data["sections"]

        # 3. URLs CSV Export
        res_urls_csv = client.get("/api/v1/reports/analysis_test_001/export/urls.csv")
        assert res_urls_csv.status_code == 200
        assert "text/csv" in res_urls_csv.headers["content-type"]
        assert 'filename="acme.com_urls.csv"' in res_urls_csv.headers["content-disposition"]
        assert "URL,Status Code,Indexability Status" in res_urls_csv.text

        # 4. Remediation Tracker CSV Export
        res_tracker_csv = client.get("/api/v1/reports/analysis_test_001/export/remediation-tracker.csv")
        assert res_tracker_csv.status_code == 200
        assert "text/csv" in res_tracker_csv.headers["content-type"]
        assert 'filename="acme.com_remediation_tracker.csv"' in res_tracker_csv.headers["content-disposition"]
        assert "Finding ID,Category,Subcategory,Severity" in res_tracker_csv.text
        assert "FIND-TECH-001" in res_tracker_csv.text
    finally:
        orchestrator.get_run = original_get_run

