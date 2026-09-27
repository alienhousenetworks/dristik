"""
Dristik AI Evidence Models
Universal immutable evidence schema with strict provenance.
"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from enum import Enum

class ProvenanceStatus(str, Enum):
    VERIFIED = "verified"
    MEASURED = "measured"
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    NOT_CONNECTED = "not_connected"
    NOT_CONFIGURED = "not_configured"
    NOT_RUN = "not_run"
    INVALID_EVIDENCE = "invalid_evidence"

class ResultProvenance(BaseModel):
    status: ProvenanceStatus = Field(default=ProvenanceStatus.OBSERVED)
    source: str = Field(..., description="Target URL, DOM element, API route, or provider identifier")
    source_type: str = Field(default="dom", description="Source channel: dom, schema, http, api, engine, inferred")
    evidence_refs: list[str] = Field(default_factory=list, description="IDs of backing immutable Evidence items")
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    agent: Optional[str] = None
    provider: Optional[str] = None
    is_live: bool = True
    is_simulated: bool = False
    details: Optional[dict[str, Any]] = None

    model_config = ConfigDict(frozen=True)

class Evidence(BaseModel):
    id: str = Field(..., description="Unique immutable evidence ID, e.g. ev_001")
    source_type: str = Field(..., description="Evidence category source")
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    value: Optional[Any] = None
    analyzer: str = Field(..., description="Name of deterministic analyzer that produced this evidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hash: str = Field(..., description="SHA-256 cryptographic hash of extracted evidence payload")
    content_sha256: str = Field(default="", description="SHA-256 of raw source material at fetch time")
    fetched_at: Optional[datetime] = None
    raw_snapshot_id: Optional[str] = Field(default=None, description="Content-addressed snapshot of the raw fetch")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)

    def to_ref(self) -> "EvidenceRef":
        st = (self.source_type or "").lower()
        if st in ("crawl", "http", "dom", "html", "robots", "sitemap"):
            mapped_st = "crawl"
        elif st in ("measured", "perf", "performance", "crux", "lighthouse", "meta"):
            mapped_st = "measured"
        elif st in ("external", "gsc", "ga4", "ahrefs", "semrush", "dataforseo"):
            mapped_st = "external"
        else:
            mapped_st = "derived"
        return EvidenceRef(
            source_type=mapped_st,
            source_id=self.id,
            evidence_hash=self.hash,
            observed_at=self.timestamp,
            methodology_version="dristik_v2.1",
            url=self.url,
            selector=self.selector,
            snippet=(self.text[:200] if self.text else None),
            observed_value=self.value,
            collector_or_analyzer=self.analyzer,
            metadata=dict(self.metadata),
        )


class DataAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_CONNECTED = "not_connected"
    NOT_CONFIGURED = "not_configured"
    NOT_EVALUATED = "not_evaluated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"


class DataAvailability(BaseModel):
    status: DataAvailabilityStatus = Field(default=DataAvailabilityStatus.AVAILABLE)
    reason: Optional[str] = None
    source: Optional[str] = None
    missing_evidence_required: Optional[str] = None
    required_action: Optional[str] = None
    observed_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(frozen=True)


class EvidenceRef(BaseModel):
    source_type: str = Field(
        default="crawl",
        description="Classification of evidence origin: crawl, measured, derived, external",
    )
    source_id: str = Field(..., description="Unique identifier of raw evidence node or analyzer")
    evidence_hash: str = Field(..., description="SHA-256 cryptographic hash of extracted payload")
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    methodology_version: str = Field(default="dristik_v2.1")
    url: Optional[str] = None
    selector: Optional[str] = None
    snippet: Optional[str] = None
    observed_value: Optional[Any] = None
    collector_or_analyzer: Optional[str] = None
    parent_evidence_refs: list[str] = Field(default_factory=list, description="IDs of parent evidence nodes for derived claims")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


