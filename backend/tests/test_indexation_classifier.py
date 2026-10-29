"""
Unit tests for Dristik AI 16-point Indexation Intelligence Classifier.
"""
from app.domain.models import PageEvidence, CrawlManifest
from app.intelligence.indexation.classifier import IndexationClassifier


def test_indexation_classifier_all_conditions():
    classifier = IndexationClassifier()

    pages = [
        # 1. Perfectly indexable page
        PageEvidence(
            url="https://example.com/",
            status_code=200,
            title="Acme - AI Automated Data Intelligence",
            canonical_url="https://example.com/",
            h1=["Acme - AI Automated Data Intelligence"],
            body_text="Acme is the premier automated data intelligence platform for fast-growing businesses. We streamline telemetry and reporting across multi-cloud environments.",
            word_count=25,
            raw_html="<html><head><title>Acme</title><link rel='canonical' href='https://example.com/'></head><body><h1>Acme - AI Automated Data Intelligence</h1><p>Acme is the premier automated data intelligence platform for fast-growing businesses. We streamline telemetry and reporting across multi-cloud environments.</p></body></html>"
        ),
        # 2. Noindex meta tag
        PageEvidence(
            url="https://example.com/admin",
            status_code=200,
            title="Admin Dashboard",
            robots_meta="noindex, nofollow",
            canonical_url="https://example.com/admin",
            body_text="Admin portal login form for staff members.",
            word_count=7
        ),
        # 3. Soft 404 (returns 200 OK, but says page not found)
        PageEvidence(
            url="https://example.com/old-product",
            status_code=200,
            title="404 - Page Not Found",
            h1=["Oops! Page Not Found"],
            body_text="Sorry, we couldn't find the page you're looking for. It may have been deleted or moved.",
            word_count=16
        ),
        # 4. Robots.txt blocked
        PageEvidence(
            url="https://example.com/checkout/step2",
            status_code=200,
            title="Checkout Step 2",
            canonical_url="https://example.com/checkout/step2",
            body_text="Enter credit card details and confirm shipping address.",
            word_count=8
        ),
        # 5. Canonical mismatch / Alternate canonical
        PageEvidence(
            url="https://example.com/blog/item?utm_source=twitter",
            status_code=200,
            title="Blog Article",
            canonical_url="https://example.com/blog/item",
            body_text="Detailed blog article discussing search engine crawlers and headless browser rendering.",
            word_count=13
        ),
        # 6. JavaScript-only content dependency
        PageEvidence(
            url="https://example.com/app",
            status_code=200,
            title="Interactive Web App",
            canonical_url="https://example.com/app",
            h1=["Dynamic Enterprise Analytics Suite"],
            body_text="Dynamic Enterprise Analytics Suite. This full interactive dashboard provides real-time latency graphs, user conversions, search performance summaries, and predictive revenue intelligence across all company domains.",
            word_count=29,
            raw_html="<html><head><title>Interactive Web App</title></head><body><div id='root'>Loading...</div></body></html>"
        ),
    ]

    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        pages=pages,
        robots_txt_content="User-agent: *\nDisallow: /checkout/\nDisallow: /api/\n"
    )

    gsc_data = {
        "inspections": {
            "https://example.com/": {
                "coverage_state": "Submitted and indexed",
                "indexing_state": "INDEXED",
                "selected_canonical": "https://example.com/"
            }
        }
    }

    rollup, findings = classifier.audit(manifest=manifest, pages=pages, gsc_data=gsc_data)

    assert rollup.total_pages_evaluated == 6
    # 1. Homepage
    home = next(p for p in rollup.pages if p.url == "https://example.com/")
    assert home.crawlable is True
    assert home.indexable is True
    assert home.indexed_state == "INDEXED"
    assert home.canonical_match is True

    # 2. Noindex
    admin = next(p for p in rollup.pages if p.url == "https://example.com/admin")
    assert admin.has_noindex is True
    assert admin.indexable is False

    # 3. Soft 404
    soft = next(p for p in rollup.pages if p.url == "https://example.com/old-product")
    assert soft.is_soft_404 is True
    assert soft.indexable is False
    assert any("idx_soft404" in f.finding_id for f in findings)

    # 4. Robots blocked
    checkout = next(p for p in rollup.pages if p.url == "https://example.com/checkout/step2")
    assert checkout.robots_blocked is True
    assert checkout.crawlable is False
    assert checkout.indexable is False

    # 5. Canonical mismatch / Alternate canonical
    canonical_mismatch = next(p for p in rollup.pages if "utm_source" in p.url)
    assert canonical_mismatch.canonical_match is False
    assert canonical_mismatch.alternate_canonical == "https://example.com/blog/item"
    assert canonical_mismatch.indexable is False

    # 6. JS-only content
    js_page = next(p for p in rollup.pages if p.url == "https://example.com/app")
    assert js_page.render_delta is not None
    assert js_page.render_delta.js_dependency_risk == "CRITICAL"
    assert js_page.is_js_only_content is True
    assert any("idx_js_only" in f.finding_id for f in findings)
