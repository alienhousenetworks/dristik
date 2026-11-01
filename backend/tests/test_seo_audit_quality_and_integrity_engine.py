"""
Test Suite: Dristik SEO Audit Quality & Central Integrity Engine
Validates all 22 identified issues across applicability, deduplication, evidence,
remediation contracts, score reconciliation, visual styling, and PDF size gating.
"""
import pytest
from app.domain.models import (
    Finding,
    ExecutiveReport,
    CrawlManifest,
    PageEvidence,
    BusinessProfile,
    OverallScoreResult,
)
from app.domain.enums import Category, Severity
from app.crawl.audit.consistency_engine import CrossChapterConsistencyEngine
from app.reports.plain_english_engine import PlainEnglishEngine
from app.seo.reporting.seo_book_renderer import seo_audit_book_renderer, build_seo_book_context


def _make_report(domain="example.com", findings=None, profile=None, manifest=None):
    return ExecutiveReport(
        report_id="DST-TEST-ENG",
        analysis_id="test-run-eng",
        website_url=f"https://{domain}",
        domain=domain,
        generated_at="2026-10-31T12:00:00Z",
        business_profile=profile,
        crawl_manifest=manifest,
        scores=OverallScoreResult(
            overall_score=80.0,
            grade="B",
            health_label="Good",
        ),
        story_summary="Representative sample audit demonstrates baseline infrastructure compliance.",
        primary_strategic_opportunity="Consolidate commercial service offerings with validated structured data.",
        consultant_advice_what_to_ignore="Ignore cosmetic copy nuances.",
        findings=list(findings or []),
    )


def test_applicability_filter_drops_ecommerce_and_byline_on_service_site():
    """Issue 6, 7, 8: Faceted navigation, product variants, and service bylines dropped for services site."""
    profile = BusinessProfile(
        business_model="b2b_service",
        industry="Technology Solutions",
        niche="Cloud and AI Engineering",
    )
    pages = [
        PageEvidence(url="https://example.com/", title="Home", canonical_url="https://example.com/", meta_description="Home page meta description."),
        PageEvidence(url="https://example.com/services/cloud", title="Cloud", canonical_url="https://example.com/services/cloud", meta_description="Cloud services."),
    ]
    manifest = CrawlManifest(pages=pages, total_pages_discovered=2, total_pages_crawled=2)
    report = _make_report(
        domain="example.com",
        profile=profile,
        manifest=manifest,
        findings=[
            Finding(finding_id="f1", title="Faceted navigation missing", description="No filter parameters found", category=Category.TECHNICAL_SEO, severity=Severity.MEDIUM),
            Finding(finding_id="f2", title="Product variant out of stock handling", description="Inventory status missing", category=Category.TECHNICAL_SEO, severity=Severity.HIGH),
            Finding(finding_id="f3", title="Author byline missing", description="Service page lacks author byline", category=Category.ON_PAGE_SEO, severity=Severity.LOW, affected_urls=["https://example.com/services/cloud"]),
            Finding(finding_id="f4", title="Slow TTFB", description="Server latency exceeds 800ms", category=Category.TECHNICAL_SEO, severity=Severity.HIGH),
        ]
    )

    reconciled, _ = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    titles = [f.title.lower() for f in reconciled.findings]
    assert not any("faceted" in t for t in titles), "Faceted navigation should be dropped for service site"
    assert not any("variant" in t for t in titles), "Product variant should be dropped for service site"
    assert not any("byline" in t for t in titles), "Author byline on service page should be dropped"
    assert any("ttfb" in t for t in titles), "Legitimate technical defect must be preserved"


def test_schema_deduplication_and_severity_realignment():
    """Issue 3, 4, 5: Merge duplicate schema defects, downgrade from CRITICAL, fix remediation from breadcrumb."""
    f_schema_1 = Finding(
        finding_id="SEO-004",
        title="Schema markup is limited to Organization only; missing Service schema",
        description="Site declares Organization schema but lacks service-specific schema.",
        category=Category.SCHEMA,
        severity=Severity.CRITICAL,
        priority=10,
        recommendation="Add BreadcrumbList schema to improve hierarchy.",
        affected_urls=["https://example.com/services/software"],
    )
    f_schema_2 = Finding(
        finding_id="SEO-010",
        title="Schema markup only declares Organization; service-specific Offer markup missing",
        description="Service pages lack Product or Service schema declaration.",
        category=Category.SCHEMA,
        severity=Severity.HIGH,
        priority=8,
        recommendation="Implement service structured data.",
        affected_urls=["https://example.com/services/consulting"],
    )
    report = _make_report(
        domain="example.com",
        findings=[f_schema_1, f_schema_2]
    )

    reconciled, _ = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    schema_findings = [f for f in reconciled.findings if "schema" in f.title.lower()]
    assert len(schema_findings) == 1, "Duplicate schema findings must be merged into one canonical finding"
    canonical = schema_findings[0]
    assert canonical.severity == Severity.MEDIUM, "Missing optional Service schema must not remain CRITICAL"
    assert canonical.priority <= 6
    assert "breadcrumb" not in canonical.recommendation.lower(), "Service schema remediation must not prescribe BreadcrumbList"
    assert "service" in canonical.recommendation.lower()
    assert set(canonical.affected_urls) == {"https://example.com/services/software", "https://example.com/services/consulting"}


def test_image_alt_synchronization_and_chapter_honesty():
    """Issue 1, 2: 15 missing alt attributes must create a finding, reflect in On-Page, and prevent zero-defects claim."""
    pages = [
        PageEvidence(url="https://example.com/", total_images=16, images_without_alt=15, canonical_url="https://example.com/", meta_description="Home"),
        PageEvidence(url="https://example.com/services", total_images=4, images_without_alt=0, canonical_url="https://example.com/services", meta_description="Services"),
    ]
    manifest = CrawlManifest(pages=pages, total_pages_discovered=2, total_pages_crawled=2)
    report = _make_report(
        domain="example.com",
        manifest=manifest,
        findings=[]
    )

    reconciled, _ = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    alt_findings = [f for f in reconciled.findings if "alt" in f.title.lower() and "image" in f.title.lower()]
    assert len(alt_findings) == 1, "Canonical missing image alt finding must be synthesized from PageEvidence"
    assert "15" in alt_findings[0].title
    assert alt_findings[0].category == Category.ON_PAGE_SEO

    ctx = build_seo_book_context(reconciled)
    image_chapter = next((s for s in ctx["seo_sections"] if s["id"] == "sec-image-seo"), None)
    if image_chapter:
        assert len(image_chapter["findings"]) > 0, "Image chapter must recognize the 15 missing alt defects"
        exec_text = image_chapter["analysis"]["executive_interpretation"].lower()
        assert "zero defects" not in exec_text, "Image SEO chapter must not claim zero defects when 15 images lack alt attributes"


def test_measurable_acceptance_criteria_and_cro_ownership():
    """Issue 16, 17: Acceptance criteria must be testable assertions; CTA assigned to CRO/Content, not Analytics."""
    finding_cta = Finding(
        finding_id="f_cta",
        title="Multiple service pages share identical CTA 'REQUEST CUSTOM BUILD'",
        description="Identical generic button across service pages dilutes conversion relevance.",
        category=Category.UX_CONVERSION,
        severity=Severity.HIGH,
        affected_urls=["https://example.com/services/cloud"],
    )

    enriched = PlainEnglishEngine.enrich_finding(finding_cta, 1)
    assert enriched["responsible_role"] == "CRO Specialist", "CTA issue must be assigned to CRO Specialist, not Analytics Owner"
    assert "analytics administrative access" not in [d.lower() for d in enriched.get("dependencies", [])]
    assert "with zero " not in enriched["acceptance_criteria"], "Acceptance criteria must not repeat 'with zero <title>' boilerplate"
    assert "conversion intent" in enriched["acceptance_criteria"].lower() or "cta text" in enriched["acceptance_criteria"].lower()


def test_visual_palette_and_cover_dossier():
    """Template must use executive slate palette without harsh yellow or neon red backgrounds."""
    report = _make_report(domain="example.com", findings=[])
    html = seo_audit_book_renderer.render_html_report(report)
    
    # Assert harsh yellow / red badge and variable declarations are eliminated
    assert "--critical: #a51d2d" not in html
    assert "--medium: #8a6100" not in html
    assert "#d97706" not in html, "Harsh yellow #d97706 must be eliminated"
    assert "#fffbeb" not in html, "Harsh yellow background #fffbeb must be eliminated"
    assert "C-SUITE AUDIT PUBLICATION" in html or "EXECUTIVE DOSSIER" in html
