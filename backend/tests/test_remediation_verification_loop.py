"""
Tests for Automatic Remediation Verification Loop: FIX -> RECRAWL -> RECHECK -> COMPARE -> CERTIFY.

ZERO-FAKE TEST CONTRACT:
Every test provides real HTML/XML/robots.txt content and verifies that the verification
loop produces results from actual DOM/XML/HTTP parsing — never from hardcoded values.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.domain.enums import Category, Severity
from app.domain.models import Finding
from app.verification.verification_loop import verification_loop_service
from app.main import app


# ── Sitemap / Robots.txt Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_sitemap_verification_with_real_xml():
    """Provide actual XML sitemap and robots.txt. Verify real parsing."""
    finding = Finding(
        finding_id="find_005",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="XML Sitemap missing or unreferenced",
        finding="No /sitemap.xml detected.",
        description="/sitemap.xml missing in root directory.",
        recommendation="Publish /sitemap.xml and reference it in robots.txt.",
    )

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '  <url><loc>https://alienhousenetworks.com/</loc></url>'
        '  <url><loc>https://alienhousenetworks.com/services</loc></url>'
        '  <url><loc>https://alienhousenetworks.com/about</loc></url>'
        '</urlset>'
    )

    robots_txt = "User-agent: *\nAllow: /\nSitemap: https://alienhousenetworks.com/sitemap.xml"

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://alienhousenetworks.com",
        live_html=sitemap_xml,
        live_status=200,
        robots_txt_content=robots_txt,
        sitemap_content=sitemap_xml,
    )

    assert report is not None
    assert report.finding_id == "find_005"
    assert report.status == "RESOLVED"
    assert report.stage == "CERTIFIED"

    # Verify all checks exist and are from real parsing
    check_names = [c.name for c in report.checks]
    assert "/sitemap.xml detected" in check_names
    assert "referenced in robots.txt" in check_names
    assert "audited URLs present in sitemap" in check_names
    assert "HTTP 200 status" in check_names
    assert "XML valid syntax" in check_names

    # Verify the sitemap check references actual <loc> count (3 entries)
    loc_check = next(c for c in report.checks if "audited URLs" in c.name)
    assert "3" in loc_check.detail  # Should show 3 <loc> entries

    # Verify robots.txt check references actual directive
    robots_check = next(c for c in report.checks if "robots.txt" in c.name)
    assert "Sitemap:" in robots_check.detail

    # Verify HTTP status check shows actual status code, NOT hardcoded "TTFB 142ms"
    http_check = next(c for c in report.checks if "HTTP 200" in c.name)
    assert "200" in http_check.detail
    assert "142ms" not in http_check.detail  # No hardcoded TTFB

    for check in report.checks:
        assert check.passed is True
        assert len(check.detail) > 0

    assert report.score_delta > 0
    assert report.evidence_seal.startswith("sha256:")

    # Verify finding state mutated
    assert finding.resolution_status == "RESOLVED"
    assert finding.remediation_verification == report


@pytest.mark.asyncio
async def test_sitemap_verification_fails_without_content():
    """No sitemap content provided — checks should fail, not fake-pass."""
    finding = Finding(
        finding_id="find_006",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="XML Sitemap missing",
        finding="No /sitemap.xml detected.",
        description="Missing sitemap.",
        recommendation="Publish /sitemap.xml.",
    )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com",
        live_html="<html><body>Hello world</body></html>",
        live_status=200,
        robots_txt_content="User-agent: *\nDisallow: /admin",
        sitemap_content=None,
    )

    assert report.status != "RESOLVED"  # Must NOT fake-resolve
    # Sitemap detection should fail (no <urlset> in plain HTML)
    sitemap_check = next(c for c in report.checks if "/sitemap.xml detected" in c.name)
    assert sitemap_check.passed is False

    # Robots.txt should fail (no Sitemap: directive)
    robots_check = next(c for c in report.checks if "robots.txt" in c.name)
    assert robots_check.passed is False

    assert report.score_delta == 0.0  # No score recovered for unresolved


# ── Schema JSON-LD Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_verification_with_real_jsonld():
    """Provide real JSON-LD in DOM. Verify actual parsing."""
    finding = Finding(
        finding_id="find_012",
        category=Category.SCHEMA,
        severity=Severity.HIGH,
        title="Missing Service schema",
        finding="No Service JSON-LD schema found.",
        description="Lacks structured data for AI search ingestion.",
        recommendation="Inject Service schema.",
    )

    html = (
        '<html><head>'
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Service","name":"SEO Audit","url":"https://example.com/services"}'
        '</script>'
        '</head><body></body></html>'
    )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com/services",
        live_html=html,
        live_status=200,
    )

    assert report.status == "RESOLVED"
    assert len(report.checks) >= 4

    # Verify actual parsing happened
    type_check = next(c for c in report.checks if "entity type" in c.name)
    assert type_check.passed is True
    assert "Service" in type_check.detail  # Real @type extracted

    props_check = next(c for c in report.checks if "properties" in c.name)
    assert props_check.passed is True
    assert "@context" in props_check.detail


@pytest.mark.asyncio
async def test_schema_verification_fails_without_jsonld():
    """DOM without JSON-LD — all schema checks should fail."""
    finding = Finding(
        finding_id="find_013",
        category=Category.SCHEMA,
        severity=Severity.HIGH,
        title="Missing Organization schema",
        finding="No JSON-LD schema found.",
        description="No structured data.",
        recommendation="Add Organization schema.",
    )

    html = "<html><head><title>Test</title></head><body><p>No schema here</p></body></html>"

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com",
        live_html=html,
        live_status=200,
    )

    assert report.status != "RESOLVED"
    ld_check = next(c for c in report.checks if "JSON-LD" in c.name)
    assert ld_check.passed is False
    assert report.score_delta == 0.0


# ── H1 / Positioning Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_h1_verification_real_dom():
    """DOM with single valid H1 — should pass."""
    finding = Finding(
        finding_id="find_020",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="Homepage H1 lacks commercial specificity",
        finding="H1 tag is vague.",
        description="H1 does not communicate service category.",
        recommendation="Rewrite H1 with commercial clarity.",
    )

    html = (
        '<html><head><title>Test</title></head>'
        '<body><h1>Enterprise AI-Powered SEO Audit Platform</h1><p>Content</p></body></html>'
    )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com",
        live_html=html,
        live_status=200,
    )

    assert report.status == "RESOLVED"
    h1_check = next(c for c in report.checks if "Single H1" in c.name)
    assert h1_check.passed is True
    assert "1 <h1>" in h1_check.detail

    # Verify actual character count in detail
    clarity_check = next(c for c in report.checks if "clarity" in c.name.lower())
    assert "Enterprise AI-Powered SEO Audit Platform" in clarity_check.detail


@pytest.mark.asyncio
async def test_h1_verification_fails_multiple_h1():
    """DOM with 2 H1 tags — single-H1 check should fail."""
    finding = Finding(
        finding_id="find_021",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="H1 positioning issue",
        finding="Multiple H1 tags detected.",
        description="Duplicate H1 elements.",
        recommendation="Use single H1.",
    )

    html = (
        '<html><head><title>Test</title></head>'
        '<body><h1>First Heading</h1><h1>Second Heading</h1></body></html>'
    )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com",
        live_html=html,
        live_status=200,
    )

    assert report.status != "RESOLVED"
    h1_check = next(c for c in report.checks if "Single H1" in c.name)
    assert h1_check.passed is False
    assert "2 <h1>" in h1_check.detail


# ── Metadata Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metadata_verification_real_dom():
    """DOM with proper title, meta description, canonical — should pass."""
    finding = Finding(
        finding_id="find_030",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="Duplicate or missing metadata",
        finding="Missing meta description.",
        description="Meta tags incomplete.",
        recommendation="Add unique title and meta description.",
    )

    html = (
        '<html><head>'
        '<title>Dristik AI — Enterprise SEO Audit Platform</title>'
        '<meta name="description" content="Dristik is an evidence-first AI SEO audit platform for enterprise teams.">'
        '<link rel="canonical" href="https://example.com/">'
        '</head><body><p>Content</p></body></html>'
    )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com/",
        live_html=html,
        live_status=200,
    )

    assert report.status == "RESOLVED"

    # Verify actual title text is in the detail
    title_check = next(c for c in report.checks if "title" in c.name.lower())
    assert title_check.passed is True
    assert "Dristik AI" in title_check.detail

    # Verify actual character count (not hardcoded "145 characters")
    meta_check = next(c for c in report.checks if "description" in c.name.lower())
    assert meta_check.passed is True
    assert "145" not in meta_check.detail  # No fake hardcoded count


# ── General / Unknown Finding Type Tests ────────────────────────────────

@pytest.mark.asyncio
async def test_general_finding_returns_inconclusive_or_partial():
    """Non-classifiable finding — should NOT fake-resolve."""
    finding = Finding(
        finding_id="find_099",
        category=Category.TECHNICAL_SEO,
        severity=Severity.LOW,
        title="Custom internal audit policy violation",
        finding="Internal compliance check XYZ failed.",
        description="Custom policy not met.",
        recommendation="Review internal audit policy.",
    )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com",
        live_html="<html><body>Hello</body></html>",
        live_status=200,
    )

    # The general handler can only check HTTP status — it cannot verify
    # "remediation satisfied" or "no regression" without specific assertion logic
    assert report.status != "RESOLVED" or len(report.checks) == 1
    # Verify we're not faking "Remediation assertion satisfied" or "No regression introduced"
    for check in report.checks:
        assert "assertion satisfied" not in check.detail.lower()
        assert "remains stable" not in check.detail.lower()


@pytest.mark.asyncio
async def test_crawl_failure_returns_failed_recrawl():
    """Unreachable URL — should return FAILED_RECRAWL, not fabricate HTML."""
    finding = Finding(
        finding_id="find_100",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing sitemap",
        finding="No sitemap detected.",
        description="Sitemap not found.",
        recommendation="Add sitemap.",
    )

    # Pass no live_html and a non-routable URL to trigger fetch failure
    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="http://192.0.2.1:99999",  # Non-routable
        live_html=None,
        live_status=None,
    )

    assert report.status == "FAILED_RECRAWL"
    assert report.stage == "RECRAWL"
    assert len(report.checks) == 0
    assert report.score_delta == 0.0
    assert "unreachable" in report.after_state.lower() or "failed" in report.after_state.lower()


# ── Live AI Citation Engine Tests ───────────────────────────────────────

def test_live_citation_engine_returns_honest_not_available():
    """LiveAICitationEngine should return is_cited=False without API keys."""
    from app.intelligence.citations.live import LiveAICitationEngine

    engine = LiveAICitationEngine()
    result = engine.evaluate_query(
        domain="linear.app",
        query="linear issue tracking",
        engine="perplexity",
    )

    assert result.is_cited is False
    assert result.citation_rank is None
    assert result.cited_url is None
    assert result.extracted_snippet is None
    assert result.notice is not None
    assert "API key" in result.notice


# ── API Endpoint Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_verify_finding_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/remediation/verify-finding", json={
            "finding_id": "find_005",
            "website_url": "https://example.com",
            "mock_live_html": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://example.com/</loc></url>'
                '</urlset>'
            )
        })
        assert res.status_code == 200
        data = res.json()
        assert data["finding_id"] == "find_005"
        assert data["evidence_seal"].startswith("sha256:")
        # Should have real checks, not hardcoded
        assert len(data["checks"]) >= 1
