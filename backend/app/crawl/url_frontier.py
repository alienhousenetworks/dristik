"""URL normalization, page roles, and the crawl frontier.

These functions are the crawler's own URL rules. The crawler calls them so
there is one implementation of normalization and role ordering.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urldefrag, urljoin, urlparse


class UrlCrawlState(str, Enum):
    """Explicit lifecycle status for every discoverable URL in an audit."""
    DISCOVERED = "DISCOVERED"
    QUEUED = "QUEUED"
    FETCHED = "FETCHED"
    RENDERED = "RENDERED"
    PARSED = "PARSED"
    ANALYZED = "ANALYZED"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    ROBOTS_DENIED = "ROBOTS_DENIED"
    RENDER_FAILED = "RENDER_FAILED"
    PARSE_FAILED = "PARSE_FAILED"
    DUPLICATE = "DUPLICATE"


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

    Each open role reserves one URL. Scoring every commercial URL with the same
    bonus lets a long product list take the whole budget in one batch and leave
    pricing, contact, and about unfetched.
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

    # Slot bonuses are 1000 apart. page_priority is at most 100, so a reserved
    # role stays ahead of every later role and of the unreserved remainder.
    open_slots = []
    if "homepage" not in filled:
        open_slots.append(("homepage", 5000))
    if "commercial" not in filled:
        open_slots.append(("commercial", 4000))
    if "high_intent" not in filled:
        open_slots.append(("high_intent", 3000))
    if "secondary_commercial" not in filled:
        open_slots.append(("commercial", 2000))
    if "proof" not in filled:
        open_slots.append(("proof", 1000))

    remaining = list(urls)
    slot_bonus = {}
    for role, bonus in open_slots:
        candidates = [url for url in remaining if url_role(url) == role]
        if not candidates:
            continue
        # Equal priority keeps the earlier discovered URL.
        chosen = sorted(candidates, key=page_priority, reverse=True)[0]
        slot_bonus[chosen] = bonus
        remaining.remove(chosen)

    def rank(url: str) -> int:
        return slot_bonus.get(url, 0) + page_priority(url)

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
    """Normalized, de-duplicated URL queue with explicit discovery & sampling state tracking."""

    def __init__(self, base_domain: str, base_origin: str):
        self.base_domain = base_domain
        self.base_origin = base_origin
        self._seen: set[str] = set()
        self.url_states: Dict[str, UrlCrawlState] = {}
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}

    def normalize(self, raw_url: str) -> Optional[str]:
        return normalize_url(raw_url, self.base_domain, self.base_origin)

    def admit(self, raw_url: str) -> Optional[str]:
        """Return the normalized URL the first time it is admitted."""
        normalized = self.normalize(raw_url)
        if not normalized:
            return None
        self.discovered_urls.add(normalized)
        if normalized in self._seen:
            self.url_states[normalized] = UrlCrawlState.DUPLICATE
            return None
        self._seen.add(normalized)
        self.url_states[normalized] = UrlCrawlState.QUEUED
        return normalized

    def mark_state(self, url: str, state: UrlCrawlState, error: Optional[str] = None) -> None:
        """Track explicit transition through the crawl state machine."""
        normalized = self.normalize(url) or url
        self.url_states[normalized] = state
        if state in (UrlCrawlState.FETCHED, UrlCrawlState.RENDERED, UrlCrawlState.PARSED, UrlCrawlState.ANALYZED):
            self.crawled_urls.add(normalized)
        elif state in (UrlCrawlState.BLOCKED, UrlCrawlState.TIMEOUT, UrlCrawlState.HTTP_ERROR, UrlCrawlState.ROBOTS_DENIED, UrlCrawlState.RENDER_FAILED, UrlCrawlState.PARSE_FAILED):
            if error:
                self.failed_urls[normalized] = error

    def get_coverage_summary(self) -> Dict[str, Any]:
        """Return honest coverage metrics distinguishing discovered URLs from crawled sample."""
        disc = len(self.discovered_urls)
        crawled = len(self.crawled_urls)
        scope = "EXHAUSTIVE" if disc > 0 and crawled >= disc else "REPRESENTATIVE" if crawled > 0 else "EMPTY"
        pct = round((crawled / disc) * 100, 1) if disc > 0 else 0.0
        return {
            "discovered_count": disc,
            "inspected_count": crawled,
            "failed_count": len(self.failed_urls),
            "coverage_percentage": pct,
            "sampling_scope": scope,
            "is_representative_sample": disc > crawled,
            "sampling_note": f"Sampled {crawled} of {disc} discovered URLs ({pct}% coverage; {scope} scope)" if disc > crawled else f"Inspected all {crawled} discovered URLs ({scope} scope)",
        }

    def order(self, urls: List[str], crawled_pages: List[Any]) -> List[str]:
        return order_for_roles(urls, crawled_pages)
