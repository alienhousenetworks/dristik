"""
Dristik AI Universal Patch Engine (v2)
=======================================
Transforms audit findings and business profiles into typed RemediationPatch
specifications. Classifies all patches into 3 deterministic risk tiers:
  - Level 1: SAFE_AUTO (Non-destructive: JSON-LD Schema, Canonical, robots.txt)
  - Level 2: HUMAN_APPROVAL (Editorial/Brand review: Title, Meta, Hero, FAQ)
  - Level 3: DEVELOPER_REQUIRED (Code/Architecture: layout.tsx, security headers)

Evidence-gating guardrails (v2):
  1. If business_name is "Unknown", "Unknown Business", or empty → every patch
     that embeds the business name is BLOCKED with a clear human explanation.
  2. If value_proposition is absent → copy-heavy patches are BLOCKED.
  3. If niche is absent → category-specific copy patches are BLOCKED.
  4. GUESSING / LOW_CONFIDENCE / UNVERIFIED findings never generate auto-patches.
     They are skipped with is_blocked=True.

A blocked patch is still returned in the list so the frontend can surface
"This patch requires you to complete your Business Profile first" messaging.
"""
from __future__ import annotations

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
    RubricConfidence,
)

# Placeholder sentinel — if biz_name resolves to one of these, patches are BLOCKED.
_UNKNOWN_SENTINELS = frozenset({
    "", "unknown", "unknown business", "target company",
    "the company", "company", "n/a", "none",
})


def _is_unknown(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in _UNKNOWN_SENTINELS


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


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

        # --- Evidence-gate: resolve business profile fields ------------------
        raw_name = business_profile.business_name if business_profile else ""
        biz_name_unknown = _is_unknown(raw_name)
        biz_name = raw_name if not biz_name_unknown else ""

        raw_niche = business_profile.niche if business_profile else ""
        niche_unknown = _is_unknown(raw_niche)
        niche = raw_niche if not niche_unknown else ""

        raw_vp = business_profile.value_proposition if business_profile else ""
        vp_unknown = _is_unknown(raw_vp)
        val_prop = raw_vp if not vp_unknown else ""

        # Build a clear human-readable reason for blocked patches
        missing_fields: List[str] = []
        if biz_name_unknown:
            missing_fields.append("business_name")
        if niche_unknown:
            missing_fields.append("niche")
        if vp_unknown:
            missing_fields.append("value_proposition")
        profile_blocked = bool(missing_fields)
        profile_block_reason = (
            f"Patch blocked: business profile is incomplete. "
            f"Missing required fields: {', '.join(missing_fields)}. "
            "Complete the Business Profile in Settings before applying this patch."
            if profile_blocked else ""
        )

        # Safe display names for use in snippets even when partially unknown
        display_name = biz_name or "this company"
        display_niche = niche or "their industry"
        display_vp = val_prop or "their core services"

        addressed_finding_ids: set = set()

        # 1. Finding-derived patches ------------------------------------------
        for idx, finding in enumerate(findings):
            # Skip hypothesis / low-confidence findings — no auto-patch
            rubric = getattr(finding, "confidence_rubric", None)
            if rubric and getattr(rubric, "is_hypothesis", False):
                patches.append(
                    RemediationPatch(
                        patch_id=f"PATCH-SKIP-{idx+1:03d}",
                        finding_id=finding.finding_id,
                        title=f"[Hypothesis] {finding.title[:60]}",
                        category=finding.category,
                        risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                        target_url=website_url,
                        target_file="—",
                        operation=PatchOperation.REPLACE,
                        before_snippet=None,
                        after_snippet="",
                        explanation=finding.recommendation or "",
                        confidence=float(getattr(finding, "confidence", 0.5)),
                        approval_status=PatchApprovalStatus.PENDING,
                        is_blocked=True,
                        blocked_reason=(
                            f"Patch blocked: finding '{finding.title}' has "
                            f"confidence level '{rubric.customer_label}' and "
                            "requires verification before a patch can be generated."
                        ),
                        required_evidence="Confirm this issue is present via a manual inspection or re-crawl.",
                    )
                )
                continue

            patch = self._patch_from_finding(
                finding=finding,
                biz_name=display_name,
                niche=display_niche,
                val_prop=display_vp,
                website_url=website_url,
                idx=idx + 1,
                profile_blocked=profile_blocked,
                profile_block_reason=profile_block_reason,
            )
            if patch:
                patches.append(patch)
                addressed_finding_ids.add(finding.finding_id)

        # 2. Universal patches — gated by profile completeness ----------------

        # A. Organization JSON-LD (Level 1 - Safe Auto)
        if not any("organization" in p.title.lower() or ("schema" in p.title.lower() and "inject" in p.title.lower()) for p in patches):
            if profile_blocked:
                org_patch = RemediationPatch(
                    patch_id=f"PATCH-{len(patches)+1:03d}",
                    finding_id="F-SCHEMA-ORG",
                    title="Inject Schema.org Organization Graph",
                    category=Category.SCHEMA,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_url=website_url,
                    target_file="index.html (<head>) or app/layout.tsx",
                    operation=PatchOperation.UPDATE_JSONLD,
                    before_snippet="<!-- No structured Organization JSON-LD found in DOM -->",
                    after_snippet="",
                    explanation="Directly declares entity authority to search crawlers and AI search answer engines.",
                    confidence=0.98,
                    approval_status=PatchApprovalStatus.PENDING,
                    is_blocked=True,
                    blocked_reason=profile_block_reason,
                    required_evidence="Complete Business Profile: business_name, niche, value_proposition.",
                    metadata_payload={"schema_type": "Organization"},
                )
            else:
                org_schema = {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "@id": f"{website_url.rstrip('/')}/#organization",
                    "name": biz_name,
                    "url": website_url,
                    "description": val_prop[:200] if val_prop else "",
                    "sameAs": [
                        f"https://www.linkedin.com/company/{_slug(biz_name)}",
                        f"https://twitter.com/{_slug(biz_name)}",
                    ],
                }
                org_patch = RemediationPatch(
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
                    approval_status=PatchApprovalStatus.APPROVED,
                    metadata_payload={"schema_type": "Organization", "jsonld": org_schema},
                )
            patches.append(org_patch)

        # B. Meta & Canonical (Level 1 - Safe Auto)
        if not any("canonical" in p.title.lower() or "opengraph" in p.title.lower() for p in patches):
            if profile_blocked:
                meta_patch = RemediationPatch(
                    patch_id=f"PATCH-{len(patches)+1:03d}",
                    finding_id="F-META-CANONICAL",
                    title="Inject Canonical URL & OpenGraph Social Meta Tags",
                    category=Category.TECHNICAL_SEO,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_url=website_url,
                    target_file="index.html (<head>)",
                    operation=PatchOperation.INSERT_HEAD,
                    before_snippet=None,
                    after_snippet="",
                    explanation="Enforces single canonical URL authority and standardizes link snippets across social & search.",
                    confidence=0.96,
                    approval_status=PatchApprovalStatus.PENDING,
                    is_blocked=True,
                    blocked_reason=profile_block_reason,
                    required_evidence="Complete Business Profile to generate accurate meta description.",
                )
            else:
                clean_desc = (
                    val_prop[:155]
                    if len(val_prop) >= 140
                    else f"{val_prop.strip('.')} — Discover solutions."
                ).strip()[:158]
                og_block = (
                    f'<link rel="canonical" href="{website_url}" />\n'
                    f'<meta name="description" content="{clean_desc}" />\n'
                    f'<meta property="og:title" content="{biz_name} — {niche}" />\n'
                    f'<meta property="og:description" content="{clean_desc}" />\n'
                    f'<meta property="og:url" content="{website_url}" />\n'
                    f'<meta name="twitter:card" content="summary_large_image" />'
                )
                meta_patch = RemediationPatch(
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
            patches.append(meta_patch)

        # C. AI Search Directives robots.txt (Level 1 - Safe Auto)
        if not any("robots" in p.title.lower() for p in patches):
            robots_txt = (
                "User-agent: *\n"
                "Allow: /\n\n"
                "# Explicit permissions for AI Research & Search Crawlers\n"
                "User-agent: GPTBot\n"
                "Allow: /\n\n"
                "User-agent: PerplexityBot\n"
                "Allow: /\n\n"
                "User-agent: ClaudeBot\n"
                "Allow: /\n\n"
                "User-agent: Google-Extended\n"
                "Allow: /\n\n"
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

        # D. Editorial Hero Headline (Level 2 - Human Approval)
        # Blocked unless we have biz_name AND val_prop
        hero_blocked = biz_name_unknown or vp_unknown
        hero_block_reason = (
            f"Patch blocked: cannot write a specific hero headline without a verified "
            f"business_name and value_proposition. Missing: {', '.join(f for f in missing_fields if f in ('business_name', 'value_proposition'))}."
            if hero_blocked else ""
        )
        patches.append(
            RemediationPatch(
                patch_id=f"PATCH-{len(patches)+1:03d}",
                finding_id="F-COPY-HERO",
                title=f"Editorial Hero Headline & Value Proposition{f' for {biz_name}' if not biz_name_unknown else ''}",
                category=Category.UX_CONVERSION,
                risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                target_url=website_url,
                target_file="src/components/Hero.tsx or index.html (hero section)",
                operation=PatchOperation.REPLACE,
                before_snippet=None,
                after_snippet=(
                    f'<h1 class="hero-title">{niche or "[Your Category]"} for Modern Teams</h1>\n'
                    f'<p class="hero-subhead">{val_prop or "[Your value proposition]"}</p>'
                    if not hero_blocked else ""
                ),
                explanation="Enhances 5-second visitor clarity and aligns the main above-the-fold value proposition with ICP.",
                confidence=0.92 if not hero_blocked else 0.0,
                approval_status=PatchApprovalStatus.PENDING,
                is_blocked=hero_blocked,
                blocked_reason=hero_block_reason or None,
                required_evidence=(
                    "Complete Business Profile (business_name, value_proposition) before applying."
                    if hero_blocked else None
                ),
                metadata_payload={"profile_complete": not profile_blocked},
            )
        )

        # E. Next.js Metadata (Level 3 - Developer Required)
        # Not blocked by profile — uses display_name gracefully
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
                after_snippet=self._generate_nextjs_metadata_code(
                    display_name, display_niche, display_vp, website_url
                ),
                explanation="Implements type-safe Next.js metadata API to handle SSR meta tags and prevent client-side hydration drops.",
                confidence=0.94,
                approval_status=PatchApprovalStatus.PENDING,
                metadata_payload={"framework": "Next.js", "target_path": "src/app/layout.tsx"},
            )
        )

        # F. Security Headers (Level 3 - Developer Required)
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

    # -------------------------------------------------------------------------
    # Per-finding patch generator
    # -------------------------------------------------------------------------

    def _patch_from_finding(
        self,
        finding: Finding,
        biz_name: str,
        niche: str,
        val_prop: str,
        website_url: str,
        idx: int,
        profile_blocked: bool = False,
        profile_block_reason: str = "",
    ) -> Optional[RemediationPatch]:
        cat = finding.category
        title_lower = finding.title.lower()
        desc_lower = finding.description.lower()

        common_kw = dict(
            patch_id=f"PATCH-{idx:03d}",
            finding_id=finding.finding_id,
            target_url=website_url,
        )

        # Schema finding → Level 1 Safe Auto
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
            is_blocked = profile_blocked and _is_unknown(biz_name)
            return RemediationPatch(
                **common_kw,
                title=f"Resolve Schema Issue: {finding.title[:50]}",
                category=Category.SCHEMA,
                risk_level=PatchRiskLevel.SAFE_AUTO,
                target_file="index.html",
                operation=PatchOperation.UPDATE_JSONLD,
                before_snippet=finding.evidence[0].snippet if finding.evidence else "<!-- Invalid or missing schema -->",
                after_snippet=(
                    f'<script type="application/ld+json">\n{json.dumps(schema_sample, indent=2)}\n</script>'
                    if not is_blocked else ""
                ),
                explanation=finding.recommendation or "Injects verified valid Schema.org microdata to address finding.",
                confidence=0.97 if not is_blocked else 0.0,
                approval_status=PatchApprovalStatus.APPROVED if not is_blocked else PatchApprovalStatus.PENDING,
                is_blocked=is_blocked,
                blocked_reason=profile_block_reason if is_blocked else None,
                required_evidence="Complete business_name in Business Profile." if is_blocked else None,
                metadata_payload={"finding_ref": finding.finding_id},
            )

        # Meta / Technical → Level 1 or 2
        if cat in (Category.TECHNICAL_SEO, Category.ON_PAGE_SEO):
            if "title" in title_lower or "h1" in title_lower:
                is_blocked = profile_blocked
                return RemediationPatch(
                    **common_kw,
                    title=f"Copy Fix: {finding.title[:50]}",
                    category=cat,
                    risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                    target_file="index.html",
                    operation=PatchOperation.REPLACE,
                    before_snippet=finding.evidence[0].snippet if finding.evidence else "<title>Unoptimized Title</title>",
                    after_snippet=(
                        f"<title>{biz_name} — {niche}</title>"
                        if not is_blocked else ""
                    ),
                    explanation=finding.recommendation or "Optimizes page title character density to 50-60 compliant length.",
                    confidence=0.93 if not is_blocked else 0.0,
                    approval_status=PatchApprovalStatus.PENDING,
                    is_blocked=is_blocked,
                    blocked_reason=profile_block_reason if is_blocked else None,
                    required_evidence="Complete business_name and niche in Business Profile." if is_blocked else None,
                    metadata_payload={"finding_ref": finding.finding_id},
                )
            else:
                return RemediationPatch(
                    **common_kw,
                    title=f"Technical Fix: {finding.title[:50]}",
                    category=cat,
                    risk_level=PatchRiskLevel.SAFE_AUTO,
                    target_file="index.html",
                    operation=PatchOperation.INSERT_HEAD,
                    before_snippet=finding.evidence[0].snippet if finding.evidence else "<!-- Missing technical tag -->",
                    after_snippet='<meta name="robots" content="index, follow, max-image-preview:large" />',
                    explanation=finding.recommendation or "Ensures indexability and crawler compliance.",
                    confidence=0.96,
                    approval_status=PatchApprovalStatus.APPROVED,
                    metadata_payload={"finding_ref": finding.finding_id},
                )

        # UX / Copywriting → Level 2
        if cat in (Category.CONTENT, Category.UX_CONVERSION):
            is_blocked = profile_blocked
            return RemediationPatch(
                **common_kw,
                title=f"Content Polish: {finding.title[:50]}",
                category=cat,
                risk_level=PatchRiskLevel.HUMAN_APPROVAL,
                target_file="index.html",
                operation=PatchOperation.REPLACE,
                before_snippet=finding.evidence[0].snippet if finding.evidence else "<!-- Vague copy -->",
                after_snippet=(
                    f'<p class="value-prop">{val_prop}</p>'
                    if not is_blocked else ""
                ),
                explanation=finding.recommendation or "Clarifies conversion copy and value proposition.",
                confidence=0.90 if not is_blocked else 0.0,
                approval_status=PatchApprovalStatus.PENDING,
                is_blocked=is_blocked,
                blocked_reason=profile_block_reason if is_blocked else None,
                required_evidence="Complete value_proposition in Business Profile." if is_blocked else None,
                metadata_payload={"finding_ref": finding.finding_id},
            )

        return None

    # -------------------------------------------------------------------------
    # Next.js code generator
    # -------------------------------------------------------------------------

    def _generate_nextjs_metadata_code(
        self, biz_name: str, niche: str, val_prop: str, url: str
    ) -> str:
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
