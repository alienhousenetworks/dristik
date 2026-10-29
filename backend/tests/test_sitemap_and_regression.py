"""
Unit tests for Phase 2: Sitemap Parser and Regression Engine.
"""
from app.crawl.sitemap import SitemapParser
from app.audit.regression_engine import AuditRegressionEngine


def test_sitemap_parser_prioritization():
    parser = SitemapParser()
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://linear.app/pricing</loc>
            <priority>0.9</priority>
            <changefreq>daily</changefreq>
        </url>
        <url>
            <loc>https://linear.app/docs/api</loc>
            <priority>0.3</priority>
            <changefreq>monthly</changefreq>
        </url>
        <url>
            <loc>https://linear.app/blog/feature-release</loc>
            <priority>0.7</priority>
            <changefreq>weekly</changefreq>
        </url>
    </urlset>
    """
    urls = parser.parse_sitemap_xml(sample_xml)
    assert len(urls) == 3
    # First URL should be P1 (pricing)
    assert urls[0].url == "https://linear.app/pricing"
    assert urls[0].tier == "P1"
    # Second URL should be P2 (blog)
    assert urls[1].url == "https://linear.app/blog/feature-release"
    assert urls[1].tier == "P2"
    # Third URL should be P3 (docs)
    assert urls[2].url == "https://linear.app/docs/api"
    assert urls[2].tier == "P3"


def test_sitemap_index_extraction():
    parser = SitemapParser()
    index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://linear.app/sitemap-main.xml</loc>
        </sitemap>
        <sitemap>
            <loc>https://linear.app/sitemap-blog.xml</loc>
        </sitemap>
    </sitemapindex>
    """
    children = parser.extract_child_sitemaps(index_xml)
    assert len(children) == 2
    assert "https://linear.app/sitemap-main.xml" in children
    assert "https://linear.app/sitemap-blog.xml" in children


def test_regression_engine_diff_and_alerts():
    engine = AuditRegressionEngine()

    baseline = {
        "audit_id": "audit_baseline",
        "overall_score": 88,
        "category_scores": {"on_page_seo": 90, "technical": 85},
        "pages": [
            {"url": "https://linear.app/", "status_code": 200, "canonical": "https://linear.app/", "title": "Linear"},
            {"url": "https://linear.app/pricing", "status_code": 200, "canonical": "https://linear.app/pricing", "title": "Pricing"},
        ],
        "schema_types": ["Organization", "WebSite", "SoftwareApplication"],
    }

    current = {
        "audit_id": "audit_current",
        "overall_score": 79,  # dropped by 9 points!
        "category_scores": {"on_page_seo": 78, "technical": 85},
        "pages": [
            {"url": "https://linear.app/", "status_code": 200, "canonical": "https://linear.app/", "title": "Linear - Issue Tracking"},
            {"url": "https://linear.app/pricing", "status_code": 404, "canonical": None, "title": "404 Not Found"},  # Broke!
            {"url": "https://linear.app/changelog", "status_code": 200, "canonical": "https://linear.app/changelog", "title": "Changelog"},
        ],
        "schema_types": ["Organization", "WebSite"],  # Dropped SoftwareApplication!
    }

    diff = engine.compare_audits(current, baseline)
    assert diff.overall_score_delta == -9
    assert "https://linear.app/changelog" in diff.pages_added
    assert "SoftwareApplication" in diff.schema_types_dropped

    alert_types = [a.alert_type for a in diff.alerts]
    assert "SCORE_DROP" in alert_types
    assert "HTTP_STATUS_CHANGED" in alert_types
    assert "SCHEMA_DROPPED" in alert_types
