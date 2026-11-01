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
from pydantic import BaseModel, Field


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
