"""Phase 40 — Complete Enterprise CRO REST & SSE API Router (`/api/v1/cro/*`).

Enforces:
- Pydantic v2 request/response validation
- Strict tenant isolation (`user.org_id`)
- Role-based access control (`require_permission` on approvals, deployments, experiment launches)
- SSRF URL validation (`is_safe_url`)
- Pagination & filtering
- Idempotency keys on audit creation
- Real-time SSE progress stream of all 21 `cro.*` events
- SOC 2 enterprise audit logging on governance actions
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.security.enterprise_audit_logger import EnterpriseAuditLogger
from app.core.security.ssrf import is_safe_url
from app.cro.browser_testing import CROBrowserTestingEngine
from app.cro.business_models import BusinessUnderstandingEngine
from app.cro.experimentation_engine import (
    calculate_required_sample_size,
    enterprise_experiment_engine,
    format_hypothesis_statement,
)
from app.cro.models import (
    CROBusinessModelType,
    CROBusinessProfile,
    CROExperiment,
    CROExperimentStatus,
    CROGoal,
    CROPage,
    CROTaskStatus,
    CROVariant,
)
from app.cro.monitoring import CROMonitoringEngine
from app.cro.orchestrator import CROAuditOrchestrator
from app.cro.remediation_center import CRORemediationCenter
from app.cro.reports.builder import CROReportBuilder
from app.cro.reports.section_registry import CRO_REPORT_PROFILES
from app.cro.specialists.analytics_attribution import (
    build_connector_capability_registry,
    build_impact_scenario_estimate,
)
from app.cro.verification_engine import CROIndependentVerificationEngine
from app.db.cro_schema import get_cro_store
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission

router = APIRouter(prefix="/cro", tags=["CRO Enterprise Intelligence"])

# Active orchestrators indexed by (tenant_id, audit_id) for live SSE streaming, cancel & resume
ACTIVE_CRO_ORCHESTRATORS: Dict[str, CROAuditOrchestrator] = {}


def _tenant(user: UserIdentity) -> str:
    return user.org_id or "default"


def _audit_log(user: UserIdentity, action: str, resource_type: str, resource_id: str, payload: Dict[str, Any]) -> None:
    try:
        EnterpriseAuditLogger.log_action(
            org_id=_tenant(user),
            user_id=user.user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────────────────────


class CreateCROAuditRequest(BaseModel):
    target_url: str = Field(..., min_length=4)
    mode: str = Field(default="standard", pattern="^(quick|standard|deep|continuous)$")
    business_config: Optional[Dict[str, Any]] = None
    analytics_payload: Optional[Dict[str, Any]] = None
    campaign_context: Optional[Dict[str, Any]] = None
    crm_payload: Optional[Dict[str, Any]] = None
    commerce_payload: Optional[Dict[str, Any]] = None
    field_cwv_payload: Optional[Dict[str, Any]] = None
    connected_providers: List[str] = Field(default_factory=list)
    seed_pages: Optional[List[Dict[str, Any]]] = None
    safe_mode: bool = True
    use_live_browser: bool = False
    run_async: bool = False


class BusinessProfileRequest(BaseModel):
    domain: str
    website_url: str
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    products_and_services: List[str] = Field(default_factory=list)
    target_customers: Optional[str] = None
    geographic_markets: List[str] = Field(default_factory=list)
    pricing_model: Optional[str] = None
    primary_conversion: Optional[str] = None
    secondary_conversions: List[str] = Field(default_factory=list)
    average_order_value: Optional[float] = None
    currency: Optional[str] = None
    revenue_model: Optional[str] = None
    lead_qualification_criteria: List[str] = Field(default_factory=list)
    main_acquisition_channels: List[str] = Field(default_factory=list)
    known_competitors: List[str] = Field(default_factory=list)
    analytics_configuration: Dict[str, Any] = Field(default_factory=dict)
    important_pages: List[str] = Field(default_factory=list)
    known_conversion_problems: List[str] = Field(default_factory=list)


class CreateGoalRequest(BaseModel):
    audit_id: Optional[str] = None
    profile_id: Optional[str] = None
    name: str
    goal_type: str = Field(default="primary", pattern="^(primary|secondary|micro)$")
    target_action: str
    target_urls: List[str] = Field(default_factory=list)
    analytics_event_name: Optional[str] = None
    required_event_params: List[str] = Field(default_factory=list)
    value_per_conversion: Optional[float] = None
    qualification_criteria: Optional[str] = None


class ValidateGoalRequest(BaseModel):
    observed_event_names: List[str] = Field(default_factory=list)
    observed_parameters: List[str] = Field(default_factory=list)


class CreateBrowserTestRequest(BaseModel):
    audit_id: Optional[str] = None
    url: str
    raw_html: Optional[str] = None
    viewports: List[str] = Field(default_factory=lambda: ["desktop", "tablet", "mobile"])
    safe_mode: bool = True
    use_live_browser: bool = False


class CreateExperimentRequest(BaseModel):
    audit_id: Optional[str] = None
    finding_ids: List[str] = Field(default_factory=list)
    title: str
    experiment_type: str = "ab_test"
    change_experience: str
    target_audience: str = "All eligible visitors"
    desired_action: str = "complete the primary conversion"
    evidence_rationale: str
    primary_metric: str = "Primary Conversion Rate"
    guardrail_metrics: List[str] = Field(default_factory=lambda: ["Revenue", "Qualified lead rate", "Checkout errors"])
    baseline_rate_input: float = Field(default=0.03, gt=0.0, lt=1.0)
    minimum_detectable_effect: float = Field(default=0.15, gt=0.01, lt=5.0)
    planned_duration_days: int = Field(default=14, ge=7)
    owner: str = "Growth Lead"


class AddVariantRequest(BaseModel):
    name: str
    is_control: bool = False
    traffic_allocation_pct: float = Field(default=50.0, gt=0.0, le=100.0)
    description: str = ""
    changes_spec: Dict[str, Any] = Field(default_factory=dict)


class RecordExperimentResultsRequest(BaseModel):
    control_visitors: int = Field(..., gt=0)
    control_conversions: int = Field(..., ge=0)
    variant_visitors: int = Field(..., gt=0)
    variant_conversions: int = Field(..., ge=0)
    days_elapsed: int = Field(default=14, ge=1)
    guardrail_deltas: Dict[str, float] = Field(default_factory=dict)
    num_comparisons: int = Field(default=1, ge=1)
    expected_control_share: float = Field(default=0.50, gt=0.0, lt=1.0)


class DeployTaskRequest(BaseModel):
    deployment_ref: str = Field(..., min_length=2)


class VerifyTaskRequest(BaseModel):
    before_html: Optional[str] = None
    after_html: Optional[str] = None
    expected_text_present: Optional[str] = None
    analytics_event_confirmed: Optional[bool] = None
    pre_conversion_metrics: Optional[Dict[str, Any]] = None
    post_conversion_metrics: Optional[Dict[str, Any]] = None
    use_live_browser: bool = False
    viewport: str = "desktop"


class CreateScheduleRequest(BaseModel):
    domain: str
    target_urls: List[str] = Field(default_factory=list)
    cadence: str = Field(default="daily", pattern="^(hourly|daily|weekly)$")
    checks_enabled: Optional[List[str]] = None


class CreateReportRequest(BaseModel):
    audit_id: str
    profile: str = "complete_audit_book"
    format: str = Field(default="html", pattern="^(html|json|pdf)$")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Audits & Streaming Progress
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/audits", status_code=status.HTTP_201_CREATED)
async def create_cro_audit(
    req: CreateCROAuditRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    if not req.seed_pages:
        safe, reason = is_safe_url(req.target_url)
        if not safe:
            raise HTTPException(status_code=400, detail=f"URL blocked by SSRF security guard: {reason}")

    store = get_cro_store()
    tenant = _tenant(user)
    if idempotency_key:
        existing = store.find_audit_by_idempotency(tenant, idempotency_key)
        if existing:
            return {"audit": existing.model_dump(), "idempotent_replay": True}

    orch = CROAuditOrchestrator(
        tenant_id=tenant,
        target_url=req.target_url,
        mode=req.mode,
        business_config=req.business_config,
        analytics_payload=req.analytics_payload,
        campaign_context=req.campaign_context,
        crm_payload=req.crm_payload,
        commerce_payload=req.commerce_payload,
        field_cwv_payload=req.field_cwv_payload,
        connected_providers=req.connected_providers,
        seed_pages=req.seed_pages,
        safe_mode=req.safe_mode,
        use_live_browser=req.use_live_browser,
        idempotency_key=idempotency_key,
        store=store,
    )
    ACTIVE_CRO_ORCHESTRATORS[f"{tenant}:{orch.audit_id}"] = orch
    _audit_log(user, "cro.audit.create", "cro_audit", orch.audit_id, {"target_url": req.target_url, "mode": req.mode})

    if req.run_async:
        background_tasks.add_task(orch.run)
        return {
            "audit": orch.audit.model_dump(),
            "progress_url": f"/api/v1/cro/audits/{orch.audit_id}/progress",
        }

    result = await orch.run()
    return result


@router.get("/audits")
async def list_cro_audits(
    domain: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    items = get_cro_store().list_audits(_tenant(user), domain=domain, limit=limit, offset=offset)
    return {"items": [a.model_dump() for a in items], "count": len(items), "limit": limit, "offset": offset}


@router.get("/audits/{audit_id}")
async def get_cro_audit(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    store = get_cro_store()
    tenant = _tenant(user)
    audit = store.get_audit(tenant, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="CRO audit not found.")
    return {
        "audit": audit.model_dump(),
        "scorecard": store.get_artifact(tenant, audit_id, "scorecard"),
        "qa_report": store.get_artifact(tenant, audit_id, "qa_report"),
        "department_artifacts": store.get_artifact(tenant, audit_id, "department_artifacts"),
        "agent_executions": store.list_agent_executions(tenant, audit_id),
    }


@router.get("/audits/{audit_id}/progress")
async def stream_cro_audit_progress(audit_id: str, user: UserIdentity = Depends(get_current_user)):
    tenant = _tenant(user)
    orch = ACTIVE_CRO_ORCHESTRATORS.get(f"{tenant}:{audit_id}")
    if not orch:
        audit = get_cro_store().get_audit(tenant, audit_id)
        if not audit:
            raise HTTPException(status_code=404, detail="CRO audit not found.")
        return {"audit_id": audit_id, "status": audit.status, "current_stage": audit.current_stage, "events": []}
    return StreamingResponse(
        orch.events.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/audits/{audit_id}/cancel")
async def cancel_cro_audit(audit_id: str, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    orch = ACTIVE_CRO_ORCHESTRATORS.get(f"{_tenant(user)}:{audit_id}")
    if not orch:
        raise HTTPException(status_code=404, detail="Active CRO audit not found.")
    orch.cancel()
    return {"audit_id": audit_id, "status": "cancelled"}


@router.post("/audits/{audit_id}/resume")
async def resume_cro_audit(audit_id: str, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    orch = ACTIVE_CRO_ORCHESTRATORS.get(f"{_tenant(user)}:{audit_id}")
    if not orch:
        raise HTTPException(status_code=404, detail="Active CRO audit not found.")
    return await orch.resume()


def _require_audit(tenant: str, audit_id: str):
    audit = get_cro_store().get_audit(tenant, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="CRO audit not found.")
    return audit


@router.get("/audits/{audit_id}/pages")
async def get_audit_pages(
    audit_id: str,
    page_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    pages = get_cro_store().list_pages(tenant, audit_id, page_type=page_type, limit=limit, offset=offset)
    return {"audit_id": audit_id, "items": [p.model_dump() for p in pages], "count": len(pages)}


@router.get("/audits/{audit_id}/journeys")
async def get_audit_journeys(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_journeys(tenant, audit_id=audit_id)
    return {"audit_id": audit_id, "items": [j.model_dump() for j in items], "count": len(items)}


@router.get("/audits/{audit_id}/goals")
async def get_audit_goals(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_goals(tenant, audit_id=audit_id)
    return {"audit_id": audit_id, "items": [g.model_dump() for g in items], "count": len(items)}


@router.get("/audits/{audit_id}/audiences")
async def get_audit_audiences(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_audiences(tenant, audit_id=audit_id)
    return {"audit_id": audit_id, "items": [a.model_dump() for a in items], "count": len(items)}


@router.get("/audits/{audit_id}/elements")
async def get_audit_elements(
    audit_id: str,
    category: Optional[str] = None,
    device: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_elements(tenant, audit_id, element_category=category, device=device, limit=limit, offset=offset)
    return {"audit_id": audit_id, "items": [e.model_dump() for e in items], "count": len(items)}


@router.get("/audits/{audit_id}/ctas")
async def get_audit_ctas(audit_id: str, device: Optional[str] = None, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_elements(tenant, audit_id, element_category="cta", device=device)
    return {"audit_id": audit_id, "items": [e.model_dump() for e in items], "count": len(items)}


@router.get("/audits/{audit_id}/forms")
async def get_audit_forms(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_elements(tenant, audit_id, element_category="form")
    art = (get_cro_store().get_artifact(tenant, audit_id, "department_artifacts") or {}).get("forms_cta_workspace") or {}
    return {"audit_id": audit_id, "items": [e.model_dump() for e in items], "registry": art.get("forms_registry", []), "count": len(items)}


@router.get("/audits/{audit_id}/findings")
async def get_audit_findings(
    audit_id: str,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_findings(tenant, audit_id, severity=severity, category=category, source_type=source_type, limit=limit, offset=offset)
    return {"audit_id": audit_id, "items": [f.model_dump() for f in items], "count": len(items)}


@router.get("/audits/{audit_id}/scores")
async def get_audit_scores(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    return get_cro_store().get_artifact(tenant, audit_id, "scorecard") or {"audit_id": audit_id, "status": "unavailable"}


@router.get("/audits/{audit_id}/evidence")
async def get_audit_evidence(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    store = get_cro_store()
    return {
        "audit_id": audit_id,
        "snapshots": [s.model_dump() for s in store.list_snapshots(tenant, audit_id=audit_id)],
        "interaction_tests": [t.model_dump() for t in store.list_interaction_tests(tenant, audit_id=audit_id)],
    }


@router.get("/audits/{audit_id}/recommendations")
async def get_audit_recommendations(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_recommendations(tenant, audit_id)
    return {"audit_id": audit_id, "items": [r.model_dump() for r in items], "count": len(items)}


@router.get("/audits/{audit_id}/funnels")
async def get_audit_funnels(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_funnels(tenant, audit_id=audit_id)
    return {"audit_id": audit_id, "items": [f.model_dump() for f in items], "count": len(items)}


@router.get("/audits/{audit_id}/analytics")
async def get_audit_analytics(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    art = (get_cro_store().get_artifact(tenant, audit_id, "department_artifacts") or {}).get("analytics_intelligence") or {}
    return {"audit_id": audit_id, **art}


@router.get("/audits/{audit_id}/remediation")
async def get_audit_remediation(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    pack = get_cro_store().get_remediation_pack(tenant, audit_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Remediation pack not generated for this audit.")
    return {"pack": pack.model_dump(), "views": CRORemediationCenter.build_operational_views(pack.tasks)}


@router.get("/audits/{audit_id}/reports")
async def get_audit_reports(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    items = get_cro_store().list_reports(tenant, audit_id=audit_id)
    return {"audit_id": audit_id, "available_profiles": CRO_REPORT_PROFILES, "items": [r.model_dump() for r in items]}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Business Profiles & Conversion Goals
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/business-profiles/create", status_code=status.HTTP_201_CREATED)
async def create_business_profile(req: BusinessProfileRequest, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    profile, goals, audiences, scope = BusinessUnderstandingEngine.build(
        tenant_id=tenant,
        audit_id=None,
        target_url=req.website_url,
        user_config=req.model_dump(),
    )
    store = get_cro_store()
    store.save_business_profile(profile)
    for g in goals:
        store.save_goal(g)
    for a in audiences:
        store.save_audience(a)
    return {"profile": profile.model_dump(), "goals": [g.model_dump() for g in goals], "audiences": [a.model_dump() for a in audiences], "scope": scope}


@router.get("/business-profiles/{profile_id}")
async def get_business_profile(profile_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    bp = get_cro_store().get_business_profile(_tenant(user), profile_id)
    if not bp:
        raise HTTPException(status_code=404, detail="CRO business profile not found.")
    return bp.model_dump()


@router.put("/business-profiles/{profile_id}/update")
async def update_business_profile(profile_id: str, req: BusinessProfileRequest, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    store = get_cro_store()
    tenant = _tenant(user)
    existing = store.get_business_profile(tenant, profile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="CRO business profile not found.")
    updated, _g, _a, scope = BusinessUnderstandingEngine.build(
        tenant_id=tenant,
        audit_id=existing.audit_id,
        target_url=req.website_url,
        user_config=req.model_dump(),
    )
    updated.profile_id = existing.profile_id
    updated.created_at = existing.created_at
    store.save_business_profile(updated)
    return {"profile": updated.model_dump(), "scope": scope}


@router.post("/goals/create", status_code=status.HTTP_201_CREATED)
async def create_goal(req: CreateGoalRequest, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    goal = CROGoal(
        tenant_id=_tenant(user),
        audit_id=req.audit_id,
        profile_id=req.profile_id,
        name=req.name,
        goal_type=req.goal_type,
        target_action=req.target_action,
        target_urls=req.target_urls,
        analytics_event_name=req.analytics_event_name,
        required_event_params=req.required_event_params,
        value_per_conversion=req.value_per_conversion,
        qualification_criteria=req.qualification_criteria,
    )
    get_cro_store().save_goal(goal)
    return goal.model_dump()


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    g = get_cro_store().get_goal(_tenant(user), goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="CRO goal not found.")
    return g.model_dump()


@router.post("/goals/{goal_id}/validate")
async def validate_goal(goal_id: str, req: ValidateGoalRequest, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    store = get_cro_store()
    g = store.get_goal(_tenant(user), goal_id)
    if not g:
        raise HTTPException(status_code=404, detail="CRO goal not found.")
    if not req.observed_event_names:
        g.validation_status = "unavailable"
        g.validation_notes = "No observed analytics events provided for validation."
    elif g.analytics_event_name and g.analytics_event_name in req.observed_event_names:
        missing = [p for p in g.required_event_params if p not in req.observed_parameters]
        if missing:
            g.validation_status = "failed"
            g.validation_notes = f"Event found but missing required parameter(s): {', '.join(missing)}."
        else:
            g.validation_status = "verified"
            g.validation_notes = "Goal event and required parameters confirmed."
    else:
        g.validation_status = "failed"
        g.validation_notes = f"Expected event '{g.analytics_event_name}' not found in observed events."
    store.save_goal(g)
    return g.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Browser Tests
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/browser-tests/create", status_code=status.HTTP_201_CREATED)
async def create_browser_test(req: CreateBrowserTestRequest, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    if req.use_live_browser:
        safe, reason = is_safe_url(req.url)
        if not safe:
            raise HTTPException(status_code=400, detail=f"SSRF guard blocked browser test URL: {reason}")
    store = get_cro_store()
    tenant = _tenant(user)
    engine = CROBrowserTestingEngine(store=store)
    page = CROPage(tenant_id=tenant, audit_id=req.audit_id or "standalone", url=req.url)
    tests, elements, snaps = await engine.audit_page(
        tenant_id=tenant,
        audit_id=req.audit_id or "standalone",
        page=page,
        raw_html=req.raw_html,
        viewports=req.viewports,
        safe_mode=req.safe_mode,
        use_live_browser=req.use_live_browser,
    )
    for t in tests:
        store.save_interaction_test(t)
    return {
        "test_id": tests[0].test_id if tests else None,
        "tests": [t.model_dump() for t in tests],
        "elements_count": len(elements),
        "snapshots_count": len(snaps),
    }


@router.get("/browser-tests/{test_id}")
@router.get("/browser-tests/{test_id}/results")
async def get_browser_test_results(test_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    t = get_cro_store().get_interaction_test(_tenant(user), test_id)
    if not t:
        raise HTTPException(status_code=404, detail="Browser interaction test not found.")
    return t.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Analytics, Connectors, Events, Funnels, Segments, Attribution
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/analytics/connectors")
async def list_cro_connectors(user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    connected: List[str] = []
    try:
        from app.connectors.store import connector_store
        for integ in connector_store.list_integrations(org_id=_tenant(user)):
            if str(getattr(integ, "status", "")).lower() in ("connected", "active"):
                connected.append(str(getattr(integ, "provider", "")).lower())
    except Exception:
        pass
    caps = build_connector_capability_registry(connected)
    return {"connectors": [c.model_dump() for c in caps], "count": len(caps)}


@router.get("/analytics/events")
async def list_cro_analytics_events(audit_id: Optional[str] = None, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    items = get_cro_store().list_analytics_events(_tenant(user), audit_id=audit_id)
    return {"items": [e.model_dump() for e in items], "count": len(items)}


@router.get("/analytics/funnels")
async def list_cro_funnels(audit_id: Optional[str] = None, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    items = get_cro_store().list_funnels(_tenant(user), audit_id=audit_id)
    return {"items": [f.model_dump() for f in items], "count": len(items)}


@router.get("/analytics/segments")
async def get_cro_segments(audit_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    art = (get_cro_store().get_artifact(tenant, audit_id, "department_artifacts") or {}).get("analytics_intelligence") or {}
    return {"audit_id": audit_id, "device_performance": art.get("device_performance", {"status": "data_unavailable"})}


@router.get("/analytics/attribution")
async def get_cro_attribution(
    audit_id: str,
    hypothetical_lift_pct: Optional[float] = None,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    tenant = _tenant(user)
    _require_audit(tenant, audit_id)
    art = (get_cro_store().get_artifact(tenant, audit_id, "department_artifacts") or {}).get("analytics_intelligence") or {}
    out = {
        "audit_id": audit_id,
        "channel_attribution": art.get("channel_attribution", {"status": "data_unavailable"}),
        "crm_pipeline": art.get("crm_pipeline", {"status": "data_unavailable"}),
        "impact_scenario_estimate": art.get("impact_scenario_estimate"),
    }
    if hypothetical_lift_pct is not None:
        sc = get_cro_store().get_artifact(tenant, audit_id, "scorecard") or {}
        cr_m = next((m for m in sc.get("business_performance_metrics", []) if m.get("metric") == "Primary Conversion Rate"), None)
        aov_m = next((m for m in sc.get("business_performance_metrics", []) if m.get("metric") == "Average Order Value (AOV)"), None)
        base_cr = (cr_m["value"] / 100.0) if (cr_m and cr_m.get("value") is not None) else None
        out["custom_scenario_estimate"] = build_impact_scenario_estimate(
            measured_visitors=None,
            measured_conversion_rate=base_cr,
            hypothetical_conversion_rate=(base_cr * (1.0 + hypothetical_lift_pct / 100.0)) if base_cr else None,
            value_per_conversion=aov_m.get("value") if aov_m else None,
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 5. Experiments & Statistical Integrity
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/experiments/create", status_code=status.HTTP_201_CREATED)
async def create_experiment(req: CreateExperimentRequest, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    tenant = _tenant(user)
    stmt = format_hypothesis_statement(
        change_experience=req.change_experience,
        target_audience=req.target_audience,
        desired_action=req.desired_action,
        evidence_rationale=req.evidence_rationale,
        primary_metric=req.primary_metric,
        guardrail_metrics=req.guardrail_metrics,
    )
    n_per_var = calculate_required_sample_size(req.baseline_rate_input, req.minimum_detectable_effect)
    exp = CROExperiment(
        tenant_id=tenant,
        audit_id=req.audit_id,
        finding_ids=req.finding_ids,
        title=req.title,
        experiment_type=req.experiment_type,
        hypothesis_statement=stmt,
        target_audience=req.target_audience,
        primary_metric=req.primary_metric,
        guardrail_metrics=req.guardrail_metrics,
        baseline_rate_input=req.baseline_rate_input,
        minimum_detectable_effect=req.minimum_detectable_effect,
        required_sample_per_variant=n_per_var,
        total_required_sample=n_per_var * 2,
        planned_duration_days=req.planned_duration_days,
        owner=req.owner,
    )
    get_cro_store().save_experiment(exp)
    _audit_log(user, "cro.experiment.create", "cro_experiment", exp.experiment_id, {"title": exp.title})
    return exp.model_dump()


@router.get("/experiments")
async def list_experiments(audit_id: Optional[str] = None, status_filter: Optional[str] = Query(default=None, alias="status"), user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    items = get_cro_store().list_experiments(_tenant(user), audit_id=audit_id, status=status_filter)
    return {"items": [e.model_dump() for e in items], "count": len(items)}


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    exp = get_cro_store().get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    return exp.model_dump()


@router.post("/experiments/{experiment_id}/variants")
async def add_experiment_variant(experiment_id: str, req: AddVariantRequest, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    store = get_cro_store()
    tenant = _tenant(user)
    exp = store.get_experiment(tenant, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    var = CROVariant(
        tenant_id=tenant,
        experiment_id=experiment_id,
        name=req.name,
        is_control=req.is_control,
        traffic_allocation_pct=req.traffic_allocation_pct,
        description=req.description,
        changes_spec=req.changes_spec,
    )
    exp.variants.append(var)
    store.save_experiment(exp)
    return exp.model_dump()


@router.post("/experiments/{experiment_id}/approve")
async def approve_experiment(experiment_id: str, user: UserIdentity = Depends(require_permission("patches:approve"))) -> Dict[str, Any]:
    store = get_cro_store()
    exp = store.get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    exp.approval_status = "approved"
    exp.approved_by = user.email
    exp.status = CROExperimentStatus.APPROVED.value
    store.save_experiment(exp)
    _audit_log(user, "cro.experiment.approve", "cro_experiment", experiment_id, {"approved_by": user.email})
    return exp.model_dump()


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str, user: UserIdentity = Depends(require_permission("patches:approve"))) -> Dict[str, Any]:
    store = get_cro_store()
    exp = store.get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    if exp.approval_status != "approved":
        raise HTTPException(status_code=400, detail="Experiment requires explicit approval before starting.")
    exp.status = CROExperimentStatus.RUNNING.value
    exp.start_date = datetime.now(timezone.utc).isoformat()
    store.save_experiment(exp)
    _audit_log(user, "cro.experiment.start", "cro_experiment", experiment_id, {})
    return exp.model_dump()


@router.post("/experiments/{experiment_id}/stop")
async def stop_experiment(experiment_id: str, reason: str = "manual_stop", user: UserIdentity = Depends(require_permission("patches:approve"))) -> Dict[str, Any]:
    store = get_cro_store()
    exp = store.get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    exp.end_date = datetime.now(timezone.utc).isoformat()
    exp.status = CROExperimentStatus.STOPPED_GUARDRAIL.value if "guardrail" in reason.lower() else CROExperimentStatus.COMPLETED.value
    store.save_experiment(exp)
    _audit_log(user, "cro.experiment.stop", "cro_experiment", experiment_id, {"reason": reason})
    return exp.model_dump()


@router.post("/experiments/{experiment_id}/results")
async def evaluate_experiment_results(experiment_id: str, req: RecordExperimentResultsRequest, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    store = get_cro_store()
    exp = store.get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    try:
        res = enterprise_experiment_engine.evaluate_experiment_results(
            experiment=exp,
            control_visitors=req.control_visitors,
            control_conversions=req.control_conversions,
            variant_visitors=req.variant_visitors,
            variant_conversions=req.variant_conversions,
            days_elapsed=req.days_elapsed,
            guardrail_deltas=req.guardrail_deltas,
            num_comparisons=req.num_comparisons,
            expected_control_share=req.expected_control_share,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    exp.latest_result = res
    if res.decision == "stopped_guardrail":
        exp.status = CROExperimentStatus.STOPPED_GUARDRAIL.value
    elif res.decision in ("winner", "loser"):
        exp.status = CROExperimentStatus.COMPLETED.value
    else:
        exp.status = CROExperimentStatus.INCONCLUSIVE.value
    store.save_experiment(exp)
    return {"experiment": exp.model_dump(), "result": res.model_dump()}


@router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    exp = get_cro_store().get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="CRO experiment not found.")
    return {"experiment_id": experiment_id, "status": exp.status, "latest_result": exp.latest_result.model_dump() if exp.latest_result else None}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Remediation Packs, Tasks, Approval, Deployment & Independent Verification
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/remediation/packs")
async def list_remediation_packs(user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    packs = get_cro_store().list_remediation_packs(_tenant(user))
    return {"items": [p.model_dump() for p in packs], "count": len(packs)}


@router.get("/remediation/tasks")
async def list_remediation_tasks(
    audit_id: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    department: Optional[str] = None,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    tasks = get_cro_store().list_remediation_tasks(_tenant(user), audit_id=audit_id, status=status_filter, department=department)
    return {"items": [t.model_dump() for t in tasks], "views": CRORemediationCenter.build_operational_views(tasks), "count": len(tasks)}


@router.get("/remediation/tasks/{task_id}")
async def get_remediation_task(task_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    store = get_cro_store()
    tenant = _tenant(user)
    task = store.get_remediation_task(tenant, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")
    vers = store.list_verifications(tenant, task_id=task_id)
    return {"task": task.model_dump(), "verifications": [v.model_dump() for v in vers]}


@router.post("/remediation/tasks/{task_id}/approve")
async def approve_remediation_task(task_id: str, user: UserIdentity = Depends(require_permission("patches:approve"))) -> Dict[str, Any]:
    store = get_cro_store()
    task = store.get_remediation_task(_tenant(user), task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")
    task.approval_status = "approved"
    task.approved_by = user.email
    task.approved_at = datetime.now(timezone.utc).isoformat()
    task.status = CROTaskStatus.APPROVED.value
    store.save_remediation_task(task)
    _audit_log(user, "cro.remediation.approve", "cro_task", task_id, {"approved_by": user.email})
    return task.model_dump()


@router.post("/remediation/tasks/{task_id}/deploy")
async def deploy_remediation_task(task_id: str, req: DeployTaskRequest, user: UserIdentity = Depends(require_permission("patches:export_pr"))) -> Dict[str, Any]:
    verifier = CROIndependentVerificationEngine(get_cro_store())
    try:
        task = verifier.mark_deployed(tenant_id=_tenant(user), task_id=task_id, deployed_by=user.email, deployment_ref=req.deployment_ref)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _audit_log(user, "cro.remediation.deploy", "cro_task", task_id, {"deployment_ref": req.deployment_ref})
    return task.model_dump()


@router.post("/remediation/tasks/{task_id}/verify")
async def verify_remediation_task(task_id: str, req: VerifyTaskRequest, user: UserIdentity = Depends(require_permission("provenance:verify"))) -> Dict[str, Any]:
    verifier = CROIndependentVerificationEngine(get_cro_store())
    try:
        ver = await verifier.verify_task(
            tenant_id=_tenant(user),
            task_id=task_id,
            verifier=user.email,
            before_html=req.before_html,
            after_html=req.after_html,
            expected_text_present=req.expected_text_present,
            analytics_event_confirmed=req.analytics_event_confirmed,
            pre_conversion_metrics=req.pre_conversion_metrics,
            post_conversion_metrics=req.post_conversion_metrics,
            use_live_browser=req.use_live_browser,
            viewport=req.viewport,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    _audit_log(user, "cro.remediation.verify", "cro_verification", ver.verification_id, {"task_id": task_id, "implementation_verified": ver.implementation_verified})
    return ver.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Continuous Monitoring & Alerts
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/monitoring/schedules", status_code=status.HTTP_201_CREATED)
async def create_monitoring_schedule(req: CreateScheduleRequest, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    mon = CROMonitoringEngine(get_cro_store())
    sched = mon.create_schedule(
        tenant_id=_tenant(user),
        domain=req.domain,
        target_urls=req.target_urls,
        cadence=req.cadence,
        checks_enabled=req.checks_enabled,
    )
    return sched.model_dump()


@router.get("/monitoring/schedules")
async def list_monitoring_schedules(domain: Optional[str] = None, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    items = get_cro_store().list_monitoring_schedules(_tenant(user), domain=domain)
    return {"items": [s.model_dump() for s in items], "count": len(items)}


@router.get("/monitoring/alerts")
async def list_monitoring_alerts(domain: Optional[str] = None, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    items = get_cro_store().list_monitoring_alerts(_tenant(user), domain=domain)
    return {"items": [a.model_dump() for a in items], "count": len(items)}


@router.get("/monitoring/history")
async def get_monitoring_history(domain: Optional[str] = None, limit: int = Query(default=30, ge=1, le=200), user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    store = get_cro_store()
    tenant = _tenant(user)
    audits = store.list_audits(tenant, domain=domain, limit=limit)
    alerts = store.list_monitoring_alerts(tenant, domain=domain, limit=limit)
    return {
        "domain": domain,
        "audits": [a.model_dump() for a in audits],
        "alerts": [al.model_dump() for al in alerts],
        "comparison_disclosure": "Audit comparisons disclose methodology_version, scope coverage, and connector status so changes in data sources are transparent.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. Reports (14 Audience Profiles · HTML / JSON / PDF)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/reports/create", status_code=status.HTTP_201_CREATED)
async def create_cro_report(req: CreateReportRequest, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    if req.profile not in CRO_REPORT_PROFILES:
        raise HTTPException(status_code=422, detail=f"Unknown CRO report profile '{req.profile}'.")
    tenant = _tenant(user)
    _require_audit(tenant, req.audit_id)
    builder = CROReportBuilder(get_cro_store())
    rep, _content = await builder.publish_report(tenant_id=tenant, audit_id=req.audit_id, profile=req.profile, fmt=req.format)
    return {
        "report": rep.model_dump(),
        "download_url": f"/api/v1/cro/reports/{rep.report_id}/download",
    }


@router.get("/reports/{report_id}")
async def get_cro_report(report_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    rep = get_cro_store().get_report(_tenant(user), report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="CRO report not found.")
    return rep.model_dump()


@router.get("/reports/{report_id}/download")
async def download_cro_report(report_id: str, user: UserIdentity = Depends(get_current_user)):
    store = get_cro_store()
    rep = store.get_report(_tenant(user), report_id)
    if not rep or not rep.storage_uri:
        raise HTTPException(status_code=404, detail="CRO report artifact not found.")
    from app.db.storage_cas import get_cas_storage
    raw = get_cas_storage().get(rep.storage_uri)
    if raw is None:
        raise HTTPException(status_code=404, detail="Stored report content missing from CAS.")
    media_map = {"pdf": "application/pdf", "json": "application/json", "html": "text/html"}
    media = media_map.get(rep.format, "application/octet-stream")
    return Response(
        content=raw,
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{rep.profile}_{rep.audit_id}.{rep.format}"'},
    )
