"""
Recover copy that never appears as static HTML: CMS/admin fields stored in the
database and injected by JavaScript (Next.js, Nuxt, Django json_script, Wagtail
headless, React shells, JSON-LD).
"""
from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, List, Set
from bs4 import BeautifulSoup

CONTENT_KEYS = {
    "title", "seo_title", "meta_title", "og_title", "headline", "heading", "h1",
    "h2", "name", "content", "body", "html", "text", "copy", "description",
    "meta_description", "og_description", "excerpt", "intro", "summary",
    "caption", "richtext", "rich_text", "value", "message", "subtitle", "hero",
    "cta", "label", "quote", "answer", "question", "lede", "dek", "standfirst",
    "body_text", "page_title", "page_content", "rendered", "plaintext",
}

SKIP_KEYS = {
    "id", "pk", "uuid", "slug", "url", "href", "src", "hash", "token", "key",
    "class", "className", "style", "type", "pathname", "locale", "created",
    "updated", "published_at", "image", "images", "icon", "logo", "width",
    "height", "color", "colours", "colors",
}

SKIP_VALUE = re.compile(
    r"^(https?:|mailto:|tel:|/[\w\-./]+|#[0-9a-f]{3,8}|[0-9a-f]{8,}|true|false|null)$",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")


def _plain(value: str) -> str:
    text = TAG_RE.sub(" ", unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _walk_json(node: Any, out: List[str], headings: Dict[str, List[str]], depth: int = 0) -> None:
    if depth > 10 or node is None:
        return
    if isinstance(node, str):
        text = _plain(node)
        if len(text) >= 20 and not SKIP_VALUE.match(text):
            out.append(text)
        return
    if isinstance(node, list):
        for item in node[:80]:
            _walk_json(item, out, headings, depth + 1)
        return
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            if lowered in SKIP_KEYS and not isinstance(value, (dict, list)):
                continue
            if lowered in {"h1", "headline", "heading", "hero_title", "page_title", "title"} and isinstance(value, str):
                cleaned = _plain(value)
                if cleaned:
                    bucket = "h1" if lowered != "title" or len(cleaned) < 90 else "h2"
                    headings.setdefault(bucket, []).append(cleaned)
            if lowered in {"h2", "subtitle", "subheading"} and isinstance(value, str):
                cleaned = _plain(value)
                if cleaned:
                    headings.setdefault("h2", []).append(cleaned)
            if lowered in CONTENT_KEYS or isinstance(value, (dict, list, str)):
                _walk_json(value, out, headings, depth + 1)


def _parse_json_blob(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("window.") or text.startswith("var ") or text.startswith("self."):
        assign = text.split("=", 1)
        if len(assign) == 2:
            text = assign[1].strip().rstrip(";")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def extract_embedded_cms_content(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Pull human copy out of CMS/JS payloads that sit next to an empty HTML shell.
    """
    chunks: List[str] = []
    headings: Dict[str, List[str]] = {}
    sources: Set[str] = set()

    for noscript in soup.find_all("noscript"):
        text = noscript.get_text(" ", strip=True)
        if text:
            chunks.append(text)
            sources.add("noscript")

    script_ids = {
        "__NEXT_DATA__": "nextjs",
        "__NUXT_DATA__": "nuxt",
        "__NUXT__": "nuxt",
        "__remixContext": "remix",
    }

    for script in soup.find_all("script"):
        script_id = (script.get("id") or "").strip()
        script_type = (script.get("type") or "").lower()
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue

        kind = None
        if script_id in script_ids:
            kind = script_ids[script_id]
        elif script_type in {"application/json", "application/ld+json"}:
            kind = "json_script" if script_type == "application/json" else "jsonld"
        elif "application/json" in script_type:
            kind = "json_script"
        elif any(token in raw[:400] for token in ("__NEXT_DATA__", "__NUXT__", "__INITIAL_STATE__", "__PRELOADED_STATE__")):
            kind = "hydration"
        elif "self.__next_f" in raw:
            kind = "nextjs_app_router"
            # Extract serialized chunks from self.__next_f.push([1, "..."])
            rsc_matches = re.findall(r'self\.__next_f\.push\((\[.*?\])\)', raw, re.DOTALL)
            for m in rsc_matches:
                try:
                    data = json.loads(m)
                    payload_str = data[1] if isinstance(data, list) and len(data) > 1 else ""
                    if isinstance(payload_str, str) and payload_str:
                        colon_idx = payload_str.find(":")
                        if colon_idx != -1 and payload_str[:colon_idx].isalnum():
                            tag_or_id = payload_str[:colon_idx]
                            sub_str = payload_str[colon_idx + 1:]
                            try:
                                sub_parsed = json.loads(sub_str)
                                # Detect React element like ["$", "h1", null, {"children": "..."}]
                                if isinstance(sub_parsed, list) and len(sub_parsed) >= 4 and sub_parsed[0] == "$":
                                    elem_tag = str(sub_parsed[1]).lower()
                                    props = sub_parsed[3] if isinstance(sub_parsed[3], dict) else {}
                                    children = props.get("children")
                                    if elem_tag in {"h1", "h2", "h3"} and isinstance(children, str):
                                        c_clean = _plain(children)
                                        if c_clean:
                                            headings.setdefault(elem_tag, []).append(c_clean)
                                _walk_json(sub_parsed, chunks, headings)
                            except Exception:
                                _walk_json(sub_str, chunks, headings)
                        else:
                            _walk_json(payload_str, chunks, headings)
                except Exception:
                    # Fallback regex extraction of text sentences
                    sentences = re.findall(r'[A-Z][^"\\]{15,}\.?', m)
                    for s in sentences:
                        s_clean = _plain(s)
                        if len(s_clean) >= 20 and not SKIP_VALUE.match(s_clean):
                            chunks.append(s_clean)
            if rsc_matches:
                sources.add("nextjs_app_router")
                continue
        elif script_id.endswith("-data") or script.get("data-django") is not None:
            kind = "django"

        if not kind:
            continue

        parsed = _parse_json_blob(raw)
        if parsed is None:
            continue
        before = len(chunks)
        _walk_json(parsed, chunks, headings)
        if len(chunks) > before:
            sources.add(kind)

    # data-* blobs used by some CMS blocks
    for el in soup.find_all(attrs=True):
        attrs = getattr(el, "attrs", {}) or {}
        for key, value in attrs.items():
            if not isinstance(key, str) or not key.startswith("data-"):
                continue
            if not isinstance(value, str) or len(value) < 40:
                continue
            if value.strip()[:1] in "[{":
                parsed = _parse_json_blob(value)
                if parsed is not None:
                    _walk_json(parsed, chunks, headings)
                    sources.add("data_attr")

    seen: Set[str] = set()
    unique: List[str] = []
    for chunk in chunks:
        key = chunk[:180].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)

    text = re.sub(r"\s+", " ", " ".join(unique)).strip()[:8000]
    return {
        "text": text,
        "h1": headings.get("h1", [])[:6],
        "h2": headings.get("h2", [])[:10],
        "sources": sorted(sources),
        "word_count": len(re.findall(r"\b\w+\b", text)),
    }


def needs_js_render(soup: BeautifulSoup, visible_word_count: int) -> bool:
    """
    True when the first HTML response is a shell that waits for JS/CMS data.
    """
    root_ids = ["root", "__next", "app", "content", "main", "page", "__nuxt"]
    empty_root = False
    for rid in root_ids:
        el = soup.find(id=rid) or soup.find(attrs={"id": re.compile(rf"^{rid}$", re.I)})
        if el is not None and len(el.get_text(strip=True)) < 40:
            empty_root = True
            break

    html_head = str(soup)[:12000].lower()
    markers = [
        'id="root"', "id='root'", 'id="__next"', 'id="app"', "data-reactroot",
        "__next_data__", "__nuxt_data__", "__nuxt__", "ng-version",
        "data-server-rendered", "__initial_state__", "__preloaded_state__",
        "gatsby-focus-wrapper", "data-astro-cid", "wp-block-next",
    ]
    has_marker = any(m in html_head for m in markers)
    scripts = len(soup.find_all("script"))

    if has_marker and (visible_word_count < 140 or empty_root):
        return True
    if empty_root and scripts >= 4:
        return True
    if visible_word_count < 40 and scripts >= 6:
        return True
    return False
