"""Production contracts for enterprise SEO agents, evidence, and findings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Scope = Literal["PAGE_VERIFIED", "SAMPLE_VERIFIED", "SITE_INFERRED"]
Severity = Literal["critical", "high", "medium", "low", "info"]
IssueType = Literal["defect", "diagnostic", "observation"]
RuleClass = Literal["mandatory", "conditional", "recommended", "heuristic"]
CauseLabel = Literal["confirmed", "strongly_supported", "plausible", "unknown"]
VerificationState = Literal["VERIFIED", "PARTIALLY_VERIFIED", "FAILED", "NOT_VERIFIABLE"]
FindingStatus = Literal[
    "open",
    "approved",
    "in_progress",
    "fixed_unverified",
    "verified",
    "partially_verified",
    "reopened",
    "not_applicable",
    "insufficient_evidence",
    "accepted_risk",
]
ChapterStatus = Literal[
    "ISSUE_VERIFIED",
    "NO_ISSUE",
    "MEASURED",
    "INFERRED",
    "DATA_UNAVAILABLE",
    "NOT_TESTED",
    "NOT_APPLICABLE",
]
AgentStatus = Literal["completed", "partial", "unavailable", "failed"]
FailureMode = Literal["fail_closed", "partial_result", "unavailable"]
ExecutionMode = Literal["deterministic", "interpretive", "gated"]
PromptSource = Literal["inline_role", "versioned_file"]
ClaimKind = Literal["observed", "judgment", "hypothesis"]


class ModelPolicy(BaseModel):
    """Which models may run, and what happens when none of them complete."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    permitted_models: tuple[str, ...] = ()
    on_unavailable: Literal["unavailable", "partial"] = "unavailable"


_DEFAULT_MODEL_POLICY = ModelPolicy()


class SEOAgentContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    version: str
    purpose: str
    group: Literal["technical", "onpage", "intelligence", "assurance"]
    chapters: list[int]
    input_schema_version: str
    output_schema_version: str
    data_permissions: list[str]
    evidence_requirements: list[str]
    policy_requirements: list[str]
    timeout_seconds: int = Field(ge=1, le=300)
    max_retries: int = Field(ge=0, le=3)
    failure_mode: FailureMode = "unavailable"
    execution_mode: ExecutionMode
    dependencies: list[str]
    dedicated_prompt: str
    prompt_source: PromptSource = "inline_role"
    prompt_version: str | None = None
    prompt_sha256: str | None = None
    model_policy: ModelPolicy = _DEFAULT_MODEL_POLICY


class SEOAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    agent_version: str
    status: AgentStatus
    finding_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage_note: str
    limitations: list[str] = Field(default_factory=list)
    error_code: str | None = None
    prompt_version: str | None = None
    prompt_sha256: str | None = None


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    content_hash: str
    audit_run_id: str
    collected_at: str | None = None
    source: str
    url: str | None = None
    snapshot_type: Literal["raw", "rendered", "external", "derived"]
    collection_method: str
    collector: str
    scope: Scope
    integrity: Literal["intact", "stale", "derived"] = "derived"
    snapshot_ids: list[str] = Field(default_factory=list)
    superseded_by: str | None = None


class EnterpriseFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    audit_run_id: str
    rule_id: str
    rule_version: str
    rule_class: RuleClass
    title: str
    category: str
    chapter: int
    subchapters: list[str]
    severity: Severity
    issue_type: IssueType
    status: FindingStatus = "open"
    scope: Scope
    affected_urls: list[str] = Field(default_factory=list)
    affected_count: int = Field(ge=0)
    eligible_count: int | None = Field(default=None, ge=0)
    evidence_ids: list[str] = Field(min_length=1)
    observed_condition: str
    expected_condition: str
    simple_explanation: str
    seo_significance: str
    root_cause_hypothesis: str
    cause_label: CauseLabel
    remediation_steps: list[str]
    code_examples: list[str] = Field(default_factory=list)
    code_is_illustrative: bool = True
    stack_detected: str | None = None
    acceptance_tests: list[str]
    regression_risk: str
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
    owner_role: str | None = None
    estimated_effort: str | None = None
    dependency_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationState = "NOT_VERIFIABLE"
    observed_at: str | None = None
    evaluation_state: ChapterStatus = "ISSUE_VERIFIED"
    claim_kind: ClaimKind = "observed"
    business_impact: str = ""
    investigation_targets: list[str] = Field(default_factory=list)
    severity_rationale: str = ""
    confidence_rationale: str = ""


class RejectedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    reason: str


class SubchapterCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subchapter_id: str
    title: str
    status: ChapterStatus
    note: str


class ChapterCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter: int
    title: str
    part: str
    status: ChapterStatus
    summary: str
    finding_ids: list[str] = Field(default_factory=list)
    subchapters: list[SubchapterCoverage]
    working: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ScoreDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    score: float | None = None
    methodology_version: str | None = None
    status: Literal["sealed", "not_scored"]
    note: str


class IntegrationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: str
    note: str


class CoverageStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls_discovered: int | None = None
    urls_requested: int | None = None
    urls_crawled: int | None = None
    urls_rendered: int | None = None
    discovered_denominator_known: bool
    sampling_status: str
    statement: str
    integrations: list[IntegrationStatus]


class RoadmapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window: Literal["24h", "7d", "30d", "60d", "90d"]
    finding_id: str
    title: str
    owner_role: str | None = None
    estimated_effort: str | None = None
    verification: str


class FindingCardSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int
    heading: str
    body: str


class FindingCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    title: str
    complete: bool
    sections: list[FindingCardSection]


class EnterpriseSeoAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "seo.enterprise.v1"
    audit_run_id: str
    domain: str
    generated_at: str | None = None
    report_stage: Literal["preliminary", "final"]
    coverage: CoverageStatement
    scores: list[ScoreDisclosure]
    chapters: list[ChapterCoverage]
    agents: list[SEOAgentResult]
    execution_order: list[str]
    findings: list[EnterpriseFinding]
    rejected: list[RejectedFinding]
    evidence: list[EvidenceRecord]
    cards: list[FindingCard]
    roadmap: list[RoadmapItem]
    limitations: list[str]
    diagnostic_summary: str = ""
    deferred_modules: list[str] = Field(default_factory=list)
