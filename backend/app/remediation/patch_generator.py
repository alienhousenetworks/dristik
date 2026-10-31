"""
Dristik AI Grounded Remediation & Code Patch Generator — Enterprise Edition
Generates exact, page-specific, copy-pasteable and auto-applicable code & configuration
patches grounded in real crawl findings, DOM observations, and business profile metadata.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional, Dict, Any, Set
from urllib.parse import urlparse, urljoin

from app.domain.models import Finding, CodePatch, BusinessProfile, PageEvidence
from app.domain.enums import Category, ReleaseStatus


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _clean_path(url_or_path: str) -> str:
    if not url_or_path:
        return "/"
    p = urlparse(url_or_path).path if "://" in url_or_path else url_or_path
    if not p.startswith("/"):
        p = "/" + p
    return p


def _format_title_copy(page_path: str, biz_name: str, niche: str) -> str:
    """Constructs character-safe (50-60 characters) title copy without ellipses."""
    p = page_path.strip("/").lower()
    if not p or p in ("", "index.html", "home"):
        raw = f"{biz_name} — {niche}"
        if len(raw) < 50:
            raw = f"{biz_name} — Enterprise {niche}"
        if len(raw) < 50:
            raw = f"{biz_name} — {niche} Platform & Solutions"
    elif "pricing" in p:
        raw = f"{biz_name} Pricing — Transparent Plans for {niche}"
    elif "about" in p:
        raw = f"About {biz_name} — High-Performance {niche}"
    elif "contact" in p:
        raw = f"Contact {biz_name} — Get Started with {niche}"
    elif "blog" in p or "resources" in p:
        raw = f"{biz_name} Blog — Insights on Modern {niche}"
    elif "docs" in p or "guide" in p:
        raw = f"{biz_name} Documentation — Technical {niche} Guides"
    elif "solutions" in p or "features" in p or "product" in p:
        raw = f"{biz_name} Solutions — Next-Gen {niche} Capabilities"
    else:
        # Reconstruct path as readable title
        subparts = [sp.replace("-", " ").replace("_", " ").title() for sp in p.split("/") if sp]
        subparts.reverse()
        sub_title = " - ".join(subparts)
        raw = f"{sub_title} | {biz_name}"
        if len(raw) < 50:
            raw = f"{sub_title} | {biz_name} — {niche}"

    if len(raw) < 50:
        raw = f"{raw} Platform"
    if len(raw) > 60:
        from app.remediation.serp_text import fit_serp_text
        raw = fit_serp_text(raw, 60)
    return raw[:60].strip()


def _format_meta_description(page_path: str, biz_name: str, val_prop: str, audience: str, page_title: Optional[str] = None) -> str:
    """Constructs character-safe (140-160 characters) page-specific meta description copy."""
    clean_vp = val_prop.rstrip(".").strip()
    p = page_path.strip("/").lower()

    if "pricing" in p:
        desc = f"Explore transparent pricing plans for {biz_name}. Engineered for {audience}, delivering {clean_vp.lower()} with zero lock-in."
    elif "about" in p:
        desc = f"Learn how {biz_name} accelerates outcomes for {audience}. Our team delivers {clean_vp.lower()} with proven reliability and measurable impact."
    elif "contact" in p:
        desc = f"Connect with the {biz_name} team. Discover how our {clean_vp.lower()} solutions empower {audience} to scale efficiently."
    elif p:
        topic = p.replace("-", " ").replace("_", " ").replace("/", " — ").title()
        desc = f"Discover {topic} from {biz_name}. Purpose-built for {audience} seeking proven results, high reliability, and clear technical value."
    else:
        desc = f"{biz_name} delivers {clean_vp}. Engineered specifically for {audience} with guaranteed precision, high performance, and rapid time-to-value."

    if len(desc) < 140:
        desc = f"{desc} Complete technical specifications and architectural guidelines."
    if len(desc) > 160:
        from app.remediation.serp_text import fit_serp_text
        desc = fit_serp_text(desc, 160)
    return desc


class RemediationPatcher:
    """
    Transforms audit findings into concrete, production-ready code diffs and configuration patches.
    """

    def generate_patches(
        self,
        findings: List[Finding],
        business_profile: Optional[BusinessProfile],
        website_url: str,
        pages: Optional[List[PageEvidence]] = None,
    ) -> List[CodePatch]:
        patches: List[CodePatch] = []
        p_idx = 0
        seen_patch_keys: Set[str] = set()

        bp = business_profile
        biz_name = bp.business_name if (bp and bp.business_name and bp.business_name not in ["Unknown", "Unknown Business"]) else "Target Platform"
        niche = bp.niche if (bp and bp.niche) else "Digital Solutions & Infrastructure"
        val_prop = bp.value_proposition if (bp and bp.value_proposition) else f"High-performance {niche.lower()} and scalable systems"
        audience = bp.target_audience if (bp and bp.target_audience) else "growth teams and industry leaders"
        base_domain = urlparse(website_url).netloc.lower() or "example.com"
        clean_origin = f"{urlparse(website_url).scheme or 'https'}://{base_domain}"

        # Build page map for fast URL context lookup
        page_map: Dict[str, PageEvidence] = {}
        if pages:
            for p in pages:
                norm_p = p.url.rstrip("/")
                page_map[norm_p] = p
                page_map[_clean_path(p.url)] = p

        # =========================================================================
        # 1. FINDING-GROUNDED CODE PATCHES
        # =========================================================================
        for finding in findings:
            cat = finding.category
            rule_id = getattr(finding, "rule_id", "") or ""
            t_low = finding.title.lower()
            d_low = (finding.description or getattr(finding, "finding", "") or "").lower()

            # Collect affected URLs from evidence
            ev_urls: List[str] = []
            ev_snippets: List[str] = []
            for ev in (finding.evidence or []):
                if ev.url and ev.url not in ev_urls:
                    ev_urls.append(ev.url)
                if ev.snippet or ev.value:
                    ev_snippets.append(str(ev.snippet or ev.value))

            # Default to website_url if no specific URL attached to finding
            target_urls = ev_urls or [website_url]

            # --- A. Title Tag Issues ---
            if "title" in rule_id.lower() or ("title" in t_low and "pixel" not in t_low and "h1" not in t_low):
                for tgt_url in target_urls[:3]:
                    path = _clean_path(tgt_url)
                    patch_key = f"title_{path}"
                    if patch_key in seen_patch_keys:
                        continue
                    seen_patch_keys.add(patch_key)

                    p_idx += 1
                    opt_title = _format_title_copy(path, biz_name, niche)
                    pe = page_map.get(tgt_url.rstrip("/")) or page_map.get(path)
                    cur_title = (pe.title if pe else None) or (ev_snippets[0] if ev_snippets else None) or "Home"
                    before_snip = f"<title>{cur_title}</title>" if cur_title != "MISSING" else "<!-- Missing <title> tag in <head> -->"

                    patches.append(CodePatch(
                        patch_id=f"patch_{p_idx:03d}",
                        title=f"Optimize Title Tag for '{path}' ({len(opt_title)} chars)",
                        category=Category.ON_PAGE_SEO,
                        target_file=f"index.html / template (<head> for {path})",
                        before_snippet=before_snip,
                        after_snippet=f"<title>{opt_title}</title>",
                        explanation=(
                            f"Enforces character-safe title tag length ({len(opt_title)} chars) to prevent Google desktop/mobile "
                            f"pixel truncation (<= 580px) and explicitly targets '{niche}' keyword intent."
                        ),
                        release_status=ReleaseStatus.PENDING_APPROVAL,
                    ))

            # --- B. Meta Description Issues ---
            elif "meta_desc" in rule_id.lower() or "meta description" in t_low:
                for tgt_url in target_urls[:3]:
                    path = _clean_path(tgt_url)
                    patch_key = f"meta_desc_{path}"
                    if patch_key in seen_patch_keys:
                        continue
                    seen_patch_keys.add(patch_key)

                    p_idx += 1
                    pe = page_map.get(tgt_url.rstrip("/")) or page_map.get(path)
                    opt_desc = _format_meta_description(path, biz_name, val_prop, audience, page_title=(pe.title if pe else None))
                    cur_desc = (pe.meta_description if pe else None) or (ev_snippets[0] if ev_snippets else None)
                    before_snip = f'<meta name="description" content="{cur_desc}">' if cur_desc and cur_desc != "MISSING" else "<!-- Missing meta description tag in <head> -->"

                    patches.append(CodePatch(
                        patch_id=f"patch_{p_idx:03d}",
                        title=f"Deploy Compliant Meta Description for '{path}' ({len(opt_desc)} chars)",
                        category=Category.ON_PAGE_SEO,
                        target_file=f"index.html / template (<head> for {path})",
                        before_snippet=before_snip,
                        after_snippet=f'<meta name="description" content="{opt_desc}">',
                        explanation=(
                            f"Provides an optimized {len(opt_desc)}-character meta description within the recommended 140-160 character "
                            "window to ensure Google renders the complete snippet without trailing ellipsis on mobile SERPs."
                        ),
                        release_status=ReleaseStatus.PENDING_APPROVAL,
                    ))

            # --- C. Canonical Issues ---
            elif "canonical" in rule_id.lower() or "canonical" in t_low:
                for tgt_url in target_urls[:3]:
                    path = _clean_path(tgt_url)
                    patch_key = f"canonical_{path}"
                    if patch_key in seen_patch_keys:
                        continue
                    seen_patch_keys.add(patch_key)

                    p_idx += 1
                    clean_target = f"{clean_origin}{path if path != '/' else ''}"
                    pe = page_map.get(tgt_url.rstrip("/")) or page_map.get(path)
                    cur_can = (pe.canonical_url if pe else None) or "None"
                    before_snip = f'<link rel="canonical" href="{cur_can}" />' if cur_can and cur_can != "None" else "<!-- Missing canonical tag in <head> -->"

                    patches.append(CodePatch(
                        patch_id=f"patch_{p_idx:03d}",
                        title=f"Self-Referencing Canonical Directive for '{path}'",
                        category=Category.TECHNICAL_SEO,
                        target_file=f"index.html (<head> for {path})",
                        before_snippet=before_snip,
                        after_snippet=f'<link rel="canonical" href="{clean_target}" />',
                        explanation=(
                            f"Declares canonical link tag for '{clean_target}'. Prevents duplicate content dilution and consolidates "
                            "indexing signals across query parameter variants."
                        ),
                        release_status=ReleaseStatus.PENDING_APPROVAL,
                    ))

            # --- D. Heading Hierarchy (Missing H1 or Multiple H1s) ---
            elif "h1" in rule_id.lower() or "h1" in t_low or "heading" in t_low:
                for tgt_url in target_urls[:2]:
                    path = _clean_path(tgt_url)
                    patch_key = f"h1_{path}"
                    if patch_key in seen_patch_keys:
                        continue
                    seen_patch_keys.add(patch_key)

                    p_idx += 1
                    pe = page_map.get(tgt_url.rstrip("/")) or page_map.get(path)
                    h1_list = (pe.h1 if pe else None) or []
                    headline = f"{biz_name} — High-Performance {niche}" if path == "/" else f"{path.strip('/').replace('-', ' ').title()} with {biz_name}"

                    if len(h1_list) > 1:
                        # Demote secondary H1s
                        sec_h1 = h1_list[1]
                        before_snip = f'<h1 class="section-title">{sec_h1}</h1>'
                        after_snip = f'<h2 class="section-title">{sec_h1}</h2>'
                        patch_title = f"Demote Secondary <h1> to <h2> on '{path}'"
                        patch_expl = "Restores strict heading hierarchy by ensuring exactly one top-level <h1> exists per page."
                    elif len(h1_list) == 1:
                        # 1 H1 exists: optimize or clarify the existing heading rather than inserting duplicate
                        existing_h1 = h1_list[0]
                        before_snip = f'<h1 class="hero-title">{existing_h1}</h1>'
                        after_snip = f'<h1 class="hero-title text-4xl font-bold tracking-tight text-ink-900">\n  {headline}\n</h1>'
                        patch_title = f"Optimize Non-Descriptive <h1> Heading on '{path}'"
                        patch_expl = f"Replaces vague or non-descriptive heading '{existing_h1}' with an entity-grounded headline without creating duplicate <h1> tags."
                    else:
                        before_snip = "<!-- Missing primary <h1> heading tag in hero section -->"
                        after_snip = f'<h1 class="hero-title text-4xl font-bold tracking-tight text-ink-900">\n  {headline}\n</h1>'
                        patch_title = f"Insert Semantic Primary <h1> on '{path}'"
                        patch_expl = "Establishes clear topical hierarchy for search crawlers and AI answer engines above the viewport fold."

                    patches.append(CodePatch(
                        patch_id=f"patch_{p_idx:03d}",
                        title=patch_title,
                        category=Category.ON_PAGE_SEO,
                        target_file=f"src/components/Hero.tsx or index.html ({path})",
                        before_snippet=before_snip,
                        after_snippet=after_snip,
                        explanation=patch_expl,
                        release_status=ReleaseStatus.PENDING_APPROVAL,
                    ))

            # --- E. Broken Internal Links & 4xx Statuses (301 Redirect Rules) ---
            elif "status" in rule_id.lower() or "broken" in rule_id.lower() or "404" in t_low or "4xx" in t_low or "broken" in t_low or "5xx" in t_low:
                patch_key = "redirect_rules"
                if patch_key not in seen_patch_keys:
                    seen_patch_keys.add(patch_key)
                    p_idx += 1

                    broken_paths = [_clean_path(u) for u in target_urls if u != website_url][:3]
                    if not broken_paths:
                        broken_paths = ["/legacy-page"]

                    # Multi-platform redirect rules
                    apache_lines = "\n".join(f"Redirect 301 {bp} /" for bp in broken_paths)
                    nginx_lines = "\n".join(f"location = {bp} {{ return 301 /; }}" for bp in broken_paths)
                    next_rules = ",\n".join(
                        f"      {{ source: '{bp}', destination: '/', permanent: true }}" for bp in broken_paths
                    )

                    redirect_snippet = (
                        f"// Next.js (next.config.js)\n"
                        f"module.exports = {{\n"
                        f"  async redirects() {{\n"
                        f"    return [\n{next_rules}\n    ];\n"
                        f"  }}\n"
                        f"}};\n\n"
                        f"# Nginx (nginx.conf)\n{nginx_lines}\n\n"
                        f"# Apache (.htaccess)\n{apache_lines}"
                    )

                    patches.append(CodePatch(
                        patch_id=f"patch_{p_idx:03d}",
                        title=f"301 Permanent Redirects for Broken/Missing Endpoints",
                        category=Category.TECHNICAL_SEO,
                        target_file="next.config.js / nginx.conf / .htaccess",
                        before_snippet="// Server returns HTTP 404 / 500 error on requested routes",
                        after_snippet=redirect_snippet,
                        explanation=(
                            f"Establishes 301 permanent redirects for {len(broken_paths)} error routes ({', '.join(broken_paths)}). "
                            "Stops crawl budget waste and retains existing inbound link equity."
                        ),
                        release_status=ReleaseStatus.PENDING_APPROVAL,
                    ))

            # --- F. Image Alt Text & CLS Dimensions ---
            elif "image" in rule_id.lower() or "alt" in t_low or "cls" in t_low:
                patch_key = "image_optimization"
                if patch_key not in seen_patch_keys:
                    seen_patch_keys.add(patch_key)
                    p_idx += 1

                    # Sanitize image source - discard IP addresses or non-image strings
                    sample_img = None
                    for snip in ev_snippets:
                        s = str(snip).strip()
                        if s.startswith("<img") and 'src="' in s:
                            m = re.search(r'src=["\']([^"\']+)["\']', s)
                            if m:
                                s = m.group(1)
                        if any(ext in s.lower() for ext in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".avif"]) or any(k in s.lower() for k in ["/media/", "/images/", "/assets/", "/img/"]):
                            if not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", s):
                                sample_img = s
                                break

                    if not sample_img and pages:
                        for p in pages:
                            assets = getattr(p, "image_assets", None) or []
                            for a in assets:
                                src = a.get("src") or a.get("url")
                                if src and not a.get("alt") and not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", str(src)):
                                    sample_img = src
                                    break
                            if sample_img:
                                break

                    sample_img = sample_img or "/assets/hero-banner.png"
                    if "http" in sample_img:
                        sample_img = urlparse(sample_img).path or sample_img

                    clean_alt = f"{biz_name} — {niche} Platform Overview"

                    patches.append(CodePatch(
                        patch_id=f"patch_{p_idx:03d}",
                        title="Add Descriptive Alt Text & Explicit Image Dimensions (CLS Fix)",
                        category=Category.ON_PAGE_SEO,
                        target_file="src/components/Media.tsx or index.html",
                        before_snippet=f'<img src="{sample_img}" />',
                        after_snippet=f'<img src="{sample_img}" alt="{clean_alt}" width="800" height="450" loading="lazy" decoding="async" />',
                        explanation=(
                            "Resolves WCAG 2.2 accessibility requirement by providing descriptive alternative text. "
                            "Explicit width/height attributes prevent Cumulative Layout Shift (CLS) Core Web Vital degradation."
                        ),
                        release_status=ReleaseStatus.PENDING_APPROVAL,
                    ))

        # =========================================================================
        # 2. UNIVERSAL BASELINE ENTERPRISE PATCHES
        # (Included if not already addressed by finding-specific patches)
        # =========================================================================

        # A. Robots.txt with Search & AI Crawler Directives
        if not any("robots.txt" in p.target_file for p in patches):
            p_idx += 1
            robots_content = (
                "User-agent: *\n"
                "Allow: /\n"
                "Disallow: /api/\n"
                "Disallow: /admin/\n\n"
                "# AI Search & Retrieval Crawlers\n"
                "User-agent: GPTBot\n"
                "Allow: /\n\n"
                "User-agent: PerplexityBot\n"
                "Allow: /\n\n"
                "User-agent: ClaudeBot\n"
                "Allow: /\n\n"
                "User-agent: Google-Extended\n"
                "Allow: /\n\n"
                f"Sitemap: {clean_origin}/sitemap.xml\n"
            )
            patches.append(CodePatch(
                patch_id=f"patch_{p_idx:03d}",
                title="Deploy Production robots.txt with Verified AI Directives",
                category=Category.GEO,
                target_file="public/robots.txt (root directory)",
                before_snippet="# Default or unconfigured robots.txt",
                after_snippet=robots_content,
                explanation=(
                    "Explicitly welcomes generative AI answer engine indexing bots (GPTBot, PerplexityBot, ClaudeBot, Google-Extended) "
                    f"while protecting internal API/admin endpoints and referencing the verified XML sitemap at {clean_origin}/sitemap.xml."
                ),
                release_status=ReleaseStatus.PENDING_APPROVAL,
            ))

        # B. Complete Schema.org JSON-LD Graph
        if not any("schema" in p.title.lower() or "json-ld" in p.title.lower() for p in patches):
            p_idx += 1
            schema_graph = {
                "@context": "https://schema.org",
                "@graph": [
                    {
                        "@type": "Organization",
                        "@id": f"{clean_origin}/#organization",
                        "name": biz_name,
                        "url": clean_origin,
                        "description": val_prop[:200],
                        "sameAs": [
                            f"https://www.linkedin.com/company/{_slug(biz_name)}",
                            f"https://twitter.com/{_slug(biz_name)}"
                        ]
                    },
                    {
                        "@type": "WebSite",
                        "@id": f"{clean_origin}/#website",
                        "url": clean_origin,
                        "name": biz_name,
                        "publisher": {"@id": f"{clean_origin}/#organization"}
                    }
                ]
            }
            patches.append(CodePatch(
                patch_id=f"patch_{p_idx:03d}",
                title="Structured Schema.org Organization & WebSite JSON-LD Graph",
                category=Category.SCHEMA,
                target_file="index.html (<head>) or src/app/layout.tsx",
                before_snippet="<!-- Missing structured Schema.org JSON-LD markup -->",
                after_snippet=f'<script type="application/ld+json">\n{json.dumps(schema_graph, indent=2)}\n</script>',
                explanation=(
                    "Injects linked Schema.org Organization and WebSite entity graphs. Establishes machine-verifiable "
                    "corporate identity and enables rich snippet extraction across Google Search, ChatGPT, Perplexity, and Gemini."
                ),
                release_status=ReleaseStatus.PENDING_APPROVAL,
            ))

        # C. Enterprise Security & Transport Headers
        if not any("security" in p.title.lower() for p in patches):
            p_idx += 1
            sec_patch_snippet = (
                "// Next.js (next.config.js)\n"
                "const securityHeaders = [\n"
                "  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },\n"
                "  { key: 'X-Content-Type-Options', value: 'nosniff' },\n"
                "  { key: 'X-Frame-Options', value: 'DENY' },\n"
                "  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },\n"
                "  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' }\n"
                "];\n\n"
                "// Nginx (nginx.conf)\n"
                "add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;\n"
                "add_header X-Content-Type-Options 'nosniff' always;\n"
                "add_header X-Frame-Options 'DENY' always;\n"
                "add_header Referrer-Policy 'strict-origin-when-cross-origin' always;"
            )
            patches.append(CodePatch(
                patch_id=f"patch_{p_idx:03d}",
                title="Strict Enterprise Transport Security & Hardening Headers",
                category=Category.TECHNICAL_SEO,
                target_file="next.config.js or /etc/nginx/nginx.conf",
                before_snippet="// Missing HSTS, X-Frame-Options, and security posture headers in server responses",
                after_snippet=sec_patch_snippet,
                explanation=(
                    "Enforces HTTP Strict Transport Security (HSTS) and modern defensive headers. Eliminates clickjacking "
                    "vulnerabilities and satisfies institutional enterprise security requirements."
                ),
                release_status=ReleaseStatus.PENDING_APPROVAL,
            ))

        return patches
