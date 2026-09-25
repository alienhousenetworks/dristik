"""
Dristik AI Universal Patch Engine
Transforms audit findings and business profiles into typed RemediationPatch specifications.
Classifies all patches into 3 deterministic risk tiers:
- Level 1: SAFE_AUTO (Non-destructive: JSON-LD Schema, Canonical, standard robots.txt)
- Level 2: HUMAN_APPROVAL (Editorial/Brand review: Title rewrites, Meta description, Hero copy, FAQ)
- Level 3: DEVELOPER_REQUIRED (Code/Architecture: Next.js layout.tsx, Server security headers, routing)
"""
import json
import re
from typing import List, Dict, Any, Optional
from app.domain.models import (
    Finding,
    RemediationPatch,
    BusinessProfile,
    CommercialQueryEvaluation,
)
from app.domain.enums import (
    Category,
    Severity,
    PatchRiskLevel,
    PatchOperation,
    PatchApprovalStatus,
    VerificationStatus,
)

class UniversalPatchEngine:
    """
    Universal Patch Engine that normalizes fixes across CMSs and repositories.
    """

    def generate_patches(
        self,
        findings: List[Finding],
        business_profile: Optional[BusinessProfile] = None,
        website_url: str = "https://example.com",
        commercial_evals: Optional[List[CommercialQueryEvaluation]] = None,
    ) -> List[RemediationPatch]:
        patches: List[RemediationPatch] = []
        biz_name = (
            business_profile.business_name
            if business_profile and business_profile.business_name and business_profile.business_name not in ["Unknown", "Unknown Business"]
            else "Target Company"
        )
        niche = (
            business_profile.niche
            if business_profile and business_profile.niche
            else "Enterprise SaaS & Solutions"
        )
        val_prop = (
            business_profile.value_proposition
            if business_profile and business_profile.value_proposition
            else "Enterprise website intelligence and AI search readiness platform."
        )

        # Track finding IDs addressed
        addressed_finding_ids = set()

        # 1. Evaluate Findings
        for idx, finding in enumerate(findings):
            patch = self._patch_from_finding(
                finding=finding,
                biz_name=biz_name,
                niche=niche,
                val_prop=val_prop,
                website_url=website_url,
                idx=idx + 1,
            )
            if patch:
                patches.append(patch)
                addressed_finding_ids.add(finding.finding_id)

        # 2. Ensure Core Essential Universal Patches exist if not covered
        # A. Organization JSON-LD (Level 1 - Safe Auto)
        if not any("organization" in p.title.lower() or "schema" in p.title.lower() for p in patches):
            org_schema = {
                "@context": "https://schema.org",
                "@type": "Organization",
                "@id": f"{website_url.rstrip('/')}/#organization",
                "name": biz_name,
                "url": website_url,
                "description": val_prop,
                "sameAs": [
                    f"https://www.linkedin.com/company/{biz_name.lower().replace(' ', '')}",
                    f"https://twitter.com/{biz_name.lower().replace(' ', '')}",
                ],
            }
            patches.append(
                RemediationPatch(
                    patch_id=f"PATCH-{len(patches)+1:03d}",
                    finding_id="F-SCHEMA-ORG",
                    title="Inject Schema.org Organization Graph",
                    category=Category.SCHEMA,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_url=website_url,
                    target_file="index.html (<head>) or app/layout.tsx",
                    operation=PatchOperation.UPDATE_JSONLD,
                    before_snippet="<!-- No structured Organization JSON-LD found in DOM -->",
                    after_snippet=f'<script type="application/ld+json">\n{json.dumps(org_schema, indent=2)}\n</script>',
                    explanation="Directly declares entity authority to search crawlers and AI search answer engines.",
                    confidence=0.98,
                    approval_status=PatchApprovalStatus.APPROVED,  # Safe auto pre-approved
                    metadata_payload={"schema_type": "Organization", "jsonld": org_schema},
                )
            )

        # B. Meta & Canonical (Level 1 - Safe Auto)
        if not any("canonical" in p.title.lower() or "opengraph" in p.title.lower() for p in patches):
            clean_desc = (val_prop[:155] if len(val_prop) >= 140 else f"{val_prop.strip('.')} — Built for modern teams. Discover solutions.").strip()[:158]
            og_block = (
                f'<link rel="canonical" href="{website_url}" />\n'
                f'<meta name="description" content="{clean_desc}" />\n'
                f'<meta property="og:title" content="{biz_name} — {niche}" />\n'
                f'<meta property="og:description" content="{clean_desc}" />\n'
                f'<meta property="og:url" content="{website_url}" />\n'
                f'<meta name="twitter:card" content="summary_large_image" />'
            )
            patches.append(
                RemediationPatch(
                    patch_id=f"PATCH-{len(patches)+1:03d}",
                    finding_id="F-META-CANONICAL",
                    title="Inject Canonical URL & OpenGraph Social Meta Tags",
                    category=Category.TECHNICAL_SEO,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_url=website_url,
                    target_file="index.html (<head>)",
                    operation=PatchOperation.INSERT_HEAD,
                    before_snippet="<!-- Incomplete or unverified canonical & OpenGraph headers -->",
                    after_snippet=og_block,
                    explanation="Enforces single canonical URL authority and standardizes link snippets across social & search.",
                    confidence=0.96,
                    approval_status=PatchApprovalStatus.APPROVED,
                    metadata_payload={"canonical": website_url, "meta_desc": clean_desc},
                )
            )

        # C. AI Search Directives (Level 1 - Safe Auto)
        if not any("robots" in p.title.lower() for p in patches):
            robots_txt = (
                f"User-agent: *\n"
                f"Allow: /\n\n"
                f"# Explicit permissions for AI Research & Search Crawlers\n"
                f"User-agent: GPTBot\n"
                f"Allow: /\n\n"
                f"User-agent: PerplexityBot\n"
                f"Allow: /\n\n"
                f"User-agent: ClaudeBot\n"
                f"Allow: /\n\n"
                f"User-agent: Google-Extended\n"
                f"Allow: /\n\n"
                f"Sitemap: {website_url.rstrip('/')}/sitemap.xml\n"
            )
            patches.append(
                RemediationPatch(
                    patch_id=f"PATCH-{len(patches)+1:03d}",
                    finding_id="F-ROBOTS-AI",
                    title="Allow AI Search Engine Crawlers in robots.txt",
                    category=Category.AI_SEARCH,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_url=f"{website_url.rstrip('/')}/robots.txt",
                    target_file="public/robots.txt",
                    operation=PatchOperation.APPEND_ROBOTS,
                    before_snippet="# Default or restrictive robots.txt",
                    after_snippet=robots_txt,
                    explanation="Ensures Perplexity, ChatGPT, and Claude crawlers are explicitly welcomed for real-time citation.",
                    confidence=0.99,
                    approval_status=PatchApprovalStatus.APPROVED,
                    metadata_payload={"file": "robots.txt", "content": robots_txt},
                )
            )

        # D. Character-Safe Hero Headline (Level 2 - Human Approval Required)
        patches.append(
            RemediationPatch(
                patch_id=f"PATCH-{len(patches)+1:03d}",
                finding_id="F-COPY-HERO",
                title=f"Editorial Hero Headline & Value Proposition for {biz_name}",
                category=Category.UX_CONVERSION,
                risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                target_url=website_url,
                target_file="src/components/Hero.tsx or index.html (hero section)",
                operation=PatchOperation.REPLACE,
                before_snippet=f"<h1>Welcome to {biz_name}</h1>\n<p>We provide great digital services.</p>",
                after_snippet=(
                    f'<h1 class="hero-title">The Definitive {niche} for Modern Teams</h1>\n'
                    f'<p class="hero-subhead">{biz_name} delivers {val_prop.strip(".")}. '
                    f'Experience verified intelligence, zero operational drag, and immediate business ROI.</p>'
                ),
                explanation="Enhances 5-second visitor clarity and aligns the main above-the-fold value proposition with ICP.",
                confidence=0.92,
                approval_status=PatchApprovalStatus.PENDING,
                metadata_payload={"headline_word_count": 9, "subhead_word_count": 21},
            )
        )

        # E. Next.js App Router Metadata Module (Level 3 - Developer Required)
        patches.append(
            RemediationPatch(
                patch_id=f"PATCH-{len(patches)+1:03d}",
                finding_id="F-DEV-NEXTJS",
                title="Next.js App Router Root Metadata & Dynamic OpenGraph",
                category=Category.TECHNICAL_SEO,
                risk_level=PatchRiskLevel.DEVELOPER_REQUIRED,
                target_url=website_url,
                target_file="src/app/layout.tsx",
                operation=PatchOperation.UPDATE_FILE,
                before_snippet="// export const metadata: Metadata = { title: 'Create Next App' }",
                after_snippet=self._generate_nextjs_metadata_code(biz_name, niche, val_prop, website_url),
                explanation="Implements type-safe Next.js metadata API to handle SSR meta tags and prevent client-side hydration drops.",
                confidence=0.94,
                approval_status=PatchApprovalStatus.PENDING,
                metadata_payload={"framework": "Next.js", "target_path": "src/app/layout.tsx"},
            )
        )

        # F. Server Security & Caching Headers (Level 3 - Developer Required)
        patches.append(
            RemediationPatch(
                patch_id=f"PATCH-{len(patches)+1:03d}",
                finding_id="F-DEV-SECURITY-HEADERS",
                title="Strict Enterprise Security & Cache-Control Headers",
                category=Category.TECHNICAL_SEO,
                risk_level=PatchRiskLevel.DEVELOPER_REQUIRED,
                target_url=website_url,
                target_file="next.config.js or nginx.conf",
                operation=PatchOperation.UPDATE_FILE,
                before_snippet="// missing security headers in server response",
                after_snippet=(
                    "// Security Headers Configuration\n"
                    "const securityHeaders = [\n"
                    "  { key: 'X-Content-Type-Options', value: 'nosniff' },\n"
                    "  { key: 'X-Frame-Options', value: 'DENY' },\n"
                    "  { key: 'X-XSS-Protection', value: '1; mode=block' },\n"
                    "  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },\n"
                    "  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' }\n"
                    "];"
                ),
                explanation="Hardens website against clickjacking, MIME-sniffing, and satisfies Enterprise security audit requirements.",
                confidence=0.95,
                approval_status=PatchApprovalStatus.PENDING,
                metadata_payload={"headers_count": 5},
            )
        )

        return patches

    def _patch_from_finding(
        self,
        finding: Finding,
        biz_name: str,
        niche: str,
        val_prop: str,
        website_url: str,
        idx: int,
    ) -> Optional[RemediationPatch]:
        cat = finding.category
        title_lower = finding.title.lower()
        desc_lower = finding.description.lower()

        # Schema finding -> Level 1 Safe Auto
        if cat == Category.SCHEMA or "schema" in title_lower or "json-ld" in desc_lower:
            schema_sample = {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": biz_name,
                "url": website_url,
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": f"{website_url.rstrip('/')}/search?q={{search_term_string}}",
                    "query-input": "required name=search_term_string",
                },
            }
            return RemediationPatch(
                patch_id=f"PATCH-{idx:03d}",
                finding_id=finding.finding_id,
                title=f"Resolve Schema Issue: {finding.title[:50]}",
                category=Category.SCHEMA,
                risk_level=PatchRiskLevel.SAFE_AUTO,
                target_url=website_url,
                target_file="index.html",
                operation=PatchOperation.UPDATE_JSONLD,
                before_snippet=finding.evidence[0].snippet if finding.evidence else "<!-- Invalid or missing schema -->",
                after_snippet=f'<script type="application/ld+json">\n{json.dumps(schema_sample, indent=2)}\n</script>',
                explanation=finding.recommendation or "Injects verified valid Schema.org microdata to address finding.",
                confidence=0.97,
                approval_status=PatchApprovalStatus.APPROVED,
                metadata_payload={"finding_ref": finding.finding_id},
            )

        # Meta/Technical finding -> Level 1 or 2
        if cat in [Category.TECHNICAL_SEO, Category.ON_PAGE_SEO]:
            if "title" in title_lower or "h1" in title_lower:
                return RemediationPatch(
                    patch_id=f"PATCH-{idx:03d}",
                    finding_id=finding.finding_id,
                    title=f"Copy Fix: {finding.title[:50]}",
                    category=cat,
                    risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                    target_url=website_url,
                    target_file="index.html",
                    operation=PatchOperation.REPLACE,
                    before_snippet=finding.evidence[0].snippet if finding.evidence else "<title>Unoptimized Title</title>",
                    after_snippet=f"<title>{biz_name} — Enterprise {niche} Platform</title>",
                    explanation=finding.recommendation or "Optimizes page title character density to 50-60 compliant length.",
                    confidence=0.93,
                    approval_status=PatchApprovalStatus.PENDING,
                    metadata_payload={"finding_ref": finding.finding_id},
                )
            else:
                return RemediationPatch(
                    patch_id=f"PATCH-{idx:03d}",
                    finding_id=finding.finding_id,
                    title=f"Technical Fix: {finding.title[:50]}",
                    category=cat,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_url=website_url,
                    target_file="index.html",
                    operation=PatchOperation.INSERT_HEAD,
                    before_snippet=finding.evidence[0].snippet if finding.evidence else "<!-- Missing technical tag -->",
                    after_snippet=f'<meta name="robots" content="index, follow, max-image-preview:large" />',
                    explanation=finding.recommendation or "Ensures indexability and crawler compliance.",
                    confidence=0.96,
                    approval_status=PatchApprovalStatus.APPROVED,
                    metadata_payload={"finding_ref": finding.finding_id},
                )

        # UX / Copywriting -> Level 2
        if cat in [Category.CONTENT, Category.UX_CONVERSION]:
            return RemediationPatch(
                patch_id=f"PATCH-{idx:03d}",
                finding_id=finding.finding_id,
                title=f"Content Polish: {finding.title[:50]}",
                category=cat,
                risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                target_url=website_url,
                target_file="index.html",
                operation=PatchOperation.REPLACE,
                before_snippet=finding.evidence[0].snippet if finding.evidence else "<!-- Vague copy -->",
                after_snippet=f'<p class="value-prop">{val_prop}</p>',
                explanation=finding.recommendation or "Clarifies conversion copy and value proposition.",
                confidence=0.90,
                approval_status=PatchApprovalStatus.PENDING,
                metadata_payload={"finding_ref": finding.finding_id},
            )

        return None

    def _generate_nextjs_metadata_code(self, biz_name: str, niche: str, val_prop: str, url: str) -> str:
        clean_desc = val_prop[:155].replace('"', '\\"')
        return f"""import type {{ Metadata }} from 'next';

export const metadata: Metadata = {{
  title: '{biz_name} — {niche}',
  description: '{clean_desc}',
  metadataBase: new URL('{url}'),
  alternates: {{
    canonical: '/',
  }},
  openGraph: {{
    title: '{biz_name} — {niche}',
    description: '{clean_desc}',
    url: '{url}',
    siteName: '{biz_name}',
    locale: 'en_US',
    type: 'website',
  }},
  robots: {{
    index: true,
    follow: true,
    googleBot: {{
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    }},
  }},
}};
"""

patch_engine = UniversalPatchEngine()
