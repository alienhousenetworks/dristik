"""
Four-axis finding calibration.

Technical severity, business impact, confidence, and blocking are assigned
independently. Technical severity never sets the other three, and a finding
may be described as stopping an outcome only when `blocks` names that outcome.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from app.domain.enums import ConfidenceBand, ImpactLevel, RubricConfidence, Severity
from app.domain.models import Finding, FindingCalibratedImpact, OutcomeImpact

logger = logging.getLogger("dristik.scoring.calibration")

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
    },
    "positioning": {
        "outcomes": [("buyer_conversion", ImpactLevel.HIGH)],
        "blocks": [],
        "floor": None,
        "cap": ConfidenceBand.MEDIUM,
    },
    "robots_missing": {
        "outcomes": [("crawl_hygiene", ImpactLevel.MEDIUM)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
    },
    "alt": {
        "outcomes": [
            ("accessibility", ImpactLevel.MEDIUM),
            ("image_search", ImpactLevel.LOW),
        ],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
    },
    "entity_graph_contradiction": {
        "outcomes": [("entity_clarity", ImpactLevel.HIGH)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
    },
    "entity_graph_gap": {
        "outcomes": [("entity_clarity", ImpactLevel.MEDIUM)],
        "blocks": [],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
    },
    "indexation_block": {
        "outcomes": [("indexation", ImpactLevel.HIGH)],
        "blocks": ["indexation"],
        "floor": ConfidenceBand.HIGH,
        "cap": None,
    },
}


class AIFindingExplanation(BaseModel):
    """
    AI-generated explanation and calibration for a finding in simple, non-technical language.
    """
    what_is_this: str = Field(
        ...,
        description="A concise summary (1-2 sentences) of what the technical issue is in simple, non-technical plain English.",
    )
    why_to_change: str = Field(
        ...,
        description="A concise explanation (1-2 sentences) of why fixing this issue matters commercially, for UX, or for organic search in simple language without jargon or overclaims.",
    )
    how_to_change: str = Field(
        ...,
        description="Actionable, step-by-step guidance (1-2 sentences) on how to fix or remediate this issue in plain English.",
    )
    business_impact: ImpactLevel = Field(
        default=ImpactLevel.MEDIUM,
        description="Estimated business impact level: Critical, High, Medium, Low, or Info.",
    )
    is_blocking: bool = Field(
        default=False,
        description="True ONLY if this defect directly blocks crawlers from indexing the site or users from loading it.",
    )
    blocks: List[str] = Field(
        default_factory=list,
        description="List of outcomes blocked (e.g. ['indexation']). Must be empty if is_blocking is False.",
    )
    blocking_reason: Optional[str] = Field(
        default=None,
        description="Specific reason why this defect blocks the named outcome.",
    )
    affected_outcomes: List[str] = Field(
        default_factory=list,
        description="List of outcomes affected, e.g. ['security_posture', 'buyer_conversion', 'accessibility', 'crawl_hygiene', 'entity_clarity'].",
    )


async def calibrate_and_explain_finding_ai(
    finding: Finding,
    domain: Optional[str] = None,
    client: Optional[Any] = None,
) -> Finding:
    """
    Asynchronous AI-powered calibration and plain-language explanation for a finding.

    Uses LLMClient / ModelRouter to generate:
    - what_is_this: simple plain-English explanation of the issue
    - why_to_change: commercial / UX / organic search consequence
    - how_to_change: concrete, actionable remediation steps
    while calibrating business impact, confidence, and blocking behavior.

    Gracefully falls back to deterministic calibrate_finding if LLM is unavailable or fails.
    """
    # 1. Deterministic baseline to establish fallback values & confidence band
    calibrate_finding(finding)
    band = _band_from_rubric(finding)

    try:
        if client is None:
            from app.core.inference.llm_client import LLMClient
            client = LLMClient()

        if not getattr(client, "available", True):
            return finding

        evidence_snippets: List[str] = []
        for ev in (finding.evidence or [])[:3]:
            snip = getattr(ev, "snippet", "") or getattr(ev, "observation", "") or ""
            if snip:
                evidence_snippets.append(str(snip)[:150])

        urls = (finding.affected_urls or [])[:2]

        system_prompt = (
            "You are a principal website intelligence auditor explaining a technical defect to business stakeholders and developers.\n"
            "Explain everything in simple, clear, non-technical language.\n\n"
            "Requirements:\n"
            "1. what_is_this: Explain in 1-2 plain sentences what the defect is.\n"
            "2. why_to_change: Explain in 1-2 plain sentences why the business stakeholder should care (commercial, user trust, or search visibility consequence). "
            "Never guarantee rankings, traffic, or revenue. Do not claim this defect freezes unrelated pillars.\n"
            "3. how_to_change: Provide 1-2 plain sentences describing concrete, actionable steps to resolve it.\n"
            "4. business_impact: Assign 'Critical', 'High', 'Medium', 'Low', or 'Info'. Note: technical severity does not automatically dictate business impact.\n"
            "5. is_blocking: Set to true ONLY if this defect stops crawlers or users from accessing/indexing the site (e.g. sitewide robots.txt Disallow: /, sitewide noindex, 5xx server crash, DNS/TLS failure). Security headers, missing alt text, missing CTAs, or missing schema are NEVER blocking.\n"
            "6. blocks: List of blocked outcomes (e.g. ['indexation']) if is_blocking is true, else empty list.\n"
            "7. blocking_reason: Explanation if is_blocking is true, else null.\n"
            "8. affected_outcomes: List of affected outcome areas (e.g. ['security_posture', 'buyer_conversion', 'accessibility', 'crawl_hygiene', 'entity_clarity']).\n"
            "Output MUST be a single valid JSON object matching the requested schema."
        )

        user_prompt = (
            f"Website: {domain or 'audited site'}\n"
            f"Finding ID: {finding.finding_id}\n"
            f"Title: {finding.title}\n"
            f"Technical Severity: {finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)}\n"
            f"Category: {finding.category.value if hasattr(finding.category, 'value') else str(finding.category)}\n"
            f"Technical Description: {finding.description}\n"
            f"Affected URLs: {', '.join(urls) if urls else 'N/A'}\n"
            f"Evidence Snippets: {' | '.join(evidence_snippets) if evidence_snippets else 'N/A'}\n"
            'Return JSON matching: {"what_is_this": "...", "why_to_change": "...", "how_to_change": "...", "business_impact": "...", "is_blocking": false, "blocks": [], "blocking_reason": null, "affected_outcomes": ["..."]}'
        )

        model = getattr(client, "model", None) or "gpt-4o-mini"
        if hasattr(client, "generate_chat_completion"):
            response = await client.generate_chat_completion(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=600,
                response_format="DEFAULT",
            )
            raw_text = response.get("text", "") if isinstance(response, dict) else str(response)
        elif hasattr(client, "complete"):
            raw_text = await client.complete(prompt=f"{system_prompt}\n\n{user_prompt}", max_tokens=600)
        else:
            return finding

        from app.core.inference.json_repair import repair_and_parse_json
        parsed = repair_and_parse_json(raw_text)
        if not parsed:
            return finding

        raw_impact = str(parsed.get("business_impact", "")).upper()
        impact_level = {
            "CRITICAL": ImpactLevel.CRITICAL,
            "HIGH": ImpactLevel.HIGH,
            "MEDIUM": ImpactLevel.MEDIUM,
            "LOW": ImpactLevel.LOW,
            "INFO": ImpactLevel.INFO,
        }.get(raw_impact, ImpactLevel.MEDIUM)

        is_blocking = bool(parsed.get("is_blocking", False))
        blocks = [str(b) for b in parsed.get("blocks", [])] if is_blocking else []
        blocking_reason = str(parsed.get("blocking_reason")) if is_blocking and parsed.get("blocking_reason") else None

        # Guardrail: non-blocking categories must never be blocking
        text_blob = f"{finding.title} {finding.description} {finding.rule_id or ''}".lower()
        if any(term in text_blob for term in ("hsts", "security", "alt text", "missing alt", "cta", "positioning", "schema", "entity")):
            is_blocking = False
            blocks = []
            blocking_reason = None

        what_is_this = str(parsed.get("what_is_this", "")).strip()
        why_to_change = str(parsed.get("why_to_change", "")).strip()
        how_to_change = str(parsed.get("how_to_change", "")).strip()

        # Sanitize outcome overclaims
        clean_replacement = "Resolving this defect improves technical compliance and organic search visibility."
        what_is_this, _ = rewrite_outcome_overclaims(what_is_this, "")
        why_to_change, _ = rewrite_outcome_overclaims(why_to_change, clean_replacement)

        if what_is_this:
            finding.description = what_is_this
            if hasattr(finding, "plain_english_summary"):
                finding.plain_english_summary = what_is_this

        if why_to_change:
            finding.why_it_matters = why_to_change
            if hasattr(finding, "business_impact"):
                finding.business_impact = why_to_change

        if how_to_change:
            finding.recommendation = how_to_change
            if hasattr(finding, "recommended_action"):
                finding.recommended_action = how_to_change

        affected = [str(o) for o in parsed.get("affected_outcomes", [])]
        outcomes = [OutcomeImpact(outcome=o, level=impact_level) for o in affected] if affected else [OutcomeImpact(outcome="general_health", level=impact_level)]

        label = _LEVEL_NAME.get(impact_level, "Medium")
        finding.calibrated_impact = FindingCalibratedImpact(
            technical_severity=finding.severity,
            business_impact=impact_level,
            business_impact_label=label,
            confidence=float(finding.confidence or 0.0),
            confidence_band=band,
            is_blocking=is_blocking,
            blocks=blocks,
            blocking_reason=blocking_reason,
            affected_outcomes=outcomes,
        )
        finding.impact = _IMPACT_POINTS.get(impact_level, 5)
        setattr(finding, "_ai_calibrated", True)

    except Exception as exc:
        logger.debug("[calibrate_and_explain_finding_ai] AI explanation fallback: %s", exc)

    return finding


async def batch_calibrate_and_explain_findings_ai(
    findings: Sequence[Finding],
    domain: Optional[str] = None,
    concurrency_limit: int = 5,
    client: Optional[Any] = None,
) -> List[Finding]:
    """Calibrate and explain multiple findings concurrently with bounded concurrency."""
    sem = asyncio.Semaphore(concurrency_limit)

    async def _cal(f: Finding) -> Finding:
        async with sem:
            if client is not None:
                return await calibrate_and_explain_finding_ai(f, domain=domain, client=client)
            return await calibrate_and_explain_finding_ai(f, domain=domain)

    return list(await asyncio.gather(*[_cal(f) for f in findings]))


def calibrate_finding(finding: Finding) -> Finding:
    """Stamp an independent calibration record and align the 1–10 impact integer with business impact."""
    if getattr(finding, "_ai_calibrated", False) and finding.calibrated_impact is not None:
        return finding

    family, reason = _family_and_reason(finding)
    band = _band_from_rubric(finding)
    if family == "unknown":
        headline = _STEP_DOWN.get(finding.severity, ImpactLevel.LOW)
        outcomes: List[Tuple[str, ImpactLevel]] = []
        blocks: List[str] = []
    else:
        spec = _FAMILY_SPECS[family]
        outcomes = list(spec["outcomes"])
        headline = _headline([level for _, level in outcomes])
        blocks = list(spec["blocks"])
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
