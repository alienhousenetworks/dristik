"""Separate technical, visibility, and business results.

A resolved code check is not an increase in citations. A citation change is
not revenue. Observed analytics are not a causal estimate.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class VerificationLayer(BaseModel):
    layer: str
    status: str
    summary: str
    before: Optional[Any] = None
    after: Optional[Any] = None
    uncertainty: Optional[str] = None


class AttributionLayer(BaseModel):
    level: str
    status: str
    summary: str
    model: Optional[str] = None
    values: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def verification_layers_for_check(
    *,
    technical_status: str,
    visibility_measured: bool = False,
    visibility_summary: str = "Search and AI citation change was not measured for this fix.",
    business_measured: bool = False,
    business_summary: str = "Qualified traffic, leads, conversions, and revenue were not measured for this fix.",
) -> list[VerificationLayer]:
    return [
        VerificationLayer(
            layer="technical",
            status=technical_status,
            summary="Whether the targeted condition changed on the re-checked page or response.",
        ),
        VerificationLayer(
            layer="search_visibility",
            status="measured" if visibility_measured else "not_measured",
            summary=visibility_summary,
            uncertainty="A score change is not a citation change." if not visibility_measured else None,
        ),
        VerificationLayer(
            layer="business_outcome",
            status="measured" if business_measured else "not_measured",
            summary=business_summary,
            uncertainty="A deployment is not proof that revenue changed." if not business_measured else None,
        ),
    ]


def attribution_layers_from_channels(google_performance: Optional[dict[str, Any]]) -> list[AttributionLayer]:
    """Level 1 uses connected analytics. Levels 2 and 3 stay unmeasured until a model is supplied."""
    performance = google_performance or {}
    analytics = performance.get("analytics") or {}
    search = performance.get("search_console") or {}
    analytics_state = str(analytics.get("state") or "NOT_CONNECTED")
    search_state = str(search.get("state") or "NOT_CONNECTED")
    observed_values: dict[str, Any] = {}
    limitations = [
        "Referrers can be missing.",
        "Sessions can be misclassified.",
        "AI-assisted conversions can arrive as direct visits or through other channels.",
    ]
    if analytics_state == "MEASURED":
        for key in ("sessions", "conversions", "engagement_rate_pct"):
            if analytics.get(key) is not None:
                observed_values[key] = analytics.get(key)
        observed_values["analytics_property"] = analytics.get("property")
        observed_values["analytics_period"] = analytics.get("period")
    if search_state == "MEASURED":
        for key in ("clicks", "impressions", "average_ctr", "average_position"):
            if search.get(key) is not None:
                observed_values[f"search_console_{key}"] = search.get(key)
    observed_status = "measured" if observed_values else analytics_state.lower()
    observed_summary = (
        "Observed Search Console and analytics values for the connected property and period."
        if observed_values
        else f"Analytics is {analytics_state}. Search Console is {search_state}. No sessions or revenue are invented."
    )
    return [
        AttributionLayer(
            level="observed",
            status=observed_status,
            summary=observed_summary,
            values=observed_values,
            limitations=limitations,
        ),
        AttributionLayer(
            level="associated",
            status="not_measured",
            summary="No stated attribution model has associated leads or revenue with an AI-referred visit.",
            model=None,
            limitations=["Association requires a documented journey and a named attribution model."],
        ),
        AttributionLayer(
            level="incremental",
            status="not_measured",
            summary="No comparison period, control group, or other causal method has been applied.",
            limitations=["Correlation in the observed layer is not causation."],
        ),
    ]


class FlywheelObservation(BaseModel):
    """One intervention outcome that may later train recommendations.

    Failed and successful interventions are both valid records. Reuse requires
    a contractual permission flag. Removing a name does not make the row anonymous.
    """
    finding_type: str
    severity: Optional[str] = None
    evidence_quality: Optional[str] = None
    site_type: Optional[str] = None
    rendering_method: Optional[str] = None
    cms: Optional[str] = None
    patch_type: Optional[str] = None
    implementation_effort: Optional[str] = None
    technical_succeeded: Optional[bool] = None
    visibility_comparable: bool = False
    rolled_back: bool = False
    business_outcome_authorized: bool = False
    reuse_permitted: bool = False
    methodology_version: Optional[str] = None
    notes: Optional[str] = None


def gross_margin_pct(revenue: float, direct_service_costs: float) -> Optional[float]:
    if revenue <= 0:
        return None
    return round(((revenue - direct_service_costs) / revenue) * 100.0, 2)


def verified_remediation_count(records: list[dict[str, Any]]) -> int:
    """North-star count: customer-approved remediations with a technical verification.

    A score increase without a verification does not count.
    """
    count = 0
    for record in records:
        approved = bool(record.get("customer_approved") or record.get("approval_status") == "APPROVED")
        technical = str(record.get("technical_status") or record.get("status") or "")
        if approved and technical in {"RESOLVED", "condition_resolved", "VERIFIED"}:
            count += 1
    return count
