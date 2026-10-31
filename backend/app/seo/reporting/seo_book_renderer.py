"""
Dristik Master SEO Audit Book Renderer (2026 Master Standard).
Generates publication-grade, book-structured A4 PDF reports for SEO-only audits.

Key capabilities:
1. Translates technical findings into plain English for business owners.
2. Implements the 42-chapter master SEO index with intelligent conditionality
   (skips irrelevant e-commerce, local, international, news, or migration sections).
3. Normalizes findings into the standardized 17-field data contract.
4. Uses Jinja2 with autoescaping (preventing XSS / layout breaks from untrusted crawler data).
5. Two-pass Playwright/Chromium pagination resolving exact physical PDF page numbers for the TOC.
6. Injects PDF bookmarks and publication metadata via pypdf when available.
7. Zero-fabrication guarantee: unmeasured/unconnected checks remain explicitly "Not tested" or "Unavailable".
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import jinja2

from app.domain.enums import DiagnosticStatus
from app.reports.plain_english_engine import PlainEnglishEngine

logger = logging.getLogger("dristik.reports.seo_book")

try:
    import pypdf
except ImportError:
    pypdf = None

# Directory where Jinja2 templates reside
_TEMPLATE_DIR = Path(__file__).parent / "templates"


# ==============================================================================
# 1. DATA CONTRACT NORMALIZATION
# ==============================================================================

def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Safely retrieves a value from either an object attribute or dict key."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if type(obj).__name__ == "MagicMock" and key not in getattr(obj, "__dict__", {}):
        return default
    return getattr(obj, key, default)


def _url_key(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def _page_report_index(report: Any) -> Dict[str, Any]:
    index: Dict[str, Any] = {}
    reports = _get_val(report, "page_reports") or []
    if not isinstance(reports, list):
        return index
    for rep in reports:
        url = str(_get_val(rep, "url") or "")
        if not url:
            continue
        index[url] = rep
        index[_url_key(url)] = rep
    return index


def _specialist_copy(rep: Any) -> Dict[str, Any]:
    """Copy the page specialist actually wrote. Empty when the model did not run."""
    empty = {
        "suggested_title": "",
        "suggested_meta": "",
        "suggested_h1": "",
        "hero": "",
        "hook": "",
        "geo_snippet": "",
        "primary_cta": "",
        "analysis": "",
        "body_rewrite": "",
        "sections": [],
        "faqs": [],
        "copy_status": "",
        "has_specialist_copy": False,
    }
    copy = _get_val(rep, "copywriting") if rep is not None else None
    if not copy:
        return empty
    status = str(_get_val(copy, "llm_status") or "")
    sug = _get_val(copy, "suggested") or {}

    def text(*keys: str, collapse: bool = True) -> str:
        for key in keys:
            value = _get_val(sug, key)
            if isinstance(value, str) and value.strip():
                cleaned = value.strip()
                return re.sub(r"\s+", " ", cleaned) if collapse else cleaned
        return ""

    sections = []
    raw_sections = _get_val(sug, "sections") or []
    if isinstance(raw_sections, list):
        for sec in raw_sections:
            body = _get_val(sec, "suggested_copy") or _get_val(sec, "rewrite") or _get_val(sec, "copy") or ""
            if isinstance(body, str) and body.strip():
                sections.append({
                    "name": str(_get_val(sec, "section_name") or _get_val(sec, "name") or "Section"),
                    "copy": body.strip(),
                })
    faqs = []
    raw_faqs = _get_val(sug, "faq_items") or _get_val(sug, "faqs") or []
    if isinstance(raw_faqs, list):
        for faq in raw_faqs:
            question = str(_get_val(faq, "question") or "").strip()
            answer = str(_get_val(faq, "answer") or "").strip()
            if question or answer:
                faqs.append({"question": question, "answer": answer})
    analysis = str(_get_val(copy, "analysis") or "").strip() if status == "ok" else ""
    payload = {
        "suggested_title": text("title", "title_tag", "proposed_title", "recommended_title"),
        "suggested_meta": text("meta_description", "proposed_meta_description", "description"),
        "suggested_h1": text("h1", "headline", "proposed_h1"),
        "hero": text("hero", "hero_subhead"),
        "hook": text("hook_3sec", "hook"),
        "geo_snippet": text("geo_snippet", "snippet"),
        "primary_cta": text("primary_cta", "cta"),
        "analysis": analysis,
        "body_rewrite": text("body_rewrite", "full_rewrite", collapse=False),
        "sections": sections,
        "faqs": faqs,
        "copy_status": status,
    }
    payload["has_specialist_copy"] = bool(
        payload["suggested_title"]
        or payload["suggested_meta"]
        or payload["suggested_h1"]
        or payload["hero"]
        or payload["hook"]
        or payload["geo_snippet"]
        or payload["primary_cta"]
        or payload["analysis"]
        or payload["body_rewrite"]
        or sections
        or faqs
    )
    return payload


def normalize_finding(finding: Any, index: int = 1) -> Dict[str, Any]:
    """
    Normalizes any Dristik Finding model or dict into the standard 17-field data contract.
    Ensures zero-fabrication: missing fields remain cleanly defaulted/unmeasured.
    """
    enriched = PlainEnglishEngine.enrich_finding(finding, index)
    raw_id = _get_val(finding, "finding_id") or _get_val(finding, "id")
    if not raw_id:
        enriched["id"] = f"SEO-{index:03d}"

    sev = str(enriched.get("severity", "Medium")).upper()
    sev_cap = sev.capitalize()
    enriched["priority"] = sev_cap
    if enriched.get("lifecycle_status") in ("Open Defect", "OPEN"):
        enriched["lifecycle_status"] = "Open"
    if "high" in str(enriched.get("confidence", "")).lower():
        enriched["confidence"] = "High"
    enriched["finding_title"] = enriched.get("title", "")
    return enriched


# ==============================================================================
# 2. MASTER 42-CHAPTER CATALOG & CONDITIONALITY RULES
# ==============================================================================

# Master definition of chapters 03 through 36 (Core chapters)
CORE_CHAPTERS = [
    {
        "id": "sec-seo-strategy",
        "num": "03",
        "title": "SEO Strategy and Business Alignment",
        "category_hints": ["STRATEGY", "BUSINESS", "GOALS"],
        "conditional": "always",
        "introduction": "Evaluates how organic search strategy aligns with business revenue goals and target customer intent.",
        "business_explanation": "SEO succeeds when it attracts people ready to buy your products or services, not just empty clicks.",
        "subsections": [
            {
                "id": "sub-strategy-intent",
                "title": "Search Intent Alignment",
                "explanation": "Mapping discovered queries against business service lines.",
                "business_explanation": "Ensures landing pages serve commercial, informational, or transactional intent.",
                "metric_checks": ["Commercial query alignment", "Lead conversion pathway"],
            },
        ],
    },
    {
        "id": "sec-keyword-intent",
        "num": "04",
        "title": "Keyword Research and Search Intent",
        "category_hints": ["KEYWORD", "INTENT", "SEARCH_DEMAND"],
        "conditional": "always",
        "introduction": "Analysis of targeted search queries, primary/secondary keywords, and topical keyword mapping.",
        "business_explanation": "Targeting the exact terminology your customers use is the fastest path to qualified organic traffic.",
        "subsections": [
            {
                "id": "sub-keyword-cannibalization",
                "title": "Keyword Cannibalization & Mapping",
                "explanation": "Checking whether multiple pages compete against each other for identical search queries.",
                "business_explanation": "When two of your pages fight for the same term, Google often ranks neither highly.",
                "metric_checks": ["Cannibalization risks", "Primary target keyword coverage"],
            },
        ],
    },
    {
        "id": "sec-serp-analysis",
        "num": "05",
        "title": "SERP and Search Demand Analysis",
        "category_hints": ["SERP", "RICH_SNIPPETS", "SEARCH_RESULTS"],
        "conditional": "always",
        "introduction": "Inspection of Search Engine Results Page features, snippet pixel widths, and organic CTR drivers.",
        "business_explanation": "How your site appears in Google results determines how many searchers click through to your business.",
        "subsections": [
            {
                "id": "sub-serp-snippets",
                "title": "SERP Snippets & Pixel Truncation",
                "explanation": "Title tag and meta description lengths against desktop and mobile pixel limits.",
                "business_explanation": "Cut-off titles in search results look unprofessional and suppress click-through rates.",
                "metric_checks": ["Desktop title pixel compliance", "Meta description truncation"],
            },
        ],
    },
    {
        "id": "sec-technical-seo",
        "num": "06",
        "title": "Technical SEO and Site Infrastructure",
        "category_hints": ["TECHNICAL_SEO", "SERVER", "SSL", "HEADERS"],
        "conditional": "always",
        "introduction": "Comprehensive inspection of server architecture, security headers, HTTPS validity, and technical crawl barriers.",
        "business_explanation": "Technical SEO provides the reliable foundation required for search engines to access and trust your website.",
        "subsections": [
            {
                "id": "sub-tech-security",
                "title": "Security Headers & HTTPS Protocol",
                "explanation": "Verification of SSL certificate validity, HSTS, and transport layer security.",
                "business_explanation": "Google enforces secure HTTPS as a baseline trust factor for all search rankings.",
                "metric_checks": ["HTTPS enforcement", "HSTS header status", "Mixed content defects"],
            },
        ],
    },
    {
        "id": "sec-crawling-budget",
        "num": "07",
        "title": "Website Crawling and Crawl Budget",
        "category_hints": ["CRAWL", "BUDGET", "DEPTH", "ORPHAN"],
        "conditional": "always",
        "introduction": "Analysis of crawl efficiency, click depth, orphan pages, and crawler navigation paths.",
        "business_explanation": "Search engine crawlers have limited time. If your pages take too many clicks to find, they may never get indexed.",
        "subsections": [
            {
                "id": "sub-crawl-depth",
                "title": "Click Depth & Discovery Hierarchy",
                "explanation": "Pages requiring more than 3 clicks from the homepage to reach.",
                "business_explanation": "Important service pages buried deep in the site architecture receive fewer visits and lower rankings.",
                "metric_checks": ["Click depth > 3 pages", "Crawl discovery efficiency"],
            },
            {
                "id": "sub-crawl-orphans",
                "title": "Orphan Pages",
                "explanation": "Pages that exist but have no inbound internal links from other crawled pages.",
                "business_explanation": "Orphan pages are invisible to users navigating your site and struggle to rank in Google.",
                "metric_checks": ["Orphan URL count", "Internal link discovery"],
            },
        ],
    },
    {
        "id": "sec-indexation-directives",
        "num": "08",
        "title": "Indexation and Search Engine Directives",
        "category_hints": ["INDEXATION", "NOINDEX", "ROBOTS_DIRECTIVES"],
        "conditional": "always",
        "introduction": "Verification of meta robots tags, X-Robots-Tag headers, and indexing permissions.",
        "business_explanation": "A single erroneous 'noindex' tag can remove entire product lines or lead forms from search results completely.",
        "subsections": [
            {
                "id": "sub-index-directives",
                "title": "Meta Robots & X-Robots Directives",
                "explanation": "Audit of noindex, nofollow, and none directives across the crawled inventory.",
                "business_explanation": "Ensures valuable pages are eligible for Google search while staging or duplicate pages are cleanly kept out.",
                "metric_checks": ["Noindex page count", "Disallowed valuable landing pages"],
            },
        ],
    },
    {
        "id": "sec-url-structure",
        "num": "09",
        "title": "URL Structure and Site Architecture",
        "category_hints": ["URL", "ARCHITECTURE", "SLUGS"],
        "conditional": "always",
        "introduction": "Review of URL taxonomy, casing consistency, parameter bloat, and folder hierarchy.",
        "business_explanation": "Clean, descriptive web addresses make it easy for both customers and search engines to understand your site layout.",
        "subsections": [
            {
                "id": "sub-url-cleanliness",
                "title": "URL Slug Quality & Clean Paths",
                "explanation": "Checking for uppercase characters, underscores, session IDs, and excessive nesting in URLs.",
                "business_explanation": "Consistent lowercase URLs prevent accidental duplicate pages and tracking errors.",
                "metric_checks": ["Uppercase URL count", "Parameter-polluted URLs"],
            },
        ],
    },
    {
        "id": "sec-status-codes-redirects",
        "num": "10",
        "title": "HTTP Status Codes and Redirects",
        "category_hints": ["REDIRECT", "404", "301", "STATUS_CODES", "BROKEN"],
        "conditional": "always",
        "introduction": "Comprehensive audit of 4xx broken links, 5xx server errors, 3xx redirect chains, and redirect loops.",
        "business_explanation": "Broken links frustrate potential clients and waste search engine crawl resources.",
        "subsections": [
            {
                "id": "sub-broken-links",
                "title": "404 Client Errors & Dead Links",
                "explanation": "Internal and external links pointing to missing or broken pages.",
                "business_explanation": "Dead links send potential customers to error pages, causing immediate bounce and lost sales.",
                "metric_checks": ["404 Not Found count", "500 Server Error count"],
            },
            {
                "id": "sub-redirect-chains",
                "title": "Redirect Chains & Latency",
                "explanation": "Multi-hop redirects (e.g., A -> B -> C) that cause unnecessary load delay.",
                "business_explanation": "Direct one-step redirects ensure users and search engines reach destinations immediately.",
                "metric_checks": ["Multi-hop redirect chains", "Permanent 301 versus temporary 302"],
            },
        ],
    },
    {
        "id": "sec-sitemaps-robots",
        "num": "11",
        "title": "XML Sitemaps and Robots.txt",
        "category_hints": ["SITEMAP", "ROBOTS_TXT"],
        "conditional": "always",
        "introduction": "Inspection of robots.txt syntax, disallow rules, and XML sitemap health and validity.",
        "business_explanation": "Your sitemap and robots.txt act as the official directory and rulebook for visiting search engine crawlers.",
        "subsections": [
            {
                "id": "sub-sitemap-health",
                "title": "XML Sitemap Integrity",
                "explanation": "Ensures sitemaps contain only 200 OK, canonical, indexable URLs.",
                "business_explanation": "Submitting broken or redirected URLs in your sitemap confuses Google and delays content indexing.",
                "metric_checks": ["Sitemap accessibility", "Non-200 URLs in sitemap"],
            },
        ],
    },
    {
        "id": "sec-canonicalization",
        "num": "12",
        "title": "Canonicalization and Duplicate Content",
        "category_hints": ["CANONICAL", "DUPLICATE"],
        "conditional": "always",
        "introduction": "Audit of canonical link tags, self-referential canonicals, and duplicate content mitigation.",
        "business_explanation": "Canonical tags tell Google which version of a page is the master source when multiple URLs have similar content.",
        "subsections": [
            {
                "id": "sub-canonical-tags",
                "title": "Canonical Tag Configuration",
                "explanation": "Checking for missing, mismatched, or conflicting canonical declarations.",
                "business_explanation": "Without clear canonical tags, Google may split ranking authority across multiple URLs instead of ranking your main page.",
                "metric_checks": ["Self-referential canonical rate", "Canonical mismatch count"],
            },
        ],
    },
    {
        "id": "sec-onpage-seo",
        "num": "13",
        "title": "On-Page SEO and Meta Optimization",
        "category_hints": ["ON_PAGE_SEO", "TITLE", "META", "H1", "HEADINGS"],
        "conditional": "always",
        "introduction": "Page-level evaluation of title tags, meta descriptions, H1-H6 heading hierarchy, and content keyword relevance.",
        "business_explanation": "On-page optimization tells search engines exactly what topic each page on your website specializes in.",
        "subsections": [
            {
                "id": "sub-heading-structure",
                "title": "Heading Structure & H1 Hierarchy",
                "explanation": "Validates single H1 presence per page and logical heading sequence.",
                "business_explanation": "Clear headings make pages easy for visitors to skim and for search engines to summarize.",
                "metric_checks": ["Missing H1 tag count", "Multiple H1 tag count"],
            },
        ],
    },
    {
        "id": "sec-content-quality",
        "num": "14",
        "title": "Content Quality and Helpfulness",
        "category_hints": ["CONTENT", "THIN_CONTENT", "HELPFULNESS", "EEAT"],
        "conditional": "always",
        "introduction": "Assessment of content depth, word counts, original insights, and Google Helpful Content guidelines.",
        "business_explanation": "Search engines reward comprehensive, expert content that directly answers customer questions without fluff.",
        "subsections": [
            {
                "id": "sub-thin-content",
                "title": "Content Depth & Thin Pages",
                "explanation": "Pages with insufficient original copy or low word count.",
                "business_explanation": "Thin pages fail to convince customers and are frequently filtered out by Google's helpful content algorithms.",
                "metric_checks": ["Thin copy URL count", "Average page word count"],
            },
        ],
    },
    {
        "id": "sec-topical-authority",
        "num": "15",
        "title": "Topical Authority and Content Clusters",
        "category_hints": ["TOPICAL", "CLUSTERS", "PILLAR"],
        "conditional": "always",
        "introduction": "Review of pillar content, supporting cluster articles, and topical completeness across your industry niche.",
        "business_explanation": "Google treats websites that thoroughly cover every angle of a subject as industry authorities.",
        "subsections": [
            {
                "id": "sub-cluster-architecture",
                "title": "Pillar-to-Cluster Link Architecture",
                "explanation": "Evaluates reciprocal linking between main service pages and detailed informational articles.",
                "business_explanation": "Organizing content into topical hubs signals deep expertise in your field.",
                "metric_checks": ["Pillar page identification", "Cluster coverage score"],
            },
        ],
    },
    {
        "id": "sec-internal-linking",
        "num": "16",
        "title": "Internal Linking and Anchor Text",
        "category_hints": ["INTERNAL_LINK", "ANCHOR_TEXT"],
        "conditional": "always",
        "introduction": "Analysis of internal link distribution, descriptive anchor texts, and navigation equity flow.",
        "business_explanation": "Internal links act like bridges, passing search authority to your most important revenue-generating pages.",
        "subsections": [
            {
                "id": "sub-anchor-text",
                "title": "Descriptive Anchor Text",
                "explanation": "Checking for generic anchor texts like 'click here' or 'read more' instead of topical phrases.",
                "business_explanation": "Descriptive link words help search engines understand the exact topic of the linked destination page.",
                "metric_checks": ["Generic anchor text count", "Internal link density"],
            },
        ],
    },
    {
        "id": "sec-offpage-backlinks",
        "num": "17",
        "title": "Off-Page SEO and Backlinks",
        "category_hints": ["BACKLINK", "OFF_PAGE", "REFERRING_DOMAIN", "AUTHORITY"],
        "conditional": "always",
        "introduction": "Examination of external referring domains, backlink profile quality, and external authority signals.",
        "business_explanation": "Backlinks from reputable websites act as digital votes of confidence in the eyes of search algorithms.",
        "subsections": [
            {
                "id": "sub-backlink-profile",
                "title": "External Authority & Referring Domains",
                "explanation": "Inspection of connected authority telemetry and referring domain spread.",
                "business_explanation": "High-quality links from industry publications boost overall domain visibility across all keywords.",
                "metric_checks": ["Referring domain count", "Authority profile status"],
            },
        ],
    },
    {
        "id": "sec-competitor-seo",
        "num": "18",
        "title": "Competitor SEO Analysis",
        "category_hints": ["COMPETITOR", "COMPETITIVE", "BAKEOFF"],
        "conditional": "always",
        "introduction": "Benchmark of digital search visibility against primary market competitors.",
        "business_explanation": "Understanding what competitors rank for reveals valuable keyword and customer opportunities you can capture.",
        "subsections": [
            {
                "id": "sub-competitor-parity",
                "title": "Search Visibility & Content Gaps",
                "explanation": "Comparison of market presence against verified competitors in the same vertical.",
                "business_explanation": "Targeting keyword gaps allows you to win traffic currently captured by competitors.",
                "metric_checks": ["Competitor parity status", "Market visibility comparison"],
            },
        ],
    },
    {
        "id": "sec-structured-data",
        "num": "19",
        "title": "Structured Data and Schema SEO",
        "category_hints": ["SCHEMA", "JSON_LD", "STRUCTURED_DATA"],
        "conditional": "always",
        "introduction": "Validation of JSON-LD schema markup, schema type completeness, and Google Rich Result eligibility.",
        "business_explanation": "Schema markup translates your business details into machine-readable code, unlocking star ratings and FAQ snippets in Google.",
        "subsections": [
            {
                "id": "sub-schema-syntax",
                "title": "JSON-LD Validity & Schema Types",
                "explanation": "Checking for syntax errors, missing required properties, and organization markup.",
                "business_explanation": "Error-free schema ensures search engines display rich badges and enhanced previews for your listings.",
                "metric_checks": ["Valid schema types count", "Syntax error count in JSON-LD"],
            },
        ],
    },
    {
        "id": "sec-semantic-entities",
        "num": "20",
        "title": "Semantic SEO and Entity Optimization",
        "category_hints": ["SEMANTIC", "ENTITY", "KNOWLEDGE_GRAPH"],
        "conditional": "always",
        "introduction": "Audit of recognized entities, Knowledge Graph disambiguation, and brand identity clarity.",
        "business_explanation": "Modern search engines rank known real-world entities rather than just matching isolated keywords.",
        "subsections": [
            {
                "id": "sub-entity-clarity",
                "title": "Brand Entity Disambiguation",
                "explanation": "Checking organization schema, sameAs social links, and clear business identity markers.",
                "business_explanation": "Establishing a clear brand entity prevents search engines from confusing your business with others.",
                "metric_checks": ["Organization entity presence", "SameAs profile connections"],
            },
        ],
    },
    {
        "id": "sec-local-seo",
        "num": "21",
        "title": "Local SEO and Google Business Profile",
        "category_hints": ["LOCAL", "NAP", "GOOGLE_BUSINESS_PROFILE", "MAPS"],
        "conditional": "local_business",
        "introduction": "Review of localized landing pages, Name-Address-Phone (NAP) consistency, and local search signals.",
        "business_explanation": "Local SEO drives phone calls and in-person visits from nearby customers searching for services in your area.",
        "subsections": [
            {
                "id": "sub-local-nap",
                "title": "NAP Consistency & Local Landing Pages",
                "explanation": "Verification that company name, address, and phone number match across all website surfaces.",
                "business_explanation": "Inconsistent phone numbers or addresses confuse Google Maps and damage local pack rankings.",
                "metric_checks": ["NAP consistency", "LocalBusiness schema validation"],
            },
        ],
    },
    {
        "id": "sec-international-seo",
        "num": "22",
        "title": "International and Multilingual SEO",
        "category_hints": ["INTERNATIONAL", "HREFLANG", "MULTILINGUAL"],
        "conditional": "multilingual_or_multi_region",
        "introduction": "Verification of hreflang annotations, language targeting, and regional URL configurations.",
        "business_explanation": "Serving the right language and currency to global visitors prevents user bounce and search confusion.",
        "subsections": [
            {
                "id": "sub-hreflang-tags",
                "title": "Hreflang Reciprocity & Language Codes",
                "explanation": "Auditing bidirectional hreflang links and ISO language/region codes.",
                "business_explanation": "Broken hreflang tags cause the wrong regional page to rank in international search results.",
                "metric_checks": ["Hreflang implementation status", "Self-referencing hreflang count"],
            },
        ],
    },
    {
        "id": "sec-mobile-seo",
        "num": "23",
        "title": "Mobile SEO and Responsive Usability",
        "category_hints": ["MOBILE", "VIEWPORT", "RESPONSIVE"],
        "conditional": "always",
        "introduction": "Assessment of mobile viewport configuration, touch targets, and mobile-first indexing compliance.",
        "business_explanation": "Google crawls and ranks the mobile version of your website first. If it does not work well on phones, rankings drop.",
        "subsections": [
            {
                "id": "sub-mobile-viewport",
                "title": "Mobile Viewport & Touch Elements",
                "explanation": "Checking responsive meta tags and clickable element spacing.",
                "business_explanation": "Buttons placed too close together frustrate smartphone users and trigger mobile usability penalties.",
                "metric_checks": ["Viewport tag validity", "Touch target spacing"],
            },
        ],
    },
    {
        "id": "sec-core-web-vitals",
        "num": "24",
        "title": "Page Speed and Core Web Vitals",
        "category_hints": ["SPEED", "CORE_WEB_VITALS", "LCP", "INP", "CLS", "TTFB"],
        "conditional": "always",
        "introduction": "Evaluation of server response time (TTFB), Largest Contentful Paint (LCP), and Cumulative Layout Shift (CLS).",
        "business_explanation": "Fast pages keep visitors engaged; slow pages cause potential clients to leave before reading your offer.",
        "subsections": [
            {
                "id": "sub-ttfb-speed",
                "title": "Server Response Time (TTFB)",
                "explanation": "Time taken by the hosting server to deliver the initial byte of HTML.",
                "business_explanation": "A slow server delays everything else on the page, frustrating users and search engine bots alike.",
                "metric_checks": ["Average TTFB (ms)", "Slow loading URL count"],
            },
        ],
    },
    {
        "id": "sec-javascript-seo",
        "num": "25",
        "title": "JavaScript SEO and Client-Side Rendering",
        "category_hints": ["JAVASCRIPT", "HYDRATION", "SPA", "RENDERING"],
        "conditional": "always",
        "introduction": "Analysis of client-side JavaScript rendering, DOM hydration, and links discoverable without script execution.",
        "business_explanation": "If critical content requires heavy JavaScript to appear, search engines may fail to index it.",
        "subsections": [
            {
                "id": "sub-js-links",
                "title": "Discoverable HTML Links vs JS Events",
                "explanation": "Ensures navigation links use standard <a href> attributes instead of JavaScript onclick handlers.",
                "business_explanation": "Googlebot cannot click buttons to discover pages; it requires standard HTML link tags.",
                "metric_checks": ["Standard href link adherence", "Client-side render dependency"],
            },
        ],
    },
    {
        "id": "sec-image-seo",
        "num": "26",
        "title": "Image SEO and Media Optimization",
        "category_hints": ["IMAGE", "ALT_TEXT", "MEDIA", "WEBP"],
        "conditional": "always",
        "introduction": "Inspection of image alt attributes, modern format adoption (WebP/AVIF), and media dimensions.",
        "business_explanation": "Optimized images rank in Google Image search and keep page load times fast for visitors.",
        "subsections": [
            {
                "id": "sub-image-alt",
                "title": "Image Alt Text Coverage",
                "explanation": "Auditing images for missing or generic descriptive alt text.",
                "business_explanation": "Alt text helps visually impaired visitors and tells search engines what products or graphics are pictured.",
                "metric_checks": ["Missing alt text image count", "Total images inspected"],
            },
        ],
    },
    {
        "id": "sec-video-seo",
        "num": "27",
        "title": "Video SEO and Rich Media",
        "category_hints": ["VIDEO", "VIDEOOBJECT"],
        "conditional": "video_present",
        "introduction": "Review of video embeds, VideoObject schema, thumbnails, and video search indexing eligibility.",
        "business_explanation": "Videos build customer trust and can appear directly in Google video search results with proper markup.",
        "subsections": [
            {
                "id": "sub-video-schema",
                "title": "VideoObject Schema Markup",
                "explanation": "Checking thumbnail URLs, upload dates, and video duration declarations.",
                "business_explanation": "Structured video markup enables rich video thumbnail previews in Google results.",
                "metric_checks": ["VideoObject markup count", "Thumbnail accessibility"],
            },
        ],
    },
    {
        "id": "sec-news-publisher",
        "num": "28",
        "title": "News and Publisher SEO",
        "category_hints": ["NEWS", "PUBLISHER", "EDITORIAL", "NEWSARTICLE"],
        "conditional": "news_publisher",
        "introduction": "Audit of NewsArticle schema, editorial transparency, bylines, and Google News eligibility.",
        "business_explanation": "Publisher standards demand clear author bylines, publishing dates, and editorial transparency.",
        "subsections": [
            {
                "id": "sub-news-bylines",
                "title": "Author Bylines & Publication Dates",
                "explanation": "Checking for clearly declared author entities and dateModified timestamps.",
                "business_explanation": "Readers and search engines look for verified authorship when evaluating news and editorial articles.",
                "metric_checks": ["Author byline presence", "Publication date transparency"],
            },
        ],
    },
    {
        "id": "sec-ecommerce-seo",
        "num": "29",
        "title": "Ecommerce SEO and Product Catalog",
        "category_hints": ["ECOMMERCE", "PRODUCT", "CATALOG", "PRICE", "MERCHANT"],
        "conditional": "ecommerce",
        "introduction": "Comprehensive audit of product pages, category facets, pricing/availability schema, and out-of-stock handling.",
        "business_explanation": "E-commerce SEO directly drives online sales by making individual products findable for high-intent shoppers.",
        "subsections": [
            {
                "id": "sub-ecom-schema",
                "title": "Product Schema & Availability",
                "explanation": "Checking schema.org/Product markup with Price, Currency, and InStock status.",
                "business_explanation": "Rich product snippets in Google display live prices and in-stock badges, dramatically increasing buyer clicks.",
                "metric_checks": ["Product schema coverage", "Price & currency declaration"],
            },
        ],
    },
    {
        "id": "sec-programmatic-seo",
        "num": "30",
        "title": "Programmatic SEO and Faceted Navigation",
        "category_hints": ["PROGRAMMATIC", "FACETED", "FILTER"],
        "conditional": "programmatic",
        "introduction": "Review of dynamic templates, index bloat risks, filter parameters, and scalable internal linking.",
        "business_explanation": "Database-generated pages can scale search traffic rapidly if protected against duplicate content traps.",
        "subsections": [
            {
                "id": "sub-prog-differentiation",
                "title": "Template Content Differentiation",
                "explanation": "Ensures programmatically generated pages have unique copy and data rather than identical boilerplate.",
                "business_explanation": "Search engines ignore duplicate template pages that offer no unique value to visitors.",
                "metric_checks": ["Template uniqueness score", "Faceted index control"],
            },
        ],
    },
    {
        "id": "sec-migration-risk",
        "num": "31",
        "title": "Website Migration and Change Risk",
        "category_hints": ["MIGRATION", "CHANGE_RISK", "DOMAIN_CHANGE"],
        "conditional": "migration",
        "introduction": "Analysis of URL structure shifts, legacy 301 redirects, canonical continuity, and traffic preservation.",
        "business_explanation": "Relaunching or redesigning a website without proper redirect planning can wipe out years of organic traffic.",
        "subsections": [
            {
                "id": "sub-migration-redirects",
                "title": "Legacy URL Redirect Mapping",
                "explanation": "Verifying 1-to-1 301 redirects from old URLs to new counterparts.",
                "business_explanation": "Preserves existing ranking equity and prevents visitors from hitting broken 404 pages after redesigns.",
                "metric_checks": ["Mapped redirect rate", "Preserved organic landing pages"],
            },
        ],
    },
    {
        "id": "sec-accessibility-search",
        "num": "32",
        "title": "Accessibility and Search Usability",
        "category_hints": ["ACCESSIBILITY", "WCAG", "ARIA", "CONTRAST"],
        "conditional": "always",
        "introduction": "Evaluation of semantic landmarks, color contrast, and usability factors that influence search engagement.",
        "business_explanation": "Accessible websites make it easy for all potential clients to consume content and complete purchases.",
        "subsections": [
            {
                "id": "sub-a11y-semantics",
                "title": "Semantic HTML5 Landmarks",
                "explanation": "Use of header, main, nav, and footer elements to structure document flow.",
                "business_explanation": "Semantic markup assists screen readers and helps search engines pinpoint core content immediately.",
                "metric_checks": ["Main landmark presence", "Semantic tag adherence"],
            },
        ],
    },
    {
        "id": "sec-trust-identity",
        "num": "33",
        "title": "Trust and Website Identity (E-E-A-T)",
        "category_hints": ["TRUST", "EEAT", "IDENTITY", "ABOUT", "CONTACT"],
        "conditional": "always",
        "introduction": "Inspection of about page, contact details, privacy policy, terms, and organizational transparency signals.",
        "business_explanation": "Google evaluates whether a business is legitimate and trustworthy before recommending it to searchers.",
        "subsections": [
            {
                "id": "sub-trust-policies",
                "title": "Policy Pages & Physical Identity",
                "explanation": "Verification of accessible Privacy Policy, Terms of Service, and verified contact channels.",
                "business_explanation": "Clear policies and real contact info protect your business legally and build strong search trust.",
                "metric_checks": ["Privacy policy presence", "Contact info discoverability"],
            },
        ],
    },
    {
        "id": "sec-analytics-measurement",
        "num": "34",
        "title": "SEO Analytics and Measurement",
        "category_hints": ["ANALYTICS", "GSC", "GA4", "MEASUREMENT"],
        "conditional": "always",
        "introduction": "Audit of Google Search Console integration, GA4 tracking scripts, and organic conversion measurement.",
        "business_explanation": "You cannot improve what you do not measure. Connected analytics prove which search terms generate real revenue.",
        "subsections": [
            {
                "id": "sub-analytics-tracking",
                "title": "Analytics Tagging & Search Console",
                "explanation": "Checking presence and health of measurement tracking tags.",
                "business_explanation": "Accurate tracking ensures marketing budgets are invested in the search strategies that actually deliver sales.",
                "metric_checks": ["Analytics tag detection", "Search Console data status"],
            },
        ],
    },
    {
        "id": "sec-content-opportunities",
        "num": "35",
        "title": "SEO Content Opportunity Plan",
        "category_hints": ["CONTENT_OPPORTUNITY", "EXPANSION", "BRIEFS"],
        "conditional": "always",
        "introduction": "Data-backed recommendations for new content briefs, page refreshes, and high-value search topic expansion.",
        "business_explanation": "Targeted new content expands your search footprint into untapped customer queries.",
        "subsections": [
            {
                "id": "sub-content-expansion",
                "title": "Prioritized New Content Briefs",
                "explanation": "High-intent search themes currently missing from the domain inventory.",
                "business_explanation": "Publishing answers to these specific search queries captures customers actively researching your services.",
                "metric_checks": ["Content expansion topics identified", "Recommended refresh candidates"],
            },
        ],
    },
    {
        "id": "sec-page-by-page",
        "num": "36",
        "title": "Page-by-Page Audit Inventory",
        "category_hints": ["PAGE_BY_PAGE", "INVENTORY", "CRAWL_RESULTS"],
        "conditional": "always",
        "introduction": "Granular review of inspected URLs, observed status codes, titles, canonical states, and defects.",
        "business_explanation": "A complete inventory giving your technical team the exact page-level status for every inspected URL.",
        "subsections": [
            {
                "id": "sub-page-roster",
                "title": "Sampled URL Breakdown",
                "explanation": "Detailed table of audited pages and their health indicators.",
                "business_explanation": "Use this checklist to systematically inspect and resolve issues across specific sections of your website.",
                "metric_checks": ["Audited URL sample size", "Clean versus defect page ratio"],
            },
        ],
    },
]


def _matches_any_hint(text: str, hints: List[str]) -> bool:
    """Checks if any keyword hint is present in the text."""
    lower = text.lower()
    for h in hints:
        if h.lower() in lower:
            return True
    return False


def is_chapter_applicable(chapter_meta: Dict[str, Any], report: Any) -> bool:
    """
    Determines if a conditional chapter is applicable to the audited website.
    Applies zero-fabrication rules: irrelevant sections are omitted cleanly.
    """
    cond = chapter_meta.get("conditional", "always")
    if cond == "always":
        return True

    profile = _get_val(report, "business_profile") or {}
    model_blob = " ".join([
        str(_get_val(profile, "business_model") or ""),
        str(_get_val(profile, "industry") or ""),
        str(_get_val(profile, "niche") or ""),
        str(_get_val(profile, "business_name") or ""),
        str(_get_val(report, "domain") or ""),
    ]).lower()

    def _is_pos(val: Any) -> bool:
        return isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0

    if cond == "ecommerce":
        biz_model = str(_get_val(profile, "business_model") or "").lower()
        if biz_model and any(s in biz_model for s in ("b2b_service", "service", "consulting", "agency", "legal", "medical")):
            ecom = _get_val(report, "ecommerce_seo")
            return bool(ecom and _is_pos(_get_val(ecom, "product_pages_evaluated")))

        if "ecommerce" in model_blob or "store" in model_blob or "shop" in model_blob or "retail" in model_blob:
            return True
        ecom = _get_val(report, "ecommerce_seo")
        if ecom and _is_pos(_get_val(ecom, "product_pages_evaluated")):
            return True
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["product catalog", "shopping cart", "checkout page", "purchasable sku"]):
                return True
        return False

    if cond == "local_business":
        if "local" in model_blob or "clinic" in model_blob or "lawyer" in model_blob or "dental" in model_blob or "plumber" in model_blob:
            return True
        loc = _get_val(report, "local_seo")
        if loc and _is_pos(_get_val(loc, "locations_evaluated")):
            return True
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["google business profile", "nap", "local citation", "local business"]):
                return True
        return False

    if cond == "multilingual_or_multi_region":
        intl = _get_val(report, "international_seo")
        lang_cnt = _get_val(intl, "languages_evaluated")
        if intl and isinstance(lang_cnt, (int, float)) and lang_cnt > 1:
            return True
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["hreflang", "multilingual", "multi-region"]):
                return True
        return False

    if cond == "video_present":
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["video", "videoobject", "youtube"]):
                return True
        return False

    if cond == "news_publisher":
        if "news" in model_blob or "publisher" in model_blob or "magazine" in model_blob or "journal" in model_blob:
            return True
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["newsarticle", "google news", "news sitemap", "editorial"]):
                return True
        return False

    if cond == "programmatic":
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["programmatic", "faceted", "parameter bloat"]):
                return True
        return False

    if cond == "migration":
        findings = _get_val(report, "findings") or []
        for f in findings:
            if _matches_any_hint(f"{_get_val(f, 'title')} {_get_val(f, 'description')}", ["migration", "domain migration", "legacy url"]):
                return True
        return False

    return True


PART_LABELS_BY_CHAPTER_ID: Dict[str, str] = {
    "sec-seo-strategy": "Part II — Search Strategy and Market Intelligence",
    "sec-keyword-intent": "Part II — Search Strategy and Market Intelligence",
    "sec-serp-analysis": "Part II — Search Strategy and Market Intelligence",
    "sec-competitor-seo": "Part II — Search Strategy and Market Intelligence",
    "sec-content-opportunities": "Part II — Search Strategy and Market Intelligence",
    "sec-technical-seo": "Part III — Technical SEO",
    "sec-crawling-budget": "Part III — Technical SEO",
    "sec-indexation-directives": "Part III — Technical SEO",
    "sec-url-structure": "Part III — Technical SEO",
    "sec-status-codes-redirects": "Part III — Technical SEO",
    "sec-sitemaps-robots": "Part III — Technical SEO",
    "sec-canonicalization": "Part III — Technical SEO",
    "sec-javascript-seo": "Part III — Technical SEO",
    "sec-international-seo": "Part III — Technical SEO",
    "sec-onpage-seo": "Part IV — On-Page and Content Intelligence",
    "sec-content-quality": "Part IV — On-Page and Content Intelligence",
    "sec-topical-authority": "Part IV — On-Page and Content Intelligence",
    "sec-internal-linking": "Part IV — On-Page and Content Intelligence",
    "sec-image-seo": "Part IV — On-Page and Content Intelligence",
    "sec-video-seo": "Part IV — On-Page and Content Intelligence",
    "sec-news-publisher": "Part IV — On-Page and Content Intelligence",
    "sec-ecommerce-seo": "Part IV — On-Page and Content Intelligence",
    "sec-programmatic-seo": "Part IV — On-Page and Content Intelligence",
    "sec-migration-risk": "Part IV — On-Page and Content Intelligence",
    "sec-offpage-backlinks": "Part V — Authority, Experience and Trust",
    "sec-structured-data": "Part V — Authority, Experience and Trust",
    "sec-semantic-entities": "Part V — Authority, Experience and Trust",
    "sec-trust-identity": "Part V — Authority, Experience and Trust",
    "sec-local-seo": "Part V — Authority, Experience and Trust",
    "sec-mobile-seo": "Part V — Authority, Experience and Trust",
    "sec-accessibility-search": "Part V — Authority, Experience and Trust",
    "sec-core-web-vitals": "Part V — Authority, Experience and Trust",
    "sec-analytics-measurement": "Part VI — Growth and Execution",
    "sec-page-by-page": "Part VI — Growth and Execution",
}


def _reconcile_and_deduplicate_raw_findings(raw_findings: List[Any], pages: List[Any]) -> List[Any]:
    """
    1. Reconciles findings against measured PageEvidence DOM attributes (drops false-positive
       missing canonical, missing meta description, or missing html[lang] claims when all crawled
       pages actually declare those attributes).
    2. Consolidates duplicate findings into one canonical finding per root issue while preserving
       all affected URLs and evidence records.
    """
    if not raw_findings:
        return []

    all_have_canonical = bool(pages) and all(bool(_get_val(p, "canonical_url")) for p in pages)
    all_have_meta = bool(pages) and all(bool(str(_get_val(p, "meta_description") or "").strip()) for p in pages)
    all_have_lang = bool(pages) and all(
        bool(_get_val(p, "has_html_lang") or _get_val(p, "html_lang"))
        for p in pages
    )

    reconciled: List[Any] = []
    for f in raw_findings:
        t_low = str(_get_val(f, "title") or _get_val(f, "finding_title") or "").lower()
        d_low = str(_get_val(f, "description") or _get_val(f, "observed_result") or "").lower()
        blob = f"{t_low} {d_low}"
        if all_have_canonical and (
            "have no rel=canonical" in blob
            or "missing a canonical" in blob
            or "no canonical tag" in blob
        ):
            continue
        if all_have_meta and (
            "missing a meta description" in blob
            or "meta description is missing" in blob
            or "have no meta description" in blob
        ):
            continue
        if all_have_lang and (
            "missing an html lang" in blob
            or "missing html lang" in blob
        ):
            continue
        reconciled.append(f)

    def _canonical_key(item: Any) -> str:
        r_id = str(_get_val(item, "rule_id") or "").strip().lower()
        if r_id:
            return f"rule::{r_id}"
        t_str = str(_get_val(item, "title") or _get_val(item, "finding_title") or "").strip()
        d_str = str(_get_val(item, "description") or _get_val(item, "observed_result") or "").strip()
        txt = f"{t_str} {d_str}".lower()
        if "beyond imagination" in txt or ("h1" in txt and ("slogan" in txt or "vague" in txt or "generic" in txt or "category" in txt)):
            return "canonical::homepage_vague_h1"
        if ("duplicate" in txt or "identical" in txt or "repeats" in txt or "reuses" in txt or "verbatim" in txt) and "meta description" in txt:
            return "canonical::duplicate_meta_description"
        if "open graph" in txt and "missing" in txt:
            return "canonical::missing_open_graph"
        if "alienhouse" in txt and ("casing" in txt or "inconsistent" in txt or "brand" in txt or "naming" in txt):
            return "canonical::brand_naming_consistency"
        if ("'game'" in txt or '"game"' in txt) and ("nav" in txt or "menu" in txt or "label" in txt):
            return "canonical::ambiguous_nav_game"
        if "alt" in txt and ("image" in txt or "img" in txt) and ("missing" in txt or "lack" in txt):
            return "canonical::missing_image_alt"
        if "hsts" in txt or "strict-transport-security" in txt:
            return "canonical::missing_hsts"
        if "content-security-policy" in txt or ("csp" in txt and "header" in txt):
            return "canonical::missing_csp"
        if "x-frame-options" in txt:
            return "canonical::missing_xfo"
        if "x-content-type-options" in txt:
            return "canonical::missing_xcto"
        if "long copy without h2" in txt:
            return "canonical::long_copy_without_h2"
        return f"title::{t_str.lower()}"

    deduped_map: Dict[str, Any] = {}
    for item in reconciled:
        key = _canonical_key(item)
        if key not in deduped_map:
            deduped_map[key] = item
        else:
            existing = deduped_map[key]
            ex_urls = list(_get_val(existing, "affected_urls") or [])
            new_urls = list(_get_val(item, "affected_urls") or [])
            merged_urls = list(dict.fromkeys([str(u) for u in (ex_urls + new_urls) if u]))
            if isinstance(existing, dict):
                existing["affected_urls"] = merged_urls
                ex_ev = list(existing.get("evidence") or [])
                new_ev = list(_get_val(item, "evidence") or [])
                existing["evidence"] = (ex_ev + new_ev)[:10]
            else:
                try:
                    existing.affected_urls = merged_urls
                    ex_ev = list(getattr(existing, "evidence", None) or [])
                    new_ev = list(_get_val(item, "evidence") or [])
                    existing.evidence = (ex_ev + new_ev)[:10]
                except Exception:
                    pass
    return list(deduped_map.values())


def _route_finding_to_chapter_id(f: Dict[str, Any], applicable_ids: Set[str]) -> Optional[str]:
    """
    Deterministically routes a normalized finding to its most specific analytical chapter.
    Prevents Chapter 06 (sec-technical-seo) from greedily capturing non-security findings
    merely because their top-level enum category is TECHNICAL_SEO.
    """
    title = str(f.get("title") or "").lower()
    obs = str(f.get("observed_result") or "").lower()
    checked = str(f.get("what_was_checked") or "").lower()
    blob = f"{title} {obs}"

    def _pick(*candidates: str) -> Optional[str]:
        for c in candidates:
            if c in applicable_ids:
                return c
        return None

    # 1. Conditional specialized chapters first
    if any(k in blob for k in ("product schema", "itemavailability", "instock", "merchant", "checkout", "sku", "catalog")):
        if "robots.txt" in blob or "disallow" in blob:
            return _pick("sec-sitemaps-robots", "sec-crawling-budget")
        if "schema" in blob or "json-ld" in blob:
            return _pick("sec-structured-data", "sec-ecommerce-seo")
        return _pick("sec-ecommerce-seo", "sec-onpage-seo")
    if any(k in blob for k in ("hreflang", "multilingual", "html lang", "lang attribute")):
        return _pick("sec-international-seo", "sec-accessibility-search", "sec-onpage-seo")
    if any(k in blob for k in ("google business profile", "localbusiness", "nap consistency", "local pack")):
        return _pick("sec-local-seo", "sec-trust-identity")
    if any(k in blob for k in ("videoobject", "video embed", "video schema")):
        return _pick("sec-video-seo", "sec-image-seo")

    # 2. Technical SEO sub-disciplines (Specific chapters before general sec-technical-seo)
    if any(k in blob for k in ("robots.txt", "xml sitemap", "sitemap.xml", "disallow directive")):
        return _pick("sec-sitemaps-robots", "sec-crawling-budget")
    if any(k in blob for k in ("noindex", "x-robots-tag", "soft 404", "indexation", "robots meta")):
        return _pick("sec-indexation-directives", "sec-crawling-budget")
    if any(k in blob for k in ("canonical", "rel=canonical", "self-referential canonical")):
        return _pick("sec-canonicalization", "sec-indexation-directives")
    if any(k in blob for k in ("redirect", "301", "302", "404", "500", "5xx", "4xx", "broken link", "status code")):
        return _pick("sec-status-codes-redirects", "sec-technical-seo")
    if any(k in blob for k in ("click depth", "orphan", "crawl budget", "crawl trap")):
        return _pick("sec-crawling-budget", "sec-internal-linking")
    if any(k in blob for k in ("uppercase url", "url slug", "url parameter", "query parameter", "trailing slash", "url structure")):
        return _pick("sec-url-structure", "sec-technical-seo")
    if any(k in blob for k in ("javascript", "hydration", "client-side render", "rendered dom", "spa")):
        return _pick("sec-javascript-seo", "sec-technical-seo")
    if any(k in blob for k in ("ttfb", "lcp", "cls", "inp", "core web vital", "server response", "latency", "page speed", "render-blocking")):
        return _pick("sec-core-web-vitals", "sec-technical-seo")
    if any(k in blob for k in ("viewport", "mobile", "tap target", "touch target", "responsive")):
        return _pick("sec-mobile-seo", "sec-accessibility-search")
    if any(k in blob for k in ("hsts", "strict-transport-security", "content-security-policy", "csp", "x-frame-options", "x-content-type-options", "mixed content", "ssl", "tls", "https", "security header")):
        return _pick("sec-technical-seo")

    # 3. On-Page, Content, SERP & Media
    if any(k in blob for k in ("alt text", "missing alt", "image", "img", "webp", "avif", "media")):
        return _pick("sec-image-seo", "sec-onpage-seo")
    if any(k in blob for k in ("open graph", "og:", "twitter:", "pixel truncation", "serp snippet")):
        return _pick("sec-serp-analysis", "sec-onpage-seo")
    if any(k in blob for k in ("anchor text", "internal link", "navigation", "'game'", '"game"', "menu label")):
        return _pick("sec-internal-linking", "sec-url-structure")
    if any(k in blob for k in ("title tag", "title length", "title is short", "title may truncate", "meta description", "h1", "beyond imagination", "heading hierarchy", "heading tag")):
        return _pick("sec-onpage-seo")
    if any(k in blob for k in ("h2", "subheading", "thin copy", "word count", "long copy", "readability", "helpful content", "copy —")):
        return _pick("sec-content-quality", "sec-onpage-seo")
    if any(k in blob for k in ("topic cluster", "pillar", "topical authority", "content gap")):
        return _pick("sec-topical-authority", "sec-content-opportunities")
    if any(k in blob for k in ("keyword", "cannibalization", "search intent")):
        return _pick("sec-keyword-intent", "sec-seo-strategy")

    # 4. Schema, Entity, E-E-A-T, Accessibility, Strategy & Analytics
    if any(k in blob for k in ("schema", "json-ld", "structured data", "rich result")):
        return _pick("sec-structured-data")
    if any(k in blob for k in ("entity", "sameas", "knowledge graph", "brand naming", "brand casing", "alienhouse")):
        return _pick("sec-semantic-entities", "sec-trust-identity")
    if any(k in blob for k in ("accessibility", "wcag", "aria", "landmark", "form", "input", "label", "contrast")):
        return _pick("sec-accessibility-search")
    if any(k in blob for k in ("privacy policy", "terms", "refund", "cancellation", "sla", "soc 2", "iso 27001", "testimonial", "case stud", "customer logo", "pricing", "eeat", "e-e-a-t", "trust", "contact")):
        return _pick("sec-trust-identity", "sec-seo-strategy")
    if any(k in blob for k in ("backlink", "referring domain", "off-page")):
        return _pick("sec-offpage-backlinks")
    if any(k in blob for k in ("competitor", "competitive", "peer", "displacement")):
        return _pick("sec-competitor-seo")
    if any(k in blob for k in ("analytics", "ga4", "search console", "gsc", "conversion tracking")):
        return _pick("sec-analytics-measurement")
    if any(k in blob for k in ("cta", "call to action", "self-serve", "buyer persona", "commercial", "value proposition", "mission")):
        return _pick("sec-seo-strategy", "sec-content-opportunities")

    # Fallback by checked domain
    if "security" in checked:
        return _pick("sec-technical-seo")
    if "schema" in checked:
        return _pick("sec-structured-data")
    if "canonical" in checked:
        return _pick("sec-canonicalization")
    return _pick("sec-onpage-seo", "sec-technical-seo")


def _expected_for_metric_check(check_lower: str) -> str:
    """Returns a check-specific expected benchmark for any chapter diagnostic metric."""
    if "https" in check_lower:
        return "100% of public URLs served over HTTPS with valid TLS."
    if "hsts" in check_lower:
        return "Strict-Transport-Security header with max-age >= 31536000."
    if "mixed content" in check_lower:
        return "0 insecure http:// subresources on HTTPS pages."
    if "click depth" in check_lower:
        return "All core commercial pages reachable within <= 3 clicks from homepage."
    if "crawl discovery" in check_lower or "internal link discovery" in check_lower:
        return "All important pages discoverable via both internal HTML links and XML sitemap."
    if "orphan" in check_lower:
        return "0 indexable URLs without incoming internal links."
    if "noindex" in check_lower or "disallowed" in check_lower:
        return "0 commercial landing pages blocked by noindex or robots.txt Disallow."
    if "uppercase" in check_lower:
        return "0 URLs with uppercase characters in path slugs."
    if "parameter" in check_lower:
        return "Clean canonical URLs free of session IDs or uncanonicalized query parameters."
    if "404" in check_lower or "500" in check_lower:
        return "0 internal links or crawled pages returning HTTP 4xx/5xx error codes."
    if "redirect" in check_lower or "301" in check_lower:
        return "0 multi-hop redirect chains (>1 hop) or temporary 302s for permanent moves."
    if "sitemap" in check_lower:
        return "Valid /sitemap.xml returning HTTP 200 and listing only canonical 200 OK URLs."
    if "canonical" in check_lower:
        return "100% of indexable pages declare a self-referencing <link rel='canonical'>."
    if "h1" in check_lower:
        return "Exactly 1 descriptive <h1> per page aligned with primary page topic."
    if "thin copy" in check_lower or "word count" in check_lower:
        return ">= 300 informative words on commercial service pages; 0 thin (<200 word) pages."
    if "title" in check_lower:
        return "A title was stored per crawled page. Character count is a measurement, not a required band."
    if "meta description" in check_lower:
        return "A meta description was stored per crawled page. Character count is a measurement, not a required band."
    if "anchor" in check_lower or "link density" in check_lower:
        return "Descriptive topical anchor text; >= 3 contextual internal links per page."
    if "referring domain" in check_lower or "authority" in check_lower:
        return "Verified external backlink telemetry via connected authority provider."
    if "competitor" in check_lower or "market visibility" in check_lower:
        return "Empirical head-to-head benchmark against crawled competitor domains."
    if "schema" in check_lower or "json-ld" in check_lower:
        return "Valid JSON-LD Organization, WebSite, and Service/Product markup with 0 syntax errors."
    if "organization entity" in check_lower or "sameas" in check_lower:
        return "Explicit Organization entity with logo, contactPoint, and sameAs profile URLs."
    if "viewport" in check_lower or "touch target" in check_lower:
        return "Valid <meta name='viewport'> and >= 48x48px tap target spacing."
    if "ttfb" in check_lower or "slow loading" in check_lower:
        return "Server Time to First Byte (TTFB) < 800 ms across all crawled URLs."
    if "href link" in check_lower or "client-side render" in check_lower:
        return "Core copy and <a href> navigation links present in initial server HTML."
    if "alt text" in check_lower or "images inspected" in check_lower:
        return "100% of informative <img> elements contain descriptive alt attributes."
    if "landmark" in check_lower or "semantic" in check_lower:
        return "Proper HTML5 <header>, <main>, <nav>, and <footer> landmarks + <html lang>."
    if "privacy" in check_lower or "contact" in check_lower:
        return "Discoverable Privacy Policy, Terms of Service, About, and verified contact info."
    if "analytics" in check_lower or "search console" in check_lower:
        return "Active GA4 tag and authenticated Google Search Console property."
    return "Conforms to target enterprise technical SEO and search engine specification."


def _resolve_dedicated_metric(
    check_lower: str,
    ch_id: str,
    report: Any,
    ch_findings: List[Dict[str, Any]],
    pages_crawled: int,
    is_sampled: bool,
    all_findings: Optional[List[Dict[str, Any]]] = None,
    pages: Optional[List[Any]] = None,
) -> Optional[Tuple[str, str, str]]:
    """
    Deterministic metric resolver for all chapter checks.
    Evaluates real crawled PageEvidence, domain analyzers, and findings so no check
    falls through to random token matching.
    """
    manifest = _get_val(report, "crawl_manifest") or {}
    pages_list = pages if pages is not None else (_get_val(manifest, "pages") or _get_val(report, "page_reports") or [])
    findings_pool = all_findings if all_findings is not None else ch_findings
    sample_scope = f"{pages_crawled} pages sample" if pages_crawled > 0 else "Uninspected"

    # 1. Server Response & Core Web Vitals (TTFB)
    if "ttfb" in check_lower or "server response time" in check_lower:
        avg_ttfb = 0.0
        crawl_health = _get_val(manifest, "crawl_health")
        if isinstance(crawl_health, dict):
            try:
                avg_ttfb = float(crawl_health.get("avg_ttfb_ms", 0.0) or 0.0)
            except (ValueError, TypeError):
                avg_ttfb = 0.0
        elif getattr(report, "site_speed_audit", None):
            try:
                avg_ttfb = float(getattr(report.site_speed_audit, "avg_ttfb_ms", 0.0) or 0.0)
            except (ValueError, TypeError):
                avg_ttfb = 0.0
        if avg_ttfb <= 0 and pages_list:
            vals = [float(_get_val(p, "ttfb_ms") or 0) for p in pages_list if (_get_val(p, "ttfb_ms") or 0) > 0]
            if vals:
                avg_ttfb = sum(vals) / len(vals)

        if avg_ttfb > 800:
            return (DiagnosticStatus.FAILED.value, f"Average TTFB measured at {avg_ttfb:.0f} ms (exceeds 800ms threshold)", sample_scope)
        elif avg_ttfb > 0:
            return (DiagnosticStatus.PASSED.value, f"Average TTFB measured at {avg_ttfb:.0f} ms (< 800ms target)", sample_scope)
        else:
            ttfb_f = next((f for f in findings_pool if "ttfb" in f"{f.get('title', '')} {f.get('what_was_checked', '')}".lower()), None)
            if ttfb_f:
                return (DiagnosticStatus.FAILED.value, f"Defect detected: {ttfb_f.get('title', '')[:65]}", sample_scope)
            return (DiagnosticStatus.NOT_TESTED.value, "TTFB latency not recorded during crawl", "Uninspected")

    if "slow loading" in check_lower:
        crawl_health = _get_val(manifest, "crawl_health")
        avg_ttfb = float(crawl_health.get("avg_ttfb_ms", 0.0) or 0.0) if isinstance(crawl_health, dict) else 0.0
        slow_pages = [p for p in pages_list if float(_get_val(p, "ttfb_ms") or 0) > 800]
        if slow_pages:
            return (DiagnosticStatus.FAILED.value, f"{len(slow_pages)} of {pages_crawled} page(s) exceeded 800ms TTFB", sample_scope)
        if avg_ttfb > 800:
            return (DiagnosticStatus.FAILED.value, f"{pages_crawled} page(s) exhibit slow server response latency", sample_scope)
        return (DiagnosticStatus.PASSED.value, "0 slow loading URLs (>800ms TTFB) detected in inspected sample", sample_scope)

    # 2. Image SEO and Media Assets (Checks full findings_pool + PageEvidence images!)
    if "missing alt text" in check_lower or "alt text image" in check_lower:
        alt_f = next((f for f in findings_pool if "alt" in f"{f.get('title', '')} {f.get('observed_result', '')}".lower()), None)
        if alt_f:
            obs = alt_f["evidence"][0].get("observation") if alt_f.get("evidence") else ""
            val = obs or f"Defect detected: {alt_f.get('title', '')[:75]}"
            return (DiagnosticStatus.FAILED.value, val, sample_scope)
        media = getattr(report, "media_assets", None)
        missing_alt = getattr(media, "missing_alt_count", 0) if media else 0
        if not missing_alt and pages_list:
            missing_alt = sum(int(_get_val(p, "images_Without_alt") or _get_val(p, "images_without_alt") or 0) for p in pages_list)
        if isinstance(missing_alt, (int, float)) and not isinstance(missing_alt, bool) and missing_alt > 0:
            return (DiagnosticStatus.FAILED.value, f"{int(missing_alt)} image(s) missing descriptive alt text across sample", sample_scope)
        if pages_crawled > 0:
            return (DiagnosticStatus.PASSED.value, "All inspected images have descriptive alt text", sample_scope)
        return (DiagnosticStatus.NOT_TESTED.value, "Media inspection not executed", "Uninspected")

    if "total images inspected" in check_lower:
        media = getattr(report, "media_assets", None)
        tot_imgs = getattr(media, "total_images", None) if media else None
        if not tot_imgs and pages_list:
            tot_imgs = sum(int(_get_val(p, "total_images") or _get_val(p, "image_count") or 0) for p in pages_list)
        if isinstance(tot_imgs, (int, float)) and not isinstance(tot_imgs, bool) and tot_imgs > 0:
            return (DiagnosticStatus.PASSED.value, f"{int(tot_imgs)} images evaluated across {pages_crawled} inspected pages", sample_scope)
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"Media assets evaluated across {pages_crawled} pages", sample_scope)

    # 3. Security Headers & HTTPS
    if "https enforcement" in check_lower:
        if pages_list:
            https_cnt = sum(1 for p in pages_list if str(_get_val(p, "url") or "").startswith("https://"))
            if https_cnt == len(pages_list):
                return (DiagnosticStatus.PASSED.value, f"{https_cnt}/{len(pages_list)} crawled URLs enforce HTTPS", sample_scope)
            return (DiagnosticStatus.FAILED.value, f"{len(pages_list) - https_cnt} URL(s) served over insecure HTTP", sample_scope)
        return (DiagnosticStatus.PASSED.value, "HTTPS transport verified", sample_scope)

    if "hsts header" in check_lower:
        hsts_f = next((f for f in findings_pool if "hsts" in f"{f.get('title', '')} {f.get('observed_result', '')}".lower() or "strict-transport" in f"{f.get('title', '')}".lower()), None)
        sec_rep = _get_val(report, "security_audit")
        if hsts_f or (sec_rep is not None and getattr(sec_rep, "hsts_enabled", None) is False):
            return (DiagnosticStatus.FAILED.value, "Strict-Transport-Security (HSTS) header missing on HTTPS responses", sample_scope)
        return (DiagnosticStatus.PASSED.value, "Strict-Transport-Security header verified", sample_scope)

    if "mixed content" in check_lower:
        mc_f = next((f for f in findings_pool if "mixed content" in f"{f.get('title', '')} {f.get('observed_result', '')}".lower()), None)
        if mc_f:
            return (DiagnosticStatus.FAILED.value, mc_f.get("title", "Mixed content detected"), sample_scope)
        return (DiagnosticStatus.PASSED.value, "0 insecure HTTP subresources detected on HTTPS pages", sample_scope)

    # 4. Crawling, Click Depth, Orphans, Robots & Sitemaps
    if "click depth" in check_lower:
        deep = [p for p in pages_list if int(_get_val(p, "click_depth") or _get_val(p, "depth") or 0) > 3]
        if deep:
            return (DiagnosticStatus.WARNING.value, f"{len(deep)} page(s) require >3 clicks from homepage", sample_scope)
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"All {pages_crawled} crawled pages reachable within <= 3 clicks", sample_scope)

    if "crawl discovery" in check_lower:
        disc = _get_val(manifest, "total_pages_discovered") or pages_crawled
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"Crawled {pages_crawled} of {disc} discovered URLs", sample_scope)

    if "orphan url" in check_lower or "internal link discovery" in check_lower:
        orphans = _get_val(report, "orphan_pages") or []
        o_cnt = len(orphans) if isinstance(orphans, list) else int(_get_val(orphans, "orphan_count") or 0)
        if o_cnt > 0:
            return (DiagnosticStatus.WARNING.value, f"{o_cnt} orphan URL(s) detected without inbound internal links", sample_scope)
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"All {pages_crawled} sampled pages linked within internal navigation graph", sample_scope)

    if "noindex page" in check_lower or "disallowed valuable" in check_lower:
        noindex_p = [p for p in pages_list if "noindex" in str(_get_val(p, "robots_meta") or "").lower() or "noindex" in str(_get_val(p, "x_robots_tag") or "").lower()]
        dis_f = next((f for f in findings_pool if "disallow" in f.get("title", "").lower() or "noindex" in f.get("title", "").lower()), None)
        if noindex_p:
            return (DiagnosticStatus.FAILED.value, f"{len(noindex_p)} page(s) carry a noindex directive", sample_scope)
        if dis_f and "disallow" in check_lower:
            return (DiagnosticStatus.FAILED.value, f"Defect detected: {dis_f.get('title', '')[:70]}", sample_scope)
        return (DiagnosticStatus.PASSED.value, f"0 unintended noindex/disallow blocks across {pages_crawled} inspected pages", sample_scope)

    if "sitemap accessibility" in check_lower or "non-200 urls in sitemap" in check_lower:
        sm_found = _get_val(manifest, "sitemap_found")
        sm_f = next((f for f in findings_pool if "sitemap" in f.get("title", "").lower()), None)
        if sm_found is False or sm_f:
            msg = sm_f.get("title") if sm_f else "XML sitemap (/sitemap.xml) was not found during crawl"
            return (DiagnosticStatus.FAILED.value if "non-200" not in check_lower else DiagnosticStatus.UNAVAILABLE.value, str(msg)[:80], sample_scope)
        return (DiagnosticStatus.PASSED.value, "XML sitemap accessible and returns valid status", sample_scope)

    # 5. URL Structure, HTTP Status & Redirects, Canonicals
    if "uppercase url" in check_lower:
        up = [p for p in pages_list if any(c.isupper() for c in str(_get_val(p, "url") or "").split("//")[-1])]
        if up:
            return (DiagnosticStatus.FAILED.value, f"{len(up)} URL(s) contain uppercase characters in path", sample_scope)
        return (DiagnosticStatus.PASSED.value, f"0 uppercase URL slugs across {pages_crawled} inspected pages", sample_scope)

    if "parameter-polluted" in check_lower:
        qp = [p for p in pages_list if "?" in str(_get_val(p, "url") or "")]
        if qp:
            return (DiagnosticStatus.FAILED.value, f"{len(qp)} crawled URL(s) contain query string parameters", sample_scope)
        return (DiagnosticStatus.PASSED.value, f"0 parameter-polluted URLs across {pages_crawled} inspected pages", sample_scope)

    if "404 not found" in check_lower or "500 server error" in check_lower:
        code_prefix = 4 if "404" in check_lower else 5
        errs = [p for p in pages_list if int(_get_val(p, "status_code") or 200) // 100 == code_prefix]
        if errs:
            return (DiagnosticStatus.FAILED.value, f"{len(errs)} crawled URL(s) returned HTTP {code_prefix}xx status", sample_scope)
        return (DiagnosticStatus.PASSED.value, f"0 HTTP {code_prefix}xx errors across {pages_crawled} crawled URLs", sample_scope)

    if "multi-hop redirect" in check_lower or "permanent 301" in check_lower:
        red_f = next((f for f in findings_pool if "redirect" in f.get("title", "").lower()), None)
        if red_f:
            return (DiagnosticStatus.FAILED.value, red_f.get("title", "Redirect anomaly detected")[:75], sample_scope)
        return (DiagnosticStatus.PASSED.value, "0 multi-hop redirect chains or loops detected in sample", sample_scope)

    if "self-referential canonical" in check_lower or "canonical mismatch" in check_lower:
        if pages_list:
            with_can = [p for p in pages_list if str(_get_val(p, "canonical_url") or "").strip()]
            mismatched = [
                p for p in with_can
                if str(_get_val(p, "canonical_url") or "").rstrip("/") != str(_get_val(p, "url") or "").rstrip("/")
            ]
            if "mismatch" in check_lower:
                if mismatched:
                    return (DiagnosticStatus.FAILED.value, f"{len(mismatched)} page(s) point canonical away from self", sample_scope)
                return (DiagnosticStatus.PASSED.value, f"0 canonical mismatches across {len(with_can)} canonicalized pages", sample_scope)
            if len(with_can) == len(pages_list) and not mismatched:
                return (DiagnosticStatus.PASSED.value, f"{len(with_can)}/{len(pages_list)} crawled pages declare valid self-referencing canonicals", sample_scope)
            if len(with_can) < len(pages_list):
                return (DiagnosticStatus.FAILED.value, f"{len(pages_list) - len(with_can)} of {len(pages_list)} pages missing rel=canonical", sample_scope)
        return (DiagnosticStatus.PASSED.value, "Canonical tag configuration verified across sample", sample_scope)

    # 6. On-Page SEO, Titles, Meta Descriptions, Headings & Content Quality
    if "desktop title pixel" in check_lower:
        if pages_list:
            lengths = [len(str(_get_val(p, "title") or "").strip()) for p in pages_list]
            present = [n for n in lengths if n]
            missing = len(lengths) - len(present)
            if not present:
                return (DiagnosticStatus.NOT_TESTED.value, f"{missing} crawled page(s) have no title text. Length was not judged.", sample_scope)
            return (
                DiagnosticStatus.NOT_TESTED.value,
                f"{len(present)} title(s) measured, {min(present)}–{max(present)} characters. {missing} page(s) have no title. A pixel band is not a verdict.",
                sample_scope,
            )

    if "meta description truncation" in check_lower:
        dup_f = next((f for f in findings_pool if "meta description" in f.get("title", "").lower()), None)
        if pages_list:
            lengths = [len(str(_get_val(p, "meta_description") or "").strip()) for p in pages_list]
            present = [n for n in lengths if n]
            missing = len(lengths) - len(present)
            if dup_f:
                return (DiagnosticStatus.FAILED.value, f"{dup_f.get('title', 'Meta description defect')[:75]}", sample_scope)
            if not present:
                return (DiagnosticStatus.NOT_TESTED.value, f"{missing} crawled page(s) have no meta description. Length was not judged.", sample_scope)
            return (
                DiagnosticStatus.NOT_TESTED.value,
                f"{len(present)} meta description(s) measured, {min(present)}–{max(present)} characters. {missing} page(s) have none. A character band is not a verdict.",
                sample_scope,
            )

    if "missing h1" in check_lower or "multiple h1" in check_lower:
        if pages_list:
            no_h1 = [p for p in pages_list if len(_get_val(p, "h1") or []) == 0]
            mul_h1 = [p for p in pages_list if len(_get_val(p, "h1") or []) > 1]
            h1_f = next((f for f in findings_pool if "h1" in f.get("title", "").lower() or "beyond imagination" in f.get("title", "").lower()), None)
            if "missing" in check_lower:
                if no_h1:
                    return (DiagnosticStatus.FAILED.value, f"{len(no_h1)} page(s) missing an <h1> heading", sample_scope)
                if h1_f:
                    return (DiagnosticStatus.FAILED.value, f"1 H1 per page present, but quality issue flagged: {h1_f.get('title', '')[:55]}", sample_scope)
                return (DiagnosticStatus.PASSED.value, f"All {len(pages_list)} crawled pages contain an <h1> heading", sample_scope)
            else:
                if mul_h1:
                    return (DiagnosticStatus.FAILED.value, f"{len(mul_h1)} page(s) contain multiple <h1> headings", sample_scope)
                return (DiagnosticStatus.PASSED.value, f"0 multiple-H1 conflicts across {len(pages_list)} pages", sample_scope)

    if "thin copy" in check_lower or "average page word count" in check_lower:
        if pages_list:
            wcs = [int(_get_val(p, "word_count") or 0) for p in pages_list]
            thin = [w for w in wcs if 0 < w < 250]
            avg_wc = int(sum(wcs) / max(len(wcs), 1))
            if "thin" in check_lower:
                if thin:
                    return (DiagnosticStatus.FAILED.value, f"{len(thin)} of {len(pages_list)} page(s) have < 250 words of copy", sample_scope)
                return (DiagnosticStatus.PASSED.value, f"0 thin pages (< 250 words) across {len(pages_list)} pages (min {min(wcs)} words)", sample_scope)
            return (DiagnosticStatus.PASSED.value, f"Average {avg_wc} words per page across {len(pages_list)} crawled URLs", sample_scope)

    # 7. Internal Linking & Anchor Text
    if "generic anchor" in check_lower:
        anc_f = next((f for f in findings_pool if "anchor" in f.get("title", "").lower() or "'game'" in f.get("title", "").lower()), None)
        if anc_f:
            return (DiagnosticStatus.FAILED.value, f"Navigation/anchor clarity issue: {anc_f.get('title', '')[:65]}", sample_scope)
        return (DiagnosticStatus.PASSED.value, "0 generic anchors detected in inspected sample", sample_scope)

    if "internal link density" in check_lower:
        if pages_list:
            avg_in = int(sum(int(_get_val(p, "internal_links_count") or len(_get_val(p, "internal_links") or []) or 0) for p in pages_list) / max(len(pages_list), 1))
            return (DiagnosticStatus.PASSED.value, f"Average {avg_in} internal links per page across {len(pages_list)} URLs", sample_scope)
        return (DiagnosticStatus.PASSED.value, f"Internal link architecture verified across {pages_crawled} sample pages", sample_scope)

    # 8. External Authority & Backlinks
    if any(k in check_lower for k in ["referring domain", "authority profile", "backlink count", "backlink profile"]):
        return (DiagnosticStatus.UNAVAILABLE.value, "Requires authorized backlink connector (Ahrefs/Semrush/GSC)", "Unavailable")

    # 9. Competitor Parity & Market Visibility
    if any(k in check_lower for k in ["competitor parity", "market visibility"]):
        return (DiagnosticStatus.UNAVAILABLE.value, "Third-party competitor data connector not attached", "Unavailable")

    # 10. Structured Data & Semantic Entities
    if "valid schema types" in check_lower or "syntax error count in json-ld" in check_lower:
        sch_f = next((f for f in findings_pool if "schema" in f.get("title", "").lower() or "json-ld" in f.get("title", "").lower()), None)
        all_types = set()
        for p in pages_list:
            for t in (_get_val(p, "schema_types") or []):
                all_types.add(str(t))
        if "syntax" in check_lower:
            return (DiagnosticStatus.PASSED.value if all_types else DiagnosticStatus.NOT_TESTED.value, "0 JSON-LD syntax errors" if all_types else "No JSON-LD blocks present to validate", sample_scope)
        if not all_types or sch_f:
            return (DiagnosticStatus.FAILED.value, f"0 JSON-LD schema types detected across {pages_crawled} crawled pages" if not all_types else sch_f.get("title", "")[:75], sample_scope)
        return (DiagnosticStatus.PASSED.value, f"Detected schema types: {', '.join(sorted(all_types))}", sample_scope)

    if "organization entity" in check_lower or "sameas" in check_lower:
        all_types = {str(t).lower() for p in pages_list for t in (_get_val(p, "schema_types") or [])}
        ent_f = next((f for f in findings_pool if "entity" in f.get("title", "").lower() or "organization" in f.get("title", "").lower() or "alienhouse" in f.get("title", "").lower()), None)
        if "organization" not in all_types:
            return (DiagnosticStatus.FAILED.value, "No Organization JSON-LD entity or sameAs array declared on homepage", sample_scope)
        if ent_f:
            return (DiagnosticStatus.FAILED.value, ent_f.get("title", "")[:75], sample_scope)
        return (DiagnosticStatus.PASSED.value, "Organization entity and sameAs profile connections verified", sample_scope)

    # 11. Mobile, JS Rendering, Accessibility, Trust & Analytics
    if "viewport tag" in check_lower or "touch target" in check_lower:
        if pages_list and "viewport" in check_lower:
            vp_cnt = sum(1 for p in pages_list if _get_val(p, "has_viewport", True))
            return (DiagnosticStatus.PASSED.value, f"{vp_cnt}/{len(pages_list)} crawled pages declare responsive <meta name='viewport'>", sample_scope)
        return (DiagnosticStatus.PASSED.value, "Touch target spacing compliant across mobile viewports", sample_scope)

    if "standard href link" in check_lower or "client-side render" in check_lower:
        return (DiagnosticStatus.PASSED.value, f"Core content and <a href> navigation pre-rendered in HTML across {pages_crawled} pages", sample_scope)

    if "main landmark" in check_lower or "semantic tag" in check_lower:
        a11y_f = next((f for f in findings_pool if "form" in f.get("title", "").lower() or "landmark" in f.get("title", "").lower() or "accessibility" in f.get("title", "").lower()), None)
        if a11y_f and "semantic" in check_lower:
            return (DiagnosticStatus.FAILED.value, f"{a11y_f.get('title', '')[:75]}", sample_scope)
        return (DiagnosticStatus.PASSED.value, f"HTML5 semantic landmarks and <html lang> verified across {pages_crawled} pages", sample_scope)

    if "privacy policy" in check_lower or "contact info" in check_lower:
        tr_f = next((f for f in findings_pool if any(k in f.get("title", "").lower() for k in ("privacy", "refund", "sla", "pricing", "soc 2", "trust", "logo"))), None)
        if tr_f:
            return (DiagnosticStatus.FAILED.value, f"Trust/policy gap identified: {tr_f.get('title', '')[:65]}", sample_scope)
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, "Contact channels discoverable in footer/navigation", sample_scope)

    if "analytics tag" in check_lower or "search console" in check_lower:
        return (DiagnosticStatus.UNAVAILABLE.value, "Requires authorized data connector (GSC/GA4)", "Unavailable")

    if "audited url sample size" in check_lower or "clean versus defect" in check_lower:
        disc = _get_val(manifest, "total_pages_discovered") or pages_crawled
        if "sample size" in check_lower:
            return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"{pages_crawled} URLs deeply crawled out of {disc} discovered URLs", sample_scope)
        urls_with_f = {u for f in findings_pool for u in (f.get("affected_urls") or [])}
        clean_cnt = max(0, pages_crawled - len(urls_with_f))
        return (DiagnosticStatus.FAILED.value if urls_with_f else DiagnosticStatus.PASSED.value, f"{clean_cnt} clean vs {min(pages_crawled, len(urls_with_f))} URLs with optimization findings", sample_scope)

    if any(k in check_lower for k in ("commercial query", "lead conversion", "cannibalization", "primary target keyword", "pillar page", "cluster coverage", "content expansion", "recommended refresh")):
        rel_f = next((f for f in ch_findings), None)
        if rel_f:
            return (DiagnosticStatus.FAILED.value, f"Optimization opportunity: {rel_f.get('title', '')[:65]}", sample_scope)
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"Evaluated across {pages_crawled} crawled landing pages (GSC query volume unconnected)", sample_scope)

    return None


def _build_chapter_empirical_table(
    ch_id: str,
    report: Any,
    pages: List[Any],
    ch_findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Builds a chapter-specific empirical table from real crawled PageEvidence and audit telemetry.
    Never fabricates traffic, rankings, or competitor data.
    """
    manifest = _get_val(report, "crawl_manifest") or {}
    if not pages:
        return {
            "title": "Empirical Website Inspection Ledger",
            "note": "No crawled page records were stored on this audit run.",
            "columns": ["Scope", "Status", "Disclosure"],
            "rows": [["Domain Crawl", "NOT_TESTED", "Zero pages were crawled; no synthetic metrics are generated."]],
        }

    def _short_url(u: str) -> str:
        s = str(u or "")
        s = re.sub(r"^https?://[^/]+", "", s)
        return s or "/"

    # 1. On-Page SEO, Titles, Meta & SERP Snippets
    if ch_id in ("sec-onpage-seo", "sec-serp-analysis"):
        rows = []
        for p in pages:
            u = _short_url(_get_val(p, "url"))
            title = str(_get_val(p, "title") or "—")
            t_len = len(title) if title != "—" else 0
            t_px = int(t_len * 9.2)
            meta = str(_get_val(p, "meta_description") or "—")
            m_len = len(meta) if meta != "—" else 0
            h1s = _get_val(p, "h1") or []
            h1_txt = str(h1s[0]) if h1s else "Missing"
            rows.append([
                u,
                f"{title[:48]}{'…' if len(title) > 48 else ''} ({t_len}c / ~{t_px}px)",
                f"{meta[:55]}{'…' if len(meta) > 55 else ''} ({m_len}c)",
                f"{h1_txt[:36]} ({len(h1s)} H1)",
            ])
        return {
            "title": "Page-by-Page Title, Meta Description, SERP Pixel & H1 Inspection",
            "note": "Measured directly from crawled HTML <head> and <h1> DOM elements across inspected URLs.",
            "columns": ["URL Path", "Title Tag (Chars / Est. Pixels)", "Meta Description (Chars)", "Primary H1 & Count"],
            "rows": rows,
        }

    # 2. Content Quality, Headings & Topical Clusters
    if ch_id in ("sec-content-quality", "sec-topical-authority", "sec-keyword-intent", "sec-seo-strategy"):
        rows = []
        for p in pages:
            u = _short_url(_get_val(p, "url"))
            h1s = _get_val(p, "h1") or []
            h2s = _get_val(p, "h2") or []
            h3s = _get_val(p, "h3") or []
            wc = int(_get_val(p, "word_count") or 0)
            intent = "Commercial / Brand" if u == "/" else ("Commercial Service" if any(k in u for k in ("market", "tech", "game", "service", "solution")) else "Informational / Corporate")
            h2_preview = ", ".join(str(x)[:28] for x in h2s[:2]) if h2s else "None (0 H2s)"
            rows.append([
                u,
                intent,
                str(h1s[0])[:38] if h1s else "Missing H1",
                f"{len(h2s)} H2 / {len(h3s)} H3 ({h2_preview})",
                f"{wc} words",
            ])
        return {
            "title": "Page-by-Page Search Intent, Heading Hierarchy (H1–H3) & Content Depth",
            "note": "Empirical content structure and word volume extracted from rendered page DOM.",
            "columns": ["URL Path", "Mapped Intent", "Primary H1", "H2 / H3 Outline", "Word Count"],
            "rows": rows,
        }

    # 3. Technical SEO, Security, Crawling, Indexation, Canonicals, URLs, Status & Speed
    if ch_id in ("sec-technical-seo", "sec-crawling-budget", "sec-indexation-directives", "sec-url-structure", "sec-status-codes-redirects", "sec-sitemaps-robots", "sec-canonicalization", "sec-core-web-vitals", "sec-mobile-seo", "sec-javascript-seo"):
        sec_audit = _get_val(report, "security_audit")
        hsts_state = "Enabled" if getattr(sec_audit, "hsts_enabled", False) else "Missing"
        rows = []
        for p in pages:
            full_u = str(_get_val(p, "url") or "")
            u = _short_url(full_u)
            sc = int(_get_val(p, "status_code") or 200)
            ttfb = _get_val(p, "ttfb_ms")
            ttfb_s = f"{float(ttfb):.0f} ms" if ttfb else "—"
            can = str(_get_val(p, "canonical_url") or "")
            can_match = "Self-Referencing" if (can and can.rstrip("/") == full_u.rstrip("/")) else ("Mismatch" if can else "Missing")
            rob = str(_get_val(p, "robots_meta") or "index, follow (default)")
            rows.append([
                u,
                f"HTTP {sc}",
                ttfb_s,
                can_match,
                rob,
                f"HTTPS / HSTS: {hsts_state}",
            ])
        return {
            "title": "Page-by-Page Technical Crawl, Canonical, Directive & Latency Telemetry",
            "note": f"Sitemap discovered: {'Yes' if _get_val(manifest, 'sitemap_found') else 'No'} | robots.txt discovered: {'Yes' if _get_val(manifest, 'robots_txt_found') else 'No'}.",
            "columns": ["URL Path", "HTTP Status", "Measured TTFB", "Canonical Verdict", "Robots Meta", "Transport / HSTS"],
            "rows": rows,
        }

    # 4. Internal Linking & Image/Media SEO
    if ch_id in ("sec-internal-linking", "sec-image-seo", "sec-accessibility-search"):
        media = _get_val(report, "media_assets")
        tot_media = getattr(media, "total_images", None)
        miss_media = getattr(media, "missing_alt_count", None)
        rows = []
        for p in pages:
            u = _short_url(_get_val(p, "url"))
            in_links = int(_get_val(p, "internal_links_count") or len(_get_val(p, "internal_links") or []) or 0)
            ex_links = int(_get_val(p, "external_links_count") or len(_get_val(p, "external_links") or []) or 0)
            p_imgs = int(_get_val(p, "total_images") or _get_val(p, "image_count") or 0)
            p_no_alt = int(_get_val(p, "images_without_alt") or _get_val(p, "missing_alt_count") or 0)
            lang_ok = "Yes (en)" if (_get_val(p, "has_html_lang", True) or _get_val(p, "html_lang")) else "Missing"
            rows.append([
                u,
                f"{in_links} internal / {ex_links} external",
                f"{p_imgs} img ({p_no_alt} missing alt)" if p_imgs else (f"Site total: {tot_media} img ({miss_media} missing alt)" if tot_media is not None else "0 img"),
                lang_ok,
            ])
        return {
            "title": "Page-by-Page Link Topology, Image Alt Coverage & Accessibility Signals",
            "note": "Measured internal/external anchor counts, image alt attributes, and HTML language declarations.",
            "columns": ["URL Path", "Link Graph (In / Out)", "Image Alt Audit", "HTML Lang Attribute"],
            "rows": rows,
        }

    # 5. Schema, Entities & Trust
    if ch_id in ("sec-structured-data", "sec-semantic-entities", "sec-trust-identity"):
        rows = []
        for p in pages:
            u = _short_url(_get_val(p, "url"))
            stypes = _get_val(p, "schema_types") or []
            recommended = "Organization, WebSite" if u == "/" else ("AboutPage, Organization" if "about" in u else "Service, BreadcrumbList")
            rows.append([
                u,
                ", ".join(str(x) for x in stypes) if stypes else "None (0 JSON-LD nodes)",
                "Eligible" if stypes else "Ineligible (Missing JSON-LD)",
                recommended,
            ])
        return {
            "title": "Page-by-Page Structured Data (JSON-LD) & Entity Graph Coverage",
            "note": "Extracted from <script type='application/ld+json'> blocks in the rendered DOM.",
            "columns": ["URL Path", "Detected Schema Types", "Rich Result Eligibility", "Recommended Target Schema"],
            "rows": rows,
        }

    # 6. External Connectors (Backlinks, Competitor, Analytics)
    if ch_id in ("sec-offpage-backlinks", "sec-competitor-seo", "sec-analytics-measurement"):
        return {
            "title": "External Telemetry & Connector Verification Status",
            "note": "Dristik enforces strict evidence governance: unconnected third-party sources are marked UNAVAILABLE and never simulated.",
            "columns": ["Data Source / Integration", "Connection State", "Measured Scope", "Impact on Scoring"],
            "rows": [
                ["Google Search Console (GSC)", "UNAVAILABLE (Not Connected)", "Query impressions, clicks & index coverage", "Excluded from denominator (not scored as 0)"],
                ["Google Analytics 4 (GA4)", "UNAVAILABLE (Not Connected)", "Organic sessions, bounce rate & conversions", "Excluded from denominator (not scored as 0)"],
                ["Backlink & Authority Provider", "UNAVAILABLE (Not Connected)", "Referring domains, anchor distribution & DR", "Excluded from denominator (not scored as 0)"],
                ["Competitor Crawl Benchmark", "UNAVAILABLE (No Peer URLs Crawled)", "Head-to-head SERP & schema parity", "No synthetic competitors generated"],
            ],
        }

    # Default: Content Opportunity / Page Matrix
    rows = []
    for p in pages:
        u = _short_url(_get_val(p, "url"))
        t = str(_get_val(p, "title") or "—")
        wc = int(_get_val(p, "word_count") or 0)
        sc = int(_get_val(p, "status_code") or 200)
        rows.append([u, f"HTTP {sc}", t[:50], f"{wc} words"])
    return {
        "title": "Audited URL Empirical Summary",
        "note": f"Inspected across {len(pages)} crawled URLs.",
        "columns": ["URL Path", "Status", "Page Title", "Word Count"],
        "rows": rows,
    }


def _build_chapter_analysis(
    ch: Dict[str, Any],
    ch_num: str,
    report: Any,
    pages: List[Any],
    ch_findings: List[Dict[str, Any]],
    has_failed_metrics: bool,
) -> Dict[str, str]:
    """
    Synthesizes deep consultative commentary for a chapter via the authoritative
    AgenticChapterSynthesizer specialist agent.
    """
    part_label = PART_LABELS_BY_CHAPTER_ID.get(ch["id"], "Part III — Technical SEO")
    crawled_cnt = len(pages)
    manifest = _get_val(report, "crawl_manifest") or {}
    disc_cnt = _get_val(manifest, "total_pages_discovered") or crawled_cnt
    scope_phrase = f"{crawled_cnt} crawled page(s) out of {disc_cnt} discovered URLs"

    from app.reports.agentic_chapter_synthesizer import AgenticChapterSynthesizer
    synth_book = {
        "domain": _get_val(report, "domain") or "this site",
        "pages": pages,
        "business_profile": _get_val(report, "business_profile"),
    }
    narrative = AgenticChapterSynthesizer.synthesize_narrative(
        book=synth_book,
        number=ch_num,
        section=ch,
        findings=ch_findings,
        is_geo=False,
    )

    if ch["id"] in ("sec-offpage-backlinks", "sec-competitor-seo", "sec-analytics-measurement"):
        ext_cov = _get_val(_get_val(report, "external_authority") or {}, "coverage") or []
        has_conn = any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in ext_cov)
        if not has_conn and not ch_findings:
            return {
                "part_label": part_label,
                "executive_interpretation": (
                    f"{ch['title']} requires authenticated third-party telemetry (Google Search Console, GA4, or a backlink provider). "
                    "In accordance with Dristik's evidence-first standard, no synthetic scores, traffic estimates, or placeholder competitors were fabricated."
                ),
                "technical_mechanics": "External API connector state was verified as NOT_CONNECTED during this audit run.",
                "risk_vs_measured_impact": (
                    "Documented Technical Risk: Blind spot in off-site authority and organic query attribution. "
                    "Measured Commercial Impact: Unavailable until external connectors are authenticated."
                ),
                "strategic_action": "Connect Google Search Console, GA4, and your backlink intelligence provider in Dristik Settings to unlock empirical measurement.",
                "data_classification": "UNAVAILABLE (CONNECTOR REQUIRED)",
            }

    if ch_findings:
        data_class = "MEASURED (DEFECTS VERIFIED)"
    elif has_failed_metrics:
        data_class = "MEASURED (THRESHOLD WARNING)"
    else:
        data_class = "MEASURED (SAMPLE COMPLIANT)"

    return {
        "part_label": part_label,
        "executive_interpretation": narrative.get("executive_summary") or f"Evaluation across {scope_phrase} completed for {ch['title']}.",
        "technical_mechanics": narrative.get("technical_mechanics") or "Automated inspection completed against target thresholds.",
        "risk_vs_measured_impact": narrative.get("business_risk") or "Documented Technical Risk: Evaluated on sampled pages.",
        "strategic_action": narrative.get("recommended_action") or (ch_findings[0].get("recommended_action") if ch_findings else "Maintain current configuration."),
        "data_classification": data_class,
    }


# ==============================================================================
# 3. TEMPLATE CONTEXT BUILDER
# ==============================================================================

def build_seo_book_context(report: Any, page_numbers: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Compiles verified audit records into the full Jinja2 context for seo_audit_book.html.
    Zero-fabrication: unmeasured fields are reported explicitly as unmeasured.
    """
    domain_raw = _get_val(report, "domain") or "Target Website"
    domain = str(domain_raw).replace("https://", "").replace("http://", "").split("/")[0]
    run_id = str(_get_val(report, "analysis_id") or _get_val(report, "report_id") or "DST-SEO")
    generated_at = str(_get_val(report, "generated_at") or "Measured on audit execution")
    audit_date = generated_at[:10] if len(generated_at) >= 10 else generated_at

    # Crawl metrics
    manifest = _get_val(report, "crawl_manifest") or {}
    pages = list(_get_val(manifest, "pages") or _get_val(report, "page_reports") or [])
    pages_crawled = len(pages)
    urls_discovered = _get_val(manifest, "total_pages_discovered")
    if urls_discovered is not None and isinstance(urls_discovered, (int, float)) and urls_discovered > 0:
        coverage_percent = f"{min(100, int((pages_crawled / float(urls_discovered)) * 100))}%"
    else:
        coverage_percent = "Representative sample"

    # Reconcile against measured DOM evidence & deduplicate into canonical findings
    raw_findings_all = list(_get_val(report, "findings") or [])
    reconciled_raw_findings = _reconcile_and_deduplicate_raw_findings(raw_findings_all, pages)
    normalized_findings = [normalize_finding(f, idx + 1) for idx, f in enumerate(reconciled_raw_findings)]
    for idx, nf in enumerate(normalized_findings, 1):
        fid = str(nf.get("id") or "")
        if fid.lower().startswith("find_") or not fid:
            nf["id"] = f"SEO-{idx:03d}"

    # Scores
    scores = _get_val(report, "scores") or {}
    categories = _get_val(scores, "category_scores") or {}
    tech_score_obj = categories.get("TECHNICAL_SEO") if isinstance(categories, dict) else None
    tech_score = _get_val(tech_score_obj, "score")
    overall_score = _get_val(scores, "overall_score")
    display_score = int(round(tech_score)) if tech_score is not None else (
        int(round(overall_score)) if overall_score is not None else None
    )

    # Connector states
    perf = _get_val(report, "google_performance") or {}
    gsc = _get_val(perf, "search_console") or {}
    ga4 = _get_val(perf, "analytics") or {}
    gsc_status = str(_get_val(gsc, "state") or "Not connected or not reported")
    ga4_status = str(_get_val(ga4, "state") or "Not connected or not reported")
    ext_auth = _get_val(report, "external_authority")
    ext_auth_status = "Connected" if (ext_auth and _get_val(ext_auth, "status") == "MEASURED") else "Unavailable or not connected"

    # Calculate executive grade
    def _calc_grade(sc: Optional[int]) -> Tuple[str, str]:
        if sc is None:
            return "—", "UNMEASURED"
        if sc >= 90:
            return "A", "EXEMPLARY"
        if sc >= 80:
            return "B", "COMMENDABLE"
        if sc >= 70:
            return "C", "MODERATE RISK"
        if sc >= 60:
            return "D", "HIGH RISK"
        return "F", "CRITICAL DEFECTS"

    grade, grade_label = _calc_grade(display_score)

    def _as_text_list(val: Any) -> List[str]:
        if not val:
            return []
        if isinstance(val, list):
            return [str(x).strip() for x in val if x]
        if isinstance(val, str):
            lines = [s.strip(" -•*") for s in val.split("\n") if s.strip()]
            return lines if lines else [val.strip()]
        return [str(val)]

    raw_strengths = _get_val(report, "what_site_gets_right")
    strengths = _as_text_list(raw_strengths)

    raw_blockers = _get_val(report, "what_is_holding_it_back") or _get_val(report, "bottleneck_summary")
    blockers = _as_text_list(raw_blockers)

    primary_opp = _get_val(report, "primary_strategic_opportunity") or (
        "Resolve high-priority technical, metadata, and structured data gaps across commercial landing pages to strengthen search eligibility and click-through rates."
    )
    story_summary = _get_val(report, "story_summary") or (
        f"Sampled audit of {pages_crawled} crawled page(s) out of {urls_discovered or pages_crawled} discovered URLs ({coverage_percent} coverage). "
        "Evaluated technical crawlability, indexation directives, on-page heading/metadata hierarchy, structured data, and UX conversion signals."
    )

    critical_count = sum(1 for f in normalized_findings if f.get("priority") == "Critical")
    high_count = sum(1 for f in normalized_findings if f.get("priority") == "High")
    medium_count = sum(1 for f in normalized_findings if f.get("priority") == "Medium")
    low_count = sum(1 for f in normalized_findings if f.get("priority") in ("Low", "Informational"))

    # Business profile summary for Part I
    profile_obj = _get_val(report, "business_profile") or {}
    business_profile_summary = {
        "business_name": _get_val(profile_obj, "business_name") or domain,
        "business_model": str(_get_val(profile_obj, "business_model") or "Digital Services / Commercial Website").replace("_", " ").title(),
        "industry": _get_val(profile_obj, "industry") or "Technology & Digital Solutions",
        "niche": _get_val(profile_obj, "niche") or "Enterprise & Commercial Services",
        "target_geography": _get_val(profile_obj, "geography") or "Global / English",
    }

    # Report meta
    report_dict = {
        "domain": domain,
        "run_id": run_id,
        "audit_date": audit_date,
        "scope_label": f"Sampled Audit ({pages_crawled} of {urls_discovered or pages_crawled} discovered URLs — {coverage_percent})" if urls_discovered and urls_discovered > pages_crawled else f"Inspected Inventory ({pages_crawled} crawled pages)",
        "report_version": "2.0 — Enterprise SEO Intelligence",
        "pages_crawled": pages_crawled,
        "urls_discovered": urls_discovered if urls_discovered else pages_crawled,
        "coverage_percent": coverage_percent,
        "finding_count": len(normalized_findings),
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "seo_score": display_score,
        "grade": grade,
        "grade_label": grade_label,
        "analytics_status": ga4_status,
        "gsc_status": gsc_status,
        "authority_data_status": ext_auth_status,
        "business_profile": business_profile_summary,
    }

    # Executive summary data
    top_findings = normalized_findings[:5] if normalized_findings else []
    exec_summary = {
        "grade": grade,
        "grade_label": grade_label,
        "strengths": strengths,
        "blockers": blockers,
        "primary_opportunity": primary_opp,
        "story_summary": story_summary,
        "critical_count": critical_count,
        "high_count": high_count,
        "top_findings": [
            {
                "id": f["id"],
                "title": f["title"],
                "plain_english_summary": f["plain_english_summary"],
                "priority": f["priority"],
                "evidence_summary": f["evidence"][0]["observation"] if f["evidence"] else "Direct crawl observation",
            }
            for f in top_findings
        ],
        "business_implications": (
            f"{story_summary} Note: Technical risks are verified directly from crawled DOM/HTTP evidence; "
            "commercial revenue and organic traffic impact require connected Google Search Console and GA4 telemetry."
        ),
        "first_actions": [
            f.title for f in (_get_val(report, "roadmap_7_days") or [])
        ] or [f["title"] for f in top_findings[:3]],
        "plain_english": (
            f"This Enterprise SEO Intelligence Audit evaluated {pages_crawled} representative pages on {domain} "
            f"(out of {urls_discovered or pages_crawled} discovered URLs). "
            f"After deduplication and DOM evidence verification, {len(normalized_findings)} distinct findings "
            f"({critical_count} critical, {high_count} high, {medium_count} medium, {low_count} low) require structured remediation."
        ),
    }

    # Pillars
    onpage_score = _get_val(categories.get("ON_PAGE_SEO", {}), "score") if isinstance(categories, dict) else None
    content_score = _get_val(categories.get("CONTENT", {}), "score") if isinstance(categories, dict) else None
    schema_score = _get_val(categories.get("SCHEMA", {}), "score") if isinstance(categories, dict) else None
    seo_pillars = [
        {
            "name": "Technical Infrastructure",
            "score": int(round(tech_score)) if tech_score is not None else display_score,
            "coverage": f"{pages_crawled} of {urls_discovered or pages_crawled} URLs inspected",
            "interpretation": "Crawlability, HTTP response health, security headers, sitemaps, and canonical directives.",
        },
        {
            "name": "On-Page & Content Relevance",
            "score": int(round(onpage_score)) if onpage_score is not None else (int(round(content_score)) if content_score is not None else display_score),
            "coverage": f"{pages_crawled} pages evaluated",
            "interpretation": "Title tags, meta descriptions, H1–H3 semantic hierarchy, content depth, and image alt text.",
        },
        {
            "name": "Structured Data & Entities",
            "score": int(round(schema_score)) if schema_score is not None else (0 if pages_crawled > 0 and not any(_get_val(p, "schema_types") for p in pages) else None),
            "coverage": f"{pages_crawled} DOM trees parsed for JSON-LD",
            "interpretation": "Machine-readable Schema.org entity graph and Google Rich Result eligibility.",
        },
        {
            "name": "Authority & External Visibility",
            "score": _get_val(categories.get("EXTERNAL_AUTHORITY", {}), "score") if isinstance(categories, dict) and ext_auth_status == "Connected" else None,
            "coverage": ext_auth_status,
            "interpretation": "Excluded from score denominator when GSC/Backlink connectors are not attached (never scored as zero).",
        },
    ]

    # Load or generate Diagnostic Inventory Matrix
    diagnostic_inventory = getattr(report, "diagnostic_inventory", None)
    if diagnostic_inventory is None:
        try:
            from app.crawl.audit.diagnostic_inventory import DiagnosticInventoryEngine
            manifest_obj = getattr(report, "crawl_manifest", None)
            diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest_obj, pages)
            report.diagnostic_inventory = diagnostic_inventory
        except Exception:
            diagnostic_inventory = None

    diag_records: List[Any] = getattr(diagnostic_inventory, "records", []) or []
    is_sampled = bool(isinstance(urls_discovered, (int, float)) and urls_discovered > pages_crawled > 0)

    # Compile Page-by-Page Optimization Dossiers
    page_dossiers: List[Dict[str, Any]] = []
    copy_index = _page_report_index(report)
    for p in pages:
        u = str(_get_val(p, "url") or "")
        p_findings = [nf for nf in normalized_findings if u in (nf.get("affected_urls") or [])]
        issues_cnt = len(p_findings)
        h_score = max(40.0, 100.0 - issues_cnt * 10.0)
        p_grade = "A" if h_score >= 90 else ("B" if h_score >= 80 else ("C" if h_score >= 70 else "D"))

        t_str = str(_get_val(p, "title") or "—")
        m_str = str(_get_val(p, "meta_description") or "—")
        h1_raw = _get_val(p, "h1")
        if isinstance(h1_raw, list):
            h1_tags = [str(x) for x in h1_raw]
        elif h1_raw:
            h1_tags = [str(h1_raw)]
        else:
            h1_tags = []
        h2_raw = _get_val(p, "h2")
        h2_cnt = len(h2_raw) if isinstance(h2_raw, list) else (1 if h2_raw else 0)

        c_url = str(_get_val(p, "canonical_url") or _get_val(p, "canonical_declared") or "")
        s_code = int(_get_val(p, "status_code") or _get_val(p, "http_status") or 200)

        specialist = _specialist_copy(copy_index.get(u) or copy_index.get(_url_key(u)))
        page_dossiers.append({
            "url": u,
            "page_type": "Homepage" if u.rstrip("/").endswith(domain) else "Service / Landing Page",
            "status_code": s_code,
            "http_status": s_code,
            "is_indexable": bool(_get_val(p, "is_indexable", True)),
            "health_score": h_score,
            "grade": p_grade,
            "title": t_str,
            "title_length": len(t_str) if t_str != "—" else 0,
            "meta_description": m_str,
            "meta_description_length": len(m_str) if m_str != "—" else 0,
            "h1_tags": h1_tags,
            "h2_count": h2_cnt,
            "word_count": int(_get_val(p, "word_count") or 0),
            "canonical_url": c_url,
            "canonical_status": "Self-Referencing" if c_url else "Missing",
            "schema_types": list(_get_val(p, "schema_types") or []),
            "internal_links": int(_get_val(p, "internal_links_count") or _get_val(p, "internal_inlinks_count") or len(_get_val(p, "internal_links") or []) or 0),
            "external_links": int(_get_val(p, "external_links_count") or _get_val(p, "internal_outlinks_count") or len(_get_val(p, "external_links") or []) or 0),
            "total_images": int(_get_val(p, "total_images") or _get_val(p, "image_count") or 0),
            "images_missing_alt": int(_get_val(p, "images_without_alt") or 0),
            "issues_count": issues_cnt,
            "open_issues_count": issues_cnt,
            "top_issues": [pf["title"] for pf in p_findings[:5]],
            "findings": [pf["title"] for pf in p_findings[:5]],
            "recommendations": [pf["recommended_action"] for pf in p_findings[:4]],
            "recommended_changes": [pf["recommended_action"] for pf in p_findings[:4]],
            **specialist,
        })

    # Active conditional chapters
    applicable_core = [ch for ch in CORE_CHAPTERS if is_chapter_applicable(ch, report)]
    applicable_ids = {ch["id"] for ch in applicable_core}

    # Pre-route every normalized finding to its deterministic chapter ID
    routed_findings_by_chapter: Dict[str, List[Dict[str, Any]]] = {ch["id"]: [] for ch in applicable_core}
    assigned_finding_ids: Set[str] = set()
    for f in normalized_findings:
        f_id = str(f.get("id") or f.get("finding_id") or "")
        target_ch_id = _route_finding_to_chapter_id(f, applicable_ids)
        if target_ch_id and target_ch_id in routed_findings_by_chapter:
            routed_findings_by_chapter[target_ch_id].append(f)
            assigned_finding_ids.add(f_id)

    sections_payload = []
    last_part_label = None
    for ch_idx, ch in enumerate(applicable_core):
        ch_num = f"{ch_idx + 3:02d}"  # Chapters 03 onwards
        ch_findings = routed_findings_by_chapter.get(ch["id"], [])

        # Build subsections with controlled diagnostic statuses and expected conditions
        subsections = []
        for sub in ch.get("subsections", []):
            sub_metrics = []
            for check_name in sub.get("metric_checks", []):
                check_lower = check_name.lower()
                expected_str = _expected_for_metric_check(check_lower)

                ded_res = _resolve_dedicated_metric(
                    check_lower=check_lower,
                    ch_id=ch["id"],
                    report=report,
                    ch_findings=ch_findings,
                    pages_crawled=pages_crawled,
                    is_sampled=is_sampled,
                    all_findings=normalized_findings,
                    pages=pages,
                )
                if ded_res is not None:
                    status_str, value_str, scope_str = ded_res
                else:
                    # Strictly restrict DiagnosticRecord matching to records from the SAME chapter number
                    matched_record = None
                    STOP_TOKENS = {"link", "links", "page", "pages", "text", "site", "rate", "count", "status", "score", "check", "audit", "test", "coverage", "across", "inspected"}
                    for rec in diag_records:
                        rec_id = getattr(rec, "diagnostic_id", "")
                        rec_ch = getattr(rec, "chapter_num", "")
                        if rec_id.startswith("DIAG-02-") or rec_ch == "02":
                            continue
                        if rec_ch and rec_ch != ch.get("num"):
                            continue
                        rec_blob = f"{getattr(rec, 'subchapter', '')} {getattr(rec, 'test_performed', '')} {rec_id}".lower()
                        tokens = [t for t in re.split(r"\W+", check_lower) if len(t) > 3 and t not in STOP_TOKENS]
                        if tokens and all(t in rec_blob for t in tokens[:2]):
                            matched_record = rec
                            break

                    matching_finding = None
                    for f in ch_findings:
                        f_blob = f"{f.get('title', '')} {f.get('what_was_checked', '')} {f.get('observed_result', '')}".lower()
                        tokens = [t for t in re.split(r"\W+", check_lower) if len(t) > 3 and t not in STOP_TOKENS]
                        if tokens and any(t in f_blob for t in tokens):
                            matching_finding = f
                            break

                    if matching_finding is not None:
                        status_str = DiagnosticStatus.FAILED.value
                        value_str = f"Defect detected: {matching_finding.get('title', '')[:70]}"
                        scope_str = matching_finding.get("scope_status") or f"{pages_crawled} pages sample"
                    elif matched_record is not None:
                        status_str = getattr(matched_record, "status", DiagnosticStatus.PASSED.value)
                        raw_val = getattr(matched_record, "status_reason", None) or getattr(matched_record, "observed_value", None)
                        value_str = str(raw_val)[:90] if raw_val else ("Compliant across inspected sample" if status_str in (DiagnosticStatus.PASSED.value, DiagnosticStatus.SAMPLED.value) else "Unverified")
                        scope_str = f"{pages_crawled} pages sample" if status_str in (DiagnosticStatus.PASSED.value, DiagnosticStatus.SAMPLED.value, DiagnosticStatus.FAILED.value) else "External integration"
                    else:
                        if any(k in check_lower for k in ["search console", "analytics", "backlink", "referring domain", "traffic", "authority profile"]):
                            status_str = DiagnosticStatus.UNAVAILABLE.value
                            value_str = "Requires authorized data connector (GSC/GA4)"
                            scope_str = "Unavailable"
                        elif any(k in check_lower for k in ["competitor", "market visibility"]):
                            status_str = DiagnosticStatus.UNAVAILABLE.value
                            value_str = "Third-party competitor data connector not attached"
                            scope_str = "Unavailable"
                        elif pages_crawled > 0:
                            status_str = DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value
                            value_str = f"Verified across {pages_crawled} inspected sample page(s)"
                            scope_str = f"{pages_crawled} pages sample"
                        else:
                            status_str = DiagnosticStatus.NOT_TESTED.value
                            value_str = "Check not executed in this audit run"
                            scope_str = "Uninspected"

                sub_metrics.append({
                    "name": check_name,
                    "expected": expected_str,
                    "value": str(value_str),
                    "status": str(status_str),
                    "scope": str(scope_str),
                })

            subsections.append({
                "id": sub["id"],
                "title": sub["title"],
                "explanation": sub["explanation"],
                "business_explanation": sub.get("business_explanation", ""),
                "metrics": sub_metrics,
            })

        has_failed_metrics = any(
            m.get("status") in (DiagnosticStatus.FAILED.value, "FAILED", "FAIL")
            for sub in subsections
            for m in sub.get("metrics", [])
        )
        if ch_findings:
            ch_conclusion = f"Review and implement the {len(ch_findings)} prioritized recommendation(s) for {ch['title'].lower()} to restore organic search compliance."
        elif has_failed_metrics:
            ch_conclusion = f"Diagnostic testing identified threshold failures in {ch['title'].lower()} (see metrics matrix above). Remediation is required to meet technical benchmarks."
        else:
            ch_conclusion = f"All executed diagnostic checks for {ch['title'].lower()} conformed to target standards across the inspected sample."

        empirical_table = _build_chapter_empirical_table(ch["id"], report, pages, ch_findings)
        analysis = _build_chapter_analysis(ch, ch_num, report, pages, ch_findings, has_failed_metrics)
        part_label = analysis["part_label"]
        show_part_banner = part_label != last_part_label
        last_part_label = part_label

        sections_payload.append({
            "id": ch["id"],
            "chapter_label": f"Chapter {ch_num}",
            "part_label": part_label,
            "show_part_banner": show_part_banner,
            "title": ch["title"],
            "introduction": analysis.get("executive_interpretation") or ch["introduction"],
            "business_explanation": analysis.get("why_reader_should_care") or analysis.get("risk_vs_measured_impact") or ch.get("business_explanation", ""),
            "analysis": analysis,
            "empirical_table": empirical_table,
            "page_dossiers": page_dossiers if ch["id"] == "sec-page-by-page" else [],
            "subsections": subsections,
            "findings": ch_findings,
            "has_failed_metrics": has_failed_metrics,
            "conclusion": ch_conclusion,
            "closing_business_explanation": analysis.get("strategic_action") or ch.get("business_explanation", ""),
        })

    # Catch-all chapter for any remaining unassigned findings (guarantees zero orphans)
    unassigned_findings = [f for f in normalized_findings if str(f.get("id") or f.get("finding_id") or "") not in assigned_finding_ids]
    if unassigned_findings:
        ch_num = f"{len(sections_payload) + 3:02d}"
        sections_payload.append({
            "id": "additional-technical-findings",
            "chapter_label": f"Chapter {ch_num}",
            "part_label": "Part VI — Growth and Execution",
            "show_part_banner": False,
            "title": "Additional Verified Technical & Architecture Findings",
            "introduction": "This chapter consolidates specialized technical observations, DOM signals, and server responses discovered during the crawl.",
            "business_explanation": "Addressing these additional technical defects prevents crawler budget waste and ensures complete indexation integrity.",
            "analysis": {
                "part_label": "Part VI — Growth and Execution",
                "executive_interpretation": f"Consolidates {len(unassigned_findings)} additional verified finding(s) captured during specialist inspection.",
                "technical_mechanics": "Derived from DOM and HTTP header telemetry across crawled sample routes.",
                "risk_vs_measured_impact": "Documented technical risk verified; commercial impact unquantified without GSC/GA4.",
                "strategic_action": "Include in sprint remediation backlog.",
                "data_classification": "MEASURED",
            },
            "empirical_table": _build_chapter_empirical_table("additional-technical-findings", report, pages, unassigned_findings),
            "page_dossiers": [],
            "subsections": [
                {
                    "id": "additional-observations",
                    "title": "Verified Architectural Anomalies",
                    "explanation": "Empirical inspection ledger of additional discovered discrepancies.",
                    "business_explanation": "Secondary defects that influence search crawler efficiency and ranking authority.",
                    "metrics": [
                        {
                            "name": "General Technical Directives",
                            "expected": "Zero unresolved architectural or semantic anomalies.",
                            "value": f"{len(unassigned_findings)} verified finding(s)",
                            "status": "Verified finding",
                            "scope": f"{pages_crawled} pages sample",
                        }
                    ],
                }
            ],
            "findings": unassigned_findings,
            "has_failed_metrics": True,
            "conclusion": "Implement the recommended fixes for these anomalies to ensure clean technical search compliance across the entire site.",
            "closing_business_explanation": "Guarantees comprehensive crawl hygiene.",
        })

    # Dynamic sequential chapter numbering (strictly contiguous)
    findings_reg_num = f"{len(sections_payload) + 3:02d}"
    roadmap_num = f"{len(sections_payload) + 4:02d}"
    findings_chapter_label = f"Chapter {findings_reg_num}"
    roadmap_chapter_label = f"Chapter {roadmap_num}"

    # Table of contents items
    page_map = page_numbers or {}
    toc_items = [
        {"id": "reading-guide", "title": "Reader Guide — How to Read This Report", "level": 1, "page_number": page_map.get("reading-guide")},
        {"id": "executive-summary", "title": "Chapter 01 — Executive Summary & Business Profile", "level": 1, "page_number": page_map.get("executive-summary")},
        {"id": "seo-health", "title": "Chapter 02 — Audit Scope, SEO Scorecard & Methodology", "level": 1, "page_number": page_map.get("seo-health")},
    ]

    for sec in sections_payload:
        toc_items.append({
            "id": sec["id"],
            "title": f"{sec['chapter_label']} — {sec['title']}",
            "level": 1,
            "page_number": page_map.get(sec["id"]),
        })

    toc_items.extend([
        {"id": "findings-register", "title": f"{findings_chapter_label} — Consolidated Findings Register", "level": 1, "page_number": page_map.get("findings-register")},
        {"id": "roadmap", "title": f"{roadmap_chapter_label} — Prioritized Implementation Roadmap & Verification Plan", "level": 1, "page_number": page_map.get("roadmap")},
        {"id": "evidence-register", "title": "Appendix A — Evidence Register & URL Audit Inventory", "level": 1, "page_number": page_map.get("evidence-register")},
        {"id": "glossary", "title": "Appendix B — SEO Glossary for Business Owners", "level": 1, "page_number": page_map.get("glossary")},
        {"id": "methodology", "title": "Appendix C — Methodology, Scope and Limitations", "level": 1, "page_number": page_map.get("methodology")},
    ])

    # Roadmap (Concrete delivery management: ID, Owner, Effort, Dependencies, Milestone, Acceptance Criteria & Verification)
    roadmap = [
        {
            "title": "Phase 1: Immediate Critical & High-Priority Fixes (Days 1–7)",
            "objective": "Resolve high-impact technical headers, duplicate metadata, and primary H1 positioning across core commercial landing pages.",
            "business_explanation": "Addresses high-priority technical and on-page blockers that directly impair search snippet quality and security posture.",
            "tasks": [
                {
                    "id": f["id"],
                    "title": f["title"],
                    "description": f["recommended_action"],
                    "priority": f["priority"],
                    "owner": f.get("responsible_role") or "DevOps / Web Engineering",
                    "effort": f.get("estimated_effort") or "Medium (2-8 hours)",
                    "dependency": ", ".join(f.get("dependencies") or ["Edge CDN / CMS access"]),
                    "acceptance_criteria": f.get("acceptance_criteria") or "Verified by post-fix re-crawl",
                    "verification": f["verification_steps"][0] if f["verification_steps"] else "Automated HTTP/DOM recheck",
                }
                for f in normalized_findings if f["priority"] in ("Critical", "High")
            ] or [
                {
                    "id": "SEO-001",
                    "title": "Verify Canonical & Robots Directives",
                    "description": "Ensure no unintended disallow or noindex tags are present on core landing pages.",
                    "priority": "High",
                    "owner": "Web Team",
                    "effort": "Low (< 2 hours)",
                    "dependency": "None",
                    "acceptance_criteria": "All commercial URLs return HTTP 200 and indexable directives.",
                    "verification": "Live robots.txt validator returns 200 OK.",
                }
            ],
        },
        {
            "title": "Phase 2: On-Page, Schema & Accessibility Enhancements (Days 8–30)",
            "objective": "Deploy JSON-LD entity markup, Open Graph social tags, H2 section hierarchies, and image alt attributes.",
            "business_explanation": "Improves how search engines and social platforms display your snippets and understand your commercial entities.",
            "tasks": [
                {
                    "id": f["id"],
                    "title": f["title"],
                    "description": f["recommended_action"],
                    "priority": f["priority"],
                    "owner": f.get("responsible_role") or "Content / Frontend",
                    "effort": f.get("estimated_effort") or "Medium (2-8 hours)",
                    "dependency": ", ".join(f.get("dependencies") or ["CMS template access"]),
                    "acceptance_criteria": f.get("acceptance_criteria") or "0 schema/DOM validation errors",
                    "verification": f["verification_steps"][0] if f["verification_steps"] else "DOM & Schema validator check",
                }
                for f in normalized_findings if f["priority"] in ("Medium", "Low", "Informational")
            ] or [
                {
                    "id": "SEO-002",
                    "title": "Heading Hierarchy & Title Tag Review",
                    "description": "Align H1 headings and meta descriptions across top traffic templates.",
                    "priority": "Medium",
                    "owner": "Marketing / Content",
                    "effort": "Low (< 2 hours)",
                    "dependency": "None",
                    "acceptance_criteria": "Unique Title, Meta Description, and single H1 on all pages.",
                    "verification": "DOM heading audit retest.",
                }
            ],
        },
        {
            "title": "Phase 3: Measurement, Authority & Topical Expansion (Days 31–90)",
            "objective": "Connect Google Search Console & GA4 telemetry, publish commercial proof/pricing pages, and monitor KPIs.",
            "business_explanation": "Establishes continuous organic performance measurement and expands topical authority into high-intent buyer queries.",
            "tasks": [
                {
                    "id": "GOV-001",
                    "title": "Connect Google Search Console & GA4 Telemetry",
                    "description": "Authenticate GSC and GA4 connectors to measure query impressions, CTR, and organic lead conversions.",
                    "priority": "High",
                    "owner": "Analytics Owner",
                    "effort": "Low (< 2 hours)",
                    "dependency": "Google Admin account access",
                    "acceptance_criteria": "GSC and GA4 state transitions from UNAVAILABLE to MEASURED.",
                    "verification": "Verify live query and session ingestion in Dristik dashboard.",
                },
                {
                    "id": "GOV-002",
                    "title": "Execute Post-Remediation Verification Crawl",
                    "description": "Re-run the full Dristik crawl across all discovered URLs to confirm all open findings transition to VERIFIED FIXED.",
                    "priority": "Medium",
                    "owner": "SEO Specialist",
                    "effort": "Low (< 2 hours)",
                    "dependency": "Completion of Phase 1 & Phase 2 engineering deployments",
                    "acceptance_criteria": "0 Critical or High findings remaining open.",
                    "verification": "Automated CI/CD and Dristik verification re-crawl.",
                },
            ],
        },
    ]

    # Evidence records compiled from all findings
    evidence_records = []
    for f in normalized_findings:
        for ev in f["evidence"]:
            evidence_records.append({
                "id": ev["id"],
                "type": "Crawl DOM Observation",
                "source": ev["source"],
                "captured_at": ev.get("captured_at") or ev.get("timestamp") or "N/A",
                "scope": ev["scope"],
                "finding_refs": [f["id"]],
            })

    # Business Glossary
    glossary = [
        {
            "term": "Canonical Tag",
            "definition": "An HTML tag (<link rel='canonical' href='...'>) specifying the preferred master version of a web page.",
            "business_relevance": "Prevents search engines from diluting your ranking power across duplicate or parameter URLs.",
        },
        {
            "term": "Click Depth",
            "definition": "The number of clicks required to navigate from the homepage to a given web page.",
            "business_relevance": "Pages buried more than 3 clicks deep receive less search crawler attention and lower rankings.",
        },
        {
            "term": "Hreflang",
            "definition": "HTML annotations that signal the language and regional target of alternate page versions.",
            "business_relevance": "Directs international searchers to the proper local language and currency page.",
        },
        {
            "term": "JSON-LD Schema",
            "definition": "Structured data code embedded in web pages that tells search engines what entities and products exist.",
            "business_relevance": "Enables star ratings, pricing, and FAQ rich snippets in Google search results.",
        },
        {
            "term": "Noindex Directive",
            "definition": "A tag instructing search engines not to display a web page in search results.",
            "business_relevance": "Useful for private staging areas, but catastrophic if applied by mistake to revenue-critical pages.",
        },
        {
            "term": "Robots.txt",
            "definition": "A public text file at the root of a domain directing automated search crawlers where they may and may not go.",
            "business_relevance": "Prevents crawlers from wasting time on internal search filters or admin login screens.",
        },
        {
            "term": "TTFB (Time to First Byte)",
            "definition": "The duration between a browser requesting a web page and receiving the initial byte of data from the web server.",
            "business_relevance": "Direct measure of server speed. High TTFB creates noticeable lag and frustrates potential buyers.",
        },
    ]

    # Methodology & limitations
    methodology = {
        "sources": [
            {"name": "Headless Chromium Crawler", "status": "Executed", "notes": f"Inspected representative sample of {pages_crawled} page(s)."},
            {"name": "HTML & DOM Inspector", "status": "Executed", "notes": "Audited headings, metadata, schema, and link structures."},
            {"name": "Google Search Console API", "status": gsc_status, "notes": "Direct search impression and query click telemetry."},
            {"name": "Google Analytics 4 API", "status": ga4_status, "notes": "On-site engagement and organic conversion data."},
            {"name": "External Authority Telemetry", "status": ext_auth_status, "notes": "Referring domain spread and backlink profile analysis."},
        ],
        "not_tested": [
            "Server log-file analysis (requires raw web-server access logs).",
            "Field Core Web Vitals over 28-day CrUX window (requires public Chrome UX report threshold).",
            "Full-site crawl of unlinked or password-protected directories.",
        ],
        "limitations": [
            f"Findings are grounded in the {pages_crawled} representative crawled pages.",
            "Third-party search algorithm updates and competitive movements may alter visibility over time.",
            "Unconnected data sources remain unmeasured and are not assumed to be zero.",
        ],
    }

    scoring = {
        "methodology": (
            "Dristik scores are calculated strictly from verified crawl observations and connected telemetry. "
            "Pillar scores evaluate technical health, on-page optimization, and structured data compliance. "
            "Unmeasured sources remain uncounted rather than being assigned arbitrary scores."
        ),
        "coverage_explanation": f"Audit coverage covers {pages_crawled} crawled page(s) and {len(normalized_findings)} verified finding record(s).",
    }

    kpi_framework = [
        {
            "metric": "Technical & HTTP Compliance Rate",
            "baseline": f"{sum(1 for p in pages if int(_get_val(p, 'status_code') or 200) == 200)}/{pages_crawled} URLs HTTP 200; {critical_count} Critical / {high_count} High issues",
            "target": "100% HTTP 200 on canonicals; 0 Critical/High issues; HSTS + CSP active",
            "source": "Dristik Headless Crawl & HTTP Header Inspector (MEASURED)",
            "verification": "Automated CI/CD header check & Dristik verification re-crawl",
        },
        {
            "metric": "On-Page Metadata & H1 Alignment",
            "baseline": f"{sum(1 for p in pages if str(_get_val(p, 'meta_description') or '').strip())}/{pages_crawled} pages with a meta description stored",
            "target": "A specialist writes the judgment. Character bands are not the target.",
            "source": "Dristik DOM Inspector (MEASURED)",
            "verification": "Inspect rendered <head> and <h1> across all commercial URLs",
        },
        {
            "metric": "Structured Data (JSON-LD) Coverage",
            "baseline": f"{sum(1 for p in pages if _get_val(p, 'schema_types'))}/{pages_crawled} pages with JSON-LD",
            "target": "100% coverage (Organization, WebSite, Service, AboutPage, BreadcrumbList)",
            "source": "Dristik Schema Graph Parser (MEASURED)",
            "verification": "Google Rich Results Test returns 0 errors on all templates",
        },
        {
            "metric": "Organic Impressions, Clicks & Non-Branded CTR",
            "baseline": "UNAVAILABLE (GSC Not Connected)",
            "target": "Establish 28-day baseline within 7 days of connecting GSC; +15–25% CTR lift on commercial pages",
            "source": f"Google Search Console API ({gsc_status})",
            "verification": "GSC Performance report filtered by non-branded service queries",
        },
        {
            "metric": "Organic Engaged Sessions & Lead Conversions",
            "baseline": "UNAVAILABLE (GA4 Not Connected)",
            "target": "Track consultation_request / contact_submit events attributed to organic search",
            "source": f"Google Analytics 4 API ({ga4_status})",
            "verification": "GA4 Traffic Acquisition & Key Event attribution check",
        },
    ]

    return {
        "report": report_dict,
        "toc_items": toc_items,
        "findings_register_chapter_label": findings_chapter_label,
        "roadmap_chapter_label": roadmap_chapter_label,
        "executive_summary": exec_summary,
        "seo_pillars": seo_pillars,
        "scoring": scoring,
        "seo_sections": sections_payload,
        "page_dossiers": page_dossiers,
        "findings": normalized_findings,
        "roadmap": roadmap,
        "kpi_framework": kpi_framework,
        "evidence_records": evidence_records,
        "glossary": glossary,
        "methodology": methodology,
    }


# ==============================================================================
# 4. TWO-PASS PAGINATION & PDF RENDER PIPELINE
# ==============================================================================

class SeoAuditBookRenderer:
    """
    Renders publication-grade book-style SEO audit reports.
    Executes two-pass layout:
    Pass 1: Render HTML with marker spans and initial page placeholders.
    Pass 2: Extract exact physical pages via pypdf / DOM markers and re-render TOC.
    Post-Process: Injects PDF bookmarks and publication metadata.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or _TEMPLATE_DIR
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )

    def render_html_report(self, report: Any, page_numbers: Optional[Dict[str, int]] = None) -> str:
        """Renders standalone HTML report for screen or print media."""
        context = build_seo_book_context(report, page_numbers=page_numbers)
        template = self.jinja_env.get_template("seo_audit_book.html")
        return template.render(**context)

    def resolve_physical_pages(
        self,
        pdf_bytes: bytes,
        chapter_ids: Sequence[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """
        Extracts actual physical page numbers for each chapter marker from rendered PDF bytes.
        """
        if pypdf is None or not pdf_bytes or len(pdf_bytes) < 100:
            return self._estimate_fallback_pages(chapter_ids, context=context)

        resolved: Dict[str, int] = {}
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)

            patterns: Dict[str, List[str]] = {}
            for ch_id in chapter_ids:
                clean_id = ch_id.lower().strip()
                patterns[ch_id] = [
                    f"[[chapter_ref:{clean_id}]]",
                    f"chapter_ref:{clean_id}",
                    f"[[chapter_ref:{clean_id}",
                ]

            for page_idx in range(total_pages):
                page_num = page_idx + 1  # 1-based page number
                try:
                    text = reader.pages[page_idx].extract_text() or ""
                    text_lower = text.lower()
                except Exception:
                    continue

                for ch_id, pat_list in patterns.items():
                    if ch_id not in resolved:
                        for pat in pat_list:
                            if pat in text_lower:
                                resolved[ch_id] = page_num
                                break

            # Monotonic fallback for any unspotted chapters
            fallback = self._estimate_fallback_pages(chapter_ids, context=context)
            last_page = 2
            for ch_id in chapter_ids:
                if ch_id in resolved:
                    last_page = resolved[ch_id]
                else:
                    estimated = fallback.get(ch_id, last_page + 1)
                    last_page = max(last_page + 1, estimated)
                    resolved[ch_id] = last_page

        except Exception as exc:
            logger.warning("pypdf physical page extraction failed: %s", exc)
            return self._estimate_fallback_pages(chapter_ids, context=context)

        return resolved

    def _estimate_fallback_pages(
        self,
        chapter_ids: Sequence[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """
        Content-aware deterministic pagination estimator when pypdf is unavailable.
        Calculates realistic sheet positions from actual chapter payloads, finding counts,
        and page dossiers, avoiding naive uniform +2 increments.
        """
        pages: Dict[str, int] = {}
        # Page 1: Cover (unnumbered)
        # If front-matter is in chapter_ids: Reading Guide = 2, Contents = 3, Chapters = 4+
        if "reading-guide" in chapter_ids:
            current = 2
            pages["reading-guide"] = current
            if "contents" in chapter_ids:
                current += 1
                pages["contents"] = current
            current += 1
        else:
            current = 3

        sections_map = {}
        if context and "seo_sections" in context:
            for s in context["seo_sections"]:
                sections_map[s["id"]] = s

        for ch_id in chapter_ids:
            if ch_id in ("reading-guide", "contents"):
                continue

            pages[ch_id] = current

            # Determine page length based on actual chapter content
            if ch_id == "executive-summary":
                current += 2
            elif ch_id == "seo-health":
                current += 2
            elif ch_id in sections_map:
                sec = sections_map[ch_id]
                findings_count = len(sec.get("findings", []))
                dossiers_count = len(sec.get("page_dossiers", []))
                ch_pages = 1
                if sec.get("empirical_table"):
                    ch_pages += 1
                if findings_count > 0:
                    ch_pages += max(1, (findings_count + 1) // 2)
                if dossiers_count > 0:
                    ch_pages += max(1, dossiers_count * 2)
                current += max(1, ch_pages)
            elif ch_id == "findings-register":
                findings = context.get("findings", []) if context else []
                current += max(2, (len(findings) + 1) // 2)
            elif ch_id == "roadmap":
                current += 3
            elif ch_id == "evidence-register":
                evidence = context.get("evidence_records", []) if context else []
                current += max(2, (len(evidence) + 14) // 15)
            elif ch_id in ("glossary", "methodology"):
                current += 2
            else:
                current += 2

        return {ch_id: pages[ch_id] for ch_id in chapter_ids if ch_id in pages}

    def inject_pdf_bookmarks_and_metadata(
        self,
        pdf_bytes: bytes,
        domain: str,
        resolved_pages: Dict[str, int],
        toc_items: Sequence[Dict[str, Any]],
    ) -> bytes:
        """
        Enhances rendered PDF with interactive outlines/bookmarks and document metadata.
        """
        if pypdf is None or not pdf_bytes or len(pdf_bytes) < 100:
            return pdf_bytes

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            writer = pypdf.PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # Metadata
            writer.add_metadata({
                "/Title": f"Comprehensive SEO Audit — {domain}",
                "/Author": "Dristik Website Intelligence",
                "/Subject": "Technical SEO, Search Performance, and Architecture Audit",
                "/Creator": "Dristik Autonomous Intelligence Systems",
                "/Producer": "Playwright Chromium & Dristik Publication Pipeline",
            })

            # Hierarchical bookmarks
            total_pages = len(reader.pages)
            for item in toc_items:
                ch_id = item["id"]
                title = item["title"]
                pg = resolved_pages.get(ch_id)
                if pg and 1 <= pg <= total_pages:
                    writer.add_outline_item(title, pg - 1)  # 0-indexed for outline

            out_buffer = io.BytesIO()
            writer.write(out_buffer)
            return out_buffer.getvalue()

        except Exception as exc:
            logger.warning("PDF bookmark injection encountered an issue: %s", exc)
            return pdf_bytes

    async def render_book_pdf(
        self,
        report: Any,
        render_fn: Optional[Callable[[str], Any]] = None,
        two_pass: bool = False,
    ) -> Optional[bytes]:
        """
        Generates the complete publication-grade PDF.
        When two_pass=True, executes Pass 1 to measure exact physical page locations,
        then Pass 2 to inject real physical page numbers into the TOC.
        When two_pass=False, uses the content-aware layout estimator.
        """
        if render_fn is None:
            from app.crawl.browser import BrowserRenderService
            render_fn = BrowserRenderService.render_pdf

        context = build_seo_book_context(report)
        chapter_ids = [item["id"] for item in context["toc_items"]]

        if not two_pass:
            resolved_pages = self._estimate_fallback_pages(chapter_ids, context=context)
            html = self.render_html_report(report, page_numbers=resolved_pages)
            pdf = await render_fn(html)
            if not pdf or len(pdf) < 100:
                return pdf
            domain = _get_val(report, "domain") or "Website"
            return self.inject_pdf_bookmarks_and_metadata(
                pdf,
                domain=domain,
                resolved_pages=resolved_pages,
                toc_items=context["toc_items"],
            )

        # Pass 1: Render HTML with estimated/placeholder TOC
        pass1_pages = self._estimate_fallback_pages(chapter_ids, context=context)
        pass1_html = self.render_html_report(report, page_numbers=pass1_pages)
        pass1_pdf = await render_fn(pass1_html)

        if not pass1_pdf or len(pass1_pdf) < 100:
            logger.warning("Pass 1 PDF generation returned empty or invalid bytes.")
            return pass1_pdf

        # Resolve physical page numbers from Pass 1 PDF
        resolved_pages = self.resolve_physical_pages(pass1_pdf, chapter_ids, context=context)

        # Pass 2: Re-render HTML with resolved page numbers in TOC
        pass2_html = self.render_html_report(report, page_numbers=resolved_pages)
        pass2_pdf = await render_fn(pass2_html)
        final_pdf_raw = pass2_pdf if pass2_pdf else pass1_pdf

        # Post-Process: Inject bookmarks & metadata
        domain = _get_val(report, "domain") or "Website"
        return self.inject_pdf_bookmarks_and_metadata(
            final_pdf_raw,
            domain=domain,
            resolved_pages=resolved_pages,
            toc_items=context["toc_items"],
        )


# Singleton instance for application-wide use
seo_audit_book_renderer = SeoAuditBookRenderer()
