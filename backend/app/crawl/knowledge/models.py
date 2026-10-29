"""
Dristik Knowledge Intelligence Engine (KIE) - Core Domain Models
Defines primitives for Entities, Relationships, Atomic Claims, Evidence Provenance,
Page Knowledge Classification, Contradiction Detection, and 5-Dimension AI Visibility.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    FACT = "FACT"                  # Objective, verifiable specification or credential
    CAPABILITY = "CAPABILITY"      # Product mechanics, feature, workflow, or integration
    MARKETING = "MARKETING"        # Subjective qualitative boast or value statement
    OPINION = "OPINION"            # Editorial stance or subjective perspective
    PROMISE = "PROMISE"            # SLA, performance commitment, or outcome guarantee


class EvidenceState(str, Enum):
    SUPPORTED = "SUPPORTED"        # Backed by explicit, unambiguous first-party or verified authority
    PARTIAL = "PARTIAL"            # Related evidence discovered, but lacking standalone completeness
    MISSING = "MISSING"            # Zero on-page or external evidence found across crawl scope
    CONTRADICTED = "CONTRADICTED"  # Contradicts another first-party or external statement
    STALE = "STALE"                # Deprecated or outdated assertion superseded by newer content
    UNVERIFIED = "UNVERIFIED"      # Stated as claim but without verifiable proof


class EvidenceStrength(str, Enum):
    HIGH = "HIGH"                  # Official dedicated documentation, pricing table, or legal policy
    MEDIUM = "MEDIUM"              # In-line passing mention or secondary blog reference
    LOW = "LOW"                    # Ambiguous footer snippet or generic marketing blurb


class AnswerRisk(str, Enum):
    HIGH = "HIGH"                  # High-intent commercial/compliance void: AI will hallucinate or substitute rivals
    MEDIUM = "MEDIUM"              # Technical/operational ambiguity causing partial or vague answers
    LOW = "LOW"                    # Minor informational gap with negligible buyer-decision risk


class KnowledgeSourceTier(str, Enum):
    FIRST_PARTY = "FIRST_PARTY"    # Direct authorial control (Website, docs, legal, pricing, PDFs)
    THIRD_PARTY = "THIRD_PARTY"    # External web (Google KG, Wikipedia, LinkedIn, Crunchbase, directories)


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


class PageKnowledgeClassification(BaseModel):
    url: str
    page_role: PageRole
    knowledge_domains: List[str] = Field(default_factory=list)
    primary_entities: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    confidence: float = 1.0


class AtomicClaim(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    object: str
    claim_type: ClaimType = ClaimType.CAPABILITY
    evidence_state: EvidenceState = EvidenceState.SUPPORTED
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM
    confidence: float = 0.8
    source_url: str
    source_section: Optional[str] = None
    exact_sentence: str
    crawl_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_tier: KnowledgeSourceTier = KnowledgeSourceTier.FIRST_PARTY


class EntityNode(BaseModel):
    entity_id: str
    name: str
    category: str  # e.g., Organization, Product, Service, Technology, Certification, Location
    properties: Dict[str, Any] = Field(default_factory=dict)
    knowledge_tier: KnowledgeSourceTier = KnowledgeSourceTier.FIRST_PARTY
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EntityRelationship(BaseModel):
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    predicate: str  # e.g., offers, integrates_with, claims_certification, serves_industry
    confidence: float = 1.0
    provenance_url: Optional[str] = None


class ContradictionItem(BaseModel):
    contradiction_id: str
    topic: str
    claim_a: str
    claim_b: str
    source_url_a: str
    source_url_b: str
    severity: str = "MODERATE"  # CRITICAL | MODERATE | LOW
    explanation: str


class QuestionBudgetTier(str, Enum):
    STARTER = "STARTER"          # 30-50 questions
    STANDARD = "STANDARD"        # 100 questions (10 facets x 10)
    ENTERPRISE = "ENTERPRISE"    # 250 questions
    DEEP_AUDIT = "DEEP_AUDIT"    # 500+ questions


class QuestionProvenance(BaseModel):
    question_id: str
    synthesized_for_facet: str
    source_entities: List[str] = Field(default_factory=list)
    rationale: str
    commercial_importance: str


class ClaimGroundingResult(BaseModel):
    claim_text: str
    status: str = "SUPPORTED"  # SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED
    evidence_snippet: Optional[str] = None
    evidence_url: Optional[str] = None
    confidence: float = 1.0


class FiveDimensionAiVisibility(BaseModel):
    knowledge_coverage: float = Field(default=0.0, description="0-100% Availability of atomic claims")
    retrieval_coverage: float = Field(default=0.0, description="0-100% Success rate of Query Planner")
    evidence_quality: float = Field(default=0.0, description="0-100% Proportion of HIGH-strength factual evidence")
    answer_grounding: float = Field(default=0.0, description="0-100% Ratio of verified claims in simulated answers")
    citation_quality: float = Field(default=0.0, description="0-100% Disambiguation & canonical URL attribution")
    aggregate_index: Optional[float] = Field(default=None, description="Documented, configurable aggregate visibility")
