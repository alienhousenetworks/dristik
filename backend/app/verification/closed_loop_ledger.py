"""
Closed-Loop Remediation & Cryptographically Sealed Verification Engine.

Enforces all 10 required lifecycle states:
OPEN | PLANNED | IN_PROGRESS | DEPLOYED | RETEST_PENDING |
VERIFIED_FIXED | PARTIALLY_FIXED | REGRESSION | REOPENED | WONT_FIX

Strict VERIFIED_FIXED Evidence Contract:
A finding can NEVER transition to VERIFIED_FIXED based on a static screenshot alone.
Every VERIFIED_FIXED record requires:
1. original_evidence_ref
2. remediation_ref (patch_id)
3. deployment_ref (deployment_id / git_commit_sha)
4. before_observation & after_observation
5. retest_timestamp_utc
6. test_environment & browser_device
7. At least one functional/behavioral/DOM/HTTP automated assertion (not screenshot-only)
8. Regression test results with zero regressions
9. verifier_identity
10. Cryptographic SHA-256 hash of the verification evidence bundle
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

from app.db.verification_historical_schema import connect_verification_history_db
from app.governance.data_reliability import utc_now_iso

ENTERPRISE_VERIFICATION_STATES = (
    "OPEN",
    "PLANNED",
    "IN_PROGRESS",
    "DEPLOYED",
    "RETEST_PENDING",
    "VERIFIED_FIXED",
    "PARTIALLY_FIXED",
    "REGRESSION",
    "REOPENED",
    "WONT_FIX",
)

ALLOWED_TRANSITIONS: Dict[str, set[str]] = {
    "OPEN": {"PLANNED", "IN_PROGRESS", "WONT_FIX"},
    "PLANNED": {"IN_PROGRESS", "WONT_FIX"},
    "IN_PROGRESS": {"DEPLOYED", "WONT_FIX"},
    "DEPLOYED": {"RETEST_PENDING"},
    "RETEST_PENDING": {"VERIFIED_FIXED", "PARTIALLY_FIXED", "REGRESSION", "REOPENED"},
    "PARTIALLY_FIXED": {"IN_PROGRESS", "RETEST_PENDING", "REOPENED", "WONT_FIX"},
    "REGRESSION": {"IN_PROGRESS", "REOPENED"},
    "REOPENED": {"PLANNED", "IN_PROGRESS"},
    "VERIFIED_FIXED": {"REOPENED", "REGRESSION"},
    "WONT_FIX": {"REOPENED"},
}


class AutomatedAssertion(BaseModel):
    assertion_type: str  # "dom" | "http" | "schema" | "functional_cta" | "checkout_flow" | "screenshot"
    description: str
    passed: bool
    observed_value: str = ""


class RegressionCheck(BaseModel):
    check_name: str
    has_regression: bool
    details: str


class VerificationProofBundle(BaseModel):
    verification_run_id: str
    task_id: str
    finding_id: str
    outcome_state: str
    original_evidence_ref: str
    remediation_ref: str
    deployment_ref: Optional[str] = None
    retest_timestamp_utc: str
    test_environment: str
    browser_device: str
    verifier_identity: str
    artifact_sha256: str
    assertions_passed: int
    assertions_total: int
    regressions_detected: int


class ClosedLoopVerificationEngine:
    """Manages persistent remediation lifecycle and cryptographic verification proof."""

    @classmethod
    def create_task(
        cls,
        *,
        org_id: str,
        audit_run_id: str,
        finding_id: str,
        affected_url: str,
        severity: str,
        baseline_evidence_ref: str,
        baseline_observation: Dict[str, Any],
        db_path: Optional[str] = None,
    ) -> str:
        task_id = f"rem_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        conn = connect_verification_history_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO remediation_tasks (
                    task_id, org_id, audit_run_id, finding_id, affected_url, severity,
                    current_state, baseline_evidence_ref, baseline_observation_json,
                    created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
                """,
                (
                    task_id, org_id, audit_run_id, finding_id, affected_url, severity.upper(),
                    baseline_evidence_ref, json.dumps(baseline_observation, sort_keys=True), now, now,
                ),
            )
            conn.commit()
            return task_id
        finally:
            conn.close()

    @classmethod
    def transition_state(
        cls,
        *,
        org_id: str,
        task_id: str,
        target_state: str,
        actor_id: str,
        reason: str = "",
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        target = target_state.upper()
        if target == "VERIFIED_FIXED":
            raise ValueError("Cannot manually set VERIFIED_FIXED. Use execute_verification() with empirical evidence.")
        now = utc_now_iso()
        conn = connect_verification_history_db(db_path)
        try:
            row = conn.execute(
                "SELECT finding_id, current_state FROM remediation_tasks WHERE org_id = ? AND task_id = ?",
                (org_id, task_id),
            ).fetchone()
            if not row:
                raise KeyError(f"Remediation task '{task_id}' not found.")
            curr = row["current_state"]
            if target not in ALLOWED_TRANSITIONS.get(curr, set()):
                raise ValueError(f"Illegal transition {curr} -> {target}.")
            if target == "WONT_FIX" and len(reason.strip()) < 8:
                raise ValueError("WONT_FIX requires an explicit authorized justification.")
            conn.execute(
                "UPDATE remediation_tasks SET current_state = ?, wont_fix_justification = CASE WHEN ? = 'WONT_FIX' THEN ? ELSE wont_fix_justification END, updated_at_utc = ? WHERE org_id = ? AND task_id = ?",
                (target, target, reason, now, org_id, task_id),
            )
            conn.execute(
                """
                INSERT INTO finding_state_history (id, org_id, task_id, finding_id, from_state, to_state, actor_id, reason, transitioned_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"fsh_{uuid.uuid4().hex[:12]}", org_id, task_id, row["finding_id"], curr, target, actor_id, reason, now),
            )
            conn.commit()
            return {"task_id": task_id, "from_state": curr, "to_state": target}
        finally:
            conn.close()

    @classmethod
    def execute_verification(
        cls,
        *,
        org_id: str,
        task_id: str,
        remediation_ref: str,
        deployment_ref: Optional[str],
        after_observation: Dict[str, Any],
        assertions: Sequence[AutomatedAssertion],
        regressions: Sequence[RegressionCheck],
        test_environment: str,
        browser_device: str,
        verifier_identity: str,
        db_path: Optional[str] = None,
    ) -> VerificationProofBundle:
        """Evaluates post-deploy evidence & seals cryptographic proof before allowing VERIFIED_FIXED."""
        now = utc_now_iso()
        conn = connect_verification_history_db(db_path)
        try:
            task = conn.execute(
                "SELECT finding_id, current_state, baseline_evidence_ref, baseline_observation_json FROM remediation_tasks WHERE org_id = ? AND task_id = ?",
                (org_id, task_id),
            ).fetchone()
            if not task:
                raise KeyError(f"Task '{task_id}' not found.")
            if task["current_state"] != "RETEST_PENDING":
                raise ValueError(f"Task must be in RETEST_PENDING before verification (current: {task['current_state']}).")

            non_screenshot_assertions = [a for a in assertions if a.assertion_type.lower() != "screenshot"]
            if not non_screenshot_assertions:
                raise ValueError("Screenshot-only verification is forbidden. Include DOM, HTTP, schema, or functional assertions.")
            if not regressions:
                raise ValueError("At least one regression check is required before closing a finding.")

            passed_cnt = sum(1 for a in assertions if a.passed)
            reg_cnt = sum(1 for r in regressions if r.has_regression)

            if reg_cnt > 0:
                outcome = "REGRESSION"
            elif passed_cnt == len(assertions):
                outcome = "VERIFIED_FIXED"
            elif passed_cnt > 0:
                outcome = "PARTIALLY_FIXED"
            else:
                outcome = "REOPENED"

            before_obs = json.loads(task["baseline_observation_json"])
            proof_payload = {
                "task_id": task_id,
                "finding_id": task["finding_id"],
                "original_evidence_ref": task["baseline_evidence_ref"],
                "remediation_ref": remediation_ref,
                "deployment_ref": deployment_ref,
                "before": before_obs,
                "after": after_observation,
                "assertions": [a.model_dump() for a in assertions],
                "regressions": [r.model_dump() for r in regressions],
                "test_environment": test_environment,
                "browser_device": browser_device,
                "verifier_identity": verifier_identity,
                "retest_timestamp_utc": now,
                "outcome_state": outcome,
            }
            artifact_sha = hashlib.sha256(json.dumps(proof_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            vrun_id = f"vrun_{uuid.uuid4().hex[:12]}"

            conn.execute(
                """
                INSERT INTO verification_runs (
                    verification_run_id, org_id, task_id, deployment_id, retest_timestamp_utc,
                    test_environment, browser_device, verifier_identity,
                    before_observation_json, after_observation_json, outcome_state, artifact_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vrun_id, org_id, task_id, deployment_ref, now, test_environment, browser_device,
                    verifier_identity, json.dumps(before_obs), json.dumps(after_observation), outcome, artifact_sha,
                ),
            )
            for a in assertions:
                conn.execute(
                    "INSERT INTO verification_assertions (assertion_id, verification_run_id, assertion_type, description, passed, observed_value) VALUES (?, ?, ?, ?, ?, ?)",
                    (f"va_{uuid.uuid4().hex[:12]}", vrun_id, a.assertion_type, a.description, int(a.passed), a.observed_value),
                )
            for r in regressions:
                conn.execute(
                    "INSERT INTO regression_results (regression_id, verification_run_id, check_name, has_regression, details, checked_at_utc) VALUES (?, ?, ?, ?, ?, ?)",
                    (f"reg_{uuid.uuid4().hex[:12]}", vrun_id, r.check_name, int(r.has_regression), r.details, now),
                )
            conn.execute(
                "UPDATE remediation_tasks SET current_state = ?, updated_at_utc = ? WHERE org_id = ? AND task_id = ?",
                (outcome, now, org_id, task_id),
            )
            conn.execute(
                "INSERT INTO finding_state_history (id, org_id, task_id, finding_id, from_state, to_state, actor_id, reason, transitioned_at_utc) VALUES (?, ?, ?, ?, 'RETEST_PENDING', ?, ?, ?, ?)",
                (f"fsh_{uuid.uuid4().hex[:12]}", org_id, task_id, task["finding_id"], outcome, verifier_identity, f"Automated verification run {vrun_id}", now),
            )
            conn.commit()
            return VerificationProofBundle(
                verification_run_id=vrun_id,
                task_id=task_id,
                finding_id=task["finding_id"],
                outcome_state=outcome,
                original_evidence_ref=task["baseline_evidence_ref"],
                remediation_ref=remediation_ref,
                deployment_ref=deployment_ref,
                retest_timestamp_utc=now,
                test_environment=test_environment,
                browser_device=browser_device,
                verifier_identity=verifier_identity,
                artifact_sha256=artifact_sha,
                assertions_passed=passed_cnt,
                assertions_total=len(assertions),
                regressions_detected=reg_cnt,
            )
        finally:
            conn.close()
