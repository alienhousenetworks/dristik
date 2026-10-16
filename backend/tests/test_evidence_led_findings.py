"""
Unit tests for Sprint 2 (Phases 2 & 3) improvements:
- 7-Part Evidence-Led Finding Schema
- Chapter-independent diagnostic logic with genuine 6-state status model
- Role-based recommendations (developer, content editor, SEO specialist, analytics owner)
- Estimated effort, dependencies, priority rationale, acceptance criteria, and verification commands
- Absence of unbacked ranking/revenue claims
"""
from typing import List
import pytest

from app.domain.enums import Category, DiagnosticStatus, FindingClassification, Severity
from app.domain.models import (
    CrawlManifest,
    DiagnosticCoverageMatrix,
    DiagnosticRecord,
    ExecutiveReport,
    Finding,
    FindingEvidence,
    PageEvidence,
)
from app.reports.plain_english_engine import PlainEnglishEngine
from app.reports.seo_book_renderer import build_seo_book_context, normalize_finding


def test_plain_english_engine_enriches_7_part_analytical_structure():
    """Verify that PlainEnglishEngine.enrich_finding populates all 7 parts of the schema."""
    evidence = FindingEvidence(
        evidence_id="EV-TEST-001",
        url="https://example.com/services/",
        element="img",
        observed_value="",
        expected_condition="Informative content image must have a descriptive non-empty alt attribute",
        test_method="crawl_html_dom",
        snippet='<img src="/hero.webp">',
        source="crawl",
    )
    finding = Finding(
        finding_id="FND-TEST-01",
        title="Image Lacks Alternative Text on /services/",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        classification=FindingClassification.VERIFIED_DEFECT,
        affected_urls=["https://example.com/services/"],
        evidence=[evidence],
        evidence_ids=["EV-TEST-001"],
        owner="Content Editor",
        responsible_role="Content Editor",
        estimated_effort="Low (< 2 hours)",
        dependencies=["CMS media asset library access"],
        priority_rationale="Medium: Essential for accessibility and image search context.",
        acceptance_criteria="Image on /services/ must have descriptive alt attribute.",
        verification_command="curl -s 'https://example.com/services/' | grep -i '<img' | grep -v 'alt='",
    )

    enriched = PlainEnglishEngine.enrich_finding(finding)

    # 1. Observation
    assert "plain_english_summary" in enriched and len(enriched["plain_english_summary"]) > 10
    assert "observed_result" in enriched

    # 2. Evidence
    assert "evidence" in enriched and len(enriched["evidence"]) == 1
    ev_item = enriched["evidence"][0]
    assert ev_item["id"] == "EV-TEST-001"
    assert ev_item["url"] == "https://example.com/services/"
    assert ev_item["element"] == "img"
    assert ev_item["test_method"] == "crawl_html_dom"
    assert '<img src="/hero.webp">' in ev_item["snippet"]

    # 3. Diagnosis
    assert "what_was_checked" in enriched and len(enriched["what_was_checked"]) > 0
    assert "priority_rationale" in enriched and "Medium" in enriched["priority_rationale"]

    # 4. Impact
    assert "business_impact" in enriched and len(enriched["business_impact"]) > 10
    assert "who_affected" in enriched

    # 5. Confidence
    assert "confidence" in enriched and "Verified" in enriched["confidence"]
    assert "limitations" in enriched

    # 6. Remediation Roadmap (Priority 6)
    assert enriched["responsible_role"] == "Content Editor"
    assert enriched["estimated_effort"] == "Low (< 2 hours)"
    assert enriched["dependencies"] == ["CMS media asset library access"]
    assert "recommended_action" in enriched

    # 7. Validation Protocol (Priority 6)
    assert enriched["acceptance_criteria"] == "Image on /services/ must have descriptive alt attribute."
    assert "curl" in enriched["verification_command"]
    assert len(enriched["verification_steps"]) > 0


def test_chapter_subsections_render_honest_statuses_from_diagnostic_inventory():
    """Verify that chapter subsections reflect authentic DiagnosticRecord statuses rather than default Passed."""
    diag_records = [
        DiagnosticRecord(
            diagnostic_id="DIAG-03-HTTP-STATUS",
            chapter_num="10",
            chapter_title="HTTP Status Codes and Redirects",
            subchapter="HTTP Response Codes",
            applicable_url_types=["all"],
            required_data_sources=["raw_http"],
            test_performed="Verify all sampled internal URLs return HTTP 200 OK without unhandled 4xx/5xx exceptions.",
            status=DiagnosticStatus.PASSED.value,
            status_reason="All audited URLs responded with valid HTTP 200 status codes.",
            severity="INFORMATIONAL",
        ),
        DiagnosticRecord(
            diagnostic_id="DIAG-11-SITEMAP",
            chapter_num="11",
            chapter_title="XML Sitemaps and Robots.txt",
            subchapter="XML Sitemap Integrity",
            applicable_url_types=["sitemap"],
            required_data_sources=["xml_sitemap"],
            test_performed="Validate XML sitemap syntax and indexability.",
            status=DiagnosticStatus.FAILED.value,
            status_reason="Sitemap contains 3 non-200 URLs.",
            severity="HIGH",
        ),
        DiagnosticRecord(
            diagnostic_id="DIAG-04-CLICK-DEPTH",
            chapter_num="07",
            chapter_title="Website Crawling and Crawl Budget",
            subchapter="Crawl Depth Architecture",
            applicable_url_types=["html"],
            required_data_sources=["crawl_graph"],
            test_performed="Calculate crawl distance from homepage.",
            status=DiagnosticStatus.SAMPLED.value,
            status_reason="Evaluated on 5 sampled pages; all within 3 clicks.",
            severity="INFORMATIONAL",
        ),
    ]

    matrix = DiagnosticCoverageMatrix(
        matrix_id="TEST-MATRIX",
        run_id="test_run",
        records=diag_records,
        passed_count=1,
        failed_count=1,
        sampled_count=1,
    )

    manifest = CrawlManifest(
        run_id="test_run",
        domain="example.com",
        discovered_urls=["https://example.com/", "https://example.com/about", "https://example.com/contact"],
        crawled_urls=["https://example.com/"],
        pages=[PageEvidence(url="https://example.com/", status_code=200)],
    )

    report = ExecutiveReport.model_construct(
        report_id="rep_test_01",
        website_url="https://example.com",
        run_id="test_run",
        domain="example.com",
        diagnostic_inventory=matrix,
        crawl_manifest=manifest,
        findings=[],
    )

    ctx = build_seo_book_context(report)
    sections = ctx.get("seo_sections", [])
    assert len(sections) > 0

    all_statuses = []
    for sec in sections:
        for sub in sec.get("subsections", []):
            for m in sub.get("metrics", []):
                all_statuses.append(m.get("status"))

    # Assert controlled statuses appear in metrics tables
    assert DiagnosticStatus.PASSED.value in all_statuses or DiagnosticStatus.SAMPLED.value in all_statuses
    assert DiagnosticStatus.UNAVAILABLE.value in all_statuses
    # Confirm no legacy free-form "Passed check"
    assert "Passed check" not in all_statuses


def test_zero_unbacked_ranking_or_revenue_claims_in_analyzer_findings():
    """Verify that analyzers do not generate unbacked claims of lost rankings or revenue."""
    from app.analyzers.canonical_auditor import analyze_canonicals
    from app.analyzers.heading_analyzer import HeadingAnalyzer, analyze_heading_hierarchy
    from app.analyzers.media_asset_analyzer import MediaAssetAnalyzer, analyze_media_assets

    page = PageEvidence(
        url="https://example.com/",
        status_code=200,
        raw_html="<html><head></head><body><h1>One</h1><h1>Two</h1><img src='test.png'></body></html>",
    )

    _, can_findings = analyze_canonicals([page])
    hdg_rep = analyze_heading_hierarchy([page])
    hdg_findings = HeadingAnalyzer.generate_findings(hdg_rep)
    media_rep = analyze_media_assets([page])
    media_findings = MediaAssetAnalyzer.generate_findings(media_rep)

    all_findings = can_findings + hdg_findings + media_findings
    for f in all_findings:
        text = f"{f.title} {f.description} {f.why_it_matters} {f.recommendation}".lower()
        assert "lost revenue" not in text
        assert "revenue loss" not in text
        assert "drops page rankings" not in text
        assert "duplicate content penalty" not in text
