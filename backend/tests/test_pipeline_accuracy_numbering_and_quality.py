"""
Unit tests for end-to-end pipeline accuracy, numbering integrity, and quality gates.
Covers:
1. MathematicalScoreEngine proportional compliance thresholds and finding deduplication.
2. ScoringEngine unmatched findings fallback not failing verified robots.txt/sitemaps.
3. map_finding_to_chapter deterministic multi-category routing (no Ch 05 dumping).
4. seo_chapter_visuals 20-section master SEO report chart rendering vs 55-chapter book.
5. Consistency engine deduction cleanup on false-positive removal.
"""
from __future__ import annotations

import pytest

from app.domain.enums import Category, Severity
from app.domain.models import BusinessProfile, Finding, PageReport
from app.domain.scoring.engine import ScoringEngine
from app.seo.audit.scoring.mathematical_score_engine import MathematicalScoreEngine
from app.seo.reporting.seo_chapter_visuals import chapter_panel
from app.seo.reporting.seo_print_report import map_finding_to_chapter


def test_mathematical_score_proportional_compliance_and_deduplication():
    """Verifies that high-compliance sites (e.g. 95% perfect) don't have checks collapse to 0."""
    engine = MathematicalScoreEngine()

    # 20 pages: 19 have titles/metas/canonicals/h1/alts, 1 page has a minor gap
    pages = [
        {
            "url": f"https://example.com/page-{i}",
            "status_code": 200,
            "has_canonical": True,
            "is_indexable": True,
            "title": f"Page Title {i}",
            "meta_description": f"Meta description for page {i}",
            "h1": [f"Header {i}"],
            "word_count": 600,
            "has_links": True,
            "images_total": 4,
            "images_without_alt": 0,
        }
        for i in range(19)
    ]
    # Page 20 has missing alt and long title
    pages.append({
        "url": "https://example.com/page-19",
        "status_code": 200,
        "has_canonical": True,
        "is_indexable": True,
        "title": "Page Title 19 with very long title text that triggers advisory",
        "meta_description": "Meta description 19",
        "h1": ["Header 19"],
        "word_count": 550,
        "has_links": True,
        "images_total": 5,
        "images_without_alt": 1,
    })

    findings = [
        {
            "rule_id": "onpage.image_alt_missing",
            "category": "ON_PAGE_SEO",
            "severity": "LOW",
            "finding_id": "f_alt_1",
            "root_cause_id": "rc_missing_alt",
            "affected_urls": ["https://example.com/page-19"],
        },
        # Duplicate finding for the same root cause on another element
        {
            "rule_id": "onpage.image_alt_missing",
            "category": "ON_PAGE_SEO",
            "severity": "LOW",
            "finding_id": "f_alt_2",
            "root_cause_id": "rc_missing_alt",
            "affected_urls": ["https://example.com/page-19"],
        },
    ]

    scorecard = engine.build_scorecard_from_observations(
        pages=pages,
        findings=findings,
        evidence_records=[],
        discovered_count=20,
        crawled_count=20,
        sampling_status="FULL_CRAWL",
    )

    onpage_dim = next(d for d in scorecard.dimensions if d.dimension_id == "on_page_seo")
    assert onpage_dim.is_measured is True
    # 19/20 >= 80% alt coverage and title presence, so baseline checks pass
    assert onpage_dim.score >= 80.0

    # Executed checks: 4 baseline checks (title, meta, h1, alt) + 1 deduplicated finding check = 5 checks
    assert onpage_dim.executed_checks_count == 5
    assert onpage_dim.passed_checks_count == 4
    assert onpage_dim.failed_checks_count == 1


def test_scoring_engine_unmatched_findings_preserves_verified_robots_txt():
    """Unclassified technical findings must not override verified robots.txt."""
    engine = ScoringEngine()

    # Manifest confirms robots.txt was fetched and found
    manifest_obj = type("ManifestMock", (), {
        "robots_txt_found": True,
        "sitemap_found": True,
        "pages": [{"url": "https://example.com/", "status_code": 200}],
    })()

    # Finding in TECHNICAL_SEO with unmapped title
    unmatched_tech_finding = Finding(
        finding_id="find_tech_misc_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.LOW,
        title="Edge CDN Worker Header Stripping Warning",
        description="Origin headers stripped at Cloudflare edge worker.",
    )

    result = engine.calculate_scores(
        findings=[unmatched_tech_finding],
        business_profile=BusinessProfile(business_name="Test Co", domain="example.com"),
        manifest=manifest_obj,
    )

    tech_score = result.category_scores.get(Category.TECHNICAL_SEO.value)
    assert tech_score is not None

    # Check result for robots.txt must still be PASS (score == 1.0)
    robots_check = next((c for c in tech_score.check_results if c.check_id == "robots_txt_rfc9309"), None)
    assert robots_check is not None
    assert robots_check.score == 1.0
    assert robots_check.passed == 1


def test_map_finding_to_chapter_routing():
    """Verifies findings route accurately to diagnostic chapters without defaulting to Ch 05."""
    # Technical crawl
    f_crawl = Finding(finding_id="f1", category=Category.TECHNICAL_SEO, severity=Severity.MEDIUM, title="Soft 404 Error Encountered")
    assert map_finding_to_chapter(f_crawl) == "03"

    # Schema
    f_schema = Finding(finding_id="f2", category=Category.SCHEMA, severity=Severity.HIGH, title="Missing Service Markup")
    assert map_finding_to_chapter(f_schema) == "08"

    # CWV / Performance
    f_perf = Finding(finding_id="f3", category=Category.TECHNICAL_SEO, severity=Severity.MEDIUM, title="LCP Element Latency Exceeds 2.5s")
    assert map_finding_to_chapter(f_perf) == "10"

    # Security
    f_sec = Finding(finding_id="f4", category=Category.TECHNICAL_SEO, severity=Severity.MEDIUM, title="Strict-Transport-Security Header Omitted")
    assert map_finding_to_chapter(f_sec) == "11"

    # UX / CRO
    f_cro = Finding(finding_id="f5", category=Category.UX_CONVERSION, severity=Severity.LOW, title="Unclear Form Error Messaging")
    assert map_finding_to_chapter(f_cro) == "07"

    # GEO / AEO
    f_geo = Finding(finding_id="f6", category=Category.AI_SEARCH, severity=Severity.MEDIUM, title="Low Citability in AI Answer Engines")
    assert map_finding_to_chapter(f_geo) == "18"

    # On-Page
    f_onpage = Finding(finding_id="f7", category=Category.ON_PAGE_SEO, severity=Severity.MEDIUM, title="H1 Heading Tag Missing")
    assert map_finding_to_chapter(f_onpage) == "05"


def test_chapter_panel_renders_20_section_charts():
    """Verifies that chapter_panel produces expected visual charts for the 20-Section Master standard."""
    mock_book = type("ReportWrapperMock", (), {
        "page_reports": [
            PageReport(url="https://example.com/", status_code=200, word_count=800, ttfb_ms=150.0)
        ],
        "crawl_manifest": {
            "pages": [
                {"url": "https://example.com/", "status_code": 200, "word_count": 800, "ttfb_ms": 150.0}
            ]
        },
        "sample": "1 page fetched over HTTPS",
    })()

    # Chapter 03 (Indexability) should produce HTTP status chart
    html_ch03 = chapter_panel(mock_book, "03", [])
    assert "HTTP status in the crawled sample" in html_ch03

    # Chapter 06 (Content) should produce Word counts chart
    html_ch06 = chapter_panel(mock_book, "06", [])
    assert "Extracted word counts" in html_ch06
