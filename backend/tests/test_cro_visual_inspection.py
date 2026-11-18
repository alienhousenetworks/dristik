"""
Tests for Phase 6.1: Browser-based Visual Inspection Infrastructure.
"""
import pytest
from app.cro.visual_inspector import (
    VisualInspector,
    VIEWPORT_PROFILES,
    VIEWPORT_DISCLOSURE,
)
from app.cro.visual_ux_tester import VisualUxTester


def test_visual_inspector_supports_all_5_viewports():
    expected_viewports = {"desktop", "laptop", "tablet", "mobile", "small_mobile"}
    assert set(VIEWPORT_PROFILES.keys()) == expected_viewports

    assert VIEWPORT_PROFILES["desktop"]["width"] == 1440
    assert VIEWPORT_PROFILES["desktop"]["height"] == 900
    assert VIEWPORT_PROFILES["laptop"]["width"] == 1366
    assert VIEWPORT_PROFILES["laptop"]["height"] == 768
    assert VIEWPORT_PROFILES["tablet"]["width"] == 768
    assert VIEWPORT_PROFILES["tablet"]["height"] == 1024
    assert VIEWPORT_PROFILES["mobile"]["width"] == 390
    assert VIEWPORT_PROFILES["mobile"]["height"] == 844
    assert VIEWPORT_PROFILES["small_mobile"]["width"] == 360
    assert VIEWPORT_PROFILES["small_mobile"]["height"] == 800


def test_visual_inspector_detects_sticky_ctas_and_modals():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Store</title></head>
    <body>
        <div id="cookie-banner" class="cookie-consent">
            <p>We use cookies</p>
            <button>Accept</button>
        </div>
        <div class="hero">
            <h1>Scale Your Enterprise Revenue</h1>
            <a href="/pricing" class="btn">View Pricing</a>
        </div>
        <div class="fixed-bottom sticky-bar" style="position: fixed; bottom: 0;">
            <button class="btn btn-primary">Instant Checkout</button>
        </div>
    </body>
    </html>
    """
    res = VisualInspector.inspect("https://example.com", html, "2026-11-18T10:00:00Z")

    assert len(res.viewports) == 5
    assert "cookie_consent_banner" in res.detected_modals
    assert "Instant Checkout" in res.sticky_ctas
    assert "not a substitute" in res.disclosure.lower()


def test_visual_ux_tester_integrates_viewports():
    html = "<html><body><h1>Hello</h1><button class='btn'>Get Started</button></body></html>"
    tester = VisualUxTester()
    report = tester.inspect_website_visual_ux(
        domain="example.com",
        website_url="https://example.com",
        dom_evidence={"html": html},
    )

    assert report.overall_visual_ux_score is not None
    assert len(report.viewports) == 5
    assert "desktop" in report.viewports
    assert "mobile" in report.viewports
    assert report.viewports["mobile"].width == 390
    assert report.viewports["small_mobile"].width == 360
