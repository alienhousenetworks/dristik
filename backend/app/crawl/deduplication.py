"""Exact URL de-duplication for a crawl.

Identity is the normalized URL. This does not treat two different URLs as the
same page from similar HTML.
"""
from __future__ import annotations

from typing import Iterable, Optional

from app.crawl.url_frontier import normalize_url


class UrlDeduper:
    def __init__(self, base_domain: str, base_origin: str):
        self.base_domain = base_domain
        self.base_origin = base_origin
        self.seen: set[str] = set()

    def key(self, raw_url: str) -> Optional[str]:
        return normalize_url(raw_url, self.base_domain, self.base_origin)

    def add(self, raw_url: str) -> bool:
        """Return True when the URL is new."""
        normalized = self.key(raw_url)
        if not normalized or normalized in self.seen:
            return False
        self.seen.add(normalized)
        return True

    def extend(self, urls: Iterable[str]) -> list[str]:
        admitted: list[str] = []
        for url in urls:
            normalized = self.key(url)
            if normalized and self.add(normalized):
                admitted.append(normalized)
        return admitted
