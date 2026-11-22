"""
Stage 7b Deterministic Narrative Validator & Placeholder Hydrator

Enforces zero-fabrication guarantees across all 5 PDF + 5 PPTX AI narratives:
1. Canonical scorecard variable map (`{{score.overall}}`, `{{count.critical}}`, etc.) built
   strictly from the single Phase-6 scorecard + Critic-verified findings.
2. Raw-number guard: detects any digit/currency/percentage written by the LLM outside valid
   `{{placeholder}}` tokens. On final sanitization, removes offending sentences WHOLE
   (never leaving broken fragments like "improves by ." or "[metric not in evidence].").
3. Finding ID verification: verifies 100% of `cited_finding_ids` exist in the verified
   finding registry (excluding `held_from_executive` false positives).
4. Epistemic label preservation: preserves `UNKNOWN (Requires GA4)`, `NOT_MEASURED`, and
   `AI_INTERPRETATION` verbatim.
5. PPTX structural guard: enforces slide cap, `<= 4` bullets per slide, `<= 15` words/bullet.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.core.config import settings
from app.domain.scoring.displayed_score import displayed_composite, rating_for_displayed

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.\-]+)\s*\}\}")
# Any raw digit, currency amount, percentage, or numeric multiplier outside placeholders
_RAW_DIGIT_RE = re.compile(
    r"(?:[\$₹€£¥]\s*\d|\b\d+(?:[.,]\d+)?\s*(?:%|x\b|times\b|hours?\b|days?\b|weeks?\b|months?\b|years?\b)?|\d)",
    re.IGNORECASE,
)
# Allowlist of non-metric domain tokens that legitimately contain digits (never fabricated business metrics)
_ALLOWED_DOMAIN_TOKENS = re.compile(
    r"\b(?:h[1-6]|http/[123]|https?|wcag\s*2(?:\.[012])?|ga4|b2b|b2c|d2c|b2g|iso\s*27001|soc\s*2|"
    r"sha-?256|utf-?8|html5|css3|tls\s*1\.[23]|aes-?256|json-ld|p[0-3]|7/30/90|30/60/90|"
    r"404|301|302|307|308|403|410|500|502|503|200|"
    r"580px|44px|40-60|5-second|6-question|8-dimension|10-step|"
    r"find_\d+|finding-[a-z]+-\d+|acc_wcag_[0-9_a-z]+|root_rc_[0-9_a-z]+|cro-\d+)\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_REQUIRED_LABELS = ("UNKNOWN (Requires GA4)", "NOT_MEASURED", "AI_INTERPRETATION")


class NarrativeValidationReport(BaseModel):
    passed: bool = True
    has_raw_digits: bool = False
    raw_digit_matches: List[str] = Field(default_factory=list)
    unknown_placeholders: List[str] = Field(default_factory=list)
    invalid_finding_ids: List[str] = Field(default_factory=list)
    sentences_removed: int = 0
    chapters_dropped: int = 0
    slides_dropped: int = 0
    bullets_trimmed: int = 0
    preserved_labels_found: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


def verified_findings_for_reporting(report: Any) -> List[Any]:
    """Return strictly Critic-verified, non-held findings for reporting narratives."""
    out = []
    for f in (getattr(report, "findings", None) or []):
        if getattr(f, "held_from_executive", False):
            continue
        fid = getattr(f, "finding_id", None)
        if not fid:
            continue
        out.append(f)
    return out


def build_scorecard_vars(report: Any) -> Dict[str, str]:
    """Build the single canonical placeholder dictionary from the Phase-6 scorecard & verified findings."""
    comp = displayed_composite(report)
    scores = getattr(report, "scores", None)
    honest = getattr(report, "honest_scores", None)
    geo = getattr(report, "geo_readiness", None)
    vis = getattr(report, "ai_visibility_scorecard", None)
    manifest = getattr(report, "crawl_manifest", None)
    telemetry = getattr(report, "telemetry", None)
    findings = verified_findings_for_reporting(report)

    def _fmt_score(val: Any) -> str:
        if val is None or isinstance(val, bool):
            return "NOT_MEASURED"
        try:
            return f"{int(round(float(val)))}/100"
        except Exception:
            return "NOT_MEASURED"

    overall_val = comp if comp is not None else getattr(scores, "overall_score", None)
    grade_str, health_label = rating_for_displayed(overall_val)

    cat_scores = getattr(scores, "category_scores", None) or {}

    def _cat_score(keys: Tuple[str, ...]) -> Optional[float]:
        for k, v in cat_scores.items():
            k_up = str(getattr(k, "value", k)).upper()
            if any(target in k_up for target in keys):
                sc = getattr(v, "score", None) if not isinstance(v, dict) else v.get("score")
                if sc is not None:
                    return float(sc)
        return None

    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    pillar_counts = {"seo": 0, "geo": 0, "aeo": 0, "cro": 0}
    for f in findings:
        s_val = str(getattr(getattr(f, "severity", ""), "value", getattr(f, "severity", ""))).upper()
        if s_val in sev_counts:
            sev_counts[s_val] += 1
        c_val = str(getattr(getattr(f, "category", ""), "value", getattr(f, "category", ""))).upper()
        if any(k in c_val for k in ("TECHNICAL", "ON_PAGE", "SCHEMA", "CONTENT", "SEO")):
            pillar_counts["seo"] += 1
        elif "GEO" in c_val:
            pillar_counts["geo"] += 1
        elif any(k in c_val for k in ("AI_SEARCH", "AEO")):
            pillar_counts["aeo"] += 1
        elif any(k in c_val for k in ("UX", "CONVERSION", "CRO", "TRUST")):
            pillar_counts["cro"] += 1

    pages_crawled = len(getattr(manifest, "pages", None) or getattr(report, "page_reports", None) or [])
    sandbox = getattr(report, "dynamic_sandbox_evaluations", None) or []
    aeo_gaps = sum(1 for q in sandbox if not getattr(q, "is_answerable", False))
    patches_count = len(getattr(report, "code_patches", None) or [])

    live_vis_val = None
    if vis is not None and getattr(vis, "status", None) == "MEASURED" and getattr(vis, "citation_rate_pct", None) is not None:
        live_vis_val = getattr(vis, "citation_rate_pct", None)

    total_usd = float(getattr(telemetry, "estimated_cost_usd", 0.0) or 0.0) if telemetry else 0.0
    inr_rate = float(getattr(settings, "USD_TO_INR_RATE", 85.0) or 85.0)
    total_inr = total_usd * inr_rate
    per_page_inr = total_inr / max(1, pages_crawled)

    ga4_connected = False
    gp = getattr(report, "google_performance", None)
    if isinstance(gp, dict):
        ga4_state = str((gp.get("analytics") or {}).get("state") or "").upper()
        ga4_connected = ga4_state in ("CONNECTED", "MEASURED", "OK")

    return {
        "brand.name": str(getattr(getattr(report, "business_profile", None), "business_name", None) or getattr(report, "domain", "Website")),
        "brand.domain": str(getattr(report, "domain", "website")),
        "score.overall": _fmt_score(overall_val),
        "score.grade": grade_str,
        "score.health_label": health_label,
        "score.seo": _fmt_score(_cat_score(("TECHNICAL_SEO", "ON_PAGE_SEO", "SEO")) or getattr(honest, "google_score", None)),
        "score.geo": _fmt_score(getattr(geo, "extractability_score", None) or _cat_score(("GEO",))),
        "score.geo_readiness": _fmt_score(getattr(geo, "extractability_score", None)),
        "score.aeo": _fmt_score(_cat_score(("AI_SEARCH", "AEO")) or getattr(honest, "ai_readiness_score", None)),
        "score.cro": _fmt_score(_cat_score(("UX_CONVERSION", "CRO")) or getattr(honest, "human_score", None)),
        "score.human": _fmt_score(getattr(honest, "human_score", None)),
        "score.google": _fmt_score(getattr(honest, "google_score", None)),
        "score.ai_readiness": _fmt_score(getattr(honest, "ai_readiness_score", None)),
        "score.live_visibility": _fmt_score(live_vis_val),
        "count.total_findings": str(len(findings)),
        "count.critical": str(sev_counts["CRITICAL"]),
        "count.high": str(sev_counts["HIGH"]),
        "count.medium": str(sev_counts["MEDIUM"]),
        "count.low": str(sev_counts["LOW"]),
        "count.seo_findings": str(pillar_counts["seo"]),
        "count.geo_findings": str(pillar_counts["geo"]),
        "count.aeo_findings": str(pillar_counts["aeo"]),
        "count.cro_findings": str(pillar_counts["cro"]),
        "count.pages_crawled": str(pages_crawled),
        "count.aeo_questions": str(len(sandbox)) if sandbox else "NOT_MEASURED",
        "count.aeo_gaps": str(aeo_gaps) if sandbox else "NOT_MEASURED",
        "count.code_patches": str(patches_count),
        "cost.total_usd": f"${total_usd:.2f}",
        "cost.total_inr": f"₹{total_inr:.0f}",
        "cost.blended_per_page_inr": f"₹{per_page_inr:.1f}",
        "label.analytics": "MEASURED" if ga4_connected else "UNKNOWN (Requires GA4)",
        "label.not_measured": "NOT_MEASURED",
        "label.ai_interpretation": "AI_INTERPRETATION",
    }


def detect_raw_digits(text: str) -> List[str]:
    """Detect raw numeric tokens outside `{{placeholder}}` braces and non-metric domain tokens."""
    if not text:
        return []
    without_placeholders = _PLACEHOLDER_RE.sub(" ", text)
    without_domain = _ALLOWED_DOMAIN_TOKENS.sub(" ", without_placeholders)
    # Also allow finding IDs like find_001 or Q-001 if referenced inline
    without_ids = re.sub(r"\b(?:find|det|clm|ev|ext|Q)[_-][a-zA-Z0-9_-]+\b", " ", without_domain)
    return [m.group(0).strip() for m in _RAW_DIGIT_RE.finditer(without_ids)]


def _sanitize_and_hydrate_text(
    text: str,
    scorecard_vars: Dict[str, str],
    report: NarrativeValidationReport,
) -> str:
    """
    Validate placeholders & raw digits sentence-by-sentence, then hydrate.
    If a sentence contains raw ungrounded digits or an unresolved `{{placeholder}}`,
    the ENTIRE offending sentence is removed (never leaving broken fragments like "improves by .").
    """
    if not text or not text.strip():
        return ""

    kept_sentences: List[str] = []
    for raw_sent in _SENTENCE_SPLIT_RE.split(text.strip()):
        sent = raw_sent.strip()
        if not sent:
            continue

        # 1. Check unknown placeholders — remove sentence whole so pre-hydration tokens never leak
        bad_ph = [m.group(1) for m in _PLACEHOLDER_RE.finditer(sent) if m.group(1) not in scorecard_vars]
        if bad_ph:
            report.unknown_placeholders.extend(bad_ph)
            report.sentences_removed += 1
            continue

        # 2. Check raw digits outside placeholders — remove sentence whole (no partial "improves by .")
        raw_hits = detect_raw_digits(sent)
        if raw_hits:
            report.has_raw_digits = True
            report.raw_digit_matches.extend(raw_hits)
            report.sentences_removed += 1
            continue

        # 3. Hydrate all valid {{placeholders}} strictly from canonical scorecard_vars
        hydrated = _PLACEHOLDER_RE.sub(lambda m: scorecard_vars[m.group(1)], sent)
        # Double-check no unhydrated braces survived
        if "{{" in hydrated or "}}" in hydrated:
            report.sentences_removed += 1
            continue

        for lbl in _REQUIRED_LABELS:
            if lbl in hydrated and lbl not in report.preserved_labels_found:
                report.preserved_labels_found.append(lbl)

        kept_sentences.append(hydrated)

    return " ".join(kept_sentences).strip()


def _trim_bullet_words(bullet: str, max_words: int = 15) -> Tuple[str, bool]:
    words = bullet.split()
    if len(words) <= max_words:
        return bullet, False
    return " ".join(words[:max_words]).rstrip(",;:") + ".", True


def inspect_bundle_for_raw_digits(bundle_dict: Dict[str, Any]) -> List[str]:
    """Pre-hydration scan used to trigger a single LLM retry if raw digits were written."""
    hits: List[str] = []
    hits.extend(detect_raw_digits(str(bundle_dict.get("executive_summary") or "")))
    for ch in (bundle_dict.get("chapters") or []):
        if isinstance(ch, dict):
            for field in ("title", "executive_takeaway", "body_md", "why_it_matters"):
                hits.extend(detect_raw_digits(str(ch.get(field) or "")))
    for sl in (bundle_dict.get("slides") or []):
        if isinstance(sl, dict):
            for field in ("title", "speaker_notes"):
                hits.extend(detect_raw_digits(str(sl.get(field) or "")))
            for b in (sl.get("bullets") or []):
                hits.extend(detect_raw_digits(str(b or "")))
    return hits


def validate_and_hydrate_bundle(
    bundle_dict: Dict[str, Any],
    *,
    verified_finding_ids: Set[str],
    scorecard_vars: Dict[str, str],
    max_slides: int = 20,
    max_bullets: int = 4,
    max_bullet_words: int = 15,
) -> Tuple[Dict[str, Any], NarrativeValidationReport]:
    """
    Deterministically validate, sanitize (whole-sentence removal on bad digits/placeholders),
    verify finding IDs, enforce PPTX limits, and hydrate all `{{placeholders}}`.
    """
    val = NarrativeValidationReport()
    out = dict(bundle_dict)
    out["executive_summary"] = _sanitize_and_hydrate_text(
        str(out.get("executive_summary") or ""), scorecard_vars, val
    )

    # Validate PDF chapters
    clean_chapters: List[Dict[str, Any]] = []
    for ch in (out.get("chapters") or []):
        if not isinstance(ch, dict):
            continue
        cited = [str(fid).strip() for fid in (ch.get("cited_finding_ids") or []) if str(fid).strip()]
        invalid = [fid for fid in cited if fid not in verified_finding_ids]
        valid_cited = [fid for fid in cited if fid in verified_finding_ids]
        if invalid:
            val.invalid_finding_ids.extend(invalid)
        # If chapter cited findings and NONE of them exist in verified registry, drop the chapter
        if cited and not valid_cited:
            val.chapters_dropped += 1
            continue
        # If verified findings exist in audit, require at least 1 valid cited finding ID per chapter
        if verified_finding_ids and not valid_cited:
            val.chapters_dropped += 1
            continue

        body_clean = _sanitize_and_hydrate_text(str(ch.get("body_md") or ""), scorecard_vars, val)
        takeaway_clean = _sanitize_and_hydrate_text(str(ch.get("executive_takeaway") or ""), scorecard_vars, val)
        why_clean = _sanitize_and_hydrate_text(str(ch.get("why_it_matters") or ""), scorecard_vars, val)
        title_clean = _sanitize_and_hydrate_text(str(ch.get("title") or ""), scorecard_vars, val) or str(ch.get("title") or "")

        if not body_clean and not takeaway_clean:
            val.chapters_dropped += 1
            continue

        clean_ch = dict(ch)
        clean_ch["title"] = title_clean
        clean_ch["executive_takeaway"] = takeaway_clean
        clean_ch["body_md"] = body_clean
        clean_ch["why_it_matters"] = why_clean
        clean_ch["cited_finding_ids"] = valid_cited
        clean_chapters.append(clean_ch)

    out["chapters"] = clean_chapters

    # Validate PPTX slides
    clean_slides: List[Dict[str, Any]] = []
    for sl in (out.get("slides") or [])[:max_slides]:
        if not isinstance(sl, dict):
            continue
        cited = [str(fid).strip() for fid in (sl.get("cited_finding_ids") or []) if str(fid).strip()]
        invalid = [fid for fid in cited if fid not in verified_finding_ids]
        valid_cited = [fid for fid in cited if fid in verified_finding_ids]
        if invalid:
            val.invalid_finding_ids.extend(invalid)
        if cited and not valid_cited:
            val.slides_dropped += 1
            continue
        if verified_finding_ids and not valid_cited:
            val.slides_dropped += 1
            continue

        clean_bullets: List[str] = []
        for raw_b in (sl.get("bullets") or [])[:max_bullets]:
            b_hyd = _sanitize_and_hydrate_text(str(raw_b or ""), scorecard_vars, val)
            if not b_hyd:
                continue
            b_trimmed, was_trimmed = _trim_bullet_words(b_hyd, max_words=max_bullet_words)
            if was_trimmed:
                val.bullets_trimmed += 1
            clean_bullets.append(b_trimmed)

        notes_hyd = _sanitize_and_hydrate_text(str(sl.get("speaker_notes") or ""), scorecard_vars, val)
        title_hyd = _sanitize_and_hydrate_text(str(sl.get("title") or ""), scorecard_vars, val) or str(sl.get("title") or "")

        if not clean_bullets and not notes_hyd:
            val.slides_dropped += 1
            continue

        clean_sl = dict(sl)
        clean_sl["title"] = title_hyd
        clean_sl["bullets"] = clean_bullets
        clean_sl["speaker_notes"] = notes_hyd
        clean_sl["cited_finding_ids"] = valid_cited
        clean_slides.append(clean_sl)

    out["slides"] = clean_slides
    val.passed = not (val.unknown_placeholders or val.invalid_finding_ids)
    out["validation_summary"] = val.model_dump()
    return out, val
