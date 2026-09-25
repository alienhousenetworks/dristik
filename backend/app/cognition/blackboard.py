"""
Dristik AI Typed Cognitive Blackboard
Shared thread-safe working memory for an analysis run, containing EvidenceStore,
EvidenceGraph, ClaimRegistry, and dynamic mission state.
"""
from typing import List, Dict, Any, Optional
from app.evidence.store import EvidenceStore
from app.evidence.graph import EvidenceGraph
from app.cognition.claims import ClaimRegistry
from app.domain.models import (
    BusinessProfile,
    Observation,
    Finding,
    Contradiction,
    ContradictionReport,
    SemanticBusinessRepresentation,
    ThreeWayComparison,
    AiSearchQueryEvaluation,
    OverallScoreResult,
    RoadmapItem,
    CodePatch,
    PageEvidence,
    CrawlManifest,
    TelemetryData,
    PageReport,
)
from app.domain.enums import AnalysisStage

class CognitiveBlackboard:
    def __init__(self, run_id: str, website_url: str):
        self.run_id = run_id
        self.website_url = website_url
        self.stage: AnalysisStage = AnalysisStage.QUEUED
        
        # Memory Subsystems & Relational Graphs
        from app.audit.snapshots import SnapshotStore
        self.snapshot_store = SnapshotStore(run_id)
        self.evidence_store = EvidenceStore(run_id, snapshots=self.snapshot_store)
        self.evidence_graph = EvidenceGraph(run_id)
        self.claim_registry = ClaimRegistry(run_id)
        
        # Working State
        self.pages: List[PageEvidence] = []
        self.page_reports: List[PageReport] = []
        self.crawl_manifest: Optional[CrawlManifest] = None
        self.site_facts: Dict[str, Any] = {}
        self.user_declared_site_type: Optional[str] = None
        self.user_declared_site_type_notes: Optional[str] = None
        self.business_profile: BusinessProfile = BusinessProfile()
        self.semantic_business: Optional[SemanticBusinessRepresentation] = None
        self.identity_contradictions: List[ContradictionReport] = []
        self.observations: List[Observation] = []
        self.contradictions: List[Contradiction] = []
        self.findings: List[Finding] = []
        self.three_way_comparison: Optional[ThreeWayComparison] = None
        self.ai_search_evaluations: List[AiSearchQueryEvaluation] = []
        self.commercial_evaluations: List[Any] = []
        self.competitor_bakeoff: Optional[Any] = None
        self.honest_scores: Optional[Any] = None
        self.geo_readiness: Optional[Any] = None
        self.character_safe_copy: Optional[Any] = None
        self.scores: Optional[OverallScoreResult] = None
        self.roadmap_7_days: List[RoadmapItem] = []
        self.roadmap_30_days: List[RoadmapItem] = []
        self.roadmap_90_days: List[RoadmapItem] = []
        self.code_patches: List[CodePatch] = []
        self.executive_narrative: Dict[str, Any] = {}
        self.blackboard_state: Dict[str, Any] = {}
        self.telemetry = TelemetryData()
        self.execution_trace: List[Dict[str, Any]] = []

    def log_step(self, step_name: str, agent_id: str, details: Dict[str, Any]):
        self.execution_trace.append({
            "step": step_name,
            "agent": agent_id,
            "details": details
        })

    def add_observation(self, observation: Observation):
        self.observations.append(observation)

    def add_finding(self, finding: Finding):
        self.findings.append(finding)

    def add_code_patch(self, patch: CodePatch):
        self.code_patches.append(patch)
