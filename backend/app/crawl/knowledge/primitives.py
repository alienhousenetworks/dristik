"""
Dristik Knowledge Intelligence Engine (KIE) — Core Primitives
Defines the four foundational data primitives:
  Entity, Relationship, Claim, Evidence
and the clean orthogonal taxonomies that govern them.

These are distinct from app.domain.enums and app.domain.models —
they belong exclusively to the KIE knowledge layer.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Orthogonal Taxonomy 1: Claim Type
# "What kind of assertion is this statement?"
# ─────────────────────────────────────────────────────────────────────────────

class KieClaimType(str, Enum):
    FACT = "FACT"              # Objective, verifiable specification or credential
                               # e.g. "SOC 2 Type II certified", "Prices start at $99/mo"
    CAPABILITY = "CAPABILITY"  # Product mechanics, feature, workflow, or integration
                               # e.g. "REST API with webhook support", "Supports Kubernetes"
    MARKETING = "MARKETING"    # Subjective qualitative boast or value statement
                               # e.g. "Industry-leading real-time observability"
    OPINION = "OPINION"        # Editorial stance or subjective perspective
                               # e.g. "We believe privacy-first is the future"
    PROMISE = "PROMISE"        # SLA, performance commitment, or outcome guarantee
                               # e.g. "99.9% uptime SLA", "Deploy in 14 days"


# ─────────────────────────────────────────────────────────────────────────────
# Orthogonal Taxonomy 2: Evidence State
# "What is the verification status of this claim?"
# ─────────────────────────────────────────────────────────────────────────────

class KieEvidenceState(str, Enum):
    SUPPORTED = "SUPPORTED"        # Backed by explicit, unambiguous first-party or
                                   # verified-authority source
    PARTIAL = "PARTIAL"            # Related evidence discovered but lacks standalone
                                   # completeness or specificity
    MISSING = "MISSING"            # Zero on-page or external evidence across crawl scope
    CONTRADICTED = "CONTRADICTED"  # Conflicts with another first-party or external statement
    STALE = "STALE"                # Deprecated assertion superseded by newer content
    UNVERIFIED = "UNVERIFIED"      # Stated claim without verifiable proof in crawled scope


# ─────────────────────────────────────────────────────────────────────────────
# Orthogonal Taxonomy 3: Evidence Strength
# "How authoritative is the source of this evidence?"
# ─────────────────────────────────────────────────────────────────────────────

class KieEvidenceStrength(str, Enum):
    HIGH = "HIGH"     # Dedicated authoritative page (pricing table, legal policy,
                      # certification registry, official security page)
    MEDIUM = "MEDIUM" # In-line passing mention or secondary blog/article reference
    LOW = "LOW"       # Ambiguous footer snippet, generic marketing blurb


# ─────────────────────────────────────────────────────────────────────────────
# Orthogonal Taxonomy 4: Answer Risk
# "What business risk does this gap create for AI answer engines?"
# ─────────────────────────────────────────────────────────────────────────────

class KieAnswerRisk(str, Enum):
    HIGH = "HIGH"     # High-intent commercial/compliance void: AI will hallucinate or
                      # substitute competitor alternatives
    MEDIUM = "MEDIUM" # Technical or operational ambiguity producing incomplete answers
    LOW = "LOW"       # Minor informational gap; negligible buyer-decision impact


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Source Tiers
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeSourceTier(str, Enum):
    FIRST_PARTY = "FIRST_PARTY"   # Authorial control: website, docs, pricing, legal, PDFs
    THIRD_PARTY = "THIRD_PARTY"   # External: Google KG, Wikipedia, LinkedIn, directories


# ─────────────────────────────────────────────────────────────────────────────
# Page Classification
# ─────────────────────────────────────────────────────────────────────────────

class PageRole(str, Enum):
    HOMEPAGE = "homepage"
    ABOUT = "about"
    PRICING = "pricing"
    SERVICES = "services"
    PRODUCT = "product"
    CASE_STUDY = "case_study"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    FAQ = "faq"
    CAREERS = "careers"
    CONTACT = "contact"
    LEGAL = "legal"
    BLOG = "blog"
    UNKNOWN = "unknown"

    def knowledge_contribution(self) -> str:
        """Human-readable description of what this page role contributes to KIE."""
        return {
            "homepage": "Identity, Mission & Value Proposition",
            "about": "Company History, Team & Culture",
            "pricing": "Commercial Model, Tiers & Billing",
            "services": "Service Offerings & Capabilities",
            "product": "Product Features & Mechanics",
            "case_study": "Customer Proof & Quantified ROI",
            "security": "Trust, Compliance & Data Governance",
            "documentation": "Technical Architecture & Integration",
            "faq": "Direct Commercial Answers",
            "careers": "Organization Size & Culture",
            "contact": "Entity Location & Reachability",
            "legal": "Policies, Terms & Commitments",
            "blog": "Domain Expertise & Industry Positioning",
            "unknown": "Unclassified Page",
        }.get(self.value, "Unclassified")


# ─────────────────────────────────────────────────────────────────────────────
# Question Budget Tiers
# ─────────────────────────────────────────────────────────────────────────────

class QuestionBudgetTier(str, Enum):
    STARTER = "STARTER"        # 30–50 questions (micro-sites, single landing page)
    STANDARD = "STANDARD"      # 100 questions (typical SaaS/corporate; 10 facets x 10)
    ENTERPRISE = "ENTERPRISE"  # 250 questions (multi-product, complex matrix)
    DEEP_AUDIT = "DEEP_AUDIT"  # 500+ questions (extensive docs, international presence)

    def question_count(self) -> int:
        return {"STARTER": 50, "STANDARD": 100, "ENTERPRISE": 250, "DEEP_AUDIT": 500}[self.value]

    def questions_per_facet(self) -> int:
        return self.question_count() // 10


# ─────────────────────────────────────────────────────────────────────────────
# Core KIE Primitives — Data Models
# ─────────────────────────────────────────────────────────────────────────────

class KieEvidence(BaseModel):
    """Physical grounding proof linking a claim to first-party source content."""
    evidence_id: str
    url: str
    page_role: PageRole = PageRole.UNKNOWN
    section: Optional[str] = None
    exact_sentence: str
    crawl_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_tier: KnowledgeSourceTier = KnowledgeSourceTier.FIRST_PARTY
    strength: KieEvidenceStrength = KieEvidenceStrength.MEDIUM


class AtomicClaim(BaseModel):
    """
    A discrete, verifiable assertion made by the company on its website.
    Claims are extracted from sentences, not paragraphs —
    one sentence can produce multiple atomic claims.
    """
    claim_id: str
    subject: str                  # Entity making the claim (usually the company name)
    predicate: str                # Relationship verb (e.g. "offers", "is_certified_for")
    object: str                   # Target of the claim (e.g. "SOC 2 Type II", "React.js")
    claim_type: KieClaimType = KieClaimType.CAPABILITY
    evidence_state: KieEvidenceState = KieEvidenceState.SUPPORTED
    evidence_strength: KieEvidenceStrength = KieEvidenceStrength.MEDIUM
    confidence: float = 0.8
    evidence: Optional[KieEvidence] = None


class EntityNode(BaseModel):
    """A named entity discovered from first-party or third-party knowledge."""
    entity_id: str
    name: str
    category: str   # Organization | Product | Service | Technology | Certification | Location
    properties: Dict[str, Any] = Field(default_factory=dict)
    knowledge_tier: KnowledgeSourceTier = KnowledgeSourceTier.FIRST_PARTY
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EntityRelationship(BaseModel):
    """Directed edge in the Website Knowledge Graph."""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    predicate: str   # offers | integrates_with | claims_certification | serves_industry
    confidence: float = 1.0
    provenance_url: Optional[str] = None


class PageKnowledgeClassification(BaseModel):
    """Classification of a crawled page into KIE role and domains."""
    url: str
    title: Optional[str] = None
    page_role: PageRole = PageRole.UNKNOWN
    knowledge_domains: List[str] = Field(default_factory=list)
    primary_entities: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class ContradictionItem(BaseModel):
    """A detected cross-page knowledge conflict."""
    contradiction_id: str
    topic: str
    claim_a_text: str
    claim_b_text: str
    source_url_a: str
    source_url_b: str
    severity: str = "MODERATE"   # CRITICAL | MODERATE | LOW
    explanation: str


# ─────────────────────────────────────────────────────────────────────────────
# Grounding Primitives
# ─────────────────────────────────────────────────────────────────────────────

class ClaimGroundingResult(BaseModel):
    """Verification result for one atomic claim within a simulated answer."""
    claim_text: str
    status: str = "SUPPORTED"    # SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED
    evidence_snippet: Optional[str] = None
    evidence_url: Optional[str] = None
    confidence: float = 1.0


class GroundedAnswerSimulation(BaseModel):
    """
    A controlled simulation evaluating whether an answer engine could construct
    a defensible, hallucination-free answer from retrieved evidence.
    This is NOT a reproduction of proprietary Perplexity/ChatGPT internal code.
    """
    question_id: str
    candidate_answer: str
    retrieved_extract: str = ""
    """Verbatim passage from the crawl. This is the current page, not the written answer."""
    rag_answer: str = ""
    """Answer composed only from retrieved passages, with a source line. Abstains when the crawl has no fact."""
    claim_decomposition: List[ClaimGroundingResult] = Field(default_factory=list)
    grounding_ratio: float = 0.0    # Supported Claims / Total Claims
    retrieval_evidence_count: int = 0
    answer_risk: KieAnswerRisk = KieAnswerRisk.LOW
    assessment_status: str = "INSUFFICIENT"  # SUFFICIENT | PARTIAL | INSUFFICIENT | CONFLICTING
    missing_aspects: List[str] = Field(default_factory=list)
    supported_aspects: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    source_page_title: Optional[str] = None
    source_section: Optional[str] = None
    target_update_page: Optional[str] = None
    target_update_section: Optional[str] = None
    section_update_recommendation: Optional[str] = None
    ai_thinking_steps: List[Dict[str, Any]] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 5 Decoupled AI Visibility Dimensions
# ─────────────────────────────────────────────────────────────────────────────

class FiveDimensionAiVisibility(BaseModel):
    """
    Five independent diagnostic dimensions of AI Visibility.
    NOT equal-weighted by default; each dimension is reported independently.
    Any aggregate_index is versioned, configurable, and documented explicitly.
    """
    knowledge_coverage: float = 0.0
    """0–100%: Proportion of 10-facet taxonomy questions where atomic claims exist."""

    retrieval_coverage: float = 0.0
    """0–100%: Query Planner success rate in finding candidate evidence."""

    evidence_quality: float = 0.0
    """0–100%: Proportion of evidence with HIGH strength and FACT/CAPABILITY type."""

    answer_grounding: float = 0.0
    """0–100%: Average grounding ratio across all simulated answers."""

    citation_quality: float = 0.0
    """0–100%: Disambiguation clarity and canonical URL attribution coverage."""

    aggregate_index: Optional[float] = None
    """If provided, a transparently documented configurable aggregate; never hardcoded."""

    weighting_profile: str = "independent"
    """Version identifier of weighting config: 'independent' | 'v1.0' | etc."""
