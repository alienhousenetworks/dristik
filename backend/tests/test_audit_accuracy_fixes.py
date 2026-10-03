"""
Tests for Dristik Enterprise Audit Accuracy Improvements:
1. Security Header & Transport Analyzer
2. WCAG 2.2 Decorative Image Classification
3. Accurate Sitemap Absence Calibration
4. Unmeasured Orphan Detection on Missing Sitemap
5. Root-Cause Deduplication in Scoring Engine
"""
from bs4 import BeautifulSoup
from app.domain.models import PageEvidence, BusinessProfile, Finding, FindingEvidence
from app.domain.enums import Category, Severity, BusinessIntent
from app.analyzers.security_analyzer import SecurityAnalyzer
from app.analyzers.media_asset_analyzer import MediaAssetAnalyzer
from app.analyzers.link_depth import LinkDepthAnalyzer
from app.scoring.engine import ScoringEngine
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.dom import analyze_dom_structure
from app.agents.legacy.discovery import DiscoveryAgent


def test_security_header_analyzer():
    headers = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Server": "nginx/1.18.0",  # Info leak
    }
    rep = SecurityAnalyzer.analyze_headers("https://acme.com", response_headers=headers)
    assert rep.hsts_enabled is True
    assert rep.csp_enabled is True
    assert rep.x_frame_options == "DENY"
    assert rep.x_content_type_options == "nosniff"
    assert len(rep.information_disclosure_headers) >= 1
    assert rep.score >= 80.0
    assert rep.grade in ("A", "B")


def test_wcag_22_decorative_images_not_penalized():
    # 1 decorative with alt=""
    # 1 decorative with role="presentation"
    # 1 informative missing alt
    html = """
    <html>
      <body>
        <img src="/decorative1.png" alt="">
        <img src="/decorative2.png" role="presentation">
        <img src="/product.png">
      </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com")]
    raw_map = {"https://acme.com": html}
    media_rep = MediaAssetAnalyzer.analyze_media(pages, raw_html_map=raw_map)

    assert media_rep.total_images_analyzed == 3
    assert media_rep.missing_alt_count == 1  # Only /product.png is missing alt
    assert media_rep.empty_alt_count >= 1   # /decorative1.png is compliant decorative

    # Test DOM analyzer evidence store emission
    soup = BeautifulSoup(html, "html.parser")
    store = EvidenceStore(run_id="run_test")
    dom_res = analyze_dom_structure(soup, "https://acme.com", store)
    assert dom_res["images_without_alt"] == 1  # Only 1 violation, not 3!


def test_orphan_detection_unmeasured_when_no_sitemap():
    pages = [
        PageEvidence(url="https://acme.com", internal_links=["https://acme.com/about"]),
        PageEvidence(url="https://acme.com/about", internal_links=[]),
    ]
    rep = LinkDepthAnalyzer.detect_orphans(pages, sitemap_urls=[], homepage_url="https://acme.com")
    assert rep.total_sitemap_urls == 0
    assert "unmeasured" in rep.summary.lower()


import pytest

@pytest.mark.asyncio
async def test_sitemap_severity_calibrated_for_small_sites():
    from app.domain.models import CrawlManifest
    manifest = CrawlManifest(
        manifest_id="test_man",
        base_url="https://acme.com",
        domain="acme.com",
        sitemap_found=False,
        robots_txt_found=True,
        pages=[PageEvidence(url=f"https://acme.com/page{i}") for i in range(5)]
    )
    agent = DiscoveryAgent()
    res = await agent.run(manifest=manifest)
    sitemap_finding = next(f for f in res["findings"] if "sitemap" in f["title"].lower())
    assert sitemap_finding["severity"] == Severity.LOW.value  # Low/Advisory on 5-page crawl, not High!
    assert "advisory" in sitemap_finding["title"].lower()


def test_root_cause_deduplication_in_scoring():
    engine = ScoringEngine()
    profile = BusinessProfile(
        company_name="Acme Corp",
        target_audience="DevOps",
        primary_intent=BusinessIntent.LEAD_GENERATION
    )

    # 2 findings from the exact same root cause: ambiguous H1 hero slogan
    f1 = Finding(
        finding_id="F-H1-CONTENT",
        category=Category.CONTENT,
        severity=Severity.HIGH,
        title="Homepage Hero H1 Slogan Mismatch",
        description="The hero H1 'BEYOND IMAGINATION' is a vague slogan.",
        recommendation="Replace with explicit capability definition."
    )
    f2 = Finding(
        finding_id="F-H1-ONPAGE",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Homepage Hero H1 Slogan Mismatch",
        description="The hero H1 'BEYOND IMAGINATION' misses primary product keyword.",
        recommendation="Include primary product keyword in H1."
    )

    score_result = engine.calculate_scores([f1, f2], business_profile=profile)
    content_score = score_result.category_scores[Category.CONTENT.value]
    seo_score = score_result.category_scores[Category.ON_PAGE_SEO.value]

    # Under v5 rubric, root cause is charged once in primary pillar (4.8 pts)
    # and secondary pillar is marked downstream consequence with 0.0 pts lost.
    content_deduction = sum(item["points_lost"] for item in content_score.deductions)
    seo_deduction = sum(item["points_lost"] for item in seo_score.deductions)
    assert content_deduction == 4.8
    assert seo_deduction == 0.0
    assert any(item.get("is_downstream_consequence") for item in seo_score.deductions)
