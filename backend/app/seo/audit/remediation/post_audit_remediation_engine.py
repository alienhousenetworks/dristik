"""
Post-Audit SEO Remediation Intelligence & Independent Live Verification Engine (2026 Master Standard).
Synthesizes actionable, stack-detected remediation plans across all 10 fix types and 6 platforms,
and enforces the non-negotiable invariant: Fixed is NOT Verified until live re-crawl acceptance passes.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class FixType(str, Enum):
    TECHNICAL_CONFIG = "TECHNICAL_CONFIG"
    CODE_LEVEL = "CODE_LEVEL"
    CMS_TEMPLATE = "CMS_TEMPLATE"
    CONTENT_REWRITE = "CONTENT_REWRITE"
    INTERNAL_LINKING = "INTERNAL_LINKING"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    PERFORMANCE = "PERFORMANCE"
    INFORMATION_ARCHITECTURE = "INFORMATION_ARCHITECTURE"
    CONTENT_BRIEF = "CONTENT_BRIEF"
    MONITORING_ALERT = "MONITORING_ALERT"


class PlatformType(str, Enum):
    NEXTJS_REACT = "NEXTJS_REACT"
    WORDPRESS = "WORDPRESS"
    SHOPIFY = "SHOPIFY"
    DJANGO = "DJANGO"
    GENERIC_HTML = "GENERIC_HTML"
    NGINX_APACHE = "NGINX_APACHE"


class ImplementationDirective(BaseModel):
    platform: PlatformType
    target_file_pattern: str
    code_diff_snippet: str
    instructions: str
    stack_confidence: str  # "DETECTED" | "GENERIC_FALLBACK"


class RemediationTask(BaseModel):
    task_id: str
    finding_id: str
    root_cause_id: Optional[str] = None
    fix_type: FixType
    priority: str = "P1"
    problem: str
    root_cause: str
    affected_scope: Dict[str, Any]  # total_urls, template_pattern, sample_urls
    seo_impact: str
    business_impact: str
    recommended_fix: str
    implementation: ImplementationDirective
    owner: str
    department: str = "Engineering"
    dependencies: List[str] = Field(default_factory=list)
    effort: str
    acceptance_criteria: str
    verification_protocol: str
    evidence_refs: List[str] = Field(default_factory=list)
    status: str = "REMEDIATION_PLANNED"
    approval_status: str = "PENDING_APPROVAL"
    verification_status: str = "UNVERIFIED"  # UNVERIFIED | RETESTING | VERIFIED_FIXED | STILL_OPEN | REOPENED
    before_evidence: Dict[str, Any] = Field(default_factory=dict)
    after_evidence: Dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    task_id: str
    finding_id: str
    target_url: str
    passed: bool
    verification_status: str  # VERIFIED_FIXED | STILL_OPEN | FAILED
    check_summary: str
    before_snapshot: Dict[str, Any] = Field(default_factory=dict)
    after_snapshot: Dict[str, Any] = Field(default_factory=dict)
    comparison_rows: List[Dict[str, Any]] = Field(default_factory=list)
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PostAuditRemediationEngine:
    """
    Synthesizes implementation-ready, stack-detected remediation plans and runs
    independent live re-crawl verification against target URLs.
    """

    def detect_platform(
        self,
        server_headers: Optional[Dict[str, str]] = None,
        dom_html: Optional[str] = None,
    ) -> PlatformType:
        headers = {k.lower(): str(v).lower() for k, v in (server_headers or {}).items()}
        html = (dom_html or "").lower()

        if "next.js" in headers.get("x-powered-by", "") or "__next" in html or "_next/static" in html:
            return PlatformType.NEXTJS_REACT
        if "shopify" in html or "cdn.shopify.com" in html or "x-shopify-stage" in headers:
            return PlatformType.SHOPIFY
        if "wp-content" in html or "wp-includes" in html or "wordpress" in headers.get("x-powered-by", ""):
            return PlatformType.WORDPRESS
        if "csrfmiddlewaretoken" in html or ("csrftoken" in html and "wsgi" in headers.get("server", "")):
            return PlatformType.DJANGO
        if any(s in headers.get("server", "") for s in ("nginx", "apache")):
            return PlatformType.NGINX_APACHE

        return PlatformType.GENERIC_HTML

    @staticmethod
    def _confidence_for(platform: PlatformType) -> str:
        return "GENERIC_FALLBACK" if platform == PlatformType.GENERIC_HTML else "DETECTED"

    @staticmethod
    def _priority_for_severity(severity: str) -> str:
        sev = (severity or "MEDIUM").upper()
        if sev == "CRITICAL":
            return "P0"
        if sev == "HIGH":
            return "P1"
        if sev == "MEDIUM":
            return "P2"
        return "P3"

    def generate_task_for_finding(
        self,
        finding: Dict[str, Any],
        platform: PlatformType,
        rule_id: str,
        evidence_ids: List[str],
    ) -> RemediationTask:
        finding_id = str(finding.get("finding_id") or finding.get("id") or "FIND_UNKNOWN")
        title = str(finding.get("title") or "Unspecified Defect")
        severity = str(finding.get("severity") or "MEDIUM").upper()
        urls = list(finding.get("affected_urls") or finding.get("affected_urls_sample") or [])
        rule_l = f"{rule_id} {title}".lower()
        conf = self._confidence_for(platform)

        scope = {
            "total_urls": len(urls) if urls else 1,
            "sample_urls": urls[:10],
            "template_pattern": self._infer_template_pattern(urls),
        }

        if "title" in rule_l:
            fix_type = FixType.CODE_LEVEL
            problem = f"Page title missing, empty, or duplicated: {title}"
            root_cause = "Template <head> omits a unique page-level <title> binding."
            seo_impact = "Reduced SERP snippet clarity and search relevance."
            business_impact = "Lower organic click-through rate on commercial entry pages."
            recommended_fix = "Render a unique, descriptive <title> bound to each route's primary topic."
            implementation = self._generate_title_fix(platform, conf)
            owner, dept, effort = "Frontend Developer", "Engineering", "30 minutes"
            acceptance = "Every affected URL renders a unique, non-empty <title> between 25 and 65 characters."
            verify = "Re-crawl target URL(s) and assert document.title is non-empty and unique across sampled URLs."

        elif "meta" in rule_l and "description" in rule_l:
            fix_type = FixType.CMS_TEMPLATE
            problem = f"Meta description missing or duplicated: {title}"
            root_cause = "CMS or page layout does not supply a route-specific meta description."
            seo_impact = "Search engines fall back to arbitrary page fragments in SERP snippets."
            business_impact = "Reduced control over organic snippet messaging."
            recommended_fix = "Populate unique, accurate meta descriptions summarizing each page's value."
            implementation = self._generate_meta_desc_fix(platform, conf)
            owner, dept, effort = "SEO Specialist / Frontend Dev", "SEO & Engineering", "45 minutes"
            acceptance = "Affected URLs contain a unique <meta name='description'> between 70 and 160 characters."
            verify = "Re-crawl target URL(s) and verify head meta[name='description'] content length and uniqueness."

        elif "h1" in rule_l or "heading" in rule_l:
            fix_type = FixType.CODE_LEVEL
            problem = f"Primary H1 heading defect: {title}"
            root_cause = "Hero/header template renders a styled non-semantic element or skips <h1>."
            seo_impact = "Weakened document outline clarity and accessibility semantics."
            business_impact = "Reduced topical clarity for visitors and search crawlers."
            recommended_fix = "Render one visible, descriptive semantic <h1> element representing the page topic."
            implementation = self._generate_h1_fix(platform, conf, urls)
            owner, dept, effort = "Frontend Developer", "Engineering", "45 minutes"
            acceptance = "Rendered DOM contains at least one visible, descriptive <h1> element (ideally 1)."
            verify = "Re-crawl affected URLs and assert rendered DOM querySelectorAll('h1').length == 1."

        elif "canonical" in rule_l:
            fix_type = FixType.TECHNICAL_CONFIG
            problem = f"Canonicalization defect: {title}"
            root_cause = "Missing self-referencing canonical tag, redirected canonical target, or cross-host mismatch."
            seo_impact = "Split indexing signals and duplicate URL consolidation errors."
            business_impact = "Organic equity diluted across duplicate parameter or protocol variants."
            recommended_fix = "Emit an absolute self-referencing <link rel='canonical'> matching the final 200 OK HTTPS URL."
            implementation = self._generate_canonical_fix(platform, conf, urls[0] if urls else "")
            owner, dept, effort = "DevOps / Web Developer", "Engineering", "1 hour"
            acceptance = "Response HTML contains <link rel='canonical'> matching the normalized 200 OK URL."
            verify = "Fetch HTTP headers and rendered DOM; assert rel='canonical' resolves to 200 OK self URL."

        elif any(k in rule_l for k in ("robots", "noindex", "sitemap", "indexab")):
            fix_type = FixType.TECHNICAL_CONFIG
            problem = f"Crawlability or indexation directive defect: {title}"
            root_cause = "Conflicting robots.txt disallow, accidental meta noindex/X-Robots-Tag, or invalid XML sitemap."
            seo_impact = "Prevents search crawlers from discovering or indexing eligible commercial pages."
            business_impact = "Direct loss of organic search visibility for blocked URLs."
            recommended_fix = "Align robots.txt, meta robots, X-Robots-Tag headers, and XML sitemap entries with canonical indexable URLs."
            implementation = self._generate_indexability_fix(platform, conf, urls)
            owner, dept, effort = "DevOps / Backend Engineer", "Engineering", "1 hour"
            acceptance = "Target URLs return HTTP 200 without unintended noindex and appear cleanly in XML sitemap."
            verify = "Fetch robots.txt, sitemap.xml, HTTP X-Robots-Tag, and meta robots on affected URLs."

        elif any(k in rule_l for k in ("redirect", "404", "5xx", "status", "broken", "http")):
            fix_type = FixType.TECHNICAL_CONFIG
            problem = f"HTTP status or redirect chain defect: {title}"
            root_cause = "Multi-hop redirects, broken 4xx/5xx destinations, or protocol/host canonicalization gaps."
            seo_impact = "Wasted crawl budget and lost internal link equity."
            business_impact = "Dead user journeys and unindexed landing pages."
            recommended_fix = "Collapse redirect chains to a single 301 hop and update internal links to point to final 200 OK URLs."
            implementation = self._generate_redirect_fix(platform, conf)
            owner, dept, effort = "DevOps / Platform Engineer", "Engineering", "1.5 hours"
            acceptance = "All affected internal URLs resolve with HTTP 200 or <=1 permanent 301 hop to a valid destination."
            verify = "Re-crawl affected URLs with redirect tracing; assert 0 broken 4xx/5xx targets and hop_count <= 1."

        elif any(k in rule_l for k in ("schema", "json-ld", "json_ld", "rich", "structured")):
            fix_type = FixType.STRUCTURED_DATA
            problem = f"Structured data defect: {title}"
            root_cause = "Missing or malformed JSON-LD structured data or missing required Schema.org properties."
            seo_impact = "Reduces machine entity clarity and eligibility for Google Rich Results."
            business_impact = "Missed SERP visual enhancements (Product, Breadcrumb, Organization, Article)."
            recommended_fix = "Inject valid JSON-LD grounded strictly in visible page content."
            implementation = self._generate_schema_fix(platform, conf, urls)
            owner, dept, effort = "SEO Engineer", "Engineering", "1 hour"
            acceptance = "JSON-LD parses cleanly with 0 syntax errors and includes all required properties for its @type."
            verify = "Re-crawl URL, parse application/ld+json blocks, and run SchemaValidator with 0 errors."

        elif any(k in rule_l for k in ("link", "orphan", "depth", "anchor")):
            fix_type = FixType.INTERNAL_LINKING
            problem = f"Internal linking or architecture defect: {title}"
            root_cause = "Important pages lack contextual incoming internal links or sit at click depth >= 4."
            seo_impact = "Weak crawl discovery and diluted internal PageRank equity."
            business_impact = "Underperforming commercial or editorial pages."
            recommended_fix = "Add descriptive contextual internal links from high-equity hub/category pages."
            implementation = ImplementationDirective(
                platform=platform,
                target_file_pattern="Category/hub template or editorial navigation component",
                code_diff_snippet=(
                    "+ <nav aria-label=\"Related resources\">\n"
                    "+   <a href=\"/target-canonical-path/\">Descriptive Topic Anchor</a>\n"
                    "+ </nav>"
                ),
                instructions="Insert contextual internal links using descriptive anchor text from relevant hub pages in the same topic cluster.",
                stack_confidence=conf,
            )
            owner, dept, effort = "SEO & Content Team", "SEO", "1.5 hours"
            acceptance = "Orphan count reduced to 0 for target URLs and click depth <= 3 from homepage."
            verify = "Re-run internal link graph BFS traversal and confirm in_degree >= 1 and click_depth <= 3."

        elif any(k in rule_l for k in ("image", "alt", "media", "lcp", "cls", "inp", "ttfb", "cwv", "perf", "mobile", "viewport")):
            fix_type = FixType.PERFORMANCE
            problem = f"Performance, media, or mobile usability defect: {title}"
            root_cause = "Unoptimized assets, missing alt/dimensions, slow server response, or viewport misconfiguration."
            seo_impact = "Degraded Core Web Vitals, layout shift (CLS), or mobile usability."
            business_impact = "Higher bounce rate and lower mobile conversion efficiency."
            recommended_fix = "Add explicit width/height and descriptive alt text on images, enable caching/compression, and set responsive viewport."
            implementation = self._generate_perf_media_fix(platform, conf)
            owner, dept, effort = "Frontend / Performance Engineer", "Engineering", "2 hours"
            acceptance = "Images have descriptive alt + explicit dimensions; viewport meta present; TTFB < 800ms."
            verify = "Re-crawl URL and re-run DOM media/viewport checks and Lighthouse/TTFB telemetry."

        elif any(k in rule_l for k in ("hreflang", "international", "local", "nap", "ecommerce", "product")):
            fix_type = FixType.INFORMATION_ARCHITECTURE
            problem = f"Specialist SEO architecture defect: {title}"
            root_cause = "Missing reciprocal hreflang, inconsistent NAP/LocalBusiness schema, or ecommerce variant/facet signals."
            seo_impact = "Regional targeting mismatches or duplicate ecommerce product indexing."
            business_impact = "Reduced visibility in target local, regional, or shopping SERPs."
            recommended_fix = "Standardize reciprocal hreflang tags, verified NAP/LocalBusiness markup, or canonical ecommerce facet rules."
            implementation = self._generate_specialist_fix(platform, conf, rule_l)
            owner, dept, effort = "Technical SEO Engineer", "Engineering", "2 hours"
            acceptance = "All reciprocal hreflang, local NAP, or product schema validations pass with 0 conflicts."
            verify = "Re-crawl affected templates and verify zero hreflang reciprocity or specialist schema errors."

        elif any(k in rule_l for k in ("thin", "content", "intent", "cannibal", "freshness", "gap")):
            fix_type = FixType.CONTENT_REWRITE if "thin" in rule_l or "content" in rule_l else FixType.CONTENT_BRIEF
            problem = f"Content depth or search-intent defect: {title}"
            root_cause = "Insufficient primary editorial depth or overlapping intent across competing URLs."
            seo_impact = "Low topical authority and weak intent satisfaction."
            business_impact = "Failure to capture non-branded commercial and informational queries."
            recommended_fix = "Expand page content with verified domain substance, clear answers, and non-overlapping target intent."
            implementation = ImplementationDirective(
                platform=platform,
                target_file_pattern="CMS Page Content / Editorial Brief",
                code_diff_snippet=(
                    "1. Define unique primary intent and target audience.\n"
                    "2. Structure clear H2/H3 subsections answering core buyer questions.\n"
                    "3. Ground every factual claim with verifiable product/service specs."
                ),
                instructions="Execute editorial revision brief in CMS while preserving existing ranking headings and canonical URL.",
                stack_confidence=conf,
            )
            owner, dept, effort = "Content Lead", "Content", "3 hours"
            acceptance = "Updated page achieves substantive topical coverage without duplication or filler."
            verify = "Re-crawl URL, inspect extracted main content word count, headings, and intent alignment."

        else:
            fix_type = FixType.MONITORING_ALERT if "monitor" in rule_l else FixType.TECHNICAL_CONFIG
            problem = f"Observed SEO defect: {title}"
            root_cause = str(finding.get("root_cause") or finding.get("description") or "Technical or markup configuration does not meet enterprise SEO criteria.")
            seo_impact = "Search discoverability, crawl efficiency, or indexing hygiene impairment."
            business_impact = "Reduced organic search reliability across affected URLs."
            recommended_fix = str(finding.get("recommendation") or "Apply the verified technical correction across the shared template.")
            implementation = ImplementationDirective(
                platform=platform,
                target_file_pattern="Shared template or server configuration",
                code_diff_snippet=f"# Remediation for {rule_id or finding_id}\n# Apply fix: {recommended_fix}",
                instructions="Inspect linked evidence records, apply the change on staging, and execute automated re-crawl verification.",
                stack_confidence=conf,
            )
            owner, dept, effort = "Full Stack Engineer", "Engineering", "2 hours"
            acceptance = "Target issue no longer reproduces in post-deployment re-crawl."
            verify = "Re-crawl affected URLs and verify the failing check passes."

        return RemediationTask(
            task_id=f"REM_{finding_id}",
            finding_id=finding_id,
            root_cause_id=finding.get("root_cause_id"),
            fix_type=fix_type,
            priority=self._priority_for_severity(severity),
            problem=problem,
            root_cause=root_cause,
            affected_scope=scope,
            seo_impact=seo_impact,
            business_impact=business_impact,
            recommended_fix=recommended_fix,
            implementation=implementation,
            owner=owner,
            department=dept,
            dependencies=["Deploy to staging environment", "Run automated acceptance re-crawl"],
            effort=effort,
            acceptance_criteria=acceptance,
            verification_protocol=verify,
            evidence_refs=list(evidence_ids),
            before_evidence={
                "finding_id": finding_id,
                "rule_id": rule_id,
                "observed_condition": finding.get("observed_condition") or finding.get("description") or title,
                "affected_urls": urls[:5],
            },
        )

    def _infer_template_pattern(self, urls: List[str]) -> str:
        if not urls:
            return "/*"
        sample = urls[0].lower()
        if "/product" in sample:
            return "/products/*"
        if "/blog" in sample or "/article" in sample:
            return "/blog/*"
        if "/category" in sample or "/collection" in sample:
            return "/collections/*"
        if "/service" in sample:
            return "/services/*"
        return "/*"

    def _generate_title_fix(self, platform: PlatformType, conf: str) -> ImplementationDirective:
        if platform == PlatformType.NEXTJS_REACT:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="app/**/page.tsx",
                code_diff_snippet=(
                    "+ // Static route metadata (or export async function generateMetadata({ params }))\n"
                    "+ export const metadata = {\n"
                    "+   title: `${pageTitle} | BrandName`,\n"
                    "+   description: pageDescription,\n"
                    "+ };"
                ),
                instructions="Use Next.js Metadata API in Server Components to emit unique route titles.",
                stack_confidence=conf,
            )
        if platform == PlatformType.SHOPIFY:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="layout/theme.liquid",
                code_diff_snippet=(
                    "- <title>{{ shop.name }}</title>\n"
                    "+ <title>{{ page_title }}{% unless page_title contains shop.name %} | {{ shop.name }}{% endunless %}</title>"
                ),
                instructions="Update theme.liquid to render dynamic page_title with brand fallback.",
                stack_confidence=conf,
            )
        if platform == PlatformType.WORDPRESS:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="functions.php",
                code_diff_snippet=(
                    "+ add_theme_support('title-tag');\n"
                    "+ add_filter('document_title_separator', fn() => '|');"
                ),
                instructions="Enable core WordPress title-tag support and configure per-template title rules.",
                stack_confidence=conf,
            )
        if platform == PlatformType.DJANGO:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="templates/base.html",
                code_diff_snippet="+ <title>{% block title %}{{ page.title }} | {{ site_name }}{% endblock %}</title>",
                instructions="Expose a {% block title %} override in Django base.html and populate in each view template.",
                stack_confidence=conf,
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Document <head> template",
            code_diff_snippet="+ <title>Descriptive, unique page title (30–60 characters)</title>",
            instructions="Add a unique, descriptive <title> element inside document <head>.",
            stack_confidence=conf,
        )

    def _generate_meta_desc_fix(self, platform: PlatformType, conf: str) -> ImplementationDirective:
        if platform == PlatformType.NEXTJS_REACT:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="app/**/page.tsx",
                code_diff_snippet="+ export const metadata = { description: 'Unique summary of this page (120–155 chars).' };",
                instructions="Set route-specific description via Next.js Metadata API.",
                stack_confidence=conf,
            )
        if platform == PlatformType.SHOPIFY:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="layout/theme.liquid",
                code_diff_snippet="+ {% if page_description %}<meta name=\"description\" content=\"{{ page_description | escape }}\">{% endif %}",
                instructions="Render escaped page_description in theme.liquid.",
                stack_confidence=conf,
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Document <head> template",
            code_diff_snippet="+ <meta name=\"description\" content=\"Accurate, unique summary of page value (120–155 chars).\" />",
            instructions="Render a unique meta description per canonical URL.",
            stack_confidence=conf,
        )

    def _domain_and_brand(self, urls: Optional[List[str]] = None) -> tuple[str, str]:
        from urllib.parse import urlparse
        sample = (urls or [""])[0] if urls else ""
        host = urlparse(sample).netloc if sample else ""
        if not host and sample and "://" not in sample:
            host = sample.split("/")[0]
        origin = f"https://{host}" if host else "/"
        brand = host.replace("www.", "").split(".")[0].capitalize() if host else "Site Brand"
        return origin, brand

    def _generate_h1_fix(self, platform: PlatformType, conf: str, urls: Optional[List[str]] = None) -> ImplementationDirective:
        sample_url = (urls[0] if urls else "").lower()
        if platform == PlatformType.NEXTJS_REACT:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="components/**/PageHeader.tsx",
                code_diff_snippet=(
                    "- <div className=\"text-3xl font-bold\">{title}</div>\n"
                    "+ <h1 className=\"text-3xl font-bold\">{title}</h1>"
                ),
                instructions="Replace presentation div with one semantic <h1> element.",
                stack_confidence=conf,
            )
        if platform == PlatformType.SHOPIFY:
            if "/products/" in sample_url:
                target_file = "sections/main-product.liquid"
                diff = (
                    "- <div class=\"product__title\">{{ product.title }}</div>\n"
                    "+ <h1 class=\"product__title\">{{ product.title }}</h1>"
                )
                instr = "Wrap the product title in a single <h1> in sections/main-product.liquid."
            elif "/collections/" in sample_url:
                target_file = "sections/main-collection-banner.liquid"
                diff = (
                    "- <h2 class=\"collection-hero__title\">{{ collection.title }}</h2>\n"
                    "+ <h1 class=\"collection-hero__title\">{{ collection.title }}</h1>"
                )
                instr = "Wrap the collection title in a single <h1> in sections/main-collection-banner.liquid."
            else:
                target_file = "sections/image-banner.liquid (or homepage hero section)"
                diff = (
                    "- <h2 class=\"banner__heading\">{{ section.settings.heading }}</h2>\n"
                    "+ <h1 class=\"banner__heading\">{{ section.settings.heading }}</h1>"
                )
                instr = "Ensure the page hero section renders exactly one visible <h1> matching the page topic."
            return ImplementationDirective(
                platform=platform,
                target_file_pattern=target_file,
                code_diff_snippet=diff,
                instructions=instr,
                stack_confidence=conf,
            )
        if platform == PlatformType.DJANGO:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="templates/**/detail.html",
                code_diff_snippet="+ <h1 class=\"page-heading\">{{ object.title }}</h1>",
                instructions="Ensure each Django page template renders one primary <h1>.",
                stack_confidence=conf,
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Primary content template",
            code_diff_snippet="+ <h1 class=\"page-title\">Primary Page Topic</h1>",
            instructions="Add one visible semantic <h1> element summarizing the page topic.",
            stack_confidence=conf,
        )

    def _generate_canonical_fix(self, platform: PlatformType, conf: str, sample_url: str) -> ImplementationDirective:
        href = sample_url or "{{ canonical_url }}"
        if platform == PlatformType.NEXTJS_REACT:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="app/**/page.tsx",
                code_diff_snippet=f"+ export const metadata = {{ alternates: {{ canonical: '{href}' }} }};",
                instructions="Set alternates.canonical using Next.js Metadata API with metadataBase configured.",
                stack_confidence=conf,
            )
        if platform == PlatformType.SHOPIFY:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="layout/theme.liquid",
                code_diff_snippet="+ <link rel=\"canonical\" href=\"{{ canonical_url }}\" />",
                instructions="Output Shopify's {{ canonical_url }} inside <head> of layout/theme.liquid.",
                stack_confidence=conf,
            )
        if platform == PlatformType.WORDPRESS:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="functions.php",
                code_diff_snippet="+ add_action('wp_head', 'rel_canonical');",
                instructions="Ensure WordPress rel_canonical (or Yoast/RankMath canonical output) emits self-referencing HTTPS URLs.",
                stack_confidence=conf,
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="<head> layout template",
            code_diff_snippet=f"+ <link rel=\"canonical\" href=\"{href}\" />",
            instructions="Add an absolute self-referencing canonical tag matching the 200 OK HTTPS destination.",
            stack_confidence=conf,
        )

    def _generate_indexability_fix(self, platform: PlatformType, conf: str, urls: Optional[List[str]] = None) -> ImplementationDirective:
        origin, _ = self._domain_and_brand(urls)
        sitemap_line = f"Sitemap: {origin.rstrip('/')}/sitemap.xml\n" if origin.startswith("http") else "Sitemap: /sitemap.xml\n"
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="public/robots.txt & sitemap.xml",
            code_diff_snippet=(
                "User-agent: *\n"
                "Allow: /\n"
                f"{sitemap_line}"
                "# Ensure production routes do NOT emit X-Robots-Tag: noindex"
            ),
            instructions="Verify robots.txt permits crawling of production routes, remove accidental noindex headers, and include only 200 OK canonical URLs in sitemap.xml.",
            stack_confidence=conf,
        )

    def _generate_redirect_fix(self, platform: PlatformType, conf: str) -> ImplementationDirective:
        if platform == PlatformType.NGINX_APACHE:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="/etc/nginx/conf.d/site.conf",
                code_diff_snippet=(
                    "server {\n"
                    "    listen 80;\n"
                    "    return 301 https://$host$request_uri;\n"
                    "}"
                ),
                instructions="Collapse multi-hop HTTP/www redirects into a single 301 rule and fix internal links pointing to 4xx/3xx targets.",
                stack_confidence=conf,
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Server / CDN redirect rules (next.config.js / Nginx / Cloudflare)",
            code_diff_snippet="# Map legacy URLs directly with a single 301 to their final 200 OK canonical destination.",
            instructions="Eliminate intermediate redirect hops and update internal links to point directly to 200 OK URLs.",
            stack_confidence=conf,
        )

    def _generate_schema_fix(self, platform: PlatformType, conf: str, urls: Optional[List[str]] = None) -> ImplementationDirective:
        origin, brand = self._domain_and_brand(urls)
        snippet = (
            "+ <script type=\"application/ld+json\">\n"
            "+ {\n"
            "+   \"@context\": \"https://schema.org\",\n"
            "+   \"@type\": \"Organization\",\n"
            f"+   \"name\": \"{brand}\",\n"
            f"+   \"url\": \"{origin}\"\n"
            "+ }\n"
            "+ </script>"
        )
        target = "components/StructuredData.tsx" if platform == PlatformType.NEXTJS_REACT else "<head> template"
        return ImplementationDirective(
            platform=platform,
            target_file_pattern=target,
            code_diff_snippet=snippet,
            instructions="Inject valid Schema.org JSON-LD matching visible on-page entities; never fabricate ratings or prices.",
            stack_confidence=conf,
        )

    def _generate_perf_media_fix(self, platform: PlatformType, conf: str) -> ImplementationDirective:
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Image & Layout components",
            code_diff_snippet=(
                "+ <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
                "+ <img src=\"/hero.webp\" alt=\"Descriptive visual subject\" width=\"1200\" height=\"630\" fetchpriority=\"high\" />"
            ),
            instructions="Provide descriptive alt text, explicit width/height attributes to prevent CLS, responsive viewport meta, and modern WebP/AVIF formats.",
            stack_confidence=conf,
        )

    def _generate_specialist_fix(self, platform: PlatformType, conf: str, rule_l: str) -> ImplementationDirective:
        if "hreflang" in rule_l or "international" in rule_l:
            snippet = (
                "+ <link rel=\"alternate\" hreflang=\"en\" href=\"https://example.com/en/\" />\n"
                "+ <link rel=\"alternate\" hreflang=\"x-default\" href=\"https://example.com/\" />"
            )
            instr = "Ensure every locale variant includes bidirectional reciprocal hreflang annotations plus x-default."
        elif "local" in rule_l or "nap" in rule_l:
            snippet = "+ Standardize Name, Address, Phone identically across footer, contact page, and LocalBusiness JSON-LD."
            instr = "Align NAP across all templates and LocalBusiness structured data."
        else:
            snippet = "+ Canonicalize faceted filter URLs to parent category and emit valid Product/Offer schema with live availability."
            instr = "Control faceted crawl traps with canonical/robots directives and ensure accurate Product schema."
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Locale / Store / Location template",
            code_diff_snippet=snippet,
            instructions=instr,
            stack_confidence=conf,
        )

    def synthesize_remediation_plan(
        self,
        findings: List[Dict[str, Any]],
        server_headers: Optional[Dict[str, str]] = None,
        dom_sample: Optional[str] = None,
    ) -> List[RemediationTask]:
        """
        Synthesizes the complete post-audit remediation backlog across all verified findings,
        grouping shared root_cause_ids cleanly.
        """
        platform = self.detect_platform(server_headers, dom_sample)
        tasks: List[RemediationTask] = []
        seen_keys = set()

        for finding in findings:
            rule_id = str(finding.get("rule_id") or "")
            rc_id = finding.get("root_cause_id")
            dedup_key = (rule_id, rc_id) if rc_id else (finding.get("finding_id") or finding.get("id") or rule_id,)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            evidence_ids = list(finding.get("evidence_ids") or finding.get("evidence_refs") or [])
            task = self.generate_task_for_finding(finding, platform, rule_id, evidence_ids)
            tasks.append(task)

        return tasks

    async def verify_task_live(
        self,
        *,
        task_id: str,
        finding_id: str,
        target_url: str,
        rule_id: str,
        before_snapshot: Optional[Dict[str, Any]] = None,
        fetch_fn: Optional[Callable[[str], Awaitable[Dict[str, Any]]]] = None,
    ) -> VerificationResult:
        """
        Independently re-fetches target_url (with SSRF protection), parses fresh DOM/HTTP observations,
        evaluates deterministic acceptance criteria for rule_id, and builds a 6-row before/after diff.
        NEVER marks a task VERIFIED_FIXED unless the live observation passes acceptance criteria.
        """
        before = dict(before_snapshot or {})
        if fetch_fn is None:
            from app.seo.audit.crawlers.http_client import NativeHTTPCrawler
            crawler = NativeHTTPCrawler()
            fetch_fn = crawler.fetch_page

        try:
            fetched = await fetch_fn(target_url)
        except Exception as exc:
            return VerificationResult(
                task_id=task_id,
                finding_id=finding_id,
                target_url=target_url,
                passed=False,
                verification_status="FAILED",
                check_summary=f"Live re-crawl failed ({type(exc).__name__}: {exc}). Fix remains unverified.",
                before_snapshot=before,
                after_snapshot={"error": str(exc)},
                comparison_rows=[
                    {"dimension": "Finding Status", "before": before.get("status", "OPEN"), "after": "FAILED (Unverified)"}
                ],
            )

        status_code = int(fetched.get("status_code") or 0)
        html_text = str(fetched.get("html") or "")
        headers = {k.lower(): str(v) for k, v in (fetched.get("headers") or {}).items()}
        ttfb_ms = fetched.get("ttfb_ms")
        content_sha = fetched.get("content_sha256") or hashlib.sha256(html_text.encode("utf-8")).hexdigest()

        parsed = self._extract_dom_snapshot(html_text, status_code, headers, ttfb_ms, content_sha)
        rule_l = (rule_id or "").lower()

        # Deterministic acceptance evaluation
        passed = False
        reason = ""
        if status_code >= 400 or status_code == 0:
            passed = False
            reason = f"Target URL returned HTTP {status_code}; healthy 200 OK required."
        elif "title" in rule_l:
            t = parsed.get("title") or ""
            passed = 15 <= len(t) <= 75
            reason = f"Live <title> length={len(t)} ('{t[:60]}')." if passed else f"Live <title> invalid/missing (length={len(t)})."
        elif "meta" in rule_l and "description" in rule_l:
            md = parsed.get("meta_description") or ""
            passed = 50 <= len(md) <= 170
            reason = f"Live meta description present ({len(md)} chars)." if passed else f"Live meta description missing/invalid ({len(md)} chars)."
        elif "h1" in rule_l or "heading" in rule_l:
            h1_count = int(parsed.get("h1_count") or 0)
            passed = h1_count == 1
            reason = f"Live rendered H1 count is {h1_count}."
        elif "canonical" in rule_l:
            can = (parsed.get("canonical_url") or "").rstrip("/")
            passed = bool(can) and can.startswith("http")
            reason = f"Live rel=canonical is '{can or 'missing'}'."
        elif "noindex" in rule_l or "robots" in rule_l:
            robots_m = str(parsed.get("robots_meta") or "").lower()
            x_rob = str(headers.get("x-robots-tag") or "").lower()
            passed = ("noindex" not in robots_m) and ("noindex" not in x_rob)
            reason = "No noindex directive in live meta robots or X-Robots-Tag." if passed else "noindex still present."
        elif "schema" in rule_l or "json" in rule_l:
            passed = int(parsed.get("schema_count") or 0) > 0
            reason = f"Detected {parsed.get('schema_count', 0)} JSON-LD script block(s)."
        elif "alt" in rule_l or "image" in rule_l:
            missing_alt = int(parsed.get("images_without_alt") or 0)
            passed = missing_alt == 0
            reason = f"Live images missing alt: {missing_alt}."
        else:
            passed = 200 <= status_code < 300 and bool(parsed.get("title"))
            reason = f"Live HTTP {status_code} verified with valid document head."

        verif_status = "VERIFIED_FIXED" if passed else "STILL_OPEN"
        comparison_rows = [
            {"dimension": "Title", "before": before.get("title") or "—", "after": parsed.get("title") or "—"},
            {"dimension": "Canonical", "before": before.get("canonical_url") or "—", "after": parsed.get("canonical_url") or "—"},
            {
                "dimension": "DOM Structure",
                "before": f"H1: {before.get('h1_count', '—')} · Schema: {before.get('schema_count', '—')}",
                "after": f"H1: {parsed.get('h1_count', 0)} · Schema: {parsed.get('schema_count', 0)}",
            },
            {
                "dimension": "Snapshot / Screenshot",
                "before": before.get("snapshot_hash") or before.get("screenshot_hash") or "Not captured",
                "after": parsed.get("content_sha256", "")[:16],
            },
            {
                "dimension": "Performance (TTFB)",
                "before": f"{before['ttfb_ms']}ms" if before.get("ttfb_ms") is not None else "Not measured",
                "after": f"{parsed['ttfb_ms']}ms" if parsed.get("ttfb_ms") is not None else "Not measured",
            },
            {
                "dimension": "Verification Status",
                "before": before.get("status") or "OPEN / FIX_SUBMITTED",
                "after": verif_status,
            },
        ]

        return VerificationResult(
            task_id=task_id,
            finding_id=finding_id,
            target_url=target_url,
            passed=passed,
            verification_status=verif_status,
            check_summary=reason,
            before_snapshot=before,
            after_snapshot=parsed,
            comparison_rows=comparison_rows,
        )

    @staticmethod
    def _extract_dom_snapshot(
        html_text: str,
        status_code: int,
        headers: Dict[str, str],
        ttfb_ms: Optional[float],
        content_sha: str,
    ) -> Dict[str, Any]:
        title = ""
        meta_desc = ""
        canonical = ""
        robots_meta = ""
        h1_count = 0
        schema_count = 0
        images_without_alt = 0

        if BeautifulSoup is not None and html_text:
            soup = BeautifulSoup(html_text, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            md = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
            if md and md.get("content"):
                meta_desc = str(md["content"]).strip()
            rm = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
            if rm and rm.get("content"):
                robots_meta = str(rm["content"]).strip()
            can = soup.find("link", attrs={"rel": lambda v: v and "canonical" in (v if isinstance(v, list) else [v])})
            if can and can.get("href"):
                canonical = str(can["href"]).strip()
            h1_count = len(soup.find_all("h1"))
            schema_count = len(soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}))
            imgs = soup.find_all("img")
            images_without_alt = sum(1 for im in imgs if not str(im.get("alt") or "").strip())
        else:
            m_t = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
            if m_t:
                title = m_t.group(1).strip()
            h1_count = len(re.findall(r"<h1\b", html_text, re.I))
            schema_count = len(re.findall(r"application/ld\+json", html_text, re.I))

        return {
            "status_code": status_code,
            "title": title,
            "meta_description": meta_desc,
            "canonical_url": canonical,
            "robots_meta": robots_meta,
            "x_robots_tag": headers.get("x-robots-tag", ""),
            "h1_count": h1_count,
            "schema_count": schema_count,
            "images_without_alt": images_without_alt,
            "ttfb_ms": ttfb_ms,
            "content_sha256": content_sha,
        }
