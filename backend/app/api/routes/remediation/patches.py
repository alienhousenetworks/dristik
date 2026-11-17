"""
Dristik AI Remediation API Routes
Manages Universal Remediation Patches, HITL approvals, multi-platform deployments,
closed-loop verification, and ROI estimation.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.domain.models import RemediationPatch, RoiInput, RoiEstimate, VerificationResult, RemediationVerificationReport
from app.domain.enums import PatchRiskLevel, PatchApprovalStatus, FindingStatus, VerificationStatus
from app.identity.access import require_analysis
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user, require_permission
from app.remediation.patch_engine import patch_engine
from app.remediation.diff_engine import diff_engine
from app.remediation.approval import approval_manager
from app.connectors.store import connector_store
from app.remediation.verifier import verification_engine
from app.remediation.verification_loop import verification_loop_service
from app.orchestration.orchestrator import orchestrator

router = APIRouter(prefix="/remediation", tags=["Remediation & Universal Patches"])

# In-memory store for generated patches by analysis_id / patch_id
_PATCH_REGISTRY: Dict[str, RemediationPatch] = {}

class PatchesResponse(BaseModel):
    analysis_id: str
    total_patches: int
    safe_auto_count: int
    human_approval_count: int
    developer_required_count: int
    patches: List[RemediationPatch]
    diff_summaries: List[Dict[str, Any]]

class ApprovePatchRequest(BaseModel):
    approver: str = "analyst@dristik.ai"
    notes: Optional[str] = None

class RejectPatchRequest(BaseModel):
    rejector: str = "analyst@dristik.ai"
    reason: Optional[str] = None

class AssignRemediationRequest(BaseModel):
    assignee_id: str
    assigned_by: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None

class ApplyPatchRequest(BaseModel):
    integration_id: str = Field(..., description="ID of the connected platform (WordPress, GitHub, etc.)")


def _persist_run_safely(run: Any) -> None:
    if not run:
        return
    try:
        orchestrator.runs[run.analysis_id] = run
        orchestrator.repository.save_run(run, findings=run.report.findings if run.report else None)
    except Exception:
        pass

def _owned_patch(patch_id: str, user: UserIdentity) -> RemediationPatch:
    patch = _PATCH_REGISTRY.get(patch_id)
    org_id = (patch.metadata_payload or {}).get("org_id") if patch else None
    if not patch or not org_id or not Authorizer.can_access_org(user, org_id):
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


def _stamp_patch(patch: RemediationPatch, analysis_id: str, org_id: str) -> None:
    patch.metadata_payload["analysis_id"] = analysis_id
    patch.metadata_payload["org_id"] = org_id


def _get_or_generate_patches(analysis_id: str, user: UserIdentity) -> List[RemediationPatch]:
    run = require_analysis(analysis_id, user)
    existing = [
        p for p in _PATCH_REGISTRY.values()
        if p.metadata_payload.get("analysis_id") == run.analysis_id
        and p.metadata_payload.get("org_id") == run.org_id
    ]
    if existing:
        return existing

    if not run.report:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis run '{analysis_id}' not found or report not yet generated."
        )

    if run.report.remediation_patches:
        for patch in run.report.remediation_patches:
            _stamp_patch(patch, run.analysis_id, run.org_id)
            _PATCH_REGISTRY[patch.patch_id] = patch
        return run.report.remediation_patches

    patches = patch_engine.generate_patches(
        findings=run.report.findings or [],
        business_profile=run.report.business_profile,
        website_url=run.website_url,
        commercial_evals=run.report.commercial_evaluations
    )
    for patch in patches:
        _stamp_patch(patch, run.analysis_id, run.org_id)
        _PATCH_REGISTRY[patch.patch_id] = patch

    run.report.remediation_patches = patches
    return patches

@router.get("/patches/{analysis_id}", response_model=PatchesResponse)
async def get_remediation_patches(analysis_id: str, user: UserIdentity = Depends(get_current_user)):
    """Retrieve remediation patches for an audit the caller owns."""
    patches = _get_or_generate_patches(analysis_id, user)

    safe_count = sum(1 for p in patches if p.risk_level == PatchRiskLevel.SAFE_AUTO)
    human_count = sum(1 for p in patches if p.risk_level == PatchRiskLevel.HUMAN_APPROVAL)
    dev_count = sum(1 for p in patches if p.risk_level == PatchRiskLevel.DEVELOPER_REQUIRED)

    summaries = [diff_engine.generate_diff_summary(p) for p in patches]

    return PatchesResponse(
        analysis_id=analysis_id,
        total_patches=len(patches),
        safe_auto_count=safe_count,
        human_approval_count=human_count,
        developer_required_count=dev_count,
        patches=patches,
        diff_summaries=summaries
    )

@router.post("/patches/{patch_id}/approve", response_model=RemediationPatch)
async def approve_patch(
    patch_id: str,
    req: ApprovePatchRequest,
    user: UserIdentity = Depends(require_permission("patches:approve")),
):
    """Record approval by the signed-in owner or admin. The request body cannot name the approver."""
    patch = _owned_patch(patch_id, user)
    return approval_manager.approve_patch(patch, approver=user.email, notes=req.notes)

@router.post("/patches/{patch_id}/reject", response_model=RemediationPatch)
async def reject_patch(
    patch_id: str,
    req: RejectPatchRequest,
    user: UserIdentity = Depends(require_permission("patches:approve")),
):
    """Reject a patch as the signed-in owner or admin."""
    patch = _owned_patch(patch_id, user)
    return approval_manager.reject_patch(patch, rejector=user.email, reason=req.reason)


@router.post("/patches/{patch_id}/assign", response_model=RemediationPatch)
async def assign_patch(
    patch_id: str,
    req: AssignRemediationRequest,
    user: UserIdentity = Depends(require_permission("findings:assign")),
):
    """Assign a remediation patch to an owner/engineer with optional due date."""
    patch = _owned_patch(patch_id, user)
    assigned_by = req.assigned_by or user.email or user.user_id
    updated_patch = approval_manager.assign_patch(
        patch,
        assignee_id=req.assignee_id,
        assigned_by=assigned_by,
        due_date=req.due_date,
        notes=req.notes,
    )
    analysis_id = (patch.metadata_payload or {}).get("analysis_id")
    if analysis_id:
        try:
            run = require_analysis(analysis_id, user)
            if run and run.report:
                for f in (run.report.findings or []):
                    if f.finding_id == patch.finding_id or f.id == patch.finding_id:
                        f.assignee_id = updated_patch.assignee_id
                        f.assigned_by = updated_patch.assigned_by
                        f.assigned_at = updated_patch.assigned_at
                        f.due_date = updated_patch.due_date
                        f.owner = updated_patch.assignee_id
                for rp in (run.report.remediation_patches or []):
                    if rp.patch_id == patch.patch_id:
                        rp.assignee_id = updated_patch.assignee_id
                        rp.assigned_by = updated_patch.assigned_by
                        rp.assigned_at = updated_patch.assigned_at
                        rp.due_date = updated_patch.due_date
                _persist_run_safely(run)
        except Exception:
            pass
    return updated_patch


@router.post("/findings/{analysis_id}/{finding_id}/assign")
async def assign_finding(
    analysis_id: str,
    finding_id: str,
    req: AssignRemediationRequest,
    user: UserIdentity = Depends(require_permission("findings:assign")),
):
    """Assign an audit finding to a team member, persist to the report/DB, and log in governance audit trail."""
    run = require_analysis(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Analysis report not found")

    target_finding = None
    for f in (run.report.findings or []):
        if f.finding_id == finding_id or f.id == finding_id:
            target_finding = f
            break
    if not target_finding:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found in analysis '{analysis_id}'")

    assigned_by = req.assigned_by or user.email or user.user_id
    approval_manager.assign_finding(
        target_finding,
        assignee_id=req.assignee_id,
        assigned_by=assigned_by,
        due_date=req.due_date,
        notes=req.notes,
        org_id=run.org_id,
    )

    # Sync assignment onto any linked patches
    for p in list(_PATCH_REGISTRY.values()) + list(run.report.remediation_patches or []):
        if p.finding_id == finding_id:
            p.assignee_id = target_finding.assignee_id
            p.assigned_by = target_finding.assigned_by
            p.assigned_at = target_finding.assigned_at
            p.due_date = target_finding.due_date

    _persist_run_safely(run)
    return {
        "analysis_id": analysis_id,
        "finding_id": target_finding.finding_id,
        "assignee_id": target_finding.assignee_id,
        "assigned_by": target_finding.assigned_by,
        "assigned_at": target_finding.assigned_at,
        "due_date": target_finding.due_date,
        "notes": req.notes,
        "finding": target_finding,
    }


@router.get("/findings/{analysis_id}/{finding_id}/retest-history")
async def get_finding_retest_history(
    analysis_id: str,
    finding_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Return full chronological append-only retest history for a finding."""
    run = require_analysis(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Analysis report not found")

    target_finding = None
    for f in (run.report.findings or []):
        if f.finding_id == finding_id or f.id == finding_id:
            target_finding = f
            break
    if not target_finding:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found in analysis '{analysis_id}'")

    history = [
        item.model_dump() if hasattr(item, "model_dump") else item
        for item in (target_finding.retest_history or [])
    ]
    return {
        "analysis_id": analysis_id,
        "finding_id": target_finding.finding_id,
        "total_retests": len(history),
        "latest_status": (
            target_finding.remediation_verification.status
            if target_finding.remediation_verification
            else (history[-1].get("status") if history and isinstance(history[-1], dict) else None)
        ),
        "assignee_id": target_finding.assignee_id,
        "assigned_by": target_finding.assigned_by,
        "assigned_at": target_finding.assigned_at,
        "due_date": target_finding.due_date,
        "retest_history": history,
    }

def _owned_connector(integration_id: str, user: UserIdentity):
    integration = connector_store.get_integration(integration_id)
    if not integration or not Authorizer.can_access_org(user, integration.org_id):
        raise HTTPException(status_code=404, detail="Integration not found")
    connector = connector_store.get_connector(integration_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Integration not found")
    return connector


@router.post("/patches/{patch_id}/apply")
async def apply_patch(
    patch_id: str,
    req: ApplyPatchRequest,
    user: UserIdentity = Depends(require_permission("patches:export_pr")),
):
    """Deploy an approved patch through an integration in the same organization."""
    patch = _owned_patch(patch_id, user)
    if patch.approval_status != PatchApprovalStatus.APPROVED:
        raise HTTPException(status_code=403, detail="Approve the patch before deploying it.")
    connector = _owned_connector(req.integration_id, user)

    result = await connector.apply_patch(patch)
    return {
        "success": result.success,
        "patch_id": patch.patch_id,
        "status": patch.approval_status.value,
        "applied_via": patch.applied_via,
        "pr_url": patch.pr_url,
        "pr_number": patch.pr_number,
        "message": result.message
    }

@router.post("/patches/{patch_id}/rollback")
async def rollback_patch(
    patch_id: str,
    req: ApplyPatchRequest,
    user: UserIdentity = Depends(require_permission("patches:export_pr")),
):
    """Rollback an applied patch through an integration in the same organization."""
    patch = _owned_patch(patch_id, user)
    connector = _owned_connector(req.integration_id, user)

    result = await connector.rollback_patch(patch)
    return {
        "success": result.success,
        "patch_id": patch.patch_id,
        "status": patch.approval_status.value,
        "message": result.message
    }

@router.post("/patches/{patch_id}/verify", response_model=VerificationResult)
async def verify_patch(patch_id: str, user: UserIdentity = Depends(get_current_user)):
    """Re-check a patch the caller is allowed to see and append to retest_history."""
    patch = _owned_patch(patch_id, user)
    res = await verification_engine.verify_remediation(patch)
    entry = res.model_dump() if hasattr(res, "model_dump") else dict(res)
    if patch.retest_history is None:
        patch.retest_history = []
    patch.retest_history.append(entry)

    analysis_id = (patch.metadata_payload or {}).get("analysis_id")
    if analysis_id:
        try:
            run = require_analysis(analysis_id, user)
            if run and run.report:
                for rp in (run.report.remediation_patches or []):
                    if rp.patch_id == patch.patch_id and rp is not patch:
                        if rp.retest_history is None:
                            rp.retest_history = []
                        rp.retest_history.append(entry)
                _persist_run_safely(run)
        except Exception:
            pass
    return res
 
class VerifyFindingRequest(BaseModel):
    finding_id: str
    analysis_id: Optional[str] = None
    website_url: Optional[str] = None
    target_url: Optional[str] = None
    finding_title: Optional[str] = None
    finding_category: Optional[str] = None
    finding_text: Optional[str] = None
    finding_description: Optional[str] = None
    finding_recommendation: Optional[str] = None

@router.post("/verify-finding", response_model=RemediationVerificationReport)
async def verify_finding_remediation(
    req: VerifyFindingRequest,
    user: UserIdentity = Depends(get_current_user),
):
    """
    Executes the continuous remediation verification loop:
    FIX -> RECRAWL -> RECHECK -> COMPARE -> CERTIFY
    Operates on live original target URLs and authentic findings.
    Appends each verification run to finding.retest_history and linked patch.retest_history.
    """
    finding = None
    run = None
    target_url = req.target_url or req.website_url or ""

    if req.analysis_id:
        run = require_analysis(req.analysis_id, user)
        if run.report:
            target_url = req.target_url or req.website_url or run.website_url
            for f in (run.report.findings or []):
                if f.finding_id == req.finding_id or f.id == req.finding_id:
                    finding = f
                    # If finding has a specific target URL in its evidence, prefer that for page-level recrawl
                    for ev in (f.evidence or []):
                        if ev.url and ev.url.startswith("http"):
                            target_url = req.target_url or ev.url
                            break
                    break

    if not finding:
        # Build finding from the authentic finding details provided in the request payload
        from app.domain.models import Finding
        from app.domain.enums import Category, Severity
        cat = Category.TECHNICAL_SEO
        if req.finding_category:
            try:
                cat = Category(req.finding_category)
            except Exception:
                pass
        finding = Finding(
            finding_id=req.finding_id,
            category=cat,
            severity=Severity.HIGH,
            title=req.finding_title or req.finding_text or f"Finding {req.finding_id}",
            finding=req.finding_text or req.finding_title or "",
            description=req.finding_description or "",
            recommendation=req.finding_recommendation or ""
        )

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url=target_url or "https://example.com",
        analysis_id=req.analysis_id,
    )
    if finding:
        finding.remediation_verification = report
        if finding.retest_history is None:
            finding.retest_history = []
        finding.retest_history.append(report)

        if report.status == "RESOLVED":
            finding.status = FindingStatus.VERIFIED
            finding.resolution_status = "RESOLVED"
            finding.verification_status = VerificationStatus.VERIFIED
        elif report.status == "PARTIALLY_RESOLVED":
            finding.status = FindingStatus.IN_PROGRESS
            finding.resolution_status = "PARTIALLY_RESOLVED"
        elif report.status in ("FAILED_RECHECK", "FAILED_RECRAWL", "REGRESSED"):
            finding.status = FindingStatus.OPEN
            finding.resolution_status = "REGRESSED"

        report_dict = report.model_dump() if hasattr(report, "model_dump") else dict(report)
        seen_patches = set()
        candidate_patches = list(_PATCH_REGISTRY.values())
        if run and run.report and run.report.remediation_patches:
            candidate_patches.extend(run.report.remediation_patches)
        for p in candidate_patches:
            if id(p) in seen_patches:
                continue
            seen_patches.add(id(p))
            if p.finding_id == finding.finding_id:
                if p.retest_history is None:
                    p.retest_history = []
                p.retest_history.append(report_dict)

        if run:
            _persist_run_safely(run)

    return report

@router.post("/verify-all/{analysis_id}", response_model=List[RemediationVerificationReport])
async def verify_all_findings_remediation(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """
    Runs the verification loop across all findings in an analysis run using live original URLs,
    appending each new RemediationVerificationReport to finding.retest_history and patch.retest_history.
    """
    run = require_analysis(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Analysis run or report not found")

    results: List[RemediationVerificationReport] = []
    for f in (run.report.findings or []):
        f_url = run.website_url
        for ev in (f.evidence or []):
            if ev.url and ev.url.startswith("http"):
                f_url = ev.url
                break
        rep = await verification_loop_service.verify_finding(
            finding=f,
            website_url=f_url,
            analysis_id=analysis_id,
        )
        f.remediation_verification = rep
        if f.retest_history is None:
            f.retest_history = []
        f.retest_history.append(rep)

        if rep.status == "RESOLVED":
            f.status = FindingStatus.VERIFIED
            f.resolution_status = "RESOLVED"
            f.verification_status = VerificationStatus.VERIFIED
        elif rep.status == "PARTIALLY_RESOLVED":
            f.status = FindingStatus.IN_PROGRESS
            f.resolution_status = "PARTIALLY_RESOLVED"
        elif rep.status in ("FAILED_RECHECK", "FAILED_RECRAWL", "REGRESSED"):
            f.status = FindingStatus.OPEN
            f.resolution_status = "REGRESSED"

        rep_dict = rep.model_dump() if hasattr(rep, "model_dump") else dict(rep)
        seen_patches = set()
        for p in list(_PATCH_REGISTRY.values()) + list(run.report.remediation_patches or []):
            if id(p) in seen_patches:
                continue
            seen_patches.add(id(p))
            if p.finding_id == f.finding_id:
                if p.retest_history is None:
                    p.retest_history = []
                p.retest_history.append(rep_dict)

        results.append(rep)

    _persist_run_safely(run)
    return results

@router.post("/roi-estimate", response_model=RoiEstimate)
async def calculate_roi_estimate(inp: RoiInput, user: UserIdentity = Depends(get_current_user)):
    del user
    """
    Computes commercial revenue upside based on client deal size, traffic, and conversion rates.
    Connects: Technical problem -> Search visibility -> Traffic -> Conversion opportunity.
    """
    if inp.monthly_visitors is None or inp.monthly_visitors <= 0:
        raise HTTPException(status_code=400, detail="Real positive 'monthly_visitors' input is required to compute ROI.")
    if inp.avg_deal_size_inr is None or inp.avg_deal_size_inr <= 0:
        raise HTTPException(status_code=400, detail="Real positive 'avg_deal_size_inr' input is required to compute ROI.")

    monthly_visitors = inp.monthly_visitors
    avg_deal_size = inp.avg_deal_size_inr
    current_conv_rate = max(inp.current_conversion_rate or 0.01, 0.0001)

    # Current baseline
    current_monthly_leads = max(int(monthly_visitors * current_conv_rate), 1)
    current_annual_revenue = current_monthly_leads * 12 * avg_deal_size

    # Projected with Dristik Remediation
    projected_visitors = monthly_visitors * (1.0 + inp.expected_traffic_lift_pct)
    projected_conv_rate = current_conv_rate * (1.0 + inp.expected_cro_lift_pct)
    projected_monthly_leads = int(projected_visitors * projected_conv_rate)
    projected_annual_revenue = projected_monthly_leads * 12 * avg_deal_size

    annual_upside = max(projected_annual_revenue - current_annual_revenue, 0.0)
    # ROI multiple against Dristik Diagnostic Sprint (₹4,999) or Growth Intelligence (₹24,999)
    dristik_investment = 24999.0
    roi_multiple = round(annual_upside / dristik_investment, 1) if dristik_investment > 0 else 10.0

    opportunities = [
        f"AI Citation Lift: Recapture enterprise buyer queries currently cited for competitors (+{int(inp.expected_traffic_lift_pct*100)}% traffic upside)",
        f"Hero Value-Proposition & CRO Polish: Higher qualified demo conversion (+{int(inp.expected_cro_lift_pct*100)}% conversion upside)",
        f"High-Intent Comparison Pages: Capture comparison search intent before competitors"
    ]

    return RoiEstimate(
        monthly_visitors=monthly_visitors,
        avg_deal_size_inr=avg_deal_size,
        current_monthly_leads=current_monthly_leads,
        current_annual_revenue_inr=round(current_annual_revenue, 2),
        projected_annual_revenue_inr=round(projected_annual_revenue, 2),
        annual_upside_inr=round(annual_upside, 2),
        roi_multiple=roi_multiple,
        high_impact_opportunities=opportunities
    )

@router.get("/download-pack/{analysis_id}")
async def download_remediation_patch_pack(analysis_id: str, user: UserIdentity = Depends(get_current_user)):
    """
    Downloads the 1-click deployable code fixes packaging:
    - schema.jsonld
    - robots.txt
    - llms.txt
    - security_headers.conf
    - geo_definitions.html
    into a single downloadable 'dristik-remediation-patches.zip'.
    """
    run = require_analysis(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Analysis run or report not found")

    from app.remediation.patch_pack import generate_patch_pack_zip
    from fastapi.responses import Response

    zip_bytes = generate_patch_pack_zip(
        bp=run.report.business_profile,
        website_url=run.website_url,
        commercial_evals=run.report.commercial_evaluations or []
    )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=dristik-remediation-patches.zip"
        }
    )

