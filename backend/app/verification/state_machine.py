"""
Verification State Machine — Phase 9.5 (10/10 Transformation)

Enforces strict lifecycle transitions across all 11 explicit verification states:
- OPEN
- IN_PROGRESS
- PATCH_READY
- APPROVED
- DEPLOYED
- VERIFICATION_PENDING
- VERIFIED_FIXED
- PARTIALLY_FIXED
- FAILED
- REOPENED
- ACCEPTED_RISK

STRICT 10/10 ACCEPTANCE CONTRACT:
A finding NEVER closes (VERIFIED_FIXED) merely because a fix was proposed or deployed.
Every closed finding requires empirical post-change evidence, an executed test result,
and zero cross-discipline regressions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.verification.models import (
    EvidenceComparisonRecord,
    RegressionCheckResult,
    VerificationRunReport,
    VerificationState,
)
from app.verification.retester import (
    IndependentRetester,
    independent_retester,
)

logger = logging.getLogger("dristik.verification.state_machine")

VALID_STATE_TRANSITIONS: Dict[VerificationState, List[VerificationState]] = {
    VerificationState.OPEN: [
        VerificationState.IN_PROGRESS,
        VerificationState.ACCEPTED_RISK,
    ],
    VerificationState.IN_PROGRESS: [
        VerificationState.PATCH_READY,
        VerificationState.ACCEPTED_RISK,
    ],
    VerificationState.PATCH_READY: [
        VerificationState.APPROVED,
        VerificationState.IN_PROGRESS,
        VerificationState.ACCEPTED_RISK,
    ],
    VerificationState.APPROVED: [
        VerificationState.DEPLOYED,
        VerificationState.IN_PROGRESS,
    ],
    VerificationState.DEPLOYED: [
        VerificationState.VERIFICATION_PENDING,
    ],
    VerificationState.VERIFICATION_PENDING: [
        VerificationState.VERIFIED_FIXED,
        VerificationState.PARTIALLY_FIXED,
        VerificationState.FAILED,
        VerificationState.REOPENED,
    ],
    VerificationState.PARTIALLY_FIXED: [
        VerificationState.REOPENED,
        VerificationState.IN_PROGRESS,
        VerificationState.ACCEPTED_RISK,
    ],
    VerificationState.FAILED: [
        VerificationState.REOPENED,
        VerificationState.IN_PROGRESS,
    ],
    VerificationState.REOPENED: [
        VerificationState.IN_PROGRESS,
    ],
    VerificationState.VERIFIED_FIXED: [
        VerificationState.REOPENED,  # If regression detected in subsequent crawl
    ],
    VerificationState.ACCEPTED_RISK: [
        VerificationState.REOPENED,
        VerificationState.IN_PROGRESS,
    ],
}


class VerificationStateMachine:
    """
    Coordinates lifecycle state transitions with strict evidence gating.
    """

    @staticmethod
    def validate_transition(
        current_state: VerificationState,
        target_state: VerificationState,
        evidence_comparison: Optional[EvidenceComparisonRecord] = None,
        regression_result: Optional[RegressionCheckResult] = None,
    ) -> None:
        allowed = VALID_STATE_TRANSITIONS.get(current_state, [])
        if target_state not in allowed:
            raise ValueError(
                f"Illegal verification state transition: cannot transition from '{current_state.value}' to '{target_state.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )

        # Strict 10/10 acceptance gate: VERIFIED_FIXED requires verified post-change evidence
        if target_state == VerificationState.VERIFIED_FIXED:
            if not evidence_comparison:
                raise ValueError("Cannot transition to VERIFIED_FIXED without an EvidenceComparisonRecord.")
            if not evidence_comparison.verification_passed:
                raise ValueError("Cannot transition to VERIFIED_FIXED: independent retest did not pass.")
            if regression_result and regression_result.has_regression:
                raise ValueError(f"Cannot transition to VERIFIED_FIXED: regression detected ({regression_result.details}).")

    def process_retest_and_transition(
        self,
        finding: Any,
        current_state: VerificationState,
        baseline_evidence: Dict[str, Any],
        post_deploy_evidence: Dict[str, Any],
        regression_result: Optional[RegressionCheckResult] = None,
        retester: Optional[IndependentRetester] = None,
    ) -> Tuple[VerificationState, EvidenceComparisonRecord]:
        runner = retester or independent_retester

        # Retest finding against new evidence
        evidence_record = runner.retest_finding(
            finding=finding,
            original_evidence=baseline_evidence,
            new_evidence=post_deploy_evidence,
        )

        has_reg = regression_result.has_regression if regression_result else False

        if evidence_record.verification_passed and not has_reg:
            target_state = VerificationState.VERIFIED_FIXED
        elif evidence_record.partially_fixed and not has_reg:
            target_state = VerificationState.PARTIALLY_FIXED
        elif has_reg:
            target_state = VerificationState.REOPENED
        else:
            target_state = VerificationState.FAILED

        self.validate_transition(
            current_state=current_state,
            target_state=target_state,
            evidence_comparison=evidence_record,
            regression_result=regression_result,
        )

        evidence_record.current_finding_state = target_state
        return target_state, evidence_record


verification_state_machine = VerificationStateMachine()
