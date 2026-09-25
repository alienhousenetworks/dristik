"""
Dristik AI DOM & Structural Analyzer
Extracts DOM element counts, image alt accessibility, CTAs, forms, and layout hierarchy.
"""
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.visible import heading_text, is_hidden, is_site_chrome

CTA_TERMS = [
    "get started", "sign up", "book", "demo", "buy", "start free", "contact us",
    "talk to", "try", "join", "get a quote", "initiate contact", "send message",
    "subscribe", "request", "enquire", "inquire", "schedule",
]


def analyze_dom_structure(soup: BeautifulSoup, url: str, evidence_store: EvidenceStore) -> Dict[str, Any]:
    all_elements = soup.find_all()
    dom_count = len(all_elements)

    images = soup.find_all("img")
    total_images = len(images)
    images_without_alt = sum(1 for img in images if not img.get("alt") or not img.get("alt").strip())

    scripts = soup.find_all("script")
    scripts_count = len(scripts)

    stylesheets = soup.find_all("link", rel=lambda x: x and "stylesheet" in (x if isinstance(x, list) else [x]))
    stylesheets_count = len(stylesheets)

    buttons = soup.find_all(["button", "a"])
    cta_candidates: List[str] = []
    for b in buttons:
        if is_hidden(b) or is_site_chrome(b) or b.find_parent(is_site_chrome):
            continue
        if b.find_parent(["nav", "footer", "form"]):
            continue
        if (b.get("id") or "") in {"mobile-menu-btn"}:
            continue
        txt = re.sub(r"\s+", " ", heading_text(b)).strip()
        lowered = txt.lower()
        if not txt or len(txt) > 40 or len(txt) < 2:
            continue
        if re.match(r"^\d+[\.\)]", txt):
            continue
        if any(term in lowered for term in CTA_TERMS) or lowered in {"contact", "connect", "subscribe", "learn more"}:
            if txt not in cta_candidates:
                cta_candidates.append(txt)

    evidence_store.add_evidence(
        source_type="dom",
        analyzer="dom_analyzer",
        url=url,
        text=f"Total DOM Elements: {dom_count}, Scripts: {scripts_count}, Stylesheets: {stylesheets_count}",
        value={
            "dom_elements_count": dom_count,
            "scripts_count": scripts_count,
            "stylesheets_count": stylesheets_count
        }
    )

    if images_without_alt > 0:
        evidence_store.add_evidence(
            source_type="dom",
            analyzer="dom_analyzer",
            url=url,
            selector="img",
            text=f"{images_without_alt} out of {total_images} images lack descriptive alt text",
            value={"images_without_alt": images_without_alt, "total_images": total_images}
        )

    if cta_candidates:
        evidence_store.add_evidence(
            source_type="dom",
            analyzer="dom_analyzer",
            url=url,
            selector="button, a.cta",
            text=f"Identified Primary CTAs: {', '.join(cta_candidates[:4])}",
            value={"ctas": cta_candidates[:6]}
        )

    return {
        "dom_elements_count": dom_count,
        "total_images": total_images,
        "images_without_alt": images_without_alt,
        "scripts_count": scripts_count,
        "stylesheets_count": stylesheets_count,
        "cta_candidates": cta_candidates[:6]
    }
