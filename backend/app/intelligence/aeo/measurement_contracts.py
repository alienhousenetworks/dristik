"""
Dristik AEO Shared Measurement Contracts & Provenance Layer.

Governing Principle:
  One question intelligence layer. One evidence contract.
  Two independent measurement modes. One unified remediation workflow.
  Zero fabricated visibility metrics.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MeasurementMode(str, Enum):
    SANDBOX = "sandbox"                    # First-party on-page extraction & RAG laboratory
    LIVE_BENCHMARK = "live_benchmark"      # Empirical external answer-engine API queries


class ClaimSupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNASSESSABLE = "UNASSESSABLE"


class NormalizedEvidenceRecord(BaseModel):
    """
    Normalized, reproducible evidence unit.
    Heading is recorded only when actually observed in the DOM (never fabricated).
    """
    evidence_id: str = Field(..., description="Stable evidence identifier")
    evidence_type: Literal[
        "DOM_PASSAGE", "JSON_LD", "LIVE_ANSWER", "CITATION_URL", "EXTERNAL_SOURCE"
    ]
    source_url: str = Field(..., description="Original source URL where evidence was collected")
    canonical_url: Optional[str] = Field(None, description="Resolved canonical URL, if verified")
    snapshot_id: str = Field(..., description="Crawl snapshot or live run identifier")
    section_heading: Optional[str] = Field(
        None,
        description="Observed DOM heading (e.g. 'H2: Pricing Tiers') or None when no heading is present"
    )
    content_hash: str = Field(..., description="SHA-256 hash identifying the exact captured passage")
    observed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp when evidence was collected"
    )
    provenance: Literal["FIRST_PARTY_CRAWL", "EXTERNAL_ENGINE", "THIRD_PARTY_DIRECTORY"]
    verification_status: Literal["VERIFIED", "PARTIALLY_VERIFIED", "UNRESOLVED"] = "VERIFIED"
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    dom_selector: Optional[str] = None

    @classmethod
    def create_from_passage(
        cls,
        text: str,
        source_url: str,
        snapshot_id: str,
        canonical_url: Optional[str] = None,
        section_heading: Optional[str] = None,
        dom_selector: Optional[str] = None,
        provenance: Literal["FIRST_PARTY_CRAWL", "EXTERNAL_ENGINE", "THIRD_PARTY_DIRECTORY"] = "FIRST_PARTY_CRAWL",
    ) -> NormalizedEvidenceRecord:
        clean_text = (text or "").strip()
        chash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
        eid = f"EV-{snapshot_id[-6:] if len(snapshot_id) >= 6 else '000000'}-{chash[:8]}"
        return cls(
            evidence_id=eid,
            evidence_type="DOM_PASSAGE",
            source_url=source_url,
            canonical_url=canonical_url,
            snapshot_id=snapshot_id,
            section_heading=section_heading.strip() if section_heading and section_heading.strip() else None,
            content_hash=chash,
            observed_at=datetime.now(timezone.utc).isoformat(),
            provenance=provenance,
            verification_status="VERIFIED" if clean_text else "UNRESOLVED",
            dom_selector=dom_selector,
        )


class SharedResultEnvelope(BaseModel):
    """
    Outer result envelope returned by both Sandbox and Live Benchmark systems.
    Keeps outer structure consistent while preserving independent metric schemas.
    """
    run_id: str
    question_id: str
    measurement_mode: MeasurementMode
    status: Literal["COMPLETED", "PARTIAL", "FAILED", "NOT_EVALUATED"]
    crawl_snapshot_id: Optional[str] = None
    index_version: Optional[str] = None
    measured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_records: List[NormalizedEvidenceRecord] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    error: Optional[str] = None
