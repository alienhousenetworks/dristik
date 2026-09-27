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
    # WCAG 2.2: alt="" or role="presentation" indicates a decorative image that assistive tech ignores.
    decorative_images = sum(
        1 for img in images
        if (img.get("alt") == "" or (img.get("alt") is not None and not img.get("alt").strip()))
        or (img.get("role") or "").lower() in ("presentation", "none")
        or img.get("aria-hidden") == "true"
    )
    images_without_alt = sum(
        1 for img in images
        if img.get("alt") is None
        and (img.get("role") or "").lower() not in ("presentation", "none")
        and img.get("aria-hidden") != "true"
    )

    image_assets: List[Dict[str, Any]] = []
    for img in images[:50]:
        src = (img.get("src") or img.get("data-src") or "").strip()
        if not src:
            continue
        alt = img.get("alt")
        w_val = img.get("width")
        h_val = img.get("height")
        has_dims = bool(w_val and h_val)
        fmt = "other"
        src_lower = src.lower()
        for ext in ["avif", "webp", "svg", "png", "jpeg", "jpg", "gif"]:
            if f".{ext}" in src_lower:
                fmt = "jpg" if ext == "jpeg" else ext
                break
        is_modern = fmt in ("webp", "avif", "svg")
        is_insecure = src.startswith("http://") and url.startswith("https://")

        image_assets.append({
            "url": src[:200],
            "page_url": url,
            "alt_text": alt[:100] if alt else None,
            "has_alt": bool(alt and alt.strip()),
            "is_empty_alt": alt == "",
            "has_dimensions": has_dims,
            "width": w_val,
            "height": h_val,
            "format": fmt,
            "is_modern_format": is_modern,
            "is_insecure_http": is_insecure,
            "cls_risk": not has_dims
        })

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
            text=f"{images_without_alt} out of {total_images} images lack alt attributes (WCAG 2.2 non-compliant; {decorative_images} decorative images properly marked with alt=\"\")",
            value={
                "images_without_alt": images_without_alt,
                "total_images": total_images,
                "decorative_images": decorative_images
            }
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
        "cta_candidates": cta_candidates[:6],
        "image_assets": image_assets
    }
