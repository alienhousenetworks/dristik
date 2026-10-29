"""
Unit and integration tests for Lighthouse & Core Web Vitals runner,
patch safety & hygiene, and report integrity layer.
"""
import pytest
from app.crawl.analyzers.lighthouse import LighthouseRunner
from app.domain.models import LabPerformanceMetrics, PageEvidence, BusinessProfile, Finding, CrawlManifest
from app.domain.enums import Category, Severity
from app.remediation.patch_generator import RemediationPatcher, _format_title_copy, _format_meta_description
from app.remediation.patch_pack import build_patch_pack_files
from app.scoring.engine import ScoringEngine
from app.intelligence.competitive.benchmark import _compute_profile_metrics
from app.reports.validation_gate import ValidationGate, ValidationResult


def test_lighthouse_runner_evaluation():
    raw_html = "<html><head><title>Test Page</title></head><body><h1>Main Title</h1><p>Content</p><img src='/test.jpg' alt='test'></body></html>"
    rendered_html = raw_html

    metrics = LighthouseRunner.evaluate_lighthouse_metrics(
        url="https://example.com",
        ttfb_ms=250.0,
        raw_html=raw_html,
        rendered_html=rendered_html,
    )

    assert metrics is not None
    assert metrics["lighthouse_performance_score"] is not None
    assert 0.0 <= metrics["lighthouse_performance_score"] <= 100.0
    assert metrics["lighthouse_accessibility_score"] is not None
    assert metrics["lcp_ms"] is not None
    assert metrics["cls_score"] is not None
    assert metrics["tbt_ms"] is not None
    assert metrics["raw_vs_rendered_diff"] is not None
    assert metrics["raw_vs_rendered_diff"]["client_side_hydration_required"] is False


def test_title_and_description_copy_safety():
    # Test title truncation: must not have literal "..."
    clean_title = _format_title_copy("/solutions/cloud-enterprise", "BrandName", "Cloud Infrastructure Solutions")
    assert "..." not in clean_title
    assert len(clean_title) <= 60

    # Test meta description generation: tailored, bounded, no literal "..."
    desc = _format_meta_description("/solutions/cloud", "BrandName", "Cloud Infrastructure Solutions", "Enterprise Engineering Teams")
    assert "..." not in desc
    assert 120 <= len(desc) <= 160
    assert "Enterprise web intelligence and performance acceleration" not in desc


def test_patch_generator_safety_rules():
    page = PageEvidence(
        url="https://example.com/services",
        title="Services Overview Page With Far Too Many Words That Exceed Sixty Characters In Length",
        meta_description=None,
        h1=["Our Services"],
        word_count=500,
        status_code=200,
        image_assets=[
            {"src": "https://192.168.1.1/internal-pic.jpg", "alt": ""},
            {"src": "/images/architecture-diagram.png", "alt": ""}
        ]
    )
    profile = BusinessProfile(
        business_name="Acme Corp",
        website_url="https://example.com",
        industry="Technology"
    )
    generator = RemediationPatcher()
    findings = [
        Finding(
            finding_id="find_001",
            category=Category.ON_PAGE_SEO,
            severity=Severity.HIGH,
            title="Image alt attributes missing",
            description="Images on /services lack descriptive alt attributes.",
            recommendation="Add descriptive alt text to all images.",
            evidence_refs=["https://example.com/services"],
            evidence_snippets=["https://192.168.1.1/internal-pic.jpg", "/images/architecture-diagram.png"]
        ),
        Finding(
            finding_id="find_002",
            category=Category.ON_PAGE_SEO,
            severity=Severity.MEDIUM,
            title="Missing primary <h1> heading tag",
            description="Page lacks semantic H1.",
            recommendation="Add a single descriptive H1 heading.",
            evidence_refs=["https://example.com/services"]
        )
    ]
    patches = generator.generate_patches(findings=findings, business_profile=profile, website_url="https://example.com", pages=[page])

    for p in patches:
        # 1. No literal ... in any snippet
        assert "..." not in p.after_snippet, f"Literal '...' found in patch {p.patch_id}"
        # 2. No Disallow: /_next/
        assert "Disallow: /_next/" not in p.after_snippet, f"Disallow /_next/ found in patch {p.patch_id}"
        # 3. No deprecated SearchAction
        assert "SearchAction" not in p.after_snippet, f"SearchAction found in patch {p.patch_id}"
        # 4. No premature HSTS preload
        if "Strict-Transport-Security" in p.after_snippet:
            assert "preload" not in p.after_snippet.lower(), f"preload found in HSTS patch {p.patch_id}"
        # 5. Image patch must not use IP address as src
        if "img src=" in p.after_snippet.lower():
            assert "192.168.1.1" not in p.after_snippet, f"Raw IP address found in img patch: {p.after_snippet}"


def test_h1_patch_does_not_create_duplicate_when_single_h1_exists():
    page = PageEvidence(
        url="https://example.com/",
        title="Acme Corp Home",
        meta_description="A good description.",
        h1=["Welcome"],
        word_count=400,
        status_code=200,
    )
    profile = BusinessProfile(business_name="Acme Corp", website_url="https://example.com")
    generator = RemediationPatcher()
    finding = Finding(
        finding_id="find_h1",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Missing primary <h1> heading tag",
        description="Heading optimization needed.",
        recommendation="Optimize single H1 heading.",
        evidence_refs=["https://example.com/"]
    )
    patches = generator.generate_patches(findings=[finding], business_profile=profile, website_url="https://example.com", pages=[page])

    h1_patches = [p for p in patches if "h1" in p.title.lower()]
    assert len(h1_patches) <= 1
    if h1_patches:
        patch = h1_patches[0]
        # Should replace existing H1, not add a second one
        assert "<h1" in patch.before_snippet and "Welcome" in patch.before_snippet
        assert patch.after_snippet.count("<h1") == 1


def test_technical_seo_scoring_deducts_for_missing_robots_and_sitemap():
    engine = ScoringEngine()
    profile = BusinessProfile(business_name="Acme Corp", website_url="https://example.com")
    manifest = CrawlManifest(
        base_url="https://example.com",
        robots_txt_found=False,
        sitemap_found=False
    )

    result = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        manifest=manifest
    )

    tech_score = result.category_scores.get(Category.TECHNICAL_SEO.value)
    assert tech_score is not None
    # Must deduct for both missing robots and missing sitemap (never 100/100)
    assert tech_score.score < 90.0, f"Technical SEO score was {tech_score.score}, expected < 90.0 when robots and sitemap are missing"


def test_competitor_seo_parity_deducts_for_missing_infrastructure():
    pages = [PageEvidence(url="https://example.com", status_code=200, ttfb_ms=150.0, h1=["Title"])]
    manifest = CrawlManifest(
        base_url="https://example.com",
        robots_txt_found=False,
        sitemap_found=False
    )

    prof = _compute_profile_metrics(pages, "example.com", is_target=True, manifest=manifest)
    # 100 - 20 - 15 = 65
    assert prof.technical_health_score is not None
    assert prof.technical_health_score <= 65


def test_patch_pack_no_forbidden_patterns():
    profile = BusinessProfile(business_name="Acme Corp", website_url="https://example.com")
    files = build_patch_pack_files(profile, "https://example.com", [])

    for filename, content in files.items():
        assert "Disallow: /_next/" not in content, f"Disallow: /_next/ found in {filename}"
        assert "SearchAction" not in content, f"SearchAction found in {filename}"
        if "strict-transport-security" in content.lower():
            assert "preload" not in content.lower(), f"preload found in {filename}"
        assert "Enterprise web intelligence and performance acceleration" not in content, f"Leaked fallback found in {filename}"
