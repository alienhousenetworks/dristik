"""
Dristik AI Phase 9 — Independent Verification Engine Domain Models.

Defines canonical data structures for:
- 13 verification test categories (Phase 9.1)
- Machine-readable acceptance criteria (Phase 9.2)
- Independent retesting evidence comparison (Phase 9.3)
- Cross-discipline regression testing (Phase 9.4)
- 11-state verification lifecycle state machine (Phase 9.5)
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Phase 9.5: 11-State Verification Lifecycle ---
class VerificationState(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PATCH_READY = "PATCH_READY"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED_FIXED = "VERIFIED_FIXED"
    PARTIALLY_FIXED = "PARTIALLY_FIXED"
    FAILED = "FAILED"
    REOPENED = "REOPENED"
    ACCEPTED_RISK = "ACCEPTED_RISK"


# --- Phase 9.1: 13 Reusable Test Categories ---
class TestCategory(str, Enum):
    __test__ = False
    HTTP_CONDITION = "HTTP_CONDITION"
    HTML_CONDITION = "HTML_CONDITION"
    DOM_CONDITION = "DOM_CONDITION"
    METADATA = "METADATA"
    SCHEMA = "SCHEMA"
    INTERNAL_LINKS = "INTERNAL_LINKS"
    ACCESSIBILITY = "ACCESSIBILITY"
    PERFORMANCE = "PERFORMANCE"
    VISUAL_LAYOUT = "VISUAL_LAYOUT"
    FORM_BEHAVIOUR = "FORM_BEHAVIOUR"
    AI_ANSWER_OUTCOME = "AI_ANSWER_OUTCOME"
    SEARCH_PERFORMANCE = "SEARCH_PERFORMANCE"
    ANALYTICS_EVENTS = "ANALYTICS_EVENTS"


class TestExecutionResult(BaseModel):
    __test__ = False
    test_category: TestCategory
    name: str
    passed: bool
    observed_value: Any = None
    expected_condition: str
    execution_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    diagnostic_details: str = ""


# --- Phase 9.2: Finding-Specific Acceptance Criteria ---
class MachineAcceptanceCriterion(BaseModel):
    criterion_id: str
    finding_id: str
    test_category: TestCategory
    condition_name: str
    expected_condition_text: str
    target_selector: Optional[str] = None
    target_attribute: Optional[str] = None
    expected_value_pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    model_config = ConfigDict(extra="ignore")


# --- Phase 9.3: Independent Retesting Comparison ---
class EvidenceComparisonRecord(BaseModel):
    finding_id: str
    original_evidence: Dict[str, Any] = Field(default_factory=dict)
    new_evidence: Dict[str, Any] = Field(default_factory=dict)
    original_finding_summary: str
    current_finding_state: VerificationState
    test_environment: str = "PRODUCTION"  # STAGING, PRODUCTION, LOCAL_TEST_HARNESS
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verification_passed: bool
    partially_fixed: bool = False
    details: str = ""


# --- Phase 9.4: Cross-Discipline Regression Testing ---
class RegressionCheckResult(BaseModel):
    has_regression: bool
    regression_type: Optional[str] = None
    # Types: METADATA_RENDER, MOBILE_OVERFLOW, SCHEMA_SYNTAX, REDIRECT_LOOP, PERFORMANCE_SPIKE, BROKEN_LINKS
    details: str = ""
    affected_selector: Optional[str] = None


# --- Phase 9 Master Report ---
class VerificationRunReport(BaseModel):
    run_id: str
    finding_id: str
    initial_state: VerificationState
    final_state: VerificationState
    retest_passed: bool
    regression_detected: bool
    evidence_comparison: EvidenceComparisonRecord
    test_results: List[TestExecutionResult] = Field(default_factory=list)
    regression_details: Optional[RegressionCheckResult] = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_10_of_10_compliant: bool = True
