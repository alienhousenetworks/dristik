"""
Dristik AI Progressive Reporting Contracts.
Defines immutable data structures for Sub-Phase and Consolidated Phase reports,
enforcing evidence traceability, zero-fabrication standards, and provenance.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_MEASURED = "NOT_MEASURED"
    IN_PROGRESS = "IN_PROGRESS"


class ConfidenceLevel(str, Enum):
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    CONTESTED = "CONTESTED"
    UNMEASURED = "UNMEASURED"


class EvidenceTokenReference(BaseModel):
    evidence_id: str
    token_type: str  # dom_selector | cas_snapshot | http_header | dns_record | external_api
    locator: str
    excerpt: Optional[str] = None
    hash_sha256: Optional[str] = None


class ReportFinding(BaseModel):
    finding_id: str
    severity: str  # critical | high | medium | low | info
    title: str
    description: str
    impact: Optional[str] = None
    remediation_hint: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


_FINDING_SEVERITIES = {"critical", "high", "medium", "low", "info"}


def _severity_token(value: Any) -> str:
    raw = getattr(value, "value", value)
    token = str(raw or "info").strip().lower()
    return token if token in _FINDING_SEVERITIES else "info"


def _optional_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _clip(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _evidence_ids(raw: Any) -> List[str]:
    if not raw:
        return []
    ids: List[str] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            ids.append(entry.strip())
            continue
        if isinstance(entry, dict):
            evidence_id = entry.get("evidence_id") or entry.get("id")
        else:
            evidence_id = getattr(entry, "evidence_id", None) or getattr(entry, "id", None)
        if evidence_id:
            ids.append(str(evidence_id))
    return ids


def _finding_from_mapping(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    text = str(
        item.get("statement")
        or item.get("description")
        or item.get("claim_text")
        or item.get("finding")
        or item.get("title")
        or ""
    ).strip()
    title = _optional_text(item.get("title") if isinstance(item.get("title"), str) else None) or _clip(text, 160) or f"Finding {index + 1}"
    description = _optional_text(item.get("description") if isinstance(item.get("description"), str) else None) or text or title
    finding_id = str(item.get("finding_id") or item.get("claim_id") or item.get("id") or "").strip()
    if not finding_id:
        digest = hashlib.sha256(f"{index}:{description}".encode("utf-8")).hexdigest()[:12]
        finding_id = f"obs_{digest}"
    return {
        "finding_id": finding_id,
        "severity": _severity_token(item.get("severity")),
        "title": _clip(title, 180) or f"Finding {index + 1}",
        "description": description,
        "impact": _optional_text(item.get("impact")) or _optional_text(item.get("why_it_matters")) or _optional_text(item.get("business_impact")),
        "remediation_hint": _optional_text(item.get("remediation_hint")) or _optional_text(item.get("recommendation")),
        "evidence_ids": _evidence_ids(item.get("evidence_ids") or item.get("evidence_refs")),
    }


def coerce_report_finding(item: Any, index: int = 0) -> Any:
    """Normalize a string, claim, domain finding, or dict into ReportFinding input."""
    if isinstance(item, ReportFinding):
        return item
    if isinstance(item, str):
        text = item.strip() or f"Finding {index + 1}"
        digest = hashlib.sha256(f"{index}:{text}".encode("utf-8")).hexdigest()[:12]
        return {
            "finding_id": f"obs_{digest}",
            "severity": "info",
            "title": _clip(text, 160),
            "description": text,
        }
    if isinstance(item, dict):
        return _finding_from_mapping(item, index)
    text = str(
        getattr(item, "statement", None)
        or getattr(item, "description", None)
        or getattr(item, "claim_text", None)
        or getattr(item, "finding", None)
        or getattr(item, "title", None)
        or ""
    ).strip()
    title_attr = getattr(item, "title", None)
    description_attr = getattr(item, "description", None)
    return _finding_from_mapping(
        {
            "finding_id": getattr(item, "finding_id", None),
            "claim_id": getattr(item, "claim_id", None),
            "id": getattr(item, "id", None),
            "severity": getattr(item, "severity", None),
            "title": title_attr if isinstance(title_attr, str) else None,
            "description": description_attr if isinstance(description_attr, str) else None,
            "statement": text,
            "impact": getattr(item, "impact", None),
            "why_it_matters": getattr(item, "why_it_matters", None),
            "business_impact": getattr(item, "business_impact", None),
            "remediation_hint": getattr(item, "remediation_hint", None),
            "recommendation": getattr(item, "recommendation", None),
            "evidence_ids": getattr(item, "evidence_ids", None),
            "evidence_refs": getattr(item, "evidence_refs", None),
        },
        index,
    )


def coerce_report_findings(value: Any) -> List[Any]:
    """Accept a list of ReportFinding values, or the strings and claim objects producers emit."""
    if value is None:
        return []
    if isinstance(value, (str, dict)) or isinstance(value, ReportFinding):
        items: List[Any] = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = [value]
    return [coerce_report_finding(item, index) for index, item in enumerate(items)]


class SubPhaseReportContract(BaseModel):
    # Execution Identity
    run_id: str
    phase_id: str  # phase_01_ingestion, phase_02_business, etc.
    phase_name: str
    subphase_id: str  # 1.1, 1.2, 2.1, etc.
    subphase_title: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0
    status: ExecutionStatus = ExecutionStatus.COMPLETED

    # Objective & Agent Identity
    objective: str
    agent_id: str
    agent_model: str = "deterministic"
    execution_mode: str = "deterministic"  # deterministic | reasoning_agent | slm | hybrid

    # Input & Processing
    input_summary: Dict[str, Any] = Field(default_factory=dict)
    processing_steps: List[str] = Field(default_factory=list)

    # Actual Results (Source of Truth)
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    evidence_tokens: List[EvidenceTokenReference] = Field(default_factory=list)
    findings: List[ReportFinding] = Field(default_factory=list)

    @field_validator("findings", mode="before")
    @classmethod
    def _coerce_findings(cls, value: Any) -> List[Any]:
        return coerce_report_findings(value)

    # Truthful Metrics & Status
    confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED
    unresolved_issues: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    # Downstream Hand-off
    next_phase_handoff: Dict[str, Any] = Field(default_factory=dict)

    # Tamper-Evident Content Hash
    content_hash: str = ""

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 hash of the content excluding the hash field."""
        data = self.model_dump(mode="json", exclude={"content_hash"})
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def seal(self) -> "SubPhaseReportContract":
        self.content_hash = self.compute_hash()
        return self


class PhaseReportContract(BaseModel):
    # Phase Identity
    run_id: str
    phase_id: str
    phase_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    duration_ms: int = 0

    # Executive Overview
    summary: str
    subphase_ids: List[str] = Field(default_factory=list)
    subphase_summaries: Dict[str, Any] = Field(default_factory=dict)

    # Consolidated Findings
    reconciled_findings: List[ReportFinding] = Field(default_factory=list)
    critical_blockers: List[str] = Field(default_factory=list)
    unresolved_conflicts: List[str] = Field(default_factory=list)

    @field_validator("reconciled_findings", mode="before")
    @classmethod
    def _coerce_reconciled_findings(cls, value: Any) -> List[Any]:
        return coerce_report_findings(value)

    # Next Phase Input
    passed_to_next_phase: Dict[str, Any] = Field(default_factory=dict)

    # Hashes of all contained sub-phase reports
    subphase_hashes: Dict[str, str] = Field(default_factory=dict)
    content_hash: str = ""

    def compute_hash(self) -> str:
        data = self.model_dump(mode="json", exclude={"content_hash"})
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def seal(self) -> "PhaseReportContract":
        self.content_hash = self.compute_hash()
        return self
