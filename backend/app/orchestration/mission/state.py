"""
Dristik AI Primary Mission State
Strongly typed, serializable, and resumable state model for mission orchestration.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.domain.enums import AnalysisStage, Category, Severity, VerificationStatus
from app.domain.models import (
    PageEvidence,
    CrawlManifest,
    Claim,
    Finding,
    CodePatch,
    RoadmapItem,
    OverallScoreResult,
    BusinessProfile,
    TelemetryData,
    UntrustedObservation,
    AiSearchQueryEvaluation
)

class WebsiteTarget(BaseModel):
    url: str
    domain: str
    industry: Optional[str] = None
    country: str = "Global"
    language: str = "en"
    competitors: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None

class MissionObjective(BaseModel):
    audit_type: str = "comprehensive_growth"
    depth: int = 3
    priority_domains: List[str] = Field(default_factory=lambda: [
        "technical", "structured_data", "business", "content", "geo", "ai_search", "experience", "verification"
    ])
    max_pages: int = 25
    budget_usd: float = 0.50
    deadline_seconds: int = 300

class BudgetState(BaseModel):
    max_budget_usd: float = 0.50
    spent_usd: float = 0.0
    tokens_consumed: int = 0
    inference_calls: int = 0
    policy: str = "BALANCED"  # ECONOMY, BALANCED, DEEP, ENTERPRISE

class ConfidenceState(BaseModel):
    overall_confidence: float = 0.0
    evidence_coverage: float = 0.0
    status: str = "UNCERTAIN"  # VERIFIED, STRONGLY_SUPPORTED, PROBABLE, UNCERTAIN, UNSUPPORTED, CONTRADICTED

class Task(BaseModel):
    task_id: str
    name: str
    capability_id: str
    assigned_worker: str
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    output_summary: Optional[str] = None

class CapabilityExecution(BaseModel):
    capability_id: str
    execution_type: str  # deterministic, slm, reasoning, high_reasoning
    status: str = "pending"
    duration_ms: float = 0.0
    claims_produced: int = 0

class Hypothesis(BaseModel):
    id: str
    statement: str
    domain: str
    prior_probability: float = 0.50
    supporting_evidence_refs: List[str] = Field(default_factory=list)
    contradicting_evidence_refs: List[str] = Field(default_factory=list)
    posterior_confidence: float = 0.50
    status: str = "untested"  # untested, validated, falsified

class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    domain: str
    opportunity_score: Optional[float] = None
    strategic_value: str = "High"
    effort_level: str = "Medium"
    expected_impact: str = "Accelerated AI search citation & enterprise buyer clarity"
    action_plan: str = ""

class SimulationScenario(BaseModel):
    id: str
    name: str  # Conservative, Balanced, Aggressive
    projected_score: float
    confidence_interval: str  # e.g., "78% - 84%"
    expected_gains: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    timeframe_days: int = 30

class MissionState(BaseModel):
    mission_id: str
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    target: WebsiteTarget
    objective: MissionObjective

    # Discovery & Evidence
    crawl_snapshot: Optional[CrawlManifest] = None
    pages: List[PageEvidence] = Field(default_factory=list)
    untrusted_observations: List[UntrustedObservation] = Field(default_factory=list)

    # Cognition & Reasoning
    business_profile: BusinessProfile = Field(default_factory=BusinessProfile)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    root_cause_bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)

    # Capabilities & Workers
    capabilities: List[CapabilityExecution] = Field(default_factory=list)
    active_tasks: List[Task] = Field(default_factory=list)

    # Opportunities & Strategy
    opportunities: List[Opportunity] = Field(default_factory=list)
    simulations: List[SimulationScenario] = Field(default_factory=list)
    ai_search_evaluations: List[AiSearchQueryEvaluation] = Field(default_factory=list)

    # Action & Remediation
    scores: Optional[OverallScoreResult] = None
    code_patches: List[CodePatch] = Field(default_factory=list)
    roadmap_7_days: List[RoadmapItem] = Field(default_factory=list)
    roadmap_30_days: List[RoadmapItem] = Field(default_factory=list)
    roadmap_90_days: List[RoadmapItem] = Field(default_factory=list)
    executive_narrative: Dict[str, Any] = Field(default_factory=dict)

    # Confidence & Budget
    confidence: ConfidenceState = Field(default_factory=ConfidenceState)
    budget: BudgetState = Field(default_factory=BudgetState)
    telemetry: TelemetryData = Field(default_factory=TelemetryData)

    # Control Flow
    status: AnalysisStage = AnalysisStage.QUEUED
    current_node: str = "START"
    reflection_cycle: int = 0
    max_reflection_cycles: int = 2
    waiting_for_approval: bool = False
    approval_gate: Optional[str] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = Field(default_factory=list)
