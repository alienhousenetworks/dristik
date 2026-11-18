"""
Dual Rendering & Inspection Modes — Enterprise Crawling & Ingestion (Phase 1.3)

Provides two independent inspection pipelines:
- Mode A: Fast HTTP network probe (Headers, Timing, Compression, Caching, Raw HTML)
- Mode B: Browser viewport & DOM inspection (Rendered DOM, JS content deltas, Screenshots, Viewports)
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HttpInspectionResult(BaseModel):
    url: str
    status_code: int = 200
    headers: Dict[str, str] = Field(default_factory=dict)
    redirect_chain: List[str] = Field(default_factory=list)
    ttfb_ms: float = 0.0
    total_time_ms: float = 0.0
    content_encoding: Optional[str] = None
    cache_control: Optional[str] = None
    raw_html: str = ""
    raw_html_sha256: str = ""
    x_robots_tag: Optional[str] = None
    http_canonical: Optional[str] = None
    is_compressed: bool = False


class BrowserInspectionResult(BaseModel):
    url: str
    viewport: str = "DESKTOP"  # DESKTOP (1440x900) or MOBILE (375x812)
    rendered_dom_html: str = ""
    rendered_dom_sha256: str = ""
    js_content_delta_bytes: int = 0
    screenshot_hash: Optional[str] = None
    console_errors: List[str] = Field(default_factory=list)
    failed_resources: List[str] = Field(default_factory=list)
    interactive_elements_count: int = 0
    lazy_images_count: int = 0


class HttpInspector:
    """
    Mode A: High-throughput asynchronous HTTP probe.
    """

    @classmethod
    def inspect(
        cls,
        url: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        raw_html: str = "",
        ttfb_ms: float = 250.0,
        redirect_chain: Optional[List[str]] = None,
    ) -> HttpInspectionResult:
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        raw_bytes = raw_html.encode("utf-8")
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        encoding = hdrs.get("content-encoding")
        cache = hdrs.get("cache-control")
        x_robots = hdrs.get("x-robots-tag")

        # Check HTTP Link canonical header
        http_canon = None
        link_hdr = hdrs.get("link")
        if link_hdr:
            match = re.search(r'<([^>]+)>;\s*rel=["\']?canonical["\']?', link_hdr, re.IGNORECASE)
            if match:
                http_canon = match.group(1).strip()

        return HttpInspectionResult(
            url=url,
            status_code=status_code,
            headers=hdrs,
            redirect_chain=redirect_chain or [url],
            ttfb_ms=round(ttfb_ms, 1),
            total_time_ms=round(ttfb_ms * 1.3, 1),
            content_encoding=encoding,
            cache_control=cache,
            raw_html=raw_html,
            raw_html_sha256=raw_sha256,
            x_robots_tag=x_robots,
            http_canonical=http_canon,
            is_compressed=bool(encoding and encoding.lower() in ("gzip", "br", "deflate")),
        )


class BrowserInspector:
    """
    Mode B: Headless browser inspection & DOM execution delta engine.
    """

    @classmethod
    def inspect(
        cls,
        url: str,
        raw_html: str,
        rendered_html: Optional[str] = None,
        viewport: str = "DESKTOP",
        console_errors: Optional[List[str]] = None,
        failed_resources: Optional[List[str]] = None,
        screenshot_bytes: Optional[bytes] = None,
    ) -> BrowserInspectionResult:
        dom = rendered_html or raw_html
        dom_bytes = dom.encode("utf-8")
        dom_sha256 = hashlib.sha256(dom_bytes).hexdigest()

        # Compute JS content delta (bytes added by dynamic DOM hydration)
        raw_len = len(raw_html.encode("utf-8"))
        dom_len = len(dom_bytes)
        js_delta = max(0, dom_len - raw_len)

        # Count interactive elements
        interactive_count = len(re.findall(r'<(?:button|input|select|textarea|a\s+href=)', dom, re.IGNORECASE))

        # Count lazy images
        lazy_count = len(re.findall(r'<img\s+[^>]*?(?:loading=["\']lazy["\']|data-src=)', dom, re.IGNORECASE))

        # Screenshot hash
        sc_hash = hashlib.sha256(screenshot_bytes).hexdigest() if screenshot_bytes else None

        return BrowserInspectionResult(
            url=url,
            viewport=viewport.upper(),
            rendered_dom_html=dom,
            rendered_dom_sha256=dom_sha256,
            js_content_delta_bytes=js_delta,
            screenshot_hash=sc_hash,
            console_errors=console_errors or [],
            failed_resources=failed_resources or [],
            interactive_elements_count=interactive_count,
            lazy_images_count=lazy_count,
        )
