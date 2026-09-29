"""
Unit Tests for Deep WCAG 2.2 AA Accessibility Auditor
Verifies detection of:
- Image alt text quality
- Unlabeled form controls & input purpose autocomplete
- Skipped heading hierarchy & structure
- Language attribute declaration
- Landmark structure & skip navigation
- Duplicate IDs & parsing
- Accessible element names & ambiguous links
- Color contrast calculations (WCAG 1.4.3 minimums)
- Keyboard focus traps, positive tabindex & outline suppression
- Target size minimums (WCAG 2.2 SC 2.5.8)
- ARIA semantics, invalid roles & modal dialogs
"""
from app.domain.models import PageEvidence
from app.intelligence.accessibility.wcag_auditor import (
    DeepWcagAuditor,
    calculate_contrast_ratio,
    parse_color_to_rgb,
    relative_luminance,
)


def test_wcag_auditor_detects_all_key_violations():
    bad_html = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Main Heading</h1>
        <h3>Skipped Heading Level to H3</h3>
        <img src="/img1.jpg">
        <img src="/img2.jpg" alt="image">
        <form>
            <input type="text" name="email" id="email_input">
        </form>
        <button></button>
        <div id="duplicate_box">First</div>
        <div id="duplicate_box">Second</div>
        <iframe src="/map"></iframe>
    </body>
    </html>
    """

    pages = [
        PageEvidence(
            url="https://acme.com/accessibility-test",
            title="Test Page",
            raw_html=bad_html,
            word_count=50
        )
    ]

    summary, findings = DeepWcagAuditor.audit_pages(pages)

    # Check violations caught
    rule_ids = {v.rule_id for v in summary.violations}
    assert "WCAG_1_1_1_IMAGE_ALT" in rule_ids
    assert "WCAG_1_3_1_FORM_LABELS" in rule_ids
    assert "WCAG_4_1_2_ACCESSIBLE_NAMES" in rule_ids
    assert "WCAG_1_3_1_HEADING_ORDER" in rule_ids
    assert "WCAG_3_1_1_LANGUAGE" in rule_ids
    assert "WCAG_1_3_1_LANDMARK_MAIN" in rule_ids
    assert "WCAG_4_1_1_DUPLICATE_ID" in rule_ids
    assert "WCAG_4_1_2_IFRAME_TITLE" in rule_ids
    assert "WCAG_3_3_2_INPUT_PURPOSE" in rule_ids

    assert len(summary.violations) == 9
    assert summary.compliance_score <= 60.0
    assert len(findings) == 9
    assert summary.conformance_status == "NON_COMPLIANT"


def test_wcag_contrast_and_color_calculation():
    # Pure color math verification
    white = (255, 255, 255)
    black = (0, 0, 0)
    assert calculate_contrast_ratio(white, black) == 21.0
    assert calculate_contrast_ratio(white, white) == 1.0

    # Low contrast gray on white: #999999 (153, 153, 153) on #ffffff gives ~2.85:1 (fails 4.5:1)
    gray = (153, 153, 153)
    ratio = calculate_contrast_ratio(white, gray)
    assert ratio < 4.5

    # High contrast dark blue on white: #000080 on #ffffff gives ~14.6:1
    navy = (0, 0, 128)
    assert calculate_contrast_ratio(white, navy) >= 4.5

    contrast_html = """
    <html lang="en">
    <head><title>Contrast Test</title></head>
    <body>
        <main>
            <h1>Contrast Audit</h1>
            <p style="color: #999999; background-color: #ffffff;">This low contrast text fails WCAG 1.4.3.</p>
        </main>
    </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com/contrast", raw_html=contrast_html)]
    summary, _ = DeepWcagAuditor.audit_pages(pages)
    rule_ids = {v.rule_id for v in summary.violations}
    assert "WCAG_1_4_3_COLOR_CONTRAST" in rule_ids


def test_wcag_keyboard_and_focus_traps():
    keyboard_html = """
    <html lang="en">
    <head>
        <title>Keyboard Test</title>
        <style>
            :focus { outline: none; }
        </style>
    </head>
    <body>
        <main>
            <h1>Keyboard Nav</h1>
            <input type="text" tabindex="5" placeholder="Bad tabindex">
            <div aria-hidden="true">
                <button>Trapped Inside Aria Hidden</button>
            </div>
            <a href="/somewhere">click here</a>
        </main>
    </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com/keyboard", raw_html=keyboard_html)]
    summary, _ = DeepWcagAuditor.audit_pages(pages)
    rule_ids = {v.rule_id for v in summary.violations}
    assert "WCAG_2_1_1_KEYBOARD_ACCESSIBLE" in rule_ids  # Positive tabindex
    assert "WCAG_2_4_3_FOCUS_TRAP" in rule_ids           # Button inside aria-hidden
    assert "WCAG_2_4_4_LINK_NAMES" in rule_ids          # Ambiguous "click here"
    assert "WCAG_2_4_7_FOCUS_VISIBILITY" in rule_ids    # Outline: none suppression


def test_wcag_target_size_and_zoom_locking():
    mobile_a11y_html = """
    <html lang="en">
    <head>
        <title>Mobile Accessibility</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    </head>
    <body>
        <main>
            <h1>Mobile Experience</h1>
            <button style="width: 14px; height: 14px;">X</button>
        </main>
    </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com/mobile-a11y", raw_html=mobile_a11y_html)]
    summary, _ = DeepWcagAuditor.audit_pages(pages)
    rule_ids = {v.rule_id for v in summary.violations}
    assert "WCAG_1_4_4_VIEWPORT_SCALING" in rule_ids
    assert "WCAG_2_5_8_TARGET_SIZE" in rule_ids


def test_wcag_aria_and_modal_semantics():
    aria_html = """
    <html lang="en">
    <head><title>ARIA Test</title></head>
    <body>
        <main>
            <h1>ARIA Audit</h1>
            <div role="btn">Custom fake button role</div>
            <div role="tab">Tab missing aria-selected</div>
            <div role="dialog">Dialog missing aria-modal</div>
        </main>
    </body>
    </html>
    """
    pages = [PageEvidence(url="https://acme.com/aria", raw_html=aria_html)]
    summary, _ = DeepWcagAuditor.audit_pages(pages)
    rule_ids = {v.rule_id for v in summary.violations}
    assert "WCAG_4_1_2_ARIA_MISUSE" in rule_ids
    assert "WCAG_4_1_2_MODAL_ACCESSIBILITY" in rule_ids
