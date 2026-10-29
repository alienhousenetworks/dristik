"""
Dristik AI HTML Analyzer & Semantic Content Distiller
Extracts structured headings, body copy, and distills raw HTML (90% token reduction).
"""
import re
from typing import Dict, Any, List, Optional
try:
    from bs4 import BeautifulSoup
except ImportError:
    import sys
    from pathlib import Path
    _vp = Path(__file__).resolve().parent.parent.parent.parent / "venv/lib/python3.14/site-packages"
    if _vp.is_dir() and str(_vp) not in sys.path:
        sys.path.append(str(_vp))
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

    # Extract NAP & Local SEO Signals
    phone_numbers = []
    # 1. tel: links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("tel:"):
            raw_phone = href.replace("tel:", "").strip()
            if len(raw_phone) >= 7 and raw_phone not in phone_numbers:
                phone_numbers.append(raw_phone)
    # 2. Text regex for phone numbers
    phone_patterns = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", body_text)
    for p in phone_patterns:
        cleaned_p = p.strip()
        if len(cleaned_p) >= 10 and cleaned_p not in phone_numbers:
            phone_numbers.append(cleaned_p)

    addresses = []
    # <address> tags
    for addr in soup.find_all("address"):
        t = addr.get_text(" ", strip=True)
        if len(t) > 10 and t not in addresses:
            addresses.append(t[:200])
    # address class/id tokens
    for el in soup.find_all(attrs={"class": lambda x: x and any(c in str(x).lower() for c in ["street-address", "postal-address", "address-line", "office-address"])}):
        t = el.get_text(" ", strip=True)
        if len(t) > 10 and t not in addresses:
            addresses.append(t[:200])

    map_embed_urls = []
    for iframe in soup.find_all("iframe", src=True):
        src = iframe["src"]
        if "google.com/maps" in src or "maps.google.com" in src:
            map_embed_urls.append(src)

    gbp_links = []
    citation_links = []
    for a in soup.find_all("a", href=True):
        h = a["href"].lower()
        if any(g in h for g in ["maps.google.com", "google.com/maps", "goo.gl/maps", "g.page", "business.google.com"]):
            if a["href"] not in gbp_links:
                gbp_links.append(a["href"])
        if any(c in h for c in ["yelp.com", "maps.apple.com", "bing.com/maps", "yellowpages.com"]):
            if a["href"] not in citation_links:
                citation_links.append(a["href"])

    nap_data = {
        "page_url": url,
        "phone_numbers": phone_numbers[:5],
        "addresses": addresses[:5],
        "has_map_embed": len(map_embed_urls) > 0,
        "map_embed_urls": map_embed_urls[:3],
        "gbp_links": gbp_links[:3],
        "citation_links": citation_links[:5],
    }

    # Extract Content Quality & Topical Authority Signals
    data_tables_count = len(soup.find_all("table"))
    # Specific metrics: percentages, dollar/euro amounts, large counts
    stat_matches = re.findall(r"(?:[\$€£₹]\s*\d+(?:,\d+)*(?:\.\d+)?|\b\d+(?:\.\d+)?%|\b\d+(?:,\d+){1,}\b)", body_text)
    original_data_points = len(stat_matches)

    # Expert signals (bylines, author credentials)
    expert_signals = []
    for meta_a in soup.find_all("meta", attrs={"name": lambda x: x and x.lower() == "author"}):
        c = meta_a.get("content", "").strip()
        if c and c not in expert_signals:
            expert_signals.append(c)
    for el in soup.find_all(attrs={"class": lambda x: x and any(tok in str(x).lower() for tok in ["byline", "author-name", "author-bio", "entry-author"])}):
        t = el.get_text(" ", strip=True)
        if 2 < len(t) < 80 and t not in expert_signals:
            expert_signals.append(t)

    # First-party evidence markers
    evidence_phrases = [
        "our case study", "our data shows", "case study", "customer story",
        "we tested", "we found", "our survey", "methodology", "proprietary benchmark",
        "in our research", "we analyzed", "our customers achieved"
    ]
    first_party_markers = [phrase for phrase in evidence_phrases if phrase in body_text.lower()]

    # Unbacked claims (superlatives without proximate data)
    superlatives = [
        "world's best", "best-in-class", "industry leading", "#1 rated",
        "guaranteed results", "100% satisfaction", "unmatched quality",
        "revolutionary platform", "completely effortless"
    ]
    unbacked_claims = [s for s in superlatives if s in body_text.lower()]

    # Semantic Entities: multi-word phrases extracted from headings and prominent copy
    topical_entities = []
    for h in h1_list + h2_list:
        clean_h = re.sub(r"[^\w\s-]", "", h).strip()
        if len(clean_h) > 3 and clean_h not in topical_entities:
            topical_entities.append(clean_h)

    # Search Intent Classification
    low_text = body_text.lower()
    intent = "INFORMATIONAL"
    if any(k in low_text for k in ["pricing", "price", "plans", "per month", "billed annually", "cost"]):
        intent = "COMMERCIAL"
    elif any(k in low_text for k in ["buy now", "add to cart", "checkout", "subscribe now", "free trial", "get quote"]):
        intent = "TRANSACTIONAL"
    elif len(url.split("/")) <= 4 and ("login" in low_text or "sign in" in low_text or "portal" in low_text):
        intent = "NAVIGATIONAL"

    # Information Gain Heuristic (0 to 100)
    info_gain = 50.0
    if original_data_points > 5:
        info_gain += 20.0
    if data_tables_count > 0:
        info_gain += 15.0
    if first_party_markers:
        info_gain += 15.0
    if unbacked_claims and not stat_matches:
        info_gain -= 25.0
    info_gain = max(10.0, min(95.0, info_gain))

    content_authority = {
        "url": url,
        "word_count": word_count,
        "topical_entities": topical_entities[:10],
        "information_gain_score": round(info_gain, 1),
        "original_data_points": original_data_points,
        "first_party_evidence_markers": first_party_markers,
        "expert_signals": expert_signals[:3],
        "unbacked_claims": unbacked_claims[:5],
        "search_intent": intent,
        "data_tables_count": data_tables_count,
    }

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
            "nap_data": nap_data,
            "content_authority": content_authority,
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
        "nap_data": nap_data,
        "content_authority": content_authority,
    }
