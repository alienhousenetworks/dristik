"""
Persistence Models and DTOs for Durable Audit Checkpointing and Evidence Explorer
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import AnalysisStage, MetricProvenanceState


class StageCheckpoint(BaseModel):
    """Represents an atomic, durable pipeline stage checkpoint."""
    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:10]}")
    analysis_id: str
    stage: AnalysisStage
    step_number: int
    status: str = "COMPLETED"  # RUNNING | COMPLETED | FAILED
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    crawled_count: int = 0
    evidence_count: int = 0
    claims_count: int = 0
    findings_count: int = 0
    accumulated_cost_usd: float = 0.0
    state_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvidenceTraceItem(BaseModel):
    """Deep traceability item connecting Finding -> Claim -> Evidence -> Selector -> Snapshot."""
    finding_id: str
    category: str
    severity: str
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    verification_status: str
    claim_id: Optional[str] = None
    claim_statement: Optional[str] = None
    evidence_id: str
    evidence_class: str
    source_name: str
    url: Optional[str] = None
    selector: Optional[str] = None
    text_extract: Optional[str] = None
    evidence_hash: Optional[str] = None
    raw_snapshot_id: Optional[str] = None
    provenance_state: str
    captured_at: str


class ScoreExplanationDimension(BaseModel):
    """Decomposable score dimension."""
    dimension_key: str
    dimension_label: str
    score_or_band: str
    weight: float
    deduction: float = 0.0
    status_notice: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)


class ScoreExplanation(BaseModel):
    """Explainable scorecard for executive diagnosis."""
    analysis_id: str
    domain: str
    overall_index: float
    score_band: str
    human_score: float
    google_score: float
    ai_readiness_index: float
    ai_visibility_state: str
    dimensions: List[ScoreExplanationDimension] = Field(default_factory=list)
    top_deductions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_count: int = 0
    provenance_summary: Dict[str, int] = Field(default_factory=dict)
