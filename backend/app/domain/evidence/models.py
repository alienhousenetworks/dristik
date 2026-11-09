"""
Dristik AI Evidence Models
Universal immutable evidence schema with strict provenance.
"""
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator
from enum import Enum

from app.domain.enums import ProvenanceType, CollectionStatus

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
    audit_run_id: Optional[str] = Field(default=None, description="Associated audit execution run ID")
    source_type: str = Field(..., description="Evidence category source: HTTP, DOM, browser, crawler, API, etc.")
    source_reference: Optional[str] = Field(default=None, description="Original URL, source identifier, or provider reference")
    raw_observation: Optional[Any] = Field(default=None, description="Original captured information")
    normalized_observation: Optional[Any] = Field(default=None, description="Parsed or standardized representation")
    collection_method: Optional[str] = Field(default=None, description="How the information was obtained")
    scope: Optional[str] = Field(default=None, description="URL, page, origin, domain, site, or provider scope")
    captured_at: Optional[datetime] = Field(default=None, description="Actual collection timestamp")
    provenance_type: ProvenanceType = Field(default=ProvenanceType.RAW, description="RAW, MEASURED, DERIVED, EXTERNAL, or INFERRED")
    integrity_hash: Optional[str] = Field(default=None, description="Cryptographic hash of the original captured artifact")
    limitations: Optional[str] = Field(default=None, description="Known evidence limitations")
    collection_status: CollectionStatus = Field(default=CollectionStatus.SUCCESS, description="SUCCESS, FAILED, UNAVAILABLE, or NOT_TESTED")
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    value: Optional[Any] = None
    analyzer: str = Field(..., description="Name of deterministic analyzer that produced this evidence")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hash: str = Field(..., description="SHA-256 cryptographic hash of extracted evidence payload")
    content_sha256: str = Field(default="", description="SHA-256 of raw source material at fetch time")
    fetched_at: Optional[datetime] = None
    raw_snapshot_id: Optional[str] = Field(default=None, description="Content-addressed snapshot of the raw fetch")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _hydrate_canonical_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "evidence_id" in data and "id" not in data:
                data["id"] = data["evidence_id"]
            if not data.get("source_reference") and data.get("url"):
                data["source_reference"] = data["url"]
            if not data.get("integrity_hash") and data.get("hash"):
                data["integrity_hash"] = data["hash"]
            if not data.get("captured_at"):
                data["captured_at"] = data.get("timestamp") or datetime.now(timezone.utc)
            if data.get("raw_observation") is None:
                data["raw_observation"] = data.get("value") if data.get("value") is not None else data.get("text")
            if data.get("normalized_observation") is None:
                data["normalized_observation"] = data.get("value") if data.get("value") is not None else data.get("text")
        return data

    @property
    def evidence_id(self) -> str:
        return self.id

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


class MachineObservation(BaseModel):
    """
    Layer 1 — Canonical Machine Observation.
    Immutable empirical observation directly extracted by crawler, DOM parser, or HTTP probe.
    """
    type: str = Field(default="observation", description="Literal type identifier for Layer 1 machine observations")
    attribute: str = Field(..., description="Observed machine attribute, e.g. title, h1, status_code, schema_org")
    value: Any = Field(..., description="Exact extracted machine value")
    source: str = Field(..., description="Machine extraction channel, e.g. html, http_header, dom, robots, sitemap")
    evidence_id: str = Field(..., description="Unique immutable evidence ID, e.g. EV_001")
    url: Optional[str] = None
    selector: Optional[str] = None
    element: Optional[str] = None
    expected_condition: Optional[str] = None
    test_method: Optional[str] = None
    response_status: Optional[int] = None
    snippet: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_sha256: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(frozen=True)

    def to_layer1_json(self) -> dict[str, Any]:
        """Returns the exact canonical Layer 1 JSON representation."""
        return {
            "type": self.type,
            "attribute": self.attribute,
            "value": self.value,
            "source": self.source,
            "evidence_id": self.evidence_id,
        }



