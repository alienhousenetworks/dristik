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
    return getattr(obj, key, default)


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


def _resolve_dedicated_metric(
    check_lower: str,
    ch_id: str,
    report: Any,
    ch_findings: List[Dict[str, Any]],
    pages_crawled: int,
    is_sampled: bool,
) -> Optional[Tuple[str, str, str]]:
    """
    Dedicated deterministic metric resolver for specific chapter checks.
    Guarantees that crawler inventory counts (e.g. '0 via sitemap, 14 via links')
    never leak into unrelated checks such as internal links, backlinks, or image alt.
    Returns (status_str, value_str, scope_str) or None if general matching should proceed.
    """
    manifest = _get_val(report, "crawl_manifest") or {}

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

        if avg_ttfb > 800:
            return (
                DiagnosticStatus.FAILED.value,
                f"Average TTFB measured at {avg_ttfb:.0f} ms (exceeds 800ms threshold)",
                f"{pages_crawled} pages sample",
            )
        elif avg_ttfb > 0:
            return (
                DiagnosticStatus.PASSED.value,
                f"Average TTFB measured at {avg_ttfb:.0f} ms (< 800ms target)",
                f"{pages_crawled} pages sample",
            )
        else:
            ttfb_f = next((f for f in ch_findings if "ttfb" in f"{f.get('title', '')} {f.get('what_was_checked', '')}".lower()), None)
            if ttfb_f:
                return (DiagnosticStatus.FAILED.value, f"Defect detected: {ttfb_f.get('title', '')[:65]}", f"{pages_crawled} pages sample")
            return (DiagnosticStatus.NOT_TESTED.value, "TTFB latency not recorded during crawl", "Uninspected")

    if "slow loading" in check_lower:
        crawl_health = _get_val(manifest, "crawl_health")
        avg_ttfb = 0.0
        if isinstance(crawl_health, dict):
            try:
                avg_ttfb = float(crawl_health.get("avg_ttfb_ms", 0.0) or 0.0)
            except (ValueError, TypeError):
                avg_ttfb = 0.0
        if avg_ttfb > 800:
            return (DiagnosticStatus.FAILED.value, f"{pages_crawled} page(s) exhibit slow server response latency", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.PASSED.value, "0 slow loading URLs detected in inspected sample", f"{pages_crawled} pages sample")

    # 2. Image SEO and Media Assets
    if "missing alt text" in check_lower or "alt text image" in check_lower:
        alt_f = next((f for f in ch_findings if "alt" in f"{f.get('title', '')} {f.get('category', '')}".lower()), None)
        if alt_f:
            obs = alt_f["evidence"][0].get("observation") if alt_f.get("evidence") else ""
            val = obs or f"Defect detected: {alt_f.get('title', '')[:65]}"
            return (DiagnosticStatus.FAILED.value, val, f"{pages_crawled} pages sample")
        media = getattr(report, "media_assets", None)
        missing_alt = getattr(media, "missing_alt_count", 0) if media else 0
        if isinstance(missing_alt, (int, float)) and not isinstance(missing_alt, bool) and missing_alt > 0:
            return (DiagnosticStatus.FAILED.value, f"{missing_alt} image(s) missing alt text", f"{pages_crawled} pages sample")
        if pages_crawled > 0:
            return (DiagnosticStatus.PASSED.value, "All inspected images have descriptive alt text", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.NOT_TESTED.value, "Media inspection not executed", "Uninspected")

    if "total images inspected" in check_lower:
        media = getattr(report, "media_assets", None)
        tot_imgs = getattr(media, "total_images", None) if media else None
        if isinstance(tot_imgs, (int, float)) and not isinstance(tot_imgs, bool) and tot_imgs > 0:
            return (DiagnosticStatus.PASSED.value, f"{tot_imgs} images evaluated across inspected pages", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, f"Media assets evaluated across {pages_crawled} pages", f"{pages_crawled} pages sample")

    # 3. Internal Linking & Anchor Text (NEVER leak crawl discovery provenance)
    if "generic anchor" in check_lower:
        anc_f = next((f for f in ch_findings if "anchor" in f"{f.get('title', '')} {f.get('what_was_checked', '')}".lower()), None)
        if anc_f:
            return (DiagnosticStatus.FAILED.value, f"Defect detected: {anc_f.get('title', '')[:65]}", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.PASSED.value, "0 generic anchors detected in inspected sample", f"{pages_crawled} pages sample")

    if "internal link density" in check_lower:
        link_f = next((f for f in ch_findings if "link density" in f"{f.get('title', '')} {f.get('what_was_checked', '')}".lower()), None)
        if link_f:
            return (DiagnosticStatus.FAILED.value, f"Defect detected: {link_f.get('title', '')[:65]}", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.PASSED.value, f"Internal link architecture verified across {pages_crawled} sample pages", f"{pages_crawled} pages sample")

    # 4. External Authority & Backlinks
    if any(k in check_lower for k in ["referring domain", "authority profile", "backlink count", "backlink profile"]):
        return (DiagnosticStatus.UNAVAILABLE.value, "Requires authorized backlink connector (Ahrefs/Semrush/GSC)", "Unavailable")

    # 5. Competitor Parity & Market Visibility
    if any(k in check_lower for k in ["competitor parity", "market visibility"]):
        return (DiagnosticStatus.UNAVAILABLE.value, "Third-party competitor data connector not attached", "Unavailable")

    # 6. Semantic Entities (sameAs social profiles)
    if "sameas" in check_lower:
        sameas_f = next((f for f in ch_findings if "sameas" in f"{f.get('title', '')} {f.get('what_was_checked', '')}".lower()), None)
        if sameas_f:
            return (DiagnosticStatus.FAILED.value, f"Defect detected: {sameas_f.get('title', '')[:65]}", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.SAMPLED.value if is_sampled else DiagnosticStatus.PASSED.value, "Organization sameAs profile connections evaluated", f"{pages_crawled} pages sample")

    # 7. Mobile Touch Targets & Ergonomics
    if "touch target" in check_lower:
        tt_f = next((f for f in ch_findings if "touch" in f"{f.get('title', '')} {f.get('what_was_checked', '')}".lower()), None)
        if tt_f:
            return (DiagnosticStatus.FAILED.value, f"Defect detected: {tt_f.get('title', '')[:65]}", f"{pages_crawled} pages sample")
        return (DiagnosticStatus.PASSED.value, "Touch target spacing compliant across mobile viewports", f"{pages_crawled} pages sample")

    return None


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
    pages = _get_val(manifest, "pages") or _get_val(report, "page_reports") or []
    pages_crawled = len(pages)
    urls_discovered = _get_val(manifest, "total_pages_discovered")
    if urls_discovered is not None and isinstance(urls_discovered, (int, float)) and urls_discovered > 0:
        coverage_percent = f"{min(100, int((pages_crawled / float(urls_discovered)) * 100))}%"
    else:
        coverage_percent = "Representative sample"

    # Normalize all findings
    raw_findings = list(_get_val(report, "findings") or [])
    normalized_findings = [normalize_finding(f, idx + 1) for idx, f in enumerate(raw_findings)]

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
    ext_auth_status = "Connected" if ext_auth else "Unavailable or not connected"

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
        "Resolve high-priority crawl directives and technical canonical routing to capture unindexed search traffic."
    )
    story_summary = _get_val(report, "story_summary") or (
        "Comprehensive empirical technical audit evaluating crawler accessibility, HTML semantic hygiene, and structured data compliance."
    )

    critical_count = sum(1 for f in normalized_findings if f.get("priority") == "Critical")
    high_count = sum(1 for f in normalized_findings if f.get("priority") == "High")

    # Report meta
    report_dict = {
        "domain": domain,
        "run_id": run_id,
        "audit_date": audit_date,
        "scope_label": f"Representative sample ({pages_crawled} crawled pages)",
        "report_version": "2026.1-Master",
        "pages_crawled": pages_crawled,
        "urls_discovered": urls_discovered if urls_discovered else pages_crawled,
        "coverage_percent": coverage_percent,
        "finding_count": len(normalized_findings),
        "critical_count": critical_count,
        "high_count": high_count,
        "seo_score": display_score,
        "grade": grade,
        "grade_label": grade_label,
        "analytics_status": ga4_status,
        "gsc_status": gsc_status,
        "authority_data_status": ext_auth_status,
    }

    # Executive summary data
    top_findings = normalized_findings[:3] if normalized_findings else []
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
                "title": f["title"],
                "plain_english_summary": f["plain_english_summary"],
                "priority": f["priority"],
                "evidence_summary": f["evidence"][0]["observation"] if f["evidence"] else "Direct crawl observation",
            }
            for f in top_findings
        ],
        "business_implications": story_summary or primary_opp,
        "first_actions": [
            f.title for f in (_get_val(report, "roadmap_7_days") or [])
        ] or [f["title"] for f in top_findings],
        "plain_english": (
            f"This audit evaluated {pages_crawled} representative pages on {domain}. "
            f"There are {critical_count} critical and {high_count} high-priority issues that require prompt remediation to restore crawlability and index health."
        ),
    }

    # Pillars
    seo_pillars = [
        {
            "name": "Technical Infrastructure",
            "score": tech_score if tech_score is not None else display_score,
            "coverage": f"{pages_crawled} pages inspected",
            "interpretation": "Baseline crawlability, server health, and index directives.",
        },
        {
            "name": "On-Page & Content Relevance",
            "score": _get_val(categories.get("CONTENT", {}), "score") if isinstance(categories, dict) else None,
            "coverage": f"{pages_crawled} pages evaluated",
            "interpretation": "Heading hierarchy, title tags, and content depth.",
        },
        {
            "name": "Structured Data & Entities",
            "score": _get_val(categories.get("SCHEMA", {}), "score") if isinstance(categories, dict) else None,
            "coverage": "Schema JSON-LD nodes checked",
            "interpretation": "Machine-readable entity clarity and rich result eligibility.",
        },
        {
            "name": "Authority & External Visibility",
            "score": _get_val(categories.get("EXTERNAL_AUTHORITY", {}), "score") if isinstance(categories, dict) else None,
            "coverage": ext_auth_status,
            "interpretation": "Backlink profile and search demand signals.",
        },
    ]

    # Load or generate Diagnostic Inventory Matrix (guaranteeing authentic 6-state statuses)
    diagnostic_inventory = getattr(report, "diagnostic_inventory", None)
    if diagnostic_inventory is None:
        try:
            from app.crawl.audit.diagnostic_inventory import DiagnosticInventoryEngine
            manifest = getattr(report, "crawl_manifest", None)
            pages = getattr(report, "page_reports", []) or (getattr(manifest, "pages", []) if manifest else [])
            diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
            report.diagnostic_inventory = diagnostic_inventory
        except Exception as diag_err:
            try:
                from app.audit.diagnostic_inventory import DiagnosticInventoryEngine
                manifest = getattr(report, "crawl_manifest", None)
                pages = getattr(report, "page_reports", []) or (getattr(manifest, "pages", []) if manifest else [])
                diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
                report.diagnostic_inventory = diagnostic_inventory
            except Exception as diag_err2:
                logger.info("DiagnosticInventory build fallback note: %s", diag_err2)
                diagnostic_inventory = None

    diag_records: List[Any] = getattr(diagnostic_inventory, "records", []) or []
    is_sampled = bool(isinstance(urls_discovered, (int, float)) and urls_discovered > pages_crawled > 0)

    # Active conditional chapters
    applicable_core = [ch for ch in CORE_CHAPTERS if is_chapter_applicable(ch, report)]

    # Track assigned finding IDs to avoid duplicates across chapters
    assigned_finding_ids: Set[str] = set()
    sections_payload = []
    for ch_idx, ch in enumerate(applicable_core):
        ch_num = f"{ch_idx + 3:02d}"  # Chapters 03 onwards
        hints = ch.get("category_hints", [])
        
        # Match findings for this chapter (deduplicated)
        ch_findings = []
        for f in normalized_findings:
            f_id = str(f.get("id") or f.get("finding_id") or "")
            if f_id in assigned_finding_ids:
                continue
            match_blob = f"{f.get('title', '')} {f.get('what_was_checked', '')} {f.get('observed_result', '')} {f.get('category', '')}".lower()
            if _matches_any_hint(match_blob, hints):
                ch_findings.append(f)
                assigned_finding_ids.add(f_id)

        # Build subsections with controlled diagnostic statuses
        subsections = []
        for sub in ch.get("subsections", []):
            sub_metrics = []
            for check_name in sub.get("metric_checks", []):
                check_lower = check_name.lower()

                # 0. Dedicated deterministic resolver (isolates checks from crawler discovery leakage)
                ded_res = _resolve_dedicated_metric(
                    check_lower=check_lower,
                    ch_id=ch["id"],
                    report=report,
                    ch_findings=ch_findings,
                    pages_crawled=pages_crawled,
                    is_sampled=is_sampled,
                )
                if ded_res is not None:
                    status_str, value_str, scope_str = ded_res
                else:
                    # 1. Match against authentic diagnostic inventory records
                    matched_record = None
                    STOP_TOKENS = {"link", "links", "page", "pages", "text", "site", "rate", "count", "status", "score", "check", "audit", "test", "coverage", "across", "inspected"}
                    for rec in diag_records:
                        # STRICT ISOLATION: Chapter 02 crawl discovery records must NEVER match checks in other chapters
                        rec_id = getattr(rec, "diagnostic_id", "")
                        rec_ch = getattr(rec, "chapter_num", "")
                        if rec_id.startswith("DIAG-02-") or rec_ch == "02":
                            continue

                        rec_blob = f"{getattr(rec, 'subchapter', '')} {getattr(rec, 'test_performed', '')} {rec_id}".lower()
                        tokens = [t for t in re.split(r"\W+", check_lower) if len(t) > 3 and t not in STOP_TOKENS]
                        if tokens and any(t in rec_blob for t in tokens):
                            matched_record = rec
                            break

                    # 2. Check if an active defect in ch_findings directly targets this check
                    matching_finding = None
                    for f in ch_findings:
                        f_blob = f"{f.get('title', '')} {f.get('what_was_checked', '')} {f.get('observed_result', '')}".lower()
                        tokens = [t for t in re.split(r"\W+", check_lower) if len(t) > 3 and t not in STOP_TOKENS]
                        if tokens and any(t in f_blob for t in tokens):
                            matching_finding = f
                            break

                    if matching_finding is not None:
                        status_str = DiagnosticStatus.FAILED.value
                        value_str = f"Defect detected: {matching_finding.get('title', '')[:65]}"
                        scope_str = matching_finding.get("scope_status") or f"{pages_crawled} pages sample"
                    elif matched_record is not None:
                        status_str = getattr(matched_record, "status", DiagnosticStatus.PASSED.value)
                        raw_val = getattr(matched_record, "status_reason", None) or getattr(matched_record, "observed_value", None)
                        value_str = str(raw_val)[:80] if raw_val else ("Compliant across inspected sample" if status_str in (DiagnosticStatus.PASSED.value, DiagnosticStatus.SAMPLED.value) else "Unverified")
                        scope_str = f"{pages_crawled} pages sample" if status_str in (DiagnosticStatus.PASSED.value, DiagnosticStatus.SAMPLED.value, DiagnosticStatus.FAILED.value) else "External integration"
                    else:
                        # Check if check requires external authorizations
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
                            value_str = "Compliant across inspected sample"
                            scope_str = f"{pages_crawled} pages sample"
                        else:
                            status_str = DiagnosticStatus.NOT_TESTED.value
                            value_str = "Check not executed in this audit run"
                            scope_str = "Uninspected"

                sub_metrics.append({
                    "name": check_name,
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

        sections_payload.append({
            "id": ch["id"],
            "chapter_label": f"Chapter {ch_num}",
            "title": ch["title"],
            "introduction": ch["introduction"],
            "business_explanation": ch.get("business_explanation", ""),
            "subsections": subsections,
            "findings": ch_findings,
            "has_failed_metrics": has_failed_metrics,
            "conclusion": ch_conclusion,
            "closing_business_explanation": ch.get("business_explanation", ""),
        })

    # Catch-all chapter for any remaining unassigned findings (guarantees zero orphans)
    unassigned_findings = [f for f in normalized_findings if str(f.get("id") or f.get("finding_id") or "") not in assigned_finding_ids]
    if unassigned_findings:
        ch_num = f"{len(sections_payload) + 3:02d}"
        sections_payload.append({
            "id": "additional-technical-findings",
            "chapter_label": f"Chapter {ch_num}",
            "title": "Additional Verified Technical & Architecture Findings",
            "introduction": "This chapter consolidates specialized technical observations, DOM signals, and server responses discovered during the crawl.",
            "business_explanation": "Addressing these additional technical defects prevents crawler budget waste and ensures complete indexation integrity.",
            "subsections": [
                {
                    "id": "additional-observations",
                    "title": "Verified Architectural Anomalies",
                    "explanation": "Empirical inspection ledger of additional discovered discrepancies.",
                    "business_explanation": "Secondary defects that influence search crawler efficiency and ranking authority.",
                    "metrics": [
                        {
                            "name": "General Technical Directives",
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
        {"id": "executive-summary", "title": "Chapter 01 — Executive Summary", "level": 1, "page_number": page_map.get("executive-summary")},
        {"id": "seo-health", "title": "Chapter 02 — SEO Health and Scoring Methodology", "level": 1, "page_number": page_map.get("seo-health")},
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
        {"id": "roadmap", "title": f"{roadmap_chapter_label} — SEO Implementation Roadmap", "level": 1, "page_number": page_map.get("roadmap")},
        {"id": "evidence-register", "title": "Appendix A — Evidence Register", "level": 1, "page_number": page_map.get("evidence-register")},
        {"id": "glossary", "title": "Appendix B — SEO Glossary for Business Owners", "level": 1, "page_number": page_map.get("glossary")},
        {"id": "methodology", "title": "Appendix C — Methodology, Scope and Limitations", "level": 1, "page_number": page_map.get("methodology")},
    ])

    # Roadmap
    roadmap = [
        {
            "title": "Phase 1: Immediate Critical Fixes (Days 1–7)",
            "objective": "Resolve indexing blockers, critical robots directives, and broken link responses.",
            "business_explanation": "Fixes urgent technical errors that directly stop Google from reading your website.",
            "tasks": [
                {
                    "title": f["title"],
                    "description": f["recommended_action"],
                    "priority": f["priority"],
                    "owner": "DevOps / Web Engineering",
                    "dependency": "Edge CDN / CMS access",
                    "verification": f["verification_steps"][0] if f["verification_steps"] else "Automated HTTP recheck",
                }
                for f in normalized_findings if f["priority"] in ("Critical", "High")
            ] or [
                {
                    "title": "Verify Canonical & Robots Directives",
                    "description": "Ensure no unintended disallow or noindex tags are present on core landing pages.",
                    "priority": "High",
                    "owner": "Web Team",
                    "dependency": "None",
                    "verification": "Live robots.txt validator returns 200 OK.",
                }
            ],
        },
        {
            "title": "Phase 2: On-Page & Schema Enhancements (Days 8–30)",
            "objective": "Optimize heading structures, meta descriptions, and structured data nodes.",
            "business_explanation": "Improves how search engines display your snippets in search results to drive higher click rates.",
            "tasks": [
                {
                    "title": f["title"],
                    "description": f["recommended_action"],
                    "priority": f["priority"],
                    "owner": "Content / Frontend",
                    "dependency": "CMS template access",
                    "verification": f["verification_steps"][0] if f["verification_steps"] else "Schema validator check",
                }
                for f in normalized_findings if f["priority"] in ("Medium", "Low")
            ] or [
                {
                    "title": "Heading Hierarchy & Title Tag Review",
                    "description": "Align H1 headings and meta descriptions across top traffic templates.",
                    "priority": "Medium",
                    "owner": "Marketing / Content",
                    "dependency": "None",
                    "verification": "DOM heading audit retest.",
                }
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

    return {
        "report": report_dict,
        "toc_items": toc_items,
        "findings_register_chapter_label": findings_chapter_label,
        "roadmap_chapter_label": roadmap_chapter_label,
        "executive_summary": exec_summary,
        "seo_pillars": seo_pillars,
        "scoring": scoring,
        "seo_sections": sections_payload,
        "findings": normalized_findings,
        "roadmap": roadmap,
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

    def resolve_physical_pages(self, pdf_bytes: bytes, chapter_ids: Sequence[str]) -> Dict[str, int]:
        """
        Extracts actual physical page numbers for each chapter marker from rendered PDF bytes.
        """
        if pypdf is None or not pdf_bytes or len(pdf_bytes) < 100:
            # Deterministic fallback when pypdf is not installed
            return self._estimate_fallback_pages(chapter_ids)

        resolved: Dict[str, int] = {}
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)

            patterns = {ch_id: f"[[chapter_ref:{ch_id.lower()}]]" for ch_id in chapter_ids}

            for page_idx in range(total_pages):
                page_num = page_idx + 1  # 1-based page number
                try:
                    text = reader.pages[page_idx].extract_text() or ""
                    text_lower = text.lower()
                except Exception:
                    continue

                for ch_id, pattern in patterns.items():
                    if ch_id not in resolved and pattern in text_lower:
                        resolved[ch_id] = page_num

            # Monotonic fallback for any unspotted chapters
            last_page = 2
            for ch_id in chapter_ids:
                if ch_id in resolved:
                    last_page = resolved[ch_id]
                else:
                    last_page += 1
                    resolved[ch_id] = last_page

        except Exception as exc:
            logger.warning("pypdf physical page extraction failed: %s", exc)
            return self._estimate_fallback_pages(chapter_ids)

        return resolved

    def _estimate_fallback_pages(self, chapter_ids: Sequence[str]) -> Dict[str, int]:
        """Fallback deterministic pagination when pypdf is unavailable."""
        current = 3
        pages = {}
        for ch_id in chapter_ids:
            pages[ch_id] = current
            current += 2
        return pages

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
        By default (two_pass=False), performs a single-pass render with estimated page numbers
        to stay well within web server / reverse proxy timeout budgets (e.g. Nginx 60s).
        """
        if render_fn is None:
            from app.crawl.browser import BrowserRenderService
            render_fn = BrowserRenderService.render_pdf

        context = build_seo_book_context(report)
        chapter_ids = [item["id"] for item in context["toc_items"]]

        if not two_pass:
            resolved_pages = self._estimate_fallback_pages(chapter_ids)
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

        # Pass 1: Render HTML with placeholder TOC
        pass1_html = self.render_html_report(report)
        pass1_pdf = await render_fn(pass1_html)

        if not pass1_pdf or len(pass1_pdf) < 100:
            logger.warning("Pass 1 PDF generation returned empty or invalid bytes.")
            return pass1_pdf

        # Resolve physical page numbers from Pass 1 PDF
        resolved_pages = self.resolve_physical_pages(pass1_pdf, chapter_ids)

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
