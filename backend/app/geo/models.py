"""Canonical GEO (Generative Engine Optimization) Data Architecture — Phase 1.

Single source of truth for all GEO backend intelligence, specialist agents,
live provider testing, citation graphs, brand knowledge profiles, dual scorecards,
consolidated remediation, independent verification, experiments, monitoring,
frontend workspaces, and PDF reports.

Core architectural invariant:
Observed AI outcomes (what generative systems actually say, mention, recommend,
cite, and omit) are strictly separated from GEO readiness & contributing factors.
Missing credentials or untested platforms are never treated as zero visibility.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

GEO_METHODOLOGY_VERSION = "geo-enterprise-v1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─────────────────────────────────────────────────────────────────────────────
# Mandatory Enums & Data-Quality States
# ─────────────────────────────────────────────────────────────────────────────


class GEODataQualityState(str, Enum):
    OBSERVED = "OBSERVED"
    NOT_OBSERVED = "NOT_OBSERVED"
    NOT_TESTED = "NOT_TESTED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SIMULATION_ONLY = "SIMULATION_ONLY"
    VERIFIED = "VERIFIED"


class GEOTestingMode(str, Enum):
    API_MODEL_ONLY = "API_MODEL_ONLY"
    API_WITH_SEARCH = "API_WITH_SEARCH"
    LIVE_PRODUCT_TEST = "LIVE_PRODUCT_TEST"
    MANUAL_OBSERVATION = "MANUAL_OBSERVATION"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"


class GEOPublicationStatus(str, Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    PARTIAL = "PARTIAL"
    QA_FAILED = "QA_FAILED"
    READY_TO_PUBLISH = "READY_TO_PUBLISH"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class GEOAuditStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GEOMentionType(str, Enum):
    DIRECT_MENTION = "direct_mention"
    ENTITY_MENTION = "entity_mention"
    RECOMMENDATION = "recommendation"
    SHORTLIST_INCLUSION = "shortlist_inclusion"
    COMPARATIVE_INCLUSION = "comparative_inclusion"
    CITATION_ONLY = "citation_only"
    NEGATIVE_MENTION = "negative_mention"
    INCORRECT_REPRESENTATION = "incorrect_representation"


class GEOSourceOwnership(str, Enum):
    OWNED = "owned"
    EARNED = "earned"
    COMPETITOR = "competitor"
    INDEPENDENT = "independent"
    UNKNOWN = "unknown"


class GEOPromptCategory(str, Enum):
    CATEGORY_DISCOVERY = "category_discovery"
    BRAND_DISCOVERY = "brand_discovery"
    PRODUCT_DISCOVERY = "product_discovery"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    ALTERNATIVE_DISCOVERY = "alternative_discovery"
    PROBLEM_SOLVING = "problem_solving"
    PURCHASE_RESEARCH = "purchase_research"
    TRUST_AND_REPUTATION = "trust_and_reputation"
    FEATURE_DISCOVERY = "feature_discovery"
    LOCAL_DISCOVERY = "local_discovery"
    EXPERT_INFORMATION = "expert_information"


class GEOFindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class GEOTaskStatus(str, Enum):
    OPEN = "open"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    DEPLOYED = "deployed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED_VERIFICATION = "failed_verification"
    BLOCKED = "blocked"
    REGRESSED = "regressed"


class GEOEntityFactStatus(str, Enum):
    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"


class GEOExperimentStatus(str, Enum):
    DRAFT = "draft"
    BASELINE_CAPTURED = "baseline_captured"
    DEPLOYED = "deployed"
    RETESTED = "retested"
    CONCLUDED = "concluded"


# ─────────────────────────────────────────────────────────────────────────────
# Shared Base Record Metadata
# ─────────────────────────────────────────────────────────────────────────────


class GEOCanonicalRecord(BaseModel):
    model_config = {"protected_namespaces": ()}

    tenant_id: str = "default"
    audit_id: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    data_quality_state: GEODataQualityState = GEODataQualityState.NOT_TESTED
    methodology_version: str = GEO_METHODOLOGY_VERSION
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


# ─────────────────────────────────────────────────────────────────────────────
# 1–4. Audit, Scope, Platform, Model Version
# ─────────────────────────────────────────────────────────────────────────────


class GEOAuditScope(GEOCanonicalRecord):
    scope_id: str = Field(default_factory=lambda: _uid("gscope"))
    domain: str
    website_url: str
    brand_name: str
    brand_aliases: List[str] = Field(default_factory=list)
    industry: str = ""
    products: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=lambda: ["US"])
    languages: List[str] = Field(default_factory=lambda: ["en"])
    competitors: List[str] = Field(default_factory=list)
    target_audience: str = ""
    platforms_requested: List[str] = Field(
        default_factory=lambda: ["chatgpt", "gemini", "claude", "perplexity"]
    )
    repetitions: int = Field(default=1, ge=1, le=5)
    max_prompts: int = Field(default=24, ge=4, le=200)
    budget_usd: float = Field(default=5.0, ge=0.0)
    per_provider_budget_usd: Dict[str, float] = Field(default_factory=dict)
    allow_provider_fallback: bool = False
    pii_redaction_enabled: bool = True
    allow_live_provider_calls: bool = True
    data_quality_state: GEODataQualityState = GEODataQualityState.OBSERVED


class GEOAudit(GEOCanonicalRecord):
    audit_id: str = Field(default_factory=lambda: _uid("geo"))
    scope_id: Optional[str] = None
    domain: str
    website_url: str
    brand_name: str
    mode: str = "standard"  # quick | standard | deep | monitoring
    status: str = GEOAuditStatus.QUEUED.value
    publication_status: str = GEOPublicationStatus.DRAFT.value
    current_stage: str = "init"
    observed_performance_score: Optional[float] = None
    readiness_score: Optional[float] = None
    methodology_composite_score: Optional[float] = None
    qa_status: str = "pending"
    budget_usd: float = 5.0
    spent_usd: float = 0.0
    budget_paused: bool = False
    idempotency_key: Optional[str] = None
    platforms_configured: List[str] = Field(default_factory=list)
    platforms_tested: List[str] = Field(default_factory=list)
    platforms_unconfigured: List[str] = Field(default_factory=list)
    prompts_planned: int = 0
    prompts_executed: int = 0
    prompts_succeeded: int = 0
    prompts_failed: int = 0
    limitations: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProviderCapabilities(BaseModel):
    model_config = {"protected_namespaces": ()}

    platform_id: str
    display_name: str
    supported_models: List[str] = Field(default_factory=list)
    default_model: str = ""
    text_response: str = "Unknown"            # Yes | No | Unknown
    search_grounded_response: str = "Unknown"  # Yes | No | Unknown
    citation_metadata: str = "Unknown"        # Yes | No | Unknown
    tool_use_metadata: str = "Unknown"        # Yes | No | Unknown
    model_identification: str = "Unknown"     # Yes | No | Unknown
    geographic_controls: str = "Unknown"      # Yes | No | Unknown
    repeatable_test_config: str = "Partial"   # Yes | No | Partial
    cost_estimation: str = "Partial"          # Yes | No | Partial
    languages_supported: List[str] = Field(default_factory=lambda: ["en"])
    rate_limit_rpm: Optional[int] = None
    est_cost_per_1k_input_tokens_usd: float = 0.0
    est_cost_per_1k_output_tokens_usd: float = 0.0
    default_testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    unsupported_features: List[str] = Field(default_factory=list)
    auth_state: str = "NOT_CONFIGURED"        # CONNECTED | NOT_CONFIGURED | ERROR


class GEOPlatform(GEOCanonicalRecord):
    platform_id: str
    display_name: str
    provider_family: str = ""
    active_model: str = ""
    testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    capabilities: ProviderCapabilities
    prompts_attempted: int = 0
    prompts_succeeded: int = 0
    prompts_failed: int = 0
    mention_count: int = 0
    recommendation_count: int = 0
    citation_count: int = 0
    mention_rate_pct: Optional[float] = None
    recommendation_rate_pct: Optional[float] = None
    citation_rate_pct: Optional[float] = None
    sentiment_breakdown: Dict[str, int] = Field(default_factory=dict)
    accuracy_rate_pct: Optional[float] = None
    last_tested_at: Optional[str] = None
    total_cost_usd: float = 0.0
    limitations: List[str] = Field(default_factory=list)


class GEOModelVersion(GEOCanonicalRecord):
    version_id: str = Field(default_factory=lambda: _uid("gmod"))
    platform_id: str
    model_name: str
    provider_reported_version: Optional[str] = None
    testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    first_seen_at: str = Field(default_factory=_now_iso)
    last_seen_at: str = Field(default_factory=_now_iso)
    comparability_note: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# 5–9. Prompt Intelligence, Runs, Responses, Mentions, Citations
# ─────────────────────────────────────────────────────────────────────────────


class GEOTestPrompt(GEOCanonicalRecord):
    prompt_id: str = Field(default_factory=lambda: _uid("gprm"))
    question: str
    normalized_question: str = ""
    category: GEOPromptCategory = GEOPromptCategory.CATEGORY_DISCOVERY
    intent: str = "informational"  # informational | commercial | transactional | navigational | comparative | reputation | local
    is_branded: bool = False
    topic: str = ""
    target_brand: str = ""
    target_product: Optional[str] = None
    relevant_competitors: List[str] = Field(default_factory=list)
    market: str = "US"
    language: str = "en"
    importance: str = "medium"  # critical | high | medium | low
    testing_rationale: str = ""
    version: int = 1
    applicable_platforms: List[str] = Field(default_factory=list)
    repetitions: int = 1
    approval_status: str = "approved"  # draft | approved | excluded
    quality_flags: List[str] = Field(default_factory=list)
    data_quality_state: GEODataQualityState = GEODataQualityState.OBSERVED


class GEOPromptRun(GEOCanonicalRecord):
    run_id: str = Field(default_factory=lambda: _uid("grun"))
    prompt_id: str
    original_prompt: str
    normalized_prompt: str
    platform_id: str
    platform_name: str = ""
    model_name: str = ""
    model_version: str = ""
    testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    market: str = "US"
    language: str = "en"
    repetition_number: int = 1
    session_limitations: List[str] = Field(
        default_factory=lambda: [
            "Stateless API request; consumer chat personalization and memory are not replicated."
        ]
    )
    status: GEODataQualityState = GEODataQualityState.NOT_TESTED
    fallback_used: bool = False
    requested_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    error_message: Optional[str] = None
    executed_at: str = Field(default_factory=_now_iso)


class GEOResponse(GEOCanonicalRecord):
    response_id: str = Field(default_factory=lambda: _uid("gresp"))
    run_id: str
    prompt_id: str
    platform_id: str
    model_version: str = ""
    testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    response_text: str = ""
    response_hash: str = ""
    raw_citations: List[str] = Field(default_factory=list)
    tool_use_metadata: Dict[str, Any] = Field(default_factory=dict)
    snapshot_id: Optional[str] = None
    extracted_claims: List[Dict[str, Any]] = Field(default_factory=list)
    sentiment: str = "unmentioned"  # positive | neutral | negative | mixed | unmentioned
    brand_positioning: str = ""
    is_shortlisted: bool = False
    is_comparative: bool = False
    brand_mentioned: bool = False
    brand_recommended: bool = False
    brand_cited: bool = False
    inaccurate_claims_count: int = 0
    analysis_confidence: float = 0.85


class GEOMention(GEOCanonicalRecord):
    mention_id: str = Field(default_factory=lambda: _uid("gment"))
    response_id: str
    run_id: str
    prompt_id: str
    platform_id: str
    entity_name: str
    entity_kind: str = "brand"  # brand | product | competitor
    is_target_brand: bool = False
    mention_type: GEOMentionType = GEOMentionType.DIRECT_MENTION
    ordinal_position: Optional[int] = None
    sentiment: str = "neutral"  # positive | neutral | negative | mixed
    context_snippet: str = ""
    inaccuracy_note: Optional[str] = None
    confidence: float = 0.90


class GEOCitation(GEOCanonicalRecord):
    citation_id: str = Field(default_factory=lambda: _uid("gcit"))
    response_id: str
    run_id: str
    prompt_id: str
    platform_id: str
    cited_url: str
    resolved_url: Optional[str] = None
    canonical_url: Optional[str] = None
    domain: str
    publisher: str = ""
    source_ownership: GEOSourceOwnership = GEOSourceOwnership.UNKNOWN
    source_category: str = "general_web"
    page_subject: str = ""
    associated_claim: Optional[str] = None
    supports_claim: str = "not_checked"  # supported | partially_supported | unsupported | not_checked
    citation_position: int = 1
    published_at: Optional[str] = None
    source_updated_at: Optional[str] = None
    freshness_status: str = "unknown"  # fresh | aging | stale | unknown
    http_status: Optional[int] = None
    competitors_associated: List[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None
    url_valid: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# 10–11. Brand Entities, Page Readiness, External Sources
# ─────────────────────────────────────────────────────────────────────────────


class GEOEntity(GEOCanonicalRecord):
    entity_id: str = Field(default_factory=lambda: _uid("gent"))
    entity_type: str = "brand"  # brand | organization | product | service | person | location | social_profile | certification
    entity_name: str
    attribute: str
    value: Any
    source: str = "website_crawl"
    source_url: Optional[str] = None
    source_ownership: str = "owned"  # owned | third_party | unknown
    confidence: float = 0.85
    last_verified: Optional[str] = None
    fact_status: GEOEntityFactStatus = GEOEntityFactStatus.UNKNOWN
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    locked_from_ai_overwrite: bool = True
    conflicting_ai_observations: List[Dict[str, Any]] = Field(default_factory=list)


class GEOExternalSource(GEOCanonicalRecord):
    source_id: str = Field(default_factory=lambda: _uid("gsrc"))
    domain: str
    url: Optional[str] = None
    publisher: str = ""
    title: str = ""
    subject: str = ""
    source_category: str = "editorial"  # editorial | news | product_review | customer_review | community | association | research | directory | profile | expert
    is_relevant: bool = True
    is_independent: bool = True
    publisher_identifiable: bool = True
    is_current: Optional[bool] = None
    published_at: Optional[str] = None
    accurately_describes_brand: Optional[bool] = None
    discusses_products: bool = False
    supports_claims: List[str] = Field(default_factory=list)
    cited_in_ai_responses: bool = False
    citation_count: int = 0
    cites_competitors: bool = False
    competitors_present: List[str] = Field(default_factory=list)
    brand_present: bool = False
    evidence_of_relevance: str = ""
    potential_contribution: str = ""
    outreach_strategy: str = ""
    restrictions_and_risks: str = "Follow editorial independence; never pay for or fabricate reviews or mentions."
    opportunity_status: str = "identified"  # identified | prioritized | in_progress | completed | dismissed
    discovery_date: str = Field(default_factory=_now_iso)


class GEOPageReadiness(GEOCanonicalRecord):
    page_id: str = Field(default_factory=lambda: _uid("gpage"))
    url: str
    page_type: str = "general"  # homepage | about | product | service | category | pricing | comparison | case_study | docs | faq | editorial | contact | legal
    http_status: Optional[int] = None
    title: str = ""
    main_topic: str = ""
    relevant_audience: str = ""
    word_count: int = 0
    clarity_score: Optional[float] = None
    completeness_score: Optional[float] = None
    specificity_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    structure_score: Optional[float] = None
    extractability_score: Optional[float] = None
    differentiation_score: Optional[float] = None
    freshness_score: Optional[float] = None
    trust_score: Optional[float] = None
    consistency_score: Optional[float] = None
    overall_readiness_score: Optional[float] = None
    entity_coverage: List[str] = Field(default_factory=list)
    schema_types: List[str] = Field(default_factory=list)
    missing_questions: List[str] = Field(default_factory=list)
    content_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    has_definitions: bool = False
    has_feature_table: bool = False
    has_comparison_table: bool = False
    has_pricing_info: bool = False
    has_faq_section: bool = False
    has_author_attribution: bool = False
    has_updated_date: bool = False
    raw_html_snapshot_id: Optional[str] = None
    extracted_text_preview: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# 12–17. Findings, Recommendations, Remediation, Verification, Experiments, Snapshots
# ─────────────────────────────────────────────────────────────────────────────


class GEOFinding(GEOCanonicalRecord):
    finding_id: str = Field(default_factory=lambda: _uid("GEO"))
    category: str  # ai_visibility | citation_intelligence | entity_consistency | content_quality | technical_readiness | external_reputation | competitive_intelligence | market_intent
    department: str = "I"
    agent_id: str = "geo_orchestrator"
    title: str
    description: str
    root_cause: str = ""
    root_cause_group: str = ""
    affected_entities: List[str] = Field(default_factory=list)
    affected_urls: List[str] = Field(default_factory=list)
    affected_prompts: List[str] = Field(default_factory=list)
    affected_platforms: List[str] = Field(default_factory=list)
    competitor_references: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    severity: GEOFindingSeverity = GEOFindingSeverity.MEDIUM
    confidence: Optional[float] = None
    business_impact: Optional[str] = None
    recommendation: str = ""
    acceptance_criteria: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    is_hypothesis: bool = False
    status: str = "open"  # open | in_progress | resolved | verified | superseded


class GEORecommendation(GEOCanonicalRecord):
    recommendation_id: str = Field(default_factory=lambda: _uid("grec"))
    finding_ids: List[str] = Field(default_factory=list)
    dimension: str = "content_quality"
    title: str
    rationale: str
    expected_impact: str = "medium"  # high | medium | low
    effort: str = "medium"           # low | medium | high
    confidence: Optional[float] = None
    priority_score: float = 50.0
    owner_department: str = "Content & GEO"
    action_steps: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class GEORemediationTask(GEOCanonicalRecord):
    task_id: str = Field(default_factory=lambda: _uid("gtask"))
    pack_id: Optional[str] = None
    finding_ids: List[str] = Field(default_factory=list)
    recommendation_ids: List[str] = Field(default_factory=list)
    title: str
    root_cause: str = ""
    deliverable_section: str = "website_content_plan"
    affected_pages: List[str] = Field(default_factory=list)
    affected_prompts: List[str] = Field(default_factory=list)
    affected_platforms: List[str] = Field(default_factory=list)
    affected_entities: List[str] = Field(default_factory=list)
    affected_sources: List[str] = Field(default_factory=list)
    proposed_change: str = ""
    implementation_instructions: str = ""
    code_or_copy_patch: Optional[str] = None
    owner: str = "Unassigned"
    department: str = "Engineering"
    dependencies: List[str] = Field(default_factory=list)
    conflicts_with: List[str] = Field(default_factory=list)
    effort: str = "medium"  # low | medium | high
    priority: str = "P1"    # P0 | P1 | P2 | P3
    risk: str = "low"       # low | medium | high
    approval_status: str = "pending"  # pending | approved | rejected
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    status: str = GEOTaskStatus.OPEN.value
    deployment_ref: Optional[str] = None
    deployed_by: Optional[str] = None
    deployed_at: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    before_evidence: Dict[str, Any] = Field(default_factory=dict)
    after_evidence: Dict[str, Any] = Field(default_factory=dict)
    verification_id: Optional[str] = None
    implementation_verified: Optional[bool] = None
    outcome_improved: Optional[str] = None  # OBSERVED | NOT_OBSERVED | REGRESSED | NOT_TESTED


class GEORemediationPack(GEOCanonicalRecord):
    pack_id: str = Field(default_factory=lambda: _uid("gpack"))
    published_after_consolidation: bool = True
    executive_summary: str = ""
    root_cause_groups: List[Dict[str, Any]] = Field(default_factory=list)
    deliverables: Dict[str, Any] = Field(default_factory=dict)  # all 13 deliverables
    department_packages: Dict[str, List[str]] = Field(default_factory=dict)
    dependency_edges: List[Dict[str, str]] = Field(default_factory=list)
    conflict_notes: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[GEORemediationTask] = Field(default_factory=list)
    remaining_risks: List[Dict[str, Any]] = Field(default_factory=list)


class GEOVerification(GEOCanonicalRecord):
    verification_id: str = Field(default_factory=lambda: _uid("gver"))
    task_id: str
    verified_by: str
    verified_at: str = Field(default_factory=_now_iso)
    # Strict separation: implementation verified != AI outcome improved
    implementation_verified: bool = False
    content_update_verified: Optional[bool] = None
    structured_data_verified: Optional[bool] = None
    entity_consistency_verified: Optional[bool] = None
    external_source_checked: Optional[bool] = None
    outcome_improved: str = "NOT_TESTED"  # OBSERVED | NOT_OBSERVED | REGRESSED | NOT_TESTED
    brand_inclusion_improved: str = "NOT_TESTED"
    citation_frequency_improved: str = "NOT_TESTED"
    regression_detected: bool = False
    regression_details: List[str] = Field(default_factory=list)
    before_after_comparison: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    acceptance_criteria_results: List[Dict[str, Any]] = Field(default_factory=list)
    retest_run_ids: List[str] = Field(default_factory=list)
    retest_metadata: Dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[str] = Field(default_factory=list)
    unavailable_tests: List[str] = Field(default_factory=list)
    overall_status: str = "partial"  # verified | implementation_verified_no_outcome_change | failed | regressed | partial


class GEOExperiment(GEOCanonicalRecord):
    experiment_id: str = Field(default_factory=lambda: _uid("gexp"))
    title: str
    hypothesis: str
    target_urls: List[str] = Field(default_factory=list)
    target_entities: List[str] = Field(default_factory=list)
    baseline_prompt_suite_version: int = 1
    baseline_snapshot_id: Optional[str] = None
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)
    change_description: str = ""
    deployment_ref: Optional[str] = None
    retest_snapshot_id: Optional[str] = None
    retest_metrics: Dict[str, Any] = Field(default_factory=dict)
    platforms_tested: List[str] = Field(default_factory=list)
    repetitions: int = 1
    observed_delta: Dict[str, Any] = Field(default_factory=dict)
    confidence_note: str = ""
    causation_disclaimer: str = (
        "Before-and-after differences represent observed changes under repeated testing, not proof of causation. "
        "AI platform updates, response stochasticity, retrieval changes, and external web events may explain observed deltas."
    )
    limitations: List[str] = Field(default_factory=list)
    status: str = GEOExperimentStatus.DRAFT.value


class GEOSnapshot(GEOCanonicalRecord):
    snapshot_id: str = Field(default_factory=lambda: _uid("gsnap"))
    snapshot_type: str  # raw_html | ai_response | prompt_suite | citation_graph | report_pdf | report_html | verification
    url: Optional[str] = None
    content_hash: str
    storage_uri: str
    byte_size: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    captured_at: str = Field(default_factory=_now_iso)
    data_quality_state: GEODataQualityState = GEODataQualityState.OBSERVED


# ─────────────────────────────────────────────────────────────────────────────
# Operational Models: Agent Output, Dual Scorecard, Monitoring, Reports, QA, Connectors
# ─────────────────────────────────────────────────────────────────────────────


class GEOAgentOutput(BaseModel):
    model_config = {"protected_namespaces": ()}

    agent_id: str
    department: str
    status: str = "completed"  # completed | partial | not_tested | failed
    audit_id: str
    findings: List[GEOFinding] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    limitations: List[str] = Field(default_factory=list)
    methodology_version: str = GEO_METHODOLOGY_VERSION
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)


class GEODimensionScoreCard(BaseModel):
    dimension_key: str
    dimension_name: str
    scorecard_group: str  # observed_performance | readiness_optimization
    proposed_weight_pct: float
    score: Optional[float] = None
    grade: str = "Unmeasured"
    status: GEODataQualityState = GEODataQualityState.NOT_TESTED
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    sample_size: int = 0
    evidence_ids: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class GEOCoverageMetadata(BaseModel):
    tested_platforms: List[str] = Field(default_factory=list)
    unconfigured_platforms: List[str] = Field(default_factory=list)
    successful_prompt_executions: int = 0
    failed_prompt_executions: int = 0
    total_planned_prompts: int = 0
    branded_prompts_tested: int = 0
    non_branded_prompts_tested: int = 0
    repeat_test_count: int = 1
    markets_covered: List[str] = Field(default_factory=list)
    languages_covered: List[str] = Field(default_factory=list)
    connector_availability: Dict[str, str] = Field(default_factory=dict)
    data_freshness: str = Field(default_factory=_now_iso)
    evidence_confidence: Optional[float] = None
    methodology_version: str = GEO_METHODOLOGY_VERSION


class GEODualScorecard(BaseModel):
    model_config = {"protected_namespaces": ()}

    audit_id: str
    methodology_version: str = GEO_METHODOLOGY_VERSION
    methodology_disclosure: str = (
        "Weights (20/20/15/15/15/10/5) represent Dristik's proposed product methodology and are not an "
        "official search-engine or AI-provider formula. Observed GEO Performance and GEO Readiness & Optimization "
        "are kept strictly separate so readiness is never mistaken for observed AI visibility."
    )
    # Scorecard 1: Observed GEO Performance
    observed_performance_score: Optional[float] = None
    observed_performance_grade: str = "Unmeasured"
    observed_performance_status: GEODataQualityState = GEODataQualityState.NOT_CONFIGURED
    observed_metrics: Dict[str, Any] = Field(default_factory=dict)
    # Scorecard 2: GEO Readiness & Optimization
    readiness_score: Optional[float] = None
    readiness_grade: str = "Unmeasured"
    readiness_status: GEODataQualityState = GEODataQualityState.NOT_TESTED
    readiness_metrics: Dict[str, Any] = Field(default_factory=dict)
    # Combined methodology reference (only populated when BOTH scorecards have eligible measurements)
    methodology_composite_score: Optional[float] = None
    methodology_composite_grade: str = "Unmeasured"
    active_weight_pct: float = 0.0
    dimensions: List[GEODimensionScoreCard] = Field(default_factory=list)
    coverage: GEOCoverageMetadata = Field(default_factory=GEOCoverageMetadata)


class GEOMonitoringSchedule(GEOCanonicalRecord):
    schedule_id: str = Field(default_factory=lambda: _uid("gmon"))
    domain: str
    brand_name: str = ""
    cadence: str = "weekly"  # daily | weekly | monthly
    platforms: List[str] = Field(default_factory=lambda: ["chatgpt", "gemini", "claude", "perplexity"])
    prompt_suite_version: int = 1
    max_budget_per_run_usd: float = 2.0
    enabled: bool = True
    last_run_at: Optional[str] = None
    last_audit_id: Optional[str] = None
    checks_enabled: List[str] = Field(
        default_factory=lambda: [
            "new_brand_mentions",
            "lost_brand_mentions",
            "new_citations",
            "lost_citations",
            "brand_misinformation",
            "competitor_visibility_shifts",
            "external_references",
            "content_freshness",
            "provider_availability",
        ]
    )


class GEOMonitoringAlert(GEOCanonicalRecord):
    alert_id: str = Field(default_factory=lambda: _uid("galrt"))
    schedule_id: Optional[str] = None
    domain: str
    alert_type: str  # new_mention | lost_mention | new_citation | lost_citation | misinformation | competitor_shift | new_external_source | content_freshness | provider_unavailable
    severity: GEOFindingSeverity = GEOFindingSeverity.MEDIUM
    title: str
    description: str
    platform_id: Optional[str] = None
    prompt_id: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    acknowledged: bool = False


class GEOReport(GEOCanonicalRecord):
    report_id: str = Field(default_factory=lambda: _uid("grep"))
    domain: str
    profile: str = "complete_audit_book"
    format: str = "html"  # html | json | pdf
    title: str = ""
    snapshot_id: Optional[str] = None
    sections_included: List[str] = Field(default_factory=list)
    sections_omitted: List[Dict[str, str]] = Field(default_factory=list)
    qa_passed: bool = False
    qa_summary: Dict[str, Any] = Field(default_factory=dict)
    storage_uri: Optional[str] = None
    content_hash: Optional[str] = None
    publication_status: str = GEOPublicationStatus.DRAFT.value


class GEOProviderConnection(GEOCanonicalRecord):
    connection_id: str = Field(default_factory=lambda: _uid("gconn"))
    platform_id: str
    display_name: str
    connected: bool = False
    auth_status: str = "NOT_CONFIGURED"  # CONNECTED | NOT_CONFIGURED | AUTH_FAILED | EXPIRED
    default_model: str = ""
    testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    capabilities: Optional[ProviderCapabilities] = None
    last_successful_sync: Optional[str] = None
    last_error: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    data_freshness: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    cost_implication_note: str = ""
    reauthorization_required: bool = False
    has_stored_secret: bool = False  # Never expose ciphertext or plaintext to frontend


class GEOQACheckResult(BaseModel):
    check_id: str
    check_name: str
    passed: bool
    severity: str = "blocking"  # blocking | warning
    details: str = ""


class GEOQAReport(BaseModel):
    audit_id: str
    publication_status: str = GEOPublicationStatus.DRAFT.value
    qa_status: str = "passed"  # passed | partial | failed
    blocking_failures: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checks: List[GEOQACheckResult] = Field(default_factory=list)
    cross_system_consistency: Dict[str, bool] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=_now_iso)
    methodology_version: str = GEO_METHODOLOGY_VERSION
