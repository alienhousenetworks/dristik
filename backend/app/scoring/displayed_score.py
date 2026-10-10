"""The one composite the dashboard and the PDF cover both show.

Matches frontend ``buildDisplayedScore``: GEO is the measured extractability
score, a live citation of zero stays in the total, and an unmeasured pillar
is left out.
"""
from __future__ import annotations

import json
import math
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

    live = _num(honest.get("live_ai_citation_score"))
    if live is None and honest.get("ai_visibility_status") == "MEASURED":
        live = _num(honest.get("ai_visibility_score"))
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
