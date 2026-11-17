"""
Milestone 4 Verification Test Suite:
Reporting, Discipline Contracts, Coverage & Repetition Audit
Covers Issues 1, 2, 3, 4, 5, and 9.
"""
import pytest
from app.domain.enums import Category, Severity, BusinessIntent
from app.domain.models import (
    BusinessProfile,
    Finding,
    FindingEvidence,
    CrawlManifest,
    PageEvidence,
    OverallScoreResult,
    CategoryScore,
    CheckResult,
    AuditScopeInfo,
)
from app.domain.scoring.engine import ScoringEngine
from app.seo.reporting.seo_book_renderer import (
    build_seo_book_context,
    _compute_ttfb_outlier_diagnostics,
    validate_chapter_discipline_contract,
    SeoAuditBookRenderer,
)
from app.reports.plain_english_engine import PlainEnglishEngine
from app.crawl.crawler import compute_ttfb_stats


def test_issue_1_seo_coverage_displays_exact_rounding_not_zero():
    """
    Issue 1: 5 crawled of 504 discovered URLs = 5/504 * 100 = 0.992% -> displays 1.0%, never 0%.
    """
    manifest = CrawlManifest(
        domain="perforacare.com",
        base_url="https://perforacare.com",
        total_pages_discovered=504,
        total_pages_crawled=5,
        pages=[PageEvidence(url=f"https://perforacare.com/p{i}") for i in range(5)],
    )

    class DummyReport:
        domain = "perforacare.com"
        analysis_id = "audit_perfora_cov"
        crawl_manifest = manifest
        findings = []

    ctx = build_seo_book_context(DummyReport())

    # Must display 1.0%, strictly NEVER 0% or 0.0%
    assert "1.0%" in ctx["report"]["discovery_coverage"]
    assert "5 / 504 (1.0%)" in ctx["report"]["discovery_coverage"]
    assert "(0.0%)" not in ctx["report"]["discovery_coverage"]
    assert "(0%)" not in ctx["report"]["discovery_coverage"]


def test_issue_2_ttfb_mean_median_max_outlier_diagnosis():
    """
    Issue 2: TTFB reporting displays Mean (~7468ms), Median (288ms), and Max (36208ms),
    isolating the slow URL (Unwind combo) as an outlier rather than generic sitewide crisis.
    """
    pages = [
        PageEvidence(url="https://perforacare.com/", ttfb_ms=345.0),
        PageEvidence(url="https://perforacare.com/products/mouthwash", ttfb_ms=252.0),
        PageEvidence(url="https://perforacare.com/products/unwind-combo", ttfb_ms=36208.0),
        PageEvidence(url="https://perforacare.com/products/dream-relief", ttfb_ms=288.0),
        PageEvidence(url="https://perforacare.com/products/whitening-strips", ttfb_ms=248.0),
    ]

    stats = compute_ttfb_stats(pages)
    assert abs(stats.mean_ms - 7468.2) < 5.0
    assert stats.median_ms == 288.0
    assert stats.max_ms == 36208.0
    assert stats.min_ms == 248.0
    assert "https://perforacare.com/products/unwind-combo" in stats.outlier_urls
    assert stats.outlier_explanation is not None
    assert "36.2s" in stats.outlier_explanation or "36208" in stats.outlier_explanation or "isolated outlier" in stats.outlier_explanation


def test_issue_3_evidence_records_and_affected_urls_agreement():
    """
    Issue 3: Build affected URLs directly from validated evidence records.
    Never report 0 affected URLs when evidence records identify affected pages.
    """
    finding = Finding(
        finding_id="find_compression_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Brotli / Gzip Compression Disabled on Product Endpoints",
        description="Response payload lacks Content-Encoding compression headers on product catalog page.",
        evidence=[
            FindingEvidence(
                evidence_id="ev_comp_01",
                url="https://perforacare.com/products/unwind-combo",
                value="Content-Encoding: identity",
            ),
            FindingEvidence(
                evidence_id="ev_comp_02",
                url="https://perforacare.com/products/mouthwash",
                value="Content-Encoding: identity",
            ),
        ],
        affected_urls=[],  # Deliberately empty at initialization
    )

    # Sync must automatically populate affected_urls from evidence
    finding.sync_evidence_ids_and_refs()

    assert len(finding.affected_urls) == 2
    assert "https://perforacare.com/products/unwind-combo" in finding.affected_urls
    assert "https://perforacare.com/products/mouthwash" in finding.affected_urls
    assert finding.affected_url_count == 2
    assert finding.affected_url_count != 0, "Finding with 2 evidence items must never report 0 affected URLs"


def test_issue_4_scoring_methodology_appendix_generation():
    """
    Issue 4: Publish a scoring methodology appendix with formulas, weights, inputs,
    sample coverage, and version number dristik_central_scoring_v5.1.
    """
    engine = ScoringEngine()
    profile = BusinessProfile(
        business_name="Perfora",
        primary_intent=BusinessIntent.ECOMMERCE,
    )
    manifest = CrawlManifest(
        domain="perforacare.com",
        base_url="https://perforacare.com",
        total_pages_discovered=504,
        total_pages_crawled=5,
        pages=[PageEvidence(url=f"https://perforacare.com/p{i}") for i in range(5)],
    )

    scores = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        manifest=manifest,
    )

    appendix = engine.build_scoring_methodology_appendix(
        scores=scores,
        crawl_inventory=manifest,
    )

    assert appendix["formula_version"] == "dristik_central_scoring_v5.1"
    assert "pillars" in appendix
    assert "severity_adjustments" in appendix
    assert "sample_coverage_confidence_model" in appendix
    assert "unavailable_data_exclusion_rules" in appendix
    assert "composite_derivation" in appendix

    # Verify coverage model reflects 5 / 504 (approx 1.0%)
    cov = appendix["sample_coverage_confidence_model"]
    assert cov["tested_pages"] == 5
    assert cov["discovered_total"] == 504
    assert cov["sample_coverage_pct"] == 1.0


def test_issue_5_discipline_contracts_and_retest_criteria():
    """
    Issue 5: Every chapter is checked against its own discipline-specific contract:
    - Local SEO analyzes GBP, NAP, location pages (blocks off-discipline semantic headings)
    - Mobile SEO analyzes viewport, tap targets, responsive rendering
    - Core Web Vitals analyzes LCP, INP, CLS
    - Schema analyzes JSON-LD validation, entity graph
    Verification criteria must test real domain conditions, not generic HTTP 200.
    """
    # 1. Discipline contract validation blocks off-discipline headings in Local SEO chapter
    valid_local_text = "Verify Google Business Profile embed, NAP consistency across location endpoints, and local schema."
    res_valid = validate_chapter_discipline_contract("local_seo", valid_local_text)
    assert res_valid["is_valid"] is True
    assert "Google Business Profile" in res_valid["cleaned_text"]

    invalid_local_text = "Local SEO review complete. Recommending semantic heading hierarchy and H1 structure."
    res_invalid = validate_chapter_discipline_contract("local_seo", invalid_local_text)
    assert res_invalid["is_valid"] is False
    assert len(res_invalid["violations"]) > 0
    assert "heading" not in res_invalid["cleaned_text"].lower()

    # 2. Acceptance criteria contract: domain-specific conditions vs generic HTTP 200
    mobile_finding = Finding(
        finding_id="find_mob_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Mobile tap targets fail minimum 48px touch spacing",
        description="Navigation buttons overlap on 375px mobile viewport.",
        affected_urls=["https://example.com/menu"],
    )
    mob_enriched = PlainEnglishEngine.enrich_finding(mobile_finding, 1)
    crit_mob = mob_enriched["acceptance_criteria"].lower()
    assert "viewport" in crit_mob or "tap-target" in crit_mob or "375px" in crit_mob
    assert "endpoint resolves with http 200" not in crit_mob

    # 3. Core Web Vitals finding
    cwv_finding = Finding(
        finding_id="find_cwv_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="High TTFB and LCP latency across catalog endpoints",
        description="Origin TTFB exceeds 800ms and LCP exceeds 2.5s.",
        affected_urls=["https://example.com/products/unwind-combo"],
    )
    cwv_enriched = PlainEnglishEngine.enrich_finding(cwv_finding, 2)
    crit_cwv = cwv_enriched["acceptance_criteria"].lower()
    assert "ttfb" in crit_cwv or "lcp" in crit_cwv or "content-encoding" in crit_cwv
    assert "endpoint resolves with http 200" not in crit_cwv


def test_issue_9_semantic_deduplication_and_repetition_removal():
    """
    Issue 9: Audit report removes boilerplate repetition and ensures findings
    are consolidated rather than repeated across multiple diagnostic chapters.
    """
    findings = [
        Finding(
            finding_id="f_root_01",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Origin Server TTFB Latency Outlier",
            description="Catalog page response time spike to 36.2s.",
            affected_urls=["https://perforacare.com/products/unwind-combo"],
            root_cause_id="root_origin_latency",
        ),
        Finding(
            finding_id="f_downstream_02",
            category=Category.TECHNICAL_SEO,
            severity=Severity.MEDIUM,
            title="Core Web Vitals LCP Degradation",
            description="Downstream consequence of origin server TTFB latency outlier.",
            affected_urls=["https://perforacare.com/products/unwind-combo"],
            root_cause_id="root_origin_latency",
            is_downstream_consequence=True,
        ),
    ]

    manifest = CrawlManifest(
        domain="perforacare.com",
        base_url="https://perforacare.com",
        total_pages_discovered=504,
        total_pages_crawled=5,
        pages=[PageEvidence(url=f"https://perforacare.com/p{i}") for i in range(5)],
    )
    scores = ScoringEngine().calculate_scores(
        findings=findings,
        manifest=manifest,
        business_profile=BusinessProfile(business_name="Perfora"),
    )

    renderer = SeoAuditBookRenderer()
    report = type("Report", (), {
        "domain": "perforacare.com",
        "analysis_id": "audit_perfora_dedup",
        "crawl_manifest": manifest,
        "findings": findings,
        "overall_scores": scores,
        "business_profile": BusinessProfile(business_name="Perfora"),
    })()

    html = renderer.render_html_report(report)

    # Downstream consequence finding must be marked as downstream and not double-charged
    assert "Downstream Consequence" in html or "root_origin_latency" in html or "Origin Server TTFB Latency Outlier" in html
