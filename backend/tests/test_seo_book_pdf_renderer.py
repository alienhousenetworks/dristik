"""
Unit and Integration Tests for Dristik SEO Audit Book Renderer.
Verifies:
1. Standardized 17-field finding contract normalization.
2. Conditional chapter activation (ecommerce, local, international).
3. Full Jinja2 HTML rendering with zero-fabrication disclosures.
4. XSS auto-escaping for untrusted crawler and finding data.
5. Two-pass Playwright/Chromium pagination and bookmark injection.
6. API endpoint integration with /reports/{analysis_id}/seo-report.
"""
import pytest
from unittest.mock import AsyncMock, patch

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
from app.seo.reporting.seo_book_renderer import (
    CORE_CHAPTERS,
    SeoAuditBookRenderer,
    build_seo_book_context,
    is_chapter_applicable,
    normalize_finding,
    seo_audit_book_renderer,
)


def _make_test_report(
    domain: str = "example.com",
    is_ecommerce: bool = False,
    is_local: bool = False,
    is_international: bool = False,
) -> ExecutiveReport:
    """Creates a sample executive report for testing."""
    profile = BusinessProfile(
        domain=domain,
        business_name="Acme Corp",
        business_model="ecommerce" if is_ecommerce else "b2b_service",
        industry="Retail" if is_ecommerce else "Professional Services",
        niche="Online Store" if is_ecommerce else "Legal Consulting",
    )

    finding1 = Finding(
        finding_id="SEO-001",
        category=Category.TECHNICAL_SEO,
        subcategory="Robots Directives",
        severity=Severity.CRITICAL,
        priority=10,
        title="Disallow directive blocks search crawlers from main catalog",
        description="robots.txt contains 'Disallow: /catalog/' which blocks all Googlebot indexing.",
        root_cause="Staging robots.txt accidentally promoted to production server.",
        expected_condition="Robots.txt permits crawl access to /catalog/* paths.",
        recommendation="Remove the disallow line from edge robots.txt configuration.",
        why_it_matters="Stops search engines from discovering and ranking over 1,200 product pages.",
        business_impact="Direct organic traffic suppression and potential lead drop.",
        validation_criteria="Live robots.txt validator returns 200 OK for /catalog/index.",
        affected_urls=["https://example.com/catalog/1", "https://example.com/catalog/2"],
        status=FindingStatus.OPEN,
    )

    finding2 = Finding(
        finding_id="SEO-002",
        category=Category.SCHEMA,
        subcategory="Structured Data",
        severity=Severity.HIGH,
        priority=8,
        title="Missing Product availability schema node",
        description="Product schema omitted ItemAvailability JSON-LD declaration.",
        recommendation="Inject schema.org/InStock on all available SKUs.",
        why_it_matters="Loss of rich snippet badges and pricing in Google SERPs.",
        validation_criteria="Google Rich Results validator returns 0 errors.",
        affected_urls=["https://example.com/catalog/1"],
        status=FindingStatus.IN_PROGRESS,
    )

    finding_xss = Finding(
        finding_id="SEO-003",
        category=Category.ON_PAGE_SEO,
        subcategory="Heading Hierarchy",
        severity=Severity.LOW,
        priority=3,
        title="Unescaped Heading Tag <script>alert('xss')</script>",
        description="Found untrusted content <img src=x onerror=alert(1)> in heading.",
        why_it_matters="Heading tag formatting error.",
        recommendation="Sanitize template variables.",
        affected_urls=["https://example.com/page?query=<script>alert('xss')</script>"],
        status=FindingStatus.OPEN,
    )

    pages = [
        PageReport(url="https://example.com/", title="Home — Acme Corp", status_code=200, is_indexable=True),
        PageReport(url="https://example.com/catalog/1", title="Catalog Page 1", status_code=200, is_indexable=True),
    ]

    return ExecutiveReport(
        report_id="DST-TEST-001",
        analysis_id="test-run-123",
        website_url=f"https://{domain}",
        domain=domain,
        generated_at="2026-10-15T12:00:00Z",
        business_profile=profile,
        scores=OverallScoreResult(
            overall_score=78.5,
            grade="B+",
            health_label="Good",
        ),
        story_summary="Acme Corp shows robust technical infrastructure with isolated crawl directive blockers.",
        primary_strategic_opportunity="Unlock catalog search indexing and inject schema nodes for rich snippets.",
        consultant_advice_what_to_ignore="Ignore minor low-priority meta keywords tags.",
        what_site_gets_right=["SSL encryption is active across all endpoints", "Canonical tags are self-referential"],
        what_is_holding_it_back=["Robots.txt blocks search engines from reading product catalog"],
        findings=[finding1, finding2, finding_xss],
        page_reports=pages,
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Fast loading, clean layout.",
            search_engine_perspective="Crawlable, but shallow internal link equity.",
            ai_answer_engine_perspective="Clear entity definition, low information gain.",
        ),
    )


class TestFindingNormalization:
    """Tests the 17-field data contract normalization."""

    def test_normalize_finding_fields(self):
        report = _make_test_report()
        finding = report.findings[0]
        normalized = normalize_finding(finding, 1)

        assert normalized["id"] == "SEO-001"
        assert "catalog" in normalized["title"].lower()
        assert normalized["priority"] == "Critical"
        assert normalized["scope_status"] == "SAMPLE_VERIFIED"
        assert normalized["lifecycle_status"] == "Open"
        assert "blocks all googlebot" in normalized["observed_result"].lower()
        assert "stops search engines" in normalized["plain_english_summary"].lower()
        assert "direct organic traffic" in normalized["business_impact"].lower()
        assert len(normalized["affected_urls"]) == 2
        assert "remove the disallow line" in normalized["recommended_action"].lower()
        assert len(normalized["verification_steps"]) > 0
        assert normalized["confidence"] == "High"
        assert normalized["expected_outcome"] is not None

    def test_normalize_handles_minimal_dict(self):
        minimal = {
            "title": "Minimal Defect",
            "severity": "high",
        }
        normalized = normalize_finding(minimal, 5)
        assert normalized["id"] == "SEO-005"
        assert normalized["title"] == "Minimal Defect"
        assert normalized["priority"] == "High"
        assert normalized["lifecycle_status"] == "Open"
        assert isinstance(normalized["affected_urls"], list)
        assert isinstance(normalized["verification_steps"], list)


class TestConditionalChapters:
    """Tests intelligent conditionality of the master SEO index."""

    def test_ecommerce_chapter_activation(self):
        ecom_chapter = next(ch for ch in CORE_CHAPTERS if ch["id"] == "sec-ecommerce-seo")
        
        # Non-ecommerce report
        report_service = _make_test_report(is_ecommerce=False)
        assert not is_chapter_applicable(ecom_chapter, report_service)

        # Ecommerce report
        report_ecom = _make_test_report(is_ecommerce=True)
        assert is_chapter_applicable(ecom_chapter, report_ecom)

    def test_always_active_chapters(self):
        tech_chapter = next(ch for ch in CORE_CHAPTERS if ch["id"] == "sec-technical-seo")
        report = _make_test_report()
        assert is_chapter_applicable(tech_chapter, report)


class TestTemplateRendering:
    """Tests Jinja2 rendering of seo_audit_book.html and finding partials."""

    def test_render_html_report_contains_core_sections(self):
        report = _make_test_report(is_ecommerce=True)
        renderer = SeoAuditBookRenderer()
        html = renderer.render_html_report(report)

        # Cover page
        assert "Comprehensive SEO Audit" in html
        assert report.domain in html
        assert report.analysis_id in html

        # Reader guide
        assert "How to Read This Report" in html
        assert "Every finding has two layers" in html

        # Table of Contents
        assert "Table of Contents" in html
        assert 'class="toc-list"' in html

        # Executive summary
        assert "Executive Summary" in html
        assert "Pages inspected" in html

        # SEO Health & Pillars
        assert "SEO Health and Scoring Methodology" in html
        assert "Technical Infrastructure" in html

        # Findings register & partial
        assert 'class="finding"' in html
        assert "SEO-001" in html
        assert "What does this mean in simple English?" in html

        # Appendices
        assert "Appendix A" in html
        assert "Evidence Register" in html
        assert "Appendix B" in html
        assert "SEO Glossary for Business Owners" in html
        assert "Appendix C" in html
        assert "Methodology, Scope and Limitations" in html

    def test_autoescape_prevents_xss_injection(self):
        report = _make_test_report()
        renderer = SeoAuditBookRenderer()
        html = renderer.render_html_report(report)

        # Verify raw script tags are escaped
        assert "<script>alert('xss')</script>" not in html
        assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in html or "&lt;script&gt;alert('xss')&lt;/script&gt;" in html
        assert "<img src=x onerror=alert(1)>" not in html


class TestTwoPassPaginationAndPdf:
    """Tests two-pass pagination workflow and PDF bookmarking."""

    @pytest.mark.asyncio
    async def test_two_pass_render_invokes_browser_twice(self):
        report = _make_test_report()
        renderer = SeoAuditBookRenderer()

        mock_render_fn = AsyncMock()
        # Mock Pass 1 returning dummy PDF with chapter markers (> 100 bytes)
        mock_pdf_pass1 = b"%PDF-1.4 dummy content [[chapter_ref:sec-technical-seo]] [[chapter_ref:roadmap]]" + (b" " * 150)
        mock_pdf_pass2 = b"%PDF-1.4 final rendered publication pdf bytes" + (b" " * 150)
        mock_render_fn.side_effect = [mock_pdf_pass1, mock_pdf_pass2]

        pdf_result = await renderer.render_book_pdf(report, render_fn=mock_render_fn, two_pass=True)

        assert mock_render_fn.call_count == 2
        assert pdf_result is not None
        assert len(pdf_result) > 10

    def test_resolve_physical_pages_fallback(self):
        renderer = SeoAuditBookRenderer()
        ch_ids = ["sec-technical-seo", "sec-onpage-seo", "roadmap"]
        resolved = renderer.resolve_physical_pages(b"", ch_ids)

        assert len(resolved) == 3
        assert resolved["sec-technical-seo"] == 3
        assert resolved["sec-onpage-seo"] == 5
        assert resolved["roadmap"] == 7


class TestApiRouteIntegration:
    """Tests /reports/{analysis_id}/seo-report FastAPI integration."""

    def test_api_endpoint_format_print_returns_book_html(self):
        from starlette.testclient import TestClient
        from app.reports.pdf_generator import router
        from fastapi import FastAPI
        from app.identity.deps import get_current_user
        from app.identity.authorizer import UserIdentity

        app = FastAPI()
        app.include_router(router)

        app.dependency_overrides[get_current_user] = lambda: UserIdentity(
            user_id="usr_test",
            email="test@dristik.com",
            org_id="org_test",
            role="admin",
        )

        sample_report = _make_test_report()

        class MockAnalysisRun:
            def __init__(self):
                self.analysis_id = "test-analysis-101"
                self.report = sample_report

        with patch("app.reports.pdf_generator.require_analysis", return_value=MockAnalysisRun()):
            client = TestClient(app)
            response = client.get("/reports/test-analysis-101/seo-report?format=html")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "Comprehensive SEO Audit" in response.text
            assert "Acme Corp" in response.text
            assert "Table of Contents" in response.text
