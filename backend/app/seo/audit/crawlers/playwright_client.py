"""Real browser-backed page rendering for audits.

This crawler never fabricates a successful response. Browser startup, navigation,
and rendering failures are returned as explicit unavailable states for callers to
surface or fall back from deliberately.
"""
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urlparse

from app.seo.audit.crawlers.base import BaseCrawler
from app.seo.intelligence.mobile_experience import DEVICE_MATRIX, MobileExperienceEngine

_LAYOUT_JS = """
() => {
  const inner = window.innerWidth || 0;
  const scroll = document.documentElement ? document.documentElement.scrollWidth : 0;
  const elements = [];
  if (scroll > inner + 1) {
    elements.push({selector: "documentElement", width: scroll, height: 0, is_interactive: false});
  }
  const nodes = document.querySelectorAll("a, button, input, select, textarea, [role='button']");
  for (const el of nodes) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    elements.push({
      selector: (el.tagName || "el").toLowerCase(),
      width: rect.width,
      height: rect.height,
      is_interactive: true
    });
    if (elements.length > 40) break;
  }
  return {inner_width: inner, scroll_width: scroll, elements: elements};
}
"""


class PlaywrightCrawler(BaseCrawler):
    def __init__(
        self,
        *,
        timeout_ms: int = 30000,
        viewport_width: int = 1440,
        viewport_height: int = 900,
        headless: bool = True,
    ) -> None:
        self.timeout_ms = timeout_ms
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.headless = headless

    async def fetch_page(self, url: str) -> Dict[str, Any]:
        """Navigate with Chromium and return actual rendered DOM or an explicit failure."""
        parsed = urlparse(str(url or ""))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {
                "url": url,
                "state": "INVALID_URL",
                "status_code": None,
                "rendered": False,
                "error": "Only absolute HTTP(S) URLs can be rendered.",
            }

        browser = None
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=self.headless)
                page = await browser.new_page(
                    viewport={
                        "width": self.viewport_width,
                        "height": self.viewport_height,
                    }
                )
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                # Some pages keep long-lived requests open. A bounded best-effort
                # network-idle wait improves DOM stability without blocking forever.
                try:
                    await page.wait_for_load_state("networkidle", timeout=min(3000, self.timeout_ms))
                except Exception:
                    pass

                rendered_dom = await page.content()
                title = await page.title()
                status_code = response.status if response is not None else None
                headers = await response.all_headers() if response is not None else {}
                final_url = page.url
                return {
                    "url": final_url,
                    "requested_url": url,
                    "state": "RENDERED" if rendered_dom else "EMPTY_RENDER",
                    "status_code": status_code,
                    "headers": headers,
                    "title": title,
                    "html": rendered_dom,
                    "rendered_dom": rendered_dom,
                    "rendered": bool(rendered_dom),
                    "viewport": {
                        "width": self.viewport_width,
                        "height": self.viewport_height,
                    },
                    "http_error": bool(status_code is not None and status_code >= 400),
                    "error": None if rendered_dom else "The browser returned an empty DOM.",
                }
        except Exception as exc:
            return {
                "url": url,
                "requested_url": url,
                "state": "UNAVAILABLE",
                "status_code": None,
                "headers": {},
                "html": None,
                "rendered_dom": None,
                "rendered": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        finally:
            if browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass


async def _playwright_device_snapshots(url: str, timeout_ms: int = 15000) -> Dict[str, Dict[str, Any]]:
    """Open one headless browser and resize it across the emulated device matrix."""
    from playwright.async_api import async_playwright

    snapshots: Dict[str, Dict[str, Any]] = {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            for spec in DEVICE_MATRIX:
                page = await browser.new_page(
                    viewport={"width": int(spec["width"]), "height": int(spec["height"])},
                    is_mobile=bool(spec["is_mobile"]),
                    has_touch=bool(spec["has_touch"]),
                )
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    metrics = await page.evaluate(_LAYOUT_JS)
                    snapshots[spec["id"]] = {
                        "html": await page.content(),
                        "elements": list((metrics or {}).get("elements") or []),
                        "inner_width": (metrics or {}).get("inner_width"),
                        "scroll_width": (metrics or {}).get("scroll_width"),
                    }
                except Exception as exc:
                    snapshots[spec["id"]] = {"error": f"{type(exc).__name__}: {exc}", "elements": None}
                finally:
                    await page.close()
        finally:
            await browser.close()
    return snapshots


async def measure_emulated_devices(
    url: str,
    fetcher: Optional[Callable[[str], Awaitable[Dict[str, Dict[str, Any]]]]] = None,
) -> Dict[str, Any]:
    """Measure one URL on the emulated device matrix.

    The result is always labeled as an emulated browser, never a physical device.
    A missing browser or a failed navigation is DATA_UNAVAILABLE, not a pass.
    """
    parsed = urlparse(str(url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {
            "url": url,
            "physical_device": False,
            "measurement_method": "not_run",
            "verification_status": "NOT_TESTED",
            "label": "Browser-emulated device. Not a physical phone. Menus, forms, and checkout were not clicked.",
            "error": "Only absolute HTTP(S) URLs can be emulated.",
            "devices": [],
        }
    try:
        snapshots = await (fetcher or _playwright_device_snapshots)(url)
    except Exception as exc:
        return {
            "url": url,
            "physical_device": False,
            "measurement_method": "emulated_browser",
            "verification_status": "DATA_UNAVAILABLE",
            "label": "Browser-emulated device. Not a physical phone. Menus, forms, and checkout were not clicked.",
            "error": f"{type(exc).__name__}: {exc}",
            "devices": [],
        }
    report = MobileExperienceEngine.audit_device_matrix(url, snapshots)
    report["physical_device"] = False
    return report
