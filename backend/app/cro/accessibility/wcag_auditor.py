"""
Dristik Deep WCAG 2.2 AA Accessibility Auditor
Audits comprehensive accessibility standards across crawled DOM:
- WCAG 2.2 AA conformance checks
- Color contrast calculation (WCAG 1.4.3 minimum 4.5:1 / 3:1)
- Keyboard navigation & focus traps (WCAG 2.1.1, 2.4.3, positive tabindex anti-patterns)
- Focus visibility (WCAG 2.4.7 outline:none suppression)
- Form control explicit labels & input purpose (WCAG 1.3.1, 3.3.2)
- Landmark structure (<main>, <nav>, <header>, <footer>)
- Heading hierarchy (H1 integrity, single H1, sequential order, empty headings)
- ARIA semantics, valid roles & state attributes (WCAG 4.1.2)
- Duplicate DOM element IDs (WCAG 4.1.1)
- Button & link accessible names, ambiguous link text (WCAG 2.4.4, 4.1.2)
- Iframe descriptive titles
- Language declaration (<html lang="...">)
- Skip navigation link (WCAG 2.4.1)
- Interactive element target size (WCAG 2.2 SC 2.5.8 >=24x24px)
- Modal dialog accessibility (role="dialog", aria-modal="true")
- Screen-reader table semantics (<th>, scope) & viewport zoom locking (WCAG 1.4.4)
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from bs4 import BeautifulSoup

from app.domain.models import (
    PageEvidence,
    Finding,
    FindingEvidence,
    WcagViolation,
    WcagAuditSummary,
    WcagCategoryScore,
)
from app.domain.enums import Severity, Category, FindingClassification, ImpactLevel

# Standard W3C ARIA roles
VALID_ARIA_ROLES = {
    "alert", "alertdialog", "application", "article", "banner", "button",
    "cell", "checkbox", "columnheader", "combobox", "complementary", "contentinfo",
    "definition", "dialog", "directory", "document", "feed", "figure", "form",
    "grid", "gridcell", "group", "heading", "img", "link", "list", "listbox",
    "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem",
    "menuitemcheckbox", "menuitemradio", "navigation", "none", "note", "option",
    "presentation", "progressbar", "radio", "radiogroup", "region", "row",
    "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator",
    "slider", "spinbutton", "status", "switch", "tab", "table", "tablist",
    "tabpanel", "term", "textbox", "timer", "toolbar", "tooltip", "tree",
    "treegrid", "treeitem"
}

# Generic/placeholder text that should not count as descriptive alt text
GENERIC_ALT_STRINGS = {
    "image", "photo", "pic", "icon", "placeholder", "logo", "graphic",
    "picture", "file", "untitled", "img", "asset", "banner"
}

# Ambiguous link text that lacks context for screen reader users
AMBIGUOUS_LINK_TEXTS = {
    "click here", "read more", "learn more", "here", "more", "continue",
    "link", "view", "details", "info", "explore", "go", "check this out"
}

# Named CSS colors to RGB map for contrast auditing
NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "lightgray": (211, 211, 211),
    "darkgray": (169, 169, 169),
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "green": (0, 128, 0),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "teal": (0, 128, 128),
    "navy": (0, 0, 128),
    "orange": (255, 165, 0),
}


def parse_color_to_rgb(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parses hex, rgb(), rgba(), or named colors into (r, g, b) tuple."""
    if not color_str:
        return None
    c = color_str.strip().lower()
    if c in NAMED_COLORS:
        return NAMED_COLORS[c]

    # Hex match #rgb or #rrggbb
    hex_match = re.match(r"^#([0-9a-f]{3}|[0-9a-f]{6})$", c)
    if hex_match:
        val = hex_match.group(1)
        if len(val) == 3:
            return (int(val[0] * 2, 16), int(val[1] * 2, 16), int(val[2] * 2, 16))
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))

    # rgb/rgba match
    rgb_match = re.match(r"^rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", c)
    if rgb_match:
        try:
            return (
                min(255, max(0, int(rgb_match.group(1)))),
                min(255, max(0, int(rgb_match.group(2)))),
                min(255, max(0, int(rgb_match.group(3)))),
            )
        except ValueError:
            return None

    return None


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculates relative luminance per W3C WCAG 2.2 formula."""
    def channel_lum(val: int) -> float:
        v = val / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def calculate_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculates contrast ratio (1:1 to 21:1) between two RGB colors."""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    l_max = max(l1, l2)
    l_min = min(l1, l2)
    return round((l_max + 0.05) / (l_min + 0.05), 2)


class DeepWcagAuditor:
    """
    Executes comprehensive WCAG 2.2 Level AA accessibility evaluation on crawled pages.
    Evaluates 20 distinct criteria across all 4 WCAG Principles:
    - Perceivable
    - Operable
    - Understandable
    - Robust
    """

    @classmethod
    def audit_pages(cls, pages: List[PageEvidence]) -> Tuple[WcagAuditSummary, List[Finding]]:
        violations: List[WcagViolation] = []
        checks_passed = 0
        total_checks_evaluated = 0

        findings: List[Finding] = []

        category_counts: Dict[str, Dict[str, int]] = {
            "images": {"passed": 0, "violations": 0},
            "forms": {"passed": 0, "violations": 0},
            "headings": {"passed": 0, "violations": 0},
            "landmarks": {"passed": 0, "violations": 0},
            "tables": {"passed": 0, "violations": 0},
            "contrast": {"passed": 0, "violations": 0},
            "viewport": {"passed": 0, "violations": 0},
            "keyboard": {"passed": 0, "violations": 0},
            "navigation": {"passed": 0, "violations": 0},
            "links": {"passed": 0, "violations": 0},
            "focus": {"passed": 0, "violations": 0},
            "target_size": {"passed": 0, "violations": 0},
            "language": {"passed": 0, "violations": 0},
            "aria": {"passed": 0, "violations": 0},
            "buttons": {"passed": 0, "violations": 0},
            "iframes": {"passed": 0, "violations": 0},
            "duplicate_id": {"passed": 0, "violations": 0},
            "modals": {"passed": 0, "violations": 0},
        }

        principle_counts: Dict[str, Dict[str, int]] = {
            "Perceivable": {"passed": 0, "violations": 0},
            "Operable": {"passed": 0, "violations": 0},
            "Understandable": {"passed": 0, "violations": 0},
            "Robust": {"passed": 0, "violations": 0},
        }

        def record_result(rule_id: str, passed: bool, violation: Optional[WcagViolation] = None, principle: str = "Perceivable", category: str = "images"):
            nonlocal checks_passed, total_checks_evaluated
            total_checks_evaluated += 1
            if passed:
                checks_passed += 1
                category_counts.setdefault(category, {"passed": 0, "violations": 0})["passed"] += 1
                principle_counts.setdefault(principle, {"passed": 0, "violations": 0})["passed"] += 1
            else:
                if violation:
                    violations.append(violation)
                category_counts.setdefault(category, {"passed": 0, "violations": 0})["violations"] += 1
                principle_counts.setdefault(principle, {"passed": 0, "violations": 0})["violations"] += 1

        for p in pages:
            html = getattr(p, "raw_html", None) or ""
            url = p.url
            if not html and getattr(p, "snapshot_path", None):
                try:
                    sp = Path(p.snapshot_path)
                    if sp.exists():
                        html = sp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

            if not html:
                continue

            try:
                soup = BeautifulSoup(html, "html.parser")
            except Exception:
                continue

            # =================================================================
            # PRINCIPLE 1: PERCEIVABLE
            # =================================================================

            # 1.1.1 Image Alternative Text Quality
            imgs = soup.find_all("img")
            missing_alts = []
            for img in imgs:
                role = (img.get("role") or "").lower()
                aria_hidden = img.get("aria-hidden") == "true"
                alt = img.get("alt")
                src = (img.get("src") or img.get("data-src") or "unknown").strip()

                if role in ("presentation", "none") or aria_hidden:
                    continue

                if alt is None:
                    # Check if inside a link where img has no alt and link has no text
                    parent_link = img.find_parent("a")
                    if parent_link and not parent_link.get_text(strip=True) and not parent_link.get("aria-label"):
                        missing_alts.append((src, "Image inside link without alt attribute leaves link unannounced"))
                    else:
                        missing_alts.append((src, "Missing alt attribute completely"))
                elif alt.strip().lower() in GENERIC_ALT_STRINGS:
                    missing_alts.append((src, f"Generic, non-descriptive alt='{alt}'"))
                elif alt.strip() and re.search(r"\.(jpg|png|webp|avif|svg|gif)$", alt.strip().lower()):
                    missing_alts.append((src, f"Raw image filename used as alt text: '{alt}'"))

            if missing_alts:
                sample_src, reason = missing_alts[0]
                record_result(
                    "WCAG_1_1_1_IMAGE_ALT", False,
                    WcagViolation(
                        rule_id="WCAG_1_1_1_IMAGE_ALT",
                        wcag_criterion="1.1.1 Non-text Content",
                        level="A",
                        principle="Perceivable",
                        category="images",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"{len(missing_alts)} image(s) on {url} lack descriptive alt text ({reason}).",
                        selector="img",
                        snippet=f"<img src='{sample_src[:80]}...'>",
                        url=url,
                        recommendation="Provide concise, context-rich alt text for informative images or alt='' for purely decorative graphics."
                    ),
                    principle="Perceivable", category="images"
                )
            else:
                record_result("WCAG_1_1_1_IMAGE_ALT", True, principle="Perceivable", category="images")

            # 1.3.1 Form Control Explicit Labels
            inputs = soup.find_all(["input", "select", "textarea"])
            unlabeled_inputs = []
            for inp in inputs:
                inp_type = inp.get("type", "text").lower()
                if inp_type in ["hidden", "submit", "button", "reset", "image"]:
                    continue
                inp_id = inp.get("id")
                has_label = False
                if inp_id and soup.find("label", attrs={"for": inp_id}):
                    has_label = True
                elif inp.get("aria-label") or inp.get("aria-labelledby"):
                    has_label = True
                elif inp.find_parent("label"):
                    has_label = True
                elif inp.get("title"):
                    has_label = True

                if not has_label:
                    unlabeled_inputs.append(str(inp)[:100])

            if unlabeled_inputs:
                record_result(
                    "WCAG_1_3_1_FORM_LABELS", False,
                    WcagViolation(
                        rule_id="WCAG_1_3_1_FORM_LABELS",
                        wcag_criterion="1.3.1 Info and Relationships / 3.3.2 Labels or Instructions",
                        level="A",
                        principle="Perceivable",
                        category="forms",
                        severity=Severity.HIGH,
                        impact=ImpactLevel.HIGH,
                        description=f"{len(unlabeled_inputs)} interactive form input(s) on {url} lack programmatic labels.",
                        selector="input, select, textarea",
                        snippet=unlabeled_inputs[0],
                        url=url,
                        recommendation="Associate each form element with an explicit <label for='...'> or provide an aria-label attribute."
                    ),
                    principle="Perceivable", category="forms"
                )
            else:
                record_result("WCAG_1_3_1_FORM_LABELS", True, principle="Perceivable", category="forms")

            # 1.3.1 Heading Hierarchy & Order
            headings = soup.find_all(re.compile(r"^h[1-6]$"))
            heading_levels = [int(h.name[1]) for h in headings]
            h1s = [h for h in headings if h.name == "h1"]
            if not h1s and getattr(page, "h1", None) and len(page.h1) > 0:
                h1s = [h for h in page.h1 if h.strip()]
            empty_headings = [h for h in headings if not h.get_text(strip=True)]

            hierarchy_issues = []
            if len(h1s) == 0:
                hierarchy_issues.append(f"Page ({url}) lacks a top-level <h1> heading")
            elif len(h1s) > 1:
                hierarchy_issues.append(f"Multiple ({len(h1s)}) <h1> headings compete for primary topic")

            for i in range(len(heading_levels) - 1):
                curr = heading_levels[i]
                nxt = heading_levels[i + 1]
                if nxt > curr + 1:
                    hierarchy_issues.append(f"Heading level skipped from H{curr} to H{nxt}")
                    break

            if empty_headings:
                hierarchy_issues.append(f"{len(empty_headings)} empty heading tag(s) detected")

            if hierarchy_issues:
                record_result(
                    "WCAG_1_3_1_HEADING_ORDER", False,
                    WcagViolation(
                        rule_id="WCAG_1_3_1_HEADING_ORDER",
                        wcag_criterion="1.3.1 Info and Relationships",
                        level="AA",
                        principle="Perceivable",
                        category="headings",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.LOW,
                        description=f"Heading outline issues on {url}: {'; '.join(hierarchy_issues)}.",
                        selector="h1, h2, h3, h4",
                        snippet=" -> ".join(f"h{lvl}" for lvl in heading_levels[:6]) if heading_levels else "No headings",
                        url=url,
                        recommendation="Ensure a single <h1> declares the document topic, followed sequentially by H2, H3 without skipping levels."
                    ),
                    principle="Perceivable", category="headings"
                )
            else:
                record_result("WCAG_1_3_1_HEADING_ORDER", True, principle="Perceivable", category="headings")

            # 1.3.1 Semantic Landmark Structure
            has_main = bool(soup.find("main") or soup.find(attrs={"role": "main"}))
            has_nav = bool(soup.find("nav") or soup.find(attrs={"role": "navigation"}))
            has_header_or_banner = bool(soup.find("header") or soup.find(attrs={"role": "banner"}))
            has_footer_or_info = bool(soup.find("footer") or soup.find(attrs={"role": "contentinfo"}))

            missing_landmarks = []
            if not has_main:
                missing_landmarks.append("<main>")
            if not has_nav:
                missing_landmarks.append("<nav>")

            if missing_landmarks:
                record_result(
                    "WCAG_1_3_1_LANDMARK_MAIN", False,
                    WcagViolation(
                        rule_id="WCAG_1_3_1_LANDMARK_MAIN",
                        wcag_criterion="1.3.1 Info and Relationships",
                        level="AA",
                        principle="Perceivable",
                        category="landmarks",
                        severity=Severity.LOW,
                        impact=ImpactLevel.LOW,
                        description=f"Page {url} is missing semantic landmark element(s): {', '.join(missing_landmarks)}.",
                        selector="body",
                        snippet=f"Missing: {', '.join(missing_landmarks)}",
                        url=url,
                        recommendation="Wrap the primary page content inside a semantic <main> tag and navigation within <nav> to aid assistive navigation."
                    ),
                    principle="Perceivable", category="landmarks"
                )
            else:
                record_result("WCAG_1_3_1_LANDMARK_MAIN", True, principle="Perceivable", category="landmarks")

            # 1.3.1 Data Table Headers & Semantics
            tables = soup.find_all("table")
            tables_without_headers = []
            for tbl in tables:
                role = (tbl.get("role") or "").lower()
                if role in ("presentation", "none"):
                    continue
                ths = tbl.find_all("th")
                if not ths:
                    tables_without_headers.append(str(tbl)[:80])

            if tables_without_headers:
                record_result(
                    "WCAG_1_3_1_TABLE_HEADERS", False,
                    WcagViolation(
                        rule_id="WCAG_1_3_1_TABLE_HEADERS",
                        wcag_criterion="1.3.1 Info and Relationships",
                        level="A",
                        principle="Perceivable",
                        category="tables",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"{len(tables_without_headers)} data table(s) on {url} lack programmatic <th> header cells.",
                        selector="table",
                        snippet=tables_without_headers[0],
                        url=url,
                        recommendation="Add <th> elements with scope='col' or scope='row' to all tabular data for screen reader cell association."
                    ),
                    principle="Perceivable", category="tables"
                )
            else:
                record_result("WCAG_1_3_1_TABLE_HEADERS", True, principle="Perceivable", category="tables")

            # 1.4.3 Color Contrast Ratio Minimum (4.5:1 for normal, 3:1 for large text)
            contrast_violations = []
            # Check inline styles for text and background color pairs
            elements_with_style = soup.find_all(attrs={"style": True})
            for el in elements_with_style[:100]:
                style = el.get("style", "")
                color_m = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", style, re.IGNORECASE)
                bg_m = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)", style, re.IGNORECASE)

                if color_m and bg_m:
                    fg_rgb = parse_color_to_rgb(color_m.group(1))
                    bg_rgb = parse_color_to_rgb(bg_m.group(1))
                    if fg_rgb and bg_rgb:
                        ratio = calculate_contrast_ratio(fg_rgb, bg_rgb)
                        # Check font size if present to determine 3:1 vs 4.5:1
                        is_large = bool(re.search(r"font-size\s*:\s*(?:18|19|2\d|[3-9]\d)px", style, re.IGNORECASE))
                        threshold = 3.0 if is_large else 4.5
                        if ratio < threshold:
                            text_snippet = el.get_text(strip=True)[:40] or el.name
                            contrast_violations.append((ratio, threshold, color_m.group(1).strip(), bg_m.group(1).strip(), text_snippet))

            if contrast_violations:
                ratio, thresh, fg, bg, snip = contrast_violations[0]
                record_result(
                    "WCAG_1_4_3_COLOR_CONTRAST", False,
                    WcagViolation(
                        rule_id="WCAG_1_4_3_COLOR_CONTRAST",
                        wcag_criterion="1.4.3 Contrast (Minimum)",
                        level="AA",
                        principle="Perceivable",
                        category="contrast",
                        severity=Severity.HIGH,
                        impact=ImpactLevel.HIGH,
                        description=f"Low color contrast ({ratio}:1 vs {thresh}:1 required) detected on {url} (color: {fg}, bg: {bg}).",
                        selector="[style*='color']",
                        snippet=f"Text: '{snip}' ({ratio}:1)",
                        url=url,
                        recommendation=f"Increase foreground-to-background contrast to at least 4.5:1 for body copy and 3.0:1 for large headlines."
                    ),
                    principle="Perceivable", category="contrast"
                )
            else:
                record_result("WCAG_1_4_3_COLOR_CONTRAST", True, principle="Perceivable", category="contrast")

            # 1.4.4 Viewport Zoom Scaling (Resize Text)
            meta_viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
            vp_content = meta_viewport.get("content", "") if meta_viewport else ""
            blocks_zoom = False
            if vp_content:
                if re.search(r"user-scalable\s*=\s*(?:no|0)", vp_content, re.IGNORECASE):
                    blocks_zoom = True
                elif re.search(r"maximum-scale\s*=\s*1(?:\.0)?(?:\s*[,;]|$)", vp_content, re.IGNORECASE):
                    blocks_zoom = True

            if blocks_zoom:
                record_result(
                    "WCAG_1_4_4_VIEWPORT_SCALING", False,
                    WcagViolation(
                        rule_id="WCAG_1_4_4_VIEWPORT_SCALING",
                        wcag_criterion="1.4.4 Resize Text / 2.1 Reflow",
                        level="AA",
                        principle="Perceivable",
                        category="viewport",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"The <meta name='viewport'> tag on {url} disables user zooming (maximum-scale=1.0 or user-scalable=no).",
                        selector="meta[name='viewport']",
                        snippet=f"<meta name='viewport' content='{vp_content}'>",
                        url=url,
                        recommendation="Remove 'user-scalable=no' and 'maximum-scale=1.0' to permit low-vision users to zoom up to 200%."
                    ),
                    principle="Perceivable", category="viewport"
                )
            else:
                record_result("WCAG_1_4_4_VIEWPORT_SCALING", True, principle="Perceivable", category="viewport")

            # =================================================================
            # PRINCIPLE 2: OPERABLE
            # =================================================================

            # 2.1.1 Keyboard Navigation: Positive Tabindex & Clickable Divs
            positive_tabindex = []
            for el in soup.find_all(attrs={"tabindex": True}):
                try:
                    ti = int(el.get("tabindex"))
                    if ti > 0:
                        positive_tabindex.append(str(el)[:80])
                except (ValueError, TypeError):
                    pass

            unreachable_clickables = []
            for el in soup.find_all(attrs={"onclick": True}):
                if el.name not in ("a", "button", "input", "select", "textarea"):
                    role = (el.get("role") or "").lower()
                    ti = el.get("tabindex")
                    if role != "button" or ti is None:
                        unreachable_clickables.append(str(el)[:80])

            if positive_tabindex or unreachable_clickables:
                detail = f"{len(positive_tabindex)} element(s) with positive tabindex" if positive_tabindex else f"{len(unreachable_clickables)} non-semantic element(s) with click handlers lacking keyboard accessibility"
                sample = positive_tabindex[0] if positive_tabindex else unreachable_clickables[0]
                record_result(
                    "WCAG_2_1_1_KEYBOARD_ACCESSIBLE", False,
                    WcagViolation(
                        rule_id="WCAG_2_1_1_KEYBOARD_ACCESSIBLE",
                        wcag_criterion="2.1.1 Keyboard Accessible",
                        level="A",
                        principle="Operable",
                        category="keyboard",
                        severity=Severity.HIGH,
                        impact=ImpactLevel.HIGH,
                        description=f"Keyboard navigation barriers on {url}: {detail}.",
                        selector="[tabindex], [onclick]",
                        snippet=sample,
                        url=url,
                        recommendation="Avoid positive tabindex values (use natural DOM order) and use native <button> elements for interactive actions."
                    ),
                    principle="Operable", category="keyboard"
                )
            else:
                record_result("WCAG_2_1_1_KEYBOARD_ACCESSIBLE", True, principle="Operable", category="keyboard")

            # 2.4.1 Skip Navigation Link
            nav_links = soup.find_all("nav")
            has_skip_link = False
            first_links = soup.find_all("a")[:8]
            for a in first_links:
                href = (a.get("href") or "").lower()
                text = a.get_text(strip=True).lower()
                if (href.startswith("#") and len(href) > 1 and any(term in href for term in ["main", "content", "primary"])) or "skip" in text:
                    has_skip_link = True
                    break

            if nav_links and not has_skip_link:
                record_result(
                    "WCAG_2_4_1_SKIP_NAVIGATION", False,
                    WcagViolation(
                        rule_id="WCAG_2_4_1_SKIP_NAVIGATION",
                        wcag_criterion="2.4.1 Bypass Blocks",
                        level="A",
                        principle="Operable",
                        category="navigation",
                        severity=Severity.LOW,
                        impact=ImpactLevel.LOW,
                        description=f"Page {url} has site navigation but lacks a 'Skip to Content' link for keyboard users.",
                        selector="body",
                        snippet="<body> (missing skip link)",
                        url=url,
                        recommendation="Place an accessible <a href='#main' class='sr-only focus:not-sr-only'>Skip to main content</a> as the first focusable element."
                    ),
                    principle="Operable", category="navigation"
                )
            else:
                record_result("WCAG_2_4_1_SKIP_NAVIGATION", True, principle="Operable", category="navigation")

            # 2.4.3 Focus Order & ARIA Hidden Traps
            hidden_focusable = []
            for hidden_el in soup.find_all(attrs={"aria-hidden": "true"}):
                focusables = hidden_el.find_all(["a", "button", "input", "select", "textarea"])
                for f_el in focusables:
                    if f_el.name == "a" and not f_el.get("href"):
                        continue
                    if f_el.get("tabindex") != "-1":
                        hidden_focusable.append(str(f_el)[:80])

            if hidden_focusable:
                record_result(
                    "WCAG_2_4_3_FOCUS_TRAP", False,
                    WcagViolation(
                        rule_id="WCAG_2_4_3_FOCUS_TRAP",
                        wcag_criterion="2.4.3 Focus Order / 4.1.2 Name, Role, Value",
                        level="A",
                        principle="Operable",
                        category="keyboard",
                        severity=Severity.HIGH,
                        impact=ImpactLevel.HIGH,
                        description=f"{len(hidden_focusable)} focusable element(s) on {url} are nested inside aria-hidden='true' containers.",
                        selector="[aria-hidden='true'] a, [aria-hidden='true'] button",
                        snippet=hidden_focusable[0],
                        url=url,
                        recommendation="Do not place focusable elements inside aria-hidden='true' elements, or add tabindex='-1' to prevent keyboard focus."
                    ),
                    principle="Operable", category="keyboard"
                )
            else:
                record_result("WCAG_2_4_3_FOCUS_TRAP", True, principle="Operable", category="keyboard")

            # 2.4.4 Link Purpose & Ambiguous Anchor Names
            all_links = soup.find_all("a")
            empty_links = []
            ambiguous_links = []

            for a in all_links:
                href = (a.get("href") or "").strip()
                if not href:
                    continue
                text = a.get_text(strip=True)
                aria_lbl = a.get("aria-label") or a.get("aria-labelledby") or a.get("title")
                has_img_alt = any(img.get("alt") for img in a.find_all("img") if img.get("alt"))

                if not text and not aria_lbl and not has_img_alt:
                    empty_links.append(str(a)[:80])
                elif text and not aria_lbl:
                    if text.strip().lower() in AMBIGUOUS_LINK_TEXTS:
                        ambiguous_links.append(f"'{text}' -> {href[:60]}")

            if empty_links or ambiguous_links:
                issues = []
                if empty_links:
                    issues.append(f"{len(empty_links)} link(s) lack accessible text or aria-labels")
                if ambiguous_links:
                    issues.append(f"{len(ambiguous_links)} link(s) use ambiguous anchor text ({ambiguous_links[0]})")
                record_result(
                    "WCAG_2_4_4_LINK_NAMES", False,
                    WcagViolation(
                        rule_id="WCAG_2_4_4_LINK_NAMES",
                        wcag_criterion="2.4.4 Link Purpose (In Context)",
                        level="A",
                        principle="Operable",
                        category="links",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"Link accessibility defects on {url}: {'; '.join(issues)}.",
                        selector="a",
                        snippet=empty_links[0] if empty_links else ambiguous_links[0],
                        url=url,
                        recommendation="Ensure all links contain descriptive anchor text or distinct aria-label attributes declaring destination purpose."
                    ),
                    principle="Operable", category="links"
                )
            else:
                record_result("WCAG_2_4_4_LINK_NAMES", True, principle="Operable", category="links")

            # 2.4.7 Focus Visibility (outline: none suppression)
            style_tags = soup.find_all("style")
            outline_suppression = False
            for st in style_tags:
                txt = st.get_text()
                if re.search(r":focus\s*\{[^}]*outline\s*:\s*(?:none|0)\b", txt, re.IGNORECASE):
                    if not re.search(r"box-shadow|border|outline-color", txt, re.IGNORECASE):
                        outline_suppression = True
                        break

            if outline_suppression:
                record_result(
                    "WCAG_2_4_7_FOCUS_VISIBILITY", False,
                    WcagViolation(
                        rule_id="WCAG_2_4_7_FOCUS_VISIBILITY",
                        wcag_criterion="2.4.7 Focus Visible",
                        level="AA",
                        principle="Operable",
                        category="focus",
                        severity=Severity.HIGH,
                        impact=ImpactLevel.HIGH,
                        description=f"CSS styling on {url} suppresses default focus indicators (:focus {{ outline: none; }}) without fallback styling.",
                        selector="style",
                        snippet=":focus { outline: none; }",
                        url=url,
                        recommendation="Provide a visible, high-contrast focus indicator (:focus-visible { outline: 2px solid #2563eb; }) for keyboard users."
                    ),
                    principle="Operable", category="focus"
                )
            else:
                record_result("WCAG_2_4_7_FOCUS_VISIBILITY", True, principle="Operable", category="focus")

            # 2.5.8 Target Size Minimum (WCAG 2.2 AA SC 2.5.8 >=24x24px)
            small_targets = []
            interactive_tags = soup.find_all(["button", "a"])
            for el in interactive_tags:
                style = (el.get("style") or "").lower()
                w_m = re.search(r"width\s*:\s*(\d+)px", style)
                h_m = re.search(r"height\s*:\s*(\d+)px", style)
                if w_m and h_m:
                    w, h = int(w_m.group(1)), int(h_m.group(1))
                    if (w < 24 or h < 24) and (w > 0 and h > 0):
                        small_targets.append((w, h, str(el)[:80]))

            if small_targets:
                w, h, snip = small_targets[0]
                record_result(
                    "WCAG_2_5_8_TARGET_SIZE", False,
                    WcagViolation(
                        rule_id="WCAG_2_5_8_TARGET_SIZE",
                        wcag_criterion="2.5.8 Target Size (Minimum)",
                        level="AA",
                        principle="Operable",
                        category="target_size",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"{len(small_targets)} interactive target(s) on {url} measure under the WCAG 2.2 minimum threshold of 24x24 CSS pixels ({w}x{h}px).",
                        selector="button, a",
                        snippet=snip,
                        url=url,
                        recommendation="Expand touch target bounding boxes to at least 24x24px or provide sufficient spacing between adjacent controls."
                    ),
                    principle="Operable", category="target_size"
                )
            else:
                record_result("WCAG_2_5_8_TARGET_SIZE", True, principle="Operable", category="target_size")

            # =================================================================
            # PRINCIPLE 3: UNDERSTANDABLE
            # =================================================================

            # 3.1.1 Language Declaration
            html_tag = soup.find("html")
            lang = html_tag.get("lang") if html_tag else None
            if not lang or not lang.strip() or len(lang.strip()) < 2:
                record_result(
                    "WCAG_3_1_1_LANGUAGE", False,
                    WcagViolation(
                        rule_id="WCAG_3_1_1_LANGUAGE",
                        wcag_criterion="3.1.1 Language of Page",
                        level="A",
                        principle="Understandable",
                        category="language",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.LOW,
                        description=f"The <html> root tag on {url} is missing a valid 'lang' attribute.",
                        selector="html",
                        snippet="<html>",
                        url=url,
                        recommendation="Add a valid ISO/BCP-47 lang attribute to the <html> root element (e.g. <html lang='en'>)."
                    ),
                    principle="Understandable", category="language"
                )
            else:
                record_result("WCAG_3_1_1_LANGUAGE", True, principle="Understandable", category="language")

            # 3.3.2 Input Purpose Autocomplete
            sensitive_inputs = soup.find_all("input")
            missing_autocomplete = []
            for inp in sensitive_inputs:
                itype = inp.get("type", "text").lower()
                iname = (inp.get("name") or "").lower()
                iid = (inp.get("id") or "").lower()
                combined = f"{iname} {iid}"

                if itype in ("email", "tel") or any(k in combined for k in ["email", "phone", "telephone", "postal", "zip", "city"]):
                    if not inp.get("autocomplete"):
                        missing_autocomplete.append(str(inp)[:80])

            if missing_autocomplete:
                record_result(
                    "WCAG_3_3_2_INPUT_PURPOSE", False,
                    WcagViolation(
                        rule_id="WCAG_3_3_2_INPUT_PURPOSE",
                        wcag_criterion="1.3.5 Identify Input Purpose / 3.3.2 Labels or Instructions",
                        level="AA",
                        principle="Understandable",
                        category="forms",
                        severity=Severity.LOW,
                        impact=ImpactLevel.LOW,
                        description=f"{len(missing_autocomplete)} standard user identity input(s) on {url} lack 'autocomplete' attributes.",
                        selector="input[type='email'], input[type='tel']",
                        snippet=missing_autocomplete[0],
                        url=url,
                        recommendation="Specify appropriate autocomplete attributes (e.g. autocomplete='email', autocomplete='tel') to assist autofill."
                    ),
                    principle="Understandable", category="forms"
                )
            else:
                record_result("WCAG_3_3_2_INPUT_PURPOSE", True, principle="Understandable", category="forms")

            # =================================================================
            # PRINCIPLE 4: ROBUST
            # =================================================================

            # 4.1.1 Duplicate DOM Element IDs
            all_ids = [el.get("id").strip() for el in soup.find_all(attrs={"id": True}) if el.get("id") and el.get("id").strip()]
            seen_ids = set()
            dup_ids = set()
            for x in all_ids:
                if x in seen_ids:
                    dup_ids.add(x)
                else:
                    seen_ids.add(x)

            if dup_ids:
                record_result(
                    "WCAG_4_1_1_DUPLICATE_ID", False,
                    WcagViolation(
                        rule_id="WCAG_4_1_1_DUPLICATE_ID",
                        wcag_criterion="4.1.1 Parsing",
                        level="A",
                        principle="Robust",
                        category="duplicate_id",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.LOW,
                        description=f"Duplicate DOM element ID(s) detected on {url}: {', '.join(list(dup_ids)[:4])}.",
                        selector=f"#{list(dup_ids)[0]}",
                        snippet=f"id='{list(dup_ids)[0]}'",
                        url=url,
                        recommendation="Ensure all element ID attributes are globally unique within each page document."
                    ),
                    principle="Robust", category="duplicate_id"
                )
            else:
                record_result("WCAG_4_1_1_DUPLICATE_ID", True, principle="Robust", category="duplicate_id")

            # 4.1.2 Button Accessible Names
            buttons = soup.find_all("button")
            nameless_buttons = []
            for b in buttons:
                text = b.get_text(strip=True)
                aria_lbl = b.get("aria-label") or b.get("aria-labelledby") or b.get("title")
                has_img_alt = any(img.get("alt") for img in b.find_all("img") if img.get("alt"))
                if not text and not aria_lbl and not has_img_alt:
                    nameless_buttons.append(str(b)[:80])

            if nameless_buttons:
                record_result(
                    "WCAG_4_1_2_ACCESSIBLE_NAMES", False,
                    WcagViolation(
                        rule_id="WCAG_4_1_2_ACCESSIBLE_NAMES",
                        wcag_criterion="4.1.2 Name, Role, Value",
                        level="A",
                        principle="Robust",
                        category="buttons",
                        severity=Severity.HIGH,
                        impact=ImpactLevel.HIGH,
                        description=f"{len(nameless_buttons)} <button> element(s) on {url} lack accessible names or aria-labels.",
                        selector="button",
                        snippet=nameless_buttons[0],
                        url=url,
                        recommendation="Provide concise inner text or an explicit aria-label on all button triggers (especially icon buttons)."
                    ),
                    principle="Robust", category="buttons"
                )
            else:
                record_result("WCAG_4_1_2_ACCESSIBLE_NAMES", True, principle="Robust", category="buttons")

            # 4.1.2 Iframe Descriptive Titles
            iframes = soup.find_all("iframe")
            nameless_iframes = [ifr for ifr in iframes if not ifr.get("title") or not ifr.get("title").strip()]
            if nameless_iframes:
                record_result(
                    "WCAG_4_1_2_IFRAME_TITLE", False,
                    WcagViolation(
                        rule_id="WCAG_4_1_2_IFRAME_TITLE",
                        wcag_criterion="4.1.2 Name, Role, Value",
                        level="A",
                        principle="Robust",
                        category="iframes",
                        severity=Severity.LOW,
                        impact=ImpactLevel.LOW,
                        description=f"{len(nameless_iframes)} <iframe> element(s) on {url} lack descriptive 'title' attributes.",
                        selector="iframe",
                        snippet=str(nameless_iframes[0])[:80],
                        url=url,
                        recommendation="Add a descriptive title attribute to every <iframe> describing its embedded contents."
                    ),
                    principle="Robust", category="iframes"
                )
            else:
                record_result("WCAG_4_1_2_IFRAME_TITLE", True, principle="Robust", category="iframes")

            # 4.1.2 ARIA Misuse & Invalid Roles
            aria_elements = soup.find_all(attrs={"role": True})
            invalid_roles = []
            aria_missing_states = []

            for el in aria_elements:
                role = (el.get("role") or "").strip().lower()
                if role not in VALID_ARIA_ROLES:
                    invalid_roles.append(f"role='{role}' on <{el.name}>")
                else:
                    # Check required states for interactive roles
                    if role == "tab" and not el.get("aria-selected"):
                        aria_missing_states.append(f"role='tab' missing aria-selected")
                    elif role in ("checkbox", "switch") and not el.get("aria-checked"):
                        aria_missing_states.append(f"role='{role}' missing aria-checked")
                    elif role == "combobox" and not el.get("aria-expanded"):
                        aria_missing_states.append(f"role='combobox' missing aria-expanded")

            if invalid_roles or aria_missing_states:
                detail = "; ".join((invalid_roles[:2] + aria_missing_states[:2]))
                record_result(
                    "WCAG_4_1_2_ARIA_MISUSE", False,
                    WcagViolation(
                        rule_id="WCAG_4_1_2_ARIA_MISUSE",
                        wcag_criterion="4.1.2 Name, Role, Value",
                        level="A",
                        principle="Robust",
                        category="aria",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"ARIA semantic defects detected on {url}: {detail}.",
                        selector="[role]",
                        snippet=detail,
                        url=url,
                        recommendation="Use valid W3C ARIA roles and ensure mandatory state attributes (aria-selected, aria-checked) are declared."
                    ),
                    principle="Robust", category="aria"
                )
            else:
                record_result("WCAG_4_1_2_ARIA_MISUSE", True, principle="Robust", category="aria")

            # 4.1.2 Modal Dialog Accessibility
            modals = soup.find_all(attrs={"role": re.compile(r"^(?:dialog|alertdialog)$", re.I)}) + soup.find_all("dialog")
            invalid_modals = []
            for m in modals:
                is_modal = m.get("aria-modal") == "true" or m.name == "dialog"
                has_label = bool(m.get("aria-label") or m.get("aria-labelledby"))
                if not is_modal or not has_label:
                    invalid_modals.append(str(m)[:80])

            if invalid_modals:
                record_result(
                    "WCAG_4_1_2_MODAL_ACCESSIBILITY", False,
                    WcagViolation(
                        rule_id="WCAG_4_1_2_MODAL_ACCESSIBILITY",
                        wcag_criterion="4.1.2 Name, Role, Value / 2.4.3 Focus Order",
                        level="A",
                        principle="Robust",
                        category="modals",
                        severity=Severity.MEDIUM,
                        impact=ImpactLevel.MEDIUM,
                        description=f"{len(invalid_modals)} dialog/modal container(s) on {url} lack aria-modal='true' or accessible name attributes.",
                        selector="[role='dialog'], dialog",
                        snippet=invalid_modals[0],
                        url=url,
                        recommendation="Declare aria-modal='true' on modal overlays and link a title via aria-labelledby to assist screen reader containment."
                    ),
                    principle="Robust", category="modals"
                )
            else:
                record_result("WCAG_4_1_2_MODAL_ACCESSIBILITY", True, principle="Robust", category="modals")

        # Calculate overall compliance score
        total_evals = max(1, checks_passed + len(violations))
        comp_score = round((checks_passed / total_evals) * 100, 1)

        # Conformance status
        if comp_score >= 90.0 and len([v for v in violations if v.severity == Severity.HIGH]) == 0:
            status = "PASS"
        elif comp_score >= 70.0:
            status = "NEEDS_ATTENTION"
        else:
            status = "NON_COMPLIANT"

        # Calculate principle scores
        principle_scores: Dict[str, float] = {}
        for p_name, counts in principle_counts.items():
            tot = counts["passed"] + counts["violations"]
            principle_scores[p_name] = round((counts["passed"] / max(1, tot)) * 100, 1)

        # Build category breakdown
        CATEGORY_NAMES = {
            "images": "Image Alt & Alternatives",
            "forms": "Form Labels & Input Purpose",
            "headings": "Heading Order & Structure",
            "landmarks": "Semantic Landmarks & Main",
            "tables": "Table Headers & Data Grid",
            "contrast": "Color Contrast (4.5:1 / 3:1)",
            "viewport": "Viewport Zoom Scaling",
            "keyboard": "Keyboard & Focus Order",
            "navigation": "Skip Navigation & Bypasses",
            "links": "Link Names & Ambiguity",
            "focus": "Focus Indicator Visibility",
            "target_size": "Interactive Target Size (24x24px)",
            "language": "Document Language",
            "aria": "ARIA Semantics & Roles",
            "buttons": "Button Names & Actions",
            "iframes": "Iframe Titles",
            "duplicate_id": "DOM ID Uniqueness",
            "modals": "Modal Dialogs & Traps",
        }

        category_breakdown: List[WcagCategoryScore] = []
        for cat_key, counts in category_counts.items():
            tot = counts["passed"] + counts["violations"]
            if tot > 0:
                score = round((counts["passed"] / tot) * 100, 1)
                category_breakdown.append(WcagCategoryScore(
                    category=cat_key,
                    name=CATEGORY_NAMES.get(cat_key, cat_key.title()),
                    passed=counts["passed"],
                    violations=counts["violations"],
                    score=score
                ))

        summary = WcagAuditSummary(
            total_checks_performed=total_evals,
            violations_count=len(violations),
            passed_checks_count=checks_passed,
            compliance_score=comp_score,
            conformance_status=status,
            violations=violations,
            principle_scores=principle_scores,
            category_breakdown=category_breakdown,
        )

        # Convert high and medium severity violations to formal Finding objects
        for v in violations:
            f = Finding(
                finding_id=f"ACC_{v.rule_id}_{abs(hash(v.url)) % 10000}",
                category=Category.ON_PAGE_SEO,
                severity=v.severity,
                classification=FindingClassification.VERIFIED_DEFECT,
                title=f"Accessibility: {v.wcag_criterion} ({v.rule_id})",
                description=v.description,
                recommendation=v.recommendation,
                confidence=0.95,
                evidence=[FindingEvidence(
                    url=v.url,
                    snippet=v.snippet or "",
                    rationale=v.description
                )] if v.snippet else [],
                why_it_matters="Ensures equal access for visitors using assistive technology, prevents legal ADA/WCAG exposure, and aids search crawler parsing."
            )
            findings.append(f)

        return summary, findings
