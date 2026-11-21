"""Phase 44 — Controlled CRO Benchmark Testing Suite (All 15 Deterministic Scenarios).

Validates the CRO engine against deterministic HTML/DOM and analytics fixtures with
known defects (never relying on live external websites for regression testing):
 1. Broken primary CTA
 2. Form with validation errors
 3. Poor mobile layout (no viewport, overflow, tiny touch targets)
 4. Confusing landing page (vague headline & unanswered buyer questions)
 5. Complex checkout (forced account creation, 12 fields, hidden shipping)
 6. Missing analytics events
 7. Duplicate analytics events
 8. Strong design/structure but weak passive copy
 9. Good UX but poor performance (separate UX vs performance diagnosis)
10. Multiple competing primary CTAs
11. Missing trust information
12. Inaccessible controls (WCAG 2.2 AA + focus outline suppression)
13. Slow / failing form submission
14. High funnel abandonment in measured test data
15. No analytics connection (correct unmeasured status, never zero)
"""
from __future__ import annotations

import asyncio
import pytest

from app.cro.orchestrator import CROAuditOrchestrator
from app.db.cro_schema import CROStore


def _run_fixture(tmp_path, name: str, pages, **kwargs):
    store = CROStore(db_path=str(tmp_path / f"{name}.db"))
    orch = CROAuditOrchestrator(
        tenant_id="bench_org",
        target_url=pages[0]["url"],
        seed_pages=pages,
        use_live_browser=False,
        store=store,
        **kwargs,
    )
    res = asyncio.run(orch.run())
    findings = store.list_findings("bench_org", orch.audit_id)
    scorecard = res["scorecard"]
    return orch, store, res, findings, scorecard


def test_benchmark_01_broken_primary_cta(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Bench SaaS",
        "raw_html": (
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<h1>Automated Billing Software for SaaS Teams</h1>'
            '<button class="btn-primary" disabled>Start Free Trial</button>'
            '<a class="cta" href="#">Book Demo</a>'
            '</body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b01", pages)
    broken = [f for f in findings if f.subcategory == "broken_cta"]
    assert broken, "Must detect broken/unclickable primary CTA"
    assert broken[0].severity.value == "critical"
    assert broken[0].source_type.value in ("direct_technical", "browser_test")


def test_benchmark_02_form_with_validation_errors(tmp_path):
    pages = [{
        "url": "https://bench.example.com/contact",
        "status_code": 200,
        "title": "Contact Us",
        "raw_html": (
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<h1>Request a Consultation</h1>'
            '<form id="leadForm" novalidate><input type="text" name="email" placeholder="Email"><input type="text" name="name"><button type="submit">Request Consultation</button></form>'
            '</body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b02", pages)
    assert any(f.subcategory == "form_validation_and_labels" for f in findings)


def test_benchmark_03_poor_mobile_layout(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Mobile Broken",
        "raw_html": (
            '<html><head><style>.wrapper{width:1440px;} .tiny{width:18px;height:18px;}</style></head><body>'
            '<nav><a href="/a">A</a><a href="/b">B</a></nav>'
            '<div class="wrapper"><h1>Billing Platform for Teams</h1><a class="btn-primary tiny" href="/signup">Start Now</a></div>'
            '</body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b03", pages)
    mob = [f for f in findings if f.category == "mobile_cro"]
    assert mob, "Must detect poor mobile layout (missing viewport + fixed overflow + tiny tap targets)"


def test_benchmark_04_confusing_landing_page(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Welcome",
        "raw_html": (
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<h1>Innovating the Future</h1><p>Synergy for tomorrow.</p>'
            '</body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b04", pages)
    vp = [f for f in findings if f.subcategory == "value_proposition_clarity"]
    assert vp, "Must flag vague headline & unanswered buyer questions"
    assert vp[0].source_type.value == "heuristic_observation"


def test_benchmark_05_complex_checkout(tmp_path):
    inputs_html = "".join(f'<label for="f{i}">Field {i}</label><input id="f{i}" name="f{i}" type="text" required>' for i in range(12))
    pages = [
        {"url": "https://shop.example.com/product/shoe", "status_code": 200, "title": "Running Shoe", "raw_html": "<html><body><h1>Pro Running Shoe $129</h1><button class='btn-primary'>Add to Cart</button></body></html>"},
        {"url": "https://shop.example.com/checkout", "status_code": 200, "title": "Checkout", "raw_html": f"<html><body><h1>Checkout</h1><p>You must create an account to continue.</p><form id='chk'>{inputs_html}<button type='submit'>Pay Now</button></form></body></html>"},
    ]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b05", pages, business_config={"business_type": "ecommerce"})
    assert any(f.subcategory == "checkout_friction" for f in findings)
    assert any(f.subcategory == "shipping_and_returns" for f in findings)


def test_benchmark_06_missing_analytics_events(tmp_path):
    pages = [{"url": "https://bench.example.com/", "status_code": 200, "title": "SaaS", "raw_html": "<html><body><h1>SaaS Platform for Teams</h1><a class='btn-primary' href='/signup'>Start Free Trial</a></body></html>"}]
    analytics = {"state": "MEASURED", "provider": "ga4", "eligible_users": 1000, "events": [{"event_name": "page_view", "event_count": 1500, "parameters": ["page_location"]}]}
    _, _, _, findings, _ = _run_fixture(tmp_path, "b06", pages, business_config={"business_type": "saas"}, analytics_payload=analytics)
    assert any(f.subcategory == "missing_conversion_events" for f in findings)


def test_benchmark_07_duplicate_analytics_events(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Dup Events",
        "raw_html": "<html><head><script>gtag('config','G-ABC12345');gtag('config','G-ABC12345');</script></head><body><h1>SaaS Platform</h1></body></html>",
    }]
    analytics = {
        "state": "MEASURED",
        "provider": "ga4",
        "events": [{"event_name": "purchase", "event_count": 200, "duplicate_firing": True, "duplicate_ratio": 1.9, "parameters": ["transaction_id", "value", "currency"]}],
    }
    _, _, _, findings, _ = _run_fixture(tmp_path, "b07", pages, business_config={"business_type": "ecommerce"}, analytics_payload=analytics)
    assert any(f.subcategory == "duplicate_event_tracking" for f in findings)


def test_benchmark_08_strong_design_weak_copy(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Clean UI Weak Copy",
        "raw_html": (
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<nav><a href="/product">Product</a><a href="/pricing">Pricing</a></nav>'
            '<h1>Welcome to Our Site</h1>'
            '<a class="btn-primary" href="/contact">Click Here</a>'
            '<button type="submit">Submit</button>'
            '<footer><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/contact">Contact</a></footer>'
            '</body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b08", pages)
    assert any(f.category == "copywriting_optimization" and f.subcategory == "passive_cta_copy" for f in findings)


def test_benchmark_09_good_ux_poor_performance(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Slow Clean Page",
        "raw_html": (
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<script src="https://cdn.a.example/1.js"></script><script src="https://cdn.b.example/2.js"></script><script src="https://cdn.c.example/3.js"></script>'
            '</head><body><h1>Analytics Software for Finance Teams to Automate Reporting</h1>'
            '<p>SOC 2 certified platform trusted by finance leaders. Transparent $99/mo pricing with cancel anytime guarantee.</p>'
            '<a class="btn-primary" href="/trial">Start Free Trial</a>'
            '<footer><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/contact">Contact</a></footer></body></html>'
        ),
        "performance_metrics": {"lcp_ms": 5400, "cls_score": 0.32, "ttfb_ms": 1400, "measurement_type": "lab"},
    }]
    _, _, _, findings, scorecard = _run_fixture(tmp_path, "b09", pages)
    assert any(f.category == "performance_interaction" for f in findings)
    ux_dim = next(d for d in scorecard["experience_dimensions"] if d["dimension_id"] == "ux_usability")
    perf_dim = next(d for d in scorecard["experience_dimensions"] if d["dimension_id"] == "performance_interaction")
    assert ux_dim["score"] > perf_dim["score"], "UX and Performance diagnoses must remain cleanly separated"


def test_benchmark_10_multiple_competing_ctas(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "Competing CTAs",
        "raw_html": (
            '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            '<h1>Cloud Storage Platform for Teams</h1>'
            '<a class="btn-primary" href="/a">Start Trial</a>'
            '<a class="btn-primary" href="/b">Book Demo</a>'
            '<a class="btn-primary" href="/c">Watch Video</a>'
            '<a class="btn-primary" href="/d">Download PDF</a>'
            '</body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b10", pages)
    assert any(f.subcategory == "competing_primary_ctas" for f in findings)


def test_benchmark_11_missing_trust_information(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "No Trust",
        "raw_html": '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><h1>Buy Our Software Now</h1><a class="btn-primary" href="/buy">Buy Now</a></body></html>',
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b11", pages)
    assert any(f.category == "trust_optimization" for f in findings)


def test_benchmark_12_inaccessible_controls(tmp_path):
    pages = [{
        "url": "https://bench.example.com/",
        "status_code": 200,
        "title": "A11y Fail",
        "raw_html": '<html><head><style>*:focus{outline:none;}</style></head><body><h1>Platform</h1><button></button><img src="/hero.png"><form><input type="text" name="x"><button type="submit">Go</button></form></body></html>',
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b12", pages)
    a11y = [f for f in findings if f.category == "accessibility"]
    assert a11y, "Must flag inaccessible controls & focus suppression"
    assert any("manual" in lim.lower() for lim in a11y[0].limitations)


def test_benchmark_13_slow_failing_form_submission(tmp_path):
    pages = [{
        "url": "https://bench.example.com/demo",
        "status_code": 200,
        "title": "Demo Form",
        "raw_html": (
            '<html><body><h1>Book a Demo</h1>'
            '<form id="demoForm" data-test-error="500 Internal Server Error" data-response-ms="4500">'
            '<label for="e">Email</label><input id="e" type="email" name="email" required>'
            '<button type="submit">Book Demo</button></form></body></html>'
        ),
    }]
    _, _, _, findings, _ = _run_fixture(tmp_path, "b13", pages)
    sub = [f for f in findings if f.subcategory == "form_submission_reliability"]
    assert sub and sub[0].severity.value == "critical"


def test_benchmark_14_high_funnel_abandonment(tmp_path):
    pages = [{"url": "https://bench.example.com/", "status_code": 200, "title": "Funnel", "raw_html": "<html><body><h1>CRM Platform for Sales Teams</h1><a class='btn-primary' href='/signup'>Start Free Trial</a></body></html>"}]
    analytics = {
        "state": "MEASURED",
        "provider": "ga4",
        "date_range": "2026-10-01..2026-10-31",
        "eligible_users": 10000,
        "unique_converters": 150,
        "funnel_steps": [
            {"step_name": "Landing Page", "eligible_users": 10000, "progressing_users": 10000, "counting_unit": "unique_users"},
            {"step_name": "Form Start", "eligible_users": 10000, "progressing_users": 4000, "counting_unit": "unique_users"},
            {"step_name": "Form Submit", "eligible_users": 4000, "progressing_users": 400, "counting_unit": "unique_users"},
        ],
        "events": [{"event_name": "sign_up", "event_count": 400, "parameters": ["plan_tier", "source"]}],
    }
    _, _, _, findings, scorecard = _run_fixture(tmp_path, "b14", pages, business_config={"business_type": "saas"}, analytics_payload=analytics)
    drop = [f for f in findings if f.subcategory == "measured_funnel_abandonment"]
    assert drop and drop[0].source_type.value == "analytics_observation"
    assert scorecard["business_performance_status"] in ("measured", "partial")


def test_benchmark_15_no_analytics_connection_unmeasured(tmp_path):
    pages = [{"url": "https://bench.example.com/", "status_code": 200, "title": "No GA4", "raw_html": '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><h1>Software Platform for Operations Teams</h1><a class="btn-primary" href="/demo">Book Demo</a></body></html>'}]
    _, _, res, _, scorecard = _run_fixture(tmp_path, "b15", pages, analytics_payload=None)
    assert res["audit"]["analytics_connected"] is False
    assert scorecard["experience_score"] is not None and scorecard["experience_score"] > 0
    assert scorecard["business_performance_status"] == "data_unavailable"
    for metric in scorecard["business_performance_metrics"]:
        assert metric["value"] is None, f"Disconnected metric {metric['metric']} must stay None, never 0"
        assert metric["status"] == "data_unavailable"
