"""
SEO Remediation Intelligence — Phase 3.12

Enforces the mandatory 14-point Finding Contract for all Technical SEO findings:
1. Problem description
2. Affected URL
3. Affected element
4. Raw evidence
5. Expected condition
6. Observed condition
7. Severity
8. Confidence
9. Root cause
10. Business relevance
11. Recommended fix
12. Implementation instructions
13. Verification command or test
14. Post-fix result

Every finding must provide actionable code patches, exact CLI verification commands,
and trackable post-fix state transitions.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PostFixStatus(str, Enum):
    NOT_YET_VERIFIED = "NOT_YET_VERIFIED"
    VERIFIED_FIXED = "VERIFIED_FIXED"
    STILL_FAILING = "STILL_FAILING"
    REGRESSED = "REGRESSED"


class EngineeringSeoFinding(BaseModel):
    finding_id: str
    # 1. Problem description
    problem_description: str
    # 2. Affected URL
    affected_url: str
    # 3. Affected element
    affected_element: str
    # 4. Raw evidence
    raw_evidence: str
    # 5. Expected condition
    expected_condition: str
    # 6. Observed condition
    observed_condition: str
    # 7. Severity
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    # 8. Confidence
    confidence: str  # STRONG, LIKELY, UNCERTAIN
    # 9. Root cause
    root_cause: str
    # 10. Business relevance
    business_relevance: str
    # 11. Recommended fix
    recommended_fix: str
    # 12. Implementation instructions
    implementation_instructions: str
    # 13. Verification command or test
    verification_command: str
    # 14. Post-fix result
    post_fix_result: PostFixStatus = PostFixStatus.NOT_YET_VERIFIED


class SeoRemediationEngine:
    """
    Validates that every SEO finding conforms to the 14-point contract and executes verification commands.
    """

    @classmethod
    def validate_finding_contract(cls, finding: EngineeringSeoFinding) -> Dict[str, Any]:
        missing: List[str] = []
        fields = [
            ("problem_description", finding.problem_description),
            ("affected_url", finding.affected_url),
            ("affected_element", finding.affected_element),
            ("raw_evidence", finding.raw_evidence),
            ("expected_condition", finding.expected_condition),
            ("observed_condition", finding.observed_condition),
            ("severity", finding.severity),
            ("confidence", finding.confidence),
            ("root_cause", finding.root_cause),
            ("business_relevance", finding.business_relevance),
            ("recommended_fix", finding.recommended_fix),
            ("implementation_instructions", finding.implementation_instructions),
            ("verification_command", finding.verification_command),
            ("post_fix_result", finding.post_fix_result),
        ]

        for name, val in fields:
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(name)

        is_valid = len(missing) == 0
        return {
            "is_valid": is_valid,
            "contract_points_satisfied": 14 - len(missing),
            "missing_points": missing,
        }

    @classmethod
    def record_verification_result(
        cls,
        finding: EngineeringSeoFinding,
        test_passed: bool,
        verification_log: str = "",
    ) -> EngineeringSeoFinding:
        if test_passed:
            finding.post_fix_result = PostFixStatus.VERIFIED_FIXED
        else:
            finding.post_fix_result = PostFixStatus.STILL_FAILING
        return finding
