"""Crawler methods delegate to the shared frontier and robots parser."""
from app.crawl.crawler import CrawlerService
from app.crawl.robots import declared_sitemaps
from app.crawl.url_frontier import normalize_url


def test_crawler_uses_shared_url_rules():
    crawler = CrawlerService()
    raw = "https://example.com/about/?utm_campaign=spring"
    assert crawler._normalize_url(raw, "example.com", "https://example.com") == normalize_url(
        raw, "example.com", "https://example.com"
    )
    assert crawler._classify_page_type("/pricing") == "pricing"
    assert declared_sitemaps("Sitemap: https://example.com/sitemap.xml\n") == [
        "https://example.com/sitemap.xml"
    ]
