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

FORMULA_VERSION = "dristik_central_scoring_v5.1"


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _score(value: Any) -> Optional[float]:
    """Accept only finite measured scores in the documented 0..100 range."""
    number = _num(value)
    return number if number is not None and 0.0 <= number <= 100.0 else None


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


def rating_for_displayed(score: Optional[float]) -> tuple[str, str]:
    """Canonical (letter_grade, health_label) pair across all reports and UI surfaces."""
    if score is None:
        return "—", "Unmeasured"
    if score >= 93:
        return "A+", "Exceptional"
    if score >= 85:
        return "A", "Excellent"
    if score >= 75:
        return "B", "Good"
    if score >= 65:
        return "C", "Moderate"
    if score >= 50:
        return "D", "Needs Attention"
    return "F", "Low readiness"


def _score_claim_pattern(token: Optional[str] = None) -> "re.Pattern[str]":
    number = rf"{re.escape(token)}(?:\.0)?" if token else r"\d+(?:\.\d+)?"
    return re.compile(
        rf"{number}/100(?:\s*\([^)]*\))?(?:,?\s*grade\s+[A-F]\+?)?",
        re.IGNORECASE,
    )


def first_story_score(story: str) -> Optional[float]:
    """The first composite-shaped score in a sentence, if the prose states one."""
    if not story:
        return None
    match = _score_claim_pattern().search(story)
    if not match:
        return None
    raw = match.group(0).split("/100", 1)[0].strip()
    try:
        number = float(raw)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def story_matches_composite(story: str, composite: Optional[float], tolerance: float = 0.15) -> bool:
    """A story with no score claim agrees. A stated score must be the dossier composite."""
    claimed = first_story_score(story)
    if claimed is None or composite is None:
        return True
    return abs(claimed - composite) <= tolerance


def align_story_score(story: str, sealed_score: Any, composite: float) -> str:
    """Replace the headline score with the dossier composite and its grade.

    The sealed overall and a synthesizer number are both rewritten. A later
    pillar score in the same paragraph is left alone.
    """
    if not story or composite is None:
        return story
    replacement = f"{composite:.1f}/100 (grade {grade_for_displayed(composite)})"
    sealed = _num(sealed_score)
    if sealed is not None:
        sealed_token = str(int(round(sealed)))
        updated, count = _score_claim_pattern(sealed_token).subn(replacement, story, count=1)
        if count:
            return updated
    updated, count = _score_claim_pattern().subn(replacement, story, count=1)
    return updated if count else story


def _live_citation(payload: dict, honest: dict) -> Optional[float]:
    if not live_execution_proven(payload):
        return None
    live = _score(honest.get("live_ai_citation_score"))
    if live is None and honest.get("ai_visibility_status") == "MEASURED":
        live = _score(honest.get("ai_visibility_score"))
    if live is None:
        card = payload.get("ai_visibility_scorecard") or {}
        if isinstance(card, dict):
            live = _score(card.get("citation_rate_pct"))
    return live


def displayed_composite(report: Any) -> Optional[float]:
    """Return the canonical enterprise composite score, or None when no pillars are measured."""
    payload = _as_report(report)
    if not payload:
        return None
    try:
        from app.domain.scoring.canonical_scorecard import CanonicalScorecardEngine
        card = CanonicalScorecardEngine.evaluate_from_report(report)
        return card.composite_health_score
    except Exception:
        # Fallback to direct sealed overall_score if available
        scores = payload.get("scores") or {}
        return _score(scores.get("overall_score"))


def compute_ttfb_summary(samples: list[float]) -> dict[str, Any]:
    """Deterministic TTFB aggregation from raw samples with median, mean, P90, and outlier detection."""
    clean = sorted(float(v) for v in (samples or []) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) and float(v) > 0)
    n = len(clean)
    if n == 0:
        return {
            "sample_size": 0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "median_ms": 0.0,
            "mean_ms": 0.0,
            "p90_ms": 0.0,
            "trimmed_mean_ms": 0.0,
            "outliers_ms": [],
            "outlier_count": 0,
        }
    mid = n // 2
    median_ms = clean[mid] if n % 2 == 1 else (clean[mid - 1] + clean[mid]) / 2.0
    mean_ms = sum(clean) / n
    p90_pos = max(0, min(n - 1, math.ceil(0.9 * n) - 1))
    p90_ms = clean[p90_pos]
    outlier_threshold = max(2000.0, median_ms * 3.0)
    outliers = [round(v, 1) for v in clean if n >= 3 and v > outlier_threshold]
    inliers = [v for v in clean if not (n >= 3 and v > outlier_threshold)] or clean
    trimmed_mean = sum(inliers) / len(inliers)
    return {
        "sample_size": n,
        "min_ms": round(clean[0], 1),
        "max_ms": round(clean[-1], 1),
        "median_ms": round(median_ms, 1),
        "mean_ms": round(mean_ms, 1),
        "p90_ms": round(p90_ms, 1),
        "trimmed_mean_ms": round(trimmed_mean, 1),
        "outliers_ms": outliers,
        "outlier_count": len(outliers),
    }
