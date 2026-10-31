"""
Dristik AI Developer Patch Pack Generator — Institutional Edition
Generates production-ready, enterprise-grade drop-in packages:
1. schema.jsonld (Complete Organization, WebSite, Service/SoftwareApplication, BreadcrumbList & FAQPage graph)
2. metadata.html (Enforced Character-Safe Title 50-60, Meta 140-160, OpenGraph, Twitter Cards, Robots Directives)
3. faq.html (Accessible Semantic HTML5 <details><summary> accordion with Schema.org microdata & responsive CSS)
4. llms.txt (Standard curated Markdown specification for Perplexity, ChatGPT, Claude, and Gemini)
5. robots.txt (Complete directives for all modern AI agents: GPTBot, PerplexityBot, ClaudeBot, Google-Extended, etc.)
6. README_DEV_INSTALL.md (Comprehensive 15-minute multi-platform guide for Next.js, React/Vite, WordPress, Webflow, Shopify)
"""
import io
import json
import zipfile
from typing import Dict, Any, List, Tuple, Optional
from app.domain.models import BusinessProfile, CommercialQueryEvaluation, CharacterSafeCopy

def generate_character_safe_copy(bp: Optional[BusinessProfile], website_url: str) -> CharacterSafeCopy:
    """Observed profile text only. A character count is not a compliance grade."""
    del website_url
    biz_name = ""
    if bp and bp.business_name and bp.business_name not in ["Unknown", "Unknown Business"]:
        biz_name = bp.business_name.strip()
    niche = (bp.niche or "").strip() if bp and bp.niche else ""
    val_prop = (bp.value_proposition or "").strip() if bp and bp.value_proposition else ""
    title = " — ".join(part for part in (biz_name, niche) if part)
    headline = biz_name
    subhead = val_prop
    total_words = len(f"{headline} {subhead}".split()) if (headline or subhead) else 0
    cta = (bp.primary_cta or "").strip() if bp and bp.primary_cta else ""
    return CharacterSafeCopy(
        title=title,
        title_char_count=len(title),
        title_status="unjudged" if title else "not_written",
        meta_description=val_prop,
        meta_char_count=len(val_prop),
        meta_status="unjudged" if val_prop else "not_written",
        hero_headline=headline,
        hero_subhead=subhead,
        hero_word_count=total_words,
        hero_status="unjudged" if total_words else "not_written",
        primary_cta=cta,
    )

def _get_canonical_qa_items(
    bp: Optional[BusinessProfile],
    website_url: str,
    commercial_evals: List[CommercialQueryEvaluation]
) -> List[Dict[str, str]]:
    """Only answers a specialist or the crawl already stored. Missing answers are omitted."""
    del bp, website_url
    items: List[Dict[str, str]] = []
    for ev in commercial_evals or []:
        answer = (ev.after_answer or ev.before_answer or "").strip()
        question = (ev.buyer_query or ev.question_title or "").strip()
        if not answer or not question:
            continue
        items.append({
            "key": ev.question_key or question,
            "question": question,
            "answer": answer,
        })
    return items

def build_patch_pack_files(
    bp: Optional[BusinessProfile],
    website_url: str,
    commercial_evals: List[CommercialQueryEvaluation]
) -> Dict[str, str]:
    clean_url = website_url.rstrip("/")
    biz_name = (
        bp.business_name
        if bp and bp.business_name and bp.business_name not in ["Unknown", "Unknown Business"]
        else "Target Enterprise"
    )
    niche = bp.niche if bp and bp.niche else "Enterprise Technology"
    val_prop = (
        bp.value_proposition
        if bp and bp.value_proposition
        else "High-performance enterprise technology platform."
    )
    audience = bp.target_audience if bp and bp.target_audience else "Enterprise Leaders & Engineers"
    copy = generate_character_safe_copy(bp, clean_url)
    qa_items = _get_canonical_qa_items(bp, clean_url, commercial_evals)

    # -------------------------------------------------------------------------
    # 1. schema.jsonld — Full Multi-Entity Graph
    # -------------------------------------------------------------------------
    faq_elements = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {
                "@type": "Answer",
                "text": item["answer"]
            }
        }
        for item in qa_items
    ]

    schema_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{clean_url}/#organization",
                "name": biz_name,
                "legalName": biz_name,
                "url": clean_url,
                "logo": {
                    "@type": "ImageObject",
                    "@id": f"{clean_url}/#logo",
                    "url": f"{clean_url}/logo.png",
                    "caption": f"{biz_name} Logo"
                },
                "image": f"{clean_url}/logo.png",
                "description": val_prop,
                "knowsAbout": [
                    niche
                ],
                "contactPoint": [
                    {
                        "@type": "ContactPoint",
                        "contactType": "customer inquiries",
                        "url": f"{clean_url}/contact",
                        "availableLanguage": ["en"]
                    }
                ]
            },
            {
                "@type": "WebSite",
                "@id": f"{clean_url}/#website",
                "url": clean_url,
                "name": biz_name,
                "description": val_prop,
                "publisher": {
                    "@id": f"{clean_url}/#organization"
                },
                "inLanguage": "en-US"
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{clean_url}/#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": clean_url
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Solutions",
                        "item": f"{clean_url}/solutions"
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": "Pricing & FAQs",
                        "item": f"{clean_url}/pricing"
                    }
                ]
            },
            {
                "@type": "FAQPage",
                "@id": f"{clean_url}/#faq",
                "isPartOf": {
                    "@id": f"{clean_url}/#website"
                },
                "mainEntity": faq_elements
            }
        ]
    }
    schema_json = json.dumps(schema_data, indent=2)

    # -------------------------------------------------------------------------
    # 2. metadata.html — Enforced Character-Safe + OpenGraph + Twitter + Robots
    # -------------------------------------------------------------------------
    metadata_html = f"""<!-- ================================================================= -->
<!-- Dristik AI Institutional Metadata Patch (Character-Safe Enforced)   -->
<!-- Title: {copy.title_char_count}/60 chars (Enforces Google SERP desktop <580px width)  -->
<!-- Meta:  {copy.meta_char_count}/160 chars (Enforces Google SERP desktop <960px width) -->
<!-- ================================================================= -->
<title>{copy.title}</title>
<meta name="description" content="{copy.meta_description}">
<link rel="canonical" href="{clean_url}">

<!-- Bot Indexing & Generative Snippet Directives -->
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta name="googlebot" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">

<!-- OpenGraph / Social Protocols -->
<meta property="og:site_name" content="{biz_name}">
<meta property="og:title" content="{copy.title}">
<meta property="og:description" content="{copy.meta_description}">
<meta property="og:url" content="{clean_url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{clean_url}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{biz_name} Platform Overview">

<!-- Twitter Card Protocols -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@{biz_name.lower().replace(' ', '')}">
<meta name="twitter:title" content="{copy.title}">
<meta name="twitter:description" content="{copy.meta_description}">
<meta name="twitter:image" content="{clean_url}/og-image.png">

<!-- Mobile Viewport & Theme Protocols -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0F172A">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{biz_name}">

<!-- Injected Schema.org Complete Entity Graph -->
<script type="application/ld+json">
{schema_json}
</script>
"""

    # -------------------------------------------------------------------------
    # 3. faq.html — Modern Semantic HTML5 Accordion with Microdata & Styling
    # -------------------------------------------------------------------------
    faq_items_html = ""
    for item in qa_items:
        faq_items_html += f"""    <details class="dristik-faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
      <summary class="dristik-faq-question" itemprop="name">
        <span>{item["question"]}</span>
        <svg class="dristik-faq-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </summary>
      <div class="dristik-faq-answer" itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
        <p itemprop="text">{item["answer"]}</p>
      </div>
    </details>\n"""

    faq_html = f"""<!-- ================================================================= -->
<!-- Dristik AI Semantic FAQ Component with Schema.org Microdata         -->
<!-- Paste directly into your Landing Page, Pricing Page, or About Page  -->
<!-- ================================================================= -->
<style>
  .dristik-faq-section {{
    max-width: 860px;
    margin: 48px auto;
    padding: 32px 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1e293b;
  }}
  .dristik-faq-header {{
    text-align: center;
    margin-bottom: 36px;
  }}
  .dristik-faq-header h2 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #0f172a;
    margin: 0 0 8px 0;
  }}
  .dristik-faq-header p {{
    font-size: 15px;
    color: #64748b;
    margin: 0;
  }}
  .dristik-faq-list {{
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .dristik-faq-item {{
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }}
  .dristik-faq-item:hover {{
    border-color: #cbd5e1;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  }}
  .dristik-faq-question {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 18px 20px;
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    cursor: pointer;
    user-select: none;
    list-style: none;
  }}
  .dristik-faq-question::-webkit-details-marker {{
    display: none;
  }}
  .dristik-faq-icon {{
    width: 20px;
    height: 20px;
    color: #64748b;
    transition: transform 0.2s ease;
    flex-shrink: 0;
    margin-left: 12px;
  }}
  .dristik-faq-item[open] .dristik-faq-icon {{
    transform: rotate(180deg);
    color: #0f172a;
  }}
  .dristik-faq-answer {{
    padding: 0 20px 20px 20px;
    font-size: 14px;
    line-height: 1.6;
    color: #475569;
    border-top: 1px solid #f1f5f9;
  }}
  .dristik-faq-answer p {{
    margin: 12px 0 0 0;
  }}
  @media (prefers-color-scheme: dark) {{
    .dristik-faq-section {{ color: #f1f5f9; }}
    .dristik-faq-header h2 {{ color: #f8fafc; }}
    .dristik-faq-header p {{ color: #94a3b8; }}
    .dristik-faq-item {{ border-color: #334155; background: #1e293b; }}
    .dristik-faq-item:hover {{ border-color: #475569; }}
    .dristik-faq-question {{ color: #f8fafc; }}
    .dristik-faq-answer {{ color: #cbd5e1; border-top-color: #334155; }}
  }}
</style>

<section class="dristik-faq-section" itemscope itemtype="https://schema.org/FAQPage">
  <div class="dristik-faq-header">
    <h2>Frequently Asked Questions About {biz_name}</h2>
    <p>Grounded answers regarding our {niche} offerings, commercial terms, and enterprise reliability.</p>
  </div>
  <div class="dristik-faq-list">
{faq_items_html}  </div>
</section>
"""

    # -------------------------------------------------------------------------
    # 4. llms.txt — Official /llms.txt Specification for AI Agents
    # -------------------------------------------------------------------------
    llms_qa_blocks = ""
    for item in qa_items:
        llms_qa_blocks += f"\n### {item['question']}\n{item['answer']}\n"

    llms_txt = f"""# {biz_name}
> {val_prop}

## Executive Summary & Core Mission
{biz_name} provides {niche} solutions engineered for {audience}. We focus on delivering {val_prop.lower().strip('.')}, removing operational friction across business workflows.

## Canonical Entity Definitions
- Official Name: {biz_name}
- Industry Niche: {niche}
- Primary Canonical Domain: {clean_url}
- Service Classification: {niche} Solutions & Services

## Target Audience & Ideal Customer Profile (ICP)
- Ideal Customer Profile: {audience}
- Primary Qualification: Organizations seeking professional {niche} solutions aligned with defined commercial requirements.

## Core Platform Architecture & Offerings
- Core Capability: {val_prop}
- Primary Action: {copy.primary_cta}

## Commercial Model & Inquiries
- Commercial Structure: Direct engagement tailored to organization scope; contact team via {clean_url} for details.

## The 6 Canonical Commercial Inquiries (Direct Grounded Answers for AI Answer Engines)
{llms_qa_blocks}
## Canonical Citation Links & URLs
- Homepage & Overview: {clean_url}
- Contact & Inquiries: {clean_url}/contact
"""

    # -------------------------------------------------------------------------
    # 5. robots.txt — Directives for Modern Generative Search & AI Agents
    # -------------------------------------------------------------------------
    robots_txt = f"""# =================================================================
# Dristik AI Answer Engine & Web Crawler Directives
# Enables Perplexity, ChatGPT, Gemini, Claude & Google to index verified entities
# =================================================================

# 1. General Web Crawlers
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/private/
Disallow: /checkout/
Disallow: /login

# 2. OpenAI Search & Model Crawlers
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

# 3. Perplexity Real-Time AI Search Engine
User-agent: PerplexityBot
Allow: /

# 4. Anthropic Claude Search Agent
User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

# 5. Google Gemini & Generative Search
User-agent: Google-Extended
Allow: /

User-agent: GoogleOther
Allow: /

# 6. Apple Intelligence Web Crawler
User-agent: Applebot-Extended
Allow: /

# 7. Cohere AI Model Crawler
User-agent: cohere-ai
Allow: /

# 8. ByteDance AI Crawler
User-agent: Bytespider
Allow: /

# 9. Common Crawl AI Training Corpus
User-agent: CCBot
Allow: /

# Sitemaps & Canonical AI Specification
Sitemap: {clean_url}/sitemap.xml
# AI Agents: Refer to {clean_url}/llms.txt for canonical entity definitions.
"""

    # -------------------------------------------------------------------------
    # 6. README_DEV_INSTALL.md — Multi-Platform 15-Minute Drop-In Recipes
    # -------------------------------------------------------------------------
    readme_md = f"""# {biz_name} — Institutional Developer Patch Pack
**Deploy time:** ~15 minutes  
**Target:** Eliminate AI Answer Engine blindness and capture high-intent commercial buyer citations in Perplexity, ChatGPT, Gemini, and Claude.

---

## 📦 What's Inside This Patch Pack

| File | Purpose | Target Destination |
| :--- | :--- | :--- |
| `schema.jsonld` | Multi-entity Schema graph (Org + WebSite + Service + FAQ) | Injected into `<head>` inside `<script type="application/ld+json">` |
| `metadata.html` | Observed title and meta text. Character counts are not a required band. | Review before replacing live `<title>` and `<meta>` tags |
| `faq.html` | Semantic HTML5 `<details><summary>` accordion with microdata | Embed inside Homepage or `/pricing` page layout |
| `llms.txt` | Standardized AI agent reference file | Upload directly to `{clean_url}/llms.txt` (in `/public/llms.txt`) |
| `robots.txt` | Directives allowing GPTBot, PerplexityBot, ClaudeBot, etc. | Append to `{clean_url}/robots.txt` |

---

## 🚀 15-Minute Multi-Platform Installation Recipes

### Option A: Next.js (App Router `app/layout.tsx`)
```tsx
import type {{ Metadata }} from 'next';

export const metadata: Metadata = {{
  title: '{copy.title}',
  description: '{copy.meta_description}',
  alternates: {{ canonical: '{clean_url}' }},
  openGraph: {{
    title: '{copy.title}',
    description: '{copy.meta_description}',
    url: '{clean_url}',
    siteName: '{biz_name}',
    images: [{{ url: '{clean_url}/og-image.png', width: 1200, height: 630 }}],
    type: 'website',
  }},
  twitter: {{
    card: 'summary_large_image',
    title: '{copy.title}',
    description: '{copy.meta_description}',
  }},
  robots: {{
    index: true,
    follow: true,
    googleBot: {{ 'max-snippet': -1, 'max-image-preview': 'large' }},
  }},
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{{{ __html: JSON.stringify({json.dumps(schema_data)}) }}}}
        />
      </head>
      <body>{{children}}</body>
    </html>
  );
}}
```

### Option B: React / Vite / Static HTML (`index.html`)
1. Open `index.html`.
2. Replace your existing `<title>` and `<meta name="description">` with the entire contents of `metadata.html` inside `<head>`.
3. Copy `llms.txt` into your `/public/` directory so it builds to `{clean_url}/llms.txt`.
4. Copy `robots.txt` into your `/public/` directory.

### Option C: WordPress & WooCommerce
1. **Metadata & Schema**: Install the **WPCode** plugin (or edit `functions.php`), and add a "Header Snippet" set to *Site Wide*:
   - Paste the contents of `metadata.html`.
2. **FAQ Accordion**: In the Gutenberg or Elementor editor on your Homepage or `/pricing` page, add a **Custom HTML** block and paste `faq.html`.
3. **llms.txt & robots.txt**: Upload `llms.txt` directly to your WordPress web root (`/public_html/llms.txt`) via FTP or File Manager.

### Option D: Webflow
1. Navigate to **Project Settings** → **Custom Code**.
2. In the **Head Code** box, paste the contents of `metadata.html`. Save and publish to selected domains.
3. On your Homepage, add an **Embed Code** element and paste `faq.html`.
4. In **Project Settings** → **SEO** → **Robots.txt**, append the lines from `robots.txt`.

### Option E: Shopify (`theme.liquid`)
1. In Shopify Admin, go to **Online Store** → **Themes** → **Edit Code**.
2. Open `layout/theme.liquid`.
3. Locate `</head>` and paste the `<script type="application/ld+json">` block from `schema.jsonld` right above it.
4. Replace existing `<title>` and `<meta name="description">` tags with the character-safe definitions from `metadata.html`.

---

## 🔍 Verification & Testing Protocol

Execute these 3 checks immediately following deployment:

1. **Google Rich Results Test**:
   - Test URL: `https://search.google.com/test/rich-results?url={clean_url}`
   - Expected verdict: Valid `FAQPage`, `Organization`, and `WebSite` structured data detected.

2. **Verify `llms.txt` Endpoint**:
   ```bash
   curl -I {clean_url}/llms.txt
   # Ensure HTTP status returns: 200 OK (Content-Type: text/plain)
   ```

3. **Perplexity Citations Verification**:
   - Query in Perplexity or ChatGPT Search: *"What is {biz_name} and how is it priced?"*
   - Verify that your brand domain appears in the citation pill links within 48-72 hours.
"""

    # -------------------------------------------------------------------------
    # 6. security_headers.conf — Nginx / Cloudflare HSTS, CSP, X-Frame-Options
    # -------------------------------------------------------------------------
    security_headers_conf = f"""# =================================================================
# Dristik AI Production Security Headers Specification (Nginx / Cloudflare)
# Prevents clickjacking, MIME-sniffing, XSS, and enforces modern HTTPS transport security
# =================================================================

add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https:;" always;
"""

    # -------------------------------------------------------------------------
    # 7. geo_definitions.html — 40-60 Word Answer-First Definition Blocks
    # -------------------------------------------------------------------------
    observed_offer = val_prop.strip() if val_prop else "No value proposition was stored. A specialist did not write a definition."
    geo_definitions_html = f"""<!-- Observed profile text only. This file is not a word-count regulation and not a citation promise. -->
<section>
  <h2>Stored offer for {biz_name}</h2>
  <p>{observed_offer}</p>
</section>
"""

    return {
        "schema.jsonld": schema_json,
        "robots.txt": robots_txt,
        "llms.txt": llms_txt,
        "security_headers.conf": security_headers_conf,
        "geo_definitions.html": geo_definitions_html,
        "metadata.html": metadata_html,
        "faq.html": faq_html,
        "README_DEV_INSTALL.md": readme_md
    }

def generate_patch_pack_zip(
    bp: Optional[BusinessProfile],
    website_url: str,
    commercial_evals: List[CommercialQueryEvaluation]
) -> bytes:
    """Creates an in-memory zip archive of the developer patch pack."""
    files = build_patch_pack_files(bp, website_url, commercial_evals)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    buffer.seek(0)
    return buffer.getvalue()

def generate_notion_block(
    bp: Optional[BusinessProfile],
    website_url: str,
    commercial_evals: List[CommercialQueryEvaluation]
) -> str:
    """Generates a clean, copyable Notion/Markdown block for project management."""
    files = build_patch_pack_files(bp, website_url, commercial_evals)
    biz_name = (
        bp.business_name
        if bp and bp.business_name and bp.business_name not in ["Unknown", "Unknown Business"]
        else "Target Enterprise"
    )

    md = f"""# 🚀 {biz_name} — Dristik AI Production Patch Pack
> Generated by Dristik AI Website Intelligence. Ready to paste into codebase, CMS, or Jira.

---

## 1. Schema.org Multi-Entity Graph (`schema.jsonld`)
```json
{files["schema.jsonld"]}
```

---

## 2. Character-Safe Metadata (<head> section)
```html
{files["metadata.html"]}
```

---

## 3. Semantic FAQ Accordion (`faq.html`)
```html
{files["faq.html"]}
```

---

## 4. `llms.txt` Standard (Publish to `/public/llms.txt`)
```markdown
{files["llms.txt"]}
```

---

## 5. `robots.txt` AI Search Crawler Directives
```text
{files["robots.txt"]}
```

---

## 6. Multi-Platform Deployment Guide
```markdown
{files["README_DEV_INSTALL.md"]}
```
"""
    return md

def generate_whatsapp_summary(
    domain: str,
    honest_scores: Any,
    what_to_ignore: str,
    top_bottleneck: str,
    top_actions: List[str],
    report_url: str = ""
) -> str:
    """Formats a clean, C-suite WhatsApp shareable 1-pager. Unmeasured scores stay unmeasured."""
    def _num(name: str):
        value = getattr(honest_scores, name, None) if honest_scores is not None else None
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _points(value):
        return "not measured" if value is None else f"{value:.0f}/100"

    h_score = _num("human_score")
    g_score = _num("google_score")
    readiness = _num("ai_readiness_score")
    if readiness is None:
        readiness = _num("on_page_proxy_score")
    visibility = _num("ai_visibility_score")
    if visibility is None:
        visibility = _num("live_ai_citation_score")
    band = getattr(honest_scores, "score_band", None) or "Not scored"
    overall = _num("overall_score")

    actions_text = "\n".join([f"• {a}" for a in top_actions[:3]]) if top_actions else "• No prioritized actions were recorded."
    ignore_text = what_to_ignore.strip() if what_to_ignore else "No ignore-list was recorded."

    return f"""*DRISTIK AI EXECUTIVE AUDIT — {domain.upper()}*
*Score:* {_points(overall)} ({band})

*HONEST SCORES:*
• *Human (5-Sec Clarity):* {_points(h_score)}
• *Google (Technical & Schema):* {_points(g_score)}
• *AI readiness (on-page):* {_points(readiness)}
• *AI visibility (live citations):* {_points(visibility)}

*⚠️ WHAT TO IGNORE THIS MONTH:*
{ignore_text}

*PRIMARY BOTTLENECK:*
{top_bottleneck or 'No primary bottleneck was recorded.'}

*PRIORITY ACTIONS:*
{actions_text}

*Deploy Patch Pack:* {report_url or 'Open Dristik Audit Deck'}"""
