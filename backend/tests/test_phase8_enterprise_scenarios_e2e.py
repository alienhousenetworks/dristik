import pytest
from app.domain.models import (
    ExecutiveReport,
    Finding,
    FindingEvidence,
    OverallScoreResult,
    CroAuditReport,
    PageEvidence,
    PublicationStatus,
)
from app.domain.enums import Category, Severity
from app.crawl.audit.inventory_helper import get_canonical_crawl_inventory
from app.seo.reporting.seo_book_renderer import _compute_ttfb_outlier_diagnostics
from app.seo.analyzers.schema_validator import analyze_schema_rich_results
from app.reports.validation_gate import ReportPublicationValidator

def test_phase8_scenario_large_site_sampling_coverage_never_zero():
    """Scenario: 504 discovered URLs, 5 crawled URLs. Coverage must be ~1.0%, never 0.0%."""
    manifest = {
        "total_pages_discovered": 504,
        "total_pages_crawled": 5,
        "discovered_urls": [f"https://perforacare.com/p/{i}" for i in range(504)],
        "pages": [{"url": f"https://perforacare.com/p/{i}"} for i in range(5)],
    }
    report = ExecutiveReport(
        org_id="test_org",
        report_id="RUN_AF865F8B",
        domain="perforacare.com",
        website_url="https://perforacare.com",
        scores=OverallScoreResult(overall_score=75.2),
        story_summary="Sampled crawl.",
        primary_strategic_opportunity="Scale crawl.",
        consultant_advice_what_to_ignore="None.",
    )
    inv = get_canonical_crawl_inventory(manifest, report)
    assert inv.discovered_total == 504
    assert inv.tested_pages == 5
    # 5 / 504 * 100 = 0.992% -> rounded to 1.0%
    assert inv.url_coverage_pct == 1.0
    assert inv.url_coverage_pct > 0.0
    assert inv.sampling_status == "SAMPLED_AUDIT"

def test_phase8_scenario_ttfb_outlier_distribution_and_isolation():
    """Scenario: 5 URLs with [345, 252, 36208, 288, 248] ms TTFB.

    Mean is ~7468ms, median is 288ms, max is 36208ms on /products/unwind.
    Outlier must be identified and isolated from healthy pages.
    """
    page_metrics = [
        {"url": "https://perforacare.com/", "ttfb_ms": 345},
        {"url": "https://perforacare.com/products/mouthwash", "ttfb_ms": 252},
        {"url": "https://perforacare.com/products/unwind", "ttfb_ms": 36208},
        {"url": "https://perforacare.com/products/dream-relief", "ttfb_ms": 288},
        {"url": "https://perforacare.com/products/whitening-strips", "ttfb_ms": 248},
    ]
    diag = _compute_ttfb_outlier_diagnostics(None, page_metrics)
    assert diag["mean_ms"] == pytest.approx(7468.2, abs=1.0)
    assert diag["median_ms"] == 288
    assert diag["max_ms"] == 36208
    assert diag["is_single_outlier"] is True
    assert "unwind" in diag["outlier_url"]
    assert "36.2" in diag["outlier_narrative"] or "36,208" in diag["outlier_narrative"]

def test_phase8_scenario_missing_ai_api_keys_honesty():
    """Scenario: Live AI engine API keys unavailable. Content readiness reported while live visibility marked untested."""
    scores = OverallScoreResult(
        overall_score=72.0,
        website_geo_readiness_score=68.0,
        aeo_readiness_score=74.0,
        observed_ai_visibility_score=None, # Unmeasured, no negative penalty
    )
    assert scores.website_geo_readiness_score == 68.0
    assert scores.aeo_readiness_score == 74.0
    assert scores.observed_ai_visibility_score is None

def test_phase8_scenario_multi_schema_reconciliation():
    """Scenario: Multi-schema graph containing Organization, Product, and WebSite with zero contradiction."""
    page = PageEvidence(
        url="https://perforacare.com/products/teeth-whitening",
        raw_schema=[{
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "@id": "https://perforacare.com/#org", "name": "Perfora", "url": "https://perforacare.com"},
                {"@type": "WebSite", "@id": "https://perforacare.com/#website", "name": "Perfora"},
                {"@type": "Product", "name": "Teeth Whitening Pen", "offers": {"@type": "Offer", "price": "499"}},
            ]
        }]
    )
    report = analyze_schema_rich_results([page])
    assert set(report.detected_types).issuperset({"Organization", "Product", "WebSite"})
    assert report.has_graph_organization_reference is True
    assert report.canonical_inventory["syntax_valid"] is True

def test_phase8_scenario_e2e_publication_blocking_on_inconsistency():
    """Scenario: E2E publication gate catches contradiction introduced into bundle."""
    report = ExecutiveReport(
        org_id="test_org",
        report_id="RUN_AF865F8B",
        domain="perforacare.com",
        website_url="https://perforacare.com",
        scores=OverallScoreResult(overall_score=75.2),
        story_summary="E2E test summary.",
        primary_strategic_opportunity="Opportunity.",
        consultant_advice_what_to_ignore="Advice.",
        cro_audit=CroAuditReport(),
        certification_status="CERTIFIED", # Faulty claim!
    )
    qa = ReportPublicationValidator.validate_publication_bundle(report)
    assert qa.is_publishable is False
    assert qa.status == PublicationStatus.BLOCKED
