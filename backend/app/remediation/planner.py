"""
Dristik AI Remediation Planner
Translates strategic recommendations into validated implementation workflows,
sandboxed code patches, and human approval gates.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.models import Finding, CodePatch, BusinessProfile, PageEvidence
from app.domain.enums import ReleaseStatus
from app.remediation.patch_generator import RemediationPatcher
from app.remediation.validator import PatchValidator, PatchValidationResult

class RemediationPlan(BaseModel):
    plan_id: str
    target_url: str
    total_patches: int
    all_patches_validated: bool
    patches: List[CodePatch] = Field(default_factory=list)
    validation_results: Dict[str, PatchValidationResult] = Field(default_factory=dict)
    approval_required: bool = True
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, REJECTED

class RemediationPlanner:
    """
    Coordinates creation, validation, and human-in-the-loop review of code patches.
    """

    def __init__(self):
        self.patcher = RemediationPatcher()
        self.validator = PatchValidator()

    def build_remediation_plan(
        self,
        findings: List[Finding],
        business_profile: BusinessProfile,
        target_url: str,
        pages: Optional[List[PageEvidence]] = None,
    ) -> RemediationPlan:
        raw_patches = self.patcher.generate_patches(findings, business_profile, target_url, pages=pages)
        validated_patches: List[CodePatch] = []
        val_results: Dict[str, PatchValidationResult] = {}
        all_ok = True

        for p in raw_patches:
            val = self.validator.validate_patch(p)
            val_results[p.patch_id] = val
            if not val.is_valid:
                all_ok = False
            p.release_status = ReleaseStatus.PENDING_APPROVAL
            validated_patches.append(p)

        import uuid
        plan_id = f"rem_{uuid.uuid4().hex[:8]}"

        return RemediationPlan(
            plan_id=plan_id,
            target_url=target_url,
            total_patches=len(validated_patches),
            all_patches_validated=all_ok,
            patches=validated_patches,
            validation_results=val_results,
            approval_required=True,
            status="PENDING_APPROVAL"
        )
