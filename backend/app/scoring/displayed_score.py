"""The one composite the dashboard and the PDF cover both show.

Matches frontend ``buildDisplayedScore``. GEO is the measured extractability
score. A live citation of zero stays in the total only when this run recorded
successful engine responses. An unmeasured pillar is left out.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Optional


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round_to(value: float, digits: int) -> float:
    factor = 10 ** digits
    return math.floor(value * factor + 0.5) / factor


def _as_report(report: Any) -> Optional[dict]:
    if report is None:
        return None
    if isinstance(report, str):
        if not report.strip():
            return None
        try:
            report = json.loads(report)
        except (TypeError, ValueError):
            return None
    if not isinstance(report, dict) and hasattr(report, "model_dump"):
        try:
            report = report.model_dump(mode="json")
        except Exception:
            return None
    return report if isinstance(report, dict) else None


def _positive_int(value: Any) -> int:
    number = _num(value)
    if number is None or number <= 0:
        return 0
    return int(number)


def _record_identifies_engine(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    return bool(str(record.get("engine_id") or "").strip() or str(record.get("engine_name") or "").strip())


def live_execution_proven(report: Any) -> bool:
    """True when this run has a successful engine response, not merely an attempted budget."""
    payload = _as_report(report) or {}
    card = payload.get("ai_visibility_scorecard") or {}
    records = []
    if isinstance(card, dict):
        if _positive_int(card.get("successful_runs")) > 0:
            return True
        card_records = card.get("observatory_records") or []
        if isinstance(card_records, list):
            records.extend(card_records)
    top_records = payload.get("observatory_records") or []
    if isinstance(top_records, list):
        records.extend(top_records)
    return any(_record_identifies_engine(record) for record in records)


def grade_for_displayed(score: float) -> str:
    """Grade bands shared with the editorial ledger."""
    if score >= 93:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 65:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def align_story_score(story: str, sealed_score: Any, composite: float) -> str:
    """Replace the sealed overall sentence with the dossier composite and its grade."""
    if not story or composite is None:
        return story
    sealed = _num(sealed_score)
    if sealed is None:
        return story
    sealed_token = str(int(round(sealed)))
    pattern = rf"{re.escape(sealed_token)}(?:\.0)?/100(?:\s*\([^)]*\))?"
    replacement = f"{composite:.1f}/100 (grade {grade_for_displayed(composite)})"
    updated, count = re.subn(pattern, replacement, story, count=1)
    return updated if count else story


def _live_citation(payload: dict, honest: dict) -> Optional[float]:
    if not live_execution_proven(payload):
        return None
    live = _num(honest.get("live_ai_citation_score"))
    if live is None and honest.get("ai_visibility_status") == "MEASURED":
        live = _num(honest.get("ai_visibility_score"))
    if live is None:
        card = payload.get("ai_visibility_scorecard") or {}
        if isinstance(card, dict):
            live = _num(card.get("citation_rate_pct"))
    return live


def displayed_composite(report: Any) -> Optional[float]:
    """Return the dossier composite, or None when the report has no measured pillars."""
    payload = _as_report(report)
    if not payload:
        return None
    scores = payload.get("scores") or {}
    honest = payload.get("honest_scores") or {}
    categories = scores.get("category_scores") or {}
    geo = payload.get("geo_readiness") or {}

    def category_score(key: str) -> Optional[float]:
        category = categories.get(key) or {}
        if not isinstance(category, dict) or category.get("status") == "NOT_MEASURED":
            return None
        return _num(category.get("score"))

    live = _live_citation(payload, honest if isinstance(honest, dict) else {})
    pillars = [
        (0.30, _num(honest.get("google_score")) if _num(honest.get("google_score")) is not None else category_score("TECHNICAL_SEO")),
        (0.25, _num(geo.get("extractability_score")) if _num(geo.get("extractability_score")) is not None else (
            _num(honest.get("ai_readiness_score")) if _num(honest.get("ai_readiness_score")) is not None else category_score("GEO")
        )),
        (0.25, live),
        (0.20, _num(honest.get("human_score")) if _num(honest.get("human_score")) is not None else category_score("UX_CONVERSION")),
    ]
    measured = [(weight, score) for weight, score in pillars if score is not None]
    if not measured:
        return None
    weight_sum = sum(weight for weight, _ in measured)
    if weight_sum <= 0:
        return None
    composite = sum(score * (weight / weight_sum) for weight, score in measured)
    return _round_to(composite, 1)
