"""Fixture coverage for template defects and emulated mobile viewports.

These pages are labelled fixtures. They are not a live audit.
"""
import pytest

from app.crawl.coverage_reporter import CrawlCoverageReporter
from app.crawl.orchestration import CrawlProfile
from app.crawl.template_discovery import StandardPageType, build_page_template_intelligence
from app.seo.audit.crawlers.playwright_client import measure_emulated_devices
from app.seo.intelligence.mobile_experience import MobileExperienceEngine


PRODUCT_HTML = """
<html>
  <header><nav><a href="/">Home</a></nav></header>
  <main><section class="product-hero"><h1>Shoe</h1></section></main>
  <footer><p>Footer</p></footer>
</html>
"""
ARTICLE_HTML = """
<html>
  <header><nav><a href="/">Home</a></nav></header>
  <main><article class="blog-post"><h1>Note</h1><p>Body</p></article></main>
  <footer><p>Footer</p></footer>
</html>
"""


def test_shared_template_defect_does_not_condemn_unfetched_urls():
    pages = [
        {"url": "https://example.com/products/a", "raw_html": PRODUCT_HTML, "page_type": "PRODUCT"},
        {"url": "https://example.com/products/b", "raw_html": PRODUCT_HTML, "page_type": "PRODUCT"},
        {"url": "https://example.com/blog/one", "raw_html": ARTICLE_HTML, "page_type": "BLOG_ARTICLE"},
    ]
    discovered = [page["url"] for page in pages] + ["https://example.com/products/c", "https://example.com/blog/two"]
    report = build_page_template_intelligence(pages, discovered)

    assert report["urls_discovered"] == 5
    assert report["urls_crawled"] == 3
    assert report["urls_rendered"] == 0
    assert report["urls_deeply_analyzed"] == 0
    assert report["full_site_audit"] is False
    assert "not a full-site audit" in report["statement"]
    assert len(report["templates"]) == 2

    defect = report["template_defects"][0]
    assert "missing_canonical" in defect["defects"]
    assert defect["affected_urls"] == [
        "https://example.com/products/a",
        "https://example.com/products/b",
    ]
    assert "https://example.com/products/c" in report["expansion_urls"]
    assert "https://example.com/blog/two" not in report["expansion_urls"]
    assert "https://example.com/products/c" not in defect["affected_urls"]


def test_coverage_reporter_does_not_scale_page_type_counts():
    discovered = [f"https://example.com/page-{i}" for i in range(10)]
    crawled = [
        {"url": "https://example.com/products/a", "page_type": StandardPageType.PRODUCT.value, "is_rendered": False},
        {"url": "https://example.com/products/b", "page_type": StandardPageType.PRODUCT.value, "is_rendered": False},
    ]
    report, _inventory = CrawlCoverageReporter.generate_coverage_report(
        audit_run_id="fixture",
        domain="example.com",
        profile_used=CrawlProfile.QUICK,
        discovered_urls=discovered,
        crawled_urls=crawled,
    )
    product = next(row for row in report.page_type_coverage if row.page_type == "PRODUCT")
    assert product.inspected_count == 2
    assert product.discovered_count == 2
    assert report.full_site_audit is False
    assert "not a full-site audit" in report.honest_coverage_statement


def test_viewport_tag_alone_is_not_a_mobile_pass():
    html = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    report = MobileExperienceEngine.audit_mobile_viewport("https://example.com/", html)
    assert report.has_viewport_meta is True
    assert report.layout_measured is False
    assert report.is_mobile_friendly is None
    assert report.has_horizontal_overflow is False
    assert report.physical_device is False


def test_emulated_matrix_keeps_unmeasured_devices_untested():
    snapshots = {
        "standard_mobile": {
            "html": '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "elements": [
                {"selector": "button", "width": 24, "height": 24, "spacing": 4, "is_interactive": True},
                {"selector": "table", "width": 1200, "height": 40, "is_interactive": False},
            ],
        }
    }
    report = MobileExperienceEngine.audit_device_matrix("https://example.com/cart", snapshots)
    assert report["physical_device"] is False
    assert "Not a physical phone" in report["label"]
    assert "not clicked" in report["label"]
    standard = next(row for row in report["devices"] if row["device_id"] == "standard_mobile")
    assert standard["measurement_method"] == "emulated_browser"
    assert standard["has_horizontal_overflow"] is True
    assert standard["is_mobile_friendly"] is False
    small = next(row for row in report["devices"] if row["device_id"] == "small_mobile")
    assert small["verification_status"] == "NOT_TESTED"
    assert small["is_mobile_friendly"] is None


@pytest.mark.asyncio
async def test_failed_browser_is_data_unavailable():
    async def unavailable(_url):
        raise RuntimeError("browser missing")

    report = await measure_emulated_devices("https://example.com/", unavailable)
    assert report["verification_status"] == "DATA_UNAVAILABLE"
    assert report["physical_device"] is False
    assert report["devices"] == []
