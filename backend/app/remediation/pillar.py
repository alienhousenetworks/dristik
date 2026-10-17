"""Remediation pillar: patches, diffs, and rollback."""
from app.domain.pillar import PillarId
from app.remediation.patch_generator import RemediationPatcher
from app.remediation.patch_engine import UniversalPatchEngine
from app.remediation.diff_engine import DiffEngine
from app.remediation.rollback import PatchRollbackEngine


class RemediationPillar:
    pillar_id = PillarId.REMEDIATION
    domains = {"REMEDIATION", "VERIFICATION"}

    def __init__(self):
        self.patcher = RemediationPatcher()
        self.patch_engine = UniversalPatchEngine()
        self.diff_engine = DiffEngine()
        self.rollback = PatchRollbackEngine()


__all__ = [
    "RemediationPillar",
    "RemediationPatcher",
    "UniversalPatchEngine",
    "DiffEngine",
    "PatchRollbackEngine",
]
