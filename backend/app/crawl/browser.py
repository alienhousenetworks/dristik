"""
Enterprise Headless Browser Rendering Service
Executes dynamic client-side JavaScript, waiting for database-driven content
to hydrate into the DOM. Uses high-performance asset blocking (images, media, fonts)
for fast execution and minimal CPU/memory overhead.
"""
import time
import asyncio
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings

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
                except Exception:
                    cls._browser = None
                    return None
            return cls._browser

    @classmethod
    async def render_page(
        cls,
        url: str,
        timeout_ms: Optional[int] = None
    ) -> Tuple[Optional[str], int, float, Dict[str, str], Optional[str], Optional[str]]:
        """
        Renders a page using headless Chromium, waiting for DOM hydration.
        Returns: (html_content, status_code, ttfb_ms, headers, error_msg, inner_text)
        inner_text is document.body.innerText — what a person can actually read.
        """
        if not cls.is_available():
            return None, 0, 0.0, {}, "playwright_not_installed", None

        start_time = time.time()
        timeout = timeout_ms or settings.PLAYWRIGHT_TIMEOUT_MS

        browser = await cls.get_browser()
        if not browser:
            return None, 0, 0.0, {}, "browser_launch_failed", None

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
            resp_headers = {"x-crawler": "playwright-local-js"}

            return html_content, status_code, ttfb_ms, resp_headers, None, inner_text

        except Exception as e:
            ttfb_ms = (time.time() - start_time) * 1000
            return None, 0, ttfb_ms, {}, str(e), None

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
