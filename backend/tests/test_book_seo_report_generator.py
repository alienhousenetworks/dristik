"""
Unit and Integration Tests for Publication-Grade Book-Style SEO Report Generator
Verifies:
1. Cover page layout, branding, metadata grid, and print styling
2. Dynamic Table of Contents with all 20 chapters, dot leaders, anchor links, and page numbers
3. Chapter-based pagination, running headers/footers, and A4 print CSS
4. Data-grounded chapter content, SVG gauges, and zero-fake disclosures across all 20 sections
5. API endpoints for format=print and format=pdf integration
"""
import pytest
from app.domain.enums import Category, FindingStatus, Severity
from app.domain.models import (
    BusinessProfile,
    EcommerceSeoAuditReport,
    ExecutiveReport,
    Finding,
    HttpStatusBreakdown,
    IndexationAuditRollup,
    OverallScoreResult,
    PageReport,
    SerpAppearanceReport,
    ThreeWayComparison,
)
from app.reports.seo_print_report import (
    SeoPrintReportRenderer,
    calculate_chapter_page_numbers,
    render_svg_donut_chart,
    render_svg_score_gauge,
)
from app.reports.seo_report_generator import CompleteSeoReportGenerator, seo_report_generator


def _make_sample_report(ecommerce_detected: bool = True) -> ExecutiveReport:
    """Creates a sample executive report for testing."""
    finding_p0 = Finding(
        finding_id="F-P0-001",
        category=Category.TECHNICAL_SEO,
        subcategory="Indexation Blockers",
        severity=Severity.CRITICAL,
        priority=10,
        title="Critical Robots Disallow on Product Catalog",
        finding_title="Critical Robots Disallow on Product Catalog",
        description="robots.txt blocks Googlebot from crawling all /catalog/* endpoints.",
        detailed_diagnosis="robots.txt blocks Googlebot from crawling all /catalog/* endpoints.",
        root_cause="Staging robots.txt configuration accidentally promoted to production.",
        expected_condition="Disallow: /catalog/ removed; catalog open to all crawlers.",
        recommended_solution="Modify robots.txt on edge CDN to allow /catalog/ paths.",
        why_it_matters="Search engines cannot index over 5,000 product pages, causing 90% organic loss.",
        acceptance_criteria="Live robots.txt validator returns 200 OK for /catalog/items.",
        verification_method="Automated HTTP robots.txt tester.",
        relevant_code_or_configuration_example="User-agent: *\nDisallow: /admin/\nAllow: /catalog/",
        implementation_steps=["Access Cloudflare Workers", "Update robots.txt routing rule", "Deploy and test"],
        owner="DevOps",
        effort=2,
        impact=10,
        affected_sample_count=50,
        affected_urls=["https://example.com/catalog/1", "https://example.com/catalog/2"],
        status=FindingStatus.OPEN,
    )

    finding_p1 = Finding(
        finding_id="F-P1-002",
        category=Category.SCHEMA,
        subcategory="Product Schema",
        severity=Severity.HIGH,
        priority=8,
        title="Missing InStock Availability Schema",
        description="Product schema omitted required availability property.",
        root_cause="Template lacked stock quantity check.",
        expected_condition="schema.org/InStock declared on all purchasable SKUs.",
        recommended_solution="Inject ItemAvailability JSON-LD node.",
        why_it_matters="Loss of rich snippet stock badge in Google SERP.",
        acceptance_criteria="Google Rich Results validator returns 0 errors.",
        verification_method="DOM JSON-LD validation assertion.",
        owner="Frontend Team",
        effort=3,
        impact=7,
        status=FindingStatus.IN_PROGRESS,
    )

    finding_p2 = Finding(
        finding_id="F-P2-003",
        category=Category.CONTENT,
        subcategory="Thin Content",
        severity=Severity.MEDIUM,
        priority=5,
        title="Thin Content Under 150 Words on Tag Pages",
        description="Tag archive pages contain minimal unique copy.",
        expected_condition="Tag pages have unique 100-word intro summaries or noindex.",
        recommended_solution="Add descriptive category copy.",
        acceptance_criteria="Word count assertion >150 words.",
        owner="Content Marketing",
        status=FindingStatus.FIXED,
    )

    finding_p3 = Finding(
        finding_id="F-P3-004",
        category=Category.TECHNICAL_SEO,
        subcategory="Image Optimization",
        severity=Severity.LOW,
        priority=3,
        title="Legacy PNG Format on Hero Carousel",
        description="Hero carousel uses uncompressed 1.2MB PNG images.",
        expected_condition="Images served as WebP or AVIF <150KB.",
        recommended_solution="Compress hero assets with squoosh.",
        acceptance_criteria="Header image payload <150KB.",
        owner="Design",
        status=FindingStatus.VERIFIED,
    )

    page_1 = PageReport(
        url="https://example.com",
        title="Example Enterprise Platform | Complete Visibility",
        meta_description="Example provides enterprise search intelligence, automated diagnostics, and SEO governance.",
        status_code=200,
        word_count=1200,
        h1_tags=["Enterprise Search Intelligence"],
        schema_types=["Organization", "WebSite"],
        ttfb_ms=180.0,
    )

    ecom_report = EcommerceSeoAuditReport(
        is_ecommerce_detected=ecommerce_detected,
        status="WARNING" if ecommerce_detected else "NOT_APPLICABLE",
        products_analyzed=120 if ecommerce_detected else 0,
        product_schema_compliance_pct=75.0 if ecommerce_detected else 0.0,
        faceted_urls_found=18 if ecommerce_detected else 0,
        summary="120 product URLs audited with 25% schema omissions." if ecommerce_detected else "Non-ecommerce site.",
    )

    serp_report = SerpAppearanceReport(
        status="COMPLIANT",
        total_urls_evaluated=1,
        titles_truncated_count=0,
        descriptions_truncated_count=0,
        rich_snippets_supported_count=1,
        rich_snippet_readiness_pct=100.0,
        summary="All titles compliant with 580px desktop boundary.",
    )

    return ExecutiveReport(
        report_id="DRS-2026-TEST",
        analysis_id="analysis_book_001",
        website_url="https://example.com",
        domain="example.com",
        generated_at="May 24, 2026",
        business_profile=BusinessProfile(business_name="Example Corp"),
        scores=OverallScoreResult(overall_score=78.4, grade="C+", health_label="Fair"),
        story_summary="The website demonstrates a solid technical foundation with strong indexability. However, there are significant opportunities in content depth, internal linking, and structured data.",
        what_site_gets_right=["Good crawlability", "HTTPS secured", "Mobile responsive", "Clean URL structure"],
        what_is_holding_it_back=["Thin content pages", "Missing schema markup", "Internal linking gaps", "Cannibalization issues"],
        primary_strategic_opportunity="Expand topical authority and optimize for AI search (GEO/AEO) to capture emerging traffic channels.",
        consultant_advice_what_to_ignore="Ignore superficial meta keyword tags.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Fast loading, clean layout.",
            search_engine_perspective="Crawlable, but shallow internal link equity.",
            ai_answer_engine_perspective="Clear entity definition, low information gain.",
        ),
        findings=[finding_p0, finding_p1, finding_p2, finding_p3],
        page_reports=[page_1],
        crawl_summary={"total_pages_crawled": 1248, "avg_ttfb_ms": 195.0},
        ecommerce_seo=ecom_report,
        serp_appearance=serp_report,
        indexation_intelligence=IndexationAuditRollup(
            indexed_count=1142,
            noindex_count=96,
            blocked_by_robots_count=32,
        ),
        http_status_breakdown=HttpStatusBreakdown(
            count_200=1140,
            count_301=60,
            count_404=26,
            count_500=15,
            count_other=7,
        ),
    )


def test_book_cover_rendering():
    """Validates the dedicated book cover page structure and metadata."""
    report = _make_sample_report()
    html_out = seo_report_generator.render_print_html_report(report)

    # Must contain book-cover section
    assert '<section class="book-cover">' in html_out
    assert "DRISTIK AI" in html_out
    assert "ENTERPRISE INTELLIGENCE ADVISORY" in html_out
    assert "Complete SEO Master Audit &amp; Remediation Report" in html_out
    assert "TECHNICAL &bull; CONTENT &bull; AUTHORITY &bull; GEO &bull; CRO" in html_out
    assert "PREPARED FOR" in html_out
    assert "example.com" in html_out
    assert "REPORT REFERENCE" in html_out
    assert "DRS-2026-TEST" in html_out
    assert "DOCUMENT CLASSIFICATION" in html_out
    assert "CONFIDENTIAL" in html_out
    assert "SEE WHAT OTHERS MISS" in html_out

    # Must not contain web dashboard elements like sidebar
    assert '<aside class="sidebar">' not in html_out


def test_table_of_contents_all_20_chapters():
    """Validates Table of Contents lists all 20 chapters with dot leaders and resolved page references."""
    report = _make_sample_report()
    html_out = seo_report_generator.render_print_html_report(report)

    assert '<section id="table-of-contents" class="toc">' in html_out
    assert "Table of Contents" in html_out

    # All 20 sections must be represented in TOC
    for sec_id, sec_title in CompleteSeoReportGenerator.SECTIONS:
        assert f'href="#{sec_id}"' in html_out
        assert sec_id.replace("sec-", "") in html_out

    # Check dot leaders and page elements
    assert 'class="toc-dots"' in html_out
    assert 'class="toc-page"' in html_out


def test_custom_page_numbers_override():
    """Validates passing explicit page_numbers dictionary reflects in TOC references."""
    report = _make_sample_report()
    custom_pages = {sec_id: (i * 4 + 1) for i, (sec_id, _) in enumerate(CompleteSeoReportGenerator.SECTIONS)}
    html_out = seo_report_generator.render_print_html_report(report, page_numbers=custom_pages)

    # sec-01 custom start page is 1 -> 01
    assert '<span class="toc-page">01</span>' in html_out
    # sec-02 custom start page is 5 -> 05
    assert '<span class="toc-page">05</span>' in html_out


def test_chapter_pagination_and_headers():
    """Validates that each chapter starts on a new page with proper headers and footers."""
    report = _make_sample_report()
    html_out = seo_report_generator.render_print_html_report(report)

    # 20 chapter-start sections
    chapter_count = html_out.count('class="chapter-start report-section"')
    assert chapter_count == 20

    # Running headers and footers
    assert '<div class="page-running-header">' in html_out
    assert '<div class="page-running-footer">' in html_out
    assert "Enterprise Intelligence Advisory" in html_out


def test_a4_print_css_rules():
    """Validates print-specific CSS rules for A4 paper and margins."""
    report = _make_sample_report()
    html_out = seo_report_generator.render_print_html_report(report)

    assert "@page {" in html_out
    assert "size: A4;" in html_out
    assert "@page :first {" in html_out
    assert "margin: 0;" in html_out
    assert "break-before: page;" in html_out
    assert "break-inside: avoid;" in html_out


def test_data_grounded_chapters():
    """Validates chapters render real report data rather than generic placeholders."""
    report = _make_sample_report(ecommerce_detected=True)
    html_out = seo_report_generator.render_print_html_report(report)

    # Section 01: Score & 3-column takeaways
    assert "Site Health Score" in html_out
    assert "78" in html_out
    assert "Good crawlability" in html_out
    assert "Thin content pages" in html_out
    assert "Expand topical authority" in html_out

    # Section 02: 4-Layer Architecture & Inventory
    assert "2.1 Our 4-Layer Epistemic Integrity Architecture" in html_out
    assert "Machine Observations" in html_out
    assert "Deterministic Rules" in html_out
    assert "Derived Intelligence" in html_out
    assert "Grounded Prescriptions" in html_out
    assert "Dristik Zero-Fake Evidence Governance" in html_out

    # Section 03: Indexability & HTTP Donut
    assert "1142" in html_out  # Indexed pages
    assert "HTTP Status Breakdown" in html_out
    assert "200 OK" in html_out

    # Section 14: E-commerce detected
    assert "120" in html_out  # Products analyzed
    assert "75.0%" in html_out  # Schema compliance

    # Section 16: External Authority NOT_CONNECTED disclosure
    assert "External Authority Status: NOT_CONNECTED" in html_out
    assert "No authenticated external backlink intelligence API" in html_out

    # Section 19: Prioritized Roadmap P0-P3
    assert "F-P0-001" in html_out
    assert "Critical Robots Disallow on Product Catalog" in html_out
    assert "P0 Critical" in html_out
    assert "7 Days &bull; Quick Wins" in html_out

    # Section 20: 5-Stage Lifecycle Protocol
    assert "5-Stage Continuous Assurance Protocol" in html_out
    assert "Fixed is not the same as Verified" in html_out


def test_ecommerce_not_applicable_disclosure():
    """Validates that non-ecommerce sites display explicit NOT_APPLICABLE status."""
    report = _make_sample_report(ecommerce_detected=False)
    html_out = seo_report_generator.render_print_html_report(report)

    assert "E-commerce SEO &amp; Product Architecture: NOT_APPLICABLE" in html_out
    assert "Target website does not exhibit transactional product catalog" in html_out


def test_svg_chart_renderers():
    """Validates SVG donut and score gauge generators produce valid vector markup."""
    gauge = render_svg_score_gauge(85.0, size=140)
    assert '<svg width="140"' in gauge
    assert "85" in gauge
    assert "#10b981" in gauge

    donut = render_svg_donut_chart([("A", 10, "#ff0000"), ("B", 20, "#00ff00")], size=120)
    assert '<svg width="120"' in donut
    assert "30" in donut


def test_api_endpoint_format_print():
    """Validates API route handles format=print returning publication-grade print HTML and format=pdf download."""
    import sys
    from unittest.mock import MagicMock, patch
    if "bs4" not in sys.modules:
        sys.modules["bs4"] = MagicMock()

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.reports.pdf_generator import router
    from app.identity.deps import get_current_user
    from app.identity.authorizer import UserIdentity

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    mock_user = UserIdentity(id="u1", user_id="u1", email="test@example.com", org_id="org1", role="admin")
    mock_run = MagicMock()
    mock_run.report = _make_sample_report()
    mock_run.org_id = "org1"
    mock_run.analysis_id = "analysis_book_001"
    mock_run.domain = "example.com"
    mock_run.website_url = "https://example.com"

    test_app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch("app.reports.pdf_generator.require_analysis", return_value=mock_run):
        client = TestClient(test_app)
        res_print = client.get("/api/v1/reports/analysis_book_001/seo-report?format=print")
        assert res_print.status_code == 200
        assert "text/html" in res_print.headers["content-type"]
        assert "book-cover" in res_print.text
        assert "Table of Contents" in res_print.text
        assert "chapter-start" in res_print.text
        assert "screen-toolbar" in res_print.text
        assert "Print / Save as PDF" in res_print.text
        assert "Download PDF File" in res_print.text

        with patch("app.crawl.browser.BrowserRenderService.render_pdf", return_value=b"%PDF-1.4 mock"):
            res_pdf = client.get("/api/v1/reports/analysis_book_001/seo-report?format=pdf&download=true")
            assert res_pdf.status_code == 200
            assert res_pdf.headers["content-type"] == "application/pdf"
            assert "attachment;" in res_pdf.headers["content-disposition"]
            assert res_pdf.content == b"%PDF-1.4 mock"


def test_external_authority_list_coverage_safety():
    """Validates that external_authority with list coverage (e.g. from _unavailable) does not raise AttributeError."""
    report = _make_sample_report()
    # Case 1: Standard _unavailable() payload where coverage is an empty list
    report.external_authority = {
        "title": "External Authority & Entity Intelligence",
        "coverage": [],
        "findings": [],
        "pillars": {},
        "sections": {},
        "notes": ["External authority was not attached."],
    }
    html_out = seo_report_generator.render_print_html_report(report)
    assert "External Authority Status: NOT_CONNECTED" in html_out

    # Case 2: external_authority with active measured providers list
    report.external_authority = {
        "title": "External Authority & Entity Intelligence",
        "status": "CONNECTED",
        "coverage": [
            {"provider": "ahrefs", "connection_status": "CONNECTED", "data_state": "MEASURED"}
        ],
        "metrics": {
            "domain_authority": 72,
            "referring_domains": 1420,
            "total_backlinks": 45800,
            "toxic_link_ratio_pct": 2.1,
        },
    }
    html_out_conn = seo_report_generator.render_print_html_report(report)
    assert "72" in html_out_conn
    assert "1420" in html_out_conn

    # Case 3: external_authority set to unexpected raw list
    report.external_authority = ["some_unexpected_list_data"]  # type: ignore[assignment]
    html_out_list = seo_report_generator.render_print_html_report(report)
    assert "External Authority Status: NOT_CONNECTED" in html_out_list

