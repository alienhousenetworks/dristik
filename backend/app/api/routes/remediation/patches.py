"""
Dristik AI Remediation API Routes
Manages Universal Remediation Patches, HITL approvals, multi-platform deployments,
closed-loop verification, and ROI estimation.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.domain.models import RemediationPatch, RoiInput, RoiEstimate, VerificationResult, RemediationVerificationReport
from app.domain.enums import PatchRiskLevel, PatchApprovalStatus
from app.remediation.patch_engine import patch_engine
from app.remediation.diff_engine import diff_engine
from app.remediation.approval import approval_manager
from app.connectors.store import connector_store
from app.verification.verifier import verification_engine
from app.verification.verification_loop import verification_loop_service
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

class ApplyPatchRequest(BaseModel):
    integration_id: str = Field(..., description="ID of the connected platform (WordPress, GitHub, etc.)")

def _get_or_generate_patches(analysis_id: str) -> List[RemediationPatch]:
    # Check if we already have them in memory
    existing = [p for p in _PATCH_REGISTRY.values() if p.metadata_payload.get("analysis_id") == analysis_id]
    if existing:
        return existing

    # Find analysis run
    run = orchestrator.get_run(analysis_id)
    if not run or not run.report:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis run '{analysis_id}' not found or report not yet generated."
        )

    # Check report for existing patches
    if run.report.remediation_patches:
        for p in run.report.remediation_patches:
            p.metadata_payload["analysis_id"] = analysis_id
            _PATCH_REGISTRY[p.patch_id] = p
        return run.report.remediation_patches

    # Generate from report findings
    patches = patch_engine.generate_patches(
        findings=run.report.findings or [],
        business_profile=run.report.business_profile,
        website_url=run.website_url,
        commercial_evals=run.report.commercial_evaluations
    )
    for p in patches:
        p.metadata_payload["analysis_id"] = analysis_id
        _PATCH_REGISTRY[p.patch_id] = p
    
    run.report.remediation_patches = patches
    return patches

@router.get("/patches/{analysis_id}", response_model=PatchesResponse)
async def get_remediation_patches(analysis_id: str):
    """Retrieve all Universal Remediation Patches generated for an audit run."""
    patches = _get_or_generate_patches(analysis_id)

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
async def approve_patch(patch_id: str, req: ApprovePatchRequest):
    """Human-in-the-Loop approval for Level 2 or Level 3 patch."""
    patch = _PATCH_REGISTRY.get(patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return approval_manager.approve_patch(patch, approver=req.approver, notes=req.notes)

@router.post("/patches/{patch_id}/reject", response_model=RemediationPatch)
async def reject_patch(patch_id: str, req: RejectPatchRequest):
    """Reject a patch."""
    patch = _PATCH_REGISTRY.get(patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return approval_manager.reject_patch(patch, rejector=req.rejector, reason=req.reason)

@router.post("/patches/{patch_id}/apply")
async def apply_patch(patch_id: str, req: ApplyPatchRequest):
    """Deploy patch via target integration (WordPress direct or GitHub PR)."""
    patch = _PATCH_REGISTRY.get(patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    connector = connector_store.get_connector(req.integration_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Integration {req.integration_id} not found")

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
async def rollback_patch(patch_id: str, req: ApplyPatchRequest):
    """Rollback an applied patch."""
    patch = _PATCH_REGISTRY.get(patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    connector = connector_store.get_connector(req.integration_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Integration not found")

    result = await connector.rollback_patch(patch)
    return {
        "success": result.success,
        "patch_id": patch.patch_id,
        "status": patch.approval_status.value,
        "message": result.message
    }

@router.post("/patches/{patch_id}/verify", response_model=VerificationResult)
async def verify_patch(patch_id: str):
    """Trigger automated verification scan: Detect -> Explain -> Fix -> Verify."""
    patch = _PATCH_REGISTRY.get(patch_id)
    if not patch:
        raise HTTPException(
            status_code=404,
            detail=f"Remediation patch '{patch_id}' not found. Cannot verify an ungenerated patch."
        )

    return await verification_engine.verify_remediation(patch)
 
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
    mock_live_html: Optional[str] = None  # retained solely for test fixture compatibility
    override_html_for_testing: Optional[str] = None

@router.post("/verify-finding", response_model=RemediationVerificationReport)
async def verify_finding_remediation(req: VerifyFindingRequest):
    """
    Executes the continuous remediation verification loop:
    FIX -> RECRAWL -> RECHECK -> COMPARE -> CERTIFY
    Operates on live original target URLs and authentic findings.
    """
    finding = None
    target_url = req.target_url or req.website_url or ""

    if req.analysis_id:
        run = orchestrator.get_run(req.analysis_id)
        if run and run.report:
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

    test_html = req.override_html_for_testing or req.mock_live_html

    report = await verification_loop_service.verify_finding(
        finding=finding,
        website_url=target_url or "https://example.com",
        live_html=test_html,
        analysis_id=req.analysis_id,
    )
    return report

@router.post("/verify-all/{analysis_id}", response_model=List[RemediationVerificationReport])
async def verify_all_findings_remediation(analysis_id: str):
    """
    Runs the verification loop across all findings in an analysis run using live original URLs.
    """
    run = orchestrator.get_run(analysis_id)
    if not run or not run.report:
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
        results.append(rep)
    return results

@router.post("/roi-estimate", response_model=RoiEstimate)
async def calculate_roi_estimate(inp: RoiInput):
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
async def download_remediation_patch_pack(analysis_id: str):
    """
    Downloads the 1-click deployable code fixes packaging:
    - schema.jsonld
    - robots.txt
    - llms.txt
    - security_headers.conf
    - geo_definitions.html
    into a single downloadable 'dristik-remediation-patches.zip'.
    """
    run = orchestrator.get_run(analysis_id)
    if not run or not run.report:
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

