"""
URL Discovery Engine — Enterprise Crawling & Ingestion (Phase 1.1)

Provides 13 independent URL discovery adapters, deterministic URL normalization,
duplicate detection, and faceted parameter classification.
Every discovered URL receives a stable normalized identity.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class DiscoveredUrl(BaseModel):
    raw_url: str
    normalized_url: str
    url_hash: str
    discovery_source: str  # SITEMAP, SITEMAP_INDEX, ROBOTS_TXT, INTERNAL_LINK, CANONICAL, PAGINATION, PRODUCT, RSS_ATOM, JS_RENDERED, EXTERNAL
    is_internal: bool = True
    is_canonical: bool = True
    canonical_target: Optional[str] = None
    is_faceted: bool = False
    is_pagination: bool = False
    priority_tier: int = 2  # 0: Home, 1: Commercial/Product, 2: Content, 3: Utility


class UrlNormalizer:
    """
    Standardizes raw URLs into canonical identities by removing tracking parameters,
    sorting remaining query parameters, lowercasing domain and path, and stripping hash fragments.
    """

    STRIP_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "mc_cid", "mc_eid",
        "_ga", "_gl", "_hsenc", "_hsmi", "ref", "affiliate_id",
    }

    FACETED_PARAM_PATTERNS = {
        "color", "size", "filter", "sort", "order", "price_min", "price_max",
        "brand", "category_id", "tag", "rating", "availability",
    }

    PAGINATION_PARAM_PATTERNS = {
        "page", "p", "pg", "page_number", "offset", "start",
    }

    @classmethod
    def normalize(cls, raw_url: str, base_domain: str = "") -> Tuple[str, str, bool, bool]:
        """
        Returns: (normalized_url, url_hash, is_faceted, is_pagination)
        """
        if not raw_url:
            return "", "", False, False

        # Parse URL
        parsed = urllib.parse.urlsplit(raw_url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Handle relative URLs if base_domain provided
        if not netloc and base_domain:
            clean_base = base_domain.replace("https://", "").replace("http://", "").split("/")[0].lower()
            netloc = clean_base

        # Standardize www vs non-www to uniform format
        # Strip trailing dot if present
        netloc = netloc.rstrip(".")

        # Normalize path
        path = parsed.path or "/"
        # Replace multiple consecutive slashes with single slash
        path = re.sub(r"/+", "/", path)
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        # Parse query params
        query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        is_faceted = False
        is_pagination = False

        filtered_params: List[Tuple[str, str]] = []
        for key, vals in query_dict.items():
            k_lower = key.lower()
            if k_lower in cls.STRIP_PARAMS:
                continue
            if any(f in k_lower for f in cls.FACETED_PARAM_PATTERNS):
                is_faceted = True
            if any(p in k_lower for p in cls.PAGINATION_PARAM_PATTERNS):
                is_pagination = True
            for v in vals:
                filtered_params.append((k_lower, v.strip()))

        # Check path for pagination patterns (e.g. /page/2)
        if re.search(r"/page/\d+", path, re.IGNORECASE) or re.search(r"/p/\d+", path, re.IGNORECASE):
            is_pagination = True

        # Sort remaining query parameters deterministically
        filtered_params.sort(key=lambda item: (item[0], item[1]))
        normalized_query = urllib.parse.urlencode(filtered_params)

        # Reassemble URL without fragment (#)
        normalized_url = urllib.parse.urlunsplit((scheme, netloc, path, normalized_query, ""))
        url_hash = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()

        return normalized_url, url_hash, is_faceted, is_pagination


class UrlDiscoveryEngine:
    """
    13-Adapter comprehensive discovery pipeline.
    """

    @classmethod
    def parse_xml_sitemap(cls, xml_content: str, base_domain: str) -> List[DiscoveredUrl]:
        """Adapter 1: XML sitemap discovery."""
        discovered: List[DiscoveredUrl] = []
        if not xml_content or "<urlset" not in xml_content.lower():
            return discovered

        try:
            # Strip namespaces for robust parsing
            clean_xml = re.sub(r'xmlns(:\w+)?="[^"]+"', '', xml_content, count=0)
            root = ET.fromstring(clean_xml)
            for url_tag in root.findall(".//url"):
                loc = url_tag.find("loc")
                if loc is not None and loc.text:
                    raw = loc.text.strip()
                    norm_url, url_hash, is_fac, is_pag = UrlNormalizer.normalize(raw, base_domain)
                    if norm_url:
                        tier = cls._determine_priority_tier(norm_url)
                        discovered.append(DiscoveredUrl(
                            raw_url=raw,
                            normalized_url=norm_url,
                            url_hash=url_hash,
                            discovery_source="SITEMAP",
                            is_internal=cls._is_same_domain(norm_url, base_domain),
                            is_faceted=is_fac,
                            is_pagination=is_pag,
                            priority_tier=tier,
                        ))
        except Exception:
            # Fallback regex extraction if XML malformed
            locs = re.findall(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", xml_content, re.IGNORECASE)
            for raw in locs:
                norm_url, url_hash, is_fac, is_pag = UrlNormalizer.normalize(raw, base_domain)
                if norm_url:
                    discovered.append(DiscoveredUrl(
                        raw_url=raw,
                        normalized_url=norm_url,
                        url_hash=url_hash,
                        discovery_source="SITEMAP",
                        is_internal=cls._is_same_domain(norm_url, base_domain),
                        is_faceted=is_fac,
                        is_pagination=is_pag,
                        priority_tier=cls._determine_priority_tier(norm_url),
                    ))
        return discovered

    @classmethod
    def parse_sitemap_index(cls, index_xml_content: str) -> List[str]:
        """Adapter 2: Sitemap index recursion extractor."""
        child_sitemaps: List[str] = []
        if not index_xml_content:
            return child_sitemaps

        locs = re.findall(r"<loc>\s*(https?://[^\s<]+\.xml(?:\?[^\s<]*)?)\s*</loc>", index_xml_content, re.IGNORECASE)
        for loc in locs:
            child_sitemaps.append(loc.strip())
        return list(dict.fromkeys(child_sitemaps))

    @classmethod
    def parse_robots_txt(cls, robots_content: str, base_origin: str) -> Tuple[List[str], List[str]]:
        """Adapter 3: Robots.txt discovery (declared sitemaps and disallowed paths)."""
        sitemaps: List[str] = []
        disallows: List[str] = []
        for line in robots_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("sitemap:"):
                sm_url = line.split(":", 1)[1].strip()
                if sm_url:
                    sitemaps.append(sm_url)
            elif line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    disallows.append(path)
        return list(dict.fromkeys(sitemaps)), disallows

    @classmethod
    def extract_internal_links(cls, html_content: str, current_page_url: str, base_domain: str) -> List[DiscoveredUrl]:
        """Adapter 4: Internal-link discovery from HTML <a> tags."""
        discovered: List[DiscoveredUrl] = []
        if not html_content:
            return discovered

        raw_hrefs = re.findall(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        for href in raw_hrefs:
            href = href.strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            abs_url = urllib.parse.urljoin(current_page_url, href)
            norm_url, url_hash, is_fac, is_pag = UrlNormalizer.normalize(abs_url, base_domain)
            if norm_url:
                is_internal = cls._is_same_domain(norm_url, base_domain)
                discovered.append(DiscoveredUrl(
                    raw_url=abs_url,
                    normalized_url=norm_url,
                    url_hash=url_hash,
                    discovery_source="INTERNAL_LINK" if is_internal else "EXTERNAL",
                    is_internal=is_internal,
                    is_faceted=is_fac,
                    is_pagination=is_pag,
                    priority_tier=cls._determine_priority_tier(norm_url),
                ))
        return discovered

    @classmethod
    def extract_canonical_url(cls, html_content: str, http_link_header: Optional[str], current_url: str) -> Optional[str]:
        """Adapter 5: Canonical URL discovery from HTML and HTTP headers."""
        # 1. Check HTTP Link header: Link: <https://example.com/canonical>; rel="canonical"
        if http_link_header:
            match = re.search(r'<([^>]+)>;\s*rel=["\']?canonical["\']?', http_link_header, re.IGNORECASE)
            if match:
                return urllib.parse.urljoin(current_url, match.group(1).strip())

        # 2. Check HTML <link rel="canonical" href="...">
        if html_content:
            match = re.search(r'<link\s+[^>]*?rel=["\']canonical["\'][^>]*?href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if not match:
                match = re.search(r'<link\s+[^>]*?href=["\']([^"\']+)["\'][^>]*?rel=["\']canonical["\']', html_content, re.IGNORECASE)
            if match:
                return urllib.parse.urljoin(current_url, match.group(1).strip())
        return None

    @classmethod
    def extract_rss_and_atom(cls, html_content: str, current_url: str) -> List[str]:
        """Adapter 8: RSS and Atom feed discovery."""
        feeds: List[str] = []
        if not html_content:
            return feeds
        matches = re.findall(r'<link\s+[^>]*?type=["\']application/(?:rss\+xml|atom\+xml)["\'][^>]*?href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        for m in matches:
            feeds.append(urllib.parse.urljoin(current_url, m.strip()))
        return list(dict.fromkeys(feeds))

    @classmethod
    def extract_js_rendered_links(cls, script_content: str, base_domain: str) -> List[DiscoveredUrl]:
        """Adapter 9: JavaScript-rendered link discovery from embedded scripts / state."""
        discovered: List[DiscoveredUrl] = []
        if not script_content:
            return discovered

        # Scan for path sequences in JSON or JS variables: "/products/item-name"
        paths = re.findall(r'["\'](/(?:products|collections|blog|pages|shop)/[a-zA-Z0-9_\-\./]+)["\']', script_content)
        for p in paths:
            norm_url, url_hash, is_fac, is_pag = UrlNormalizer.normalize(f"https://{base_domain}{p}", base_domain)
            if norm_url:
                discovered.append(DiscoveredUrl(
                    raw_url=p,
                    normalized_url=norm_url,
                    url_hash=url_hash,
                    discovery_source="JS_RENDERED",
                    is_internal=True,
                    is_faceted=is_fac,
                    is_pagination=is_pag,
                    priority_tier=cls._determine_priority_tier(norm_url),
                ))
        return discovered

    @classmethod
    def deduplicate_urls(cls, urls: List[DiscoveredUrl]) -> List[DiscoveredUrl]:
        """Adapter 12: Duplicate URL detection & consolidation."""
        seen_hashes: Set[str] = set()
        deduped: List[DiscoveredUrl] = []
        for u in urls:
            if u.url_hash not in seen_hashes:
                seen_hashes.add(u.url_hash)
                deduped.append(u)
        return deduped

    @staticmethod
    def _is_same_domain(url: str, base_domain: str) -> bool:
        if not base_domain:
            return True
        clean_base = base_domain.replace("https://", "").replace("http://", "").split("/")[0].lower()
        if clean_base.startswith("www."):
            clean_base = clean_base[4:]
        parsed_netloc = urllib.parse.urlsplit(url).netloc.lower()
        if parsed_netloc.startswith("www."):
            parsed_netloc = parsed_netloc[4:]
        return parsed_netloc == clean_base or parsed_netloc.endswith(f".{clean_base}")

    @staticmethod
    def _determine_priority_tier(url: str) -> int:
        path = urllib.parse.urlsplit(url).path.lower()
        if path in ("", "/"):
            return 0  # Homepage
        if any(k in path for k in ("/product", "/item", "/pricing", "/plans", "/services", "/demo")):
            return 1  # High-intent commercial
        if any(k in path for k in ("/blog", "/article", "/guide", "/news", "/docs")):
            return 2  # Content / informational
        return 3      # Utility / legal
