"""
Dristik AI Domain Enums
Defines standardized types, severities, stages, and categories.
"""
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class Category(str, Enum):
    TECHNICAL_SEO = "TECHNICAL_SEO"
    ON_PAGE_SEO = "ON_PAGE_SEO"
    CONTENT = "CONTENT"
    GEO = "GEO"
    AI_SEARCH = "AI_SEARCH"
    SCHEMA = "SCHEMA"
    UX_CONVERSION = "UX_CONVERSION"
    TRUST_AUTHORITY = "TRUST_AUTHORITY"
    COMPETITIVE = "COMPETITIVE"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    PROVISIONAL = "provisional"
    REJECTED = "rejected"
    CONFLICTED = "conflicted"
    CONTESTED = "contested"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_MEASURED = "not_measured"
    PENDING_VERIFICATION = "pending_verification"
    UNSUPPORTED = "unsupported"
    SINGLE_SOURCE_UNVERIFIED = "single_source_unverified"


class SourceIntegrityLabel(str, Enum):
    CORROBORATED = "CORROBORATED"
    CONTESTED = "CONTESTED"
    SINGLE_SOURCE_UNVERIFIED = "SINGLE_SOURCE_UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GroundTruthRelation(str, Enum):
    CONFIRMS = "CONFIRMS"
    CONTRADICTS = "CONTRADICTS"
    MISSING_EXTERNAL = "MISSING_EXTERNAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ClaimFamily(str, Enum):
    ICP = "icp"
    PRICING = "pricing"
    PERFORMANCE = "performance"
    TRUST = "trust"
    AUTHORSHIP = "authorship"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RubricConfidence(str, Enum):
    CERTAIN = "CERTAIN"
    LIKELY = "LIKELY"
    GUESSING = "GUESSING"


class Materiality(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"

class EvidenceLevel(str, Enum):
    E0_NONE = "E0_NONE"                                 # No evidence
    E1_LLM_ASSERTION = "E1_LLM_ASSERTION"               # Pure model generation (insufficient alone)
    E2_DERIVED = "E2_DERIVED"                           # Derived from supplied evidence
    E3_DETERMINISTIC = "E3_DETERMINISTIC"               # Deterministic parser observation
    E4_FIRST_PARTY_DOM = "E4_FIRST_PARTY_DOM"           # First-party website DOM/HTTP evidence
    E5_AUTHORIZED_EXTERNAL = "E5_AUTHORIZED_EXTERNAL"   # Authorized external API source
    E6_CORROBORATED = "E6_CORROBORATED"                 # Independently corroborated external evidence

class ClaimState(str, Enum):
    CREATED = "CREATED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    EVIDENCE_ATTACHED = "EVIDENCE_ATTACHED"
    SOURCE_VALIDATED = "SOURCE_VALIDATED"
    CONTRADICTION_CHECK = "CONTRADICTION_CHECK"
    ADVERSARIAL_REVIEW = "ADVERSARIAL_REVIEW"
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    REJECTED = "REJECTED"
    CONFLICTED = "CONFLICTED"
    CONTESTED = "CONTESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_MEASURED = "NOT_MEASURED"
    SINGLE_SOURCE_UNVERIFIED = "SINGLE_SOURCE_UNVERIFIED"

class ObservationType(str, Enum):
    OBSERVED = "OBSERVED"
    CALCULATED = "CALCULATED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"
    SIMULATION = "SIMULATION"
    UNKNOWN = "UNKNOWN"

class ClaimType(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"

class BusinessIntent(str, Enum):
    LEAD_GENERATION = "lead_generation"
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    CONTENT_PUBLISHING = "content_publishing"
    PORTFOLIO = "portfolio"
    AGENCY = "agency"
    LOCAL_BUSINESS = "local_business"
    MARKETPLACE = "marketplace"
    EDUCATION = "education"
    MEDIA = "media"
    COMMUNITY = "community"
    DOCUMENTATION = "documentation"
    CORPORATE = "corporate"
    PERSONAL_BRAND = "personal_brand"
    NON_PROFIT = "non_profit"

class EvidenceConfidence(str, Enum):
    CONFIRMED = "Confirmed"          # 0.95 - 1.00 (deterministic proof)
    STRONG = "Strong Evidence"      # 0.85 - 0.94
    LIKELY = "Likely"                # 0.70 - 0.84
    POTENTIAL = "Potential"          # 0.50 - 0.69
    UNCERTAIN = "Uncertain"          # < 0.50

class EvidenceState(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"

class AnalysisStage(str, Enum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    DETERMINISTIC_ANALYSIS = "deterministic_analysis"
    PLANNING = "planning"
    SPECIALIST_EXECUTION = "specialist_execution"
    ADVERSARIAL_VERIFICATION = "adversarial_verification"
    SCORING = "scoring"
    EXECUTIVE_SYNTHESIS = "executive_synthesis"
    COMPLETED = "completed"
    FAILED = "failed"

class ReleaseStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"

class UserRole(str, Enum):
    SYSTEM_ADMIN = "system_admin"
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    AUDITOR = "auditor"

class DataResidency(str, Enum):
    US = "us-east-1"
    EU = "eu-central-1"
    IN = "ap-south-1"
    GLOBAL = "global"

class PolicyDecisionType(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_HITL = "REQUIRE_HITL"

class PatchRiskLevel(str, Enum):
    SAFE_AUTO = "SAFE_AUTO"                 # Level 1: Meta tags, canonical, json-ld schema, robots.txt
    HUMAN_APPROVAL = "HUMAN_APPROVAL"       # Level 2: Titles, descriptions, hero headlines, FAQ copy
    DEVELOPER_REQUIRED = "DEVELOPER_REQUIRED" # Level 3: App code, routing, security headers, layout.tsx

class PatchOperation(str, Enum):
    REPLACE = "REPLACE"
    INSERT_HEAD = "INSERT_HEAD"
    INSERT_BODY = "INSERT_BODY"
    UPDATE_JSONLD = "UPDATE_JSONLD"
    UPDATE_FILE = "UPDATE_FILE"
    APPEND_ROBOTS = "APPEND_ROBOTS"

class PatchApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"

class ConnectorType(str, Enum):
    WORDPRESS = "wordpress"
    GITHUB = "github"
    SHOPIFY = "shopify"
    WEBFLOW = "webflow"
    GOOGLE_SEARCH_CONSOLE = "google_search_console"
    GENERIC = "generic"

class ConnectorHealthStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"

class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    NOT_CONNECTED = "NOT_CONNECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    PARTIAL = "PARTIAL"

class EvidenceOrigin(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class MetricProvenanceState(str, Enum):
    MEASURED = "MEASURED"
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    SIMULATED = "SIMULATED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_CONNECTED = "NOT_CONNECTED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


