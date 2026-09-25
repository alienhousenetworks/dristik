"""
Dristik Metric Provenance & Evidence Verification Protocol
Ensures that every metric in Dristik traces strictly to verified evidence,
with zero tolerated synthetic or fabricated fallbacks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

from app.domain.enums import MetricProvenanceState

T = TypeVar("T")


class ProvenancedMetric(BaseModel, Generic[T]):
    """
    Every numeric or categorical score presented by Dristik must carry
    its explicit provenance state and evidence pointers.
    """
    value: Optional[T] = None
    provenance: MetricProvenanceState
    evidence_ids: List[str] = Field(default_factory=list)
    source: str
    status_notice: Optional[str] = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Optional[Dict[str, Any]] = None

    @classmethod
    def measured(cls, value: T, source: str, evidence_ids: List[str] = None, notice: Optional[str] = None) -> "ProvenancedMetric[T]":
        return cls(
            value=value,
            provenance=MetricProvenanceState.MEASURED,
            evidence_ids=evidence_ids or [],
            source=source,
            status_notice=notice,
        )

    @classmethod
    def observed(cls, value: T, source: str, evidence_ids: List[str] = None, notice: Optional[str] = None) -> "ProvenancedMetric[T]":
        return cls(
            value=value,
            provenance=MetricProvenanceState.OBSERVED,
            evidence_ids=evidence_ids or [],
            source=source,
            status_notice=notice,
        )

    @classmethod
    def not_configured(cls, source: str, notice: str) -> "ProvenancedMetric[T]":
        return cls(
            value=None,
            provenance=MetricProvenanceState.NOT_CONFIGURED,
            evidence_ids=[],
            source=source,
            status_notice=notice,
        )

    @classmethod
    def not_connected(cls, source: str, notice: str) -> "ProvenancedMetric[T]":
        return cls(
            value=None,
            provenance=MetricProvenanceState.NOT_CONNECTED,
            evidence_ids=[],
            source=source,
            status_notice=notice,
        )

    @classmethod
    def unavailable(cls, source: str, notice: str) -> "ProvenancedMetric[T]":
        return cls(
            value=None,
            provenance=MetricProvenanceState.UNAVAILABLE,
            evidence_ids=[],
            source=source,
            status_notice=notice,
        )
