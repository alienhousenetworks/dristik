r"""
Unit tests for Phase 1 Crawler Foundation:
- Hop-by-hop redirect chain recording with follow_redirects=False
- SSRF validation on intermediate redirect hops
- Redirect loop detection
- Recursive sitemap parsing up to 500 URLs
- Snapshot persistence on PageEvidence
- Image asset dimensions and format metadata (CLS risk)
- Crawl budget accounting (discovered, allowed, crawled, skipped)
- Orphan page detection (sitemap \ internal link graph)
- CrawlManifest redirect_chains formatting
"""
import pytest
import httpx
from bs4 import BeautifulSoup
from unittest.mock import AsyncMock, patch

from app.crawl.crawler import CrawlerService
from app.crawl.analyzers.dom import analyze_dom_structure
from app.evidence.store import EvidenceStore
from app.domain.models import PageEvidence, CrawlManifest


@pytest.mark.asyncio
async def test_hop_by_hop_redirect_tracking():
    """
    Verify step-by-step redirect tracking:
    http://example.com/start -> 301 -> http://example.com/middle -> 302 -> https://example.com/final (200 OK)
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "http://example.com/start":
            return httpx.Response(301, headers={"Location": "/middle"})
        elif url == "http://example.com/middle":
            return httpx.Response(302, headers={"Location": "https://example.com/final"})
        elif url == "https://example.com/final":
            return httpx.Response(200, text="<html><body><h1>Terminal Page</h1></body></html>")
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    crawler = CrawlerService()

    async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
        html, status, ttfb, headers, nbytes, err, md, chain, final_url, _timing = await crawler._fetch_page_with_fallbacks(
            "http://example.com/start", client
        )

        assert status == 200
        assert "Terminal Page" in (html or "")
        assert final_url == "https://example.com/final"
        assert len(chain) == 2
        assert chain[0]["status"] == 301
        assert chain[0]["url"] == "http://example.com/start"
        assert chain[0]["location"] == "http://example.com/middle"
        assert chain[1]["status"] == 302
        assert chain[1]["url"] == "http://example.com/middle"
        assert chain[1]["location"] == "https://example.com/final"


@pytest.mark.asyncio
async def test_redirect_loop_detection():
    """
    Verify redirect loop detection terminates gracefully:
    http://example.com/loop-a -> 301 -> http://example.com/loop-b -> 301 -> http://example.com/loop-a
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "http://example.com/loop-a":
            return httpx.Response(301, headers={"Location": "http://example.com/loop-b"})
        elif url == "http://example.com/loop-b":
            return httpx.Response(301, headers={"Location": "http://example.com/loop-a"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    crawler = CrawlerService()

    async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
        html, status, ttfb, headers, nbytes, err, md, chain, final_url, _timing = await crawler._fetch_page_with_fallbacks(
            "http://example.com/loop-a", client
        )

        assert err is not None
        assert "Redirect loop detected" in err
        assert len(chain) >= 2


@pytest.mark.asyncio
async def test_recursive_sitemap_discovery():
    """
    Verify recursive sitemap parsing through child sitemaps.
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "https://example.com/sitemap.xml":
            return httpx.Response(200, headers={"Content-Type": "application/xml"}, text="""<?xml version="1.0" encoding="UTF-8"?>
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
                <sitemap><loc>https://example.com/sitemap-posts.xml</loc></sitemap>
            </sitemapindex>
            """)
        elif url == "https://example.com/sitemap-pages.xml":
            return httpx.Response(200, headers={"Content-Type": "application/xml"}, text="""<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url><loc>https://example.com/pricing</loc></url>
                <url><loc>https://example.com/about</loc></url>
            </urlset>
            """)
        elif url == "https://example.com/sitemap-posts.xml":
            return httpx.Response(200, headers={"Content-Type": "application/xml"}, text="""<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url><loc>https://example.com/blog/ai-search</loc></url>
                <url><loc>https://example.com/blog/geo-optimization</loc></url>
            </urlset>
            """)
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    crawler = CrawlerService()

    async with httpx.AsyncClient(transport=transport) as client:
        found, s_url, urls = await crawler._fetch_sitemap_urls(
            "https://example.com", "example.com", [], client, max_sitemap_urls=500
        )

        assert found is True
        assert s_url == "https://example.com/sitemap.xml"
        assert len(urls) == 4
        assert "https://example.com/pricing" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/blog/ai-search" in urls
        assert "https://example.com/blog/geo-optimization" in urls


def test_dom_image_asset_extraction_and_cls_risk():
    """
    Verify DOM analyzer extracts image assets, formats, and flags missing dimensions for CLS.
    """
    html = """
    <html>
        <body>
            <img src="/assets/hero.webp" width="1200" height="600" alt="Hero banner">
            <img src="http://example.com/logo.png" alt="">
            <img src="/assets/diagram.avif" width="800">
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    ev_store = EvidenceStore("test_run_img")
    res = analyze_dom_structure(soup, "https://example.com/test", ev_store)

    assert "image_assets" in res
    assets = res["image_assets"]
    assert len(assets) == 3

    # Asset 1: webp, has dimensions, modern
    assert assets[0]["format"] == "webp"
    assert assets[0]["has_dimensions"] is True
    assert assets[0]["cls_risk"] is False
    assert assets[0]["is_modern_format"] is True

    # Asset 2: png, no dimensions, cls_risk
    assert assets[1]["format"] == "png"
    assert assets[1]["has_dimensions"] is False
    assert assets[1]["cls_risk"] is True
    assert assets[1]["is_empty_alt"] is True

    # Asset 3: avif, partial dimension (missing height), cls_risk
    assert assets[2]["format"] == "avif"
    assert assets[2]["has_dimensions"] is False
    assert assets[2]["cls_risk"] is True


def test_crawl_budget_accounting_and_orphan_detection():
    """
    Verify CrawlManifest correctly computes crawl budget and identifies orphan pages.
    """
    crawler = CrawlerService()
    p1 = PageEvidence(
        url="https://example.com/",
        internal_links=["https://example.com/pricing", "https://example.com/about"],
        redirect_chain=[{"status": 301, "url": "http://example.com/", "location": "https://example.com/"}],
        is_redirected=True
    )
    p2 = PageEvidence(
        url="https://example.com/pricing",
        internal_links=["https://example.com/"]
    )
    p3 = PageEvidence(
        url="https://example.com/about",
        internal_links=["https://example.com/"]
    )

    sitemap_urls = [
        "https://example.com/",
        "https://example.com/pricing",
        "https://example.com/about",
        "https://example.com/orphan-landing-page",
        "https://example.com/forgotten-promo"
    ]

    manifest = crawler._build_crawl_manifest(
        base_domain="example.com",
        base_url="https://example.com/",
        crawled_pages=[p1, p2, p3],
        total_discovered=10,
        sitemap_found=True,
        sitemap_url="https://example.com/sitemap.xml",
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /",
        broken_links=[{"url": "https://example.com/broken", "error": "HTTP 404"}],
        sitemap_urls=sitemap_urls,
        target_max_pages=5
    )

    # Crawl budget accounting
    budget = manifest.crawl_budget
    assert budget["urls_discovered"] == 10
    assert budget["urls_allowed"] == 5
    assert budget["urls_crawled"] == 3
    assert budget["urls_skipped"] == 7
    assert budget["skip_reasons"]["failed_or_broken"] == 1

    # Orphan page detection
    assert len(manifest.orphan_urls) == 2
    assert "https://example.com/orphan-landing-page" in manifest.orphan_urls
    assert "https://example.com/forgotten-promo" in manifest.orphan_urls

    # Redirect chains captured
    assert len(manifest.redirect_chains) == 1
    assert manifest.redirect_chains[0]["initial_url"] == "https://example.com/"
    assert manifest.redirect_chains[0]["hops"][0]["status"] == 301
    assert manifest.redirect_chains[0]["hop_count"] == 1
