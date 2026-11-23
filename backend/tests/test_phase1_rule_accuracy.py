"""Phase 1 Gate: Rule Accuracy & False-Positive Regression Tests (perforacare.com RUN_D47F4DC8)."""
from __future__ import annotations

from bs4 import BeautifulSoup
from app.crawl.analyzers.dom import analyze_dom_structure
from app.crawl.crawler import compute_ttfb_stats
from app.cro.accessibility.wcag_auditor import DeepWcagAuditor
from app.domain.evidence.deterministic_rules import DeterministicFindingEngine
from app.domain.evidence.rule_catalog import (
    RULE_CATALOG,
    is_non_html_utility_url,
    is_skip_link,
    list_rules,
)
from app.domain.evidence.store import EvidenceStore
from app.domain.models import CrawlManifest, PageEvidence
from app.evidence.store import EvidenceStore as LegacyEvidenceStore
from app.seo.analyzers.link_depth import LinkDepthAnalyzer
from app.seo.analyzers.local_seo_analyzer import analyze_local_seo
from app.seo.analyzers.sitemap_orphan_analyzer import SitemapOrphanAnalyzer
from app.seo.audit.remediation.post_audit_remediation_engine import (
    PlatformType,
    PostAuditRemediationEngine,
)


def test_rule_catalog_has_required_metadata():
    rules = list_rules()
    assert len(rules) >= 12
    for r in rules:
        assert r["rule_id"]
        assert r["input"]
        assert r["threshold"]
        assert r["applicable_site_types"]
        assert r["standard_version"]
    assert "TTFB_P1" in RULE_CATALOG


def test_non_html_urls_excluded_from_orphan_and_depth_and_zero_edges_unmeasured():
    assert is_non_html_utility_url("https://perforacare.com/sitemap.xml")
    assert is_non_html_utility_url("https://perforacare.com/robots.txt")
    assert not is_non_html_utility_url("https://perforacare.com/products/lemon-mint-probiotic-rinse")

    pages = [
        PageEvidence(url="https://perforacare.com/", status_code=200, internal_links=[]),
        PageEvidence(url="https://perforacare.com/sitemap.xml", status_code=200, internal_links=[]),
        PageEvidence(url="https://perforacare.com/products/rinse", status_code=200, internal_links=[]),
    ]
    cd = LinkDepthAnalyzer.analyze_click_depth(pages, "https://perforacare.com/")
    orphans = LinkDepthAnalyzer.detect_orphans(
        pages,
        ["https://perforacare.com/sitemap.xml", "https://perforacare.com/products/rinse"],
        "https://perforacare.com/",
    )
    assert cd.status == "UNMEASURED"
    assert orphans.status == "UNMEASURED"
    findings = LinkDepthAnalyzer.generate_findings(cd, orphans, LinkDepthAnalyzer.audit_anchor_texts(pages))
    assert not any(f.finding_id in ("finding_excessive_click_depth", "finding_orphan_sitemap_pages") for f in findings)

    manifest = CrawlManifest(
        domain="perforacare.com",
        base_url="https://perforacare.com/",
        pages=pages,
        sitemap_urls=["https://perforacare.com/sitemap.xml", "https://perforacare.com/products/rinse"],
        orphan_urls=["https://perforacare.com/sitemap.xml"],
    )
    res = SitemapOrphanAnalyzer().analyze(manifest)
    assert res["summary"]["status"] == "UNMEASURED"
    assert res["findings"] == []


def test_local_seo_gated_on_local_signals_not_d2c_phone():
    # D2C Shopify store with a support phone and bogus numeric token — no address, no LocalBusiness
    pages = [
        PageEvidence(
            url="https://perforacare.com/",
            status_code=200,
            nap_data={"phone_numbers": ["+91 98765 43210", "1234567"]},
            raw_schema=[{"@type": "Organization", "name": "Perfora"}],
        ),
        PageEvidence(
            url="https://perforacare.com/products/rinse",
            status_code=200,
            nap_data={"phone_numbers": ["+91 88888 77777"]},
        ),
    ]
    report, findings = analyze_local_seo(pages, target_domain="perforacare.com")
    assert report.status == "NOT_APPLICABLE"
    assert findings == []


def test_wcag_22_removes_411_and_accepts_aria_label_close():
    html = """
    <html lang="en">
      <head><title>Perfora</title></head>
      <body>
        <main>
          <h1>Perfora Oral Care</h1>
          <svg><defs><clipPath id="clip0"></clipPath><clipPath id="clip0"></clipPath></defs></svg>
          <button aria-label="Close"><svg><path d="M0 0"></path></svg></button>
        </main>
      </body>
    </html>
    """
    page = PageEvidence(
        url="https://perforacare.com/",
        status_code=200,
        title="Perfora",
        h1=["Perfora Oral Care"],
        raw_html=html,
    )
    res, _ = DeepWcagAuditor.audit_pages([page])
    rule_ids = {v.rule_id for v in res.violations}
    assert "WCAG_4_1_1_DUPLICATE_ID" not in rule_ids
    assert "WCAG_4_1_2_ACCESSIBLE_NAMES" not in rule_ids


def test_skip_link_ignored_by_cta_detection():
    assert is_skip_link("Skip to content", "#MainContent", "skip-to-content-link")
    html = """
    <html><body>
      <a href="#MainContent" class="skip-to-content-link">Skip to content</a>
      <main id="MainContent">
        <a href="/products/brush" class="btn-primary">Shop Now</a>
      </main>
    </body></html>
    """
    store = LegacyEvidenceStore(run_id="test_skip")
    dom = analyze_dom_structure(BeautifulSoup(html, "html.parser"), "https://perforacare.com/", store)
    assert all("skip" not in c.lower() for c in dom["cta_candidates"])


def test_ttfb_p1_emits_over_800ms_and_excludes_zero_from_stats_and_reads_jsonld():
    stats = compute_ttfb_stats([
        {"url": "https://perforacare.com/", "ttfb_ms": 2809.0},
        {"url": "https://perforacare.com/p1", "ttfb_ms": 0.0},
        {"url": "https://perforacare.com/p2", "ttfb_ms": 400.0},
    ])
    assert stats.min_ms == 400.0
    assert stats.mean_ms == 1604.5

    store = EvidenceStore(run_id="run_test")
    store.add_observation(url="https://perforacare.com/", attribute="ttfb_ms", value=2809.0, source="http")
    store.add_observation(url="https://perforacare.com/p1", attribute="ttfb_ms", value=0.0, source="http")
    store.add_observation(url="https://perforacare.com/", attribute="schema_types", value=[], source="dom")

    manifest = CrawlManifest(
        domain="perforacare.com",
        base_url="https://perforacare.com/",
        pages=[
            PageEvidence(
                url="https://perforacare.com/",
                status_code=200,
                ttfb_ms=2809.0,
                canonical_url="",
                raw_schema=[{"@type": "Organization", "name": "Perfora"}, {"@type": "WebSite", "name": "Perfora"}],
            )
        ],
    )
    engine = DeterministicFindingEngine()
    findings = engine.evaluate(store, manifest=manifest)
    rule_ids = {f.rule_id for f in findings}
    finding_ids = {f.finding_id for f in findings}
    assert "TTFB_P1" in rule_ids
    assert "SCHEMA_MISSING_001" not in rule_ids
    assert "finding_missing_canonicals" in finding_ids
    assert any(p["rule_id"] == "SCHEMA_MISSING_001" for p in engine.passed_checks)


def test_remediation_engine_has_no_placeholders_or_wrong_shopify_template():
    engine = PostAuditRemediationEngine()
    h1_home = engine._generate_h1_fix(PlatformType.SHOPIFY, "HIGH", ["https://perforacare.com/"])
    assert "main-product.liquid" not in h1_home.target_file_pattern
    h1_prod = engine._generate_h1_fix(PlatformType.SHOPIFY, "HIGH", ["https://perforacare.com/products/rinse"])
    assert "main-product.liquid" in h1_prod.target_file_pattern

    idx_fix = engine._generate_indexability_fix(PlatformType.SHOPIFY, "HIGH", ["https://perforacare.com/"])
    assert "yourdomain.com" not in idx_fix.code_diff_snippet
    assert "perforacare.com" in idx_fix.code_diff_snippet

    schema_fix = engine._generate_schema_fix(PlatformType.SHOPIFY, "HIGH", ["https://perforacare.com/"])
    assert "Verified Brand Name" not in schema_fix.code_diff_snippet
    assert "yourdomain.com" not in schema_fix.code_diff_snippet
    assert "perforacare.com" in schema_fix.code_diff_snippet
