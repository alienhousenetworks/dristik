"""URL normalization, page roles, and the crawl frontier.

These functions are the crawler's own URL rules. The crawler calls them so
there is one implementation of normalization and role ordering.
"""
from __future__ import annotations

from typing import Any, List, Optional
from urllib.parse import urldefrag, urljoin, urlparse


def classify_page_type(path: str) -> str:
    p = path.lower().strip("/")
    if not p or p == "":
        return "homepage"
    if any(k in p for k in ["privacy", "terms", "legal", "cookie", "gdpr", "compliance"]):
        return "legal"
    if any(k in p for k in ["blog", "news", "articles", "posts", "insights", "resources"]):
        return "blog"
    if any(k in p for k in ["pricing", "price", "plans", "tier", "subscription", "cost"]):
        return "pricing"
    if any(k in p for k in ["docs", "documentation", "guide", "learn", "developer"]):
        return "docs"
    if any(k in p for k in ["contact", "support", "help", "sales", "demo"]):
        return "contact"
    if any(k in p for k in ["features", "product", "solutions", "platform", "integrations", "services"]):
        return "product"
    if any(k in p for k in ["about", "team", "story", "mission", "leadership", "careers"]):
        return "about"
    return "general"


def url_role(url: str) -> str:
    """Role slot used to keep a short crawl representative."""
    parsed = urlparse(url)
    ptype = classify_page_type(parsed.path)
    if ptype == "homepage":
        return "homepage"
    if ptype == "product":
        return "commercial"
    if ptype in ("pricing", "contact"):
        return "high_intent"
    if ptype == "about":
        return "proof"
    return "other"


def page_priority(url: str) -> int:
    parsed = urlparse(url)
    ptype = classify_page_type(parsed.path)
    weights = {
        "homepage": 100,
        "pricing": 95,
        "product": 85,
        "about": 80,
        "contact": 75,
        "docs": 70,
        "blog": 55,
        "legal": 45,
        "general": 40,
    }
    return weights.get(ptype, 30)


def order_for_roles(urls: List[str], crawled_pages: List[Any]) -> List[str]:
    """
    Fill unfilled roles before spending the remaining budget on the priority queue.
    Homepage, primary commercial, high-intent, a second commercial URL, then proof.
    """
    commercial_count = 0
    filled = set()
    for page in crawled_pages:
        role = url_role(getattr(page, "url", "") or "")
        if role == "commercial":
            commercial_count += 1
            filled.add("commercial")
            if commercial_count >= 2:
                filled.add("secondary_commercial")
        elif role != "other":
            filled.add(role)

    def rank(url: str) -> int:
        role = url_role(url)
        bonus = 0
        if role == "homepage" and "homepage" not in filled:
            bonus = 5000
        elif role == "commercial" and "commercial" not in filled:
            bonus = 4000
        elif role == "high_intent" and "high_intent" not in filled:
            bonus = 3000
        elif role == "commercial" and "secondary_commercial" not in filled:
            bonus = 2000
        elif role == "proof" and "proof" not in filled:
            bonus = 1000
        return bonus + page_priority(url)

    return sorted(urls, key=rank, reverse=True)


def normalize_url(raw_url: str, base_domain: str, base_origin: str) -> Optional[str]:
    if not raw_url or raw_url.startswith(("javascript:", "mailto:", "tel:", "#", "data:")):
        return None
    joined = urljoin(base_origin, raw_url)
    clean_url, _ = urldefrag(joined)
    parsed = urlparse(clean_url)
    if parsed.scheme.lower() not in ["http", "https"]:
        return None

    netloc = parsed.netloc.lower()
    if ":" in netloc:
        parts = netloc.split(":", 1)
        if (parsed.scheme.lower() == "http" and parts[1] == "80") or (parsed.scheme.lower() == "https" and parts[1] == "443"):
            netloc = parts[0]

    def _host(value: str) -> str:
        host = (value or "").lower().split(":")[0]
        return host[4:] if host.startswith("www.") else host

    base_dom = _host(base_domain)
    if _host(netloc) != base_dom and not _host(netloc).endswith("." + base_dom):
        return None

    path = parsed.path
    if path.endswith(("/index.html", "/index.htm", "/index.php")):
        path = path.rsplit("/", 1)[0]

    path = path.rstrip("/")

    query = parsed.query
    if query:
        filtered_params = []
        for param in query.split("&"):
            k = param.split("=")[0].lower()
            if not any(k.startswith(p) for p in ["utm_", "fbclid", "gclid", "ref", "mc_cid"]):
                filtered_params.append(param)
        query = "&".join(filtered_params)

    normalized = f"{parsed.scheme.lower()}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


class UrlFrontier:
    """Normalized, de-duplicated URL queue for one site."""

    def __init__(self, base_domain: str, base_origin: str):
        self.base_domain = base_domain
        self.base_origin = base_origin
        self._seen: set[str] = set()

    def normalize(self, raw_url: str) -> Optional[str]:
        return normalize_url(raw_url, self.base_domain, self.base_origin)

    def admit(self, raw_url: str) -> Optional[str]:
        """Return the normalized URL the first time it is admitted."""
        normalized = self.normalize(raw_url)
        if not normalized or normalized in self._seen:
            return None
        self._seen.add(normalized)
        return normalized

    def order(self, urls: List[str], crawled_pages: List[Any]) -> List[str]:
        return order_for_roles(urls, crawled_pages)
