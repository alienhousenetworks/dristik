"""
Enterprise Headless Browser Rendering Service
Executes dynamic client-side JavaScript, waiting for database-driven content
to hydrate into the DOM. Uses high-performance asset blocking (images, media, fonts)
for fast execution and minimal CPU/memory overhead.
"""
import time
import asyncio
import logging
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings

logger = logging.getLogger("dristik.browser")

# Graceful detection of playwright package
_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, Playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class BrowserRenderService:
    _playwright: Optional[Any] = None
    _browser: Optional[Any] = None
    _lock = asyncio.Lock()

    @classmethod
    def is_available(cls) -> bool:
        """Returns True if Playwright is installed and enabled in settings."""
        return _PLAYWRIGHT_AVAILABLE and settings.PLAYWRIGHT_ENABLED

    @classmethod
    async def get_browser(cls) -> Optional[Any]:
        if not cls.is_available():
            return None

        async with cls._lock:
            if cls._browser is None or not cls._browser.is_connected():
                try:
                    cls._playwright = await async_playwright().start()
                    cls._browser = await cls._playwright.chromium.launch(
                        headless=settings.PLAYWRIGHT_HEADLESS,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                            "--disable-extensions",
                        ]
                    )
                except Exception as exc:
                    logger.warning("Failed to launch headless Chromium: %s", exc)
                    cls._browser = None
                    return None
            return cls._browser

    @classmethod
    async def render_page(
        cls,
        url: str,
        timeout_ms: Optional[int] = None
    ) -> Tuple[Optional[str], int, float, Dict[str, str], Optional[str], Optional[str], Optional[Dict[str, Any]]]:
        """
        Renders a page using headless Chromium, waiting for DOM hydration.
        Returns: (html_content, status_code, ttfb_ms, headers, error_msg, inner_text, perf_data)
        inner_text is document.body.innerText — what a person can actually read.
        perf_data contains W3C Navigation Timing Level 2 and resource footprint.
        """
        if not cls.is_available():
            return None, 0, 0.0, {}, "playwright_not_installed", None, None

        start_time = time.time()
        timeout = timeout_ms or settings.PLAYWRIGHT_TIMEOUT_MS

        browser = await cls.get_browser()
        if not browser:
            return None, 0, 0.0, {}, "browser_launch_failed", None, None

        context = None
        page = None
        try:
            context = await browser.new_context(
                user_agent=settings.USER_AGENT,
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True
            )
            page = await context.new_page()

            # Enterprise Optimization: Block heavy media and tracking assets
            async def filter_route(route):
                req = route.request
                rtype = req.resource_type
                if rtype in ["image", "media", "font"]:
                    await route.abort()
                elif any(t in req.url.lower() for t in ["google-analytics", "googletagmanager", "hotjar", "facebook.net", "clarity.ms"]):
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", filter_route)

            # networkidle hangs on long-polling/WebGL sites; DOM + a short hydrate wait is enough
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            status_code = response.status if response else 200
            ttfb_ms = (time.time() - start_time) * 1000

            try:
                await page.wait_for_selector("main, article, h1, [role='main'], body", timeout=4000)
            except Exception:
                pass

            # Dismiss cookie / protocol gates that hide the real page after hydration
            for selector in [
                "button:has-text('Accept')",
                "button:has-text('Accept Protocol')",
                "button:has-text('I agree')",
                "button:has-text('Allow')",
                "#cookie-banner button",
                "[id*='cookie'] button",
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click(timeout=800)
                        break
                except Exception:
                    continue

            try:
                await page.wait_for_timeout(600)
            except Exception:
                pass

            html_content = await page.content()
            inner_text = None
            try:
                inner_text = await page.evaluate(
                    """() => {
                        const main = document.querySelector('main, [role=main], article, #content, #main');
                        const root = main || document.body;
                        return root ? (root.innerText || root.textContent || '') : '';
                    }"""
                )
            except Exception:
                inner_text = None

            # Extract Navigation Timing Level 2 and Resource Timings for true TTFB and Lab CWV
            perf_data = None
            try:
                perf_data = await page.evaluate(
                    """() => {
                        try {
                            const nav = performance.getEntriesByType('navigation')[0] || {};
                            const paint = performance.getEntriesByType('paint') || [];
                            const resources = performance.getEntriesByType('resource') || [];

                            const fp = paint.find(p => p.name === 'first-paint');
                            const fcp = paint.find(p => p.name === 'first-contentful-paint');

                            let ttfb = 0;
                            if (nav.responseStart && nav.requestStart) {
                                ttfb = Math.max(0, nav.responseStart - nav.requestStart);
                            } else if (nav.responseStart) {
                                ttfb = Math.max(0, nav.responseStart);
                            }

                            const dns = (nav.domainLookupEnd && nav.domainLookupStart) ? Math.max(0, nav.domainLookupEnd - nav.domainLookupStart) : 0;
                            const tcp = (nav.connectEnd && nav.connectStart) ? Math.max(0, nav.connectEnd - nav.connectStart) : 0;
                            const tls = (nav.secureConnectionStart && nav.connectEnd) ? Math.max(0, nav.connectEnd - nav.secureConnectionStart) : 0;
                            const download = (nav.responseEnd && nav.responseStart) ? Math.max(0, nav.responseEnd - nav.responseStart) : 0;
                            const dom_content_loaded = nav.domContentLoadedEventEnd || 0;
                            const load_event = nav.loadEventEnd || 0;

                            let js_bytes = 0, css_bytes = 0, img_bytes = 0, font_bytes = 0, total_bytes = 0;
                            const counts = { document: 1, script: 0, stylesheet: 0, image: 0, font: 0, other: 0 };
                            const render_blocking = [];
                            const third_party_scripts = [];
                            const pageHost = window.location.hostname;

                            resources.forEach(r => {
                                const transfer = r.transferSize || r.encodedBodySize || 0;
                                total_bytes += transfer;
                                const itype = (r.initiatorType || 'other').toLowerCase();
                                if (itype === 'script') {
                                    js_bytes += transfer;
                                    counts.script = (counts.script || 0) + 1;
                                } else if (itype === 'css' || itype === 'link') {
                                    css_bytes += transfer;
                                    counts.stylesheet = (counts.stylesheet || 0) + 1;
                                } else if (itype === 'img' || itype === 'image') {
                                    img_bytes += transfer;
                                    counts.image = (counts.image || 0) + 1;
                                } else if (itype === 'font') {
                                    font_bytes += transfer;
                                    counts.font = (counts.font || 0) + 1;
                                } else {
                                    counts.other = (counts.other || 0) + 1;
                                }

                                if (r.renderBlockingStatus === 'blocking') {
                                    render_blocking.push({ url: r.name, initiator: itype, duration_ms: Math.round(r.duration || 0) });
                                }

                                try {
                                    const u = new URL(r.name);
                                    if (u.hostname !== pageHost && !u.hostname.endsWith('.' + pageHost)) {
                                        if (itype === 'script') {
                                            third_party_scripts.push({ url: r.name, hostname: u.hostname, transfer_bytes: transfer });
                                        }
                                    }
                                } catch(e) {}
                            });

                            return {
                                ttfb_ms: Math.round(ttfb * 10) / 10,
                                dns_ms: Math.round(dns * 10) / 10,
                                tcp_ms: Math.round(tcp * 10) / 10,
                                tls_ms: Math.round(tls * 10) / 10,
                                download_ms: Math.round(download * 10) / 10,
                                dom_content_loaded_ms: Math.round(dom_content_loaded * 10) / 10,
                                load_event_ms: Math.round(load_event * 10) / 10,
                                fcp_ms: fcp ? Math.round(fcp.startTime * 10) / 10 : null,
                                total_transferred_bytes: total_bytes,
                                js_bytes: js_bytes,
                                css_bytes: css_bytes,
                                img_bytes: img_bytes,
                                font_bytes: font_bytes,
                                request_counts: counts,
                                total_requests: resources.length + 1,
                                render_blocking: render_blocking,
                                third_party_scripts: third_party_scripts
                            };
                        } catch(err) {
                            return null;
                        }
                    }"""
                )
            except Exception:
                perf_data = None

            if perf_data and perf_data.get("ttfb_ms") and perf_data["ttfb_ms"] > 0:
                ttfb_ms = perf_data["ttfb_ms"]

            resp_headers = {"x-crawler": "playwright-local-js"}

            return html_content, status_code, ttfb_ms, resp_headers, None, inner_text, perf_data

        except Exception as e:
            ttfb_ms = (time.time() - start_time) * 1000
            return None, 0, ttfb_ms, {}, str(e), None, None

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

    @classmethod
    async def render_pdf(cls, html: str, timeout_ms: int = 60000) -> Optional[bytes]:
        """
        Renders standalone HTML to a PDF using headless Chromium.
        Honors the document's CSS @page size/margins and preserves backgrounds.
        Returns None when the browser is unavailable or rendering fails.
        """
        browser = await cls.get_browser()
        if browser is None:
            return None
        context = None
        page = None
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.set_content(html, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.emulate_media(media="print")
            try:
                await asyncio.wait_for(page.evaluate("document.fonts && document.fonts.ready"), timeout=2.0)
            except Exception:
                pass
            pdf_coro = page.pdf(
                prefer_css_page_size=True,
                print_background=True,
            )
            if timeout_ms and timeout_ms > 0:
                return await asyncio.wait_for(pdf_coro, timeout=timeout_ms / 1000.0)
            return await pdf_coro
        except Exception as exc:
            logger.warning("Failed to render PDF with Playwright: %s", exc)
            return None
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

    @classmethod
    async def shutdown(cls):
        """Cleanly releases browser and playwright resources."""
        async with cls._lock:
            if cls._browser:
                try:
                    await cls._browser.close()
                except Exception:
                    pass
                cls._browser = None
            if cls._playwright:
                try:
                    await cls._playwright.stop()
                except Exception:
                    pass
                cls._playwright = None
