"""
Tests for Industry-Standard SEO Audit and Competitor Parity Engines:
- Google SERP Pixel Width Calculator
- Canonical Tag Auditor
- HTTP Status Code & Broken Link Auditor
- Competitor SEO Parity Matrix
"""
import pytest
from app.domain.models import PageEvidence, CrawlManifest
from app.crawl.analyzers.pixel_calculator import (
    calculate_title_pixel_width,
    calculate_meta_pixel_width,
    evaluate_title_pixel_status,
    evaluate_meta_pixel_status,
)
from app.analyzers.canonical_auditor import analyze_canonicals
from app.analyzers.http_status_auditor import analyze_http_statuses
from app.intelligence.competitive.benchmark import build_competitor_seo_parity_matrix


def test_pixel_width_calculator():
    # Narrow string (many 'i's) vs wide string (many 'W's)
    narrow = "iiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
    wide = "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW"
    assert len(narrow) == len(wide)
    assert calculate_title_pixel_width(wide) > calculate_title_pixel_width(narrow) * 2

    # Truncation threshold evaluation
    px, status = evaluate_title_pixel_status("Short Title")
    assert status == "too_short"

    # 50 chars of wide characters will exceed 580px
    long_wide = "ENTERPRISE CLOUD SECURITY ARCHITECTURE PLATFORM & INFRASTRUCTURE"
    px_long, status_long = evaluate_title_pixel_status(long_wide)
    assert px_long > 500


def test_canonical_auditor():
    pages = [
        PageEvidence(
            url="https://example.com/",
            canonical_url="https://example.com/",
            status_code=200
        ),
        PageEvidence(
            url="https://example.com/blog?tag=seo",
            canonical_url="https://example.com/blog",
            status_code=200
        ),
        PageEvidence(
            url="https://example.com/missing-can",
            canonical_url=None,
            status_code=200
        ),
        PageEvidence(
            url="https://example.com/relative-can",
            canonical_url="/relative-can",
            status_code=200
        ),
        PageEvidence(
            url="https://example.com/broken-can",
            canonical_url="https://example.com/404-page",
            status_code=200
        ),
        PageEvidence(
            url="https://example.com/404-page",
            status_code=404
        ),
    ]

    rollup, findings = analyze_canonicals(pages)
    assert rollup.total_pages_evaluated == 6
    assert rollup.self_canonical_count >= 1
    assert rollup.canonicalized_count >= 1
    assert rollup.missing_canonical_count >= 1
    assert rollup.relative_canonical_count >= 1
    assert rollup.broken_canonical_count >= 1
    assert any(f.finding_id == "finding_broken_canonicals" for f in findings)
    assert any(f.finding_id == "finding_missing_canonicals" for f in findings)


def test_http_status_auditor():
    pages = [
        PageEvidence(url="https://example.com/page1", status_code=200),
        PageEvidence(url="https://example.com/page2", status_code=301, redirect_chain=[{"location": "https://example.com/dest"}]),
        PageEvidence(url="https://example.com/page3", status_code=404),
        PageEvidence(url="https://example.com/page4", status_code=500),
    ]
    raw_broken = [
        {"source_url": "https://example.com/page1", "target_url": "https://example.com/page3", "anchor": "Dead Link", "status": 404}
    ]

    rollup, findings = analyze_http_statuses(pages, broken_links_raw=raw_broken)
    assert rollup.count_2xx == 1
    assert rollup.count_3xx == 1
    assert rollup.count_4xx == 1
    assert rollup.count_5xx == 1
    assert len(rollup.broken_links) == 1
    assert rollup.broken_links[0].anchor_text == "Dead Link"
    assert any(f.finding_id == "finding_http_4xx_errors" for f in findings)
    assert any(f.finding_id == "finding_http_5xx_errors" for f in findings)


def test_competitor_seo_parity_matrix():
    target_pages = [
        PageEvidence(
            url="https://target.com/",
            title="Target Enterprise Web Intelligence Platform - Fast & Secure",
            meta_description="Target provides enterprise grade intelligence with automated compliance and fast response times across all services.",
            h1=["Enterprise Web Intelligence"],
            word_count=850,
            ttfb_ms=180.0,
            status_code=200,
            schema_types=["Organization", "WebSite", "BreadcrumbList"]
        ),
        PageEvidence(
            url="https://target.com/pricing",
            title="Target Transparent Pricing Plans & Enterprise Subscriptions",
            meta_description="Explore transparent pricing options for teams of all sizes with zero hidden fees and enterprise SLAs included.",
            h1=["Pricing Plans"],
            word_count=600,
            ttfb_ms=210.0,
            status_code=200,
            schema_types=["Product"]
        ),
    ]

    rival_pages = [
        PageEvidence(
            url="https://rival.com/",
            title="Rival Homepage",
            meta_description="Rival short description",
            h1=["Home"],
            word_count=220,
            ttfb_ms=650.0,
            status_code=200,
            schema_types=["WebSite"]
        )
    ]

    comp_map = {"rival.com": rival_pages}
    matrix = build_competitor_seo_parity_matrix(
        target_pages=target_pages,
        target_domain="target.com",
        competitors=["rival.com"],
        competitor_pages_map=comp_map
    )

    assert matrix.target_domain == "target.com"
    assert len(matrix.competitors) == 2
    assert matrix.target_rank == 1
    assert len(matrix.top_advantages) >= 1
