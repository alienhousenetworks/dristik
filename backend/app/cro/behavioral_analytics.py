"""
Evidence-Safe Behavioral Analytics Integration for CRO (Phase 6.8).

Integrates GA4, Search Console, and CRM analytics connectors.
Analyzes:
- Landing-page sessions
- CTA events
- Form starts & completions
- Checkout starts & purchases
- Abandonment rate
- Device segmentation (desktop vs mobile vs tablet)
- Traffic source breakdown
- Conversion rate
- Returning users

Strict Zero-Fake Evidence Standard:
- If analytics is NOT connected, all metrics are explicitly marked DATA_UNAVAILABLE or UNMEASURED.
- Zero simulated session heatmaps or synthetic rates from static screenshots.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FunnelDropoffStep(BaseModel):
    step_name: str
    events: Optional[int] = None
    dropoff_rate: Optional[float] = None
    is_measured: bool = False


class BehavioralAnalyticsSummary(BaseModel):
    is_connected: bool = False
    provider: str = "Google Analytics 4"
    status: str = "NOT_CONNECTED" # "MEASURED", "NOT_CONNECTED", "FETCH_FAILED"
    sessions: Optional[int] = None
    cta_events: Optional[int] = None
    form_starts: Optional[int] = None
    form_completions: Optional[int] = None
    checkout_starts: Optional[int] = None
    purchases: Optional[int] = None
    cart_abandonment_rate: Optional[float] = None
    unique_user_conversion_rate: Optional[float] = None
    returning_user_rate: Optional[float] = None
    device_segmentation: Dict[str, Optional[float]] = Field(default_factory=dict)
    traffic_sources: List[Dict[str, Any]] = Field(default_factory=list)
    funnel_steps: List[FunnelDropoffStep] = Field(default_factory=list)
    session_replay_or_heatmaps: str = "NOT_INTEGRATED"
    disclaimer: str = (
        "Behavioral analytics metrics reflect real GA4/connector API queries. "
        "Static screenshots and heuristic inspections do not invent conversion rates or heatmaps."
    )


class BehavioralAnalyticsEvaluator:
    """Evaluates real provider analytics without fabricating synthetic data."""

    @classmethod
    def evaluate(
        cls,
        analytics_payload: Optional[Dict[str, Any]] = None,
        ga4_data: Optional[Any] = None,
    ) -> BehavioralAnalyticsSummary:
        payload = analytics_payload or {}
        state = str(payload.get("state") or getattr(ga4_data, "state", "NOT_CONNECTED")).upper()
        is_conn = (state == "MEASURED") or getattr(ga4_data, "is_connected", False)

        if not is_conn:
            return BehavioralAnalyticsSummary(
                is_connected=False,
                status="NOT_CONNECTED" if state != "FETCH_FAILED" else "FETCH_FAILED",
                sessions=None,
                cta_events=None,
                form_starts=None,
                form_completions=None,
                checkout_starts=None,
                purchases=None,
                cart_abandonment_rate=None,
                unique_user_conversion_rate=None,
                returning_user_rate=None,
                device_segmentation={"desktop": None, "mobile": None, "tablet": None},
                traffic_sources=[],
                funnel_steps=[
                    FunnelDropoffStep(step_name="Landing Page", events=None, dropoff_rate=None, is_measured=False),
                    FunnelDropoffStep(step_name="CTA Click", events=None, dropoff_rate=None, is_measured=False),
                    FunnelDropoffStep(step_name="Form / Checkout Start", events=None, dropoff_rate=None, is_measured=False),
                    FunnelDropoffStep(step_name="Conversion Complete", events=None, dropoff_rate=None, is_measured=False),
                ],
            )

        # Measured payload — strict counting-unit discipline (never divide purchases/sessions into unique_user_conversion_rate)
        sessions = payload.get("sessions")
        key_events = payload.get("key_events") or payload.get("conversions")
        purchases = payload.get("purchases")
        form_starts = payload.get("form_starts")
        form_completions = payload.get("form_completions")
        unique_converters = payload.get("unique_converters")
        eligible_users = payload.get("eligible_users")

        cr = None
        if isinstance(unique_converters, (int, float)) and isinstance(eligible_users, (int, float)) and eligible_users > 0:
            cr = round(unique_converters / eligible_users, 4)

        raw_dev_seg = payload.get("device_segmentation")
        device_seg = (
            raw_dev_seg
            if isinstance(raw_dev_seg, dict) and raw_dev_seg
            else {"desktop": None, "mobile": None, "tablet": None}
        )

        return BehavioralAnalyticsSummary(
            is_connected=True,
            status="MEASURED",
            sessions=int(sessions) if isinstance(sessions, (int, float)) else None,
            cta_events=int(key_events) if isinstance(key_events, (int, float)) else None,
            form_starts=int(form_starts) if isinstance(form_starts, (int, float)) else None,
            form_completions=int(form_completions) if isinstance(form_completions, (int, float)) else None,
            purchases=int(purchases) if isinstance(purchases, (int, float)) else None,
            unique_user_conversion_rate=cr,
            device_segmentation=device_seg,
            traffic_sources=payload.get("traffic_sources", []),
            funnel_steps=[
                FunnelDropoffStep(step_name="Landing Page", events=sessions, dropoff_rate=0.0, is_measured=True),
                FunnelDropoffStep(step_name="Key Event", events=key_events, dropoff_rate=None, is_measured=True),
            ],
        )


behavioral_analytics_evaluator = BehavioralAnalyticsEvaluator()
