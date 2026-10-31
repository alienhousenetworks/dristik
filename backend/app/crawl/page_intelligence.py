"""
Per-page SEO, copywriting, and UX intelligence.
The page specialist writes the judgment. Measurements remain when the model does not run.
"""
from __future__ import annotations

import asyncio
import json
import re
import logging
from typing import Any, Dict, List, Optional

from app.orchestration.runtime.base import BaseAgent
from app.orchestration.runtime.task_cards import task_card_for
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.domain.evidence.models import Evidence
from app.core.inference.prompt_compiler import load_prompt
from app.domain.models import (
    BusinessProfile,
    CopyFaqItem,
    CopyIssue,
    CopySection,
    PageCopyAudit,
    PageEvidence,
    PageReport,
    PageSeoAudit,
    PageUxSignals,
    SuggestedCopy,
)

logger = logging.getLogger("dristik.page_intelligence")

WORD_TARGETS = {
    "homepage": 400,
    "pricing": 250,
    "product": 350,
    "about": 300,
    "contact": 120,
    "docs": 400,
    "blog": 600,
    "legal": 200,
    "general": 250,
}

# Observed CTAs only. Do not invent a trial/demo button that is not on the page.
WEAK_CTAS = {"submit", "click here", "learn more", "read more", "here", "click"}
PAIN_MARKERS = re.compile(
    r"\b(problem|challenge|struggle|pain|without|bottleneck|friction|slow|manual|fragmented|waste|risk|fail)\b",
    re.I,
)


def _clip(text: Optional[str], n: int) -> str:
    value = re.sub(r"\s+", " ", (text or "").strip())
    if len(value) <= n:
        return value
    cut = value[: n - 1].rsplit(" ", 1)[0]
    return (cut or value[: n - 1]).rstrip(".,;:") + "…"


def _sentences(text: str, limit: int = 3) -> List[str]:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
    return parts[:limit]


def _status_len(value: Optional[str], low: int, high: int, missing: str = "missing") -> str:
    if not value or not value.strip():
        return missing
    length = len(value.strip())
    if length < low:
        return "too_short"
    if length > high:
        return "too_long"
    return "good"


def audit_page_seo(page: PageEvidence) -> PageSeoAudit:
    """Record what is on the page. Do not grade it or write a fix."""
    title = (page.title or "").strip()
    meta = (page.meta_description or "").strip()
    h1_count = len(page.h1 or [])
    heading_bits = []
    if page.h2:
        heading_bits.append(f"{len(page.h2)} H2")
    if page.h3:
        heading_bits.append(f"{len(page.h3)} H3")
    robots = (page.robots_meta or "").lower()
    if "noindex" in robots:
        robots_status = "noindex"
        indexability = "noindex"
    elif page.status_code and page.status_code >= 400:
        robots_status = "observed"
        indexability = f"http_{page.status_code}"
    else:
        robots_status = "observed"
        indexability = "observed"
    og_title = bool((page.og_tags or {}).get("og:title"))
    og_description = bool((page.og_tags or {}).get("og:description"))
    if og_title and og_description:
        og_status = "present"
    elif og_title or og_description:
        og_status = "partial"
    else:
        og_status = "absent"

    return PageSeoAudit(
        score=None,
        title_status="present" if title else "absent",
        title_length=len(title),
        meta_status="present" if meta else "absent",
        meta_length=len(meta),
        h1_status="absent" if h1_count == 0 else ("multiple" if h1_count > 1 else "one"),
        heading_structure=", ".join(heading_bits) if heading_bits else "no subheadings stored",
        canonical_status="present" if (page.canonical_url or "").strip() else "absent",
        robots_status=robots_status,
        og_status=og_status,
        schema_status="present" if page.schema_types else "absent",
        indexability=indexability,
        issues=[],
        strengths=[],
        recommendations=[],
    )


def audit_page_ux(page: PageEvidence) -> PageUxSignals:
    return PageUxSignals(
        cta_count=len(page.ctas or []),
        ctas=list(page.ctas or [])[:8],
        images_missing_alt=page.images_without_alt,
        total_images=page.total_images,
        internal_links=len(page.internal_links or []),
        external_links=len(page.external_links or []),
        ttfb_ms=page.ttfb_ms or 0.0,
        readability=page.readability_score or 0.0,
        word_count=page.word_count or 0,
        viewport=page.viewport,
        scripts_count=page.scripts_count or 0,
    )


NAV_NOISE = re.compile(
    r"(about us.{0,24}careers|careers.{0,24}blog|sign in|log in|cookie settings|company\s*>\s*about)",
    re.I,
)
KICKER_NOISE = re.compile(
    r"(legal\s*//|system module|system status|protocol|initialize handshake|mission brief|click to start|system_intake)",
    re.I,
)


def _clean_lead(body: str, h1: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n+", body or "") if b.strip()]
    if not blocks:
        blocks = _sentences(re.sub(r"\s+", " ", body or ""), 8)
    picked = []
    for sentence in blocks:
        lowered = sentence.lower()
        if len(sentence) < 40:
            continue
        if h1 and sentence.lower().replace(" ", "").startswith(h1.lower().replace(" ", "")[:12]):
            if len(sentence) < 80:
                continue
        if KICKER_NOISE.search(sentence) and len(sentence) < 90:
            continue
        if NAV_NOISE.search(sentence) and len(sentence) < 120:
            continue
        if sentence.count(">") >= 2 or sentence.count("|") >= 2:
            continue
        if sentence.isupper() and len(sentence) < 80:
            continue
        picked.append(re.sub(r"\s+", " ", sentence))
        if len(picked) >= 2:
            break
    return " ".join(picked)


def _pain_sentences(body: str) -> List[str]:
    found = []
    for sentence in _sentences(re.sub(r"\s+", " ", body or ""), 20):
        if PAIN_MARKERS.search(sentence) and 40 <= len(sentence) <= 240:
            found.append(sentence)
        if len(found) >= 2:
            break
    return found


def _answer_for_heading(body: str, heading: str) -> Optional[str]:
    if not heading or not body:
        return None
    tokens = [t for t in re.findall(r"[A-Za-z]{4,}", heading.lower()) if t not in {"this", "that", "with", "from", "your"}]
    if not tokens:
        return None
    for sentence in _sentences(re.sub(r"\s+", " ", body), 40):
        low = sentence.lower()
        if any(t in low for t in tokens) and 40 <= len(sentence) <= 280:
            return sentence
    return None


# Names from the old fixed outline. A page may use one of these words, but the product
# must not invent the block when the crawl did not find it.
_TEMPLATE_SECTION_NAMES = {
    "hero & opening hook",
    "problem agitation & commercial friction",
    "solution architecture & core capabilities",
    "ai answer engine faq block",
    "closing conversion banner",
    "hero and value proposition",
    "audience and problem",
    "solution explanation",
    "features and benefits",
    "final conversion cta",
}


def _observed_sections(page: PageEvidence) -> List[Dict[str, str]]:
    """Headings crawled on this URL. The names are the page's, not a template."""
    found: List[Dict[str, str]] = []
    seen = set()
    for level, headings in (("h1", page.h1 or []), ("h2", page.h2 or []), ("h3", page.h3 or [])):
        for heading in headings:
            name = re.sub(r"\s+", " ", (heading or "").strip())
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            found.append({"name": name, "level": level})
    return found


def _heading_blob(page: PageEvidence) -> str:
    return " ".join(item["name"].lower() for item in _observed_sections(page))


def _keep_page_section(section: CopySection, page: PageEvidence) -> bool:
    """Keep copy written for a section this page actually has."""
    copy = (section.suggested_copy or "").strip()
    if not copy or copy.upper() == "NOT_IN_EVIDENCE":
        return False
    name = re.sub(r"\s+", " ", (section.section_name or "").strip()).lower()
    if name in _TEMPLATE_SECTION_NAMES and name not in _heading_blob(page):
        return False
    return True


def _build_default_sections(
    page: PageEvidence,
    profile: BusinessProfile,
    h1: str,
    hero: str,
    primary_cta: str,
    secondary_cta: Optional[str],
    points: List[str],
    brand: str,
) -> List[CopySection]:
    """Unused by the live audit. Observed headings only, with no invented outline."""
    del profile, h1, hero, primary_cta, secondary_cta, points, brand
    sections: List[CopySection] = []
    for item in _observed_sections(page):
        sections.append(
            CopySection(
                section_id=item["level"],
                section_name=item["name"],
                status="INSUFFICIENT_EVIDENCE",
                current_preview=item["name"],
                suggested_copy="",
                purpose="Heading crawled on this URL. A specialist has not written replacement copy.",
            )
        )
    return sections


def _build_default_faqs(
    brand: str,
    offer: str,
    audience: str,
    page: Optional[PageEvidence] = None,
) -> List[CopyFaqItem]:
    del brand
    headline = (page.h1[0] if page and page.h1 else (page.title if page else "") or "").strip()
    subtopics = [h.strip() for h in (page.h2 or []) if h.strip() and len(h.strip()) < 80][:4] if page else []
    meta_desc = (page.meta_description or "").strip() if page else ""
    page_cta = (page.ctas[0].strip() if page and page.ctas else "")
    body = (page.body_text or "") if page else ""
    clean_offer = offer if (offer and "unknown" not in offer.lower() and "not clearly" not in offer.lower()) else (meta_desc or headline)

    del audience, clean_offer, page_cta, meta_desc
    items: List[CopyFaqItem] = []
    if headline:
        a1 = _answer_for_heading(body, headline)
        if a1:
            items.append(CopyFaqItem(question=headline if headline.endswith("?") else f"What is {headline}?", answer=a1))
    for heading in subtopics:
        answer = _answer_for_heading(body, heading)
        if answer:
            items.append(CopyFaqItem(question=heading if heading.endswith("?") else f"What is {heading}?", answer=answer))
    return items


def _build_default_geo_snippet(
    brand: str,
    offer: str,
    audience: str,
    page: Optional[PageEvidence] = None,
) -> str:
    lead = _clean_lead((page.body_text or "") if page else "", (page.h1[0] if page and page.h1 else ""))
    bits = []
    if brand:
        bits.append(brand)
    if offer and "not clearly" not in offer.lower():
        bits.append(offer)
    elif page and (page.meta_description or page.h1):
        bits.append((page.meta_description or page.h1[0]).strip())
    if audience and "unknown" not in audience.lower():
        bits.append(f"For {audience}.")
    if page and page.h2:
        bits.append("On-page sections: " + ", ".join([h.strip() for h in page.h2 if h.strip()][:3]) + ".")
    snippet = lead or " ".join(bits)
    if not snippet:
        snippet = f"{brand or 'This organization'} delivers specialized capabilities and verified solutions designed to meet high industry standards."
    return _clip(snippet, 420)


def _fallback_suggested(page: PageEvidence, profile: BusinessProfile) -> SuggestedCopy:
    brand = (profile.business_name or "").strip()
    if brand.lower() in {"unknown", "unknown business", ""}:
        brand = ""
    offer = profile.value_proposition if profile.value_proposition and "not clearly" not in profile.value_proposition.lower() else ""
    h1 = (page.h1[0] if page.h1 else page.title or "What this page is for").strip()
    observed_ctas = [re.sub(r"\s+", " ", c).strip() for c in (page.ctas or []) if c and c.strip()]
    intent = (profile.primary_intent.value if hasattr(profile.primary_intent, "value") else str(profile.primary_intent or "")).lower()
    default_cta = "Get in touch" if "lead" in intent else ("Get started" if "saas" in intent else "Contact us")
    primary = observed_ctas[0] if observed_ctas else default_cta
    secondary = observed_ctas[1] if len(observed_ctas) > 1 else None

    legal = page.page_type == "legal"
    title_core = h1
    current_title = (page.title or "").strip()
    if legal and current_title:
        title = current_title
    else:
        title = f"{title_core} | {brand}" if brand and brand.lower() not in title_core.lower() else title_core
        title = _clip(title, 60)

    body = page.body_text or ""
    hero_src = _clean_lead(body, h1) or ("" if legal else offer) or h1
    hero = _clip(hero_src, 280)

    hook_3sec = f"{brand + ': ' if brand else ''}{offer or h1}"
    geo_snippet = _build_default_geo_snippet(brand, offer, profile.target_audience, page=page)
    faq_items = _build_default_faqs(brand, offer, profile.target_audience, page=page)

    if legal:
        meta = (page.meta_description or "").strip() or _clip(hero, 155)
        notes = "Legal page: keep current policy language; only tighten headings and opening summary."
        points = [h.strip() for h in (page.h2 or []) if h.strip()][:6]
        body_rewrite = "\n\n".join([h1, hero] + points[:6])
        legal_cta = primary if page.ctas and primary.lower() not in {"contact", "get a quote", "start free trial"} else ""
        sections_list = _build_default_sections(
            page=page,
            profile=profile,
            h1=h1,
            hero=hero,
            primary_cta=legal_cta,
            secondary_cta=None,
            points=points,
            brand=brand,
        )
        return SuggestedCopy(
            title=title,
            meta_description=_clip(meta, 160),
            h1=_clip(h1, 80),
            hero=hero,
            primary_cta=legal_cta,
            secondary_cta=None,
            supporting_points=points,
            body_rewrite=body_rewrite,
            geo_snippet=geo_snippet,
            hook_3sec=hook_3sec,
            sections=sections_list,
            faq_items=faq_items,
            notes=notes,
        )

    meta_src = (page.meta_description or "").strip() or offer or hero or h1
    meta = _clip(meta_src, 155)
    points = [h.strip() for h in (page.h2 or []) if h.strip()][:4]
    if len(points) < 2 and offer:
        points.append(offer)

    sections_text = [h1, hero]
    if points:
        sections_text.append("\n".join(f"- {p}" for p in points[:4]))
    if offer:
        sections_text.append(offer)
    sections_text.append(primary)
    body_rewrite = "\n\n".join(s for s in sections_text if s)

    sections_list = _build_default_sections(
        page=page,
        profile=profile,
        h1=h1,
        hero=hero,
        primary_cta=primary,
        secondary_cta=secondary,
        points=points,
        brand=brand,
    )

    return SuggestedCopy(
        title=title,
        meta_description=meta,
        h1=_clip(h1, 70),
        hero=hero,
        primary_cta=primary,
        secondary_cta=secondary,
        supporting_points=points[:5],
        body_rewrite=body_rewrite,
        geo_snippet=geo_snippet,
        hook_3sec=hook_3sec,
        sections=sections_list,
        faq_items=faq_items,
        notes="Deterministic draft from crawled title, headings, CTAs, and body. LLM rewrite runs when a model key is present. Nothing here is an invented feature, metric, or testimonial.",
    )


def _compute_geo_score(page: PageEvidence) -> float:
    """Deterministic extractability score from this URL only. Not a live citation rate."""
    score = 20.0
    body = (page.body_text or "")
    if any(t.lower() in {"faqpage", "question", "qapage"} for t in (page.schema_types or [])):
        score += 25
    if "faq" in body.lower() or re.search(r"\bQ\s*[:.]|\bA\s*[:.]", body):
        score += 15
    lead = _clean_lead(body, page.h1[0] if page.h1 else "")
    if 40 <= len(lead.split()) <= 80:
        score += 20
    elif lead:
        score += 10
    if page.h2:
        score += min(15, len(page.h2) * 4)
    if page.schema_types:
        score += 10
    return max(0.0, min(100.0, round(score, 1)))


def fallback_copy_audit(page: PageEvidence, profile: BusinessProfile, seo: PageSeoAudit) -> PageCopyAudit:
    """Offline page record. Measurements only. The copy specialist writes the judgment."""
    h1 = page.h1[0] if page.h1 else ""
    ctas = ", ".join((page.ctas or [])[:3]) or "none stored"
    audience = (profile.target_audience or "").strip()
    analysis = (
        f"Measured on {page.url}: title {len((page.title or '').strip())} characters "
        f"({seo.title_status}), meta {len((page.meta_description or '').strip())} characters "
        f"({seo.meta_status}), H1 {h1 or 'absent'}, {page.word_count} words, "
        f"{len(page.h2 or [])} H2 headings, CTAs: {ctas}. "
        "A copy specialist has not written a judgment for this page."
    )
    return PageCopyAudit(
        score=None,
        voice="",
        clarity="",
        persuasion="",
        audience_fit=audience,
        cta_quality="",
        geo_score=None,
        seo_score=0.0,
        issues=[],
        what_works=[],
        analysis=analysis,
        suggested=None,
        specialist_insights={
            "seo": f"Title {len((page.title or '').strip())} characters ({seo.title_status}). Meta {len((page.meta_description or '').strip())} characters ({seo.meta_status}).",
            "cro": f"CTAs stored: {ctas}.",
            "clarity": f"Word count {page.word_count}. Readability {page.readability_score or 0:.0f}.",
        },
        llm_status="skipped",
        llm_failure_reason=None,
        llm_failure_code=None,
    )


def validate_and_clip_copy(sug: SuggestedCopy, brand_name: Optional[str] = None) -> SuggestedCopy:
    """Keep the specialist's words. Do not pad or trim them to a character band."""
    del brand_name
    sug.title = re.sub(r"\s+", " ", (sug.title or "").strip())
    sug.meta_description = re.sub(r"\s+", " ", (sug.meta_description or "").strip())
    sug.hero = re.sub(r"\s+", " ", (sug.hero or "").strip())
    return sug


def _clean_text(value: Any, collapse: bool = True) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if collapse:
        text = re.sub(r"\s+", " ", text)
    return text


def _first_text(blob: Dict[str, Any], *keys: str, collapse: bool = True) -> str:
    for key in keys:
        text = _clean_text(blob.get(key), collapse=collapse)
        if text:
            return text
    return ""


def _suggested_blob(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Find the rewrite object whether the model nested it or used title_tag."""
    if not isinstance(raw, dict):
        return {}
    for key in ("suggested", "rewrite", "proposed", "recommendations", "copy"):
        blob = raw.get(key)
        if isinstance(blob, dict) and blob:
            return blob
    field_keys = (
        "title", "title_tag", "proposed_title", "recommended_title",
        "meta_description", "meta", "description",
        "h1", "hero", "hook_3sec", "hook", "geo_snippet",
        "primary_cta", "sections", "faq_items", "faqs",
    )
    if any(_clean_text(raw.get(key), collapse=False) or raw.get(key) for key in field_keys):
        return raw
    return {}


def _parse_copy_result(raw: Dict[str, Any], fallback: PageCopyAudit, brand_name: Optional[str] = None) -> PageCopyAudit:
    suggested_raw = _suggested_blob(raw)
    issues_raw = raw.get("issues") or []
    issues: List[CopyIssue] = []
    for item in issues_raw:
        if not isinstance(item, dict):
            continue
        issue_text = str(item.get("issue") or "").strip()
        if not issue_text:
            continue
        issues.append(
            CopyIssue(
                area=str(item.get("area") or "body"),
                severity=str(item.get("severity") or "MEDIUM").upper(),
                issue=issue_text,
                why_it_matters=str(item.get("why_it_matters") or ""),
            )
        )

    sections_raw = suggested_raw.get("sections") or suggested_raw.get("section_rewrites") or []
    sections: List[CopySection] = []
    if isinstance(sections_raw, list) and sections_raw:
        for s in sections_raw:
            if not isinstance(s, dict):
                continue
            sections.append(
                CopySection(
                    section_id=str(s.get("section_id") or s.get("id") or "section"),
                    section_name=_first_text(s, "section_name", "name", "section") or "Section",
                    status=str(s.get("status") or "UPDATE_RECOMMENDED"),
                    current_preview=s.get("current_preview") or s.get("current_copy"),
                    suggested_copy=_first_text(s, "suggested_copy", "rewrite", "proposed_copy", "copy", "replacement", collapse=False),
                    purpose=str(s.get("purpose") or ""),
                    seo_geo_notes=s.get("seo_geo_notes"),
                    keywords=list(s.get("keywords") or []),
                )
            )
    if not sections and fallback.suggested is not None:
        sections = list(fallback.suggested.sections)

    faqs_raw = suggested_raw.get("faq_items") or suggested_raw.get("faqs") or suggested_raw.get("faq") or []
    faq_items: List[CopyFaqItem] = []
    if isinstance(faqs_raw, list) and faqs_raw:
        for f in faqs_raw:
            if not isinstance(f, dict):
                continue
            faq_items.append(
                CopyFaqItem(
                    question=str(f.get("question") or "").strip(),
                    answer=str(f.get("answer") or "").strip(),
                    target_engine=str(f.get("target_engine") or "ChatGPT / Perplexity / Google AI Overviews"),
                )
            )
    prior = fallback.suggested
    if not faq_items and prior is not None:
        faq_items = list(prior.faq_items)

    geo_snippet = _first_text(suggested_raw, "geo_snippet", "snippet", "citation_snippet", "definition") or (prior.geo_snippet if prior else "") or ""
    hook_3sec = _first_text(suggested_raw, "hook_3sec", "hook", "three_second_hook", "first_impression") or (prior.hook_3sec if prior else "") or ""

    sug = SuggestedCopy(
        title=_first_text(suggested_raw, "title", "title_tag", "proposed_title", "recommended_title") or (prior.title if prior else ""),
        meta_description=_first_text(suggested_raw, "meta_description", "proposed_meta_description", "meta", "description") or (prior.meta_description if prior else ""),
        h1=_first_text(suggested_raw, "h1", "headline", "h1_headline", "proposed_h1") or (prior.h1 if prior else ""),
        hero=_first_text(suggested_raw, "hero", "hero_subhead", "subheadline", "subhead") or (prior.hero if prior else ""),
        primary_cta=_first_text(suggested_raw, "primary_cta", "cta", "primary_cta_text") or (prior.primary_cta if prior else ""),
        secondary_cta=_first_text(suggested_raw, "secondary_cta", "secondary_cta_text") or (prior.secondary_cta if prior else None),
        supporting_points=list(suggested_raw.get("supporting_points") or (prior.supporting_points if prior else [])),
        body_rewrite=_first_text(suggested_raw, "body_rewrite", "full_rewrite", "body", collapse=False) or (prior.body_rewrite if prior else ""),
        geo_snippet=geo_snippet,
        hook_3sec=hook_3sec,
        sections=sections,
        faq_items=faq_items,
        notes=suggested_raw.get("notes") or (prior.notes if prior else None),
    )
    sug = validate_and_clip_copy(sug, brand_name=brand_name)

    def _bounded(value: Any, fallback_value: Optional[float]) -> Optional[float]:
        if value is None or value == "":
            return fallback_value
        try:
            return max(0.0, min(100.0, round(float(value), 1)))
        except (TypeError, ValueError):
            return fallback_value

    score_n = _bounded(raw.get("score"), fallback.score)
    geo_score_n = _bounded(raw.get("geo_score"), fallback.geo_score)
    seo_score_n = _bounded(raw.get("seo_score"), fallback.seo_score if fallback.seo_score else None)

    specialist_insights_raw = raw.get("specialist_insights") or {}
    insights = dict(fallback.specialist_insights)
    if isinstance(specialist_insights_raw, dict):
        for k, v in specialist_insights_raw.items():
            insights[str(k)] = str(v)

    return PageCopyAudit(
        score=score_n,
        voice=str(raw.get("voice") or ""),
        clarity=str(raw.get("clarity") or ""),
        persuasion=str(raw.get("persuasion") or ""),
        audience_fit=str(raw.get("audience_fit") or fallback.audience_fit or ""),
        cta_quality=str(raw.get("cta_quality") or ""),
        geo_score=geo_score_n,
        seo_score=float(seo_score_n or 0.0),
        issues=issues,
        what_works=list(raw.get("what_works") or []),
        analysis=str(raw.get("analysis") or ""),
        suggested=sug,
        specialist_insights=insights,
        llm_status="ok",
        llm_failure_reason=None,
        llm_failure_code=None,
    )


def _fail_copy_audit(copy: PageCopyAudit, seo: PageSeoAudit, reason: str, code: str) -> PageCopyAudit:
    """The model did not write this page. Do not keep a checklist verdict in its place."""
    analysis = (
        f"The page specialist did not write a judgment. {reason} "
        f"Title state {seo.title_status}, {seo.title_length} characters."
    )
    return PageCopyAudit(
        score=None,
        voice="",
        clarity="",
        persuasion="",
        audience_fit="",
        cta_quality="",
        geo_score=None,
        seo_score=0.0,
        issues=[],
        what_works=list(copy.what_works or []),
        analysis=analysis,
        suggested=None,
        specialist_insights={},
        llm_status="failed",
        llm_failure_reason=reason,
        llm_failure_code=code,
    )


class PageIntelligenceAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_page_intelligence", capability="content_intelligence", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = blackboard.pages or []
        profile = blackboard.business_profile or BusinessProfile()
        reports: List[PageReport] = []
        semaphore = asyncio.Semaphore(3)

        # Identify top strategic pages for deep LLM copywriting
        # Priority: Homepage first (0), then pricing (1), product/services (2), about/contact (3), other (4)
        def _page_priority(p: PageEvidence) -> int:
            u = (p.url or "").lower()
            if u.rstrip("/").count("/") <= 2 or p.page_type == "homepage":
                return 0
            if any(k in u for k in ("pricing", "plans", "tier", "price")):
                return 1
            if any(k in u for k in ("product", "features", "solutions", "services")):
                return 2
        async def one(page: PageEvidence) -> PageReport:
            async with semaphore:
                return await self._analyze_page(page, profile, blackboard, enable_llm_copy=True)

        if pages:
            reports = await asyncio.gather(*[one(p) for p in pages])
            reports = list(reports)

        blackboard.page_reports = reports

        for report in reports:
            if report.copywriting.llm_status != "ok":
                continue
            page_ev_ids = [ev.id for ev in blackboard.evidence_store.get_all() if getattr(ev, "url", None) == report.url][:3]
            if not page_ev_ids:
                continue
            for copy_issue in report.copywriting.issues[:4]:
                sev = Severity.HIGH if copy_issue.severity == "HIGH" else Severity.MEDIUM
                area_l = (copy_issue.area or "").lower()
                sugg = report.copywriting.suggested
                extra_sugg = ""
                if sugg:
                    if ("h1" in area_l or "hero" in area_l or "headline" in area_l) and getattr(sugg, "h1", None):
                        extra_sugg = f" Suggested H1: {sugg.h1}"
                    elif "title" in area_l and getattr(sugg, "title", None):
                        extra_sugg = f" Suggested Title: {sugg.title}"
                    elif ("meta" in area_l or "description" in area_l) and getattr(sugg, "meta_description", None):
                        extra_sugg = f" Suggested Meta Description: {sugg.meta_description}"
                    elif "cta" in area_l and getattr(sugg, "primary_cta", None):
                        extra_sugg = f" Suggested CTA: {sugg.primary_cta}"
                self.register_claim(
                    blackboard=blackboard,
                    statement=f"{report.url} copy — {copy_issue.area}: {copy_issue.issue}",
                    category=Category.CONTENT,
                    severity=sev,
                    confidence=0.9,
                    evidence_refs=page_ev_ids,
                    recommendation=f"Replace {copy_issue.area} copy.{extra_sugg}",
                    impact=8,
                    effort=3,
                )

        scores = [r.overall_score for r in reports if r.overall_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        blackboard.log_step(
            "Per-page SEO and copy reports completed",
            self.agent_id,
            {"pages": len(reports), "avg_score": avg_score},
        )
        return {"page_reports": len(reports)}

    def _page_to_evidence(self, page: PageEvidence, blackboard: Optional[CognitiveBlackboard] = None) -> List[Evidence]:
        slices: List[Evidence] = []
        n = 0

        def add(kind: str, text: Optional[str], sel: Optional[str] = None) -> None:
            nonlocal n
            value = (text or "").strip()
            if not value:
                return
            n += 1
            slices.append(
                Evidence(
                    id=f"ev_pg_{n:03d}",
                    source_type=kind,
                    analyzer="page_intelligence",
                    hash=f"pg_{n}_{kind}",
                    url=page.url,
                    text=value[:800],
                    selector=sel,
                )
            )

        add("title", page.title)
        add("meta", page.meta_description)
        for h in page.h1[:3]:
            add("h1", h)
        for h in page.h2[:8]:
            add("h2", h)
        for c in (page.ctas or [])[:6]:
            add("cta", c)
        add("body", (page.body_text or "")[:4000])
        if page.schema_types:
            add("schema", ", ".join(page.schema_types))

        if blackboard and getattr(blackboard, "evidence_store", None):
            try:
                for ev in blackboard.evidence_store.get_all()[:40]:
                    if ev.url and page.url and ev.url.rstrip("/") == page.url.rstrip("/"):
                        slices.append(ev)
            except Exception:
                logger.debug("Could not merge blackboard evidence for %s", page.url)
        return slices

    async def _analyze_page(
        self,
        page: PageEvidence,
        profile: BusinessProfile,
        blackboard: Optional[CognitiveBlackboard] = None,
        enable_llm_copy: bool = True,
    ) -> PageReport:
        seo = audit_page_seo(page)
        ux = audit_page_ux(page)
        copy = fallback_copy_audit(page, profile, seo)
        if enable_llm_copy:
            try:
                copy = await self._llm_copy(page, profile, copy, blackboard)
            except Exception as exc:
                logger.warning("LLM page copy failed for %s: %s", page.url, exc)
                copy = _fail_copy_audit(copy, seo, str(exc), "llm_exception")
        overall = round(copy.score, 1) if copy.llm_status == "ok" and copy.score is not None else None
        findings = [i.issue for i in copy.issues[:6]] if copy.llm_status == "ok" else []
        return PageReport(
            url=page.url,
            page_type=page.page_type,
            title=page.title,
            overall_score=overall,
            seo=seo,
            copywriting=copy,
            ux=ux,
            findings=findings[:8],
        )

    async def _llm_copy(
        self,
        page: PageEvidence,
        profile: BusinessProfile,
        fallback: PageCopyAudit,
        blackboard: Optional[CognitiveBlackboard] = None,
    ) -> PageCopyAudit:
        intent = profile.primary_intent.value if hasattr(profile.primary_intent, "value") else str(profile.primary_intent)

        # Cross-pillar audit gaps from SEO, GEO, CRO, and AEO
        pillar_gaps = []
        if blackboard and getattr(blackboard, "findings", None):
            for f in blackboard.findings:
                f_urls = [str(u).rstrip("/") for u in (getattr(f, "affected_urls", []) or [])]
                if page.url and (page.url.rstrip("/") in f_urls or not f_urls):
                    c_name = getattr(getattr(f, "category", None), "value", str(getattr(f, "category", "AUDIT")))
                    t_name = getattr(f, "title", None) or getattr(f, "finding_title", "")
                    why_txt = getattr(f, "why_it_matters", "") or getattr(f, "description", "")
                    pillar_gaps.append(f"[{c_name}] {t_name}: {why_txt[:120]}")

        context = {
            "url": page.url,
            "page_type": page.page_type,
            "title": page.title,
            "meta_description": page.meta_description,
            "h1": page.h1,
            "h2": page.h2[:12],
            "h3": (page.h3 or [])[:12],
            "observed_sections": _observed_sections(page),
            "ctas": page.ctas,
            "word_count": page.word_count,
            "readability": page.readability_score,
            "body": (page.body_text or "")[:12000],
            "business_name": profile.business_name,
            "audience": profile.target_audience,
            "value_proposition": profile.value_proposition,
            "intent": intent,
            "pillar_audit_gaps": pillar_gaps[:8],
        }
        evidence_list = self._page_to_evidence(page, blackboard)
        page_prompt = load_prompt("page_intel")
        observed = _observed_sections(page)
        observed_names = ", ".join(item["name"] for item in observed) or "no headings were stored"
        result = await self.model_router.generate_structured(
            capability="content_intelligence",
            agent_role="Page copywriter. Write for this URL's own sections. Evidence only.",
            task_contract=(
                (page_prompt + "\n\n") if page_prompt else ""
            ) + (
                "Write copy for THIS URL only. Use <evidence> and <site_facts>.\n"
                f"Observed sections on this page: {observed_names}.\n"
                "Every company has a different page structure. Do not reuse a hero, problem, solution, "
                "features, FAQ, or closing-banner outline unless that block is one of the observed sections.\n"
                "For each observed section that needs new wording, add one sections[] item. "
                "section_name must be that section's name from this page. suggested_copy is the replacement "
                "for that section only.\n"
                "Omit a section that does not need a change. Do not invent a section the crawl did not find.\n"
                "Write a title, meta description, H1, or call to action only when this page has that element "
                "and it should change. Leave the field empty otherwise.\n"
                "A question and answer belongs in faq_items only when this page already asks it and the answer "
                "is in the crawled text.\n"
                "Do not apply a character quota. Do not add features, metrics, customers, timelines, or offers "
                "that are not already on the page."
            ),
            task_card=task_card_for("copywriting.section.v3"),
            evidence_list=evidence_list,
            site_facts=context,
            allow_fallback=False,
            rubric=(
                "Judge only this URL. Name sections the way this page names them.\n"
                "Write replacement copy only for a section that needs it.\n"
                "Leave a field empty rather than filling a template or a character band.\n"
                "Do not invent features, metrics, customers, or calls to action that are not on the page."
            ),
            output_schema_desc=(
                "{\n"
                '  "score": 0-100,\n'
                '  "seo_score": 0-100,\n'
                '  "geo_score": 0-100,\n'
                '  "voice": "string",\n'
                '  "clarity": "string",\n'
                '  "persuasion": "string",\n'
                '  "audience_fit": "string",\n'
                '  "cta_quality": "string",\n'
                '  "specialist_insights": {\n'
                '    "seo": "string",\n'
                '    "geo": "string",\n'
                '    "cro": "string",\n'
                '    "clarity": "string",\n'
                '    "sections": "string"\n'
                '  },\n'
                '  "what_works": ["string"],\n'
                '  "analysis": "2-4 sentence critique",\n'
                '  "issues": [{"area": "title|meta|h1|hero|cta|body|faq|sections", "severity": "HIGH|MEDIUM|LOW", "issue": "string", "why_it_matters": "string"}],\n'
                '  "suggested": {\n'
                '    "title": "string",\n'
                '    "meta_description": "string",\n'
                '    "h1": "string",\n'
                '    "hero": "string",\n'
                '    "hook_3sec": "string",\n'
                '    "geo_snippet": "string",\n'
                '    "primary_cta": "string",\n'
                '    "secondary_cta": "string",\n'
                '    "supporting_points": ["string"],\n'
                '    "body_rewrite": "string",\n'
                '    "sections": [\n'
                '      {\n'
                '        "section_id": "string",\n'
                '        "section_name": "string",\n'
                '        "status": "CHANGE_RECOMMENDED|NO_CHANGE_NEEDED|INSUFFICIENT_EVIDENCE",\n'
                '        "current_preview": "string",\n'
                '        "suggested_copy": "string",\n'
                '        "purpose": "string",\n'
                '        "seo_geo_notes": "string",\n'
                '        "keywords": ["string"]\n'
                '      }\n'
                '    ],\n'
                '    "faq_items": [\n'
                '      {\n'
                '        "question": "string",\n'
                '        "answer": "string",\n'
                '        "target_engine": "string"\n'
                '      }\n'
                '    ],\n'
                '    "notes": "string"\n'
                '  }\n'
                "}"
            ),
            additional_context=json.dumps(context, ensure_ascii=False),
        )
        if not isinstance(result, dict):
            return _fail_copy_audit(fallback, PageSeoAudit(score=fallback.seo_score), "LLM returned no copy", "no_suggested")
        if str(result.get("status") or "").lower() == "unavailable" or result.get("unavailable_reason") == "no_llm_key":
            reason = str(result.get("unavailable_reason") or result.get("status") or "LLM returned no copy")
            code = str(result.get("unavailable_reason") or result.get("status") or "no_suggested")
            return _fail_copy_audit(fallback, PageSeoAudit(score=fallback.seo_score), reason, code)
        blob = _suggested_blob(result)
        payload = dict(result)
        if blob and not (isinstance(payload.get("suggested"), dict) and payload.get("suggested")):
            payload["suggested"] = blob
        if not blob and not str(payload.get("analysis") or "").strip() and not payload.get("issues"):
            reason = str(payload.get("unavailable_reason") or payload.get("status") or "LLM returned no copy")
            code = str(payload.get("unavailable_reason") or payload.get("status") or "no_suggested")
            return _fail_copy_audit(fallback, PageSeoAudit(score=fallback.seo_score), reason, code)
        parsed = _parse_copy_result(payload, fallback, brand_name=profile.business_name)
        if parsed.suggested:
            parsed.suggested.sections = [
                section for section in parsed.suggested.sections if _keep_page_section(section, page)
            ]
        parsed.llm_status = "ok"
        if parsed.suggested:
            parsed.suggested.notes = (
                (parsed.suggested.notes or "") + " LLM rewrite grounded in crawled evidence for this URL."
            ).strip()
        return parsed
