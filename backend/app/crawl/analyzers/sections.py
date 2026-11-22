"""
Structured Page Section, Form, Navigation, and Footer Extractor (Phase 1).

Walks the rendered/parsed DOM in reading order so downstream AI agents and RAG
retrievers see every real section (hero, features, pricing, FAQ, testimonials,
forms, tables, nav CTAs, and footer trust/contact signals) instead of a flattened
text blob with chrome deleted.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.crawl.analyzers.visible import (
    WORD_RE,
    _class_tokens,
    extract_main_root,
    heading_text,
    is_hidden,
    is_site_chrome,
    visible_text,
)
from app.domain.models import PageSection

_SECTION_BODY_CHAR_CAP = 6000
_MAX_SECTIONS_PER_PAGE = 40

_SOCIAL_DOMAINS = (
    "linkedin.com", "twitter.com", "x.com", "github.com", "youtube.com",
    "instagram.com", "facebook.com", "tiktok.com", "wikidata.org",
    "wikipedia.org", "crunchbase.com", "g2.com", "trustpilot.com",
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}")
_CTA_CLASS_HINTS = ("btn", "button", "cta", "action", "primary", "signup", "sign-up", "demo", "trial", "buy", "cart")


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _css_selector(el: Tag) -> str:
    name = (el.name or "div").lower()
    el_id = (el.get("id") or "").strip()
    if el_id:
        return f"{name}#{el_id}"
    tokens = sorted(_class_tokens(el))[:2]
    if tokens:
        return f"{name}." + ".".join(tokens)
    return name


def _classify_section_role(
    idx: int,
    heading: str,
    body: str,
    dom_tag: str,
    selector: str,
    has_form: bool,
    has_table: bool,
) -> str:
    blob = f"{heading} {selector}".lower()
    body_low = body[:800].lower()
    if idx == 0 and (dom_tag == "header" or "hero" in blob or "banner" in blob or heading):
        if not any(k in blob for k in ("pricing", "faq", "footer")):
            return "hero"
    if any(k in blob for k in ("pricing", "plan", "tier", "billing", "packages")):
        return "pricing"
    if any(k in blob for k in ("faq", "frequently asked", "questions", "q&a")) or heading.strip().endswith("?"):
        return "faq"
    if any(k in blob for k in ("testimonial", "review", "customer say", "what our", "trusted by", "quotes")):
        return "testimonials"
    if any(k in blob for k in ("case stud", "customer stor", "results", "roi", "outcomes")):
        return "case_study"
    if any(k in blob for k in ("security", "compliance", "soc 2", "iso", "gdpr", "trust", "guarantee", "certified")):
        return "trust"
    if any(k in blob for k in ("about", "who we are", "our story", "mission", "team", "founded")):
        return "about"
    if any(k in blob for k in ("feature", "capabilit", "solution", "how it works", "platform", "service", "product", "benefit")):
        return "features"
    if has_form and len(body_low) < 1200:
        return "form"
    if has_table and any(k in body_low for k in ("$", "₹", "€", "£", "/mo", "month", "plan")):
        return "pricing"
    return "body"


def _extract_ctas_in_node(node: Tag) -> List[str]:
    ctas: List[str] = []
    seen = set()
    for el in node.find_all(["button", "a", "input"]):
        if is_hidden(el):
            continue
        name = (el.name or "").lower()
        if name == "input":
            itype = (el.get("type") or "").lower()
            if itype not in ("submit", "button"):
                continue
            label = (el.get("value") or el.get("aria-label") or "").strip()
        elif name == "button":
            label = heading_text(el)
        else:
            # <a> tag: treat as CTA if styled as button/cta or role=button
            role = (el.get("role") or "").lower()
            tokens = _class_tokens(el)
            is_btn_link = role == "button" or any(any(h in tok for h in _CTA_CLASS_HINTS) for tok in tokens)
            if not is_btn_link:
                continue
            label = heading_text(el)
        label = re.sub(r"\s+", " ", label).strip()
        if 2 <= len(label) <= 70 and label.lower() not in seen:
            seen.add(label.lower())
            ctas.append(label)
    return ctas[:12]


def _extract_form_dict(form: Tag, page_url: str = "") -> Dict[str, Any]:
    fields: List[Dict[str, Any]] = []
    labels_by_for: Dict[str, str] = {}
    for lbl in form.find_all("label"):
        f_for = (lbl.get("for") or "").strip()
        txt = heading_text(lbl)
        if f_for and txt:
            labels_by_for[f_for] = txt

    required_count = 0
    missing_label_count = 0
    submit_ctas: List[str] = []

    for inp in form.find_all(["input", "select", "textarea", "button"]):
        tag = (inp.name or "").lower()
        itype = (inp.get("type") or ("textarea" if tag == "textarea" else ("select" if tag == "select" else "text"))).lower()
        if itype == "hidden":
            continue
        if tag == "button" or itype in ("submit", "button"):
            btn_text = heading_text(inp) if tag == "button" else (inp.get("value") or "").strip()
            if btn_text:
                submit_ctas.append(btn_text[:60])
            continue

        inp_id = (inp.get("id") or "").strip()
        inp_name = (inp.get("name") or "").strip()
        placeholder = (inp.get("placeholder") or "").strip()
        aria_label = (inp.get("aria-label") or "").strip()
        parent_lbl = inp.find_parent("label")
        label_text = labels_by_for.get(inp_id) or aria_label or (heading_text(parent_lbl) if parent_lbl else "")
        is_req = inp.has_attr("required") or str(inp.get("aria-required") or "").lower() == "true"
        if is_req:
            required_count += 1
        if not label_text:
            missing_label_count += 1

        fields.append({
            "tag": tag,
            "type": itype,
            "name": inp_name or inp_id or None,
            "label": label_text or None,
            "placeholder": placeholder or None,
            "required": is_req,
            "autocomplete": inp.get("autocomplete"),
        })

    action_raw = (form.get("action") or "").strip()
    return {
        "selector": _css_selector(form),
        "action": urljoin(page_url, action_raw) if (action_raw and page_url) else (action_raw or None),
        "method": (form.get("method") or "get").upper(),
        "input_count": len(fields),
        "required_count": required_count,
        "missing_label_count": missing_label_count,
        "submit_ctas": submit_ctas[:4],
        "fields": fields[:30],
    }


def extract_forms_from_soup(soup: BeautifulSoup, page_url: str = "") -> List[Dict[str, Any]]:
    """Extracts all visible forms on the page with field, label, and submit metadata."""
    forms: List[Dict[str, Any]] = []
    for form in soup.find_all("form"):
        if is_hidden(form):
            continue
        f_dict = _extract_form_dict(form, page_url=page_url)
        if f_dict["input_count"] > 0 or f_dict["submit_ctas"]:
            forms.append(f_dict)
    return forms[:20]


def _extract_tables_in_node(node: Tag) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for tbl in node.find_all("table"):
        if is_hidden(tbl):
            continue
        headers = [heading_text(th) for th in tbl.find_all("th") if heading_text(th)]
        rows = tbl.find_all("tr")
        tables.append({
            "headers": headers[:12],
            "row_count": len(rows),
            "preview": visible_text(tbl, skip_chrome=False, skip_hidden=True)[:600],
        })
    return tables[:6]


def _extract_images_in_node(node: Tag, page_url: str = "") -> List[Dict[str, Any]]:
    imgs: List[Dict[str, Any]] = []
    for img in node.find_all("img"):
        if is_hidden(img):
            continue
        src = (img.get("src") or img.get("data-src") or "").strip()
        if not src:
            continue
        imgs.append({
            "src": urljoin(page_url, src) if page_url else src,
            "alt": (img.get("alt") or "").strip(),
        })
    return imgs[:12]


def _build_section_from_node(
    node: Tag,
    idx: int,
    page_url: str,
    override_heading: Optional[str] = None,
    override_level: Optional[str] = None,
    override_body: Optional[str] = None,
) -> Optional[PageSection]:
    body = override_body if override_body is not None else visible_text(node, skip_chrome=True, skip_hidden=True)
    body = body.strip()
    if not body:
        return None

    h_level = override_level
    h_text = (override_heading or "").strip()
    if not h_text:
        for lvl in ("h1", "h2", "h3", "h4"):
            h_tag = node.find(lvl)
            if h_tag and not is_hidden(h_tag):
                cand = heading_text(h_tag)
                if cand:
                    h_level = lvl
                    h_text = cand
                    break

    ctas = _extract_ctas_in_node(node)
    list_items = [
        heading_text(li)[:240]
        for li in node.find_all("li")
        if not is_hidden(li) and heading_text(li)
    ][:20]
    forms = [_extract_form_dict(f, page_url=page_url) for f in node.find_all("form") if not is_hidden(f)][:4]
    tables = _extract_tables_in_node(node)
    images = _extract_images_in_node(node, page_url=page_url)
    sel = _css_selector(node)
    dom_tag = (node.name or "section").lower()
    role = _classify_section_role(idx, h_text, body, dom_tag, sel, bool(forms), bool(tables))
    words = len(WORD_RE.findall(body))
    clipped_body = body[:_SECTION_BODY_CHAR_CAP]
    sec_id = f"sec_{idx + 1:02d}_{role}"

    return PageSection(
        section_id=sec_id,
        section_role=role,
        dom_tag=dom_tag,
        heading_level=h_level,
        heading_text=h_text[:300],
        body_text=clipped_body,
        ctas=ctas,
        list_items=list_items,
        forms=forms,
        tables=tables,
        images=images,
        word_count=words,
        selector=sel,
        content_sha256=_sha256(f"{page_url}|{sec_id}|{h_text}|{clipped_body}"),
    )


def _split_by_headings(root: Tag, page_url: str) -> List[PageSection]:
    """Fallback sectionizer for flat DOMs without <section>/<article> wrappers."""
    headings = [
        h for h in root.find_all(["h1", "h2", "h3"])
        if not is_hidden(h) and not is_site_chrome(h) and not h.find_parent(is_site_chrome)
    ]
    if not headings:
        sec = _build_section_from_node(root, 0, page_url)
        return [sec] if sec else []

    full_text = visible_text(root, skip_chrome=True, skip_hidden=True)
    sections: List[PageSection] = []
    pos = 0
    for idx, h in enumerate(headings[:_MAX_SECTIONS_PER_PAGE]):
        h_str = heading_text(h)
        if not h_str:
            continue
        start = full_text.find(h_str, pos)
        if start == -1:
            start = pos
        next_start = len(full_text)
        if idx + 1 < len(headings):
            nxt_str = heading_text(headings[idx + 1])
            if nxt_str:
                found_nxt = full_text.find(nxt_str, start + len(h_str))
                if found_nxt != -1:
                    next_start = found_nxt
        chunk_body = full_text[start:next_start].strip()
        pos = next_start
        parent = h.parent if isinstance(h.parent, Tag) else root
        sec = _build_section_from_node(
            parent,
            len(sections),
            page_url,
            override_heading=h_str,
            override_level=(h.name or "h2").lower(),
            override_body=chunk_body or h_str,
        )
        if sec:
            sections.append(sec)
    return sections


def extract_page_sections(soup: BeautifulSoup, page_url: str = "") -> List[PageSection]:
    """
    Extracts structured, non-overlapping sections from the page's main content.
    Prefers semantic <section>/<article>/<header> landmarks; falls back to heading-bounded
    splitting when pages use flat <div> layouts.
    """
    main_root = extract_main_root(soup)
    candidates: List[Tag] = []
    for el in main_root.find_all(["header", "section", "article"]):
        if is_hidden(el) or is_site_chrome(el):
            continue
        # Skip nested sections if an outer candidate already captures a small self-contained block,
        # OR keep leaf-level content sections when an outer <article>/<section> wraps multiple <section>s.
        child_sections = [c for c in el.find_all(["section", "article"], recursive=False) if not is_hidden(c)]
        if child_sections:
            continue
        if any(parent in candidates for parent in el.parents):
            continue
        text = visible_text(el, skip_chrome=True, skip_hidden=True)
        if len(WORD_RE.findall(text)) >= 6 or el.find(["form", "table", "h1", "h2"]):
            candidates.append(el)

    sections: List[PageSection] = []
    if len(candidates) >= 2:
        for el in candidates[:_MAX_SECTIONS_PER_PAGE]:
            sec = _build_section_from_node(el, len(sections), page_url)
            if sec:
                sections.append(sec)
    else:
        sections = _split_by_headings(main_root, page_url)

    return sections


def extract_nav_items(soup: BeautifulSoup, page_url: str = "") -> List[Dict[str, Any]]:
    """Extracts visible desktop navigation items and header CTAs without dropping them."""
    body = soup.body or soup
    items: List[Dict[str, Any]] = []
    seen = set()
    nav_containers: List[Tag] = []
    for nav in body.find_all(["nav", "header"]):
        if is_hidden(nav):
            continue
        nid = (nav.get("id") or "").lower()
        if nid.startswith("mobile"):
            continue
        # Avoid main content <header> heroes
        if nav.name == "header" and (nav.find_parent("main") or nav.find("h1")):
            continue
        nav_containers.append(nav)

    for container in nav_containers[:4]:
        for el in container.find_all(["a", "button"]):
            if is_hidden(el):
                continue
            label = re.sub(r"\s+", " ", heading_text(el)).strip()
            href = (el.get("href") or "").strip() if el.name == "a" else ""
            if not label or len(label) > 70:
                continue
            key = (label.lower(), href)
            if key in seen:
                continue
            seen.add(key)
            tokens = _class_tokens(el)
            is_cta = el.name == "button" or (el.get("role") or "").lower() == "button" or any(
                any(h in tok for h in _CTA_CLASS_HINTS) for tok in tokens
            )
            items.append({
                "label": label,
                "href": urljoin(page_url, href) if (href and page_url) else (href or None),
                "is_cta": is_cta,
            })
            if len(items) >= 40:
                return items
    return items


def extract_footer_info(soup: BeautifulSoup, page_url: str = "") -> Dict[str, Any]:
    """
    Preserves footer business identity, contact info, legal links, copyright, and
    observed social profile links that `skip_chrome=True` removes from body_text.
    """
    body = soup.body or soup
    footers = [
        f for f in body.find_all(["footer"])
        if not is_hidden(f)
    ]
    if not footers:
        footers = [
            el for el in body.find_all(attrs={"role": "contentinfo"})
            if not is_hidden(el)
        ]
    if not footers:
        return {}

    footer = footers[-1]
    text = visible_text(footer, skip_chrome=False, skip_hidden=True)
    emails = sorted(set(_EMAIL_RE.findall(text)))[:5]
    phones = sorted({m.strip() for m in _PHONE_RE.findall(text) if len(re.sub(r"\D", "", m)) >= 7})[:5]

    social_links: List[str] = []
    legal_links: List[Dict[str, str]] = []
    for a in footer.find_all("a", href=True):
        href = urljoin(page_url, (a.get("href") or "").strip()) if page_url else (a.get("href") or "").strip()
        label = heading_text(a)
        low_href = href.lower()
        if any(sd in low_href for sd in _SOCIAL_DOMAINS):
            if href not in social_links:
                social_links.append(href)
        elif any(k in f"{label} {low_href}".lower() for k in ("privacy", "terms", "cookie", "security", "gdpr", "legal", "refund", "return")):
            legal_links.append({"label": label[:60], "href": href})

    copyright_lines = [
        line.strip() for line in text.splitlines()
        if "©" in line or "copyright" in line.lower() or "all rights reserved" in line.lower()
    ]

    return {
        "text_excerpt": text[:2000],
        "emails": emails,
        "phones": phones,
        "social_links": social_links[:12],
        "legal_links": legal_links[:10],
        "copyright": copyright_lines[0][:200] if copyright_lines else None,
        "content_sha256": _sha256(f"{page_url}|footer|{text[:2000]}"),
    }
