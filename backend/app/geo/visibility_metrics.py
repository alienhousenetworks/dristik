"""Counts for AI search visibility. Failed runs stay out of the denominator.

A missing execution is not a zero. Percentages are None when the denominator
is empty. Raw counts are always returned.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

_FAILED = {
    "ERROR", "TIMEOUT", "RATE_LIMITED", "KEY_MISSING", "BLOCKED",
    "CAPTCHA", "NOT_TESTED", "FAILED", "UNAVAILABLE", "NOT_MEASURED",
}
_RECOMMENDATION_INTENTS = {
    "recommendation", "comparison", "alternative", "alternative_discovery",
    "alternatives", "commercial", "high_intent", "purchase",
    "purchase_research", "transactional", "category_discovery",
}


def _get(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _status(row: Any) -> str:
    return str(_get(row, "status", "") or _get(row, "execution_status", "") or "SUCCESS").upper()


def _valid(row: Any) -> bool:
    return _status(row) not in _FAILED


def _mentioned(row: Any) -> bool:
    return bool(_get(row, "brand_mentioned", None) if _get(row, "brand_mentioned", None) is not None else _get(row, "was_mentioned", False))


def _cited(row: Any) -> bool:
    if _get(row, "brand_cited", None) is not None:
        return bool(_get(row, "brand_cited"))
    return bool(_get(row, "was_cited", None) or _get(row, "was_first_party_cited", False))


def _recommends(row: Any) -> bool:
    if _get(row, "brand_recommended", None) is not None:
        return bool(_get(row, "brand_recommended"))
    prominence = str(_get(row, "position_prominence", "") or "").upper()
    return prominence == "PRIMARY_RECOMMENDATION"


def _intent(row: Any) -> str:
    return str(_get(row, "commercial_intent", None) or _get(row, "category", None) or _get(row, "intent", "") or "").lower()


def _competitor_citations(row: Any) -> int:
    cited = _get(row, "competitors_cited", None) or []
    return len(list(cited))


def _pct(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(100.0 * numerator / denominator, 1)


def compute_visibility_metrics(records: Iterable[Any]) -> Dict[str, Any]:
    """Mention, recommendation, citation rate, and citation share from stored runs."""
    rows = list(records or [])
    valid = [row for row in rows if _valid(row)]
    failed = [row for row in rows if not _valid(row)]
    mentions = sum(1 for row in valid if _mentioned(row))
    citations = sum(1 for row in valid if _cited(row))
    recommendation_rows = [row for row in valid if _intent(row) in _RECOMMENDATION_INTENTS]
    recommendations = sum(1 for row in recommendation_rows if _recommends(row))
    client_citations = citations
    competitor_citations = sum(_competitor_citations(row) for row in valid)
    share_denominator = client_citations + competitor_citations
    return {
        "valid_responses": len(valid),
        "failed_or_blocked": len(failed),
        "mentions": mentions,
        "mention_rate_pct": _pct(mentions, len(valid)),
        "recommendation_responses": len(recommendation_rows),
        "recommendations": recommendations,
        "recommendation_rate_pct": _pct(recommendations, len(recommendation_rows)),
        "client_citations": client_citations,
        "citation_rate_pct": _pct(citations, len(valid)),
        "competitor_citations": competitor_citations,
        "citation_share_pct": _pct(client_citations, share_denominator),
    }
