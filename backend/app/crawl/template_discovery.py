"""
Page Classification & Template Discovery — Enterprise Crawling & Ingestion (Phase 1.4)

Automatically classifies pages into 14 standard types and performs structural
DOM fingerprinting to cluster hundreds of URLs into shared template archetypes.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class StandardPageType(str, Enum):
    HOMEPAGE = "HOMEPAGE"
    PRODUCT = "PRODUCT"
    COLLECTION = "COLLECTION"
    SERVICE = "SERVICE"
    BLOG_ARTICLE = "BLOG_ARTICLE"
    LANDING_PAGE = "LANDING_PAGE"
    PRICING = "PRICING"
    ABOUT_COMPANY = "ABOUT_COMPANY"
    CONTACT = "CONTACT"
    DOCUMENTATION = "DOCUMENTATION"
    FAQ = "FAQ"
    SEARCH_RESULTS = "SEARCH_RESULTS"
    CHECKOUT = "CHECKOUT"
    UNKNOWN = "UNKNOWN"


class TemplateArchetype(BaseModel):
    template_id: str
    archetype_name: str
    dominant_page_type: StandardPageType
    structural_signature_hash: str
    member_urls: List[str] = Field(default_factory=list)
    sample_url: str = ""
    common_dom_elements: List[str] = Field(default_factory=list)


class PageClassifier:
    """
    Classifies a page into one of 14 standard enterprise categories.
    """

    @classmethod
    def classify(
        cls,
        url: str,
        title: str = "",
        h1_tags: Optional[List[str]] = None,
        schema_types: Optional[List[str]] = None,
        html_content: str = "",
    ) -> StandardPageType:
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.lower()
        title_lower = title.lower()
        schemas = [s.lower() for s in (schema_types or [])]

        # 1. Homepage
        if path in ("", "/", "/index.html", "/index.php"):
            return StandardPageType.HOMEPAGE

        # 2. Checkout & Cart
        if any(k in path for k in ("/cart", "/checkout", "/basket", "/order/pay")):
            return StandardPageType.CHECKOUT

        # 3. Search Results
        if any(k in path for k in ("/search", "/find")) or "q=" in parsed.query or "search=" in parsed.query:
            return StandardPageType.SEARCH_RESULTS

        # 4. Pricing
        if any(k in path for k in ("/pricing", "/plans", "/packages", "/cost", "/tiers")):
            return StandardPageType.PRICING
        if any(k in title_lower for k in ("pricing", "plans & pricing", "subscription plans")):
            return StandardPageType.PRICING

        # 5. Products (eCommerce / Catalog)
        if any(k in path for k in ("/products/", "/product/", "/item/", "/p/")):
            return StandardPageType.PRODUCT
        if "product" in schemas:
            return StandardPageType.PRODUCT

        # 6. Collections / Categories
        if any(k in path for k in ("/collections/", "/collection/", "/categories/", "/category/", "/c/")):
            return StandardPageType.COLLECTION
        if "collectionpage" in schemas or "itemlist" in schemas:
            return StandardPageType.COLLECTION

        # 7. Documentation / Guides / API
        if any(k in path for k in ("/docs", "/documentation", "/api-ref", "/developer", "/guide")):
            return StandardPageType.DOCUMENTATION

        # 8. FAQ
        if any(k in path for k in ("/faq", "/frequently-asked", "/questions", "/help-center")):
            return StandardPageType.FAQ
        if "faqpage" in schemas:
            return StandardPageType.FAQ

        # 9. Contact / Support
        if any(k in path for k in ("/contact", "/contact-us", "/reach-us", "/support", "/demo")):
            return StandardPageType.CONTACT

        # 10. About / Company
        if any(k in path for k in ("/about", "/about-us", "/who-we-are", "/our-story", "/company", "/team")):
            return StandardPageType.ABOUT_COMPANY

        # 11. Blog / Articles
        if any(k in path for k in ("/blog/", "/articles/", "/news/", "/post/", "/insights/")):
            return StandardPageType.BLOG_ARTICLE
        if any(s in schemas for s in ("article", "blogposting", "newsarticle")):
            return StandardPageType.BLOG_ARTICLE

        # 12. Services
        if any(k in path for k in ("/services/", "/service/", "/solutions/", "/offerings/")):
            return StandardPageType.SERVICE

        # 13. Landing Pages
        if any(k in path for k in ("/lp/", "/landing/", "/campaign/")):
            return StandardPageType.LANDING_PAGE

        return StandardPageType.UNKNOWN


class TemplateClusterEngine:
    """
    DOM Structural Fingerprinting & Template Archetype Discovery.
    """

    @classmethod
    def compute_dom_structural_hash(cls, html_content: str) -> str:
        """
        Extracts the structural tag skeleton of the page, ignoring variable text, attributes, and image sources.
        """
        if not html_content:
            return "empty_dom"

        # Extract landmark tags and major container hierarchies
        # Strip comments and scripts/styles
        cleaned = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)
        cleaned = re.sub(r"<(?:script|style)[^>]*?>.*?</(?:script|style)>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Extract sequence of structural HTML tag names
        tags = re.findall(r"<([a-zA-Z0-9]+)(?:\s+class=[\"']([^\"']+)[\"'])?[^>]*?>", cleaned)
        skeleton: List[str] = []
        for tag, classes in tags:
            tag_name = tag.lower()
            if tag_name in ("header", "nav", "main", "article", "section", "aside", "footer", "form", "table", "ul", "h1", "h2", "h3"):
                # Retain significant structural classes if any
                first_class = classes.split()[0] if classes else ""
                skeleton.append(f"{tag_name}.{first_class}" if first_class else tag_name)

        structural_string = ">".join(skeleton[:250])
        return hashlib.sha256(structural_string.encode("utf-8")).hexdigest()

    @classmethod
    def cluster_urls_into_templates(
        cls,
        page_records: List[Dict[str, Any]],
    ) -> List[TemplateArchetype]:
        """
        Groups inspected pages by structural hash into TemplateArchetypes.
        """
        clusters: Dict[str, List[Dict[str, Any]]] = {}

        for p in page_records:
            html = p.get("html") or p.get("raw_html") or ""
            sig = cls.compute_dom_structural_hash(html)
            clusters.setdefault(sig, []).append(p)

        archetypes: List[TemplateArchetype] = []
        for idx, (sig, members) in enumerate(clusters.items(), start=1):
            sample = members[0]
            dom_type = sample.get("page_type") or StandardPageType.UNKNOWN
            name = f"Template_{dom_type.value}_{idx:02d}"

            archetypes.append(TemplateArchetype(
                template_id=f"tpl_{sig[:10]}",
                archetype_name=name,
                dominant_page_type=dom_type,
                structural_signature_hash=sig,
                member_urls=[m.get("url", "") for m in members if m.get("url")],
                sample_url=sample.get("url", ""),
            ))

        return archetypes
