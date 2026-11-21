"""Canonical CRO (Conversion Rate Optimization) Enterprise Domain Models.

Powers the backend orchestrator, 10 specialist departments, 22-entity relational store,
3-scorecard engine, consolidated remediation center, independent verification engine,
statistical experimentation engine, monitoring, 65-section / 14-profile report engine,
REST/SSE API, and frontend CRO workspace from one authoritative contract.

Epistemic integrity rule:
Every observation carries an explicit EvidenceSourceType so confirmed technical defects,
browser test failures, measured analytics behavior, research findings, heuristic
assessments, untested hypotheses, and valid experiment results are never conflated.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


CRO_METHODOLOGY_VERSION = "dristik_cro_v2.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EvidenceSourceType(str, Enum):
    DIRECT_TECHNICAL = "direct_technical"           # Confirmed technical defect
    BROWSER_TEST = "browser_test"                   # Confirmed functional problem in tested conditions
    ANALYTICS_OBSERVATION = "analytics_observation" # Measured funnel behavior
    USER_RESEARCH = "user_research"                 # Research-backed usability issue
    HEURISTIC_OBSERVATION = "heuristic_observation" # Expert assessment
    AI_HYPOTHESIS = "ai_hypothesis"                 # Hypothesis requiring validation
    EXPERIMENT_RESULT = "experiment_result"         # Experiment-supported outcome


EVIDENCE_CLAIM_BOUNDARIES: Dict[str, str] = {
    EvidenceSourceType.DIRECT_TECHNICAL.value: "Confirmed technical defect",
    EvidenceSourceType.BROWSER_TEST.value: "Confirmed functional problem in tested conditions",
    EvidenceSourceType.ANALYTICS_OBSERVATION.value: "Measured funnel behavior",
    EvidenceSourceType.USER_RESEARCH.value: "Research-backed usability issue",
    EvidenceSourceType.HEURISTIC_OBSERVATION.value: "Expert assessment (not proof of measured conversion loss)",
    EvidenceSourceType.AI_HYPOTHESIS.value: "Hypothesis requiring validation",
    EvidenceSourceType.EXPERIMENT_RESULT.value: "Experiment-supported outcome",
}


class CROBusinessModelType(str, Enum):
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    B2B_LEAD_GEN = "b2b_lead_gen"
    B2C_LEAD_GEN = "b2c_lead_gen"
    PROFESSIONAL_SERVICES = "professional_services"
    LOCAL_SERVICES = "local_services"
    MARKETPLACE = "marketplace"
    SUBSCRIPTION = "subscription"
    PUBLISHER_CONTENT = "publisher_content"
    BOOKING_RESERVATION = "booking_reservation"
    EDUCATION_COURSES = "education_courses"
    FINANCIAL_SERVICES = "financial_services"
    UNKNOWN = "unknown"


class CROPageType(str, Enum):
    HOMEPAGE = "homepage"
    LANDING_PAGE = "landing_page"
    PRODUCT_PAGE = "product_page"
    SERVICE_PAGE = "service_page"
    PRICING_PAGE = "pricing_page"
    CATEGORY_PAGE = "category_page"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"
    CHECKOUT = "checkout"
    AUTH_REGISTRATION = "auth_registration"
    DEMO_CONSULTATION = "demo_consultation"
    CONTACT = "contact"
    BOOKING = "booking"
    SUPPORT_FAQ = "support_faq"
    TRUST_POLICY = "trust_policy"
    GENERAL = "general"


class CROSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class CROAuditStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CROFindingStatus(str, Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    IN_REMEDIATION = "in_remediation"
    AWAITING_VERIFICATION = "awaiting_verification"
    VERIFIED_FIXED = "verified_fixed"
    REOPENED = "reopened"
    DISMISSED = "dismissed"


class CROTaskStatus(str, Enum):
    BACKLOG = "backlog"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    DEPLOYED = "deployed"
    AWAITING_VERIFICATION = "awaiting_verification"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    REOPENED = "reopened"


class CROExperimentStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    STOPPED_GUARDRAIL = "stopped_guardrail"
    ROLLED_BACK = "rolled_back"


class CROProvenanceMixin(BaseModel):
    tenant_id: str = "default"
    audit_id: Optional[str] = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    journey_id: Optional[str] = None
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)
    status: str = "active"
    methodology_version: str = CRO_METHODOLOGY_VERSION
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    device_segments: List[str] = Field(default_factory=lambda: ["desktop", "mobile"])
    audience_segments: List[str] = Field(default_factory=list)
    data_freshness: str = Field(default_factory=_utc_now)
    provenance: str = "dristik_cro_engine"


# ─────────────────────────────────────────────────────────────────────────────
# 22 Canonical CRO Entities
# ─────────────────────────────────────────────────────────────────────────────


class CROBusinessProfile(CROProvenanceMixin):
    profile_id: str = Field(default_factory=lambda: _new_id("cro_bp"))
    domain: str
    website_url: str
    business_name: Optional[str] = None
    business_type: CROBusinessModelType = CROBusinessModelType.UNKNOWN
    products_and_services: List[str] = Field(default_factory=list)
    target_customers: Optional[str] = None
    geographic_markets: List[str] = Field(default_factory=list)
    pricing_model: str = "unknown"
    primary_conversion: str = "unknown"
    secondary_conversions: List[str] = Field(default_factory=list)
    average_order_value: Optional[float] = None
    currency: Optional[str] = None
    revenue_model: str = "unknown"
    lead_qualification_criteria: List[str] = Field(default_factory=list)
    main_acquisition_channels: List[str] = Field(default_factory=list)
    known_competitors: List[str] = Field(default_factory=list)
    analytics_configuration: Dict[str, Any] = Field(default_factory=dict)
    important_pages: List[str] = Field(default_factory=list)
    known_conversion_problems: List[str] = Field(default_factory=list)
    unknown_fields: List[str] = Field(default_factory=list)
    inference_basis: str = "User configuration and crawled evidence"


class CROGoal(CROProvenanceMixin):
    goal_id: str = Field(default_factory=lambda: _new_id("cro_goal"))
    profile_id: Optional[str] = None
    name: str
    goal_type: str = "primary"  # primary | secondary | micro
    business_model: CROBusinessModelType = CROBusinessModelType.UNKNOWN
    target_action: str
    target_urls: List[str] = Field(default_factory=list)
    analytics_event_name: Optional[str] = None
    required_event_params: List[str] = Field(default_factory=list)
    value_per_conversion: Optional[float] = None
    qualification_criteria: Optional[str] = None
    validation_status: str = "unvalidated"  # verified | failed | unavailable | unvalidated
    validation_notes: Optional[str] = None


class CROAudience(CROProvenanceMixin):
    audience_id: str = Field(default_factory=lambda: _new_id("cro_aud"))
    profile_id: Optional[str] = None
    name: str
    segment_type: str = "primary_buyer"  # primary_buyer | evaluator | returning | mobile_first | enterprise
    intent_level: str = "unknown"        # high_intent | evaluative | exploratory | unknown
    key_objections: List[str] = Field(default_factory=list)
    decision_drivers: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    measured_share_pct: Optional[float] = None


class CROAudit(CROProvenanceMixin):
    audit_id: str = Field(default_factory=lambda: _new_id("cro_audit"))
    domain: str
    target_url: str
    profile_id: Optional[str] = None
    mode: str = "standard"  # quick | standard | deep | continuous
    status: str = CROAuditStatus.QUEUED.value
    current_stage: str = "init"
    safe_mode: bool = True
    browser_testing_enabled: bool = True
    analytics_connected: bool = False
    experience_score: Optional[float] = None
    measurement_score: Optional[float] = None
    pages_audited: int = 0
    findings_count: int = 0
    critical_findings_count: int = 0
    scope_coverage_pct: Optional[float] = None
    test_coverage_pct: Optional[float] = None
    evidence_coverage_pct: Optional[float] = None
    qa_status: str = "pending"  # pending | passed | passed_with_warnings | failed
    limitations: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CROPage(CROProvenanceMixin):
    page_id: str = Field(default_factory=lambda: _new_id("cro_page"))
    url: str
    page_type: CROPageType = CROPageType.GENERAL
    business_purpose: str = ""
    conversion_objective: str = ""
    target_audience: str = "unknown"
    journey_position: str = "discovery"
    importance: str = "medium"  # critical | high | medium | low
    http_status: Optional[int] = None
    title: Optional[str] = None
    h1: Optional[str] = None
    subheadline: Optional[str] = None
    word_count: int = 0
    rendered_dom_verified: bool = False
    device_coverage: List[str] = Field(default_factory=list)
    functional_test_status: str = "not_tested"  # passed | failed | partial | not_tested
    primary_cta: Optional[str] = None
    cta_count: int = 0
    forms_count: int = 0
    ux_findings_count: int = 0
    ui_findings_count: int = 0
    analytics_coverage: str = "unmeasured"
    page_experience_score: Optional[float] = None
    remediation_status: str = "open"
    raw_html_snapshot_id: Optional[str] = None
    rendered_dom_snapshot_id: Optional[str] = None
    screenshot_snapshot_ids: Dict[str, str] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    traffic_source_context: Dict[str, Any] = Field(default_factory=dict)


class CROPageElement(CROProvenanceMixin):
    element_id: str = Field(default_factory=lambda: _new_id("cro_el"))
    page_id: str
    url: str
    element_category: str  # cta | form | navigation | headline | trust | pricing | interactive | modal
    element_type: str      # button | a | form | input | nav | h1 | badge | dialog
    section: str = "body"  # header | hero | body | sidebar | footer | sticky | modal
    selector: str = ""
    text: str = ""
    destination: Optional[str] = None
    cta_hierarchy: Optional[str] = None  # primary | secondary | tertiary | navigation | trust_support
    intent_category: Optional[str] = None  # high_intent | exploratory | passive_generic
    visible: Optional[bool] = None
    clickable: Optional[bool] = None
    above_the_fold: Optional[bool] = None
    accessible_name: Optional[str] = None
    device: str = "desktop"
    bounding_box: Optional[Dict[str, float]] = None
    contrast_ratio: Optional[float] = None
    interaction_result: str = "not_tested"
    related_goal_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class CROJourneyStep(CROProvenanceMixin):
    step_id: str = Field(default_factory=lambda: _new_id("cro_step"))
    journey_id: str
    step_order: int
    name: str
    stage: str  # entry | discovery | evaluation | trust | pricing | action | checkout | confirmation
    page_id: Optional[str] = None
    url: Optional[str] = None
    component_ref: Optional[str] = None
    expected_interaction: str = ""
    dependencies: List[str] = Field(default_factory=list)
    possible_failure_states: List[str] = Field(default_factory=list)
    analytics_event_name: Optional[str] = None
    # Two strictly separated statuses per Phase 28
    technical_status: str = "not_tested"     # passed | failed | warning | not_tested
    technical_notes: str = ""
    behavioral_status: str = "unmeasured"    # measured_healthy | measured_high_dropoff | unmeasured
    behavioral_metrics: Dict[str, Any] = Field(default_factory=dict)


class CROJourney(CROProvenanceMixin):
    journey_id: str = Field(default_factory=lambda: _new_id("cro_jrn"))
    name: str
    business_model: CROBusinessModelType = CROBusinessModelType.UNKNOWN
    goal_id: Optional[str] = None
    entry_points: List[str] = Field(default_factory=list)
    steps: List[CROJourneyStep] = Field(default_factory=list)
    device_scope: List[str] = Field(default_factory=lambda: ["desktop", "mobile"])
    technical_health: str = "not_tested"  # healthy | broken | degraded | not_tested
    behavioral_health: str = "unmeasured" # measured | unmeasured
    measured_completion_rate: Optional[float] = None
    disclosure: str = (
        "Crawl and browser testing validate functional path integrity; actual visitor flow frequency "
        "and abandonment require connected analytics or user research."
    )


class CROInteractionTest(CROProvenanceMixin):
    test_id: str = Field(default_factory=lambda: _new_id("cro_test"))
    page_id: Optional[str] = None
    url: str
    scenario: str  # viewport_render | navigation | cta_click | form_validation | modal | interactive | checkout_sandbox
    viewport_name: str = "desktop"
    viewport_width: int = 1440
    viewport_height: int = 900
    browser: str = "chromium"
    browser_version: Optional[str] = None
    execution_mode: str = "playwright_live"  # playwright_live | static_dom_only
    safe_mode: bool = True
    auth_context: str = "logged_out"
    element_selector: Optional[str] = None
    interaction_sequence: List[str] = Field(default_factory=list)
    passed: Optional[bool] = None
    result_status: str = "not_tested"  # passed | failed | blocked_safe_mode | skipped | error | static_only
    console_errors: List[str] = Field(default_factory=list)
    network_failures: List[Dict[str, Any]] = Field(default_factory=list)
    screenshot_snapshot_id: Optional[str] = None
    dom_snapshot_id: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    observations: List[str] = Field(default_factory=list)


class CROAnalyticsEvent(CROProvenanceMixin):
    event_record_id: str = Field(default_factory=lambda: _new_id("cro_evt"))
    connector_type: str = "ga4"
    event_name: str
    trigger_description: str = ""
    required_parameters: List[str] = Field(default_factory=list)
    observed_parameters: List[str] = Field(default_factory=list)
    goal_id: Optional[str] = None
    event_count: Optional[int] = None
    unique_users: Optional[int] = None
    revenue_value: Optional[float] = None
    currency: Optional[str] = None
    date_range: Optional[str] = None
    validation_status: str = "unavailable"  # verified | failed | unavailable | duplicate_detected | missing_params
    data_quality_flags: List[str] = Field(default_factory=list)


class CROFunnelStep(CROProvenanceMixin):
    funnel_step_id: str = Field(default_factory=lambda: _new_id("cro_fstep"))
    funnel_id: str
    step_order: int
    step_name: str
    event_name: Optional[str] = None
    url_pattern: Optional[str] = None
    counting_unit: str = "unique_users"  # unique_users | sessions | form_starts | checkouts
    eligible_count: Optional[int] = None
    progressing_count: Optional[int] = None
    step_conversion_rate: Optional[float] = None
    step_abandonment_rate: Optional[float] = None
    measurement_status: str = "data_unavailable"  # measured | data_unavailable | invalid_units
    linked_finding_ids: List[str] = Field(default_factory=list)


class CROFunnel(CROProvenanceMixin):
    funnel_id: str = Field(default_factory=lambda: _new_id("cro_fun"))
    name: str
    business_model: CROBusinessModelType = CROBusinessModelType.UNKNOWN
    goal_id: Optional[str] = None
    source: str = "not_connected"
    date_range: Optional[str] = None
    counting_unit: str = "unique_users"
    attribution_window: Optional[str] = None
    segment: str = "all_visitors"
    steps: List[CROFunnelStep] = Field(default_factory=list)
    overall_completion_rate: Optional[float] = None
    data_completeness: str = "unmeasured"  # complete | partial | unmeasured


class CROFinding(CROProvenanceMixin):
    finding_id: str = Field(default_factory=lambda: _new_id("CRO"))
    category: str
    subcategory: str = ""
    department: str = ""
    agent_id: str = ""
    title: str
    description: str
    root_cause: str = ""
    root_cause_group_id: Optional[str] = None
    goal_id: Optional[str] = None
    affected_urls: List[str] = Field(default_factory=list)
    affected_elements: List[str] = Field(default_factory=list)
    affected_journeys: List[str] = Field(default_factory=list)
    affected_devices: List[str] = Field(default_factory=lambda: ["desktop", "mobile"])
    evidence_ids: List[str] = Field(default_factory=list)
    source_type: EvidenceSourceType = EvidenceSourceType.HEURISTIC_OBSERVATION
    claim_boundary: str = ""
    severity: CROSeverity = CROSeverity.MEDIUM
    measurement_status: str = "observed_heuristic"  # measured | confirmed_defect | observed_heuristic | hypothesis
    business_impact: Optional[str] = None
    recommendation: str = ""
    implementation_instructions: str = ""
    owner_role: str = "Product / Engineering"
    effort: str = "medium"  # low | medium | high
    priority_score: float = 50.0
    acceptance_criteria: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    status: str = CROFindingStatus.OPEN.value


class CROHypothesis(CROProvenanceMixin):
    hypothesis_id: str = Field(default_factory=lambda: _new_id("cro_hyp"))
    finding_ids: List[str] = Field(default_factory=list)
    title: str
    change_experience: str
    target_audience: str
    desired_action: str
    evidence_rationale: str
    primary_metric: str
    guardrail_metrics: List[str] = Field(default_factory=lambda: ["Qualified lead rate", "Revenue", "Checkout errors", "Page performance"])
    statement: str = ""
    expected_mechanism: str = ""
    testability: str = "ab_test"  # ab_test | multivariate | before_after_controlled | direct_defect_fix


class CRORecommendation(CROProvenanceMixin):
    recommendation_id: str = Field(default_factory=lambda: _new_id("cro_rec"))
    finding_ids: List[str] = Field(default_factory=list)
    category: str
    title: str
    summary: str
    original_state: Optional[str] = None
    proposed_state: Optional[str] = None
    supporting_facts: List[str] = Field(default_factory=list)
    risks_and_assumptions: List[str] = Field(default_factory=list)
    implementation_instructions: str = ""
    owner_role: str = "Engineering"
    effort: str = "medium"
    priority_rank: int = 2
    requires_copy_approval: bool = False
    approval_status: str = "pending"  # pending | approved | rejected
    acceptance_criteria: List[str] = Field(default_factory=list)


class CROVariant(CROProvenanceMixin):
    variant_id: str = Field(default_factory=lambda: _new_id("cro_var"))
    experiment_id: str
    name: str
    is_control: bool = False
    traffic_allocation_pct: float = 50.0
    description: str = ""
    changes_spec: Dict[str, Any] = Field(default_factory=dict)


class CROExperimentResult(CROProvenanceMixin):
    result_id: str = Field(default_factory=lambda: _new_id("cro_expres"))
    experiment_id: str
    control_visitors: int = 0
    control_conversions: int = 0
    variant_visitors: int = 0
    variant_conversions: int = 0
    control_rate: Optional[float] = None
    variant_rate: Optional[float] = None
    relative_lift: Optional[float] = None
    absolute_lift: Optional[float] = None
    z_score: Optional[float] = None
    p_value: Optional[float] = None
    adjusted_p_value: Optional[float] = None
    confidence_interval_95: Optional[List[float]] = None
    is_statistically_significant: bool = False
    sample_size_met: bool = False
    duration_met: bool = False
    srm_p_value: Optional[float] = None
    srm_detected: bool = False
    peeking_warning: bool = False
    guardrail_results: Dict[str, Any] = Field(default_factory=dict)
    guardrail_breached: bool = False
    segment_breakdowns: Dict[str, Any] = Field(default_factory=dict)
    decision: str = "inconclusive"  # winner | loser | inconclusive | invalid_srm | stopped_guardrail
    decision_rationale: str = ""


class CROExperiment(CROProvenanceMixin):
    experiment_id: str = Field(default_factory=lambda: _new_id("CRO-EXP"))
    hypothesis_id: Optional[str] = None
    finding_ids: List[str] = Field(default_factory=list)
    title: str
    experiment_type: str = "ab_test"  # ab_test | multivariate | landing_page | headline | cta | form | checkout | pricing | trust | personalization
    hypothesis_statement: str
    target_audience: str = "All eligible visitors"
    eligibility_rules: List[str] = Field(default_factory=list)
    randomization_method: str = "User-level deterministic hash split (50/50)"
    primary_metric: str
    secondary_metrics: List[str] = Field(default_factory=list)
    guardrail_metrics: List[str] = Field(default_factory=lambda: ["Revenue", "Qualified lead rate", "Checkout errors", "Page performance", "Accessibility"])
    baseline_rate_input: Optional[float] = None
    baseline_is_measured: bool = False
    minimum_detectable_effect: float = 0.15
    alpha: float = 0.05
    power: float = 0.80
    required_sample_per_variant: int = 0
    total_required_sample: int = 0
    planned_duration_days: int = 14
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    decision_criteria: str = "Two-tailed p < 0.05, required sample & minimum 14-day duration met, no SRM (p >= 0.001), zero guardrail breaches."
    owner: str = "Growth Lead"
    approval_status: str = "pending"  # pending | approved | rejected
    approved_by: Optional[str] = None
    status: str = CROExperimentStatus.DRAFT.value
    variants: List[CROVariant] = Field(default_factory=list)
    latest_result: Optional[CROExperimentResult] = None
    data_quality_checks: List[str] = Field(default_factory=list)


class CRORemediationTask(CROProvenanceMixin):
    task_id: str = Field(default_factory=lambda: _new_id("CRO-TASK"))
    pack_id: Optional[str] = None
    root_cause_group: str = ""
    title: str
    linked_finding_ids: List[str] = Field(default_factory=list)
    affected_urls: List[str] = Field(default_factory=list)
    affected_components: List[str] = Field(default_factory=list)
    affected_journeys: List[str] = Field(default_factory=list)
    affected_devices: List[str] = Field(default_factory=lambda: ["desktop", "mobile"])
    business_objective: str = ""
    deliverable_section: str = ""
    proposed_change: str = ""
    original_copy_or_design: Optional[str] = None
    updated_copy_or_design: Optional[str] = None
    implementation_instructions: str = ""
    owner: str = "Unassigned"
    department: str = "Engineering"  # Engineering | Design | Marketing | Product | Analytics | Growth
    dependencies: List[str] = Field(default_factory=list)
    conflicting_task_ids: List[str] = Field(default_factory=list)
    effort_estimate: str = "medium"  # low | medium | high
    priority: str = "P1"             # P0 | P1 | P2 | P3
    roadmap_window: str = "days_30"  # days_30 | days_60 | days_90
    due_date: Optional[str] = None
    approval_status: str = "pending"  # pending | approved | rejected
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    deployment_ref: Optional[str] = None
    deployed_by: Optional[str] = None
    deployed_at: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    before_evidence: Dict[str, Any] = Field(default_factory=dict)
    after_evidence: Dict[str, Any] = Field(default_factory=dict)
    verification_status: str = "unverified"  # unverified | awaiting_verification | verified | failed | regression_detected
    status: str = CROTaskStatus.BACKLOG.value


class BeforeAfterComparison(BaseModel):
    comparison_id: str = Field(default_factory=lambda: _new_id("cro_cmp"))
    task_id: str
    url: str
    test_conditions: Dict[str, Any] = Field(default_factory=dict)
    before_screenshot_id: Optional[str] = None
    after_screenshot_id: Optional[str] = None
    before_dom_id: Optional[str] = None
    after_dom_id: Optional[str] = None
    before_headline: Optional[str] = None
    after_headline: Optional[str] = None
    before_value_prop: Optional[str] = None
    after_value_prop: Optional[str] = None
    before_cta: Optional[Dict[str, Any]] = None
    after_cta: Optional[Dict[str, Any]] = None
    before_form_fields: Optional[Dict[str, Any]] = None
    after_form_fields: Optional[Dict[str, Any]] = None
    before_validation: Optional[Dict[str, Any]] = None
    after_validation: Optional[Dict[str, Any]] = None
    before_mobile_layout: Optional[Dict[str, Any]] = None
    after_mobile_layout: Optional[Dict[str, Any]] = None
    before_performance: Optional[Dict[str, Any]] = None
    after_performance: Optional[Dict[str, Any]] = None
    before_funnel: Optional[Dict[str, Any]] = None
    after_funnel: Optional[Dict[str, Any]] = None
    before_analytics_events: Optional[Dict[str, Any]] = None
    after_analytics_events: Optional[Dict[str, Any]] = None
    before_conversion_metrics: Optional[Dict[str, Any]] = None
    after_conversion_metrics: Optional[Dict[str, Any]] = None
    before_finding_status: str = "open"
    after_verification_status: str = "unverified"


class CROVerification(CROProvenanceMixin):
    verification_id: str = Field(default_factory=lambda: _new_id("cro_ver"))
    task_id: str
    finding_ids: List[str] = Field(default_factory=list)
    verifier: str = "dristik_independent_verifier"
    # Phase 22: 4 strictly separated outcomes
    implementation_verified: str = "pending"   # passed | failed | pending
    functional_verification: str = "not_tested" # passed | failed | not_tested
    analytics_verification: str = "unavailable" # verified | failed | unavailable
    business_outcome: str = "insufficient_data" # improved | degraded | inconclusive | insufficient_data
    criteria_results: List[Dict[str, Any]] = Field(default_factory=list)
    regressions_detected: List[Dict[str, Any]] = Field(default_factory=list)
    before_after: Optional[BeforeAfterComparison] = None
    notes: str = ""
    verified_at: str = Field(default_factory=_utc_now)


class CROSnapshot(CROProvenanceMixin):
    snapshot_id: str = Field(default_factory=lambda: _new_id("cro_snap"))
    snapshot_type: str  # raw_html | rendered_dom | screenshot_desktop | screenshot_mobile | audit_state | before_state | after_state
    content_hash: str
    storage_uri: str
    viewport: Optional[str] = None
    browser: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CROReport(CROProvenanceMixin):
    report_id: str = Field(default_factory=lambda: _new_id("cro_rep"))
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
    published_at: str = Field(default_factory=_utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# Agent Output Contract, 3-Scorecard Bundle, Remediation Pack, Monitoring, QA
# ─────────────────────────────────────────────────────────────────────────────


class CROAgentOutput(BaseModel):
    agent_id: str
    department: str
    status: str = "completed"  # completed | partial | unavailable | failed | skipped
    audit_id: str
    findings: List[CROFinding] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    limitations: List[str] = Field(default_factory=list)
    methodology_version: str = CRO_METHODOLOGY_VERSION
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)


class CRODimensionCheck(BaseModel):
    check_id: str
    dimension_id: str
    label: str
    weight: float = 1.0
    result: Optional[float] = Field(default=None, ge=0.0, le=1.0)  # 0.0..1.0; None if not executed
    applicable: bool = True
    executed: bool = True
    source_type: EvidenceSourceType = EvidenceSourceType.HEURISTIC_OBSERVATION
    evidence_ids: List[str] = Field(default_factory=list)
    note: str = ""


class CROWeightedDimension(BaseModel):
    dimension_id: str
    name: str
    configured_weight_pct: float
    effective_weight_pct: Optional[float] = None
    applicable: bool = True
    executed_checks: int = 0
    total_checks: int = 0
    score: Optional[float] = None
    status: str = "measured"  # measured | partial | unmeasured | not_applicable
    evidence_types: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class CROThreeScorecardBundle(BaseModel):
    audit_id: str
    methodology_version: str = CRO_METHODOLOGY_VERSION
    # Scorecard 1: Experience Score (10 weighted dimensions totaling 100%)
    experience_score: Optional[float] = None
    experience_grade: str = "Unmeasured"
    experience_dimensions: List[CROWeightedDimension] = Field(default_factory=list)
    experience_active_weight_pct: float = 0.0
    # Scorecard 2: Conversion Measurement Score
    measurement_score: Optional[float] = None
    measurement_status: str = "unmeasured"  # verified | partial | unhealthy | unmeasured
    measurement_checks: List[Dict[str, Any]] = Field(default_factory=list)
    # Scorecard 3: Measured Business Performance (never converted into a quality score)
    business_performance_status: str = "data_unavailable"
    business_performance_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    # Mandatory Enterprise Qualifications
    scope_coverage_pct: Optional[float] = None
    test_coverage_pct: Optional[float] = None
    evidence_coverage_pct: Optional[float] = None
    confidence: Optional[float] = None
    data_freshness: str = Field(default_factory=_utc_now)
    analytics_completeness_pct: float = 0.0
    disclosures: List[str] = Field(default_factory=list)


class CRORemediationPack(CROProvenanceMixin):
    pack_id: str = Field(default_factory=lambda: _new_id("cro_pack"))
    audit_id: str
    executive_summary: str = ""
    root_cause_groups: List[Dict[str, Any]] = Field(default_factory=list)
    deliverables: Dict[str, Any] = Field(default_factory=dict)  # All 18 consolidated deliverables
    tasks: List[CRORemediationTask] = Field(default_factory=list)
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list)
    remaining_risks: List[Dict[str, Any]] = Field(default_factory=list)
    page_implementation_sheets: List[Dict[str, Any]] = Field(default_factory=list)
    total_findings_consolidated: int = 0
    deduplicated_count: int = 0


class CROMonitoringSchedule(CROProvenanceMixin):
    schedule_id: str = Field(default_factory=lambda: _new_id("cro_sched"))
    domain: str
    target_urls: List[str] = Field(default_factory=list)
    cadence: str = "daily"  # hourly | daily | weekly
    checks_enabled: List[str] = Field(
        default_factory=lambda: [
            "landing_pages",
            "forms",
            "ctas",
            "checkout_paths",
            "conversion_events",
            "funnel_changes",
            "performance_regressions",
            "mobile_layout",
            "broken_links",
            "js_errors",
            "experiment_guardrails",
        ]
    )
    active: bool = True
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


class CROMonitoringAlert(CROProvenanceMixin):
    alert_id: str = Field(default_factory=lambda: _new_id("cro_alert"))
    schedule_id: Optional[str] = None
    domain: str
    alert_type: str  # form_broken | checkout_errors | event_stopped | cta_dest_changed | mobile_regression | funnel_drop | tracking_inconsistent | guardrail_breached
    severity: CROSeverity = CROSeverity.HIGH
    title: str
    description: str
    affected_journeys: List[str] = Field(default_factory=list)
    affected_urls: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    suggested_action: str = ""
    acknowledged: bool = False


class CROConnectorCapability(BaseModel):
    connector_id: str
    provider: str
    category: str  # analytics | ecommerce | crm | experimentation_behavior
    priority_tier: int = 1
    connection_status: str = "not_connected"  # connected | not_connected | auth_expired | error
    permissions: List[str] = Field(default_factory=list)
    supported_data: List[str] = Field(default_factory=list)
    available_capabilities: List[str] = Field(default_factory=list)
    unsupported_or_limited: List[str] = Field(default_factory=list)
    last_successful_sync: Optional[str] = None
    last_error: Optional[str] = None
    data_freshness: Optional[str] = None
    rate_limit_status: str = "unknown"
    auth_status: str = "unauthenticated"
    reauth_required: bool = False


class CROQAReport(BaseModel):
    audit_id: str
    qa_status: str = "passed"  # passed | passed_with_warnings | failed
    checked_at: str = Field(default_factory=_utc_now)
    backend_evidence_checks: List[Dict[str, Any]] = Field(default_factory=list)
    scoring_checks: List[Dict[str, Any]] = Field(default_factory=list)
    report_checks: List[Dict[str, Any]] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
