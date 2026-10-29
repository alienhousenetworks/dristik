"""Observed traffic only.

Chrome UX Report is real-user experience data for eligible origins. It is not
a monthly-visit counter. This module does not synthesize visits, bounce rate,
rank, or country mix from a domain hash.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrafficSourceShare(BaseModel):
    direct_pct: float = Field(..., description="Direct traffic percentage")
    search_pct: float = Field(..., description="Search traffic percentage")
    referrals_pct: float = Field(..., description="Referral traffic percentage")
    social_pct: float = Field(..., description="Social traffic percentage")
    mail_pct: float = Field(..., description="Email traffic percentage")
    display_ads_pct: float = Field(..., description="Display Ads traffic percentage")
    other_pct: float = Field(..., description="Other traffic percentage")


class CountryTrafficShare(BaseModel):
    country_name: str
    country_code: str
    percentage: float
    visits_share: int


class MonthlyVisitPoint(BaseModel):
    month_label: str
    visits: int


class DomainTrafficSummary(BaseModel):
    domain: str
    data_origin: str = "NOT_MEASURED"
    is_estimated: bool = False
    measurement_status: str = "not_measured"
    confidence_interval: Optional[str] = None
    monthly_visits: Optional[int] = None
    bounce_rate_pct: Optional[float] = None
    pages_per_visit: Optional[float] = None
    avg_duration_formatted: Optional[str] = None
    avg_duration_seconds: Optional[int] = None
    global_rank: Optional[int] = None
    country_rank: Optional[int] = None
    traffic_sources: Dict[str, float] = Field(default_factory=dict)
    top_regions: List[CountryTrafficShare] = Field(default_factory=list)
    visits_history: List[MonthlyVisitPoint] = Field(default_factory=list)
    field_experience: Optional[Dict[str, Any]] = None
    attribution_note: str = (
        "Monthly visits are not estimated. Chrome UX Report measures real-user "
        "experience for eligible origins. It is not a traffic counter. Connect "
        "GA4 or server logs to report observed sessions."
    )


def _clean_domain(domain: str) -> str:
    clean = re.sub(r"^https?://", "", domain.strip().lower()).strip("/")
    return clean.split("/")[0]


def estimate_domain_traffic(
    domain: str,
    crux_data: Optional[Dict[str, Any]] = None,
    serp_count: int = 0,
    organic_keywords_count: int = 0,
    measured_monthly_visits: Optional[int] = None,
    measurement_source: Optional[str] = None,
) -> DomainTrafficSummary:
    """Return measured visits when a source supplies them. Otherwise return not measured.

    ``serp_count`` and ``organic_keywords_count`` are accepted so existing callers
    keep working. They are not converted into visits. ``crux_data`` is attached
    as field-experience context and is not converted into visits.
    """
    del serp_count, organic_keywords_count
    clean_domain = _clean_domain(domain)
    if measured_monthly_visits is None:
        return DomainTrafficSummary(
            domain=clean_domain,
            data_origin="NOT_MEASURED",
            is_estimated=False,
            measurement_status="not_measured",
            field_experience=crux_data,
            attribution_note=(
                "No analytics source supplied monthly visits. "
                "CrUX field data, when present, describes user experience for an eligible origin. "
                "It is not used as a traffic estimate."
            ),
        )
    if measured_monthly_visits < 0:
        raise ValueError("Measured monthly visits cannot be negative.")
    return DomainTrafficSummary(
        domain=clean_domain,
        data_origin=measurement_source or "FIRST_PARTY",
        is_estimated=False,
        measurement_status="measured",
        monthly_visits=measured_monthly_visits,
        field_experience=crux_data,
        attribution_note=(
            f"Monthly visits come from {measurement_source or 'a supplied first-party source'}. "
            "This is an observed count, not a CrUX conversion and not a modeled estimate."
        ),
    )
