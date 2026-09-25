"""
Dristik AI Domain Models & Pydantic Schemas
Strict typed models for Evidence, Claims, Findings, Scores, Reports, and Telemetry.
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator
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
)

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

class Finding(BaseModel):
    finding_id: str
    org_id: str = "org_default"
    workspace_id: str = "ws_default"
    mission_id: Optional[str] = None
    category: Category
    severity: Severity
    title: str
    description: str
    evidence: List[FindingEvidence] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    rule_id: Optional[str] = None
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    confidence_label: EvidenceConfidence = EvidenceConfidence.STRONG
    impact: int = Field(default=5, ge=1, le=10)
    effort: int = Field(default=5, ge=1, le=10)
    priority: int = Field(default=5, ge=1, le=10)
    recommendation: str
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

    @property
    def id(self) -> str:
        return self.finding_id

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

class BusinessProfile(BaseModel):
    business_name: str = "Unknown Business"
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

class CompetitorBakeoffResult(BaseModel):
    competitor_domain: str
    status: str = "AVAILABLE"
    message: Optional[str] = None
    evaluations: List[CompetitorBakeoffItem] = Field(default_factory=list)
    target_wins: int = 0
    competitor_wins: int = 0
    ties: int = 0
    executive_takeaway: str = ""

class GeoQuestionEvidence(BaseModel):
    question_key: str
    question: str
    status: str
    evidence_url: Optional[str] = None
    evidence_snippet: Optional[str] = None
    why: str = ""


class GeoDimension(BaseModel):
    key: str
    label: str
    band: str
    summary: str
    evidence_notes: List[str] = Field(default_factory=list)


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
    schema_types: List[str] = Field(default_factory=list)
    schema_is_evidence_layer_only: bool = True
    market_country: str = "Global"
    market_language: str = "en"
    market_note: str = "Country and language are the audit request context. They are not a live geo-rank."
    # Layer 1 High-Density AI Extractability Additions
    extractability_score: Optional[float] = None
    entity_consistency: Optional[Dict[str, Any]] = None
    claims_analysis: Optional[Dict[str, Any]] = None
    question_graph_50: Optional[Dict[str, Any]] = None
    citation_passages: Optional[Dict[str, Any]] = None
    schema_crosscheck: Optional[Dict[str, Any]] = None


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


class CategoryScore(BaseModel):
    category: Category
    score: float # 0 - 100
    confidence: float = 0.90 # 0 - 1.00
    weight: float # 0.0 - 1.0
    weighted_score: float # score * weight
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    summary: str

class OverallScoreResult(BaseModel):
    overall_score: float # 0 - 100
    overall_confidence: float = 0.90 # 0 - 1.00
    evidence_coverage: float = 0.88 # 0 - 1.00
    grade: str # A+, A, B, C, D, F
    health_label: str # Excellent, Good, Moderate, Needs Attention, Critical
    category_scores: Dict[str, CategoryScore] = Field(default_factory=dict)
    intent_adjusted_weights: Dict[str, float] = Field(default_factory=dict)

class RoadmapItem(BaseModel):
    timeframe: str # "7_days", "30_days", "90_days"
    title: str
    description: str
    impact: str # "High", "Medium", "Low"
    effort: str = "Low" # "Low", "Medium", "High"
    category: Category
    related_finding_id: Optional[str] = None
    code_snippet: Optional[str] = None

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


class TelemetryData(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cost_complete: bool = True
    unpriced_calls: int = 0
    cost_basis: str = "unpriced"
    models_used: List[str] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    model_calls_count: int = 0
    agent_timings: Dict[str, float] = Field(default_factory=dict)
    agent_calls: List[AgentCallRecord] = Field(default_factory=list)

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
    schema_types: List[str] = Field(default_factory=list)
    raw_schema: List[Dict[str, Any]] = Field(default_factory=list)
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
    ctas: List[str] = Field(default_factory=list)
    render_mode: str = "static"

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

class PageReport(BaseModel):
    url: str
    page_type: str = "general"
    title: Optional[str] = None
    overall_score: float = 0.0
    seo: PageSeoAudit = Field(default_factory=PageSeoAudit)
    copywriting: PageCopyAudit = Field(default_factory=PageCopyAudit)
    ux: PageUxSignals = Field(default_factory=PageUxSignals)
    findings: List[str] = Field(default_factory=list)

class CrawlManifest(BaseModel):
    domain: str
    base_url: str
    total_pages_discovered: int = 0
    pages: List[PageEvidence] = Field(default_factory=list)
    sitemap_found: bool = False
    sitemap_url: Optional[str] = None
    robots_txt_found: bool = False
    robots_txt_content: Optional[str] = None
    crawl_health: Dict[str, Any] = Field(default_factory=dict)

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
    competitor_bakeoff: Optional[CompetitorBakeoffResult] = None
    character_safe_copy: Optional[CharacterSafeCopy] = None
    whatsapp_summary: Optional[str] = None
    evidence_graph: Optional[Dict[str, Any]] = None
    remediation_patches: List[RemediationPatch] = Field(default_factory=list)
    roi_estimate: Optional[RoiEstimate] = None
    semantic_business: Optional[SemanticBusinessRepresentation] = None
    geo_readiness: Optional[GeoReadinessReport] = None
    agent_readiness: Optional[AgentReadinessReport] = None
    contradictions: List[ContradictionReport] = Field(default_factory=list)
    exploratory_hypotheses: List[Finding] = Field(default_factory=list)
    scoring_rubric_version: str = "enterprise_web_intel_v4"
    visual_intelligence: Optional[VisualIntelligencePayload] = None
    evidence_ledger: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    integrity_repairs_log: List[Dict[str, Any]] = Field(default_factory=list)
    certification_status: str = "CERTIFIED"  # "CERTIFIED" | "DEGRADED_SECTIONS_WITHHELD"
    withheld_sections: List[Dict[str, str]] = Field(default_factory=list)

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

