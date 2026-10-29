"""
Visible-page extractor.

Django templates, CMS HTML, and hydrated SPA shells all become a DOM.
This walks that DOM the way a person reads a screen: skip hidden/off-canvas
chrome, keep unique page copy (including content asides), and join inline
tags with spaces so "Privacy Policy" is never "PrivacyPolicy".
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from app.crawl.analyzers.dynamic_content import extract_embedded_cms_content

NON_CONTENT_TAGS = {
    "script", "style", "noscript", "template", "svg", "canvas", "iframe",
    "path", "defs", "symbol", "use", "link", "meta", "head", "source",
}

# Site chrome. Never treat a page <header> inside <main> as chrome —
# Django heroes often live in <header>.
CHROME_TAGS = {"footer"}
CHROME_ROLES = {"navigation", "contentinfo", "dialog", "alertdialog"}
CHROME_IDS = {
    "mobile-menu", "mobile-menu-btn", "cookie-banner", "contact-modal",
    "access-blocked-screen", "cursor-ship", "trail-canvas", "modal-success-overlay",
}
CHROME_ID_PREFIXES = ("mobile-", "cookie-", "modal-", "consent-")
CHROME_CLASS_TOKENS = {
    "mega-menu", "mobile-submenu", "cookie-banner", "cookie-consent",
    "site-footer", "global-nav", "navbar-collapse", "navbar", "nav-bar",
    "site-header", "site-nav", "offcanvas", "off-canvas",
}

HIDDEN_CLASS_TOKENS = {
    "hidden", "sr-only", "visually-hidden", "invisible", "opacity-0",
    "translate-x-full", "offscreen", "off-screen", "display-none",
}
RESPONSIVE_UNHIDE = re.compile(
    r"^(sm|md|lg|xl|2xl):(block|flex|grid|inline|inline-block|inline-flex|table)$"
)

BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "ul", "ol", "h1", "h2", "h3", "h4",
    "h5", "h6", "tr", "blockquote", "figcaption", "dt", "dd", "header", "main",
    "aside", "pre", "br", "address", "table", "thead", "tbody", "form", "fieldset",
    "figure", "hr",
}

MAIN_SELECTORS = [
    "main",
    "[role='main']",
    "article",
    "#content",
    "#main",
    "#main-content",
    "#page-content",
    ".main-content",
    ".page-content",
    ".entry-content",
    ".post-content",
    ".rich-text",
    ".prose",
    "#block-content",
    ".block-content",
    "[data-page-content]",
]

CHROME_HEADINGS = {
    "establish connection", "establishconnection",
    "access restricted", "accessrestricted",
    "transmission received", "protocol rejected",
}

WHITESPACE_RE = re.compile(r"[ \t]+")
WORD_RE = re.compile(r"\b\w+\b")
# Safety cap only — keep the full page a person can read.
CONTENT_CHAR_LIMIT = 100_000


def _class_tokens(el: Tag) -> Set[str]:
    raw = el.get("class") or []
    if isinstance(raw, str):
        raw = raw.split()
    return {str(c).lower() for c in raw}


def _style_hides(el: Tag) -> bool:
    # Only treat hard-hidden nodes as invisible. opacity:0 / translateX are
    # used by Django/GSAP carousels and accordions that a person can still open.
    style = (el.get("style") or "").lower().replace(" ", "")
    return "display:none" in style or "visibility:hidden" in style


def is_hidden(el: Tag) -> bool:
    """True when the node is not painted for a typical visitor."""
    if el.get("hidden") is not None:
        return True
    if str(el.get("aria-hidden") or "").lower() == "true":
        return True
    if str(el.get("type") or "").lower() == "hidden":
        return True
    if _style_hides(el):
        return True
    tokens = _class_tokens(el)
    if tokens & {"sr-only", "visually-hidden", "offscreen", "off-screen", "display-none"}:
        return True
    if "translate-x-full" in tokens and "translate-x-0" not in tokens:
        # Off-canvas duplicate menus. Carousels use inline transforms instead.
        return True
    if "hidden" in tokens:
        # Tailwind `hidden md:flex` is visible on some breakpoints — keep it.
        if any(RESPONSIVE_UNHIDE.match(t) for t in tokens):
            return False
        return True
    return False


def is_site_chrome(el: Tag) -> bool:
    """Global shell: nav bars, cookie walls, off-canvas menus, dialogs."""
    name = (el.name or "").lower()
    el_id = (el.get("id") or "").lower()
    role = (el.get("role") or "").lower()
    tokens = _class_tokens(el)

    if name in CHROME_TAGS:
        return True
    if role in CHROME_ROLES:
        return True
    if name == "nav":
        # In-page TOC / protocol lists stay — they are unique to the page.
        if el_id in {"toc", "table-of-contents"} or "toc" in tokens:
            return False
        if el.find_parent("main") or el.find_parent("article"):
            return False
        return True
    if el_id in CHROME_IDS:
        return True
    if any(el_id.startswith(prefix) for prefix in CHROME_ID_PREFIXES):
        return True
    if tokens & CHROME_CLASS_TOKENS:
        return True
    return False


def heading_text(el: Optional[Tag]) -> str:
    """Join split spans/br so 'Privacy Policy' does not become 'PrivacyPolicy'."""
    if el is None:
        return ""
    return re.sub(r"\s+", " ", visible_text(el, skip_chrome=False, skip_hidden=True)).strip()


def normalize_space(text: str) -> str:
    text = WHITESPACE_RE.sub(" ", text or "")
    lines = [line.strip() for line in text.splitlines()]
    compact: List[str] = []
    pending_blank = False
    for line in lines:
        if not line:
            pending_blank = True
            continue
        if compact and pending_blank:
            compact.append("")
        compact.append(line)
        pending_blank = False
    return "\n".join(compact).strip()


def _should_skip(el: Tag, skip_chrome: bool) -> bool:
    name = (el.name or "").lower()
    if name in NON_CONTENT_TAGS:
        return True
    if is_hidden(el):
        return True
    if skip_chrome and is_site_chrome(el):
        return True
    return False


def visible_text(root: Tag, skip_chrome: bool = False, skip_hidden: bool = True) -> str:
    """
    Depth-first visible text in reading order.
    Block tags become line breaks; inline tags become spaces.
    """
    parts: List[str] = []

    def walk(node) -> None:
        if isinstance(node, NavigableString):
            if isinstance(node, Comment):
                return
            if node.parent and (node.parent.name or "").lower() in NON_CONTENT_TAGS:
                return
            text = str(node)
            if not text:
                return
            parent_name = (node.parent.name or "").lower() if node.parent else ""
            if parent_name not in {"pre", "code", "textarea"}:
                text = re.sub(r"\s+", " ", text)
            parts.append(text)
            return
        if not isinstance(node, Tag):
            return
        name = (node.name or "").lower()
        if name in NON_CONTENT_TAGS:
            return
        if skip_hidden and is_hidden(node):
            return
        if skip_chrome and is_site_chrome(node):
            return
        if name in BLOCK_TAGS:
            parts.append("\n")
        if name == "img":
            alt = (node.get("alt") or "").strip()
            if alt and alt.lower() not in {"image", "img", "photo", "icon", "logo", "client logo"}:
                parts.append(alt)
        if name == "br":
            parts.append("\n")
            return
        for child in node.children:
            walk(child)
        if name in BLOCK_TAGS:
            parts.append("\n")

    walk(root)
    return normalize_space("".join(parts))


def extract_main_root(soup: BeautifulSoup) -> Tag:
    """
    Prefer the outermost Django/CMS page body over the global chrome shell.
    Nested <main> (a template including another <main>) is ignored.
    """
    for selector in MAIN_SELECTORS:
        try:
            matches = soup.select(selector)
        except Exception:
            continue
        # Outermost first: skip nodes nested inside an earlier match of the same kind.
        outermost: List[Tag] = []
        for el in matches:
            if any(el is other or other in el.parents for other in outermost):
                continue
            outermost.append(el)
        scored = []
        for el in outermost:
            text_len = len(visible_text(el, skip_chrome=True))
            if text_len >= 40:
                scored.append((text_len, el))
        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            return scored[0][1]

    body = soup.body or soup
    best: Optional[Tag] = None
    best_score = 0
    for el in body.find_all(["div", "section", "article"]):
        if is_hidden(el) or is_site_chrome(el):
            continue
        text = visible_text(el, skip_chrome=True)
        words = WORD_RE.findall(text)
        if len(words) < 40:
            continue
        link_words = 0
        for a in el.find_all("a"):
            link_words += len(WORD_RE.findall(a.get_text(" ", strip=True)))
        score = len(words) - int(link_words * 0.8)
        ident = f"{el.get('id') or ''} {' '.join(_class_tokens(el))}"
        if any(k in ident.lower() for k in ("content", "article", "prose", "entry", "post", "page")):
            score += 80
        if any(k in ident.lower() for k in ("nav", "menu", "footer", "cookie", "modal", "sidebar")):
            score -= 80
        if score > best_score:
            best_score = score
            best = el
    return best or body


def _unique(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        key = re.sub(r"\s+", " ", item).strip()
        if not key:
            continue
        lowered = key.lower()
        if lowered in seen:
            continue
        if lowered.replace(" ", "") in {c.replace(" ", "") for c in CHROME_HEADINGS}:
            continue
        seen.add(lowered)
        out.append(key)
    return out


def _headings(scope: Tag) -> Dict[str, List[str]]:
    result = {"h1": [], "h2": [], "h3": []}
    for level in ("h1", "h2", "h3"):
        texts = []
        for tag in scope.find_all(level):
            if is_hidden(tag) or is_site_chrome(tag):
                continue
            if tag.find_parent(is_site_chrome):
                continue
            text = heading_text(tag)
            if text:
                texts.append(text)
        result[level] = _unique(texts)
    return result


def distill_semantic_content(soup: BeautifulSoup) -> str:
    """Unique page copy: Django {% block content %} / <main>, not the site shell."""
    root = extract_main_root(soup)
    text = visible_text(root, skip_chrome=True, skip_hidden=True)
    if len(WORD_RE.findall(text)) < 20:
        # Fallback: everything visible except chrome, including content asides.
        body = soup.body or soup
        text = visible_text(body, skip_chrome=True, skip_hidden=True)
    return text[:CONTENT_CHAR_LIMIT]


def extract_visible_page(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Full structured snapshot of what a human can see, plus recovered CMS copy.
    """
    body = soup.body or soup
    main_root = extract_main_root(soup)
    main_text = visible_text(main_root, skip_chrome=True, skip_hidden=True)
    visible_all = visible_text(body, skip_chrome=True, skip_hidden=True)
    # Site-wide nav labels a person actually sees (desktop bar), not the off-canvas clone.
    nav_labels: List[str] = []
    for nav in body.find_all("nav"):
        if is_hidden(nav):
            continue
        if (nav.get("id") or "").lower().startswith("mobile"):
            continue
        label = heading_text(nav)
        if label:
            nav_labels.append(label[:240])

    headings = _headings(main_root)
    if not headings["h1"]:
        headings = _headings(body)

    embedded = extract_embedded_cms_content(soup)
    extras = (embedded.get("text") or "").strip()
    main_words = len(WORD_RE.findall(main_text))
    if extras and main_words < 80:
        merged = normalize_space(f"{main_text}\n{extras}")
        main_text = merged[:CONTENT_CHAR_LIMIT]
        visible_all = normalize_space(f"{visible_all}\n{extras}")[:CONTENT_CHAR_LIMIT]
        if not headings["h1"] and embedded.get("h1"):
            headings["h1"] = list(embedded["h1"])[:8]
        if not headings["h2"] and embedded.get("h2"):
            headings["h2"] = list(embedded["h2"])[:40]

    paragraphs = [
        p for p in (line.strip() for line in main_text.split("\n"))
        if len(p) >= 40
    ]

    return {
        "h1": headings["h1"],
        "h2": headings["h2"],
        "h3": headings["h3"],
        "main_text": main_text[:CONTENT_CHAR_LIMIT],
        "visible_text": visible_all[:CONTENT_CHAR_LIMIT],
        "paragraphs": paragraphs,
        "nav_labels": nav_labels[:8],
        "word_count": len(WORD_RE.findall(main_text)),
        "visible_word_count": len(WORD_RE.findall(visible_all)),
        "cms_sources": embedded.get("sources", []),
        "embedded_word_count": embedded.get("word_count", 0),
        "main_selector": _describe(main_root),
    }


def _describe(el: Tag) -> str:
    name = el.name or "node"
    el_id = el.get("id")
    if el_id:
        return f"{name}#{el_id}"
    tokens = list(_class_tokens(el))[:3]
    if tokens:
        return f"{name}." + ".".join(tokens)
    return name


def collect_hrefs(soup: BeautifulSoup) -> List[str]:
    """Every crawlable URL a person could reach, including hidden mega-menus."""
    hrefs: List[str] = []
    seen: Set[str] = set()

    def add(raw: Optional[str]) -> None:
        if not raw or not isinstance(raw, str):
            return
        value = raw.strip()
        if not value or value in seen:
            return
        seen.add(value)
        hrefs.append(value)

    for a in soup.find_all("a", href=True):
        add(a.get("href"))
    for area in soup.find_all("area", href=True):
        add(area.get("href"))
    for el in soup.find_all(True):
        attrs = getattr(el, "attrs", {}) or {}
        for key in ("data-href", "data-url", "data-link"):
            if key in attrs:
                add(attrs.get(key))
    return hrefs
