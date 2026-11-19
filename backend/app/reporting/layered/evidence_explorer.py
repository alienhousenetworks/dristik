"""Phase 11.4: Interactive Evidence Exploration Service.

Powers the in-app deep drilldown surface for evidence exploration:
- Open affected URLs
- View screenshots
- Inspect rendered DOM
- View raw cryptographic evidence
- Inspect finding history
- Compare before/after diffs
- Download code patches
- Assign remediation owners
- Approve changes across governance tiers
- Review independent verification outcomes
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from app.reporting.layered.models import EvidenceExplorerDTO, _utcnow


class InteractiveEvidenceExplorer:
    """Manages web application evidence exploration and remediation interaction."""

    def __init__(self):
        self._action_logs: dict[str, list[dict[str, Any]]] = {}
        self._assignments: dict[str, str] = {}
        self._approvals: dict[str, dict[str, Any]] = {}

    def get_evidence_explorer_view(
        self,
        finding_id: str,
        affected_url: str,
        screenshot_uri: Optional[str] = None,
        rendered_dom: Optional[str] = None,
        raw_evidence: Optional[dict[str, Any]] = None,
        history_records: Optional[list[dict[str, Any]]] = None,
        before_snippet: Optional[str] = None,
        after_snippet: Optional[str] = None,
        patch_diff: Optional[str] = None,
        verification_records: Optional[list[dict[str, Any]]] = None,
    ) -> EvidenceExplorerDTO:
        now = _utcnow()
        raw_payload = raw_evidence or {"finding_id": finding_id, "url": affected_url, "captured_at": now.isoformat()}
        raw_bytes = json.dumps(raw_payload, sort_keys=True).encode("utf-8")
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Before/after comparison diff
        b_snippet = before_snippet or "<title>Defective Old Snippet</title>"
        a_snippet = after_snippet or "<title>Optimized Semantic Snippet</title>"
        before_after_diff = {
            "before": b_snippet,
            "after": a_snippet,
            "diff_type": "HTML_INSPECTION",
            "modified_lines_count": 2,
        }

        # Patch representation
        p_diff = patch_diff or (
            f"--- a/template.html\n"
            f"+++ b/template.html\n"
            f"@@ -1,3 +1,3 @@\n"
            f"-{b_snippet}\n"
            f"+{a_snippet}\n"
        )
        download_url = f"/api/v1/remediation/patches/{finding_id}/download.diff"

        owner = self._assignments.get(finding_id, "Unassigned")
        appr_state = self._approvals.get(finding_id, {}).get("status", "PENDING_APPROVAL")
        v_outcomes = verification_records or [
            {
                "verification_id": f"vr_{finding_id.lower()}_01",
                "status": "VERIFICATION_PENDING",
                "timestamp": now.isoformat(),
                "test_method": "INDEPENDENT_HTTP_RETEST",
            }
        ]

        return EvidenceExplorerDTO(
            finding_id=finding_id,
            affected_url=affected_url,
            screenshot_uri=screenshot_uri or f"/assets/screenshots/{finding_id}.png",
            rendered_dom_snippet=rendered_dom or f"<div class='defect-container'>{b_snippet}</div>",
            raw_evidence_hash=raw_hash,
            raw_evidence_payload=raw_payload,
            finding_history=history_records or [{"timestamp": now.isoformat(), "event": "Discovered in audit"}],
            before_after_diff=before_after_diff,
            code_patch_download_url=download_url,
            patch_unified_diff=p_diff,
            remediation_owner=owner,
            approval_status=appr_state,
            verification_outcomes=v_outcomes,
        )

    def assign_remediation(self, finding_id: str, owner_email: str) -> dict[str, Any]:
        """Assign remediation ownership to an engineering team member."""
        self._assignments[finding_id] = owner_email
        event = {
            "finding_id": finding_id,
            "action": "ASSIGNED_OWNER",
            "owner": owner_email,
            "timestamp": _utcnow().isoformat(),
        }
        self._action_logs.setdefault(finding_id, []).append(event)
        return event

    def approve_change(self, finding_id: str, approver_tier: str, approved_by: str) -> dict[str, Any]:
        """Record an explicit governance approval tier confirmation."""
        approval = {
            "finding_id": finding_id,
            "status": "APPROVED",
            "approver_tier": approver_tier,
            "approved_by": approved_by,
            "timestamp": _utcnow().isoformat(),
        }
        self._approvals[finding_id] = approval
        self._action_logs.setdefault(finding_id, []).append(approval)
        return approval

    def record_verification_outcome(
        self, finding_id: str, outcome_status: str, notes: str = ""
    ) -> dict[str, Any]:
        """Record the result of an independent verification check."""
        record = {
            "finding_id": finding_id,
            "status": outcome_status,
            "notes": notes,
            "timestamp": _utcnow().isoformat(),
        }
        self._action_logs.setdefault(finding_id, []).append(record)
        return record

    def get_action_history(self, finding_id: str) -> list[dict[str, Any]]:
        return list(self._action_logs.get(finding_id, []))
