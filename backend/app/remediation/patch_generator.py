"""
Dristik AI Remediation & Code Patch Generator
Generates drop-in JSON-LD schemas, OpenGraph meta tags, canonical fixes, and robots.txt directives.
"""
import json
from typing import List
from app.domain.models import Finding, CodePatch, BusinessProfile
from app.domain.enums import Category

class RemediationPatcher:
    def generate_patches(self, findings: List[Finding], business_profile: BusinessProfile, website_url: str) -> List[CodePatch]:
        patches: List[CodePatch] = []
        p_idx = 0
        
        # 1. Organization JSON-LD Schema Patch
        p_idx += 1
        org_schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": business_profile.business_name,
            "url": website_url,
            "description": business_profile.value_proposition,
            "sameAs": [
                f"https://twitter.com/{business_profile.business_name.lower().replace(' ', '')}",
                f"https://linkedin.com/company/{business_profile.business_name.lower().replace(' ', '')}"
            ]
        }
        patches.append(CodePatch(
            patch_id=f"patch_{p_idx:03d}",
            title="Complete Schema.org Organization JSON-LD Snippet",
            category=Category.SCHEMA,
            target_file="index.html (inside <head>)",
            before_snippet="<!-- Missing structured JSON-LD Organization markup -->",
            after_snippet=f'<script type="application/ld+json">\n{json.dumps(org_schema, indent=2)}\n</script>',
            explanation="Injects canonical Organization entity markup to ensure AI answer engines (ChatGPT, Perplexity, Gemini) correctly identify corporate entity relationships."
        ))
        
        # 2. OpenGraph & Meta Description Patch
        p_idx += 1
        val_prop_safe = (business_profile.value_proposition or "")[:155]
        biz_name_safe = business_profile.business_name or "Official Site"
        niche_safe = business_profile.niche or "Services"
        og_snippet = f"""<meta name="description" content="{val_prop_safe}">
<link rel="canonical" href="{website_url}">
<meta property="og:title" content="{biz_name_safe} — {niche_safe}">
<meta property="og:description" content="{val_prop_safe}">
<meta property="og:url" content="{website_url}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">"""
        
        patches.append(CodePatch(
            patch_id=f"patch_{p_idx:03d}",
            title="Essential OpenGraph, Canonical & Meta Description Tags",
            category=Category.TECHNICAL_SEO,
            target_file="index.html (<head> section)",
            before_snippet="<!-- Incomplete or unoptimized social meta tags -->",
            after_snippet=og_snippet,
            explanation="Ensures clean link previews across social platforms and protects against duplicate URL canonicalization penalties."
        ))
        
        # 3. AI-Friendly robots.txt Directives
        p_idx += 1
        robots_snippet = f"""User-agent: *
Allow: /

# Allow AI Overviews & Answer Engine Crawlers
User-agent: GPTBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: {website_url.rstrip('/')}/sitemap.xml"""

        patches.append(CodePatch(
            patch_id=f"patch_{p_idx:03d}",
            title="AI-Search Friendly robots.txt Directives",
            category=Category.GEO,
            target_file="robots.txt (root directory)",
            before_snippet="# Default or unconfigured robots.txt",
            after_snippet=robots_snippet,
            explanation="Explicitly allows and directs major generative AI indexing bots to index site knowledge without crawl barriers."
        ))
        
        return patches
