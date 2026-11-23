"""
Dristik AI DOM & Structural Analyzer
Extracts DOM element counts, image alt accessibility, CTAs, forms, and layout hierarchy.
"""
import re
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.visible import heading_text, is_hidden, is_site_chrome

IMAGE_ASSET_CAP = 500
_VIDEO_HOSTS = (
    "youtube.com",
    "youtube-nocookie.com",
    "youtu.be",
    "vimeo.com",
    "wistia.com",
    "wistia.net",
    "loom.com",
)
_VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v", ".m3u8")


def _first_candidate(value: str) -> str:
    first = (value or "").split(",")[0].strip()
    if not first:
        return ""
    return first.split()[0].strip()


def _resolve_url(raw: str, page_url: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith(("data:", "javascript:", "about:", "mailto:")):
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    return urljoin(page_url, raw)[:2000]


def _raw_image_src(img) -> str:
    for key in ("src", "data-src", "data-lazy-src"):
        raw = (img.get(key) or "").strip()
        if raw and not raw.lower().startswith("data:"):
            return raw
    for key in ("srcset", "data-srcset"):
        raw = _first_candidate(img.get(key) or "")
        if raw:
            return raw
    picture = img.find_parent("picture")
    if picture is not None:
        for source in picture.find_all("source"):
            raw = _first_candidate(source.get("srcset") or "") or (source.get("src") or "").strip()
            if raw:
                return raw
    return ""


def _image_format(src: str) -> str:
    src_lower = src.lower()
    for ext in ("avif", "webp", "svg", "png", "jpeg", "jpg", "gif"):
        if f".{ext}" in src_lower:
            return "jpg" if ext == "jpeg" else ext
    return "other"


def _is_video_host(host: str) -> bool:
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == name or host.endswith("." + name) for name in _VIDEO_HOSTS)


def _looks_like_video(raw: str, mime: str) -> bool:
    if (mime or "").lower().startswith("video"):
        return True
    path = raw.lower().split("?", 1)[0]
    return path.endswith(_VIDEO_EXTENSIONS)


def _video_source(video) -> str:
    raw = (video.get("src") or "").strip()
    if raw:
        return raw
    fallback = ""
    for source in video.find_all("source"):
        candidate = (source.get("src") or "").strip() or _first_candidate(source.get("srcset") or "")
        if not candidate:
            continue
        if _looks_like_video(candidate, source.get("type") or ""):
            return candidate
        if not fallback:
            fallback = candidate
    return fallback

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
    seen_image_urls = set()
    unique_image_urls = 0
    image_assets_truncated = False
    for img in images:
        src = _resolve_url(_raw_image_src(img), url)
        if not src or src in seen_image_urls:
            continue
        seen_image_urls.add(src)
        unique_image_urls += 1
        if len(image_assets) >= IMAGE_ASSET_CAP:
            image_assets_truncated = True
            continue
        alt = img.get("alt")
        w_val = img.get("width")
        h_val = img.get("height")
        has_dims = bool(w_val and h_val)
        fmt = _image_format(src)
        is_modern = fmt in ("webp", "avif", "svg")
        is_insecure = src.startswith("http://") and url.startswith("https://")

        image_assets.append({
            "url": src,
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

    video_assets: List[Dict[str, Any]] = []
    seen_video_urls = set()
    for video in soup.find_all("video"):
        src = _resolve_url(_video_source(video), url)
        if src and src in seen_video_urls:
            continue
        if src:
            seen_video_urls.add(src)
        poster = _resolve_url(video.get("poster") or "", url)
        video_assets.append({
            "url": src or None,
            "page_url": url,
            "kind": "video",
            "poster": poster or None,
            "has_source": bool(src),
        })
    for iframe in soup.find_all("iframe"):
        src = _resolve_url((iframe.get("src") or iframe.get("data-src") or ""), url)
        host = urlparse(src).hostname if src else ""
        if not src or not _is_video_host(host or "") or src in seen_video_urls:
            continue
        seen_video_urls.add(src)
        video_assets.append({
            "url": src,
            "page_url": url,
            "kind": "iframe",
            "poster": None,
            "has_source": True,
        })

    scripts = soup.find_all("script")
    scripts_count = len(scripts)

    stylesheets = soup.find_all("link", rel=lambda x: x and "stylesheet" in (x if isinstance(x, list) else [x]))
    stylesheets_count = len(stylesheets)

    from app.domain.evidence.rule_catalog import is_skip_link

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
        href = str(b.get("href") or "")
        cls_str = " ".join(b.get("class") or []) if isinstance(b.get("class"), list) else str(b.get("class") or "")
        if is_skip_link(txt, href, cls_str):
            continue
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
        "image_assets": image_assets,
        "image_assets_truncated": image_assets_truncated,
        "unique_image_urls": unique_image_urls,
        "video_assets": video_assets,
    }
