"""
Dristik AI Phase 7 — Competitive Intelligence Domain Models.
Canonical, evidence-grounded models for multi-signal competitor discovery,
ingestion provenance isolation, discipline comparisons (SEO, GEO, AEO, CRO),
ranked opportunity gaps, and 10/10 statement traceability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CompetitorApprovalStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    PENDING_USER_APPROVAL = "PENDING_USER_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DiscoveryVectorType(str, Enum):
    BUSINESS_CATEGORY = "BUSINESS_CATEGORY"
    PRODUCT_CATEGORY = "PRODUCT_CATEGORY"
    SEARCH_INTENT = "SEARCH_INTENT"
    SEARCH_RESULT_SERP = "SEARCH_RESULT_SERP"
    GEOGRAPHIC = "GEOGRAPHIC"
    COMMERCIAL_SIMILARITY = "COMMERCIAL_SIMILARITY"
    CUSTOMER_AUDIENCE = "CUSTOMER_AUDIENCE"


class ProvenanceScope(str, Enum):
    TARGET_DOMAIN = "TARGET_DOMAIN"
    COMPETITOR_BENCHMARK = "COMPETITOR_BENCHMARK"


class DiscoveryVectorScore(BaseModel):
    vector: DiscoveryVectorType
    score: float = Field(..., ge=0.0, le=100.0)
    overlap_details: str = ""
    rationale: str = ""


class CompetitorCandidate(BaseModel):
    domain: str
    company_name: str
    approval_status: CompetitorApprovalStatus = CompetitorApprovalStatus.DISCOVERED
    similarity_score: float = Field(..., ge=0.0, le=100.0)
    vectors: Dict[str, DiscoveryVectorScore] = Field(default_factory=dict)
    rejection_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    provenance_id: str = ""
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BenchmarkGroup(BaseModel):
    target_domain: str
    approved_competitors: List[CompetitorCandidate] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None
    is_official: bool = True


class CompetitorProvenanceRecord(BaseModel):
    provenance_id: str
    domain: str
    scope: ProvenanceScope = ProvenanceScope.COMPETITOR_BENCHMARK
    audit_run_id: str
    observation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str
    source_system: str = "CRAWL_ENGINE"
    collection_method: str = "DOM_INSPECTION"
    collection_duration_ms: Optional[int] = None
    storage_partition: str = "competitors"

    model_config = ConfigDict(extra="ignore")


class CompetitorPageIngestion(BaseModel):
    url: str
    page_type: str = "UNKNOWN"  # HOMEPAGE, PRODUCT, CATEGORY, BLOG, PRICING, CONTACT, DOCS
    product_categories: List[str] = Field(default_factory=list)
    word_count: int = 0
    content_structure: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    structured_data_types: List[str] = Field(default_factory=list)
    internal_links_count: int = 0
    ttfb_ms: Optional[float] = None
    mobile_viewport_configured: bool = False
    cta_elements: List[str] = Field(default_factory=list)
    forms_count: int = 0
    provenance: CompetitorProvenanceRecord


class CompetitorIngestionArtifact(BaseModel):
    competitor_domain: str
    pages: List[CompetitorPageIngestion] = Field(default_factory=list)
    total_pages_captured: int = 0
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: CompetitorProvenanceRecord


# --- Competitive SEO Intelligence (Phase 7.3) ---
class CompetitiveSeoComparison(BaseModel):
    target_domain: str
    competitor_domain: str
    keyword_coverage: Dict[str, Any] = Field(default_factory=dict)
    search_intent_coverage: Dict[str, Any] = Field(default_factory=dict)
    page_architecture: Dict[str, Any] = Field(default_factory=dict)
    content_depth: Dict[str, Any] = Field(default_factory=dict)
    technical_quality: Dict[str, Any] = Field(default_factory=dict)
    backlink_profiles: Dict[str, Any] = Field(default_factory=dict)
    landing_page_coverage: Dict[str, Any] = Field(default_factory=dict)
    search_visibility: Dict[str, Any] = Field(default_factory=dict)
    seo_parity_score: int = Field(default=50, ge=0, le=100)


# --- Competitive GEO Intelligence (Phase 7.4) ---
class CompetitiveGeoComparison(BaseModel):
    target_domain: str
    competitor_domain: str
    entity_clarity: Dict[str, Any] = Field(default_factory=dict)
    ai_crawler_accessibility: Dict[str, Any] = Field(default_factory=dict)
    ai_mentions: Dict[str, Any] = Field(default_factory=dict)
    citation_domains: Dict[str, Any] = Field(default_factory=dict)
    citation_frequency: Dict[str, Any] = Field(default_factory=dict)
    source_credibility: Dict[str, Any] = Field(default_factory=dict)
    brand_positioning: Dict[str, Any] = Field(default_factory=dict)
    factual_consistency: Dict[str, Any] = Field(default_factory=dict)
    geo_parity_score: int = Field(default=50, ge=0, le=100)


# --- Competitive AEO Intelligence (Phase 7.5) ---
class CompetitiveAeoComparison(BaseModel):
    target_domain: str
    competitor_domain: str
    question_coverage: Dict[str, Any] = Field(default_factory=dict)
    answer_completeness: Dict[str, Any] = Field(default_factory=dict)
    answer_extractability: Dict[str, Any] = Field(default_factory=dict)
    citation_accuracy: Dict[str, Any] = Field(default_factory=dict)
    live_answer_appearance: Dict[str, Any] = Field(default_factory=dict)
    unanswered_commercial_questions: List[str] = Field(default_factory=list)
    aeo_parity_score: int = Field(default=50, ge=0, le=100)


# --- Competitive CRO Intelligence (Phase 7.6) ---
class CompetitiveCroComparison(BaseModel):
    target_domain: str
    competitor_domain: str
    value_propositions: Dict[str, Any] = Field(default_factory=dict)
    navigation: Dict[str, Any] = Field(default_factory=dict)
    pricing_visibility: Dict[str, Any] = Field(default_factory=dict)
    product_page_structures: Dict[str, Any] = Field(default_factory=dict)
    cta_placement: Dict[str, Any] = Field(default_factory=dict)
    forms: Dict[str, Any] = Field(default_factory=dict)
    trust_signals: Dict[str, Any] = Field(default_factory=dict)
    checkout_friction: Dict[str, Any] = Field(default_factory=dict)
    checkout_tested: bool = False
    checkout_status: str = "CHECKOUT_FLOW_UNTESTED"
    cro_parity_score: int = Field(default=50, ge=0, le=100)


# --- Opportunity Gap Engine (Phase 7.7) ---
class OpportunityGapType(str, Enum):
    UNANSWERED_QUESTION = "UNANSWERED_QUESTION"
    AUTHORITY_REPUTATION = "AUTHORITY_REPUTATION"
    COMMERCIAL_CLARITY = "COMMERCIAL_CLARITY"
    CONVERSION_JOURNEY = "CONVERSION_JOURNEY"
    UNMET_SEARCH_INTENT = "UNMET_SEARCH_INTENT"


class OpportunityGapItem(BaseModel):
    id: str
    title: str
    gap_type: OpportunityGapType
    priority: str = "P1"  # P1, P2, P3
    impact_score: int = Field(..., ge=1, le=10)
    effort: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    ice_score: float = 0.0
    competitor_domain: str
    proof_url: str
    proof_observation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str
    actionable_playbook: str


class OpportunityGapReport(BaseModel):
    target_domain: str
    total_gaps_identified: int = 0
    ranked_opportunities: List[OpportunityGapItem] = Field(default_factory=list)
    gaps_by_type: Dict[str, int] = Field(default_factory=dict)


# --- Competitive Scoring & 10/10 Acceptance (Phase 7.8) ---
class DisciplineComparisonScore(BaseModel):
    discipline: str  # SEO, GEO, AEO, CRO
    target_score: int = Field(..., ge=0, le=100)
    benchmark_median_score: int = Field(..., ge=0, le=100)
    competitor_scores: Dict[str, int] = Field(default_factory=dict)
    delta: int = 0  # target_score - benchmark_median_score
    status: str = "AVAILABLE"  # AVAILABLE, PARTIAL, UNMEASURED
    sample_size: int = 0
    methodology: str = ""


class Competitive10Of10Statement(BaseModel):
    claim_id: str
    statement: str
    source_url: str
    observation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    methodology: str
    discipline: str
    metric_name: str
    is_comparable: bool = True


class CompetitiveScorecard(BaseModel):
    target_domain: str
    benchmark_domains: List[str] = Field(default_factory=list)
    seo_score: DisciplineComparisonScore
    geo_score: DisciplineComparisonScore
    aeo_score: DisciplineComparisonScore
    cro_score: DisciplineComparisonScore
    overall_competitive_index: float = Field(..., ge=0.0, le=100.0)
    sample_coverage_summary: Dict[str, Any] = Field(default_factory=dict)
    statements_ledger: List[Competitive10Of10Statement] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
