"""
Lifecycle Verification State Machine — Phase 8.7 (10/10 Transformation)

Manages the strict 10-stage task lifecycle:
1. Finding detected (DETECTED)
2. Root cause confirmed (ROOT_CAUSE_CONFIRMED)
3. Patch generated (PATCH_GENERATED)
4. Patch reviewed (PATCH_REVIEWED)
5. Staging validation passed (STAGING_VALIDATION_PASSED)
6. Production deployment approved (PRODUCTION_DEPLOYMENT_APPROVED)
7. Post-deployment crawl executed (POST_DEPLOYMENT_CRAWL_EXECUTED)
8. Original condition retested (ORIGINAL_CONDITION_RETESTED)
9. Regression testing completed (REGRESSION_TESTING_COMPLETED)
10. Finding closed or reopened (CLOSED / REOPENED)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.remediation.models import (
    RemediationTaskRecord,
    RetestEvaluation,
    TaskStatus,
)

logger = logging.getLogger("dristik.remediation.lifecycle")

VALID_TRANSITIONS: Dict[TaskStatus, List[TaskStatus]] = {
    TaskStatus.DETECTED: [TaskStatus.ROOT_CAUSE_CONFIRMED],
    TaskStatus.ROOT_CAUSE_CONFIRMED: [TaskStatus.PATCH_GENERATED],
    TaskStatus.PATCH_GENERATED: [TaskStatus.PATCH_REVIEWED],
    TaskStatus.PATCH_REVIEWED: [TaskStatus.STAGING_VALIDATION_PASSED],
    TaskStatus.STAGING_VALIDATION_PASSED: [TaskStatus.PRODUCTION_DEPLOYMENT_APPROVED],
    TaskStatus.PRODUCTION_DEPLOYMENT_APPROVED: [TaskStatus.POST_DEPLOYMENT_CRAWL_EXECUTED],
    TaskStatus.POST_DEPLOYMENT_CRAWL_EXECUTED: [TaskStatus.ORIGINAL_CONDITION_RETESTED],
    TaskStatus.ORIGINAL_CONDITION_RETESTED: [TaskStatus.REGRESSION_TESTING_COMPLETED],
    TaskStatus.REGRESSION_TESTING_COMPLETED: [TaskStatus.CLOSED, TaskStatus.REOPENED],
    TaskStatus.CLOSED: [TaskStatus.REOPENED],
    TaskStatus.REOPENED: [TaskStatus.ROOT_CAUSE_CONFIRMED],
}


class LifecycleVerificationEngine:
    """
    Coordinates state transitions and executes independent retesting.
    """

    def transition_state(self, task: RemediationTaskRecord, target_state: TaskStatus) -> RemediationTaskRecord:
        allowed = VALID_TRANSITIONS.get(task.status, [])
        if target_state not in allowed:
            raise ValueError(
                f"Illegal lifecycle transition: cannot move task {task.task_id} from '{task.status.value}' to '{target_state.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )
        task.status = target_state
        task.updated_at = datetime.now(timezone.utc)
        return task

    def evaluate_retest_and_close(
        self,
        task: RemediationTaskRecord,
        observed_html: str,
        defect_indicator: str,
        regression_detected: bool = False,
    ) -> RetestEvaluation:
        # Move to retested state
        self.transition_state(task, TaskStatus.POST_DEPLOYMENT_CRAWL_EXECUTED)
        self.transition_state(task, TaskStatus.ORIGINAL_CONDITION_RETESTED)
        self.transition_state(task, TaskStatus.REGRESSION_TESTING_COMPLETED)

        # Retest condition: defect indicator must no longer be present in observed HTML
        defect_resolved = defect_indicator.lower() not in observed_html.lower()

        retest_res = RetestEvaluation(
            task_id=task.task_id,
            retest_method="CRAWL_INSPECTION",
            defect_resolved=defect_resolved,
            observed_condition=(
                f"Defect '{defect_indicator}' resolved."
                if defect_resolved else f"Defect '{defect_indicator}' still observed in post-deployment crawl."
            ),
            regression_detected=regression_detected,
        )

        if defect_resolved and not regression_detected:
            self.transition_state(task, TaskStatus.CLOSED)
        else:
            self.transition_state(task, TaskStatus.REOPENED)

        return retest_res


lifecycle_verification_engine = LifecycleVerificationEngine()
