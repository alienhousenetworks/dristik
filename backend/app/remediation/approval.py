"""
Dristik AI Patch Approval & Governance Engine
Manages Human-In-The-Loop (HITL) review, auto-approval policies, assignments, and lifecycle states.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.domain.models import Finding, RemediationPatch
from app.domain.enums import PatchRiskLevel, PatchApprovalStatus
from app.core.security.enterprise_audit_logger import get_enterprise_audit_logger

class PatchApprovalManager:
    """
    Manages approval status transitions, assignments, and governance for remediation patches and findings.
    """
    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []

    def can_auto_approve(self, patch: RemediationPatch) -> bool:
        """
        Level 1 SAFE_AUTO patches can be queued without manual signoff.
        Factual schema, pricing, reviews, and hallucination-driven changes
        still require a person. Auto-approval is not a production deploy.
        """
        if patch.risk_level != PatchRiskLevel.SAFE_AUTO:
            return False
        from app.commercial.remediation_policy import patch_requires_human_approval
        return not patch_requires_human_approval(patch)

    def approve_patch(
        self,
        patch: RemediationPatch,
        approver: str = "analyst@dristik.ai",
        notes: Optional[str] = None
    ) -> RemediationPatch:
        patch.approval_status = PatchApprovalStatus.APPROVED
        patch.approver = approver
        patch.approved_at = datetime.now(timezone.utc).isoformat()
        
        entry = {
            "action": "APPROVE",
            "patch_id": patch.patch_id,
            "risk_level": patch.risk_level.value,
            "approver": approver,
            "timestamp": patch.approved_at,
            "notes": notes
        }
        self._audit_log.append(entry)
        try:
            org_id = (patch.metadata_payload or {}).get("org_id") or "default_org"
            get_enterprise_audit_logger().log_event(
                org_id=org_id,
                action="patch.approved",
                resource_type="remediation_patch",
                resource_id=patch.patch_id,
                user_id=approver,
                payload=entry,
            )
        except Exception:
            pass
        return patch

    def reject_patch(
        self,
        patch: RemediationPatch,
        rejector: str = "analyst@dristik.ai",
        reason: Optional[str] = None
    ) -> RemediationPatch:
        patch.approval_status = PatchApprovalStatus.REJECTED
        patch.approver = rejector
        patch.approved_at = datetime.now(timezone.utc).isoformat()
        
        entry = {
            "action": "REJECT",
            "patch_id": patch.patch_id,
            "risk_level": patch.risk_level.value,
            "rejector": rejector,
            "timestamp": patch.approved_at,
            "reason": reason
        }
        self._audit_log.append(entry)
        try:
            org_id = (patch.metadata_payload or {}).get("org_id") or "default_org"
            get_enterprise_audit_logger().log_event(
                org_id=org_id,
                action="patch.rejected",
                resource_type="remediation_patch",
                resource_id=patch.patch_id,
                user_id=rejector,
                payload=entry,
            )
        except Exception:
            pass
        return patch

    def assign_patch(
        self,
        patch: RemediationPatch,
        assignee_id: str,
        assigned_by: str,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> RemediationPatch:
        now = datetime.now(timezone.utc).isoformat()
        patch.assignee_id = assignee_id
        patch.assigned_by = assigned_by
        patch.assigned_at = now
        patch.due_date = due_date

        entry = {
            "action": "ASSIGN_PATCH",
            "patch_id": patch.patch_id,
            "finding_id": patch.finding_id,
            "assignee_id": assignee_id,
            "assigned_by": assigned_by,
            "due_date": due_date,
            "timestamp": now,
            "notes": notes,
        }
        self._audit_log.append(entry)
        try:
            org_id = (patch.metadata_payload or {}).get("org_id") or "default_org"
            get_enterprise_audit_logger().log_event(
                org_id=org_id,
                action="patch.assigned",
                resource_type="remediation_patch",
                resource_id=patch.patch_id,
                user_id=assigned_by,
                payload=entry,
            )
        except Exception:
            pass
        return patch

    def assign_finding(
        self,
        finding: Finding,
        assignee_id: str,
        assigned_by: str,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Finding:
        now = datetime.now(timezone.utc).isoformat()
        finding.assignee_id = assignee_id
        finding.assigned_by = assigned_by
        finding.assigned_at = now
        finding.due_date = due_date
        finding.owner = assignee_id

        entry = {
            "action": "ASSIGN_FINDING",
            "finding_id": finding.finding_id,
            "assignee_id": assignee_id,
            "assigned_by": assigned_by,
            "due_date": due_date,
            "timestamp": now,
            "notes": notes,
        }
        self._audit_log.append(entry)
        try:
            resolved_org = org_id or getattr(finding, "org_id", None) or "default_org"
            get_enterprise_audit_logger().log_event(
                org_id=resolved_org,
                action="finding.assigned",
                resource_type="finding",
                resource_id=finding.finding_id,
                user_id=assigned_by,
                payload=entry,
            )
        except Exception:
            pass
        return finding

    def get_audit_trail(self, patch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if patch_id:
            return [
                entry for entry in self._audit_log
                if entry.get("patch_id") == patch_id or entry.get("finding_id") == patch_id
            ]
        return list(self._audit_log)

approval_manager = PatchApprovalManager()
