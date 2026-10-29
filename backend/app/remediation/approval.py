"""
Dristik AI Patch Approval & Governance Engine
Manages Human-In-The-Loop (HITL) review, auto-approval policies, and lifecycle states.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.domain.models import RemediationPatch
from app.domain.enums import PatchRiskLevel, PatchApprovalStatus

class PatchApprovalManager:
    """
    Manages approval status transitions and governance for remediation patches.
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
        
        self._audit_log.append({
            "action": "APPROVE",
            "patch_id": patch.patch_id,
            "risk_level": patch.risk_level.value,
            "approver": approver,
            "timestamp": patch.approved_at,
            "notes": notes
        })
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
        
        self._audit_log.append({
            "action": "REJECT",
            "patch_id": patch.patch_id,
            "risk_level": patch.risk_level.value,
            "rejector": rejector,
            "timestamp": patch.approved_at,
            "reason": reason
        })
        return patch

    def get_audit_trail(self, patch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if patch_id:
            return [entry for entry in self._audit_log if entry.get("patch_id") == patch_id]
        return list(self._audit_log)

approval_manager = PatchApprovalManager()
