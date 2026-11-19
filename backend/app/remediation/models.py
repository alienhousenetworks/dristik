"""
Dristik AI Phase 8 — AI Remediation Engine Domain Models.
Defines canonical data structures for:
- 14-field canonical remediation backlog (Phase 8.1)
- 10 specialist root-cause & remediation agents (Phase 8.2)
- 8 codebase and CMS connectors with permission boundaries (Phase 8.3)
- 10-type universal patch generation with atomic rollbacks (Phase 8.4)
- 9-step patch validation pipeline (Phase 8.5)
- 5-tier human governance & deployment (Phase 8.6)
- 10-stage lifecycle state machine (Phase 8.7)
- 3-tier impact attribution (Phase 8.8)
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Phase 8.1: Backlog Models ---
class TaskStatus(str, Enum):
    DETECTED = "DETECTED"
    ROOT_CAUSE_CONFIRMED = "ROOT_CAUSE_CONFIRMED"
    PATCH_GENERATED = "PATCH_GENERATED"
    PATCH_REVIEWED = "PATCH_REVIEWED"
    STAGING_VALIDATION_PASSED = "STAGING_VALIDATION_PASSED"
    PRODUCTION_DEPLOYMENT_APPROVED = "PRODUCTION_DEPLOYMENT_APPROVED"
    POST_DEPLOYMENT_CRAWL_EXECUTED = "POST_DEPLOYMENT_CRAWL_EXECUTED"
    ORIGINAL_CONDITION_RETESTED = "ORIGINAL_CONDITION_RETESTED"
    REGRESSION_TESTING_COMPLETED = "REGRESSION_TESTING_COMPLETED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class RemediationTaskRecord(BaseModel):
    task_id: str
    finding_id: str
    root_cause: str
    affected_urls: List[str] = Field(default_factory=list)
    affected_templates: List[str] = Field(default_factory=list)
    recommended_action: str
    business_impact: str
    technical_severity: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    confidence: float = Field(..., ge=0.0, le=1.0)
    estimated_effort: str = "MEDIUM"  # LOW (<2h), MEDIUM (2-8h), HIGH (>8h)
    dependencies: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    owner: str = "Engineering"
    status: TaskStatus = TaskStatus.DETECTED
    verification_criteria: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="ignore")


# --- Phase 8.2: Agent Council Models ---
class SpecialistAgentRole(str, Enum):
    TECHNICAL_DIAGNOSIS = "TECHNICAL_DIAGNOSIS"
    SEO_REMEDIATION = "SEO_REMEDIATION"
    GEO_REMEDIATION = "GEO_REMEDIATION"
    AEO_REMEDIATION = "AEO_REMEDIATION"
    CRO_REMEDIATION = "CRO_REMEDIATION"
    CONTENT_REMEDIATION = "CONTENT_REMEDIATION"
    CODE_REMEDIATION = "CODE_REMEDIATION"
    SECURITY_REVIEWER = "SECURITY_REVIEWER"
    ADVERSARIAL_CRITIC = "ADVERSARIAL_CRITIC"
    VERIFICATION_AGENT = "VERIFICATION_AGENT"


class AgentRecommendation(BaseModel):
    agent_role: SpecialistAgentRole
    finding_id: str
    diagnosis: str
    proposed_remedy: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    potential_risks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Phase 8.3: Platform Connectors & Boundaries ---
class PlatformType(str, Enum):
    WORDPRESS = "WORDPRESS"
    WOOCOMMERCE = "WOOCOMMERCE"
    SHOPIFY = "SHOPIFY"
    WEBFLOW = "WEBFLOW"
    NEXT_JS = "NEXT_JS"
    REACT_APP = "REACT_APP"
    CUSTOM_WEBSITE = "CUSTOM_WEBSITE"
    STATIC_SITE = "STATIC_SITE"


class PlatformCapability(BaseModel):
    platform: PlatformType
    can_modify_templates: bool = True
    can_modify_styles: bool = True
    can_modify_client_js: bool = True
    can_modify_server_code: bool = False
    can_modify_server_config: bool = False
    can_modify_redirects: bool = True
    can_modify_metadata: bool = True
    can_modify_structured_data: bool = True
    allowed_scopes: List[str] = Field(default_factory=list)
    boundary_notes: str = ""


# --- Phase 8.4: Universal Patch Generation ---
class PatchType(str, Enum):
    HTML = "HTML"
    CSS = "CSS"
    JAVASCRIPT = "JAVASCRIPT"
    REACT_COMPONENT = "REACT_COMPONENT"
    METADATA = "METADATA"
    JSON_LD = "JSON_LD"
    CONTENT = "CONTENT"
    INTERNAL_LINKING = "INTERNAL_LINKING"
    CONFIGURATION = "CONFIGURATION"
    REDIRECT_RULES = "REDIRECT_RULES"


class RollbackPatch(BaseModel):
    rollback_id: str
    file_path: str
    original_code: str
    rollback_code: str
    explanation: str = "Automated rollback to pre-patch state."
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UniversalPatch(BaseModel):
    patch_id: str
    patch_type: PatchType
    original_code: str
    proposed_code: str
    file_path: str
    line_references: str = "L1-L10"
    change_explanation: str
    related_finding_id: str
    dependencies: List[str] = Field(default_factory=list)
    rollback_patch: RollbackPatch
    validation_requirements: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Phase 8.5: Patch Validation ---
class ValidationStepResult(BaseModel):
    step_name: str
    passed: bool
    details: str = ""
    error_message: Optional[str] = None


class PatchValidationReport(BaseModel):
    patch_id: str
    all_passed: bool
    step_results: List[ValidationStepResult] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Phase 8.6: Human Governance & Deployment ---
class ApprovalTier(str, Enum):
    RECOMMENDATION_ONLY = "RECOMMENDATION_ONLY"
    GENERATE_CODE_PATCH = "GENERATE_CODE_PATCH"
    APPLY_TO_STAGING = "APPLY_TO_STAGING"
    DEPLOY_TO_PRODUCTION = "DEPLOY_TO_PRODUCTION"
    CHANGE_CRITICAL_INFRASTRUCTURE = "CHANGE_CRITICAL_INFRASTRUCTURE"


class DeploymentLogEntry(BaseModel):
    deployment_id: str
    patch_id: str
    target_environment: str  # STAGING, PRODUCTION
    authorized_by: str
    authorization_tier: ApprovalTier
    status: str = "SUCCESS"  # SUCCESS, FAILED, ROLLED_BACK
    deployed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""


# --- Phase 8.7: Lifecycle Verification ---
class RetestEvaluation(BaseModel):
    task_id: str
    retest_method: str = "CRAWL_INSPECTION"
    defect_resolved: bool
    observed_condition: str
    regression_detected: bool = False
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Phase 8.8: Impact Attribution ---
class ImpactAttribution(BaseModel):
    task_id: str
    finding_id: str
    technical_success: bool = False
    technical_evidence: str = ""
    search_ai_outcome_observed: bool = False
    search_ai_evidence: Optional[str] = None
    commercial_outcome_observed: bool = False
    commercial_evidence: Optional[str] = None
    historical_observation_window_days: int = 30
    zero_fabrication_confirmed: bool = True
