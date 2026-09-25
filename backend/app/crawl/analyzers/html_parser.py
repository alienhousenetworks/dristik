"""
Deterministic HTML, Meta, and Heading Parser
"""
import re
from typing import Dict, Any
from bs4 import BeautifulSoup

from app.crawl.analyzers.visible import extract_visible_page, heading_text


def parse_html_page(url: str, html_content: str, status_code: int = 200, ttfb_ms: float = 0.0) -> Dict[str, Any]:
    """
    Deterministically parses HTML content to extract all on-page metadata,
    headings, tags, links, and content signals.
    """
    soup = BeautifulSoup(html_content, "lxml")
    snapshot = extract_visible_page(soup)

    title_tag = soup.find("title")
    title = heading_text(title_tag) if title_tag else None

    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    viewport = viewport_tag.get("content", "").strip() if viewport_tag else None

    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots_meta = robots_tag.get("content", "").strip() if robots_tag else None

    canonical_tag = soup.find("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
    canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else None

    h1s = snapshot["h1"]
    h2s = snapshot["h2"]
    h3s = snapshot["h3"]

    og_tags = {}
    for meta in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
        prop = meta.get("property", "")
        content = meta.get("content", "")
        if prop and content:
            og_tags[prop.lower()] = content.strip()

    twitter_tags = {}
    for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
        name = meta.get("name", "")
        content = meta.get("content", "")
        if name and content:
            twitter_tags[name.lower()] = content.strip()

    clean_text = snapshot["main_text"] or snapshot["visible_text"]
    word_count = snapshot["word_count"]

    sentence_count = max(1, len(re.split(r"[.!?]+", clean_text)))
    words = re.findall(r"\b\w+\b", clean_text)
    syllables = sum([max(1, len(re.findall(r"[aeiouyAEIOUY]+", w))) for w in words]) if words else 0
    avg_words_per_sentence = (word_count / sentence_count) if word_count else 0
    avg_syllables_per_word = (syllables / word_count) if word_count else 1.0
    flesch_score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    flesch_score = max(0.0, min(100.0, round(flesch_score, 1)))

    images = soup.find_all("img")
    total_images = len(images)
    images_without_alt = sum(1 for img in images if not img.get("alt") or not img.get("alt").strip())

    dom_elements_count = len(soup.find_all())
    scripts_count = len(soup.find_all("script"))
    stylesheets_count = len(soup.find_all("link", rel=lambda x: x and "stylesheet" in x))

    path_lower = url.lower()
    page_type = "general"
    if path_lower.endswith("/") or path_lower.count("/") <= 3:
        page_type = "homepage"
    elif any(k in path_lower for k in ["/about", "/company", "/team", "/who-we-are"]):
        page_type = "about"
    elif any(k in path_lower for k in ["/service", "/services", "/solution", "/features", "/platform"]):
        page_type = "services"
    elif any(k in path_lower for k in ["/product", "/products", "/shop", "/item"]):
        page_type = "product"
    elif any(k in path_lower for k in ["/pricing", "/plans", "/cost"]):
        page_type = "pricing"
    elif any(k in path_lower for k in ["/blog", "/news", "/article", "/posts", "/resources"]):
        page_type = "blog"
    elif any(k in path_lower for k in ["/contact", "/support", "/get-in-touch", "/reach-us"]):
        page_type = "contact"

    return {
        "url": url,
        "status_code": status_code,
        "title": title,
        "meta_description": meta_description,
        "viewport": viewport,
        "robots_meta": robots_meta,
        "canonical_url": canonical_url,
        "h1": h1s,
        "h2": h2s[:10],
        "h3": h3s[:15],
        "word_count": word_count,
        "readability_score": flesch_score,
        "clean_text_preview": clean_text[:2000],
        "og_tags": og_tags,
        "twitter_tags": twitter_tags,
        "total_images": total_images,
        "images_without_alt": images_without_alt,
        "dom_elements_count": dom_elements_count,
        "scripts_count": scripts_count,
        "stylesheets_count": stylesheets_count,
        "ttfb_ms": ttfb_ms,
        "page_type": page_type
    }
