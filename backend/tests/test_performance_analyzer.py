"""
Unit tests for Dristik Enterprise Performance Analyzer & Two-Tier Architecture.
Verifies true server TTFB extraction, render-blocking detection, payload breakdown,
and honest fail-closed handling between deterministic Lab and CrUX Field data.
"""
import pytest
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.performance import analyze_performance_metrics
from app.agents.runtime.registry import SPECIALIST_AGENTS_V3
from app.agents.runtime.specialist import SpecialistAgent
from app.domain.models import CrawlManifest, PageEvidence, LabPerformanceMetrics, FieldPerformanceMetrics
from app.cognition.blackboard import CognitiveBlackboard


def test_analyze_performance_metrics_extracts_lab_data():
    store = EvidenceStore("run_test_perf")
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fast Enterprise Site</title>
        <link rel="stylesheet" href="/assets/main.css">
        <link rel="stylesheet" href="/assets/print.css" media="print">
        <script src="/js/blocking-bundle.js"></script>
        <script src="/js/async-bundle.js" async></script>
        <script src="https://www.google-analytics.com/analytics.js" async></script>
        <script src="https://static.hotjar.com/c/hotjar-123.js" async></script>
        <link rel="preload" href="/fonts/inter.woff2" as="font">
    </head>
    <body>
        <h1>Enterprise Architecture</h1>
        <img src="/img/hero.jpg" width="1200" height="600">
        <img src="/img/logo.png">
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    headers = {
        "content-encoding": "br",
        "cache-control": "public, max-age=31536000, immutable",
        "server": "cloudflare",
    }
    timing_data = {
        "ttfb_ms": 145.2,
        "dns_ms": 18.5,
        "tcp_ms": 22.1,
        "tls_ms": 31.0,
        "download_ms": 42.0,
        "dom_content_loaded_ms": 480.0,
        "load_event_ms": 720.0,
        "fcp_ms": 380.0,
        "total_transferred_bytes": 102400,
        "js_bytes": 45000,
        "css_bytes": 15000,
        "img_bytes": 35000,
        "font_bytes": 7400,
        "total_requests": 6,
    }
    dom_data = {
        "image_assets": [
            {"url": "/img/hero.jpg", "has_dimensions": True},
            {"url": "/img/logo.png", "has_dimensions": False},
        ]
    }

    res = analyze_performance_metrics(
        url="https://acme.com",
        ttfb_ms=145.2,
        content_length_bytes=102400,
        headers=headers,
        evidence_store=store,
        soup=soup,
        timing_data=timing_data,
        dom_data=dom_data,
    )

    assert res["ttfb_ms"] == 145.2
    assert res["is_compressed"] is True
    assert res["content_encoding"] == "br"
    assert res["server"] == "cloudflare"

    lab: LabPerformanceMetrics = res["lab_performance"]
    assert lab is not None
    assert lab.ttfb_ms == 145.2
    assert lab.fcp_ms == 380.0
    assert lab.dns_ms == 18.5
    assert lab.tcp_ms == 22.1
    assert lab.tls_ms == 31.0
    assert lab.caching_policy == "LONG_CACHE"
    assert lab.font_display_strategy == "PRELOADED_FONTS"

    # Render-blocking: /assets/main.css and /js/blocking-bundle.js (print.css and async-bundle.js excluded)
    assert lab.render_blocking_count == 2
    blocking_urls = [r["url"] for r in lab.render_blocking_resources]
    assert "/assets/main.css" in blocking_urls
    assert "/js/blocking-bundle.js" in blocking_urls
    assert "/js/async-bundle.js" not in blocking_urls

    # Third-party scripts detected: google-analytics, hotjar
    assert lab.third_party_scripts_count == 2
    assert any("google-analytics.com" in d for d in lab.third_party_domains)
    assert any("hotjar.com" in d for d in lab.third_party_domains)

    # Images missing dimensions (1 of 2)
    assert lab.images_missing_dimensions == 1


from app.domain.enums import Severity


def test_specialist_seo_performance_distinguishes_lab_from_field():
    bb = CognitiveBlackboard(run_id="run_test_agent", website_url="https://enterprise.io")
    ev = bb.evidence_store.add_evidence(
        source_type="perf",
        analyzer="performance_analyzer",
        url="https://enterprise.io",
        text="Fast site lab performance",
        value={"ttfb_ms": 120.0},
    )

    page = PageEvidence(
        url="https://enterprise.io",
        status_code=200,
        ttfb_ms=120.0,
        lab_performance=LabPerformanceMetrics(
            ttfb_ms=120.0,
            fcp_ms=350.0,
            render_blocking_count=0,
            content_encoding="br",
            third_party_scripts_count=1,
            images_missing_dimensions=0,
        ),
    )
    bb.pages = [page]

    manifest = CrawlManifest(
        manifest_id="cm_perf_fast",
        domain="enterprise.io",
        base_url="https://enterprise.io",
        total_pages_discovered=1,
        pages=[page],
        crawl_health={"avg_ttfb_ms": 120.0},
    )
    bb.crawl_manifest = manifest

    specialist = SpecialistAgent(SPECIALIST_AGENTS_V3["seo.performance.v3"], model_router=None)
    res = specialist._deterministic_audit(bb, [ev])

    claims = bb.claim_registry.get_all()
    critical_or_high = [c for c in claims if c.severity in (Severity.CRITICAL, Severity.HIGH)]
    assert len(critical_or_high) == 0

    # CrUX should be recorded as UNMEASURED rather than inventing numbers
    assert res["observations"].get("crux_telemetry_status") == "UNMEASURED"
    assert res["observations"].get("avg_ttfb_ms") == 120.0
    assert res["observations"].get("render_blocking_count") == 0


def test_specialist_seo_performance_flags_slow_ttfb_and_render_blocking():
    bb = CognitiveBlackboard(run_id="run_test_slow", website_url="https://slow-site.com")
    ev = bb.evidence_store.add_evidence(
        source_type="perf",
        analyzer="performance_analyzer",
        url="https://slow-site.com",
        text="Slow site lab performance",
        value={"ttfb_ms": 3130.0},
    )

    page = PageEvidence(
        url="https://slow-site.com",
        status_code=200,
        ttfb_ms=3130.0,
        lab_performance=LabPerformanceMetrics(
            ttfb_ms=3130.0,
            fcp_ms=3600.0,
            render_blocking_count=4,
            content_encoding="none",
            third_party_scripts_count=8,
            images_missing_dimensions=5,
        ),
    )
    bb.pages = [page]

    manifest = CrawlManifest(
        manifest_id="cm_perf_slow",
        domain="slow-site.com",
        base_url="https://slow-site.com",
        total_pages_discovered=1,
        pages=[page],
        crawl_health={"avg_ttfb_ms": 3130.0},
    )
    bb.crawl_manifest = manifest

    specialist = SpecialistAgent(SPECIALIST_AGENTS_V3["seo.performance.v3"], model_router=None)
    res = specialist._deterministic_audit(bb, [ev])

    assert bb.claim_registry.get_all() == []
    assert res["claims"] == []
    statements = " ".join(
        item["fact"] for item in (res["observations"].get("measured_facts") or [])
    ).lower()
    assert "ttfb" in statements or "server response" in statements
    assert "render-blocking" in statements
    assert "compression" in statements
