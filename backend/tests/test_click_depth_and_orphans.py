"""
Unit tests for Click-Depth Histogram, Orphan Page Detector, Anchor Text, Form, and Media Analyzers.
"""
from app.domain.models import PageEvidence
from app.seo.analyzers.link_depth import LinkDepthAnalyzer
from app.analyzers.form_analyzer import FormAccessibilityAnalyzer
from app.seo.analyzers.media_asset_analyzer import MediaAssetAnalyzer


def test_click_depth_histogram():
    # Construct a link graph:
    # Home -> P1 (Depth 1)
    # P1 -> P2 (Depth 2)
    # P2 -> P3 (Depth 3)
    # P4 (No path from home -> Depth 4+)
    pages = [
        PageEvidence(url="https://acme.com", internal_links=["https://acme.com/p1"]),
        PageEvidence(url="https://acme.com/p1", internal_links=["https://acme.com/p2"]),
        PageEvidence(url="https://acme.com/p2", internal_links=["https://acme.com/p3"]),
        PageEvidence(url="https://acme.com/p3", internal_links=[]),
        PageEvidence(url="https://acme.com/p4", internal_links=[]),
    ]

    report = LinkDepthAnalyzer.analyze_click_depth(pages, homepage_url="https://acme.com")

    assert report.total_pages_analyzed == 5
    # Home and p1 are depth 1
    assert report.depth_1_count >= 1
    assert "https://acme.com/p1" in report.pages_by_depth["depth_1"]
    assert "https://acme.com/p2" in report.pages_by_depth["depth_2"]
    assert "https://acme.com/p3" in report.pages_by_depth["depth_3"]
    assert "https://acme.com/p4" in report.pages_by_depth["depth_4_plus"]
    assert report.max_click_depth >= 3


def test_orphan_page_detection():
    # Sitemap has /p1, /p2, and /orphan
    # Crawled pages:
    # Home links to /p1 and /p2. Nobody links to /orphan.
    pages = [
        PageEvidence(url="https://acme.com", internal_links=["https://acme.com/p1", "https://acme.com/p2"]),
        PageEvidence(url="https://acme.com/p1", internal_links=[]),
        PageEvidence(url="https://acme.com/p2", internal_links=[]),
    ]
    sitemap_urls = [
        "https://acme.com",
        "https://acme.com/p1",
        "https://acme.com/p2",
        "https://acme.com/orphan",
    ]

    orphans_rep = LinkDepthAnalyzer.detect_orphans(pages, sitemap_urls, homepage_url="https://acme.com")
    assert orphans_rep.orphan_count == 1
    assert "https://acme.com/orphan" in orphans_rep.orphan_urls
    assert orphans_rep.total_sitemap_urls == 4


def test_generic_anchor_text_flagging():
    pages = [
        PageEvidence(
            url="https://acme.com",
            ctas=["Click here", "Read More", "https://acme.com/pricing", "Schedule VIP Demo"],
            internal_links=["https://acme.com/about", "https://acme.com/blog"]
        )
    ]

    anchors_rep = LinkDepthAnalyzer.audit_anchor_texts(pages)
    assert anchors_rep.generic_anchor_count >= 3

    flagged_reasons = [item["reason"] for item in anchors_rep.flagged_anchor_instances]
    assert any("click here" in r.lower() for r in flagged_reasons)
    assert any("naked link" in r.lower() or "raw url" in r.lower() for r in flagged_reasons)


def test_form_accessibility_and_friction():
    raw_html = """
    <html>
      <body>
        <form id="contact_form" action="/contact-submit">
          <input type="text" name="name" id="name_input">
          <!-- missing label for email -->
          <input type="email" name="email" id="email_input">
          <button type="submit">Submit</button>
        </form>
      </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com/contact")]
    raw_html_map = {"https://acme.com/contact": raw_html}

    form_rep = FormAccessibilityAnalyzer.analyze_forms(pages, raw_html_map=raw_html_map)
    assert form_rep.total_forms_detected == 1
    assert form_rep.forms[0].submit_button_text == "Submit"
    assert form_rep.forms_without_captcha == 1
    assert form_rep.friction_score > 0


def test_media_payload_and_mixed_content():
    raw_html = """
    <html>
      <body>
        <!-- Missing alt and dimensions -->
        <img src="https://acme.com/banner.png">
        <!-- Modern format with dimensions and alt -->
        <img src="https://acme.com/logo.webp" alt="Acme Logo" width="200" height="50">
        <!-- Insecure mixed content -->
        <img src="http://insecure-cdn.com/icon.jpg" alt="Icon" width="16" height="16">
      </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com/about")]
    raw_html_map = {"https://acme.com/about": raw_html}

    media_rep = MediaAssetAnalyzer.analyze_media(pages, raw_html_map=raw_html_map)
    assert media_rep.total_images_analyzed == 3
    assert media_rep.missing_alt_count == 1
    assert media_rep.missing_dimensions_count == 1
    assert media_rep.modern_format_count == 1
    assert media_rep.mixed_content_count == 1
    assert "http://insecure-cdn.com/icon.jpg" in media_rep.mixed_content_urls
