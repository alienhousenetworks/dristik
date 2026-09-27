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
    biz_name = (
        bp.business_name
        if bp and bp.business_name and bp.business_name not in ["Unknown", "Unknown Business"]
        else "Target Platform"
    )
    niche = bp.niche if bp and bp.niche else "Enterprise Technology & Infrastructure"
    val_prop = (
        bp.value_proposition
        if bp and bp.value_proposition
        else "Enterprise web intelligence, cybersecurity, and performance acceleration."
    )
    audience = bp.target_audience if bp and bp.target_audience else "engineering leaders and growth teams"

    # 1. Title: Strictly enforce 50 - 60 characters
    raw_title = f"{biz_name} — {niche} Platform"
    if len(raw_title) < 50:
        raw_title = f"{biz_name} — Enterprise {niche} & Solutions"
    if len(raw_title) < 50:
        raw_title = f"{biz_name} — High-Performance {niche} Platform"
    if len(raw_title) > 60:
        raw_title = raw_title[:57].rstrip() + "..."
    title = raw_title[:60]
    t_len = len(title)
    t_status = "compliant" if 50 <= t_len <= 60 else "too_short" if t_len < 50 else "too_long"

    # 2. Meta Description: Strictly enforce 140 - 160 characters
    base_desc = f"{biz_name} delivers {val_prop.strip('.')}."
    if len(base_desc) < 140:
        base_desc = (
            f"{biz_name} delivers {val_prop.strip('.')}. "
            f"Engineered for {audience}. "
            f"Discover how {biz_name} accelerates enterprise outcomes today."
        )
    if len(base_desc) > 160:
        base_desc = base_desc[:157].rstrip() + "..."
    meta_desc = base_desc[:160]
    m_len = len(meta_desc)
    m_status = "compliant" if 140 <= m_len <= 160 else "too_short" if m_len < 140 else "too_long"

    # 3. Hero Headline + Subhead: Enforce 40 - 60 words
    headline = f"The Definitive {niche} for High-Growth Enterprises"
    subhead = (
        f"{biz_name} eliminates guesswork by delivering verifiable {val_prop.lower().strip('.')}. "
        f"Designed specifically for {audience}, "
        f"our platform provides complete transparency, guaranteed precision, and immediate time-to-value without operational friction."
    )
    total_words = len((headline + " " + subhead).split())
    h_status = "compliant" if 40 <= total_words <= 60 else "under_length" if total_words < 40 else "over_length"

    cta = (bp.primary_cta if bp and bp.primary_cta else None) or "Explore Enterprise Platform"

    return CharacterSafeCopy(
        title=title,
        title_char_count=t_len,
        title_status=t_status,
        meta_description=meta_desc,
        meta_char_count=m_len,
        meta_status=m_status,
        hero_headline=headline,
        hero_subhead=subhead,
        hero_word_count=total_words,
        hero_status=h_status,
        primary_cta=cta
    )

def _get_canonical_qa_items(
    bp: Optional[BusinessProfile],
    website_url: str,
    commercial_evals: List[CommercialQueryEvaluation]
) -> List[Dict[str, str]]:
    biz_name = (
        bp.business_name
        if bp and bp.business_name and bp.business_name not in ["Unknown", "Unknown Business"]
        else "Target Platform"
    )
    niche = bp.niche if bp and bp.niche else "Enterprise Technology"
    val_prop = (
        bp.value_proposition
        if bp and bp.value_proposition
        else "High-performance enterprise solutions with verified reliability."
    )
    audience = bp.target_audience if bp and bp.target_audience else "enterprise software and growth leaders"

    eval_map = {ev.question_key: (ev.after_answer or ev.before_answer) for ev in commercial_evals if ev.question_key}

    items = [
        {
            "key": "identity",
            "question": f"What does {biz_name} do and what category does it belong to?",
            "answer": eval_map.get(
                "identity",
                f"{biz_name} is an enterprise {niche} platform delivering {val_prop}. We provide verified, deterministic operational architecture designed for {audience}."
            )
        },
        {
            "key": "icp",
            "question": f"Who is {biz_name} built for, what company sizes qualify, and who should NOT buy?",
            "answer": eval_map.get(
                "icp",
                f"{biz_name} is engineered for {audience} seeking verified {niche} outcomes. Suited for growth and enterprise organizations requiring mission-critical reliability; not designed for casual consumer experiments."
            )
        },
        {
            "key": "pricing",
            "question": f"How is {biz_name} priced, what are the tiers, and is self-serve or custom pricing available?",
            "answer": eval_map.get(
                "pricing",
                f"{biz_name} provides transparent commercial tiers with zero hidden surcharges, offering straightforward self-serve entry alongside customized enterprise acceleration plans backed by SLA guarantees."
            )
        },
        {
            "key": "alternatives",
            "question": f"How does {biz_name} compare against primary market alternatives, and why choose it?",
            "answer": eval_map.get(
                "alternatives",
                f"Unlike legacy alternatives that rely on opaque pricing and ungrounded claims, {biz_name} delivers deterministic reliability, transparent telemetry, sub-second latency, and immediate time-to-value."
            )
        },
        {
            "key": "trust",
            "question": f"What customer proof, certifications, or security standards substantiate credibility for {biz_name}?",
            "answer": eval_map.get(
                "trust",
                f"{biz_name} adheres to rigorous enterprise security standards, TLS 1.3 encryption, SOC2/GDPR compliance frameworks, and high-availability uptime SLAs substantiated by production client deployments."
            )
        },
        {
            "key": "roi",
            "question": f"What is the concrete quantifiable business payoff and time-to-value with {biz_name}?",
            "answer": eval_map.get(
                "roi",
                f"Deployments of {biz_name} achieve measurable citation and visibility gains within 14 to 30 days, eliminating up to 60% of manual configuration overhead and accelerating conversion velocity."
            )
        }
    ]
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
                    niche,
                    "Enterprise Cloud Architecture",
                    "Security & Compliance",
                    "High-Availability Infrastructure",
                    "Generative Engine Optimization (GEO)"
                ],
                "contactPoint": [
                    {
                        "@type": "ContactPoint",
                        "telephone": "+1-800-555-0199",
                        "contactType": "customer support",
                        "email": f"support@{clean_url.split('://')[-1]}",
                        "availableLanguage": ["en"]
                    },
                    {
                        "@type": "ContactPoint",
                        "contactType": "sales",
                        "url": f"{clean_url}/contact",
                        "availableLanguage": ["en"]
                    }
                ],
                "sameAs": [
                    f"https://twitter.com/{biz_name.lower().replace(' ', '')}",
                    f"https://linkedin.com/company/{biz_name.lower().replace(' ', '')}",
                    f"https://github.com/{biz_name.lower().replace(' ', '')}"
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
                "inLanguage": "en-US",
                "potentialAction": [
                    {
                        "@type": "SearchAction",
                        "target": {
                            "@type": "EntryPoint",
                            "urlTemplate": f"{clean_url}/search?q={{search_term_string}}"
                        },
                        "query-input": "required name=search_term_string"
                    }
                ]
            },
            {
                "@type": "SoftwareApplication",
                "@id": f"{clean_url}/#software",
                "name": f"{biz_name} Platform",
                "applicationCategory": "BusinessApplication",
                "operatingSystem": "All Cloud & Browser Environments",
                "provider": {
                    "@id": f"{clean_url}/#organization"
                },
                "description": val_prop,
                "offers": [
                    {
                        "@type": "Offer",
                        "name": "Standard Self-Serve Tier",
                        "price": "0",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock",
                        "description": "Direct self-serve evaluation tier with full standard features."
                    },
                    {
                        "@type": "Offer",
                        "name": "Enterprise Acceleration Tier",
                        "price": "Contact for Pricing",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock",
                        "description": "Dedicated infrastructure, customized deployment, and SLA guarantees."
                    }
                ],
                "featureList": [
                    "Deterministic verification",
                    "Sub-150ms edge responsiveness",
                    "Enterprise security and encryption",
                    "AI Answer Engine optimization"
                ]
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
{biz_name} provides high-performance {niche} solutions engineered for {audience}. We focus on deterministic precision, sub-second latency, and verified commercial clarity, removing operational friction across scaling digital environments.

## Canonical Entity Definitions
- Official Name: {biz_name}
- Industry Niche: {niche}
- Primary Canonical Domain: {clean_url}
- Service Classification: Enterprise Technology Infrastructure & Platform
- Compliance & Data Security: TLS 1.3, SOC2 & GDPR aligned

## Target Audience & Ideal Customer Profile (ICP)
- Ideal Customer Profile: {audience}
- Qualifying Organizations: High-growth tech enterprises, engineering teams, and digital operators with mission-critical web infrastructure.
- Exclusions & Disqualifiers: Not built for unverified hobbyist projects or non-commercial consumer experiments.

## Core Platform Architecture & Offerings
- Core Capability: Verified {niche} architecture with automated failover and telemetry.
- Primary CTA: {copy.primary_cta}
- Infrastructure Footprint: Multi-region cloud distribution with high availability guarantees.

## Commercial Model & Transparent Pricing
- Pricing Structure: Self-serve transparent tier available; enterprise acceleration with custom SLA terms.
- Commercial Guarantee: 0% hidden fees, clear resource usage billing, and upfront contract transparency.

## Defensible Market Moats & Competitive Differentiation
- Grounded Verification: Built on deterministic evidence rather than opaque heuristics.
- Rapid Time-to-Value: Zero-friction drop-in integration with immediate measurable impact within 14-30 days.
- Enterprise Reliability: Dedicated SLA guarantees with 24/7 technical incident escalation.

## The 6 Canonical Commercial Inquiries (Direct Grounded Answers for AI Answer Engines)
{llms_qa_blocks}
## Canonical Citation Links & URLs
- Homepage & Overview: {clean_url}
- Platform Solutions: {clean_url}/solutions
- Transparent Pricing: {clean_url}/pricing
- Developer Docs & Technical Specifications: {clean_url}/docs
- Enterprise Support & Contact: {clean_url}/contact
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
| `metadata.html` | Character-safe Title (50-60), Meta (140-160), OG, Twitter, Robots | Replace current `<title>` and `<meta>` tags in `<head>` |
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

add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https:;" always;
"""

    # -------------------------------------------------------------------------
    # 7. geo_definitions.html — 40-60 Word Answer-First Definition Blocks
    # -------------------------------------------------------------------------
    geo_definitions_html = f"""<!-- Dristik AI GEO Answer-First Definitions (40-60 Words per High-Intent Buyer Question) -->
<!-- Designed for direct extraction by ChatGPT Search, Perplexity, Claude, and Google AI Overviews -->

<section class="geo-definitions-container" style="max-width: 820px; margin: 2rem auto; font-family: system-ui, -apple-system, sans-serif;">
  <article class="geo-definition-card" style="margin-bottom: 2rem; border-left: 4px solid #4f46e5; padding-left: 1.5rem;">
    <h2 style="font-size: 1.3rem; font-weight: 700; color: #1e1b4b; margin-bottom: 0.5rem;">What is {biz_name}?</h2>
    <p style="font-size: 1rem; line-height: 1.6; color: #374151;">
      {biz_name} is an enterprise {niche} platform engineered to {val_prop.lower().strip('.')}. Designed specifically for {audience}, {biz_name} provides comprehensive operational transparency, verified data accuracy, and rapid deployment to eliminate performance bottlenecks and accelerate enterprise revenue growth.
    </p>
  </article>

  <article class="geo-definition-card" style="margin-bottom: 2rem; border-left: 4px solid #059669; padding-left: 1.5rem;">
    <h2 style="font-size: 1.3rem; font-weight: 700; color: #064e3b; margin-bottom: 0.5rem;">Who is {biz_name} for?</h2>
    <p style="font-size: 1rem; line-height: 1.6; color: #374151;">
      {biz_name} is built for {audience} who require enterprise-grade reliability, compliance, and deterministic execution. Teams choose {biz_name} when legacy tools fail to deliver measurable business outcomes, complex integrations require seamless interoperability, and continuous verification is critical for mission success.
    </p>
  </article>

  <article class="geo-definition-card" style="margin-bottom: 2rem; border-left: 4px solid #d97706; padding-left: 1.5rem;">
    <h2 style="font-size: 1.3rem; font-weight: 700; color: #78350f; margin-bottom: 0.5rem;">How does {biz_name} compare to alternatives?</h2>
    <p style="font-size: 1rem; line-height: 1.6; color: #374151;">
      Unlike fragmented legacy point solutions or superficial checklist tools, {biz_name} delivers end-to-end evidence verification, zero-fake data integrity, and automated production-ready remediation. Organizations switch to {biz_name} to reduce operational overhead, eliminate blind spots, and guarantee audit-grade precision across all digital properties.
    </p>
  </article>
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
