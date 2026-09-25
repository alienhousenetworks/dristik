"""
Dristik AI HTML Analyzer & Semantic Content Distiller
Extracts structured headings, body copy, and distills raw HTML (90% token reduction).
"""
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.visible import (
    CHROME_CLASS_TOKENS,
    distill_semantic_content,
    extract_main_root,
    extract_visible_page,
    heading_text,
)

# Re-exported so existing tests/crawler imports keep working.
CHROME_SELECTORS = [
    "nav",
    "footer",
    "script",
    "style",
    "svg",
    "iframe",
    "noscript",
    "[role='navigation']",
    "[role='contentinfo']",
    "[role='dialog']",
    "#mobile-menu",
    "#mobile-menu-btn",
    "#cookie-banner",
    "#contact-modal",
    "#access-blocked-screen",
    "#cursor-ship",
    ".mega-menu",
    ".mobile-submenu",
    ".cookie-banner",
]

MAIN_SELECTORS = [
    "main",
    "article",
    "[role='main']",
    "#content",
    "#main",
    "#main-content",
    ".main-content",
    ".page-content",
    ".entry-content",
    ".post-content",
    ".rich-text",
]


def calculate_readability(text: str) -> float:
    """
    Flesch Reading Ease score approximation.
    Higher score = easier to read (60-70 is standard plain English).
    """
    words = re.findall(r"\b\w+\b", text)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    if not words or not sentences:
        return 50.0

    word_count = len(words)
    sentence_count = max(1, len(sentences))

    syllable_count = 0
    for word in words:
        w = word.lower()
        count = len(re.findall(r"[aeiouy]+", w))
        if w.endswith("e") and not w.endswith("le") and len(w) > 2:
            count = max(1, count - 1)
        syllable_count += max(1, count)

    score = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
    return round(max(0.0, min(100.0, score)), 1)


def _strip_chrome(root: BeautifulSoup) -> None:
    """Legacy helper used by tests; prefer visible_text(skip_chrome=True)."""
    for selector in CHROME_SELECTORS:
        for tag in root.select(selector):
            tag.decompose()
    for tag in list(root.find_all(True)):
        classes = tag.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        tokens = {str(c).lower() for c in classes}
        if tokens & (CHROME_CLASS_TOKENS | {"sr-only", "visually-hidden"}):
            tag.decompose()


def analyze_html_content(
    soup: BeautifulSoup,
    url: str,
    evidence_store: EvidenceStore,
    extra_text: Optional[str] = None,
    extra_h1: Optional[List[str]] = None,
    extra_h2: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes HTML content and populates the EvidenceStore with verified observations.
    Merges CMS/admin copy recovered from JSON payloads when the visible DOM is a shell.
    """
    snapshot = extract_visible_page(soup)
    h1_list = list(snapshot["h1"])
    h2_list = list(snapshot["h2"])
    h3_list = list(snapshot["h3"])

    if extra_h1:
        h1_list = h1_list or list(extra_h1)
    if extra_h2:
        h2_list = h2_list or list(extra_h2)

    body_text = snapshot["main_text"] or snapshot["visible_text"]
    extras = " ".join(part for part in [extra_text or ""] if part).strip()
    visible_words = snapshot["word_count"]
    if extras and visible_words < 80:
        from app.crawl.analyzers.visible import normalize_space
        body_text = normalize_space(f"{body_text}\n{extras}")[:100_000]

    words = re.findall(r"\b\w+\b", body_text)
    word_count = len(words)
    readability = calculate_readability(body_text)

    for idx, h1 in enumerate(h1_list):
        evidence_store.add_evidence(
            source_type="dom",
            analyzer="html_analyzer",
            url=url,
            selector=f"h1:nth-of-type({idx+1})",
            text=h1,
            value={"type": "H1", "text": h1}
        )

    if not h1_list:
        evidence_store.add_evidence(
            source_type="dom",
            analyzer="html_analyzer",
            url=url,
            selector="h1",
            text="Missing H1 tag",
            value={"error": "missing_h1"}
        )

    for idx, h2 in enumerate(h2_list[:5]):
        evidence_store.add_evidence(
            source_type="dom",
            analyzer="html_analyzer",
            url=url,
            selector=f"h2:nth-of-type({idx+1})",
            text=h2,
            value={"type": "H2", "text": h2}
        )

    evidence_store.add_evidence(
        source_type="content",
        analyzer="html_analyzer",
        url=url,
        text=body_text[:300],
        value={
            "word_count": word_count,
            "readability_score": readability,
            "sample_content": body_text[:500],
            "main_selector": snapshot.get("main_selector"),
            "paragraphs": snapshot.get("paragraphs", [])[:4],
        }
    )

    return {
        "h1": h1_list,
        "h2": h2_list,
        "h3": h3_list,
        "word_count": word_count,
        "readability_score": readability,
        "distilled_text": body_text,
        "visible_text": snapshot["visible_text"],
        "paragraphs": snapshot.get("paragraphs", []),
        "cms_sources": snapshot.get("cms_sources", []),
        "embedded_word_count": snapshot.get("embedded_word_count", 0),
    }
