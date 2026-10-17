from enum import Enum

class AuditStage(str, Enum):
    STAGE_1_PLAN = "STAGE_1_PLAN"
    STAGE_2_CRAWL = "STAGE_2_CRAWL"
    STAGE_3_TECHNICAL = "STAGE_3_TECHNICAL"
    STAGE_4_CONTENT = "STAGE_4_CONTENT"
    STAGE_5_AUTHORITY = "STAGE_5_AUTHORITY"
    STAGE_6_GEO_AEO = "STAGE_6_GEO_AEO"
    STAGE_7_BUSINESS = "STAGE_7_BUSINESS"
    STAGE_8_SYNTHESIS = "STAGE_8_SYNTHESIS"

class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class FindingCategory(str, Enum):
    TECHNICAL = "TECHNICAL"
    CONTENT = "CONTENT"
    AUTHORITY = "AUTHORITY"
    CRO = "CRO"
    GEO = "GEO"
    AEO = "AEO"

class ProvenanceState(str, Enum):
    RAW_TELEMETRY = "RAW_TELEMETRY"
    RENDERED_DOM = "RENDERED_DOM"
    EXTRACTED_CONTENT = "EXTRACTED_CONTENT"
    THIRD_PARTY_OBSERVATION = "THIRD_PARTY_OBSERVATION"
    SYNTHESIZED_INFERENCE = "SYNTHESIZED_INFERENCE"

class UserRole(str, Enum):
    SYSTEM_ADMIN = "system_admin"
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
