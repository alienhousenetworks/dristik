"""
Four-axis finding calibration.

Technical severity, business impact, confidence, and blocking are assigned
independently. Technical severity never sets the other three, and a finding
may be described as stopping an outcome only when `blocks` names that outcome.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from app.domain.enums import ConfidenceBand, ImpactLevel, RubricConfidence, Severity
from app.domain.models import Finding, FindingCalibratedImpact, OutcomeImpact

_SEV_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}
_IMPACT_RANK = {
    ImpactLevel.INFO: 0,
    ImpactLevel.LOW: 1,
    ImpactLevel.MEDIUM: 2,
    ImpactLevel.HIGH: 3,
    ImpactLevel.CRITICAL: 4,
}
_CONF_RANK = {
    ConfidenceBand.LOW: 0,
    ConfidenceBand.MEDIUM: 1,
    ConfidenceBand.HIGH: 2,
}
_STEP_DOWN = {
    Severity.CRITICAL: ImpactLevel.HIGH,
    Severity.HIGH: ImpactLevel.MEDIUM,
    Severity.MEDIUM: ImpactLevel.LOW,
    Severity.LOW: ImpactLevel.INFO,
    Severity.INFO: ImpactLevel.INFO,
}
_IMPACT_POINTS = {
    ImpactLevel.CRITICAL: 10,
    ImpactLevel.HIGH: 8,
    ImpactLevel.MEDIUM: 5,
    ImpactLevel.LOW: 3,
    ImpactLevel.INFO: 1,
}
_BUSINESS_SCALE = {
    ImpactLevel.CRITICAL: 1.0,
    ImpactLevel.HIGH: 0.85,
    ImpactLevel.MEDIUM: 0.50,
    ImpactLevel.LOW: 0.25,
    ImpactLevel.INFO: 0.0,
}
_CONFIDENCE_SCALE = {
    ConfidenceBand.HIGH: 1.0,
    ConfidenceBand.MEDIUM: 0.75,
    ConfidenceBand.LOW: 0.0,
}
_LEVEL_NAME = {
    ImpactLevel.CRITICAL: "Critical",
    ImpactLevel.HIGH: "High",
    ImpactLevel.MEDIUM: "Medium",
    ImpactLevel.LOW: "Low",
    ImpactLevel.INFO: "Info",
}
_BY_ROOT = {
    "RC_SECURITY_HEADERS": "security",
    "RC_IMAGE_ACCESSIBILITY": "alt",
    "RC_HOMEPAGE_POSITIONING": "positioning",
}
_GENERIC_WHY = "collectively impair user experience, trust, and organic discoverability"

_OVERCLAIM_RE = re.compile(
    r"("
    r"until (?:this|that|the) defect.{0,180}?(?:seo|design|buyer|citation|conversion)"
    r"|will not change"
    r"|additional seo or design"
    r"|maximize buyer conversion and ai citation"
    r"|until the verified root constraint is fixed"
    r"|buyer or citation outcomes"
    r")",
    re.IGNORECASE | re.DOTALL,
)


def _blob(finding: Finding) -> str:
    parts = [
        finding.title or "",
        finding.description or "",
        getattr(finding, "finding", "") or "",
        finding.root_cause_id or "",
        finding.rule_id or "",
        finding.recommendation or "",
    ]
    return " ".join(parts).lower()


def _is_disallow(text: str) -> bool:
    if re.search(r"disallow\s*:\s*/(?!\w)", text):
        return True
    return "disallow all" in text or "robots.txt disallow" in text


def _is_noindex_sitewide(text: str) -> bool:
    if "noindex" not in text:
        return False
    return any(
        token in text
        for token in (
            "site-wide",
            "sitewide",
            "site wide",
            "entire site",
            "all pages",
            "every page",
            "whole site",
        )
    )


def _is_fetch_failure(text: str) -> bool:
    return any(
        token in text
        for token in (
            "dns failure",
            "dns resolution",
            "nxdomain",
            "tls handshake",
            "ssl handshake",
            "certificate verify failed",
        )
    )


def _is_5xx(text: str) -> bool:
    return bool(
        re.search(r"\b(500|502|503|504)\b", text)
        or "5xx" in text
        or "internal server error" in text
    )


def _is_security(text: str) -> bool:
    return any(
        token in text
        for token in (
            "hsts",
            "strict-transport-security",
            "content-security-policy",
            "x-frame-options",
            "x-content-type-options",
            "security header",
            "clickjacking",
            "nosniff",
        )
    )


def _is_cta_or_positioning(text: str) -> bool:
    return any(
        token in text
        for token in (
            "missing cta",
            "weak cta",
            "cta ambiguous",
            "prominent cta",
            "call to action",
            "call-to-action",
            "no primary cta",
            "lacks prominent cta",
            "primary cta",
            "value proposition",
            "positioning",
            "h1 not descriptive",
            "slogan mismatch",
            "unclear value",
            "5-second",
        )
    )


def _is_missing_robots(text: str) -> bool:
    if "disallow" in text:
        return False
    if "robots.txt" not in text and "robots txt" not in text:
        return False
    return any(token in text for token in ("missing", "not found", "404", "absent", "no robots"))


def _is_alt(text: str) -> bool:
    return any(
        token in text
        for token in (
            "missing alt",
            "lack alt",
            "alt attribute",
            "alt text",
            "images lack alt",
            "image accessibility",
            "empty alt",
            "alternative text",
        )
    )


def _family_and_reason(finding: Finding) -> Tuple[str, Optional[str]]:
    rule = finding.rule_id or ""
    if rule == "entity_graph_contradiction":
        return "entity_graph_contradiction", None
    if rule in {"entity_graph_incomplete", "entity_graph_contact", "entity_graph_applicability"}:
        return "entity_graph_gap", None
    root = finding.root_cause_id or ""
    if root in _BY_ROOT:
        return _BY_ROOT[root], None
    text = _blob(finding)
    if _is_disallow(text):
        return "indexation_block", "robots.txt Disallow: / stops crawlers from indexing the site."
    if _is_noindex_sitewide(text):
        return "indexation_block", "A sitewide noindex directive stops crawlers from indexing the site."
    if _is_fetch_failure(text):
        return "indexation_block", "The host could not be fetched, so crawlers cannot index the site."
    if _is_5xx(text):
        return "indexation_block", "An HTTP 5xx response on a sampled commercial URL stops crawlers from indexing that URL."
    if _is_security(text):
        return "security", None
    if _is_cta_or_positioning(text):
        return "positioning", None
    if _is_missing_robots(text):
        return "robots_missing", None
    if _is_alt(text):
        return "alt", None
    return "unknown", None


def _rubric_value(finding: Finding) -> str:
    rubric = getattr(finding, "confidence_rubric", None)
    if isinstance(rubric, RubricConfidence):
        return rubric.value
    return str(rubric or "")


def _band_from_rubric(finding: Finding) -> ConfidenceBand:
    value = _rubric_value(finding)
    if value in (RubricConfidence.CERTAIN.value, RubricConfidence.VERIFIED.value, RubricConfidence.HIGH_CONFIDENCE.value):
        return ConfidenceBand.HIGH
    if value in (RubricConfidence.LIKELY.value, RubricConfidence.MEDIUM_CONFIDENCE.value):
        return ConfidenceBand.MEDIUM
    if value in (
        RubricConfidence.GUESSING.value,
        RubricConfidence.LOW_CONFIDENCE.value,
        RubricConfidence.UNVERIFIED.value,
    ):
        return ConfidenceBand.LOW
    conf = float(getattr(finding, "confidence", 0) or 0)
    if conf >= 0.9:
        return ConfidenceBand.HIGH
    if conf >= 0.6:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def _observed(finding: Finding) -> bool:
    return bool(finding.evidence or finding.evidence_refs)


def _analytics_connected(finding: Finding) -> bool:
    cro = getattr(finding, "cro_dissection", None)
    return bool(cro is not None and getattr(cro, "analytics_connected", False))


def _impact_label(levels: Sequence[ImpactLevel], headline: ImpactLevel) -> str:
    ordered = sorted(set(levels), key=lambda level: _IMPACT_RANK.get(level, 0))
    if len(ordered) == 2 and _IMPACT_RANK[ordered[1]] - _IMPACT_RANK[ordered[0]] == 1:
        return f"{_LEVEL_NAME[ordered[0]]}/{_LEVEL_NAME[ordered[1]]}"
    return _LEVEL_NAME.get(headline, "Medium")


def _headline(levels: Sequence[ImpactLevel]) -> ImpactLevel:
    return max(levels, key=lambda level: _IMPACT_RANK.get(level, 0))


_FAMILY_SPECS: Dict[str, dict] = {
    "security": {
        "outcomes": [("security_posture", ImpactLevel.MEDIUM)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
        "why": (
            "Missing HSTS, CSP, or related response headers is a transport-security defect "
            "with medium business impact. It does not block indexing, buyer conversion, or AI citations."
        ),
    },
    "positioning": {
        "outcomes": [("buyer_conversion", ImpactLevel.HIGH)],
        "blocks": [],
        "floor": None,
        "cap": ConfidenceBand.MEDIUM,
        "why": (
            "A weak or missing primary call to action, or an unclear value proposition, is a "
            "buyer-conversion defect. Without analytics this commercial reading is medium confidence. "
            "It does not block indexing or AI citations."
        ),
    },
    "robots_missing": {
        "outcomes": [("crawl_hygiene", ImpactLevel.MEDIUM)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
        "why": (
            "A missing robots.txt file is a crawl-hygiene gap. It does not block indexing the way a "
            "sitewide Disallow does, and it does not block buyer conversion or AI citations."
        ),
    },
    "alt": {
        "outcomes": [
            ("accessibility", ImpactLevel.MEDIUM),
            ("image_search", ImpactLevel.LOW),
        ],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
        "why": (
            "Missing alt text is an accessibility defect. Buyer-conversion and AI-citation impact "
            "stay low. It does not block other SEO or design work."
        ),
    },
    "entity_graph_contradiction": {
        "outcomes": [("entity_clarity", ImpactLevel.HIGH)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
        "why": (
            "A machine-readable name or URL disagrees across schema and page metadata. "
            "Answer engines can attach the wrong name to the entity. This does not block indexing."
        ),
    },
    "entity_graph_gap": {
        "outcomes": [("entity_clarity", ImpactLevel.MEDIUM)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
        "why": (
            "The sampled entity graph leaves applicable identity properties unstated. "
            "Answer engines have less to resolve. This does not block indexing."
        ),
    },
    "indexation_block": {
        "outcomes": [("indexation", ImpactLevel.HIGH)],
        "blocks": ["indexation"],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
        "why": (
            "This defect blocks indexation. Crawlers cannot index until it is removed. "
            "Buyer conversion and AI citations are separate findings."
        ),
    },
}


def calibrate_finding(finding: Finding) -> Finding:
    """Stamp an independent calibration record and align the 1–10 impact integer with business impact."""
    family, reason = _family_and_reason(finding)
    band = _band_from_rubric(finding)
    if family == "unknown":
        headline = _STEP_DOWN.get(finding.severity, ImpactLevel.LOW)
        outcomes: List[Tuple[str, ImpactLevel]] = []
        blocks: List[str] = []
        why = None
    else:
        spec = _FAMILY_SPECS[family]
        outcomes = list(spec["outcomes"])
        headline = _headline([level for _, level in outcomes])
        blocks = list(spec["blocks"])
        why = spec["why"]
        if spec["floor"] == ConfidenceBand.HIGH and band != ConfidenceBand.LOW and _observed(finding):
            band = ConfidenceBand.HIGH
        if spec["cap"] == ConfidenceBand.MEDIUM and not _analytics_connected(finding) and band == ConfidenceBand.HIGH:
            band = ConfidenceBand.MEDIUM
        if family == "indexation_block" and reason:
            pass
        elif family == "indexation_block":
            reason = "Crawlers cannot index the sampled site until this defect is removed."

    label = _impact_label([level for _, level in outcomes], headline) if outcomes else _LEVEL_NAME[headline]
    finding.calibrated_impact = FindingCalibratedImpact(
        technical_severity=finding.severity,
        business_impact=headline,
        business_impact_label=label,
        confidence=float(finding.confidence or 0.0),
        confidence_band=band,
        is_blocking=bool(blocks),
        blocks=blocks,
        blocking_reason=reason if blocks else None,
        affected_outcomes=[OutcomeImpact(outcome=name, level=level) for name, level in outcomes],
    )
    finding.impact = _IMPACT_POINTS[headline]
    current_why = finding.why_it_matters or ""
    if why and (not current_why.strip() or _GENERIC_WHY in current_why.lower()):
        finding.why_it_matters = why
    return finding


def deduction_scales(calibrated: Optional[FindingCalibratedImpact]) -> Tuple[float, float]:
    """Return (business-impact scale, confidence scale) for a pillar deduction."""
    if calibrated is None:
        return 0.5, 0.75
    business = _BUSINESS_SCALE.get(calibrated.business_impact, 0.5)
    confidence = _CONFIDENCE_SCALE.get(calibrated.confidence_band, 0.75)
    if calibrated.is_blocking and calibrated.confidence_band == ConfidenceBand.HIGH:
        business = 1.0
    return business, confidence


def commercial_sort_key(finding: Finding) -> Tuple[int, int, int, int]:
    calibrated = finding.calibrated_impact
    if calibrated is None:
        return (0, 0, 0, 0)
    return (
        1 if calibrated.is_blocking else 0,
        _IMPACT_RANK.get(calibrated.business_impact, 0),
        _CONF_RANK.get(calibrated.confidence_band, 0),
        _SEV_RANK.get(calibrated.technical_severity, 0),
    )


def technical_sort_key(finding: Finding) -> Tuple[int, int, int]:
    calibrated = finding.calibrated_impact
    if calibrated is None:
        return (0, 0, 0)
    return (
        _SEV_RANK.get(calibrated.technical_severity, 0),
        _CONF_RANK.get(calibrated.confidence_band, 0),
        _IMPACT_RANK.get(calibrated.business_impact, 0),
    )


def prose_overclaims(text: str) -> bool:
    """True when prose treats a defect as freezing SEO, design, buyers, conversion, or citations."""
    return bool(text and _OVERCLAIM_RE.search(text))


def rewrite_outcome_overclaims(text: str, replacement: str) -> Tuple[str, bool]:
    """Drop sentences that overclaim a causal block and keep the calibrated replacement."""
    if not prose_overclaims(text):
        return text or "", False
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    kept = [part for part in parts if part and not prose_overclaims(part)]
    rewritten = " ".join(kept).strip()
    replacement = (replacement or "").strip()
    if replacement and replacement not in rewritten:
        rewritten = f"{rewritten} {replacement}".strip() if rewritten else replacement
    return rewritten, True
