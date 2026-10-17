"""Structured evidence record for a finding.

An identifier or a hash does not establish that a finding is correct, that its
source was authentic, or that the analysis was sound. The record keeps the
source, observation, time, scope, method, confidence, and later decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


CONFIDENCE_LABELS = ("observed", "estimated", "inferred", "unverified")


class StructuredEvidenceRecord(BaseModel):
    evidence_id: str
    source: str = Field(description="Exact URL, integration, API, or dataset.")
    observation: str
    observed_at: str
    scope: str = Field(description="Page, sample, domain, or external dataset.")
    scope_detail: Optional[str] = None
    method: str = Field(description="Analyzer version, rules, configuration, and model version.")
    confidence: str = "observed"
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    decision: Optional[str] = None
    outcome: Optional[str] = None
    proves: str = "provenance_of_this_observation"

    def canonical_body(self) -> dict[str, Any]:
        if self.confidence not in CONFIDENCE_LABELS:
            raise ValueError(f"confidence must be one of {CONFIDENCE_LABELS}")
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "observation": self.observation,
            "observed_at": self.observed_at,
            "scope": self.scope,
            "scope_detail": self.scope_detail,
            "method": self.method,
            "confidence": self.confidence,
            "reproducibility": self.reproducibility,
            "decision": self.decision,
            "outcome": self.outcome,
        }


def record_from_finding(finding: Any, *, method: str = "dristik.audit") -> StructuredEvidenceRecord:
    """Project an existing finding into the commercial evidence record."""
    refs = list(getattr(finding, "evidence_refs", None) or [])
    urls = list(getattr(finding, "affected_urls", None) or [])
    source = urls[0] if urls else (refs[0] if refs else "audit_finding")
    observed = getattr(finding, "finding", None) or getattr(finding, "description", None) or getattr(finding, "title", "")
    scope = getattr(finding, "evidence_scope", None) or "unspecified"
    label = str(getattr(finding, "confidence_label", "") or "").lower()
    if "confirm" in label or getattr(finding, "evidence_class", None) and "OBSERVED" in str(getattr(finding, "evidence_class", "")):
        confidence = "observed"
    elif "estimat" in label:
        confidence = "estimated"
    elif "infer" in label or "likely" in label or "potential" in label:
        confidence = "inferred"
    elif not refs and not urls:
        confidence = "unverified"
    else:
        confidence = "observed" if float(getattr(finding, "confidence", 0) or 0) >= 0.85 else "inferred"
    return StructuredEvidenceRecord(
        evidence_id=str(getattr(finding, "finding_id", None) or getattr(finding, "id", "finding")),
        source=str(source),
        observation=str(observed)[:2000],
        observed_at=datetime.now(timezone.utc).isoformat(),
        scope=str(scope),
        scope_detail=None if not getattr(finding, "scope_sample_size", None) else (
            f"{getattr(finding, 'scope_hit_count', 0)} of {finding.scope_sample_size} sampled"
        ),
        method=method,
        confidence=confidence,
        reproducibility={
            "evidence_refs": refs,
            "provenance_hash": getattr(finding, "provenance_hash", None),
            "rule_id": getattr(finding, "rule_id", None),
        },
        decision=getattr(finding, "recommendation", None),
        outcome=getattr(finding, "resolution_status", None),
    )
