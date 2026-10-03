"""
Dristik AI Domain Models & Pydantic Schemas
Strict typed models for Evidence, Claims, Findings, Scores, Reports, and Telemetry.
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from app.domain.enums import (
    Severity,
    Category,
    VerificationStatus,
    BusinessIntent,
    EvidenceConfidence,
    AnalysisStage,
    ClaimType,
    ReleaseStatus,
    UserRole,
    DataResidency,
    PatchRiskLevel,
    PatchOperation,
    PatchApprovalStatus,
    ConnectorType,
    ConnectorHealthStatus,
    EvidenceState,
    EvidenceLevel,
    ClaimState,
    ObservationType,
    SourceIntegrityLabel,
    GroundTruthRelation,
    ClaimFamily,
    ConfidenceBand,
    RubricConfidence,
    Materiality,
    EvidenceClass,
    EvidenceSubtype,
    FindingLifecycle,
    AiVisibilityStatus,
    GeoDimensionKey,
    QueryClass,
    FindingClassification,
    ImpactLevel,
    ClaimSourceType,
)
from app.evidence.models import EvidenceRef

class FindingEvidence(BaseModel):
    evidence_id: Optional[str] = None
    url: Optional[str] = None
    element: str = "dom"
    value: str = ""
    selector: Optional[str] = None
    line_number: Optional[int] = None
    snippet: Optional[str] = None
    source: Optional[str] = "crawl"
    excerpt: Optional[str] = None
    type: str = "content"
    state: EvidenceState = EvidenceState.OBSERVED
    evidence_class: EvidenceClass = EvidenceClass.OBSERVED
    evidence_subtype: Optional[str] = "DOM"
    evidence_ref: Optional[EvidenceRef] = None

    @field_validator("excerpt", "value", "snippet", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, list):
            return " · ".join(str(x) for x in v if x is not None)
        return str(v)

class CodePatch(BaseModel):
    patch_id: str
    title: str
    category: Category
    target_file: str  # e.g., "index.html", "schema.json", "robots.txt"
    before_snippet: Optional[str] = None
    after_snippet: str
    explanation: str
    release_status: ReleaseStatus = ReleaseStatus.PENDING_APPROVAL
    approver: Optional[str] = None
    approved_at: Optional[str] = None

class RemediationPatch(BaseModel):
    patch_id: str
    finding_id: str
    title: str
    category: Category
    risk_level: PatchRiskLevel = PatchRiskLevel.SAFE_AUTO
    target_url: str = "/"
    target_file: str = "index.html"
    operation: PatchOperation = PatchOperation.REPLACE
    before_snippet: Optional[str] = None
    after_snippet: str
    explanation: str
    confidence: float = 0.95
    approval_status: PatchApprovalStatus = PatchApprovalStatus.PENDING
    approver: Optional[str] = None
    approved_at: Optional[str] = None
    applied_via: Optional[str] = None       # e.g., "wordpress", "github", "manual"
    applied_at: Optional[str] = None
    pr_url: Optional[str] = None            # for GitHub PRs
    pr_number: Optional[int] = None
    verification_status: VerificationStatus = VerificationStatus.PROVISIONAL
    verification_notes: Optional[str] = None
    citation_score_delta: Optional[int] = None
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)
    is_blocked: bool = False
    blocked_reason: Optional[str] = None
    required_evidence: Optional[str] = None

class Integration(BaseModel):
    integration_id: str
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    provider: ConnectorType = ConnectorType.GENERIC
    name: str
    target_url: str
    status: ConnectorHealthStatus = ConnectorHealthStatus.CONNECTED
    scopes: List[str] = Field(default_factory=list)
    repository: Optional[str] = None       # e.g. "acme/website" for GitHub
    branch: Optional[str] = "main"
    created_at: str
    last_synced_at: Optional[str] = None
    error_message: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

class RoiInput(BaseModel):
    avg_deal_size_inr: Optional[float] = None
    monthly_visitors: Optional[int] = None
    current_conversion_rate: Optional[float] = None
    expected_traffic_lift_pct: Optional[float] = None
    expected_cro_lift_pct: Optional[float] = None

class RoiEstimate(BaseModel):
    is_available: bool = True
    status: str = "AVAILABLE"
    message: Optional[str] = None
    monthly_visitors: Optional[int] = None
    avg_deal_size_inr: Optional[float] = None
    current_monthly_leads: Optional[int] = None
    current_annual_revenue_inr: Optional[float] = None
    projected_annual_revenue_inr: Optional[float] = None
    annual_upside_inr: Optional[float] = None
    roi_multiple: Optional[float] = None
    high_impact_opportunities: List[str] = Field(default_factory=list)
    methodology: str = "Dristik AI Intent & Value-Lift Attribution Matrix"
    missing_inputs: List[str] = Field(default_factory=list)

class VerificationResult(BaseModel):
    patch_id: str
    target_url: str
    is_resolved: bool = False
    verified_at: str
    details: str
    status: str = "PENDING_VERIFICATION"
    before_score: Optional[int] = None
    after_score: Optional[int] = None
    score_delta: Optional[int] = None

class VerificationCheckItem(BaseModel):
    name: str
    passed: bool
    detail: str

class RemediationVerificationReport(BaseModel):
    verification_id: str
    finding_id: str
    analysis_id: Optional[str] = None
    target_url: str
    stage: str = "PENDING"  # "PENDING" -> "RECRAWL" -> "RECHECK" -> "COMPARE" -> "CERTIFIED"
    status: str = "PENDING"  # "RESOLVED", "PARTIALLY_RESOLVED", "FAILED_RECHECK", "FAILED_RECRAWL", "INCONCLUSIVE", "PENDING"
    before_state: str
    after_state: str
    checks: List[VerificationCheckItem] = Field(default_factory=list)
    passed_checks_count: int = 0
    total_checks_count: int = 0
    score_delta: Optional[float] = None
    verified_at: str
    evidence_seal: str
    certified_by: str = "Dristik Continuous Assurance Engine v4"
    recrawl_status_code: Optional[int] = None
    recrawl_ttfb_ms: Optional[float] = None
    recrawl_content_type: Optional[str] = None

class CroEvidenceDissection(BaseModel):
    observed_facts: List[str] = Field(default_factory=list) # e.g. ["No pricing information found.", "CTA text = 'REQUEST CUSTOM BUILD'"]
    inferred_impact: str = "" # e.g. "This may increase qualification friction for self-serve visitors."
    requires_analytics: Dict[str, str] = Field(default_factory=lambda: {
        "actual_abandonment_rate": "UNKNOWN (Requires GA4 connector)",
        "cta_conversion_rate": "UNKNOWN (Requires GA4 events / PostHog)",
        "form_completion_rate": "UNKNOWN (Requires CRM / Analytics connector)",
    })
    analytics_connected: bool = False
    grounded_metrics: Optional[Dict[str, Any]] = None # If connected, holds measured numbers


class OutcomeImpact(BaseModel):
    outcome: str
    level: ImpactLevel = ImpactLevel.MEDIUM


class FindingCalibratedImpact(BaseModel):
    """Technical severity, business impact, confidence, and blocking are independent."""
    technical_severity: Severity = Severity.MEDIUM
    business_impact: ImpactLevel = ImpactLevel.MEDIUM
    business_impact_label: str = "Medium"
    confidence: float = 0.85
    confidence_band: ConfidenceBand = ConfidenceBand.MEDIUM
    is_blocking: bool = False
    blocks: List[str] = Field(default_factory=list)
    blocking_reason: Optional[str] = None
    affected_outcomes: List[OutcomeImpact] = Field(default_factory=list)


class SubObservation(BaseModel):
    observation_id: str
    title: str
    description: Optional[str] = None
    selector: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None
    severity: Optional[Severity] = None
    category: Optional[Category] = None
    evidence_refs: List[str] = Field(default_factory=list)


class GroundedRecommendation(BaseModel):
    """
    Layer 4 — Grounded Recommendation.
    Prescriptive action synthesized by LLM/reasoner, strictly anchored to underlying finding and evidence.
    Cannot manufacture underlying website facts.
    """
    recommendation_id: str
    underlying_finding_id: str
    underlying_evidence_ids: List[str] = Field(default_factory=list)
    what_to_change: str = Field(..., description="Actionable change instruction")
    why: str = Field(..., description="Causal reason and impact explanation")
    how_to_change: str = Field(..., description="Concrete implementation guidance")
    example: Optional[str] = Field(default=None, description="Concrete code snippet or content example")
    target_file: Optional[str] = None


class DerivedMetric(BaseModel):
    """
    Layer 3 — Derived Intelligence Metric.
    Every derived metric must carry: formula, input evidence, algorithm version, and timestamp.
    """
    metric_id: str
    name: str = Field(..., description="e.g. topic_coverage, entity_consistency, intent_coverage, information_gain, citation_readiness")
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized score 0-100")
    formula: str = Field(..., description="Explicit mathematical or deterministic formula expression")
    input_evidence_ids: List[str] = Field(default_factory=list, description="IDs of backing Layer 1 machine observations")
    algorithm_version: str = Field(default="dristik_v2.1", description="Version of derivation algorithm")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)


class ClaimLedgerEntry(BaseModel):
    """
    Phase 2 — Claim Ledger Record.
    Every factual statement in the report is indexed with provenance and confidence.
    """
    claim_id: str
    claim: str
    source_type: ClaimSourceType = ClaimSourceType.OBSERVED
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    scope: str = "site_wide"
    created_by: str = "system"
    timestamp: str = ""
    is_valid_fact: bool = True
    rejection_reason: Optional[str] = None


class ClaimLedger(BaseModel):
    """
    Phase 2 — System-wide Claim Ledger for Certified Zero-Fake integrity.
    """
    ledger_id: str
    run_id: str
    entries: List[ClaimLedgerEntry] = Field(default_factory=list)
    certified_zero_fake: bool = True
    rejected_unsupported_count: int = 0


class Finding(BaseModel):
    finding_id: str
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    mission_id: Optional[str] = None
    category: Category
    severity: Severity
    classification: FindingClassification = FindingClassification.VERIFIED_DEFECT
    calibrated_impact: Optional[FindingCalibratedImpact] = None
    root_cause_id: Optional[str] = None
    sub_observations: List[str] = Field(default_factory=list)
    detailed_observations: List[SubObservation] = Field(default_factory=list)
    title: str
    description: str
    evidence: List[FindingEvidence] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_ref_objects: List[EvidenceRef] = Field(default_factory=list)
    rule_id: Optional[str] = None
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    confidence_label: EvidenceConfidence = EvidenceConfidence.STRONG
    impact: int = Field(default=5, ge=1, le=10)
    effort: int = Field(default=5, ge=1, le=10)
    priority: int = Field(default=5, ge=1, le=10)
    recommendation: str
    grounded_recommendation: Optional[GroundedRecommendation] = None
    reasoning: Optional[str] = None
    business_impact: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    verification_notes: Optional[str] = None
    release_status: ReleaseStatus = ReleaseStatus.PENDING_APPROVAL
    approver: Optional[str] = None
    policy_pack: str = "enterprise_web_intel_v4"
    code_patch: Optional[CodePatch] = None
    provenance_hash: Optional[str] = None
    source_integrity_label: SourceIntegrityLabel = SourceIntegrityLabel.NOT_APPLICABLE
    claim_family: Optional[ClaimFamily] = None
    routed_to: Optional[str] = None
    finding: str = ""
    confidence_rubric: RubricConfidence = RubricConfidence.LIKELY
    confidence_basis: str = ""
    materiality: Materiality = Materiality.MINOR
    source_agreement: int = 0
    adversarial_reviewed: bool = False
    held_from_executive: bool = False
    claim_refs: List[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = Field(
        default=None,
        description="Plain-language explanation of the commercial / UX / SEO consequence of this finding for a non-technical stakeholder."
    )
    validation_criteria: Optional[str] = Field(
        default=None,
        description="Concrete, checkable acceptance condition that must be true after remediation is applied. Written as a present-tense assertion."
    )
    remediation_verification: Optional[RemediationVerificationReport] = None
    resolution_status: str = "OPEN"  # "OPEN", "RESOLVED", "VERIFYING", "REGRESSED"
    evidence_class: EvidenceClass = EvidenceClass.OBSERVED
    evidence_subtype: Optional[str] = "DOM"
    epistemic_level: Optional[str] = None
    evidence_scope: Optional[str] = None
    scope_hit_count: Optional[int] = None
    scope_sample_size: Optional[int] = None
    cro_dissection: Optional[CroEvidenceDissection] = None
    surfaces_affected: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Consolidated surfaces affected by this root-cause defect (e.g. [{'surface': 'H1 Heading', 'url': '/', 'selector': 'h1'}])"
    )
    # v2: Lifecycle and display fields
    lifecycle_state: FindingLifecycle = Field(
        default=FindingLifecycle.OPEN,
        description="Current lifecycle stage of this finding in the canonical registry."
    )
    confidence_display_label: Optional[str] = Field(
        default=None,
        description="Customer-facing confidence label. Never exposes 'GUESSING'. "
                    "Auto-derived from confidence_rubric.customer_label if not set explicitly."
    )

    def get_confidence_display(self) -> str:
        """Return the customer-facing confidence label, never GUESSING."""
        if self.confidence_display_label:
            return self.confidence_display_label
        rubric = self.confidence_rubric
        if hasattr(rubric, "customer_label"):
            return rubric.customer_label
        return str(rubric.value) if rubric else "Unknown"

    @property
    def id(self) -> str:
        return self.finding_id

    @model_validator(mode="after")
    def sync_evidence_ids_and_refs(self) -> "Finding":
        if self.evidence_ids and not self.evidence_refs:
            self.evidence_refs = list(self.evidence_ids)
        elif self.evidence_refs and not self.evidence_ids:
            self.evidence_ids = list(self.evidence_refs)
        return self

    def to_layer2_json(self) -> dict[str, Any]:
        """Layer 2 canonical JSON schema: finding_id, rule_id, evidence_ids, confidence."""
        conf_str = "certain" if self.confidence >= 0.99 or str(self.confidence_rubric).upper() in ["VERIFIED", "CERTAIN", "RUBRICCONFIDENCE.VERIFIED"] else "high"
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id or "RULE_CUSTOM_001",
            "evidence_ids": list(self.evidence_ids or self.evidence_refs or []),
            "confidence": conf_str,
        }

    def emission_contract(self) -> dict:
        """Exact agent-emission schema required of every finding."""
        return {
            "finding": self.finding or self.title,
            "evidence": list(self.evidence_refs or []),
            "confidence": self.confidence_rubric.value if hasattr(self.confidence_rubric, "value") else str(self.confidence_rubric),
            "confidence_basis": self.confidence_basis,
            "materiality": self.materiality.value if hasattr(self.materiality, "value") else str(self.materiality),
            "source_agreement": int(self.source_agreement or 0),
        }

class Claim(BaseModel):
    id: str
    agent_id: str
    statement: str
    claim_type: ClaimType = ClaimType.FACT
    category: Category
    severity: Severity = Severity.MEDIUM
    evidence_refs: List[str] = Field(default_factory=list)
    evidence_ref_objects: List[EvidenceRef] = Field(default_factory=list)
    supporting_agents: List[str] = Field(default_factory=list)
    contradicting_agents: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.PROVISIONAL
    claim_state: ClaimState = ClaimState.CREATED
    evidence_level: EvidenceLevel = EvidenceLevel.E3_DETERMINISTIC
    observation_type: ObservationType = ObservationType.OBSERVED
    provenance_hash: Optional[str] = None
    verification_notes: Optional[str] = None
    recommendation: Optional[str] = None
    impact: int = 5
    effort: int = 5
    source_integrity_label: SourceIntegrityLabel = SourceIntegrityLabel.NOT_APPLICABLE
    ground_truth_relation: GroundTruthRelation = GroundTruthRelation.NOT_APPLICABLE
    claim_family: Optional[ClaimFamily] = None
    confidence_band: Optional[ConfidenceBand] = None
    routed_to: Optional[str] = None
    confidence_rubric: Optional[RubricConfidence] = None
    confidence_basis: Optional[str] = None
    materiality: Optional[Materiality] = None
    source_agreement: int = 0
    adversarial_reviewed: bool = False
    held_from_executive: bool = False

class Observation(BaseModel):
    id: str
    agent_id: str
    category: Category
    key: str
    value: Any
    evidence_refs: List[str] = Field(default_factory=list)
    severity: Severity = Severity.INFO

class Contradiction(BaseModel):
    id: str
    claim_a_id: str
    claim_b_id: str
    description: str
    resolution: str
    winner_claim_id: Optional[str] = None
    routed_to: Optional[str] = None

class ContradictionReport(BaseModel):
    id: str
    contradiction_type: str = "identity_conflict" # "user_vs_evidence", "inter_agent_conflict", "navigation_vs_content"
    declared_type: Optional[str] = None
    detected_type: Optional[str] = None
    confidence: float = 0.85
    reason: str
    evidence: List[FindingEvidence] = Field(default_factory=list)

class SemanticBusinessRepresentation(BaseModel):
    industry: str = "Unknown"
    sub_industry: Optional[str] = None
    business_model: str = "Unknown"
    secondary_business_models: List[str] = Field(default_factory=list)
    website_type: str = "Unknown"
    primary_intent: str = "Unknown"
    secondary_intents: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    geography: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    product_categories: List[str] = Field(default_factory=list)
    service_categories: List[str] = Field(default_factory=list)
    journey_stages: List[str] = Field(default_factory=list)
    conversion_events: List[str] = Field(default_factory=list)
    friction_points: List[str] = Field(default_factory=list)
    confidence: float = 0.80
    evidence: List[FindingEvidence] = Field(default_factory=list)
    consensus_summary: Optional[str] = None
    is_disputed: bool = False
    contradiction: Optional[ContradictionReport] = None
    source_provenance: Dict[str, str] = Field(default_factory=dict)
    llm_status: str = "ok"  # ok | failed
    llm_failure_reason: Optional[str] = None

class ResolvedEntity(BaseModel):
    name: str = Field(..., description="Canonical entity/brand name (never 'Unknown Business')")
    legal_name: Optional[str] = Field(None, description="Registered corporate/legal entity name")
    domain: str = Field(..., description="Canonical website domain")
    clean_host: Optional[str] = Field(None, description="Normalized hostname")
    description: Optional[str] = Field(None, description="One-sentence entity identity & core offering")
    logo: Optional[str] = Field(None, description="URL or asset path to the official entity logo")
    category: Optional[str] = Field(None, description="Industry sector or business category")
    location: Optional[str] = Field(None, description="Headquarters geography or service area")
    same_as: List[str] = Field(default_factory=list, description="Authoritative external entity URLs (Wikidata, Wikipedia, LinkedIn, etc.)")
    confidence: float = Field(0.85, ge=0.0, le=1.0)
    extraction_source: str = "DOMAIN_HEURISTIC"  # "ORGANIZATION_SCHEMA" | "OG_SITE_NAME" | "DOM_BRANDING" | "PAGE_TITLE" | "DOMAIN_TOKEN"
    niche: Optional[str] = None
    value_proposition: Optional[str] = None


class BusinessProfile(BaseModel):
    business_name: str = ""
    industry: Optional[str] = None
    niche: Optional[str] = None
    sub_niche: Optional[str] = None
    products: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    geography: Optional[str] = None
    business_model: Optional[str] = None
    value_proposition: Optional[str] = None
    primary_cta: Optional[str] = None
    secondary_cta: Optional[str] = None
    primary_intent: Optional[BusinessIntent] = None
    secondary_intents: List[BusinessIntent] = Field(default_factory=list)
    confidence: Optional[float] = None
    economic_buyer_title: Optional[str] = None
    target_org_scale: Optional[str] = None
    defensible_moat_type: Optional[str] = None
    five_second_clarity_score: Optional[int] = None
    cac_impact_risk: Optional[str] = None
    copy_rewrite: Optional[Dict[str, str]] = None
    evidence_status: str = "insufficient_evidence"

class ThreeWayComparison(BaseModel):
    human_visitor_perspective: str
    search_engine_perspective: str
    ai_answer_engine_perspective: str

class AiSearchQueryEvaluation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    query: str
    question_type: str # e.g. "Identity", "Offering", "Target Audience", "Differentiation", "Pricing"
    evidence_quality: str # "Excellent", "Good", "Moderate", "Weak", "Missing"
    score: Optional[int] = None # 1 - 10
    detected_answer: str
    evidence_snippet: Optional[str] = None
    gap_analysis: Optional[str] = None
    citation_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hallucination_vulnerability_risk: Optional[str] = None
    recommended_remediation: Optional[str] = None
    after_score: Optional[int] = None # 1 - 10 post-patch
    after_answer: Optional[str] = None # post-patch grounded answer
    delta: Optional[int] = None # after_score - before_score
    before_evidence_status: Optional[str] = None # "VERIFIED" | "AMBIGUOUS" | "MISSING"
    is_simulated: bool = True
    provenance_mode: str = "simulation"
    provenance_label: str = "MODEL_PREDICTED" # "MODEL_PREDICTED" | "LIVE_QUERIED"
    model_version: Optional[str] = "gemini-2.0-flash"
    queried_at: Optional[str] = None

class CommercialQueryEvaluation(BaseModel):
    question_key: str # "identity" | "icp" | "pricing" | "alternatives" | "trust" | "roi"
    question_title: str
    buyer_query: str
    before_score: int # 1 - 10
    before_answer: str
    before_evidence_status: str # "VERIFIED" | "AMBIGUOUS" | "MISSING"
    after_score: Optional[int] = None # 1 - 10 post-patch
    after_answer: Optional[str] = None # post-patch grounded answer
    delta: Optional[int] = None # after_score - before_score
    patch_citation_gain: Optional[float] = None
    evidence_snippet: Optional[str] = None
    gap_analysis: Optional[str] = None


class DynamicSandboxQuestionEvaluation(BaseModel):
    question_id: str                    # e.g. "Q-001" to "Q-100"
    facet: str                          # e.g. "Pricing, Packaging & Commercial Model"
    generated_question: str             # bespoke AI-generated inquiry from crawled business context
    buyer_intent: str                   # rationale why buyers or AI engines ask this
    is_answerable: bool                 # whether crawled pages supply enough evidence
    answerability_status: str = "ANSWERABLE"  # ANSWERABLE | PARTIAL | UNANSWERABLE | CONFLICTING
    crawled_answer: str                 # synthesized answer from KIE retrieval
    evidence_url: Optional[str] = None
    evidence_snippet: Optional[str] = None
    gap_analysis: Optional[str] = None  # KIE-generated gap explanation with answer risk label
    recommended_answer: Optional[str] = None  # authoritative post-remediation answer
    citability_score: int = 5           # 1–10 (= grounding_ratio × 10, floor 2)
    projected_patch_gain: float = 0.30  # expected citation coverage gain post-remediation
    # KIE Phase 6 fields
    grounding_ratio: Optional[float] = None          # 0.0–1.0 from GroundedAnswerSimulator
    answer_risk: Optional[str] = None                # HIGH | MEDIUM | LOW
    claim_decomposition: Optional[List[Dict[str, Any]]] = None  # per-claim verification
    retrieval_evidence_count: Optional[int] = None   # how many evidence chunks were retrieved


class CompetitorBakeoffItem(BaseModel):
    question_key: str
    question_title: str
    target_answer: str
    target_score: Optional[int] = None
    target_status: str # "Answerable" | "Ambiguous" | "Blind"
    competitor_answer: str
    competitor_score: Optional[int] = None
    competitor_status: str # "Answerable" | "Ambiguous" | "Blind"
    winner: str # "target" | "competitor" | "tie" | "unmeasured"
    commercial_takeaway: str
    reason_competitor_won: Optional[str] = None
    answerability_gap: Optional[str] = None

class CompetitorBakeoffResult(BaseModel):
    competitor_domain: str
    status: str = "AVAILABLE"
    message: Optional[str] = None
    evaluations: List[CompetitorBakeoffItem] = Field(default_factory=list)
    target_wins: int = 0
    competitor_wins: int = 0
    ties: int = 0
    executive_takeaway: str = ""

class EvidenceItem(BaseModel):
    url: Optional[str] = None
    selector: Optional[str] = None
    text: str
    evidence_type: str = "body_text"  # service_specification, heading, schema_declaration, case_study, pricing_table
    location_weight: float = 1.0       # main/article/heading: 0.9-1.0; nav/footer: 0.05-0.1
    strength: float = 1.0              # 0.0-1.0 quality of match


class CanonicalEntityFact(BaseModel):
    entity_type: str                  # Company, Service, Product, Pricing, Security, Leadership
    attribute: str
    value: str
    source_type: str = "DOM"          # DOM, SCHEMA, EXTERNAL
    source_url: Optional[str] = None
    verified: bool = True
    contradictions: List[str] = Field(default_factory=list)


class AiClaimRecord(BaseModel):
    prompt_id: str
    engine: str
    raw_claim: str
    claim_status: str = "UNVERIFIED"  # VERIFIED | UNVERIFIED | CONTRADICTION
    evidence_match: Optional[str] = None


class BenchmarkPromptDefinition(BaseModel):
    prompt_id: str
    tier: str = "CANONICAL"           # CANONICAL | ADAPTIVE
    funnel_stage: str = "decision"     # awareness | consideration | decision
    intent: str
    template: str


class GeoQuestionEvidence(BaseModel):
    question_key: str
    question: str
    category: str = "General"
    status: str
    answer: Optional[str] = None
    answer_snippet: Optional[str] = None
    evidence_url: Optional[str] = None
    evidence_snippet: Optional[str] = None
    why: str = ""
    recommended_answer: Optional[str] = None
    confidence: float = 0.8
    evidence_set: List[EvidenceItem] = Field(default_factory=list)
    remediation_type: Optional[str] = None  # ANSWER_BLOCK | INTERNAL_LINK | CONTENT_REQUIRED | NO_REMEDIATION_NEEDED


class GeoDimension(BaseModel):
    key: str
    label: str
    band: str
    summary: str
    evidence_notes: List[str] = Field(default_factory=list)


class GeoDimensionScore(BaseModel):
    """Score for a single GEO dimension with provenance."""
    key: str = Field(..., description="GeoDimensionKey enum value")
    label: str
    score: float = Field(..., ge=0.0, le=100.0, description="0-100 dimension score")
    band: str = Field(..., description="'high' | 'medium' | 'low'")
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    provenances: List[str] = Field(default_factory=list, description="Evidence IDs backing this score")
    summary: str = ""
    evidence_notes: List[str] = Field(default_factory=list)
    is_measured: bool = Field(
        default=False,
        description="True only when this dimension was directly measured (not inferred from HTML)."
    )
    measurement_note: Optional[str] = Field(
        default=None,
        description="If is_measured=False, explains what would be needed to measure this directly."
    )


class GeoReadinessReport(BaseModel):
    layer: str = "readiness"
    visibility_status: str = "NOT_CONFIGURED"
    visibility_message: str = ""
    entity_name: str = "Unknown"
    questions_total: int = 0
    questions_supported: int = 0
    questions_partial: int = 0
    questions_unsupported: int = 0
    questions_conflicting: int = 0
    headline: str = ""
    questions: List[GeoQuestionEvidence] = Field(default_factory=list)
    dimensions: List[GeoDimension] = Field(default_factory=list)
    # v2: Multi-dimensional scored breakdown keyed by GeoDimensionKey value
    dimension_scores: Dict[str, GeoDimensionScore] = Field(
        default_factory=dict,
        description="Scored GEO dimensions keyed by GeoDimensionKey enum values. "
                    "Populated by the multi-dimensional evaluator."
    )
    schema_types: List[str] = Field(default_factory=list)
    schema_is_evidence_layer_only: bool = True
    market_country: str = "Global"
    market_language: str = "en"
    market_note: str = "Country and language are the audit request context. They are not a live geo-rank."
    interpretation_disclaimer: str = Field(
        default=(
            "GEO Readiness measures whether AI engines can extract answers from this website. "
            "It is NOT a live citation rank. Live AI citation visibility requires a separate "
            "connector with actual engine queries and can only be reported as MEASURED when "
            "directly observed."
        ),
        description="Mandatory disclaimer surfaced on every GEO report."
    )
    # Layer 1 High-Density AI Extractability
    extractability_score: Optional[float] = None
    entity_consistency: Optional[Dict[str, Any]] = None
    claims_analysis: Optional[Dict[str, Any]] = None
    question_graph_50: Optional[Dict[str, Any]] = None
    citation_passages: Optional[Dict[str, Any]] = None
    schema_crosscheck: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# AI Visibility Record — strictly separates MEASURED from SIMULATION
# ---------------------------------------------------------------------------
class AiEngineQueryResult(BaseModel):
    """Result of a single live AI engine query."""
    engine: str = Field(..., description="Engine name: 'chatgpt', 'perplexity', 'gemini', 'claude'")
    query: str
    query_class: Optional[str] = Field(default=None, description="QueryClass enum value")
    cited: bool = Field(..., description="True if the target domain appeared in the response")
    citation_rank: Optional[int] = Field(default=None, description="1-indexed position in citations, if cited")
    response_snippet: Optional[str] = None
    queried_at: Optional[str] = None
    evidence_id: Optional[str] = Field(default=None, description="ID in the EvidenceStore for this query result")


class AiEngineSimulationResult(BaseModel):
    """Model-inferred simulation — NOT a live engine result."""
    engine: str
    query: str
    query_class: Optional[str] = None
    inferred_citability: str = Field(
        ..., description="'LIKELY_CITED' | 'UNLIKELY_CITED' | 'UNCERTAIN'"
    )
    basis: str = Field(
        ..., description="What on-page signals the model used to infer citability."
    )
    simulation_disclaimer: str = Field(
        default=(
            "This is a model inference based on on-page signals only. "
            "It is NOT a live query result. Actual citation status may differ."
        )
    )


class AiVisibilityRecord(BaseModel):
    """
    Canonical AI Search visibility record.
    Strictly separates MEASURED results from SIMULATION_ONLY inferences.
    The executive report must surface this distinction to the end user.
    """
    status: AiVisibilityStatus = AiVisibilityStatus.NOT_MEASURED
    # MEASURED results (only present when live engine was actually queried)
    measured_results: List[AiEngineQueryResult] = Field(default_factory=list)
    # SIMULATION results (model-inferred, clearly labelled)
    simulation_results: List[AiEngineSimulationResult] = Field(default_factory=list)
    # Aggregate measured metrics (only valid when status == MEASURED)
    measured_citation_rate: Optional[float] = Field(
        default=None,
        description="Fraction of live queries where the domain was cited. "
                    "None when not measured."
    )
    engines_queried: List[str] = Field(default_factory=list)
    queries_run: int = 0
    not_measured_reason: Optional[str] = Field(
        default=None,
        description="Populated when status is NOT_MEASURED or SIMULATION_ONLY to "
                    "explain why direct measurement was not performed."
    )
    measurement_disclaimer: str = Field(
        default=(
            "AI Visibility data is only reported as MEASURED when a live engine "
            "connector performed actual queries. Simulation results are model "
            "inferences and must not be presented as measured visibility."
        )
    )


class AiVisibilityScorecard(BaseModel):
    """Live multi-engine rates. None means that rate was not measured."""
    status: str = "NOT_MEASURED"
    measurement_note: str = (
        "Rates use successful API or SERP responses only. "
        "An API answer can differ from the consumer chat UI. "
        "A timeout is an error, not a failure to mention the brand."
    )
    engines_measured: int = 0
    engines_requested: int = 0
    queries: int = 0
    repeats: int = 1
    successful_runs: int = 0
    failed_runs: int = 0
    mention_rate_pct: Optional[float] = None
    citation_rate_pct: Optional[float] = None
    citation_accuracy_pct: Optional[float] = None
    entity_accuracy_pct: Optional[float] = None
    service_recognition_pct: Optional[float] = None
    icp_recognition_pct: Optional[float] = None
    pricing_recognition_pct: Optional[float] = None
    competitor_visibility_pct: Optional[float] = None
    hallucination_rate_pct: Optional[float] = None
    source_consistency_pct: Optional[float] = None
    not_measured_reason: Optional[str] = None
    matrix_grounding: Optional[str] = None
    observatory_records: List[Dict[str, Any]] = Field(default_factory=list)
    observatory_summary: Optional[Dict[str, Any]] = None


class HonestScores(BaseModel):
    human_score: Optional[float] = None # 0 - 100
    google_score: Optional[float] = None # 0 - 100
    ai_readiness_score: Optional[float] = None # 0 - 100 (On-page structural extractability, entity, schema)
    ai_visibility_score: Optional[float] = None # 0 - 100 (Strictly empirical live engine citation measurement)
    ai_visibility_status: str = "NOT_MEASURED" # MEASURED | NOT_MEASURED | NOT_CONFIGURED
    ai_citation_score: Optional[float] = None # Deprecated alias for ai_readiness_score (retained for frontend compatibility)
    on_page_proxy_score: Optional[float] = None # 0 - 100
    live_ai_citation_score: Optional[float] = None # 0 - 100 (from live engine tracker only)
    overall_score: Optional[float] = None # composite 0 - 100
    score_band: str = "Pending Evaluation"
    human_summary: str = ""
    google_summary: str = ""
    ai_citation_summary: str = ""
    evidence_refs: List[str] = Field(default_factory=list)
    status: str = "AVAILABLE"
    ai_citation_status: str = "on_page_readiness" # "on_page_readiness" | "measured" | "not_measured"

class AgentReadinessSignal(BaseModel):
    key: str
    status: str  # PRESENT | MISSING | NOT_MEASURED
    summary: str = ""

class AgentReadinessReport(BaseModel):
    """On-site readiness for AI agents. Not a live citation rank."""
    score: Optional[float] = None
    signals: List[AgentReadinessSignal] = Field(default_factory=list)
    summary: str = ""

class CharacterSafeCopy(BaseModel):
    title: str = ""
    title_char_count: int = 0
    title_status: str = "compliant" # "compliant" (50-60) | "too_short" (<50) | "too_long" (>60)
    meta_description: str = ""
    meta_char_count: int = 0
    meta_status: str = "compliant" # "compliant" (140-160) | "too_short" (<140) | "too_long" (>160)
    hero_headline: str = ""
    hero_subhead: str = ""
    hero_word_count: int = 0
    hero_status: str = "compliant" # "compliant" (40-60 words) | "under_length" (<40) | "over_length" (>60)
    primary_cta: str = ""


class CheckEvidenceItem(BaseModel):
    url: Optional[str] = None
    snippet: Optional[str] = None
    status: str = "PASS"  # PASS | FAIL | WARNING
    detail: Optional[str] = None


class LLMJudgeRecord(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    rubric_id: str
    model: str = "gemini-2.5-flash"
    model_version: Optional[str] = None
    temperature: float = 0.0
    input_evidence: Optional[str] = None
    raw_judgment: Optional[str] = None
    normalized_score: float = 1.0
    calibration_version: str = "v5.0"


class CheckResult(BaseModel):
    check_id: str
    name: str
    score: float  # 0.0 - 1.0
    weight: float
    sample_size: int = 1
    passed: int = 1
    failed: int = 0
    coverage: float = 1.0  # 0.0 - 1.0
    status: str = "PASS"  # PASS | PARTIAL | DEFICIT | NOT_MEASURED
    confidence_interval: Optional[Tuple[float, float]] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    llm_judge: Optional[LLMJudgeRecord] = None
    methodology_version: str = "5.0"


class AuditScopeInfo(BaseModel):
    plan_tier: str = "starter"
    requested_pages: int = 5
    measured_pages: int = 5
    scope_coverage: float = 1.0  # measured_pages / requested_pages


class CategoryScore(BaseModel):
    category: Category
    score: Optional[float] = None # 0 - 100 or None if unmeasured
    confidence: float = 0.90 # 0 - 1.00
    coverage: float = 1.0 # measured_weight / total_weight (>=0.60 MEASURED, 0.30-0.5999 PARTIAL, <0.30 NOT_MEASURED)
    score_interval: Optional[Tuple[float, float]] = None
    weight: float = 0.0 # 0.0 - 1.0
    weighted_score: float = 0.0 # score * weight
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    summary: str
    deductions: List[Dict[str, Any]] = Field(default_factory=list)
    formula_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    check_results: List[CheckResult] = Field(default_factory=list)
    status: str = "MEASURED" # "MEASURED" | "PARTIAL" | "NOT_MEASURED"
    provenance: Optional[str] = None

class OverallScoreResult(BaseModel):
    overall_score: float # 0 - 100
    overall_confidence: float = 0.90 # 0 - 1.00
    evidence_coverage: float = 0.88 # 0 - 1.00
    grade: str # A+, A, B, C, D, F
    health_label: str # Excellent, Good, Moderate, Needs Attention, Critical
    category_scores: Dict[str, CategoryScore] = Field(default_factory=dict)
    intent_adjusted_weights: Dict[str, float] = Field(default_factory=dict)
    mathematical_derivation: List[Dict[str, Any]] = Field(default_factory=list)

class RoadmapItem(BaseModel):
    timeframe: str # "7_days", "30_days", "90_days"
    title: str
    description: str
    impact: str # "High", "Medium", "Low"
    effort: str = "Low" # "Low", "Medium", "High"
    category: Category
    related_finding_id: Optional[str] = None
    code_snippet: Optional[str] = None

class ExecutiveActionItem(BaseModel):
    rank: int
    priority: str = "P1" # "P0", "P1", "P2", "P3"
    action: str
    impact: str = "High" # "Very High", "High", "Medium", "Low"
    effort: str = "Low" # "Low", "Medium", "High"
    expected_outcome: str
    estimated_engineer_hours: int = 4
    dependencies: List[str] = Field(default_factory=list)
    validation: str = "Automated retest"
    category: Optional[Category] = None
    related_finding_id: Optional[str] = None

class ExecutiveTopActionsPlan(BaseModel):
    actions: List[ExecutiveActionItem] = Field(default_factory=list)
    total_engineer_hours: int = 0
    dependencies_flow: str = ""
    validation_mode: str = "automated_retest"

class AuditSnapshot(BaseModel):
    snapshot_id: str
    run_label: str
    date: str
    score: float
    category_scores: Dict[str, float] = Field(default_factory=dict)
    evidence_seal: str
    verified_schema_types: List[str] = Field(default_factory=list)
    findings_count: int = 0
    status: str = "HEALTHY"  # HEALTHY, IMPROVED, REGRESSION

class RegressionItem(BaseModel):
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM
    title: str
    category: str
    dimension_delta: Optional[float] = None
    description: str
    evidence_ref: Optional[str] = None

class RegressionReport(BaseModel):
    has_regression: bool = False
    regression_count: int = 0
    score_delta: float = 0.0 # e.g. -4.0
    baseline_run: Optional[AuditSnapshot] = None
    current_run: Optional[AuditSnapshot] = None
    regressions: List[RegressionItem] = Field(default_factory=list)
    historical_timeline: List[AuditSnapshot] = Field(default_factory=list)
    summary: str = ""
    detected_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class EvidenceTaxonomyReport(BaseModel):
    total_evidence_nodes: int = 0
    epistemic_integrity_score: float = 100.0 # % of findings that are directly OBSERVED or EXTERNALLY_VERIFIED
    class_counts: Dict[str, int] = Field(default_factory=dict)
    subtype_counts: Dict[str, int] = Field(default_factory=dict)
    classes_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    description: str = ""

class ViewportInspection(BaseModel):
    device: str # "desktop", "tablet", "mobile"
    width: int
    height: int
    above_the_fold: Dict[str, Any] = Field(default_factory=dict) # value_proposition, cta, trust, hierarchy, visual_density, navigation, contrast, forms
    detected_defects: List[str] = Field(default_factory=list) # "CTA below fold", "Text over image", "Low contrast (2.8:1)", "Mobile overflow", "Layout shift", "Tiny text (< 12px)", "Inconsistent spacing", "Visual hierarchy failure"
    screenshot_url: Optional[str] = None
    dom_anchors: List[str] = Field(default_factory=list)

class VisualUxInspectionReport(BaseModel):
    inspected_at: str
    tested_devices: List[str] = Field(default_factory=lambda: ["desktop", "tablet", "mobile"])
    viewports: Dict[str, ViewportInspection] = Field(default_factory=dict)
    overall_visual_ux_score: Optional[float] = None
    critical_visual_defects: List[Dict[str, Any]] = Field(default_factory=list)
    combined_intelligence: Dict[str, Any] = Field(default_factory=dict) # DOM intelligence + screenshot intelligence + browser interaction intelligence

class GscAttributionData(BaseModel):
    queries: List[Dict[str, Any]] = Field(default_factory=list)
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    average_position: float = 0.0
    pages: List[str] = Field(default_factory=list)
    countries: List[Dict[str, Any]] = Field(default_factory=list)
    devices: Dict[str, float] = Field(default_factory=dict)
    is_connected: bool = False

class Ga4AttributionData(BaseModel):
    landing_pages: List[Dict[str, Any]] = Field(default_factory=list)
    engagement_rate: float = 0.0
    conversion_rate: float = 0.0
    funnels: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    traffic_sources: List[Dict[str, Any]] = Field(default_factory=list)
    is_connected: bool = False

class CrmAttributionData(BaseModel):
    lead_source: List[Dict[str, Any]] = Field(default_factory=list)
    lead_quality_score: float = 0.0
    pipeline_value_inr: float = 0.0
    closed_revenue_inr: float = 0.0
    conversion_rate_lead_to_customer: float = 0.0
    is_connected: bool = False

class LifecycleRevenueIntelligence(BaseModel):
    domain: str
    stages: Dict[str, Any] = Field(default_factory=dict) # website -> search -> visitor -> lead -> revenue
    gsc: GscAttributionData = Field(default_factory=GscAttributionData)
    ga4: Ga4AttributionData = Field(default_factory=Ga4AttributionData)
    crm: CrmAttributionData = Field(default_factory=CrmAttributionData)
    summary: str = ""

class AgentCallRecord(BaseModel):
    call_id: str
    capability: str
    agent_id: Optional[str] = None
    model: str
    provider: str
    prompt_sha256: str
    prompt_template_sha256: str
    called_at: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: Optional[float] = None
    cost_basis: str = "unpriced"
    is_actual: bool = False
    actual_cost_usd: Optional[float] = None
    calculated_cost_usd: Optional[float] = None


class SubStepCostRecord(BaseModel):
    sub_step: str
    display_name: str
    capability: str = "general"
    calls_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    models: List[str] = Field(default_factory=list)
    is_actual: bool = False
    cost_basis: str = "unpriced"
    formula_rate: Optional[str] = None


class StageCostRecord(BaseModel):
    stage: str
    display_name: str
    calls_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    models: List[str] = Field(default_factory=list)
    sub_steps: Dict[str, SubStepCostRecord] = Field(default_factory=dict)


class TelemetryData(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    calculated_cost_usd: float = 0.0
    has_actual_costs: bool = False
    all_costs_actual: bool = False
    cost_complete: bool = True
    unpriced_calls: int = 0
    cost_basis: str = "unpriced"
    models_used: List[str] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    model_calls_count: int = 0
    agent_timings: Dict[str, float] = Field(default_factory=dict)
    agent_calls: List[AgentCallRecord] = Field(default_factory=list)
    stage_costs: Dict[str, StageCostRecord] = Field(default_factory=dict)


class LabPerformanceMetrics(BaseModel):
    ttfb_ms: float = 0.0
    fcp_ms: Optional[float] = None
    lcp_indicator_ms: Optional[float] = None
    cls_risk_score: float = 0.0
    tbt_proxy_ms: Optional[float] = None
    dns_ms: float = 0.0
    tcp_ms: float = 0.0
    tls_ms: float = 0.0
    download_ms: float = 0.0
    dom_content_loaded_ms: float = 0.0
    load_event_ms: float = 0.0
    total_transferred_kb: float = 0.0
    js_payload_kb: float = 0.0
    css_payload_kb: float = 0.0
    image_payload_kb: float = 0.0
    font_payload_kb: float = 0.0
    total_requests: int = 0
    request_count_by_type: Dict[str, int] = Field(default_factory=dict)
    render_blocking_count: int = 0
    render_blocking_resources: List[Dict[str, Any]] = Field(default_factory=list)
    third_party_scripts_count: int = 0
    third_party_scripts_kb: float = 0.0
    third_party_domains: List[str] = Field(default_factory=list)
    caching_policy: str = "UNSPECIFIED"
    cache_control: Optional[str] = None
    content_encoding: str = "none"
    server: str = "unspecified"
    font_display_strategy: Optional[str] = None
    images_missing_dimensions: int = 0
    # Google Lighthouse & Core Web Vitals Suite
    lighthouse_performance_score: Optional[float] = None
    lighthouse_accessibility_score: Optional[float] = None
    lighthouse_best_practices_score: Optional[float] = None
    lighthouse_seo_score: Optional[float] = None
    lcp_ms: Optional[float] = None
    cls_score: Optional[float] = None
    tbt_ms: Optional[float] = None
    speed_index_ms: Optional[float] = None
    raw_vs_rendered_diff: Optional[Dict[str, Any]] = None
    lighthouse_audit_version: Optional[str] = None


class FieldPerformanceMetrics(BaseModel):
    has_field_data: bool = False
    origin: str = ""
    p75_lcp_ms: Optional[float] = None
    p75_inp_ms: Optional[float] = None
    p75_cls: Optional[float] = None
    p75_fcp_ms: Optional[float] = None
    p75_ttfb_ms: Optional[float] = None
    device_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    distributions: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    status: str = "UNAVAILABLE"
    unavailability_reason: Optional[str] = None
    provenance_label: str = "NOT_CONFIGURED"


class PageEvidence(BaseModel):
    url: str
    status_code: int = 200
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: List[str] = Field(default_factory=list)
    h2: List[str] = Field(default_factory=list)
    h3: List[str] = Field(default_factory=list)
    word_count: int = 0
    readability_score: float = 0.0
    canonical_url: Optional[str] = None
    robots_meta: Optional[str] = None
    viewport: Optional[str] = None
    og_tags: Dict[str, str] = Field(default_factory=dict)
    twitter_tags: Dict[str, str] = Field(default_factory=dict)
    meta_tags: Dict[str, str] = Field(default_factory=dict)
    schema_types: List[str] = Field(default_factory=list)
    raw_schema: List[Dict[str, Any]] = Field(default_factory=list)
    structured_data: List[Dict[str, Any]] = Field(default_factory=list)
    raw_html: Optional[str] = None
    internal_links: List[str] = Field(default_factory=list)
    external_links: List[str] = Field(default_factory=list)
    images_without_alt: int = 0
    total_images: int = 0
    ttfb_ms: float = 0.0
    dom_elements_count: int = 0
    scripts_count: int = 0
    stylesheets_count: int = 0
    page_type: str = "general"
    body_text: Optional[str] = None
    text_content: Optional[str] = None
    ctas: List[str] = Field(default_factory=list)
    call_to_actions: List[str] = Field(default_factory=list)
    forms: List[Dict[str, Any]] = Field(default_factory=list)
    render_mode: str = "static"
    response_headers: Dict[str, str] = Field(default_factory=dict)
    security_headers: Dict[str, str] = Field(default_factory=dict)
    redirect_chain: List[Dict[str, Any]] = Field(default_factory=list)
    is_redirected: bool = False
    final_url: Optional[str] = None
    snapshot_id: Optional[str] = None
    snapshot_path: Optional[str] = None
    observed_at: Optional[str] = None
    image_assets: List[Dict[str, Any]] = Field(default_factory=list)
    x_robots_tag: Optional[str] = None
    status_code_class: str = "2xx"
    is_indexable: bool = True
    canonical_status: str = "self"
    title_pixel_width: int = 0
    meta_pixel_width: int = 0
    title_pixel_status: str = "optimal"
    meta_pixel_status: str = "optimal"
    inlinks_count: int = 0
    outlinks_internal_count: int = 0
    outlinks_external_count: int = 0
    thin_content: bool = False
    hreflang_tags: Dict[str, str] = Field(default_factory=dict)
    html_lang: Optional[str] = None
    nap_data: Optional[Dict[str, Any]] = None
    content_authority: Optional[Dict[str, Any]] = None
    lab_performance: Optional[LabPerformanceMetrics] = None
    field_performance: Optional[FieldPerformanceMetrics] = None

class CopyIssue(BaseModel):
    area: str
    severity: str = "MEDIUM"
    issue: str
    why_it_matters: str = ""

class CopySection(BaseModel):
    section_id: str = "hero"
    section_name: str = "Hero & Primary Hook"
    status: str = "NEEDS_REWRITE"  # NEEDS_REWRITE | UPDATE_RECOMMENDED | OPTIMIZED
    current_preview: Optional[str] = None
    suggested_copy: str = ""
    purpose: str = ""
    seo_geo_notes: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

class CopyFaqItem(BaseModel):
    question: str
    answer: str
    target_engine: Optional[str] = "ChatGPT / Perplexity / Google AI Overviews"

class SuggestedCopy(BaseModel):
    title: str = ""
    meta_description: str = ""
    h1: str = ""
    hero: str = ""
    primary_cta: str = ""
    secondary_cta: Optional[str] = None
    supporting_points: List[str] = Field(default_factory=list)
    body_rewrite: str = ""
    geo_snippet: Optional[str] = None
    hook_3sec: Optional[str] = None
    sections: List[CopySection] = Field(default_factory=list)
    faq_items: List[CopyFaqItem] = Field(default_factory=list)
    notes: Optional[str] = None

class PageSeoAudit(BaseModel):
    score: float = 0.0
    title_status: str = "missing"
    title_length: int = 0
    meta_status: str = "missing"
    meta_length: int = 0
    h1_status: str = "missing"
    heading_structure: str = ""
    canonical_status: str = "missing"
    robots_status: str = "default"
    og_status: str = "missing"
    schema_status: str = "missing"
    indexability: str = "indexable"
    issues: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class PageCopyAudit(BaseModel):
    score: Optional[float] = None
    voice: str = ""
    clarity: str = ""
    persuasion: str = ""
    audience_fit: str = ""
    cta_quality: str = ""
    geo_score: Optional[float] = None
    seo_score: float = 0.0
    issues: List[CopyIssue] = Field(default_factory=list)
    what_works: List[str] = Field(default_factory=list)
    analysis: str = ""
    suggested: Optional[SuggestedCopy] = None
    specialist_insights: Dict[str, str] = Field(default_factory=dict)
    llm_status: str = "pending"  # ok | failed | skipped
    llm_failure_reason: Optional[str] = None
    llm_failure_code: Optional[str] = None

class PageUxSignals(BaseModel):
    cta_count: int = 0
    ctas: List[str] = Field(default_factory=list)
    images_missing_alt: int = 0
    total_images: int = 0
    internal_links: int = 0
    external_links: int = 0
    ttfb_ms: float = 0.0
    readability: float = 0.0
    word_count: int = 0
    viewport: Optional[str] = None
    scripts_count: int = 0
    lab_performance: Optional[LabPerformanceMetrics] = None
    field_performance: Optional[FieldPerformanceMetrics] = None

class PageReport(BaseModel):
    url: str
    page_type: str = "general"
    title: Optional[str] = None
    overall_score: float = 0.0
    seo: PageSeoAudit = Field(default_factory=PageSeoAudit)
    copywriting: PageCopyAudit = Field(default_factory=PageCopyAudit)
    ux: PageUxSignals = Field(default_factory=PageUxSignals)
    findings: List[str] = Field(default_factory=list)

class RenderedVsRawDelta(BaseModel):
    raw_word_count: int = 0
    rendered_word_count: int = 0
    word_count_delta: int = 0
    raw_headings: List[str] = Field(default_factory=list)
    rendered_headings: List[str] = Field(default_factory=list)
    js_only_headings: List[str] = Field(default_factory=list)
    raw_internal_links: int = 0
    rendered_internal_links: int = 0
    js_only_links_count: int = 0
    js_dependency_risk: str = "LOW"  # "LOW" | "MEDIUM" | "CRITICAL"

class IndexationPageStatus(BaseModel):
    url: str
    status_code: int = 200
    crawlable: bool = True
    indexable: bool = True
    indexed_state: str = "UNVERIFIED_NO_GSC"  # "INDEXED" | "NOT_INDEXED" | "UNVERIFIED_NO_GSC"
    canonical_declared: Optional[str] = None
    canonical_selected: Optional[str] = None
    canonical_match: bool = True
    has_noindex: bool = False
    x_robots_tag: Optional[str] = None
    robots_blocked: bool = False
    is_soft_404: bool = False
    is_duplicate: bool = False
    duplicate_of_url: Optional[str] = None
    gsc_coverage_state: Optional[str] = None  # "Discovered - currently not indexed", "Crawled - currently not indexed", etc.
    alternate_canonical: Optional[str] = None
    is_redirect: bool = False
    redirect_target: Optional[str] = None
    is_js_only_content: bool = False
    blocked_resources: List[str] = Field(default_factory=list)
    render_delta: Optional[RenderedVsRawDelta] = None

class IndexationAuditRollup(BaseModel):
    total_pages_evaluated: int = 0
    crawlable_count: int = 0
    indexable_count: int = 0
    indexed_count: int = 0
    blocked_by_robots_count: int = 0
    noindex_count: int = 0
    x_robots_tag_count: int = 0
    soft_404_count: int = 0
    duplicate_count: int = 0
    canonical_mismatch_count: int = 0
    discovered_not_indexed_count: int = 0
    crawled_not_indexed_count: int = 0
    alternate_canonical_count: int = 0
    redirect_count: int = 0
    js_dependent_count: int = 0
    blocked_resources_count: int = 0
    pages: List[IndexationPageStatus] = Field(default_factory=list)
    summary: str = ""

class CrawlManifest(BaseModel):
    domain: str = ""
    base_url: str = ""
    total_pages_discovered: int = 0
    pages: List[PageEvidence] = Field(default_factory=list)
    sitemap_found: bool = False
    sitemap_url: Optional[str] = None
    robots_txt_found: bool = False
    robots_txt_content: Optional[str] = None
    crawl_health: Dict[str, Any] = Field(default_factory=dict)
    redirect_chains: List[Dict[str, Any]] = Field(default_factory=list)
    crawl_budget: Dict[str, Any] = Field(default_factory=dict)
    sitemap_urls: List[str] = Field(default_factory=list)
    orphan_urls: List[str] = Field(default_factory=list)
    indexation_rollup: Optional[IndexationAuditRollup] = None

class UntrustedObservation(BaseModel):
    id: str
    source_url: str
    content_sha256: str
    observation_type: str  # "dom_text", "script", "meta", "heading"
    sanitized_content: str
    has_pii: bool = False
    has_injection_vector: bool = False
    redacted_fields: List[str] = Field(default_factory=list)
    is_untrusted_web_input: bool = True

class ChartSpecification(BaseModel):
    id: str
    chart_type: str  # 'radar' | 'latency_curve' | 'defect_donut' | 'engine_comparison_bar' | 'journey_funnel' | 'content_depth_bar'
    title: str
    subtitle: str
    ai_insight: str
    category: str  # 'OVERALL' | 'TECHNICAL_SEO' | 'GEO' | 'UX_CONVERSION' | 'CONTENT' | 'COMMERCIAL'
    data: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    is_recommended: bool = True
    priority_order: int = 1

class SpotlightMetric(BaseModel):
    id: str
    label: str
    value: Union[str, int, float]
    unit: Optional[str] = None
    change_indicator: Optional[str] = None
    status: str = "neutral"  # "good" | "warning" | "bad" | "neutral"
    significance: str
    category: str

class VisualIntelligencePayload(BaseModel):
    ai_rationale: str
    audit_case_profile: str
    selected_visualizations: List[ChartSpecification] = Field(default_factory=list)
    spotlight_metrics: List[SpotlightMetric] = Field(default_factory=list)
    available_customizations: List[str] = Field(default_factory=list)
    generated_at: str

    @property
    def charts(self) -> List[ChartSpecification]:
        return self.selected_visualizations

# ===========================================================================
# 40-PAGE ENTERPRISE AUDIT ROLLUP & PARAMETER MODELS
# ===========================================================================

class MetaBucketItem(BaseModel):
    url: str
    text: Optional[str] = None
    char_length: int = 0
    pixel_length: int = 0

class MetaBucketRollup(BaseModel):
    total_pages_evaluated: int = 0
    # Titles
    missing_titles: List[MetaBucketItem] = Field(default_factory=list)
    too_short_titles: List[MetaBucketItem] = Field(default_factory=list)  # <30 chars
    optimal_titles: List[MetaBucketItem] = Field(default_factory=list)    # 50-60 chars
    too_long_titles: List[MetaBucketItem] = Field(default_factory=list)    # >60 chars
    duplicate_titles: List[MetaBucketItem] = Field(default_factory=list)  # same title across URLs
    title_issue_count: int = 0
    # Descriptions
    missing_descriptions: List[MetaBucketItem] = Field(default_factory=list)
    too_short_descriptions: List[MetaBucketItem] = Field(default_factory=list)  # <70 chars
    optimal_descriptions: List[MetaBucketItem] = Field(default_factory=list)    # 150-160 chars
    too_long_descriptions: List[MetaBucketItem] = Field(default_factory=list)   # >160 chars
    duplicate_descriptions: List[MetaBucketItem] = Field(default_factory=list)
    description_issue_count: int = 0
    # Pixel Truncation
    truncated_pixel_titles: List[MetaBucketItem] = Field(default_factory=list)  # >580px
    truncated_pixel_descriptions: List[MetaBucketItem] = Field(default_factory=list)  # >960px
    # Title / H1 Collision
    h1_title_collision_count: int = 0
    h1_title_collision_urls: List[str] = Field(default_factory=list)
    title_summary: str = ""
    description_summary: str = ""

class HeadingIssueItem(BaseModel):
    url: str
    headings: List[str] = Field(default_factory=list)
    issue_type: str = ""
    detail: str = ""

class HeadingHierarchyRollup(BaseModel):
    total_pages_evaluated: int = 0
    missing_h1: List[HeadingIssueItem] = Field(default_factory=list)
    multiple_h1: List[HeadingIssueItem] = Field(default_factory=list)
    short_h1: List[HeadingIssueItem] = Field(default_factory=list)  # <10 chars
    long_h1: List[HeadingIssueItem] = Field(default_factory=list)   # >70 chars
    duplicate_h1: List[HeadingIssueItem] = Field(default_factory=list)
    hierarchy_violations: List[Dict[str, Any]] = Field(default_factory=list)
    outline_tree_sample: List[Dict[str, Any]] = Field(default_factory=list)
    total_heading_issues: int = 0
    h1_health_score: float = 100.0

class RedirectHop(BaseModel):
    status: int
    url: str
    location: Optional[str] = None

class HostVariantProbeResult(BaseModel):
    origin_url: str
    final_destination: str
    status_code: int
    hops: List[RedirectHop] = Field(default_factory=list)
    hop_count: int = 0
    proper_canonical_redirect: bool = False
    error: Optional[str] = None

class RedirectAuditReport(BaseModel):
    target_domain: str
    canonical_destination: str
    host_variants: Dict[str, HostVariantProbeResult] = Field(default_factory=dict)
    proper_301_consolidation: bool = False
    has_chain_gt_1_hop: bool = False
    has_redirect_loop: bool = False
    redirects_to_4xx: bool = False
    chains_recorded: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""

class ClickDepthReport(BaseModel):
    homepage_url: str
    total_pages_analyzed: int = 0
    depth_1_count: int = 0
    depth_2_count: int = 0
    depth_3_count: int = 0
    depth_4_plus_count: int = 0
    max_click_depth: int = 0
    pages_by_depth: Dict[str, List[str]] = Field(default_factory=dict)
    depth_distribution_pct: Dict[str, float] = Field(default_factory=dict)
    high_depth_warning_count: int = 0

class OrphanPageReport(BaseModel):
    total_sitemap_urls: int = 0
    total_crawled_urls: int = 0
    orphan_urls: List[str] = Field(default_factory=list)
    orphan_count: int = 0
    orphan_percentage: float = 0.0
    summary: str = ""

class AnchorTextAudit(BaseModel):
    total_links_analyzed: int = 0
    generic_anchor_count: int = 0
    low_equity_terms_found: List[Dict[str, Any]] = Field(default_factory=list)
    flagged_anchor_instances: List[Dict[str, str]] = Field(default_factory=list)
    summary: str = ""

class FormAuditItem(BaseModel):
    page_url: str
    form_id: Optional[str] = None
    form_action: Optional[str] = None
    input_count: int = 0
    missing_labels_count: int = 0
    input_types: List[str] = Field(default_factory=list)
    submit_button_text: str = ""
    has_captcha_or_honeypot: bool = False
    has_confirmation_destination: bool = False
    friction_risk: str = "LOW"  # "LOW" | "MEDIUM" | "HIGH"

class FormAuditReport(BaseModel):
    total_forms_detected: int = 0
    forms: List[FormAuditItem] = Field(default_factory=list)
    forms_with_missing_labels: int = 0
    forms_without_captcha: int = 0
    forms_without_confirmation: int = 0
    cro_friction_grade: str = "A"
    friction_score: float = 0.0
    actionable_remedies: List[str] = Field(default_factory=list)

class MediaAssetItem(BaseModel):
    url: str
    page_url: str
    alt_text: Optional[str] = None
    has_alt: bool = True
    is_empty_alt: bool = False
    has_dimensions: bool = True
    format: str = "other"  # "png", "jpeg", "webp", "avif", "svg", etc.
    is_modern_format: bool = False
    is_insecure_http: bool = False

class MediaAssetAuditReport(BaseModel):
    total_images_analyzed: int = 0
    missing_alt_count: int = 0
    empty_alt_count: int = 0
    missing_dimensions_count: int = 0  # CLS hazard
    modern_format_count: int = 0
    non_modern_format_count: int = 0
    mixed_content_count: int = 0
    mixed_content_urls: List[str] = Field(default_factory=list)
    cls_risk_images: List[Dict[str, str]] = Field(default_factory=list)
    decorative_alt_compliant_count: int = 0
    summary: str = ""


class WcagViolation(BaseModel):
    rule_id: str
    wcag_criterion: str  # e.g. "1.1.1 Non-text Content", "1.4.3 Contrast (Minimum)"
    level: str = "AA"     # "A" | "AA" | "AAA"
    principle: str = "Perceivable"  # "Perceivable" | "Operable" | "Understandable" | "Robust"
    category: str = "images"  # "contrast", "keyboard", "forms", "headings", "landmarks", "aria", "links", "tables", "navigation", "images", "viewport"
    severity: Severity = Severity.MEDIUM
    impact: ImpactLevel = ImpactLevel.MEDIUM
    description: str
    selector: Optional[str] = None
    snippet: Optional[str] = None
    url: str
    recommendation: str


class WcagCategoryScore(BaseModel):
    category: str
    name: str
    passed: int = 0
    violations: int = 0
    score: float = 100.0


class WcagAuditSummary(BaseModel):
    total_checks_performed: int = 0
    violations_count: int = 0
    passed_checks_count: int = 0
    compliance_score: float = 100.0  # 0 to 100
    conformance_status: str = "PASS"  # "PASS" | "NEEDS_ATTENTION" | "NON_COMPLIANT"
    violations: List[WcagViolation] = Field(default_factory=list)
    principle_scores: Dict[str, float] = Field(default_factory=dict)
    category_breakdown: List[WcagCategoryScore] = Field(default_factory=list)

class SecurityAuditReport(BaseModel):
    target_domain: str = ""
    score: Optional[float] = None
    grade: Optional[str] = None
    hsts_enabled: bool = False
    hsts_header: Optional[str] = None
    csp_enabled: bool = False
    csp_header: Optional[str] = None
    x_frame_options: Optional[str] = None
    x_content_type_options: Optional[str] = None
    referrer_policy: Optional[str] = None
    permissions_policy: Optional[str] = None
    information_disclosure_headers: List[Dict[str, str]] = Field(default_factory=list)
    insecure_cookies: List[str] = Field(default_factory=list)
    critical_findings: List[str] = Field(default_factory=list)
    recommended_headers: Dict[str, str] = Field(default_factory=dict)
    summary: str = ""

class SchemaIssue(BaseModel):
    url: str
    schema_type: str
    severity: str = "ERROR"  # "ERROR" (blocks rich results) | "WARNING" (missing recommended field)
    field: str
    message: str

class SchemaValidationReport(BaseModel):
    total_pages_with_schema: int = 0
    total_entities_detected: int = 0
    valid_entities_count: int = 0
    entities_with_errors_count: int = 0
    entities_with_warnings_count: int = 0
    detected_types: List[str] = Field(default_factory=list)
    issues: List[SchemaIssue] = Field(default_factory=list)
    summary: str = ""

class PerEngineAiScore(BaseModel):
    engine_name: str  # "ChatGPT / SearchGPT" | "Perplexity" | "Google AI Overviews" | "Claude / Gemini"
    score: float = 0.0
    grade: str = "C"
    readiness_band: str = "medium"  # "high" | "medium" | "low"
    evaluation_type: str = "On-Page Structural Readiness (Simulated Extractability)"
    strengths: List[str] = Field(default_factory=list)
    critical_gaps: List[str] = Field(default_factory=list)
    recommended_fixes: List[str] = Field(default_factory=list)

class InformationGainReport(BaseModel):
    score: Optional[float] = None
    grade: Optional[str] = None
    has_proprietary_statistics: bool = False
    has_benchmark_tables: bool = False
    has_methodology_section: bool = False
    has_executive_quotes: bool = False
    fluff_ratio_score: Optional[float] = None
    original_data_signals: List[str] = Field(default_factory=list)
    commodity_fluff_signals: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class AiBotDirectivesReport(BaseModel):
    robots_txt_status: str = "VALIDATED"
    gptbot_allowed: bool = True
    perplexitybot_allowed: bool = True
    claudebot_allowed: bool = True
    google_extended_allowed: bool = True
    llms_txt_found: bool = False
    llms_txt_url: Optional[str] = None
    llms_txt_generated: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)

class PerEngineAiMatrix(BaseModel):
    chatgpt: PerEngineAiScore
    perplexity: PerEngineAiScore
    google_aio: PerEngineAiScore
    claude_gemini: PerEngineAiScore
    overall_engine_score: float = 0.0
    overall_engine_grade: str = "B"
    information_gain: InformationGainReport
    ai_bot_directives: AiBotDirectivesReport

class CanonicalAuditItem(BaseModel):
    url: str
    canonical_url: Optional[str] = None
    status: str = "self"  # "self" | "canonicalized" | "missing" | "broken" | "relative" | "multiple" | "cross_domain"
    detail: str = ""
    is_issue: bool = False
    severity: str = "INFO"

class CanonicalAuditRollup(BaseModel):
    total_pages_evaluated: int = 0
    self_canonical_count: int = 0
    canonicalized_count: int = 0
    missing_canonical_count: int = 0
    broken_canonical_count: int = 0
    relative_canonical_count: int = 0
    multiple_canonical_count: int = 0
    cross_domain_canonical_count: int = 0
    canonical_health_score: float = 100.0
    items: List[CanonicalAuditItem] = Field(default_factory=list)
    summary: str = ""

class HttpStatusItem(BaseModel):
    url: str
    status_code: int = 200
    status_class: str = "2xx"  # "2xx" | "3xx" | "4xx" | "5xx"
    status_text: str = "OK"
    redirect_target: Optional[str] = None
    inlinks_count: int = 0

class BrokenLinkRecord(BaseModel):
    source_url: str
    target_url: str
    anchor_text: str = ""
    status_code: int = 404
    error_type: str = "404 Not Found"

class HttpStatusBreakdown(BaseModel):
    total_urls_checked: int = 0
    count_2xx: int = 0
    count_3xx: int = 0
    count_4xx: int = 0
    count_5xx: int = 0
    status_health_score: float = 100.0
    pages_2xx: List[HttpStatusItem] = Field(default_factory=list)
    pages_3xx: List[HttpStatusItem] = Field(default_factory=list)
    pages_4xx: List[HttpStatusItem] = Field(default_factory=list)
    pages_5xx: List[HttpStatusItem] = Field(default_factory=list)
    broken_links: List[BrokenLinkRecord] = Field(default_factory=list)
    summary: str = ""

class CompetitorSeoParityProfile(BaseModel):
    domain: str
    brand_name: str
    is_target: bool = False
    pages_sampled: int = 1
    technical_health_score: Optional[int] = None
    onpage_score: Optional[int] = None
    content_depth_score: Optional[int] = None
    schema_score: Optional[int] = None
    overall_seo_score: Optional[int] = None
    avg_ttfb_ms: float = 0.0
    http_200_rate_pct: float = 100.0
    title_optimal_pct: float = 100.0
    meta_optimal_pct: float = 100.0
    h1_health_pct: float = 100.0
    avg_word_count: int = 0
    schema_types_count: int = 0
    has_breadcrumbs: bool = False
    modern_image_pct: float = 0.0
    summary_verdict: str = ""

class CompetitorSeoParityMatrix(BaseModel):
    target_domain: str
    competitors: List[CompetitorSeoParityProfile] = Field(default_factory=list)
    target_rank: int = 1
    peer_avg_seo_score: Optional[int] = None
    top_advantages: List[str] = Field(default_factory=list)
    critical_deficits: List[str] = Field(default_factory=list)
    strategic_takeaway: str = ""

class CausalDiagnosticChain(BaseModel):
    bottleneck_id: str
    title: str
    primary_category: Category
    observed_symptoms: List[str] = Field(default_factory=list)
    inferred_root_cause: str
    business_consequence: str
    prescribed_remediation: str
    expected_mechanism: str
    verification_step: str
    external_verification: str
    projected_outcome: str
    severity: Severity = Severity.HIGH
    confidence: float = 0.90
    contributing_finding_ids: List[str] = Field(default_factory=list)

class NapRecord(BaseModel):
    page_url: str
    phone_numbers: List[str] = Field(default_factory=list)
    addresses: List[str] = Field(default_factory=list)
    has_map_embed: bool = False
    map_embed_urls: List[str] = Field(default_factory=list)
    gbp_links: List[str] = Field(default_factory=list)
    citation_links: List[str] = Field(default_factory=list)

class LocalLandingPageAudit(BaseModel):
    url: str
    target_location: Optional[str] = None
    has_unique_nap: bool = False
    has_local_schema: bool = False
    has_map: bool = False
    has_local_reviews: bool = False
    status: str = "PASS"  # "PASS" | "INCOMPLETE" | "CRITICAL"
    issues: List[str] = Field(default_factory=list)

class LocalSeoAuditReport(BaseModel):
    status: str = "PASS"  # "PASS" | "NEEDS_ATTENTION" | "NOT_APPLICABLE" | "FAILED"
    nap_consistency_score: float = 100.0  # 0 - 100
    detected_company_name: Optional[str] = None
    consistent_phone: Optional[str] = None
    consistent_address: Optional[str] = None
    phone_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    address_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    has_google_business_profile: bool = False
    gbp_urls: List[str] = Field(default_factory=list)
    has_google_maps_embed: bool = False
    local_citations_found: List[str] = Field(default_factory=list)
    local_business_schema_found: bool = False
    local_schema_completeness_pct: float = 0.0
    schema_missing_fields: List[str] = Field(default_factory=list)
    local_landing_pages: List[LocalLandingPageAudit] = Field(default_factory=list)
    nap_records: List[NapRecord] = Field(default_factory=list)
    summary: str = ""

class HreflangEntry(BaseModel):
    hreflang: str
    href: str

class HreflangValidationIssue(BaseModel):
    url: str
    issue_type: str  # "invalid_language_code" | "missing_return_tag" | "missing_x_default" | "canonical_conflict" | "lang_mismatch"
    severity: str    # "ERROR" | "WARNING"
    target_hreflang: Optional[str] = None
    target_url: Optional[str] = None
    message: str

class HreflangMatrixItem(BaseModel):
    url: str
    declared_lang: Optional[str] = None
    alternates_count: int = 0
    alternates: List[HreflangEntry] = Field(default_factory=list)
    has_x_default: bool = False
    return_tags_valid: bool = True
    missing_return_tags: List[str] = Field(default_factory=list)
    canonical_aligned: bool = True

class InternationalSeoAuditReport(BaseModel):
    status: str = "PASS"  # "PASS" | "WARNING" | "FAILED" | "NOT_APPLICABLE"
    is_multilingual: bool = False
    total_pages_with_hreflang: int = 0
    locales_detected: List[str] = Field(default_factory=list)
    has_x_default: bool = False
    return_tags_healthy: bool = True
    issues: List[HreflangValidationIssue] = Field(default_factory=list)
    matrix: List[HreflangMatrixItem] = Field(default_factory=list)
    summary: str = ""

class CannibalizationCluster(BaseModel):
    cluster_id: str
    primary_topic: str
    urls: List[str] = Field(default_factory=list)
    similarity_score: float = 0.0  # 0.0 - 1.0
    shared_headings: List[str] = Field(default_factory=list)
    recommendation: str = ""

class PageContentAuthority(BaseModel):
    url: str
    word_count: int = 0
    topical_entities: List[str] = Field(default_factory=list)
    information_gain_score: float = 0.0  # 0 - 100
    original_data_points: int = 0
    first_party_evidence_markers: List[str] = Field(default_factory=list)
    expert_signals: List[str] = Field(default_factory=list)
    unbacked_claims: List[str] = Field(default_factory=list)
    search_intent: str = "INFORMATIONAL"  # "INFORMATIONAL" | "COMMERCIAL" | "TRANSACTIONAL" | "NAVIGATIONAL"
    intent_mismatch: bool = False
    intent_notes: str = ""

class TopicalAuthorityAuditReport(BaseModel):
    status: str = "PASS"  # "PASS" | "NEEDS_IMPROVEMENT" | "THIN_COMMODITY"
    topical_coverage_score: float = 0.0  # 0 - 100
    avg_information_gain: float = 0.0    # 0 - 100
    total_original_data_points: int = 0
    first_party_evidence_density: float = 0.0
    pages_with_expert_signals: int = 0
    unbacked_claims_total: int = 0
    cannibalization_clusters: List[CannibalizationCluster] = Field(default_factory=list)
    search_intent_distribution: Dict[str, int] = Field(default_factory=dict)
    pages: List[PageContentAuthority] = Field(default_factory=list)
    summary: str = ""

class ExecutiveReport(BaseModel):
    report_id: str
    analysis_id: Optional[str] = None
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    mission_id: Optional[str] = None
    website_url: str
    domain: str
    generated_at: str
    business_profile: BusinessProfile
    resolved_entity: Optional[ResolvedEntity] = None
    scores: OverallScoreResult
    story_summary: str
    what_site_gets_right: List[str] = Field(default_factory=list)
    what_is_holding_it_back: List[str] = Field(default_factory=list)
    primary_strategic_opportunity: str
    consultant_advice_what_to_ignore: str
    three_way_comparison: ThreeWayComparison
    ai_search_matrix: List[AiSearchQueryEvaluation] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    code_patches: List[CodePatch] = Field(default_factory=list)
    roadmap_7_days: List[RoadmapItem] = Field(default_factory=list)
    roadmap_30_days: List[RoadmapItem] = Field(default_factory=list)
    roadmap_90_days: List[RoadmapItem] = Field(default_factory=list)
    top_10_actions: Optional[ExecutiveTopActionsPlan] = None
    regression_report: Optional[RegressionReport] = None
    evidence_taxonomy: Optional[EvidenceTaxonomyReport] = None
    visual_ux: Optional[VisualUxInspectionReport] = None
    lifecycle_revenue: Optional[LifecycleRevenueIntelligence] = None
    telemetry: TelemetryData = Field(default_factory=TelemetryData)
    crawl_summary: Dict[str, Any] = Field(default_factory=dict)
    crawl_manifest: Optional[CrawlManifest] = None
    page_reports: List[PageReport] = Field(default_factory=list)
    agent_execution_trace: List[Dict[str, Any]] = Field(default_factory=list)
    policy_pack: str = "enterprise_web_intel_v4"
    sealed_evidence_snapshot_id: Optional[str] = None
    manifest_id: Optional[str] = None
    honest_scores: Optional[HonestScores] = None
    commercial_evaluations: List[CommercialQueryEvaluation] = Field(default_factory=list)
    dynamic_sandbox_evaluations: List[DynamicSandboxQuestionEvaluation] = Field(default_factory=list)
    # KIE Phase 6: Knowledge graph summary and 5-dimension AI visibility scorecard
    kie_graph_summary: Optional[Dict[str, Any]] = None
    five_dimension_ai_visibility: Optional[Dict[str, Any]] = None
    competitor_bakeoff: Optional[CompetitorBakeoffResult] = None
    character_safe_copy: Optional[CharacterSafeCopy] = None
    whatsapp_summary: Optional[str] = None
    evidence_graph: Optional[Dict[str, Any]] = None
    remediation_patches: List[RemediationPatch] = Field(default_factory=list)
    roi_estimate: Optional[RoiEstimate] = None
    semantic_business: Optional[SemanticBusinessRepresentation] = None
    geo_readiness: Optional[GeoReadinessReport] = None
    ai_visibility_scorecard: Optional[AiVisibilityScorecard] = None
    agent_readiness: Optional[AgentReadinessReport] = None
    contradictions: List[ContradictionReport] = Field(default_factory=list)
    exploratory_hypotheses: List[Finding] = Field(default_factory=list)
    scoring_rubric_version: str = "enterprise_web_intel_v4"
    visual_intelligence: Optional[VisualIntelligencePayload] = None
    evidence_ledger: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    integrity_repairs_log: List[Dict[str, Any]] = Field(default_factory=list)
    certification_status: str = "CERTIFIED"  # "CERTIFIED" | "DEGRADED_SECTIONS_WITHHELD"
    withheld_sections: List[Dict[str, str]] = Field(default_factory=list)
    meta_rollup: Optional[MetaBucketRollup] = None
    heading_hierarchy: Optional[HeadingHierarchyRollup] = None
    host_and_redirects: Optional[RedirectAuditReport] = None
    click_depth: Optional[ClickDepthReport] = None
    orphan_pages: Optional[OrphanPageReport] = None
    anchor_text_audit: Optional[AnchorTextAudit] = None
    form_audit: Optional[FormAuditReport] = None
    media_assets: Optional[MediaAssetAuditReport] = None
    per_engine_geo: Optional[PerEngineAiMatrix] = None
    security_audit: Optional[SecurityAuditReport] = None
    schema_validation: Optional[SchemaValidationReport] = None
    canonical_audit: Optional[CanonicalAuditRollup] = None
    http_status_breakdown: Optional[HttpStatusBreakdown] = None
    competitor_seo_parity: Optional[CompetitorSeoParityMatrix] = None
    wcag_audit: Optional[WcagAuditSummary] = None
    external_authority: Optional[Dict[str, Any]] = None
    causal_diagnostic_chains: List[CausalDiagnosticChain] = Field(default_factory=list)
    scoring_explanation: Optional[str] = None
    observatory_records: List[Dict[str, Any]] = Field(default_factory=list)
    competitive_evidence_graph: Optional[Dict[str, Any]] = None
    competitive_report: Optional[Dict[str, Any]] = None
    indexation_intelligence: Optional[IndexationAuditRollup] = None
    local_seo: Optional[LocalSeoAuditReport] = None
    international_seo: Optional[InternationalSeoAuditReport] = None
    topical_authority: Optional[TopicalAuthorityAuditReport] = None
    derived_intelligence: List[DerivedMetric] = Field(default_factory=list)
    claim_ledger: Optional[ClaimLedger] = None

class AnalysisRequest(BaseModel):
    website_url: str
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    project_id: Optional[str] = "proj_default"
    country: Optional[str] = "Global"
    language: Optional[str] = "en"
    industry: Optional[str] = None
    site_type: Optional[str] = None
    declared_site_type_notes: Optional[str] = None
    competitors: List[str] = Field(default_factory=list)
    firecrawl_api_key: Optional[str] = None
    max_crawl_pages: Optional[int] = None
    voucher_code: Optional[str] = None
    data_residency: DataResidency = DataResidency.GLOBAL

class AnalysisRun(BaseModel):
    analysis_id: str
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    mission_id: str = ""
    website_url: str
    status: AnalysisStage = AnalysisStage.QUEUED
    progress_percentage: int = 0
    current_step: str = "Initialized"
    created_at: str
    updated_at: str
    error: Optional[str] = None
    report: Optional[ExecutiveReport] = None
    telemetry: TelemetryData = Field(default_factory=TelemetryData)
    is_sealed: bool = False
    manifest_id: Optional[str] = None
    report_id: Optional[str] = None


class TrackedKeyword(BaseModel):
    keyword_id: str
    project_id: str
    domain: str
    keyword: str
    target_url: Optional[str] = None
    intent: str = "Commercial"
    search_volume: int = 0
    cpc_usd: float = 0.0
    competition: float = 0.0
    keyword_difficulty: Optional[int] = None
    current_position: Optional[int] = None
    previous_position: Optional[int] = None
    best_position: Optional[int] = None
    position_delta: int = 0
    serp_features: List[str] = Field(default_factory=list)
    has_ai_overview: bool = False
    has_featured_snippet: bool = False
    is_active: bool = True
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TrackedKeywordCreate(BaseModel):
    project_id: str
    domain: str
    keyword: str
    target_url: Optional[str] = None
    intent: Optional[str] = "Commercial"
    tags: List[str] = Field(default_factory=list)


class KeywordSerpSnapshot(BaseModel):
    history_id: str
    keyword_id: str
    project_id: str
    domain: str
    position: Optional[int] = None
    previous_position: Optional[int] = None
    position_delta: int = 0
    ranking_url: Optional[str] = None
    serp_features: List[str] = Field(default_factory=list)
    has_ai_overview: bool = False
    has_featured_snippet: bool = False
    has_local_pack: bool = False
    snapshot_date: str
    raw_serp_ref: Optional[str] = None


class KeywordCompetitorSnapshot(BaseModel):
    comp_history_id: str
    keyword_id: str
    project_id: str
    competitor_domain: str
    position: Optional[int] = None
    ranking_url: Optional[str] = None
    snapshot_date: str


class KeywordMovementSummary(BaseModel):
    total_tracked: int = 0
    improved_count: int = 0
    declined_count: int = 0
    stable_count: int = 0
    top_3_count: int = 0
    top_10_count: int = 0
    page_1_breakouts: List[TrackedKeyword] = Field(default_factory=list)
    significant_drops: List[TrackedKeyword] = Field(default_factory=list)
    ai_overview_count: int = 0


class KeywordGapItem(BaseModel):
    keyword: str
    search_volume: int = 0
    keyword_difficulty: Optional[int] = None
    cpc_usd: float = 0.0
    competitor_domain: str
    competitor_rank: int
    target_rank: Optional[int] = None
    gap_type: str = "MISSING_OPPORTUNITY"  # MISSING_OPPORTUNITY, WEAK_PAGE_2, SHARED_BEHIND
    estimated_monthly_visits_opportunity: int = 0
    recommended_action: str
    recommended_page_slug: str


class KeywordGapReport(BaseModel):
    target_domain: str
    competitor_domains: List[str]
    total_missing_keywords: int = 0
    total_weak_keywords: int = 0
    total_opportunity_traffic: int = 0
    opportunities: List[KeywordGapItem] = Field(default_factory=list)
    summary: str = ""


