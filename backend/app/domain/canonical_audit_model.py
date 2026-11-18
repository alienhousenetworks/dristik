"""
Canonical Audit Data Model — Enterprise Quality Standard (Phase 0.1)

Defines the 17 core standardized entities used by all audit engines in Dristik.
Every record carries immutable execution identifiers, timestamps, and schema versions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    EvidenceStatus,
    PublicationStatus,
    Severity,
    Category,
    FindingStatus,
    MetricDirection,
    MissingDataRule,
    RootCauseTaxonomy,
)


class CanonicalBaseRecord(BaseModel):
    """Base model enforcing audit execution traceability across all entities."""
    tenant_id: str = "default_tenant"
    audit_run_id: str
    domain_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"
    engine_version: str = "2026.1"

    model_config = ConfigDict(extra="ignore")


# 1. AuditRun — One complete audit execution
class CanonicalAuditRun(CanonicalBaseRecord):
    id: str
    domain: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    crawl_snapshot_id: str = ""
    configuration_version: str = "2026.1"
    agent_manifest_version: str = "v1"
    evidence_registry_version: str = "v1"
    status: str = "completed"
    publication_status: PublicationStatus = PublicationStatus.DRAFT
    blocking_reasons: List[str] = Field(default_factory=list)


# 2. DomainProfile — Domain and business identity
class DomainProfile(CanonicalBaseRecord):
    domain: str
    primary_hostname: str
    brand_name: str
    root_url: str
    ip_addresses: List[str] = Field(default_factory=list)
    nameservers: List[str] = Field(default_factory=list)
    ssl_certified: bool = True
    cms_technology: Optional[str] = None
    hosting_provider: Optional[str] = None


# 3. BusinessProfile — Verified company facts and commercial model
class CanonicalBusinessProfile(CanonicalBaseRecord):
    business_name: str
    industry: Optional[str] = None
    niche: Optional[str] = None
    products_or_services: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    business_model: Optional[str] = None  # B2B, B2C, D2C, MARKETPLACE
    primary_value_proposition: Optional[str] = None
    economic_buyer_title: Optional[str] = None
    evidence_status: EvidenceStatus = EvidenceStatus.OBSERVED


# 4. CrawlInventory — Discovered URL inventory
class CrawlInventory(CanonicalBaseRecord):
    inventory_id: str
    discovered_urls_count: int
    inspected_urls_count: int
    sitemap_urls_count: int = 0
    discovered_urls: List[str] = Field(default_factory=list)
    crawl_budget_limit: int = 500
    is_complete_crawl: bool = False
    coverage_ratio: float = 0.0


# 5. CrawlPage — Individual inspected URL
class CrawlPage(CanonicalBaseRecord):
    page_id: str
    url: str
    status_code: int = 200
    is_homepage: bool = False
    title: Optional[str] = None
    h1_tags: List[str] = Field(default_factory=list)
    word_count: int = 0
    ttfb_ms: Optional[float] = None
    content_type: str = "text/html"
    indexability_status: str = "INDEXABLE"


# 6. PageSnapshot — Immutable page capture
class PageSnapshot(CanonicalBaseRecord):
    snapshot_id: str
    page_id: str
    url: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_html_sha256: str
    storage_uri: Optional[str] = None
    rendered_dom_captured: bool = False
    http_headers: Dict[str, str] = Field(default_factory=dict)


# 7. EvidenceRecord — Raw observations and measurements
class EvidenceRecord(CanonicalBaseRecord):
    evidence_id: str
    page_id: Optional[str] = None
    url: Optional[str] = None
    classification: EvidenceStatus = EvidenceStatus.OBSERVED
    collection_method: str = "DOM_INSPECTION"
    source_system: str = "CRAWL_ENGINE"
    collection_duration_ms: Optional[int] = None
    scope: str = "PAGE"  # PAGE, SAMPLE, DOMAIN
    raw_value: Optional[Any] = None
    normalized_value: Optional[Any] = None
    expected_condition: Optional[str] = None
    observed_condition: Optional[str] = None
    confidence_rationale: str = "Direct machine observation."
    artifact_location: Optional[str] = None
    content_hash: str = ""
    hash_validation_status: str = "VALID"
    provenance_details: Dict[str, Any] = Field(default_factory=dict)


# 8. Finding — A diagnosed defect or opportunity
class CanonicalFinding(CanonicalBaseRecord):
    finding_id: str
    root_cause_key: RootCauseTaxonomy = RootCauseTaxonomy.GENERIC
    category: Category = Category.TECHNICAL_SEO
    title: str
    description: str
    severity: Severity = Severity.MEDIUM
    impact_score: int = Field(default=5, ge=1, le=10)
    status: FindingStatus = FindingStatus.OPEN
    affected_urls: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_records: List[EvidenceRecord] = Field(default_factory=list)
    recommendation_text: str = ""
    relevant_disciplines: List[str] = Field(default_factory=list)


# 9. MetricResult — Calculated metric
class MetricResult(CanonicalBaseRecord):
    metric_id: str
    formula_version: str = "v1"
    name: str = ""
    classification: EvidenceStatus = EvidenceStatus.MEASURED
    direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER
    input_evidence_ids: List[str] = Field(default_factory=list)
    raw_value: Optional[float] = None
    normalized_score: Optional[float] = None
    benchmark_value: Optional[float] = None
    missing_data_rule: MissingDataRule = MissingDataRule.UNMEASURED_FLAG
    confidence: float = 1.0
    coverage_ratio: float = 1.0
    notes: str = ""


# 10. ScoreResult — Versioned score calculation
class ScoreResult(CanonicalBaseRecord):
    score_id: str
    scoring_version: str = "2026.1"
    overall_score: Optional[float] = None
    grade: str = "B"
    is_partial_assessment: bool = False
    coverage_score: float = 1.0
    category_scores: Dict[str, float] = Field(default_factory=dict)
    weighted_contributions: Dict[str, float] = Field(default_factory=dict)
    formula_audit_trail: List[str] = Field(default_factory=list)


# 11. Recommendation — Proposed action
class CanonicalRecommendation(CanonicalBaseRecord):
    recommendation_id: str
    finding_id: str
    title: str
    action_type: str = "CODE_CHANGE"
    target_role: str = "Engineering"
    effort_estimate: str = "MEDIUM"
    expected_outcome: str = ""
    implementation_code_snippet: Optional[str] = None


# 12. RemediationTask — Assigned implementation work
class RemediationTask(CanonicalBaseRecord):
    task_id: str
    recommendation_id: str
    finding_id: str
    assignee_role: str = "Engineering"
    status: str = "TODO"  # TODO, IN_PROGRESS, RESOLVED, VERIFIED
    resolution_note: Optional[str] = None
    verified_at: Optional[datetime] = None


# 13. VerificationRun — Post-fix testing
class VerificationRun(CanonicalBaseRecord):
    verification_id: str
    task_id: str
    finding_id: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified_fixed: bool = False
    retest_method: str = "HTTP_RETEST"
    verification_evidence_id: Optional[str] = None
    details: str = ""


# 14. CompetitorProfile — Comparable competitor entity
class CompetitorProfile(CanonicalBaseRecord):
    competitor_id: str
    domain: str
    company_name: str
    authority_score: Optional[float] = None
    ai_visibility_score: Optional[float] = None
    is_target_domain: bool = False


# 15. BenchmarkResult — Comparable measurement
class BenchmarkResult(CanonicalBaseRecord):
    benchmark_id: str
    metric_id: str
    industry: str
    median_value: float
    top_quartile_value: float
    target_value: Optional[float] = None
    sample_size: int = 100


# 16. ReportArtifact — Generated report and version
class ReportArtifact(CanonicalBaseRecord):
    artifact_id: str
    report_type: str  # MASTER_BOOK, SEO, GEO, AEO, CRO, EXEC_DECK
    version: str = "1.0.0"
    file_path: Optional[str] = None
    sha256_checksum: str = ""
    page_count: int = 0
    publication_status: PublicationStatus = PublicationStatus.DRAFT
    rendered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 17. AuditEvent — Complete execution history
class AuditEvent(CanonicalBaseRecord):
    event_id: str
    event_type: str  # CRAWL_STARTED, PAGE_INSPECTED, EVIDENCE_RECORDED, GATES_EVALUATED, PUBLISHED
    actor: str = "SYSTEM"
    details: Dict[str, Any] = Field(default_factory=dict)
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
