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

