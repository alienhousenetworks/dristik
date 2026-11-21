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
            page_type = sample.get("page_type") or StandardPageType.UNKNOWN
            if not isinstance(page_type, StandardPageType):
                key = str(page_type or "").upper()
                page_type = StandardPageType[key] if key in StandardPageType.__members__ else StandardPageType.UNKNOWN
            name = f"Template_{page_type.value}_{idx:02d}"

            archetypes.append(TemplateArchetype(
                template_id=f"tpl_{sig[:10]}",
                archetype_name=name,
                dominant_page_type=page_type,
                structural_signature_hash=sig,
                member_urls=[m.get("url", "") for m in members if m.get("url")],
                sample_url=sample.get("url", ""),
            ))

        return archetypes


def _as_dict(page: Any) -> Dict[str, Any]:
    if isinstance(page, dict):
        return page
    if hasattr(page, "model_dump"):
        return page.model_dump()
    return {}


def _norm_url(url: str) -> str:
    parts = urllib.parse.urlsplit((url or "").strip())
    if not parts.scheme or not parts.netloc:
        return (url or "").strip().rstrip("/").lower()
    path = parts.path.rstrip("/") or "/"
    return f"{parts.netloc}{path}".lower()


def _path_prefix(url: str) -> str:
    path = urllib.parse.urlsplit(url or "").path.strip("/")
    segment = path.split("/", 1)[0] if path else ""
    return f"/{segment}/" if segment else ""


def _html_of(page: Dict[str, Any]) -> str:
    for key in ("raw_html", "html", "rendered_html", "rendered_dom"):
        value = page.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _rendered(page: Dict[str, Any]) -> bool:
    if str(page.get("render_mode") or "") in {"playwright_js", "firecrawl_js"}:
        return True
    return bool(page.get("rendered_html") or page.get("rendered_dom"))


def _tag_attr(html: str, tag: str, attr: str, marker: str) -> str:
    for element in re.findall(rf"<{tag}\b[^>]*>", html, flags=re.I):
        if re.search(marker, element, flags=re.I):
            found = re.search(rf"{attr}\s*=\s*['\"]([^'\"]+)['\"]", element, flags=re.I)
            if found:
                return found.group(1).strip()
    return ""


def _observe_html(url: str, html: str) -> Dict[str, Any]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
    h1_count = len(re.findall(r"<h1\b", html, flags=re.I))
    canonical = _tag_attr(html, "link", "href", r"rel\s*=\s*['\"]?canonical")
    robots = _tag_attr(html, "meta", "content", r"name\s*=\s*['\"]robots['\"]")
    return {
        "url": url,
        "title": title,
        "h1_count": h1_count,
        "canonical": canonical,
        "canonical_is_self": bool(canonical) and _norm_url(canonical) == _norm_url(url),
        "robots": robots,
        "has_viewport": bool(re.search(r"<meta\b[^>]*name\s*=\s*['\"]viewport['\"]", html, flags=re.I)),
        "verification_status": "VERIFIED",
        "measurement_method": "fetched_html",
    }


def _shared_keys(observations: List[Dict[str, Any]]) -> List[str]:
    if len(observations) < 2:
        return []
    keys = []
    if all(row["h1_count"] == 0 for row in observations):
        keys.append("missing_h1")
    if all(not row["title"] for row in observations):
        keys.append("missing_title")
    if all(not row["canonical"] for row in observations):
        keys.append("missing_canonical")
    if all(row["canonical"] and not row["canonical_is_self"] for row in observations):
        keys.append("canonical_not_self")
    return keys


def expansion_cap() -> int:
    import os
    raw = os.environ.get("DRISTIK_TEMPLATE_EXPANSION_CAP", "40")
    try:
        return max(0, int(raw))
    except ValueError:
        return 40


def build_page_template_intelligence(
    pages: List[Any],
    discovered_urls: Optional[List[str]] = None,
    excluded_urls: Optional[List[str]] = None,
    failed_urls: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Cluster fetched HTML and count coverage. Unfetched URLs stay unverified.

    A shared defect is recorded only for URLs whose HTML was read. Matching
    discovered URLs that were not fetched are expansion candidates, not failures.
    """
    records = [_as_dict(page) for page in (pages or [])]
    fetched: List[Dict[str, Any]] = []
    validations: List[Dict[str, Any]] = []
    for page in records:
        if page.get("crawl_source") == "unfetched_seed":
            continue
        url = str(page.get("url") or "")
        html = _html_of(page)
        if not url or not html:
            continue
        observed = _observe_html(url, html)
        observed["rendered"] = _rendered(page)
        observed["page_type"] = str(page.get("page_type") or PageClassifier.classify(url, title=observed["title"], html_content=html).value)
        validations.append(observed)
        fetched.append({**page, "url": url, "html": html, "page_type": page.get("page_type") or observed["page_type"]})

    archetypes = TemplateClusterEngine.cluster_urls_into_templates(fetched) if fetched else []
    by_url = {row["url"]: row for row in validations}
    defects: List[Dict[str, Any]] = []
    expansion: List[str] = []
    defective_prefixes: Set[str] = set()
    verified_defect_urls: Set[str] = set()
    for archetype in archetypes:
        members = [by_url[url] for url in archetype.member_urls if url in by_url]
        shared = _shared_keys(members)
        if not shared:
            continue
        affected = [row["url"] for row in members]
        verified_defect_urls.update(affected)
        defects.append({
            "template_id": archetype.template_id,
            "template_name": archetype.archetype_name,
            "defects": shared,
            "affected_urls": affected,
            "verification_status": "VERIFIED",
            "measurement_method": "fetched_html",
        })
        for url in affected:
            prefix = _path_prefix(url)
            if prefix:
                defective_prefixes.add(prefix)

    fetched_norms = {_norm_url(row["url"]) for row in validations}
    discovered = [url for url in dict.fromkeys(discovered_urls or []) if url]
    if not discovered:
        discovered = [row["url"] for row in validations]
    excluded = [url for url in dict.fromkeys(excluded_urls or []) if url]
    failed = [url for url in dict.fromkeys(failed_urls or []) if url]
    excluded_norms = {_norm_url(url) for url in excluded}
    not_fetched: List[str] = []
    for url in discovered:
        if _norm_url(url) in fetched_norms or _norm_url(url) in excluded_norms:
            continue
        not_fetched.append(url)
        prefix = _path_prefix(url)
        if prefix and prefix in defective_prefixes and url not in verified_defect_urls:
            expansion.append(url)

    rendered = sum(1 for row in validations if row["rendered"])
    crawled = len(validations)
    discovered_count = len(dict.fromkeys(discovered + [row["url"] for row in validations]))
    # shortcut: a browser render is the deep inspection; fetched HTML is page validation, not a deep audit
    deep = rendered
    full_site = bool(discovered_count and deep >= discovered_count and not not_fetched and not excluded)
    statement = (
        f"Discovered {discovered_count}. Crawled {crawled}. Rendered {rendered}. "
        f"Deeply analyzed {deep}. Excluded {len(excluded)}. Not fetched {len(not_fetched)}. "
        f"Failed {len(failed)}. "
    )
    if full_site:
        statement += "Every discovered URL was rendered in a browser. URLs that were never linked or listed are still unknown."
    else:
        statement += "This is not a full-site audit."
    if expansion:
        statement += f" {len(expansion)} unfetched URL(s) share a path prefix with a verified template defect and are not assumed broken."

    return {
        "urls_discovered": discovered_count,
        "urls_crawled": crawled,
        "urls_rendered": rendered,
        "urls_deeply_analyzed": deep,
        "urls_page_validated": crawled,
        "urls_excluded": len(excluded),
        "urls_not_fetched": len(not_fetched),
        "urls_failed": len(failed),
        "full_site_audit": full_site,
        "statement": statement,
        "templates": [item.model_dump() for item in archetypes],
        "template_defects": defects,
        "expansion_urls": expansion,
        "not_fetched_urls": not_fetched[:200],
        "page_validations": validations,
    }
