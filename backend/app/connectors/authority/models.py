"""Normalized external-authority records.

Vendor scores stay on the record that produced them. There is no field
for a combined authority score.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

PERIOD_DAYS = (7, 28, 90, 365)
PERIOD_LABELS = {7: "7 days", 28: "28 days", 90: "90 days", 365: "12 months"}

CoverageState = Literal[
    "MEASURED",
    "PARTIALLY_MEASURED",
    "NOT_CONNECTED",
    "NOT_APPLICABLE",
    "UNAVAILABLE",
    "INFERRED",
]
EvidenceBasis = Literal["DIRECT_PROVIDER_EVIDENCE", "INFERRED", "UNVERIFIED"]
EntityStatus = Literal["VERIFIED", "OBSERVED", "INFERRED", "UNKNOWN"]
Applicability = Literal["LOCAL_BUSINESS", "NON_LOCAL_BUSINESS", "UNKNOWN"]
CollectionTier = Literal["FREE", "STANDARD", "ADVANCED"]
AuthMode = Literal["oauth", "api_key", "basic"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}{digest}"


def period_window(days: int, now: Optional[datetime] = None) -> tuple[str, str, str, str]:
    """Current window plus the immediately previous window of the same length."""
    end = (now or utcnow()).astimezone(timezone.utc).date()
    start = end - timedelta(days=days)
    previous_end = start
    previous_start = previous_end - timedelta(days=days)
    return (
        start.isoformat(),
        end.isoformat(),
        previous_start.isoformat(),
        previous_end.isoformat(),
    )


class ProviderCapabilities(BaseModel):
    search_performance: bool = False
    indexing: bool = False
    sitemaps: bool = False
    backlinks: bool = False
    referring_domains: bool = False
    analytics: bool = False
    business_profile: bool = False
    brand_mentions: bool = False
    citations: bool = False
    serp: bool = False
    competitors: bool = False
    crawl_stats: bool = False
    sentiment: bool = False


class ExternalRecord(BaseModel):
    record_id: str
    record_type: str
    project_id: str
    provider: str
    source: str
    external_account_id: Optional[str] = None
    external_property_id: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None
    metric: str
    metric_type: Optional[str] = None
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    collected_at: str
    evidence_url: Optional[str] = None
    raw_provider_reference: Optional[str] = None
    confidence: float = 1.0
    status: str = "MEASURED"
    evidence_basis: EvidenceBasis = "DIRECT_PROVIDER_EVIDENCE"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    snapshot_id: Optional[str] = None


class SearchPerformanceRecord(ExternalRecord):
    record_type: str = "search_performance"


class BacklinkRecord(ExternalRecord):
    record_type: str = "backlink"


class ReferringDomainRecord(ExternalRecord):
    record_type: str = "referring_domain"


class BrandMentionRecord(ExternalRecord):
    record_type: str = "brand_mention"


class BusinessListingRecord(ExternalRecord):
    record_type: str = "business_listing"


class BusinessProfileMetric(ExternalRecord):
    record_type: str = "business_profile_metric"


class EntitySignal(ExternalRecord):
    record_type: str = "entity_signal"


class CompetitorSignal(ExternalRecord):
    record_type: str = "competitor_signal"


class ExternalAccount(BaseModel):
    account_id: str
    provider: str
    external_account_id: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExternalProperty(BaseModel):
    property_id: str
    provider: str
    external_property_id: str
    label: Optional[str] = None
    domain: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RawPayload(BaseModel):
    endpoint: str
    payload: Dict[str, Any] | List[Any]
    http_status: int = 200


class CollectionResult(BaseModel):
    provider: str
    connection_status: str = "CONNECTED"
    data_state: CoverageState = "NOT_CONNECTED"
    records: List[ExternalRecord] = Field(default_factory=list)
    accounts: List[ExternalAccount] = Field(default_factory=list)
    properties: List[ExternalProperty] = Field(default_factory=list)
    raw_payloads: List[RawPayload] = Field(default_factory=list)
    error: Optional[str] = None
    partial_errors: List[str] = Field(default_factory=list)
    quota_status: Optional[str] = None
    note: Optional[str] = None


class ExternalFinding(BaseModel):
    finding_id: str
    pillar: str
    category: str = "EXTERNAL_AUTHORITY"
    severity: str
    source: str
    provider: str
    evidence_basis: EvidenceBasis
    metric: str
    observed_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    previous_value: Optional[Any] = None
    period: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.9
    scope: str
    impact: str
    recommendation: str
    verification_method: str
    title: str
    description: str
    data_state: CoverageState
    evidence_url: Optional[str] = None
    vendor_metric_label: Optional[str] = None


VENDOR_METRIC_LABELS = {
    ("ahrefs", "domain_rating"): "Ahrefs Domain Rating",
    ("semrush", "authority_score"): "Semrush Authority Score",
    ("majestic", "trust_flow"): "Majestic Trust Flow",
    ("majestic", "citation_flow"): "Majestic Citation Flow",
}


def vendor_metric_label(provider: str, metric: str) -> Optional[str]:
    return VENDOR_METRIC_LABELS.get((provider, metric))
