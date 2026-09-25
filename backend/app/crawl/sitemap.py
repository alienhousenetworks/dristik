"""
Deep XML Sitemap & URL Frontier Parser.
Supports sitemap_index.xml recursion, priority sorting, hreflang discovery,
and URL tier classification (P1 high-conversion -> P4 archival).
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urlparse


@dataclass
class SitemapURL:
    url: str
    priority: float = 0.5
    changefreq: Optional[str] = None
    lastmod: Optional[str] = None
    hreflangs: List[str] = field(default_factory=list)
    tier: str = "P3"  # P1: High-value, P2: Standard, P3: Documentation, P4: Archival


class SitemapParser:
    def __init__(self, max_urls: int = 100000):
        self.max_urls = max_urls

    def classify_url_tier(self, url: str, xml_priority: float = 0.5) -> str:
        """Classifies URLs into conversion priority tiers."""
        path = urlparse(url).path.lower().rstrip("/")
        if path == "" or path in ("/pricing", "/product", "/features", "/solutions", "/enterprise", "/demo"):
            return "P1"
        if any(keyword in path for keyword in ("/pricing", "/buy", "/compare", "/vs-", "/integrations")):
            return "P1"
        if any(keyword in path for keyword in ("/blog", "/case-studies", "/customers", "/about")):
            return "P2"
        if any(keyword in path for keyword in ("/docs", "/api", "/developers", "/help", "/support")):
            return "P3"
        if xml_priority >= 0.8:
            return "P1"
        if xml_priority >= 0.5:
            return "P2"
        return "P4"

    def parse_sitemap_xml(self, xml_content: str) -> List[SitemapURL]:
        """
        Parses XML string containing either a <urlset> or a <sitemapindex>.
        Returns discovered URLs sorted by tier and priority.
        """
        urls: List[SitemapURL] = []
        # Strip namespaces for simple tag matching
        clean_xml = re.sub(r'\sxmlns(?::\w+)?="[^"]+"', '', xml_content, count=0)
        
        try:
            root = ET.fromstring(clean_xml)
        except ET.ParseError:
            return []

        # 1. Direct URL Set
        for url_node in root.findall(".//url"):
            loc_node = url_node.find("loc")
            if loc_node is None or not loc_node.text:
                continue
            loc = loc_node.text.strip()
            
            p_node = url_node.find("priority")
            try:
                priority = float(p_node.text.strip()) if p_node is not None and p_node.text else 0.5
            except ValueError:
                priority = 0.5

            cf_node = url_node.find("changefreq")
            changefreq = cf_node.text.strip() if cf_node is not None and cf_node.text else None

            lm_node = url_node.find("lastmod")
            lastmod = lm_node.text.strip() if lm_node is not None and lm_node.text else None

            hreflangs = []
            for link_node in url_node.findall(".//link"):
                hl = link_node.get("hreflang")
                if hl:
                    hreflangs.append(hl)

            tier = self.classify_url_tier(loc, priority)
            urls.append(SitemapURL(
                url=loc,
                priority=priority,
                changefreq=changefreq,
                lastmod=lastmod,
                hreflangs=hreflangs,
                tier=tier,
            ))

            if len(urls) >= self.max_urls:
                break

        # Sort: P1 first, then by priority descending
        tier_weights = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
        urls.sort(key=lambda u: (tier_weights.get(u.tier, 5), -u.priority))
        return urls

    def extract_child_sitemaps(self, xml_content: str) -> List[str]:
        """Extracts child sitemap URLs from a sitemapindex file."""
        clean_xml = re.sub(r'\sxmlns(?::\w+)?="[^"]+"', '', xml_content, count=0)
        try:
            root = ET.fromstring(clean_xml)
        except ET.ParseError:
            return []

        child_sitemaps: List[str] = []
        for sm_node in root.findall(".//sitemap"):
            loc_node = sm_node.find("loc")
            if loc_node is not None and loc_node.text:
                child_sitemaps.append(loc_node.text.strip())
        return child_sitemaps
