"""
Test Suite — Enterprise Crawling & Ingestion (Phase 1.1 to Phase 1.6)

Verifies:
1. Phase 1.1: 13-Adapter URL discovery, canonical resolution, normalization, and facet classification.
2. Phase 1.2: Crawl profiles (Quick, Standard, Deep, Enterprise), priority queue, and rate limiting.
3. Phase 1.3: Dual inspection modes (Mode A: HTTP network probe vs Mode B: Browser DOM execution).
4. Phase 1.4: 14-page classification and DOM structural template archetype clustering.
5. Phase 1.5: Evidence snapshot engine, content-addressed storage, and independent retrieval.
6. Phase 1.6: Crawl quality and multi-dimensional coverage intelligence.
"""
import pytest
import asyncio
from pathlib import Path

from app.crawl.url_discovery import (
    UrlNormalizer,
    UrlDiscoveryEngine,
    DiscoveredUrl,
)
from app.crawl.orchestration import (
    CrawlProfile,
    CrawlBudgetConfig,
    PriorityCrawlQueue,
    CrawlScheduler,
)
from app.crawl.inspection_modes import (
    HttpInspector,
    BrowserInspector,
    HttpInspectionResult,
    BrowserInspectionResult,
)
from app.crawl.template_discovery import (
    StandardPageType,
    PageClassifier,
    TemplateClusterEngine,
    TemplateArchetype,
)
from app.crawl.snapshot_engine import (
    SnapshotEngine,
    FullPageSnapshotRecord,
)
from app.crawl.coverage_reporter import (
    CrawlCoverageReporter,
    CrawlCoverageReport,
)


def test_phase1_1_url_discovery_adapters_and_normalization():
    """Verify URL normalizer strips tracking parameters, detects facets/pagination, and adapters extract URLs."""
    # 1. Normalization & Facet Detection
    dirty_url = "https://www.example.com/products/sonic-brush/?utm_source=google&color=navy&fbclid=123#reviews"
    norm_url, url_hash, is_faceted, is_pagination = UrlNormalizer.normalize(dirty_url, "example.com")
    
    assert "utm_source" not in norm_url
    assert "fbclid" not in norm_url
    assert "#reviews" not in norm_url
    assert "color=navy" in norm_url
    assert is_faceted is True
    assert is_pagination is False
    assert len(url_hash) == 64

    # 2. XML Sitemap Discovery
    sample_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/</loc></url>
        <url><loc>https://example.com/products/toothbrush</loc></url>
        <url><loc>https://example.com/blog/oral-health?page=2</loc></url>
    </urlset>
    """
    discovered = UrlDiscoveryEngine.parse_xml_sitemap(sample_sitemap, "example.com")
    assert len(discovered) == 3
    assert any(u.priority_tier == 0 for u in discovered)  # Home
    assert any(u.is_pagination for u in discovered)       # page=2

    # 3. Sitemap Index Recursion
    sample_index = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>https://example.com/sitemap_products.xml</loc></sitemap>
        <sitemap><loc>https://example.com/sitemap_pages.xml</loc></sitemap>
    </sitemapindex>"""
    child_sitemaps = UrlDiscoveryEngine.parse_sitemap_index(sample_index)
    assert len(child_sitemaps) == 2
    assert "https://example.com/sitemap_products.xml" in child_sitemaps

    # 4. Robots.txt discovery
    sample_robots = """
    User-agent: *
    Disallow: /checkout/
    Disallow: /admin/
    Sitemap: https://example.com/sitemap.xml
    Sitemap: https://example.com/sitemap_index.xml
    """
    sitemaps, disallows = UrlDiscoveryEngine.parse_robots_txt(sample_robots, "https://example.com")
    assert len(sitemaps) == 2
    assert len(disallows) == 2
    assert "/checkout/" in disallows

    # 5. Canonical URL extraction from HTML & HTTP header
    html_with_canon = '<html><head><link rel="canonical" href="https://example.com/authoritative-product" /></head></html>'
    canon1 = UrlDiscoveryEngine.extract_canonical_url(html_with_canon, None, "https://example.com/param-product")
    assert canon1 == "https://example.com/authoritative-product"

    header_link = '<https://example.com/header-canon>; rel="canonical"'
    canon2 = UrlDiscoveryEngine.extract_canonical_url("", header_link, "https://example.com/product")
    assert canon2 == "https://example.com/header-canon"

    # 6. Internal link discovery
    html_links = '<a href="/products/item-1">Item 1</a><a href="https://external.com/partner">External</a>'
    page_links = UrlDiscoveryEngine.extract_internal_links(html_links, "https://example.com/home", "example.com")
    assert len(page_links) == 2
    internal_links = [l for l in page_links if l.is_internal]
    external_links = [l for l in page_links if not l.is_internal]
    assert len(internal_links) == 1
    assert len(external_links) == 1


def test_phase1_2_crawl_orchestration_profiles_and_priority_queue():
    """Verify crawl profiles, priority queueing (P0 Home first), and scheduler exclusions."""
    # 1. Config from profiles
    quick_cfg = CrawlBudgetConfig.from_profile(CrawlProfile.QUICK)
    assert quick_cfg.max_pages == 25
    assert quick_cfg.max_concurrency == 3

    ent_cfg = CrawlBudgetConfig.from_profile(CrawlProfile.ENTERPRISE)
    assert ent_cfg.max_pages == 5000
    assert ent_cfg.max_concurrency == 8

    # 2. Priority queue ordering
    queue = PriorityCrawlQueue()
    u_blog = DiscoveredUrl(
        raw_url="https://example.com/blog/news",
        normalized_url="https://example.com/blog/news",
        url_hash="hash_blog",
        discovery_source="INTERNAL",
        priority_tier=2, # Content
    )
    u_home = DiscoveredUrl(
        raw_url="https://example.com/",
        normalized_url="https://example.com/",
        url_hash="hash_home",
        discovery_source="INTERNAL",
        priority_tier=0, # Home
    )
    u_prod = DiscoveredUrl(
        raw_url="https://example.com/products/item",
        normalized_url="https://example.com/products/item",
        url_hash="hash_prod",
        discovery_source="INTERNAL",
        priority_tier=1, # Commercial
    )

    # Push in reverse priority order: Blog -> Home -> Prod
    queue.push(u_blog)
    queue.push(u_home)
    queue.push(u_prod)

    # Must pop in priority order: Home (0) -> Prod (1) -> Blog (2)
    first_popped = queue.pop()
    assert first_popped.priority_tier == 0
    assert first_popped.normalized_url == "https://example.com/"

    second_popped = queue.pop()
    assert second_popped.priority_tier == 1

    third_popped = queue.pop()
    assert third_popped.priority_tier == 2

    # 3. Scheduler exclusion
    scheduler = CrawlScheduler(
        run_id="RUN_ORCH_01",
        config=CrawlBudgetConfig(
            max_pages=10,
            excluded_path_regexes=[r"/cart", r"/checkout", r"/account"],
        ),
    )
    u_cart = DiscoveredUrl(
        raw_url="https://example.com/cart",
        normalized_url="https://example.com/cart",
        url_hash="hash_cart",
        discovery_source="INTERNAL",
    )
    assert scheduler.schedule_url(u_cart) is False
    assert "https://example.com/cart" in scheduler.excluded_urls


def test_phase1_3_dual_inspection_modes():
    """Verify Mode A (HTTP inspection) and Mode B (Browser inspection) extract expected telemetry."""
    # 1. Mode A: HTTP Inspection
    http_result = HttpInspector.inspect(
        url="https://example.com/product-1",
        status_code=200,
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Content-Encoding": "gzip",
            "Cache-Control": "public, max-age=3600",
            "X-Robots-Tag": "index, follow",
            "Link": '<https://example.com/canon-product>; rel="canonical"',
        },
        raw_html="<html><body><h1>Raw HTML Title</h1></body></html>",
        ttfb_ms=288.5,
    )
    assert http_result.status_code == 200
    assert http_result.is_compressed is True
    assert http_result.ttfb_ms == 288.5
    assert http_result.http_canonical == "https://example.com/canon-product"
    assert http_result.x_robots_tag == "index, follow"

    # 2. Mode B: Browser Inspection (Rendered DOM & JS Delta)
    raw_html = "<html><body><div id='app'>Loading...</div></body></html>"
    rendered_dom = "<html><body><div id='app'><button id='buy'>Buy Now</button><img loading='lazy' src='brush.jpg' /></div></body></html>"
    
    browser_result = BrowserInspector.inspect(
        url="https://example.com/product-1",
        raw_html=raw_html,
        rendered_html=rendered_dom,
        viewport="DESKTOP",
        console_errors=["Uncaught TypeError in analytics.js"],
        failed_resources=["https://cdn.example.com/missing-font.woff2"],
        screenshot_bytes=b"fake_png_bytes",
    )
    assert browser_result.viewport == "DESKTOP"
    assert browser_result.js_content_delta_bytes > 0
    assert browser_result.interactive_elements_count >= 1
    assert browser_result.lazy_images_count == 1
    assert len(browser_result.console_errors) == 1
    assert browser_result.screenshot_hash is not None


def test_phase1_4_page_classification_and_template_clustering():
    """Verify 14 standard page types and AST DOM structural template clustering."""
    # 1. Page Classification
    assert PageClassifier.classify("https://example.com/") == StandardPageType.HOMEPAGE
    assert PageClassifier.classify("https://example.com/products/sonic-brush") == StandardPageType.PRODUCT
    assert PageClassifier.classify("https://example.com/collections/oral-care") == StandardPageType.COLLECTION
    assert PageClassifier.classify("https://example.com/pricing", title="Pricing Plans") == StandardPageType.PRICING
    assert PageClassifier.classify("https://example.com/blog/gum-health-tips") == StandardPageType.BLOG_ARTICLE
    assert PageClassifier.classify("https://example.com/faq") == StandardPageType.FAQ
    assert PageClassifier.classify("https://example.com/contact-us") == StandardPageType.CONTACT
    assert PageClassifier.classify("https://example.com/checkout") == StandardPageType.CHECKOUT

    # 2. Template Clustering
    # Create 4 mock product pages sharing the exact same DOM skeleton
    product_skeleton = """
    <html>
      <header><nav><a href='/'>Home</a></nav></header>
      <main>
        <section class='product-hero'><h1>Product</h1><button>Buy</button></section>
        <section class='product-reviews'><h2>Reviews</h2></section>
      </main>
      <footer><p>Footer</p></footer>
    </html>
    """
    article_skeleton = """
    <html>
      <header><nav><a href='/'>Home</a></nav></header>
      <main>
        <article class='blog-post'><h1>Article</h1><p>Content</p></article>
        <aside><h3>Related Posts</h3></aside>
      </main>
      <footer><p>Footer</p></footer>
    </html>
    """

    pages = [
        {"url": "https://example.com/products/item-1", "html": product_skeleton, "page_type": StandardPageType.PRODUCT},
        {"url": "https://example.com/products/item-2", "html": product_skeleton, "page_type": StandardPageType.PRODUCT},
        {"url": "https://example.com/products/item-3", "html": product_skeleton, "page_type": StandardPageType.PRODUCT},
        {"url": "https://example.com/blog/article-1", "html": article_skeleton, "page_type": StandardPageType.BLOG_ARTICLE},
    ]

    archetypes = TemplateClusterEngine.cluster_urls_into_templates(pages)
    
    # 3 products + 1 blog article must group into exactly 2 template archetypes
    assert len(archetypes) == 2
    product_tpl = next(t for t in archetypes if t.dominant_page_type == StandardPageType.PRODUCT)
    blog_tpl = next(t for t in archetypes if t.dominant_page_type == StandardPageType.BLOG_ARTICLE)

    assert len(product_tpl.member_urls) == 3
    assert len(blog_tpl.member_urls) == 1


def test_phase1_5_evidence_snapshot_engine():
    """Verify content-addressed snapshot storage and retrieval."""
    engine = SnapshotEngine(run_id="RUN_SNAP_TEST01")
    
    canonical_snap, full_record = engine.capture_and_store_snapshot(
        domain_id="example.com",
        page_id="pg_001",
        url="https://example.com/about",
        raw_html="<html><body><h1>About Us</h1></body></html>",
        rendered_dom="<html><body><h1>About Us</h1><p>Dynamic Content</p></body></html>",
        status_code=200,
        headers={"Content-Type": "text/html"},
        ttfb_ms=210.0,
        extracted_headings=["About Us"],
    )

    assert canonical_snap.page_id == "pg_001"
    assert canonical_snap.rendered_dom_captured is True
    assert canonical_snap.snapshot_id.startswith("snap_")

    # Independent retrieval without recrawling
    retrieved = engine.retrieve_snapshot(canonical_snap.snapshot_id)
    assert retrieved is not None
    assert retrieved.url == "https://example.com/about"
    assert retrieved.ttfb_ms == 210.0
    assert "About Us" in retrieved.extracted_headings


def test_phase1_6_crawl_quality_and_coverage_intelligence():
    """Verify multi-dimensional crawl coverage reporting breaking down by page-type and template."""
    discovered = [f"https://example.com/page-{i}" for i in range(500)]
    
    # 25 crawled pages across different types
    crawled = [
        {"url": "https://example.com/", "page_type": StandardPageType.HOMEPAGE.value, "is_rendered": True},
        {"url": "https://example.com/pricing", "page_type": StandardPageType.PRICING.value, "is_rendered": True},
    ] + [
        {"url": f"https://example.com/products/item-{i}", "page_type": StandardPageType.PRODUCT.value, "is_rendered": True}
        for i in range(15)
    ] + [
        {"url": f"https://example.com/blog/post-{i}", "page_type": StandardPageType.BLOG_ARTICLE.value, "is_rendered": False}
        for i in range(8)
    ]

    report, canonical_inv = CrawlCoverageReporter.generate_coverage_report(
        audit_run_id="RUN_COV_01",
        domain="example.com",
        profile_used=CrawlProfile.QUICK,
        discovered_urls=discovered,
        crawled_urls=crawled,
        excluded_urls=["https://example.com/cart"],
    )

    assert report.discovered_urls == 500
    assert report.crawled_urls == 25
    assert report.overall_coverage_pct == 5.0  # (25 / 499) * 100 ~ 5.0%
    assert len(report.page_type_coverage) >= 3
    assert report.inspection_method_breakdown["HTTP_INSPECTION"] == 25
    assert report.inspection_method_breakdown["BROWSER_RENDERED"] == 17
    assert "5.0% sample coverage" in report.honest_coverage_statement
    assert canonical_inv.discovered_urls_count == 500
    assert canonical_inv.inspected_urls_count == 25
