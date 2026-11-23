"""
Report Freshness Guard & Two-Consecutive-Round Trend Confirmation.

Adapted from GeoLook's MIT-licensed `deliver.py` and `method.md` attribution discipline:
- Never silently bundles stale verification snapshots (`verified_at < audited_at`)
  into client deliverables.
- Single-round AI visibility swings are explicitly classified as `OBSERVATIONAL_NOISE`;
  only two consecutive comparable rounds moving in the same direction confirm a trend.
"""
from __future__ import annotations

from typing import List, Optional, Sequence
from pydantic import BaseModel, Field


class DeliveryFreshnessReport(BaseModel):
    is_fresh: bool
    verification_stale: bool
    audit_date: str
    verified_date: Optional[str] = None
    metrics_date: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class TrendConfirmationResult(BaseModel):
    status: str  # INSUFFICIENT_DATA | OBSERVATIONAL_NOISE | CONFIRMED_UPWARD | CONFIRMED_DOWNWARD | STABLE
    rounds_evaluated: int
    latest_delta: Optional[float] = None
    previous_delta: Optional[float] = None
    note: str


def check_delivery_freshness(
    *,
    audited_at: Optional[str],
    verified_at: Optional[str] = None,
    metrics_at: Optional[str] = None,
) -> DeliveryFreshnessReport:
    """Detect date mismatches between audit, verification, and visibility metrics."""
    audit_date = str(audited_at or "")[:10]
    ver_date = str(verified_at or "")[:10] if verified_at else None
    met_date = str(metrics_at or "")[:10] if metrics_at else None
    notes: List[str] = []

    verification_stale = False
    if not ver_date:
        verification_stale = True
        notes.append("No post-audit verification snapshot recorded for this period.")
    elif audit_date and ver_date < audit_date:
        verification_stale = True
        notes.append(
            f"Verification snapshot ({ver_date}) predates current audit ({audit_date}); "
            "withhold old pass/fail results until re-verified."
        )

    if audit_date and met_date and met_date < audit_date:
        notes.append(f"AI visibility metrics ({met_date}) predate current audit ({audit_date}).")

    return DeliveryFreshnessReport(
        is_fresh=not verification_stale and not notes,
        verification_stale=verification_stale,
        audit_date=audit_date,
        verified_date=ver_date,
        metrics_date=met_date,
        notes=notes,
    )


def evaluate_two_round_trend(
    round_values: Sequence[float],
    *,
    min_delta: float = 0.02,
) -> TrendConfirmationResult:
    """Confirm a directional trend only when two consecutive rounds move the same way >= `min_delta`."""
    vals = [float(v) for v in round_values if v is not None]
    n = len(vals)
    if n < 2:
        return TrendConfirmationResult(
            status="INSUFFICIENT_DATA",
            rounds_evaluated=n,
            note="Need at least 2 comparable sampling rounds to observe movement and 3 rounds to confirm a trend.",
        )

    latest_delta = round(vals[-1] - vals[-2], 4)
    if n == 2:
        return TrendConfirmationResult(
            status="OBSERVATIONAL_NOISE",
            rounds_evaluated=n,
            latest_delta=latest_delta,
            note="Single-round movement is observational only; LLM sampling is stochastic. Confirm on next round.",
        )

    prev_delta = round(vals[-2] - vals[-3], 4)
    if latest_delta >= min_delta and prev_delta >= min_delta:
        return TrendConfirmationResult(
            status="CONFIRMED_UPWARD",
            rounds_evaluated=n,
            latest_delta=latest_delta,
            previous_delta=prev_delta,
            note=f"Two consecutive upward rounds (+{prev_delta:.3f}, +{latest_delta:.3f}).",
        )
    if latest_delta <= -min_delta and prev_delta <= -min_delta:
        return TrendConfirmationResult(
            status="CONFIRMED_DOWNWARD",
            rounds_evaluated=n,
            latest_delta=latest_delta,
            previous_delta=prev_delta,
            note=f"Two consecutive downward rounds ({prev_delta:.3f}, {latest_delta:.3f}). Investigate regression.",
        )
    if abs(latest_delta) < min_delta and abs(prev_delta) < min_delta:
        return TrendConfirmationResult(
            status="STABLE",
            rounds_evaluated=n,
            latest_delta=latest_delta,
            previous_delta=prev_delta,
            note="Metrics remained within noise band across the last two intervals.",
        )
    return TrendConfirmationResult(
        status="OBSERVATIONAL_NOISE",
        rounds_evaluated=n,
        latest_delta=latest_delta,
        previous_delta=prev_delta,
        note="Mixed directional movement across consecutive rounds; treat as sampling noise.",
    )
