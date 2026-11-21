"""
Post-Audit SEO Remediation Intelligence Engine (2026 Master Standard).
Executes as the final synthesis stage of the SEO audit workflow.

Synthesizes actionable, platform-aware remediation plans:
- 13 required canonical fields
- 10 structured fix categories
- Platform detection (Next.js, WordPress, Shopify Liquid, Django, Nginx, W3C HTML)
- Automated verification protocols (Fixed != Verified)
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    fix_type: FixType
    problem: str
    root_cause: str
    affected_scope: Dict[str, Any]  # total_urls, template_pattern, sample_urls
    seo_impact: str
    business_impact: str
    recommended_fix: str
    implementation: ImplementationDirective
    owner: str  # Developer, SEO Specialist, Content Writer, DevOps
    dependencies: List[str] = Field(default_factory=list)
    effort: str  # e.g. "30 minutes", "2 hours", "1 day"
    acceptance_criteria: str
    verification_protocol: str
    evidence_refs: List[str] = Field(default_factory=list)
    verification_status: str = "UNVERIFIED"  # UNVERIFIED | IN_PROGRESS | VERIFIED_FIXED | REOPENED


class PostAuditRemediationEngine:
    """
    Synthesizes implementation-ready, platform-aware remediation plans for all verified findings.
    """

    def detect_platform(self, server_headers: Optional[Dict[str, str]] = None, dom_html: Optional[str] = None) -> PlatformType:
        headers = {k.lower(): v.lower() for k, v in (server_headers or {}).items()}
        html = (dom_html or "").lower()

        # Next.js / Vercel detection
        if "x-powered-by" in headers and "next.js" in headers["x-powered-by"]:
            return PlatformType.NEXTJS_REACT
        if "__next" in html or "_next/static" in html:
            return PlatformType.NEXTJS_REACT

        # Shopify detection
        if "shopify" in html or "cdn.shopify.com" in html or "x-shopify-stage" in headers:
            return PlatformType.SHOPIFY

        # WordPress detection
        if "wp-content" in html or "wp-includes" in html or "wordpress" in headers.get("x-powered-by", ""):
            return PlatformType.WORDPRESS

        # Django / Python detection
        if "csrftoken" in html and "wsgi" in headers.get("server", ""):
            return PlatformType.DJANGO

        return PlatformType.GENERIC_HTML

    def generate_task_for_finding(
        self,
        finding: Dict[str, Any],
        platform: PlatformType,
        rule_id: str,
        evidence_ids: List[str],
    ) -> RemediationTask:
        finding_id = str(finding.get("finding_id") or finding.get("id") or "FIND_UNKNOWN")
        title = finding.get("title") or "Unspecified Defect"
        urls = finding.get("affected_urls") or finding.get("affected_urls_sample") or []

        scope = {
            "total_urls": len(urls) if urls else 1,
            "sample_urls": urls[:5] if urls else [],
            "template_pattern": self._infer_template_pattern(urls),
        }

        # Dispatch fix recipe based on rule_id and platform
        if "title" in rule_id.lower():
            fix_type = FixType.CODE_LEVEL
            problem = f"Page title missing or invalid: {title}"
            root_cause = "Missing or unpopulated <title> tag in page template header."
            seo_impact = "Significant CTR and ranking impairment in Google SERPs."
            business_impact = "Loss of relevant commercial search traffic and snippet clarity."
            recommended_fix = "Implement unique, descriptive page titles between 30 and 60 characters."
            implementation = self._generate_title_fix(platform)
            owner = "Frontend Developer"
            effort = "30 minutes"
            acceptance = "Every affected URL renders a unique, non-empty <title> between 30 and 60 characters."
            verify = "Trigger re-crawl; verify DOM querySelector('title').textContent meets length and uniqueness."

        elif "h1" in rule_id.lower():
            fix_type = FixType.CODE_LEVEL
            problem = f"Primary H1 heading missing or duplicated: {title}"
            root_cause = "Template layout renders non-semantic div or omits <h1> tag."
            seo_impact = "Weakened topical entity relevance and document hierarchy signaling."
            business_impact = "Impaired keyword ranking for target commercial landing pages."
            recommended_fix = "Wrap primary page headline in a single, semantic <h1> element."
            implementation = self._generate_h1_fix(platform)
            owner = "Frontend Developer"
            effort = "45 minutes"
            acceptance = "DOM contains exactly one <h1> element matching the main page topic."
            verify = "Re-crawl affected URLs; verify document.querySelectorAll('h1').length == 1."

        elif "canonical" in rule_id.lower():
            fix_type = FixType.TECHNICAL_CONFIG
            problem = f"Canonical tag defect: {title}"
            root_cause = "Canonical tag missing, pointing to redirect, or cross-domain mismatch."
            seo_impact = "Search engine index dilution and split page authority."
            business_impact = "Duplicate content indexing diluting organic rankings."
            recommended_fix = "Add self-referential canonical link tag pointing to the authoritative HTTPS URL."
            implementation = self._generate_canonical_fix(platform)
            owner = "DevOps / Web Developer"
            effort = "1 hour"
            acceptance = "Response contains <link rel='canonical' href='https://domain/canonical-url/'> matching final URL."
            verify = "Fetch HTTP headers and DOM; assert rel=canonical matches 200 OK authoritative target."

        elif "schema" in rule_id.lower():
            fix_type = FixType.STRUCTURED_DATA
            problem = f"Structured data defect: {title}"
            root_cause = "Missing required Schema.org properties or invalid JSON-LD syntax."
            seo_impact = "Ineligibility for Google Rich Results (Stars, Product snippets, FAQ badges)."
            business_impact = "Reduced SERP click-through rates compared to competitors with rich snippets."
            recommended_fix = "Inject valid, complete JSON-LD schema with all required properties."
            implementation = self._generate_schema_fix(platform)
            owner = "SEO Engineer"
            effort = "1 hour"
            acceptance = "Google Rich Results Test validator reports zero errors on target schema."
            verify = "Run SchemaValidator on re-crawled DOM; confirm 0 syntax or missing field errors."

        else:
            fix_type = FixType.TECHNICAL_CONFIG
            problem = f"Observed SEO defect: {title}"
            root_cause = "Configuration or markup does not meet enterprise technical standards."
            seo_impact = "Search performance, indexing, or crawl budget inefficiency."
            business_impact = "Organic discoverability impairment."
            recommended_fix = "Resolve the specific defect per W3C and Google Search Essentials."
            implementation = ImplementationDirective(
                platform=platform,
                target_file_pattern="Appropriate codebase or server configuration",
                code_diff_snippet="# Implement recommended fix per audit specification",
                instructions="Review finding evidence details and apply verified change.",
                stack_confidence="GENERIC_FALLBACK",
            )
            owner = "Full Stack Engineer"
            effort = "2 hours"
            acceptance = "Target issue no longer reproducible in post-deployment re-crawl."
            verify = "Re-crawl URL sample and verify check passes."

        return RemediationTask(
            task_id=f"REM_{finding_id}",
            finding_id=finding_id,
            fix_type=fix_type,
            problem=problem,
            root_cause=root_cause,
            affected_scope=scope,
            seo_impact=seo_impact,
            business_impact=business_impact,
            recommended_fix=recommended_fix,
            implementation=implementation,
            owner=owner,
            dependencies=["Deploy to staging environment", "Run acceptance re-crawl"],
            effort=effort,
            acceptance_criteria=acceptance,
            verification_protocol=verify,
            evidence_refs=evidence_ids,
        )

    def _infer_template_pattern(self, urls: List[str]) -> str:
        if not urls:
            return "/*"
        sample = urls[0]
        if "/product" in sample:
            return "/products/*"
        if "/blog" in sample or "/article" in sample:
            return "/blog/*"
        if "/category" in sample or "/collection" in sample:
            return "/collections/*"
        return "/*"

    def _generate_title_fix(self, platform: PlatformType) -> ImplementationDirective:
        if platform == PlatformType.NEXTJS_REACT:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="app/**/page.tsx or components/layout/Head.tsx",
                code_diff_snippet=(
                    "+ export const metadata = {\n"
                    "+   title: `${pageTitle} | BrandName`,\n"
                    "+   description: pageDescription,\n"
                    "+ };"
                ),
                instructions="Use Next.js Metadata API in Server Components to dynamically set page titles.",
                stack_confidence="DETECTED",
            )
        elif platform == PlatformType.SHOPIFY:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="layout/theme.liquid",
                code_diff_snippet=(
                    "+ <title>{{ page_title }} | {{ shop.name }}</title>\n"
                    "- <title>{{ shop.name }}</title>"
                ),
                instructions="Ensure theme.liquid outputs dynamic page_title liquid tags.",
                stack_confidence="DETECTED",
            )
        elif platform == PlatformType.WORDPRESS:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="functions.php",
                code_diff_snippet=(
                    "+ add_theme_support('title-tag');\n"
                    "+ add_filter('document_title_separator', fn() => '|');"
                ),
                instructions="Enable core WordPress title-tag theme support in functions.php.",
                stack_confidence="DETECTED",
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="<head> in template",
            code_diff_snippet="+ <title>Descriptive, unique title between 30 and 60 chars</title>",
            instructions="Add standard HTML <title> tag inside document <head>.",
            stack_confidence="GENERIC_FALLBACK",
        )

    def _generate_h1_fix(self, platform: PlatformType) -> ImplementationDirective:
        if platform == PlatformType.NEXTJS_REACT:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="components/**/PageHeader.tsx",
                code_diff_snippet=(
                    "- <div className=\"text-3xl font-bold\">{title}</div>\n"
                    "+ <h1 className=\"text-3xl font-bold\">{title}</h1>"
                ),
                instructions="Replace non-semantic presentation divs with a single semantic <h1>.",
                stack_confidence="DETECTED",
            )
        elif platform == PlatformType.SHOPIFY:
            return ImplementationDirective(
                platform=platform,
                target_file_pattern="sections/main-product.liquid",
                code_diff_snippet=(
                    "- <div class=\"product__title\">{{ product.title }}</div>\n"
                    "+ <h1 class=\"product__title\">{{ product.title }}</h1>"
                ),
                instructions="Wrap product title in <h1> inside main-product.liquid.",
                stack_confidence="DETECTED",
            )
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="Main content template",
            code_diff_snippet="+ <h1 class=\"page-title\">Primary Heading</h1>",
            instructions="Add exactly one <h1> heading summarizing the main page topic.",
            stack_confidence="GENERIC_FALLBACK",
        )

    def _generate_canonical_fix(self, platform: PlatformType) -> ImplementationDirective:
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="<head> layout template",
            code_diff_snippet="+ <link rel=\"canonical\" href=\"https://domain.com/canonical-path/\" />",
            instructions="Add self-referential canonical link header to prevent duplicate indexing.",
            stack_confidence="DETECTED",
        )

    def _generate_schema_fix(self, platform: PlatformType) -> ImplementationDirective:
        return ImplementationDirective(
            platform=platform,
            target_file_pattern="<head> or footer template",
            code_diff_snippet=(
                "+ <script type=\"application/ld+json\">\n"
                "+ {\n"
                "+   \"@context\": \"https://schema.org\",\n"
                "+   \"@type\": \"Organization\",\n"
                "+   \"name\": \"BrandName\",\n"
                "+   \"url\": \"https://brandname.com\"\n"
                "+ }\n"
                "+ </script>"
            ),
            instructions="Inject valid Schema.org JSON-LD markup adhering to Google Structured Data standards.",
            stack_confidence="DETECTED",
        )

    def synthesize_remediation_plan(
        self,
        findings: List[Dict[str, Any]],
        server_headers: Optional[Dict[str, str]] = None,
        dom_sample: Optional[str] = None,
    ) -> List[RemediationTask]:
        """
        Synthesizes the complete post-audit remediation backlog across all verified findings.
        """
        platform = self.detect_platform(server_headers, dom_sample)
        tasks: List[RemediationTask] = []

        for finding in findings:
            rule_id = str(finding.get("rule_id") or "")
            evidence_ids = finding.get("evidence_ids") or []
            task = self.generate_task_for_finding(finding, platform, rule_id, evidence_ids)
            tasks.append(task)

        return tasks
