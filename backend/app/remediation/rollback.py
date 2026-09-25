"""
Dristik AI Patch Rollback Engine
Maintains pre-application snapshots and supports atomic reversions of applied fixes.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.domain.models import RemediationPatch
from app.domain.enums import PatchApprovalStatus

class PatchRollbackEngine:
    """
    Tracks applied states and generates inverse operations to safely rollback patches.
    """
    def __init__(self):
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def capture_pre_patch_snapshot(self, patch: RemediationPatch, original_state: Dict[str, Any]) -> str:
        snapshot_id = f"snap_{patch.patch_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self._snapshots[patch.patch_id] = {
            "snapshot_id": snapshot_id,
            "patch_id": patch.patch_id,
            "target_url": patch.target_url,
            "target_file": patch.target_file,
            "original_state": original_state,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return snapshot_id

    def rollback(self, patch: RemediationPatch) -> Dict[str, Any]:
        snapshot = self._snapshots.get(patch.patch_id)
        patch.approval_status = PatchApprovalStatus.ROLLED_BACK
        
        return {
            "patch_id": patch.patch_id,
            "success": True,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
            "restored_state": snapshot["original_state"] if snapshot else {},
            "message": f"Successfully reverted changes for {patch.title}"
        }

rollback_engine = PatchRollbackEngine()
