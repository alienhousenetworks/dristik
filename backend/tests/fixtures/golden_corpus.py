"""
Dristik Golden Corpus Fixtures (Workstream A & Phase P0)
Provides synthetic, reproducible test fixtures with seeded, ground-truth labeled defects.
Used by CI evaluation harness to verify analyzer Precision and Recall.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SeededDefect(BaseModel):
    defect_id: str
    check_id: str
    category: str
    severity: str
    description: str
    affected_url: str


class GoldenFixtureSite(BaseModel):
    fixture_id: str
    name: str
    domain: str
    description: str
    html_by_url: Dict[str, str] = Field(default_factory=dict)
    headers_by_url: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    redirect_chains: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    robots_txt: Optional[str] = None
    sitemap_xml: Optional[str] = None
    rendered_dom_by_url: Dict[str, str] = Field(default_factory=dict)
    ground_truth_defects: List[SeededDefect] = Field(default_factory=list)


# 10 Golden Synthetic Fixture Sites
GOLDEN_FIXTURES: List[GoldenFixtureSite] = [
    GoldenFixtureSite(
        fixture_id="synth_001_redirect_chain_3",
        name="Redirect Chain of 3 Hops",
        domain="chain-redirect.example.com",
        description="URL redirects through 3 hops: http:// -> https:// -> https://www. -> final destination",
        html_by_url={
            "https://www.chain-redirect.example.com/dest": "<html><head><title>Destination</title><link rel='canonical' href='https://www.chain-redirect.example.com/dest'/></head><body><h1>Destination</h1></body></html>"
        },
        redirect_chains={
            "http://chain-redirect.example.com/start": [
                {"status": 301, "url": "http://chain-redirect.example.com/start", "location": "https://chain-redirect.example.com/step1"},
                {"status": 301, "url": "https://chain-redirect.example.com/step1", "location": "https://www.chain-redirect.example.com/step2"},
                {"status": 301, "url": "https://www.chain-redirect.example.com/step2", "location": "https://www.chain-redirect.example.com/dest"},
                {"status": 200, "url": "https://www.chain-redirect.example.com/dest"}
            ]
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_001",
                check_id="redirect_chains_max_1_hop",
                category="TECHNICAL_SEO",
                severity="MEDIUM",
                description="Redirect chain exceeds 1 hop (observed 3 hops).",
                affected_url="http://chain-redirect.example.com/start"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_002_header_only_noindex",
        name="X-Robots-Tag Header-Only Noindex in Sitemap",
        domain="header-noindex.example.com",
        description="Page lacks HTML meta noindex but returns X-Robots-Tag: noindex, and is present in XML sitemap",
        html_by_url={
            "https://header-noindex.example.com/landing": "<html><head><title>Valuable Landing Page</title><link rel='canonical' href='https://header-noindex.example.com/landing'/></head><body><h1>Landing</h1></body></html>"
        },
        headers_by_url={
            "https://header-noindex.example.com/landing": {
                "content-type": "text/html; charset=utf-8",
                "x-robots-tag": "noindex, nofollow"
            }
        },
        sitemap_xml="""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://header-noindex.example.com/landing</loc></url>
</urlset>""",
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_002",
                check_id="x_robots_tag_indexable",
                category="TECHNICAL_SEO",
                severity="CRITICAL",
                description="Header X-Robots-Tag blocks indexation on URL listed in XML sitemap.",
                affected_url="https://header-noindex.example.com/landing"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_003_mixed_content_https",
        name="Mixed Content HTTP Insecure Assets on HTTPS",
        domain="mixed-content.example.com",
        description="Secure HTTPS page loads insecure HTTP JavaScript and image resources",
        html_by_url={
            "https://mixed-content.example.com/": """<!DOCTYPE html>
<html>
<head>
  <title>Mixed Content Page</title>
  <link rel='canonical' href='https://mixed-content.example.com/'/>
  <script src="http://insecure-cdn.example.com/analytics.js"></script>
</head>
<body>
  <h1>Secure Store</h1>
  <img src="http://insecure-cdn.example.com/logo.png" alt="Logo" />
</body>
</html>"""
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_003",
                check_id="no_mixed_content",
                category="TECHNICAL_SEO",
                severity="HIGH",
                description="Insecure HTTP assets loaded over HTTPS connection.",
                affected_url="https://mixed-content.example.com/"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_004_schema_price_contradiction",
        name="JSON-LD Schema Price Contradicts Visible DOM Price",
        domain="pricing-conflict.example.com",
        description="JSON-LD declares price $49.00 while visible HTML prominently displays $99.00",
        html_by_url={
            "https://pricing-conflict.example.com/product": """<!DOCTYPE html>
<html>
<head>
  <title>SaaS Product Pro</title>
  <link rel='canonical' href='https://pricing-conflict.example.com/product'/>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "SaaS Product Pro",
    "offers": {
      "@type": "Offer",
      "price": "49.00",
      "priceCurrency": "USD"
    }
  }
  </script>
</head>
<body>
  <h1>SaaS Product Pro</h1>
  <div class="pricing-card">
    <span class="price">$99.00 / month</span>
  </div>
</body>
</html>"""
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_004",
                check_id="schema_matches_visible_content",
                category="SCHEMA",
                severity="HIGH",
                description="JSON-LD offer price ($49.00) contradicts visible page price ($99.00).",
                affected_url="https://pricing-conflict.example.com/product"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_005_hydration_only_title",
        name="Client-Side Hydration Only Title and Canonical",
        domain="csr-spa.example.com",
        description="Server HTML is empty shell without title/canonical; Playwright DOM injects them via JS",
        html_by_url={
            "https://csr-spa.example.com/": """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body>
  <div id="root">Loading application...</div>
  <script src="/app.bundle.js"></script>
</body>
</html>"""
        },
        rendered_dom_by_url={
            "https://csr-spa.example.com/": """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Enterprise AI Platform - Hydrated</title>
  <link rel="canonical" href="https://csr-spa.example.com/" />
  <meta name="description" content="Hydrated dynamic single page app description." />
</head>
<body>
  <div id="root">
    <h1>Enterprise AI Platform</h1>
    <p>Rendered client side content.</p>
  </div>
</body>
</html>"""
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_005",
                check_id="server_html_contains_critical_metadata",
                category="TECHNICAL_SEO",
                severity="HIGH",
                description="Raw server HTML lacks title, meta description, and canonical tags (client-only hydration risk).",
                affected_url="https://csr-spa.example.com/"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_006_conflicting_addresses",
        name="Conflicting Physical Corporate Addresses Across Pages",
        domain="contradictory-brand.example.com",
        description="Homepage footer lists London, UK address; Contact page lists Austin, TX with no branch context",
        html_by_url={
            "https://contradictory-brand.example.com/": """<!DOCTYPE html>
<html>
<head><title>Nexus Tech Corp</title></head>
<body>
  <h1>Nexus Tech</h1>
  <footer>Address: 10 Downing St, London, SW1A 2AA, United Kingdom</footer>
</body>
</html>""",
            "https://contradictory-brand.example.com/contact": """<!DOCTYPE html>
<html>
<head><title>Contact Us - Nexus Tech Corp</title></head>
<body>
  <h1>Contact Nexus Tech</h1>
  <p>Our Corporate Headquarters: 500 Congress Ave, Austin, TX 78701, USA</p>
</body>
</html>"""
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_006",
                check_id="brand_address_consistency",
                category="TRUST_AUTHORITY",
                severity="MEDIUM",
                description="Contradictory headquarters address between homepage (London, UK) and contact page (Austin, TX).",
                affected_url="https://contradictory-brand.example.com/"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_007_missing_canonical",
        name="Missing Canonical Tag with Tracking Query Parameters",
        domain="no-canonical.example.com",
        description="Page lacks canonical link element entirely, risking index duplication across tracking URLs",
        html_by_url={
            "https://no-canonical.example.com/blog/article-1": """<!DOCTYPE html>
<html>
<head>
  <title>10 Essential Cloud Security Tips</title>
</head>
<body>
  <h1>10 Essential Cloud Security Tips</h1>
  <p>Article body content.</p>
</body>
</html>"""
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_007",
                check_id="canonical_tag_present",
                category="ON_PAGE_SEO",
                severity="HIGH",
                description="No canonical tag found on indexable content page.",
                affected_url="https://no-canonical.example.com/blog/article-1"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_008_duplicate_titles",
        name="Duplicate Title Tags Across Distinct Commercial Pages",
        domain="dup-titles.example.com",
        description="Two distinct product URLs share the exact same title tag",
        html_by_url={
            "https://dup-titles.example.com/features/reporting": """<!DOCTYPE html>
<html>
<head><title>Features | Analytics Cloud Pro</title><link rel='canonical' href='https://dup-titles.example.com/features/reporting'/></head>
<body><h1>Automated Reporting</h1></body>
</html>""",
            "https://dup-titles.example.com/features/integrations": """<!DOCTYPE html>
<html>
<head><title>Features | Analytics Cloud Pro</title><link rel='canonical' href='https://dup-titles.example.com/features/integrations'/></head>
<body><h1>Third-Party Integrations</h1></body>
</html>"""
        },
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_008",
                check_id="unique_title_tags",
                category="ON_PAGE_SEO",
                severity="MEDIUM",
                description="Identical title tag 'Features | Analytics Cloud Pro' on multiple distinct URLs.",
                affected_url="https://dup-titles.example.com/features/reporting"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_009_disallow_all_robots",
        name="Catastrophic Sitewide Disallow in Robots.txt",
        domain="disallow-all.example.com",
        description="Robots.txt contains Disallow: / blocking all search engine crawlers from the domain",
        html_by_url={
            "https://disallow-all.example.com/": "<html><head><title>Home</title></head><body><h1>Welcome</h1></body></html>"
        },
        robots_txt="""User-agent: *
Disallow: /
""",
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_009",
                check_id="robots_allows_crawling",
                category="TECHNICAL_SEO",
                severity="CRITICAL",
                description="Robots.txt contains sitewide 'Disallow: /' blocking all crawlers.",
                affected_url="https://disallow-all.example.com/"
            )
        ]
    ),
    GoldenFixtureSite(
        fixture_id="synth_010_orphan_sitemap_url",
        name="Orphan Page in XML Sitemap with Zero Inbound Internal Links",
        domain="orphan-sitemap.example.com",
        description="Sitemap lists /promotions/secret-sale which has 0 inbound links from crawled pages",
        html_by_url={
            "https://orphan-sitemap.example.com/": """<!DOCTYPE html>
<html>
<head><title>Home</title><link rel='canonical' href='https://orphan-sitemap.example.com/'/></head>
<body>
  <h1>Store Home</h1>
  <a href="/products">Products</a>
  <a href="/about">About</a>
</body>
</html>""",
            "https://orphan-sitemap.example.com/products": """<!DOCTYPE html>
<html>
<head><title>Products</title><link rel='canonical' href='https://orphan-sitemap.example.com/products'/></head>
<body><h1>Products</h1><a href="/">Home</a></body>
</html>""",
            "https://orphan-sitemap.example.com/promotions/secret-sale": """<!DOCTYPE html>
<html>
<head><title>Secret Sale</title><link rel='canonical' href='https://orphan-sitemap.example.com/promotions/secret-sale'/></head>
<body><h1>Secret Sale</h1></body>
</html>"""
        },
        sitemap_xml="""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://orphan-sitemap.example.com/</loc></url>
  <url><loc>https://orphan-sitemap.example.com/products</loc></url>
  <url><loc>https://orphan-sitemap.example.com/promotions/secret-sale</loc></url>
</urlset>""",
        ground_truth_defects=[
            SeededDefect(
                defect_id="DEF_010",
                check_id="no_orphan_pages",
                category="TECHNICAL_SEO",
                severity="MEDIUM",
                description="URL in XML sitemap has zero internal inlinks from crawled site.",
                affected_url="https://orphan-sitemap.example.com/promotions/secret-sale"
            )
        ]
    )
]


def get_golden_fixtures() -> List[GoldenFixtureSite]:
    return list(GOLDEN_FIXTURES)


def get_fixture_by_id(fixture_id: str) -> Optional[GoldenFixtureSite]:
    for f in GOLDEN_FIXTURES:
        if f.fixture_id == fixture_id:
            return f
    return None
