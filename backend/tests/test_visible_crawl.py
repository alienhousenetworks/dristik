"""
Visible-page crawl tests.

Reproduces the Django-template failures seen on alienhousenetworks.com:
split-span H1s, mega-menu chrome leaking into copy, content asides dropped,
hidden modals counted as CTAs, and www vs apex treated as different sites.
"""
from bs4 import BeautifulSoup

from app.crawl.analyzers.dom import analyze_dom_structure
from app.crawl.analyzers.html import analyze_html_content, distill_semantic_content, heading_text
from app.crawl.analyzers.links import analyze_link_graph
from app.crawl.analyzers.visible import extract_visible_page, is_hidden
from app.agents.page.intelligence import _clean_lead, fallback_copy_audit, audit_page_seo
from app.domain.enums import BusinessIntent
from app.domain.models import BusinessProfile, PageEvidence
from app.evidence.store import EvidenceStore
from app.crawl.crawler import CrawlerService


DJANGO_PRIVACY = """
<!DOCTYPE html>
<html>
<head>
  <title>Privacy Policy | ALIENHOUSE NETWORKS</title>
  <meta name="description" content="How we collect and use information.">
  <link rel="canonical" href="https://alienhousenetworks.com/privacy/">
</head>
<body>
  <nav class="fixed w-full">
    ALIENHOUSE NETWORKS COMPANY
    <a href="/about-us/">About Us</a>
    <a href="/careers/">Careers</a>
    <a href="/company/blog/">Blog</a>
    SERVICES
    <a href="/services/software-development/">Software Development</a>
    <a href="/services/cloud-solutions/">Cloud Solutions</a>
    <a href="javascript:void(0)">INITIATE CONTACT</a>
    <div class="mega-menu">API Development DevOps &amp; Cloud Engineering Mobile App Development</div>
  </nav>
  <div id="mobile-menu" class="fixed inset-0 translate-x-full">
    COMPANY About Us Careers Blog SERVICES Software Development
  </div>
  <main>
    <header>
      <p>LEGAL // PRIVACY NOTICE</p>
      <h1>Privacy <span class="text-alien">Policy</span></h1>
      <p>This privacy notice for ALIENHOUSE NETWORKS describes how and why we might collect, store, use, and share your information when you use our website and services.</p>
    </header>
    <aside>
      <nav id="toc">
        <p>Table of Contents</p>
        <a href="#summary">1. Summary of key points</a>
      </nav>
    </aside>
    <article class="privacy-prose">
      <h2>1. Summary of key points</h2>
      <p>We process information you submit through contact, careers, and training enrollment forms, plus limited technical data collected automatically when you visit the site.</p>
      <h2>2. What information do we collect?</h2>
      <p>We collect personal information that you voluntarily provide when you contact us, apply for a role, or enroll in industry training.</p>
    </article>
  </main>
  <footer>Copyright ALIENHOUSE NETWORKS <a href="/privacy/">Privacy Policy</a></footer>
  <div id="contact-modal" class="hidden">
    <h2>Establish Connection</h2>
    <a href="#contact">CONTACT</a>
  </div>
  <div id="access-blocked-screen" hidden>
    <h2>Access Restricted</h2>
  </div>
</body>
</html>
"""

DJANGO_SERVICE = """
<!DOCTYPE html>
<html>
<head><title>Cloud Solutions | AlienHouse Systems</title></head>
<body>
  <nav>COMPANY <a href="/about-us/">About Us</a> SERVICES
    <a href="/services/software-development/">Software Development</a>
  </nav>
  <main>
    <h1>Cloud Solutions</h1>
    <p>Our Cloud Solutions service enables businesses to design, migrate, and operate resilient cloud infrastructures optimized for performance, security, and scalability. Teams keep production estates available while they retire legacy hardware.</p>
    <main class="nested-include">
      <h3>System Overview</h3>
      <p>From cloud strategy and infrastructure design to deployment, monitoring, and optimization, we ensure your applications run reliably while minimizing operational costs. Security, automation, and future growth stay in the same operating model.</p>
    </main>
    <aside>
      <h3>Available Protocols</h3>
      <h4>Cloud Migration</h4>
      <p>Sub-service under Cloud Solutions. Move workloads without downtime.</p>
      <h4>Cloud Security</h4>
      <p>Access control and continuous monitoring for production estates.</p>
    </aside>
  </main>
  <footer>Connect</footer>
</body>
</html>
"""

DJANGO_NO_MAIN = """
<!DOCTYPE html>
<html>
<head><title>Clinic visiting hours</title></head>
<body>
  <div class="navbar">Home About <a href="/login">Login</a></div>
  <div id="content" class="page-content overflow-hidden">
    <h1>Clinic <span>visiting</span> hours</h1>
    <p>The ward is open weekdays from 8am until 6pm. Book from the patient portal or call reception to reserve a slot.</p>
    <p>Specialist clinics run on Tuesday and Thursday afternoons with same-week follow up.</p>
  </div>
  <div class="site-footer">Privacy Terms</div>
</body>
</html>
"""


def test_split_span_h1_is_not_privacypolicy():
    soup = BeautifulSoup(DJANGO_PRIVACY, "lxml")
    h1 = soup.find("h1")
    assert heading_text(h1) == "Privacy Policy"
    # The bug the live audit showed: strip=True with no separator concatenates.
    assert h1.get_text(strip=True) == "PrivacyPolicy"


def test_django_privacy_strips_nav_keeps_policy():
    soup = BeautifulSoup(DJANGO_PRIVACY, "lxml")
    result = analyze_html_content(soup, "https://alienhousenetworks.com/privacy/", EvidenceStore("priv"))
    assert result["h1"] == ["Privacy Policy"]
    assert "This privacy notice for ALIENHOUSE NETWORKS" in result["distilled_text"]
    assert "Software Development" not in result["distilled_text"]
    assert "INITIATE CONTACT" not in result["distilled_text"]
    assert "Access Restricted" not in result["distilled_text"]
    assert "Establish Connection" not in result["h2"]
    assert result["word_count"] > 80
    assert not result["distilled_text"].lower().startswith("company")


def test_overflow_hidden_is_not_treated_as_invisible():
    soup = BeautifulSoup(DJANGO_NO_MAIN, "lxml")
    content = soup.find(id="content")
    assert is_hidden(content) is False
    result = analyze_html_content(soup, "https://clinic.example/hours", EvidenceStore("clinic"))
    assert result["h1"] == ["Clinic visiting hours"]
    assert "patient portal" in result["distilled_text"]
    assert "Login" not in result["distilled_text"]


def test_content_aside_is_not_dropped():
    soup = BeautifulSoup(DJANGO_SERVICE, "lxml")
    result = analyze_html_content(soup, "https://alienhousenetworks.com/services/cloud-solutions/", EvidenceStore("cloud"))
    assert result["h1"] == ["Cloud Solutions"]
    assert "Cloud Migration" in result["distilled_text"]
    assert "Access control and continuous monitoring" in result["distilled_text"]
    assert "Software Development" not in result["distilled_text"]
    assert result["word_count"] > 80


def test_hidden_modal_ctas_are_ignored():
    soup = BeautifulSoup(DJANGO_PRIVACY, "lxml")
    dom = analyze_dom_structure(soup, "https://alienhousenetworks.com/privacy/", EvidenceStore("cta"))
    joined = " ".join(dom["cta_candidates"]).lower()
    assert "initiate contact" not in joined
    assert "establish connection" not in joined
    assert not any(c.startswith("1.") or c.startswith("11.") for c in dom["cta_candidates"])


def test_www_and_apex_are_same_site():
    html = """
    <html><body>
      <a href="https://www.alienhousenetworks.com/game/">3D World</a>
      <a href="https://alienhousenetworks.com/training/">Training</a>
      <a href="https://evworx.co.in/">EVWORX</a>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    links = analyze_link_graph(
        soup,
        "https://alienhousenetworks.com/",
        "https://alienhousenetworks.com/",
        EvidenceStore("links"),
    )
    internals = " ".join(links["internal_links"])
    assert "game" in internals
    assert "training" in internals
    assert not any("evworx" in u for u in links["internal_links"])
    assert any("evworx" in u for u in links["external_links"])

    crawler = CrawlerService()
    www = crawler._normalize_url(
        "https://www.alienhousenetworks.com/game/",
        "alienhousenetworks.com",
        "https://alienhousenetworks.com",
    )
    assert www and www.endswith("/game")


def test_company_blog_is_blog_not_about():
    crawler = CrawlerService()
    assert crawler._classify_page_type("/company/blog") == "blog"
    assert crawler._classify_page_type("/company/blog/") == "blog"


def test_copy_hero_uses_real_paragraph_not_nav():
    page = PageEvidence(
        url="https://alienhousenetworks.com/privacy/",
        title="Privacy Policy | ALIENHOUSE NETWORKS",
        meta_description="How we collect and use information.",
        h1=["Privacy Policy"],
        h2=["1. Summary of key points", "2. What information do we collect?"],
        word_count=200,
        page_type="legal",
        body_text=(
            "LEGAL // PRIVACY NOTICE\n"
            "Privacy Policy\n"
            "This privacy notice for ALIENHOUSE NETWORKS describes how and why we might collect, "
            "store, use, and share your information when you use our website and services.\n"
            "We process information you submit through contact forms."
        ),
        ctas=[],
        canonical_url="https://alienhousenetworks.com/privacy/",
        og_tags={"og:title": "x", "og:description": "y"},
        schema_types=["Organization"],
    )
    lead = _clean_lead(page.body_text, "Privacy Policy")
    assert "privacy notice" in lead.lower()
    assert "LEGAL //" not in lead
    seo = audit_page_seo(page)
    copy = fallback_copy_audit(
        page,
        BusinessProfile(business_name="ALIENHOUSE NETWORKS", primary_intent=BusinessIntent.SAAS),
        seo,
    )
    assert copy.suggested.h1 == "Privacy Policy"
    assert "Software Development" not in (copy.suggested.hero or "")
    assert copy.suggested.title == "Privacy Policy | ALIENHOUSE NETWORKS"


def test_gsap_opacity_carousel_is_still_scraped():
    """About-style Django pages hide slides with opacity:0; a human can still see them."""
    html = """
    <html><body>
      <nav>COMPANY About Us</nav>
      <main>
        <h1>AlienHouse Networks</h1>
        <p>Empowering Businesses, Elevating Brands.</p>
        <div class="journey-slide" style="transform:translateX(100%);opacity:0;">
          <h2>THE JOURNEY</h2>
          <p>AlienHouse Networks is a strategic technology consultancy engineering secure digital systems for enterprises across industries.</p>
        </div>
        <div class="journey-text" style="will-change: transform, opacity; opacity:0; transform:translateY(40px)">
          <p>Choosing AlienHouse means disciplined engineering, enterprise-grade reliability, and measurable business outcomes for every engagement.</p>
        </div>
      </main>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    result = analyze_html_content(soup, "https://alienhousenetworks.com/about-us/", EvidenceStore("about"))
    assert "strategic technology consultancy" in result["distilled_text"]
    assert "measurable business outcomes" in result["distilled_text"]
    assert result["word_count"] > 30


def test_visible_snapshot_recovers_cms_json_on_empty_shell():
    html = """
    <html><body>
      <div id="content"></div>
      <script id="page-data" type="application/json">{
        "fields": {
          "headline": "Autumn collection landing",
          "body": "Hand-finished wool coats cut in small batches from the admin CMS."
        }
      }</script>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    snap = extract_visible_page(soup)
    assert "wool coats" in snap["main_text"].lower()
    assert snap["word_count"] > 10
