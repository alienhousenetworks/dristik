"""SSRF-Hardened and Byte-Limited Native HTTP Crawler for SEO Audits & Verification."""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.core.security.ssrf import is_safe_url
from app.crawl.response_limits import read_response_limited
from app.seo.audit.crawlers.base import BaseCrawler


class SSRFBlockedError(ValueError):
    """Raised when an initial URL or redirect target fails SSRF egress policy."""


class NativeHTTPCrawler(BaseCrawler):
    MAX_REDIRECTS = 10

    async def fetch_page(self, url: str) -> Dict[str, Any]:
        current_url = url.strip()
        redirect_chain: List[Dict[str, Any]] = []
        max_bytes = int(getattr(settings, "CRAWL_MAX_HTML_BYTES", 5 * 1024 * 1024) or 5 * 1024 * 1024)
        start = time.monotonic()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            for _ in range(self.MAX_REDIRECTS + 1):
                if getattr(settings, "SSRF_PROTECTION_ENABLED", True):
                    safe, reason = is_safe_url(current_url)
                    if not safe:
                        raise SSRFBlockedError(f"SSRF_BLOCKED: {reason} ({current_url})")

                async with client.stream("GET", current_url) as resp:
                    status_code = resp.status_code
                    headers = dict(resp.headers)
                    if status_code in (301, 302, 303, 307, 308) and headers.get("location"):
                        next_url = urljoin(current_url, headers["location"])
                        redirect_chain.append({
                            "from_url": current_url,
                            "to_url": next_url,
                            "status_code": status_code,
                        })
                        current_url = next_url
                        continue

                    body = await read_response_limited(resp, max_bytes)
                    elapsed_ms = round((time.monotonic() - start) * 1000.0, 1)
                    html_text = body.decode("utf-8", errors="replace")
                    content_sha256 = hashlib.sha256(body).hexdigest()
                    return {
                        "url": str(resp.url),
                        "requested_url": url,
                        "status_code": status_code,
                        "headers": headers,
                        "html": html_text,
                        "content_sha256": content_sha256,
                        "ttfb_ms": elapsed_ms,
                        "redirect_chain": redirect_chain,
                    }

        raise ValueError(f"Redirect loop or chain exceeded {self.MAX_REDIRECTS} hops for {url}")
