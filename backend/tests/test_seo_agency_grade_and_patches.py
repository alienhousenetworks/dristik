"""
Tests for Enterprise Agency-Grade SEO Audit & Grounded Remediation Engine:
1. Grounded Remediation Patcher (Page-specific Title, Meta, Canonical, H1, Redirects, Images)
2. Universal Patch Engine finding-derived typed patches
3. XML Sitemap Hygiene Auditor (3xx/4xx, noindex, and canonicalized sitemap URLs)
4. Canonical Auditor enhancements (3xx redirect targets and noindex conflict)
5. Heading Hierarchy & Outline Auditor (empty H1, multiple H1, hierarchy violations)
6. Media Asset & CLS Auditor (missing alt, missing width/height)
7. Link Depth Auditor (click depth > 3, sitemap orphans, generic anchors)
"""
import pytest
from app.domain.models import (
    PageEvidence,
    CrawlManifest,
    Finding,
    FindingEvidence,
    BusinessProfile,
    CodePatch,
    RemediationPatch,
)
from app.domain.enums import Category, Severity, ReleaseStatus, PatchRiskLevel
from app.remediation.patch_generator import RemediationPatcher
from app.remediation.patch_engine import UniversalPatchEngine
from app.analyzers.canonical_auditor import analyze_canonicals
from app.analyzers.sitemap_orphan_analyzer import SitemapOrphanAnalyzer
from app.analyzers.heading_analyzer import HeadingAnalyzer, analyze_heading_hierarchy
from app.analyzers.media_asset_analyzer import MediaAssetAnalyzer, analyze_media_assets
from app.analyzers.link_depth import LinkDepthAnalyzer, analyze_link_depth_and_orphans


def test_grounded_remediation_patcher_url_specific():
    """Verify that RemediationPatcher produces real, page-grounded code patches for each distinct issue."""
    bp = BusinessProfile(
        business_name="Acme Cloud",
        niche="Kubernetes Security",
        value_proposition="Automated zero-trust container security and policy enforcement.",
        target_audience="DevOps and security engineers"
    )

    findings = [
        Finding(
            finding_id="f_title_pricing",
            category=Category.ON_PAGE_SEO,
            severity=Severity.HIGH,
            title="Missing Title Tag on /pricing",
            description="The page /pricing completely lacks a document <title> tag.",
            recommendation="Add a descriptive title tag containing primary commercial keywords.",
            evidence=[FindingEvidence(url="https://acme.io/pricing", element="title", value="MISSING")]
        ),
        Finding(
            finding_id="f_meta_about",
            category=Category.ON_PAGE_SEO,
            severity=Severity.MEDIUM,
            title="Missing Meta Description on /about",
            description="Page /about does not have a meta description.",
            recommendation="Add a compelling meta description between 140-160 characters.",
            evidence=[FindingEvidence(url="https://acme.io/about", element="meta[name='description']", value="MISSING")]
        ),
        Finding(
            finding_id="f_canon_blog",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Relative Canonical Tag on /blog",
            description="Page /blog specifies a relative canonical URL '/blog'.",
            recommendation="Convert canonical tag to an absolute URL.",
            evidence=[FindingEvidence(url="https://acme.io/blog", element="link[rel='canonical']", value="/blog")]
        ),
        Finding(
            finding_id="f_h1_multi",
            category=Category.ON_PAGE_SEO,
            severity=Severity.MEDIUM,
            title="Multiple <h1> Headings on /features",
            description="Page /features contains 2 separate <h1> elements.",
            recommendation="Demote redundant H1s to H2 to establish a single primary heading.",
            evidence=[FindingEvidence(url="https://acme.io/features", element="h1", value="Secondary Headline")]
        ),
        Finding(
            finding_id="f_broken_link",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="HTTP 404 Error on /old-docs",
            description="Server returns HTTP 404 for /old-docs.",
            recommendation="Configure a permanent 301 redirect to the active documentation path.",
            evidence=[FindingEvidence(url="https://acme.io/old-docs", element="http_status", value="404")]
        ),
    ]

    pages = [
        PageEvidence(url="https://acme.io/pricing", status_code=200, title=None),
        PageEvidence(url="https://acme.io/about", status_code=200, meta_description=None),
        PageEvidence(url="https://acme.io/blog", status_code=200, canonical_url="/blog"),
        PageEvidence(url="https://acme.io/features", status_code=200, h1=["Primary Headline", "Secondary Headline"]),
        PageEvidence(url="https://acme.io/old-docs", status_code=404),
    ]

    patcher = RemediationPatcher()
    patches = patcher.generate_patches(findings, bp, "https://acme.io", pages=pages)

    assert len(patches) >= 5

    # 1. Title patch for /pricing
    title_patch = next((p for p in patches if "pricing" in p.title.lower() or "pricing" in p.target_file.lower()), None)
    assert title_patch is not None
    assert "<title>" in title_patch.after_snippet
    assert "Acme Cloud" in title_patch.after_snippet
    assert len(title_patch.after_snippet.replace("<title>", "").replace("</title>", "")) <= 60

    # 2. Meta description patch for /about
    meta_patch = next((p for p in patches if "meta description" in p.title.lower() and "about" in p.title.lower()), None)
    assert meta_patch is not None
    assert '<meta name="description" content="' in meta_patch.after_snippet
    assert "Acme Cloud" in meta_patch.after_snippet

    # 3. Canonical patch for /blog
    canon_patch = next((p for p in patches if "canonical" in p.title.lower() and "blog" in p.title.lower()), None)
    assert canon_patch is not None
    assert 'href="https://acme.io/blog"' in canon_patch.after_snippet

    # 4. Heading patch for /features
    h1_patch = next((p for p in patches if "heading" in p.title.lower() or "h1" in p.title.lower() or "demote" in p.title.lower()), None)
    assert h1_patch is not None
    assert ("<h2" in h1_patch.after_snippet or "<h1" in h1_patch.after_snippet)

    # 5. Redirect patch for /old-docs
    redir_patch = next((p for p in patches if "redirect" in p.title.lower()), None)
    assert redir_patch is not None
    assert "/old-docs" in redir_patch.after_snippet
    assert "301" in redir_patch.after_snippet


def test_universal_patch_engine_typed_grounded_patches():
    """Verify that UniversalPatchEngine outputs typed RemediationPatch objects with real before/after snippets."""
    bp = BusinessProfile(
        business_name="DataCore",
        niche="Lakehouse Storage",
        value_proposition="High-concurrency cloud data warehouse acceleration.",
    )

    finding = Finding(
        finding_id="f_title_home",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Missing Title Tag",
        description="Homepage lacks a title tag.",
        recommendation="Add a title tag containing brand and value proposition.",
        evidence=[FindingEvidence(url="https://datacore.ai/", element="title", snippet="<!-- Missing title -->")]
    )

    engine = UniversalPatchEngine()
    patches = engine.generate_patches([finding], bp, website_url="https://datacore.ai")

    assert len(patches) > 0
    title_p = next((p for p in patches if p.finding_id == "f_title_home"), None)
    assert title_p is not None
    assert title_p.risk_level == PatchRiskLevel.HUMAN_APPROVAL
    assert "<title>DataCore" in title_p.after_snippet
    assert not title_p.is_blocked


def test_sitemap_hygiene_auditor():
    """Verify SitemapOrphanAnalyzer detects dirty URLs (non-200, noindex, and canonicalized) in XML sitemaps."""
    manifest = CrawlManifest(
        base_url="https://example.com",
        sitemap_found=True,
        sitemap_url="https://example.com/sitemap.xml",
        sitemap_urls=[
            "https://example.com/",
            "https://example.com/redirect-page",
            "https://example.com/broken-page",
            "https://example.com/noindex-page",
            "https://example.com/canonicalized-page",
        ],
        pages=[
            PageEvidence(url="https://example.com/", status_code=200, canonical_url="https://example.com/"),
            PageEvidence(url="https://example.com/redirect-page", status_code=301),
            PageEvidence(url="https://example.com/broken-page", status_code=404),
            PageEvidence(url="https://example.com/noindex-page", status_code=200, robots_meta="noindex, nofollow"),
            PageEvidence(url="https://example.com/canonicalized-page", status_code=200, canonical_url="https://example.com/target-page"),
        ]
    )

    analyzer = SitemapOrphanAnalyzer()
    res = analyzer.analyze(manifest)

    assert "findings" in res
    assert res["summary"]["dirty_sitemap_urls_count"] == 4
    dirty_finding = next((f for f in res["findings"] if "finding_sitemap_hygiene" in f.finding_id), None)
    assert dirty_finding is not None
    assert dirty_finding.severity == Severity.HIGH
    assert len(dirty_finding.evidence) == 4


def test_canonical_auditor_redirect_and_noindex_conflicts():
    """Verify CanonicalAuditor flags redirecting canonical targets and noindex contradictions."""
    pages = [
        PageEvidence(
            url="https://example.com/page-a",
            canonical_url="https://example.com/page-b",
            status_code=200,
        ),
        PageEvidence(
            url="https://example.com/page-b",
            status_code=301,  # Target is a redirect
        ),
        PageEvidence(
            url="https://example.com/private-page",
            canonical_url="https://example.com/private-page",
            status_code=200,
            robots_meta="noindex, follow",  # Contradiction: noindex + self-canonical
        ),
        PageEvidence(
            url="https://example.com/tracked-page",
            canonical_url="https://example.com/tracked-page?utm_source=twitter",
            status_code=200,  # Canonical has tracking params
        )
    ]

    rollup, findings = analyze_canonicals(pages)
    assert any(it.status == "redirect_target" for it in rollup.items)
    assert any(it.status == "noindex_conflict" for it in rollup.items)
    assert any(it.status == "tracking_params" for it in rollup.items)
    assert any(f.finding_id == "finding_canonical_noindex_conflict" for f in findings)


def test_heading_analyzer_empty_h1_and_findings():
    """Verify HeadingAnalyzer flags empty H1s and generates structured findings."""
    pages = [
        PageEvidence(url="https://example.com/page1", h1=["   "]),  # whitespace-only
        PageEvidence(url="https://example.com/page2", h1=["Section A", "Section B"]),  # multiple
        PageEvidence(url="https://example.com/page3", word_count=800, h1=["Valid Title"], h2=[]),  # long article without H2
    ]

    rollup = analyze_heading_hierarchy(pages)
    findings = HeadingAnalyzer.generate_findings(rollup)

    assert len(rollup.missing_h1) >= 1
    assert len(rollup.multiple_h1) == 1
    assert len(rollup.hierarchy_violations) >= 1
    assert any(f.finding_id == "finding_heading_missing_h1" for f in findings)
    assert any(f.finding_id == "finding_heading_multiple_h1" for f in findings)
    assert any(f.finding_id == "finding_heading_hierarchy_skips" for f in findings)


def test_media_asset_analyzer_generate_findings():
    """Verify MediaAssetAnalyzer creates findings for missing alt and CLS dimensions."""
    pages = [
        PageEvidence(
            url="https://example.com/gallery",
            total_images=5,
            images_without_alt=3,
            raw_html="""<html><body>
                <img src="/img/1.png">
                <img src="/img/2.png" alt="Valid alt">
                <img src="/img/3.jpg" alt="">
            </body></html>"""
        )
    ]

    report = analyze_media_assets(pages)
    findings = MediaAssetAnalyzer.generate_findings(report)

    assert report.total_images_analyzed >= 3
    assert len(findings) >= 1
    assert any(f.finding_id in ("finding_missing_image_alt", "finding_image_cls_risk") for f in findings)


def test_link_depth_analyzer_generate_findings():
    """Verify LinkDepthAnalyzer detects deep pages (depth 4+) and sitemap orphans."""
    pages = [
        PageEvidence(url="https://example.com/", internal_links=["https://example.com/deep1"]),
        PageEvidence(url="https://example.com/deep1", internal_links=["https://example.com/deep2"]),
        PageEvidence(url="https://example.com/deep2", internal_links=["https://example.com/deep3"]),
        PageEvidence(url="https://example.com/deep3", internal_links=["https://example.com/deep4"]),
        PageEvidence(url="https://example.com/deep4", internal_links=[]),
    ]

    cd, orphans, anchors = analyze_link_depth_and_orphans(
        pages,
        sitemap_urls=["https://example.com/", "https://example.com/orphan-landing"],
        homepage_url="https://example.com/"
    )

    findings = LinkDepthAnalyzer.generate_findings(cd, orphans, anchors)

    assert cd.depth_4_plus_count >= 1
    assert orphans.orphan_count >= 1
    assert any(f.finding_id == "finding_excessive_click_depth" for f in findings)
    assert any(f.finding_id == "finding_orphan_sitemap_pages" for f in findings)
