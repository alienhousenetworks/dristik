from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.core.enums import FindingSeverity, FindingCategory, ProvenanceState

class EvidenceRecord(BaseModel):
    id: str
    url: Optional[str] = None
    evidence_type: str
    provenance_state: ProvenanceState = ProvenanceState.RAW_TELEMETRY
    data: Dict[str, Any] = Field(default_factory=dict)
    content_hash: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class FindingContract(BaseModel):
    id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    confidence: float = 1.0
    evidence_ids: List[str] = Field(default_factory=list)

class AgentOutput(BaseModel):
    agent_id: str
    agent_name: str
    status: str = "COMPLETED" # COMPLETED, FAILED, SKIPPED
    execution_time_sec: float = 0.0
    findings: List[FindingContract] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
