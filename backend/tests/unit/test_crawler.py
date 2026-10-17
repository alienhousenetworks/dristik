"""URL frontier, robots parsing, and de-duplication."""
from app.crawl.deduplication import UrlDeduper
from app.crawl.robots import declared_sitemaps, parse_robots, sitewide_disallow
from app.crawl.url_frontier import UrlFrontier, normalize_url


def test_normalize_url_strips_tracking_and_index_files():
    normalized = normalize_url(
        "https://www.Example.com/pricing/index.html?utm_source=ad&plan=pro",
        "example.com",
        "https://example.com",
    )
    assert normalized == "https://www.example.com/pricing?plan=pro"


def test_frontier_admits_each_normalized_url_once():
    frontier = UrlFrontier("example.com", "https://example.com")
    first = frontier.admit("https://example.com/pricing/")
    second = frontier.admit("https://example.com/pricing")
    assert first == "https://example.com/pricing"
    assert second is None


def test_robots_sitemap_and_sitewide_disallow():
    body = "User-agent: *\nDisallow: /\nSitemap: https://example.com/sitemap.xml\n"
    assert declared_sitemaps(body) == ["https://example.com/sitemap.xml"]
    groups = parse_robots(body)
    assert groups[0].disallow == ["/"]
    assert sitewide_disallow(body) is True


def test_deduper_uses_the_same_normalization():
    deduper = UrlDeduper("example.com", "https://example.com")
    assert deduper.add("https://example.com/docs/index.html") is True
    assert deduper.add("https://example.com/docs") is False
