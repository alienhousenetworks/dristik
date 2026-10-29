"""
Tests for Enterprise Dynamic Content Ingestion and State Deserialization.
Verifies that database-driven content from Django, Next.js, and headless CMS
payloads is accurately recovered even from thin client-side shells.
"""
import pytest
from bs4 import BeautifulSoup

from app.crawl.analyzers.dynamic_content import extract_embedded_cms_content, needs_js_render
from app.crawl.analyzers.html import analyze_html_content
from app.evidence.store import EvidenceStore
from app.crawl.browser import BrowserRenderService


def test_django_json_script_recovery():
    """Verifies that database content embedded via Django json_script is recovered."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Dynamic Django CMS</title></head>
    <body>
        <div id="content"></div>
        <script id="django-post-data" type="application/json">
        {
            "headline": "Enterprise Website Intelligence at Scale",
            "subtitle": "Eliminate conversion friction and optimize for generative engines",
            "body": "This article was written by an administrator in Django admin and saved directly to PostgreSQL. The frontend hydrates this data dynamically into the container."
        }
        </script>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    res = extract_embedded_cms_content(soup)
    
    assert "Enterprise Website Intelligence at Scale" in res["h1"]
    assert any("Eliminate conversion friction" in h for h in res["h2"])
    assert "written by an administrator in Django admin" in res["text"]
    assert "django" in res["sources"] or "json_script" in res["sources"]


def test_nextjs_app_router_rsc_recovery():
    """Verifies that Next.js 13/14/15 App Router streaming chunks are parsed."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Next.js App Router Page</title></head>
    <body>
        <div id="__next"></div>
        <script>
        self.__next_f.push([1, "1:[\"$\",\"h1\",null,{\"children\":\"Autonomous AI Search Engine Architecture\"}]"]);
        self.__next_f.push([1, "2:[\"$\",\"p\",null,{\"children\":\"Our database-backed catalog features real-time inventory and pricing tiers updated every five minutes by the backend admin portal.\"}]"]);
        </script>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    res = extract_embedded_cms_content(soup)
    
    assert "nextjs_app_router" in res["sources"]
    assert any("Autonomous AI Search" in chunk for chunk in [res["text"]] + res["h1"])
    assert "database-backed catalog" in res["text"]


def test_needs_js_render_heuristic():
    """Tests SPA / unhydrated shell detection."""
    thin_spa = """
    <!DOCTYPE html>
    <html>
    <head><title>SPA App</title></head>
    <body>
        <div id="root"></div>
        <script src="/static/js/main.chunk.js"></script>
        <script src="/static/js/bundle.js"></script>
        <script src="/static/js/vendor.js"></script>
        <script src="/static/js/app.js"></script>
    </body>
    </html>
    """
    thin_soup = BeautifulSoup(thin_spa, "lxml")
    assert needs_js_render(thin_soup, visible_word_count=5) is True

    static_page = """
    <!DOCTYPE html>
    <html>
    <head><title>Static Standard Page</title></head>
    <body>
        <h1>Welcome to our Enterprise Platform</h1>
        <p>This is a fully server-rendered page containing comprehensive documentation, product features, commercial terms, and contact details with over two hundred words of clear informative copy.</p>
    </body>
    </html>
    """
    static_soup = BeautifulSoup(static_page, "lxml")
    assert needs_js_render(static_soup, visible_word_count=180) is False


def test_html_analyzer_merges_dynamic_content():
    """Verifies that analyze_html_content merges recovered dynamic CMS copy into evidence."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Dynamic Hybrid</title></head>
    <body>
        <div id="root"></div>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "title": "Generative Engine Optimization (GEO) Guide",
                    "content": "AI search engines prioritize sites with clear entity linking and verified semantic markup."
                }
            }
        }
        </script>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    store = EvidenceStore(run_id="test_run_123")
    res = analyze_html_content(soup, "https://example.com/dynamic", store)

    assert res["word_count"] > 10
    assert any("Generative Engine Optimization" in h for h in (res["h1"] + res["h2"]))
    
    # Check evidence store
    evidence_items = store.get_all()
    assert len(evidence_items) > 0


def test_browser_render_service_graceful_fallback():
    """Verifies that BrowserRenderService does not throw errors when called."""
    is_avail = BrowserRenderService.is_available()
    assert isinstance(is_avail, bool)


@pytest.mark.asyncio
async def test_browser_render_service_render_pdf_unavailable():
    """When browser is unavailable, render_pdf gracefully returns None."""
    from unittest.mock import patch
    with patch.object(BrowserRenderService, "get_browser", return_value=None):
        result = await BrowserRenderService.render_pdf("<html><body>Hello</body></html>")
        assert result is None


@pytest.mark.asyncio
async def test_browser_render_service_render_pdf_mocked_calls_page_pdf():
    """Verifies that render_pdf calls page.pdf without timeout argument and returns PDF bytes."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_page = AsyncMock()
    mock_page.pdf = AsyncMock(return_value=b"%PDF-1.4 sample content")
    mock_page.set_content = AsyncMock()
    mock_page.emulate_media = AsyncMock()
    mock_page.evaluate = AsyncMock()
    mock_page.close = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    with patch.object(BrowserRenderService, "get_browser", AsyncMock(return_value=mock_browser)):
        pdf_bytes = await BrowserRenderService.render_pdf("<html><body>Audit Dossier</body></html>", timeout_ms=30000)

        assert pdf_bytes == b"%PDF-1.4 sample content"
        mock_page.set_content.assert_awaited_once_with(
            "<html><body>Audit Dossier</body></html>",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        mock_page.emulate_media.assert_awaited_once_with(media="print")
        # Ensure page.pdf was called with prefer_css_page_size and print_background, and NOT timeout
        mock_page.pdf.assert_awaited_once_with(
            prefer_css_page_size=True,
            print_background=True,
        )
        mock_page.close.assert_awaited_once()
        mock_context.close.assert_awaited_once()
