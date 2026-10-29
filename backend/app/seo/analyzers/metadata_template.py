"""
Templated-Metadata & Scaled Content Abuse Detector for Dristik.
Adapted from Claude SEO's metadata_template detector.

Identifies machine-generated <title> and <meta name="description"> patterns:
1. templated_metadata (high): Description repeats the title verbatim and ends in a stock CTA.
2. description_echoes_title (medium): Description opens with the title verbatim.
3. brand_suffix_in_description (low): Title's brand suffix leaked into description body.
4. description_duplicates_title (medium): Description and title are identical strings.
5. Site-level rollup: Flags site-wide templated metadata abuse (Google QRG §4.6.5).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

_CTA_TAIL_PATTERNS = (
    r"try (?:it )?(?:free|now)(?: now)?",
    r"try (?:it )?today",
    r"start (?:your |the )?(?:\w+ ){0,3}(?:free|now)",
    r"(?:learn|read|find out|see) (?:more )?now",
    r"get started(?: (?:now|free|today))?",
    r"check (?:it out|your \w+) now",
    r"(?:boost|improve|upgrade) (?:your )?(?:\w+ ){0,3}now",
    r"sign up (?:free|now|today)",
)
_CTA_TAIL_RE = re.compile(
    r"(" + "|".join(_CTA_TAIL_PATTERNS) + r")[.!]*\s*$", re.IGNORECASE
)
_BRAND_SEPARATOR_RE = re.compile(r"\s[|–—-]\s")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")

_MIN_TITLE_CHARS = 18
_ECHO_PREFIX_CHARS = 60
_BRAND_MIN_CHARS = 2
_BRAND_MAX_CHARS = 30

_SITE_MIN_TEMPLATED_PAGES = 3
_SITE_HIGH_RATIO = 0.30
_SITE_MEDIUM_RATIO = 0.10


def _normalise(text: str) -> str:
    return " ".join(_NON_ALNUM_RE.sub(" ", text.lower()).split())


def _title_core(title: str) -> str:
    return _BRAND_SEPARATOR_RE.split(title)[0].strip()


def _finding(signal_id: str, severity: str, message: str, recommendation: str) -> Dict[str, str]:
    return {
        "id": signal_id,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
    }


def _echo_remainder(core: str, description: str) -> str:
    return description[len(core):].strip(" -–—:|.")


def analyse_metadata_pair(title: str, description: str, url: Optional[str] = None) -> Dict[str, Any]:
    """Score one title/description pair for templating signals."""
    title = (title or "").strip()
    description = (description or "").strip()

    result: Dict[str, Any] = {
        "url": url,
        "title": title,
        "description": description,
        "templated": False,
        "severity": "none",
        "cta_phrase": None,
        "flags": [],
        "signals": [],
    }
    if not title or not description:
        result["flags"].append("missing-metadata")
        return result

    core = _title_core(title)
    core_n = _normalise(core)
    title_n = _normalise(title)
    description_n = _normalise(description)
    signals: List[Dict[str, str]] = result["signals"]

    # 1. Description opens by restating the title
    echoes_title = (
        len(core_n) >= _MIN_TITLE_CHARS
        and description_n.startswith(core_n[:_ECHO_PREFIX_CHARS])
    )
    if echoes_title:
        cta_match = _CTA_TAIL_RE.search(_echo_remainder(core, description))
        if cta_match:
            result["templated"] = True
            result["cta_phrase"] = _normalise(cta_match.group(1))
            result["flags"].append("templated-metadata")
            signals.append(_finding(
                "templated_metadata", "high",
                "Meta description repeats the title verbatim and closes with a stock call to action. "
                "Duplicated or templated metadata is a documented quality problem under Google QRG §4.6.5.",
                "Rewrite the description to provide unique page context (what the page does, for whom, key differentiators) "
                "within 140-160 characters without stock CTAs.",
            ))
        else:
            result["flags"].append("description-echoes-title")
            signals.append(_finding(
                "description_echoes_title", "medium",
                "Meta description opens with the exact text of the title, wasting SERP real estate on duplication.",
                "Open the description with complementary information not already present in the title tag.",
            ))

    # 2. Brand suffix concatenated into the description body
    parts = _BRAND_SEPARATOR_RE.split(title)
    if len(parts) > 1:
        brand = parts[-1].strip()
        brand_n = _normalise(brand)
        if (
            _BRAND_MIN_CHARS <= len(brand) <= _BRAND_MAX_CHARS
            and brand_n
            and brand_n in description_n
            and not description.startswith(brand)
        ):
            result["flags"].append("brand-suffix-in-description")
            signals.append(_finding(
                "brand_suffix_in_description", "low",
                f"The title's brand suffix '{brand}' was concatenated into the meta description body.",
                f"Remove '{brand}' from the description body; the title already carries it.",
            ))

    # 3. Description and title are identical strings
    if len(title_n) >= _MIN_TITLE_CHARS and description_n == title_n:
        result["flags"].append("description-duplicates-title")
        signals.append(_finding(
            "description_duplicates_title", "medium",
            "Meta description is identical to the title tag.",
            "Write a distinct meta description that expands on the title instead of duplicating it.",
        ))

    order = {"high": 3, "medium": 2, "low": 1}
    if signals:
        result["severity"] = max((s["severity"] for s in signals), key=lambda s: order.get(s, 0))
    return result


def analyse_pages_metadata(pages: Iterable[Any]) -> Dict[str, Any]:
    """
    Roll multiple page title/description evaluations up to site level.
    Works with PageEvidence objects or dicts with 'title', 'meta_description', 'url'.
    """
    evaluated_pages: List[Dict[str, Any]] = []
    cta_counts: Dict[str, int] = {}

    for p in pages:
        if hasattr(p, "title") and hasattr(p, "meta_description"):
            url = getattr(p, "url", None)
            res = analyse_metadata_pair(p.title or "", p.meta_description or "", url)
        elif isinstance(p, dict):
            res = analyse_metadata_pair(p.get("title") or "", p.get("meta_description") or p.get("description") or "", p.get("url"))
        else:
            continue

        evaluated_pages.append(res)
        if res.get("cta_phrase"):
            cta = res["cta_phrase"]
            cta_counts[cta] = cta_counts.get(cta, 0) + 1

    total = len(evaluated_pages)
    templated = sum(1 for p in evaluated_pages if p.get("templated"))
    ratio = templated / total if total > 0 else 0.0

    site_flags: List[str] = []
    site_risk = "none"

    if templated >= _SITE_MIN_TEMPLATED_PAGES:
        if ratio >= _SITE_HIGH_RATIO:
            site_flags.append("site-wide-templated-metadata")
            site_risk = "high"
        elif ratio >= _SITE_MEDIUM_RATIO:
            site_flags.append("templated-metadata-pattern")
            site_risk = "medium"

    return {
        "pages": evaluated_pages,
        "pages_checked": total,
        "templated_count": templated,
        "templated_ratio": round(ratio, 3),
        "shared_cta_phrases": cta_counts,
        "site_flags": site_flags,
        "site_risk": site_risk,
        "method": "heuristic",
    }
