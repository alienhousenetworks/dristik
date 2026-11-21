"""Phase 27 — Complete Enterprise GEO REST & SSE API Router (`/api/v1/geo/*`).

Enforces:
- Pydantic v2 request/response validation
- Strict tenant isolation (`user.org_id`)
- Role-based access control (`require_permission`—developers can update/deploy
  remediation tasks with `patches:generate`, but ONLY reviewers/auditors/admins
  with `findings:approve` / `provenance:verify` can approve or independently verify)
- SSRF URL validation (`is_safe_url`)
- Fernet encrypted provider credentials (`GEOConnectorManager`)—secrets never leaked
- Pagination, filtering, idempotency keys, SSE streaming of all 17 `geo.*` events
- SOC 2 enterprise audit logging (`EnterpriseAuditLogger`)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.security.enterprise_audit_logger import EnterpriseAuditLogger
from app.core.security.ssrf import is_safe_url
from app.db.geo_schema import get_geo_store
from app.geo.adapters.base import EnginePromptRequest
from app.geo.connectors import GEOConnectorManager, redact_prompt_pii
from app.geo.entity_profile import approve_brand_fact
from app.geo.experiments import GEOExperimentationEngine
from app.geo.models import (
    GEOAuditScope,
    GEODataQualityState,
    GEOEntity,
    GEOEntityFactStatus,
    GEOPromptCategory,
    GEOPromptRun,
    GEOTaskStatus,
    GEOTestPrompt,
    GEOTestingMode,
)
from app.geo.monitoring import GEOMonitoringEngine
from app.geo.orchestrator import GEOAuditOrchestrator
from app.geo.prompt_intelligence import (
    CATEGORY_INTENT_MAP,
    generate_prompt_suite,
    normalize_prompt_text,
    validate_prompt_quality,
)
from app.geo.remediation_center import GEORemediationCenter
from app.geo.reporting.builder import GEOReportBuilder
from app.geo.reporting.section_registry import GEO_REPORT_PROFILES
from app.geo.response_analyzer import analyze_prompt_run_response
from app.geo.verification_engine import GEOIndependentVerificationEngine
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission

router = APIRouter(prefix="/geo", tags=["GEO Enterprise Intelligence"])

ACTIVE_GEO_ORCHESTRATORS: Dict[str, GEOAuditOrchestrator] = {}


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


class CreateGEOAuditRequest(BaseModel):
    target_url: str = Field(..., min_length=4)
    brand_name: Optional[str] = None
    brand_aliases: List[str] = Field(default_factory=list)
    industry: str = ""
    products: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=lambda: ["US"])
    languages: List[str] = Field(default_factory=lambda: ["en"])
    competitors: List[str] = Field(default_factory=list)
    target_audience: str = ""
    platforms_requested: List[str] = Field(default_factory=lambda: ["chatgpt", "gemini", "claude", "perplexity"])
    mode: str = Field(default="standard", pattern="^(quick|standard|deep|monitoring)$")
    repetitions: int = Field(default=1, ge=1, le=5)
    max_prompts: int = Field(default=18, ge=4, le=200)
    budget_usd: float = Field(default=5.0, ge=0.0, le=250.0)
    per_provider_budget_usd: Dict[str, float] = Field(default_factory=dict)
    allow_provider_fallback: bool = False
    pii_redaction_enabled: bool = True
    allow_live_provider_calls: bool = True
    seed_pages: Optional[List[Dict[str, Any]]] = None
    robots_txt: Optional[str] = None
    custom_prompts: Optional[List[Dict[str, Any]]] = None
    run_async: bool = False


class GeneratePromptsRequest(BaseModel):
    audit_id: Optional[str] = None
    domain: str
    website_url: Optional[str] = None
    brand_name: str
    industry: str = ""
    products: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    competitors: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=lambda: ["US"])
    languages: List[str] = Field(default_factory=lambda: ["en"])
    target_audience: str = ""
    max_prompts: int = Field(default=18, ge=4, le=200)
    version: int = Field(default=1, ge=1)


class ValidatePromptRequest(BaseModel):
    question: str
    brand_name: str
    category: GEOPromptCategory = GEOPromptCategory.CATEGORY_DISCOVERY
    is_branded: bool = False
    existing_questions: List[str] = Field(default_factory=list)


class ApprovePromptRequest(BaseModel):
    prompt_id: Optional[str] = None
    audit_id: Optional[str] = None
    question: Optional[str] = None
    category: GEOPromptCategory = GEOPromptCategory.CATEGORY_DISCOVERY
    is_branded: bool = False
    approval_status: str = Field(default="approved", pattern="^(draft|approved|excluded)$")
    market: str = "US"
    language: str = "en"
    target_brand: str = ""


class ConnectPlatformRequest(BaseModel):
    platform_id: str
    api_key: str = Field(..., min_length=4)
    model: Optional[str] = None
    endpoint_url: Optional[str] = None
    testing_mode: Optional[GEOTestingMode] = None


class TestPlatformRequest(BaseModel):
    platform_id: str
    prompt: str = "Briefly summarize what makes an enterprise SaaS documentation page clear."


class RunLabPromptRequest(BaseModel):
    audit_id: Optional[str] = None
    prompt: str = Field(..., min_length=6)
    brand_name: str
    domain: str
    competitors: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=lambda: ["chatgpt", "gemini", "claude", "perplexity"])
    pii_redaction_enabled: bool = True


class ApproveEntityFactRequest(BaseModel):
    entity_id: Optional[str] = None
    audit_id: Optional[str] = None
    entity_type: str = "brand"
    entity_name: str
    attribute: str
    value: Any


class UpdateTaskStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|blocked)$")
    owner: Optional[str] = None


class DeployTaskRequest(BaseModel):
    deployment_ref: str = Field(..., min_length=2)


class VerifyTaskRequest(BaseModel):
    before_html: Optional[str] = None
    after_html: Optional[str] = None
    target_url: Optional[str] = None
    expected_text_present: Optional[str] = None
    expected_schema_type: Optional[str] = None
    pre_prompt_metrics: Optional[Dict[str, Any]] = None
    post_prompt_metrics: Optional[Dict[str, Any]] = None
    retest_metadata: Optional[Dict[str, Any]] = None
    live_recrawl: bool = False


class CreateExperimentRequest(BaseModel):
    audit_id: Optional[str] = None
    title: str
    hypothesis: str
    target_urls: List[str] = Field(default_factory=list)
    target_entities: List[str] = Field(default_factory=list)
    change_description: str = ""
    prompt_suite_version: int = 1
    platforms_tested: List[str] = Field(default_factory=list)
    repetitions: int = Field(default=1, ge=1, le=5)
    baseline_metrics: Optional[Dict[str, Any]] = None


class RecordExperimentResultRequest(BaseModel):
    retest_metrics: Dict[str, Any]
    deployment_ref: Optional[str] = None
    platforms_tested: Optional[List[str]] = None
    model_version_changed: bool = False


class CreateScheduleRequest(BaseModel):
    domain: str
    brand_name: str = ""
    cadence: str = Field(default="weekly", pattern="^(daily|weekly|monthly)$")
    platforms: List[str] = Field(default_factory=lambda: ["chatgpt", "gemini", "claude", "perplexity"])
    max_budget_per_run_usd: float = Field(default=2.0, ge=0.0, le=100.0)
    checks_enabled: Optional[List[str]] = None


class GenerateReportRequest(BaseModel):
    audit_id: str
    profile: str = "complete_audit_book"
    format: str = Field(default="html", pattern="^(html|json|pdf)$")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Audits & Real-Time SSE Progress
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/audits", status_code=status.HTTP_201_CREATED)
async def create_geo_audit(
    req: CreateGEOAuditRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    if not req.seed_pages:
        safe, reason = is_safe_url(req.target_url)
        if not safe:
            raise HTTPException(status_code=400, detail=f"URL blocked by SSRF security guard: {reason}")

    store = get_geo_store()
    tenant = _tenant(user)
    if idempotency_key:
        existing = store.find_audit_by_idempotency(tenant, idempotency_key)
        if existing:
            return {"audit": existing.model_dump(), "idempotent_replay": True}

    orch = GEOAuditOrchestrator(
        tenant_id=tenant,
        target_url=req.target_url,
        brand_name=req.brand_name,
        brand_aliases=req.brand_aliases,
        industry=req.industry,
        products=req.products,
        services=req.services,
        markets=req.markets,
        languages=req.languages,
        competitors=req.competitors,
        target_audience=req.target_audience,
        platforms_requested=req.platforms_requested,
        mode=req.mode,
        repetitions=req.repetitions,
        max_prompts=req.max_prompts,
        budget_usd=req.budget_usd,
        per_provider_budget_usd=req.per_provider_budget_usd,
        allow_provider_fallback=req.allow_provider_fallback,
        pii_redaction_enabled=req.pii_redaction_enabled,
        allow_live_provider_calls=req.allow_live_provider_calls,
        seed_pages=req.seed_pages,
        robots_txt=req.robots_txt,
        custom_prompts=req.custom_prompts,
        idempotency_key=idempotency_key,
        store=store,
    )
    ACTIVE_GEO_ORCHESTRATORS[f"{tenant}:{orch.audit_id}"] = orch
    _audit_log(user, "geo.audit.create", "geo_audit", orch.audit_id, {"target_url": req.target_url, "mode": req.mode})

    if req.run_async:
        background_tasks.add_task(orch.run)
        return {"audit": orch.audit.model_dump(), "async": True}

    result = await orch.run()
    return result


@router.get("/audits")
def list_geo_audits(
    domain: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store = get_geo_store()
    items = store.list_audits(_tenant(user), domain=domain, limit=limit, offset=offset)
    return {"audits": [a.model_dump() for a in items], "count": len(items), "limit": limit, "offset": offset}


@router.get("/audits/{audit_id}")
def get_geo_audit(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store = get_geo_store()
    audit = store.get_audit(_tenant(user), audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="GEO audit not found.")
    return {
        "audit": audit.model_dump(),
        "scorecard": store.get_artifact(_tenant(user), audit_id, "scorecard"),
        "qa_report": store.get_artifact(_tenant(user), audit_id, "qa_report"),
        "prompt_coverage": store.get_artifact(_tenant(user), audit_id, "prompt_coverage"),
    }


@router.get("/audits/{audit_id}/bundle")
def get_geo_audit_bundle(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    """Single canonical bundle for the Enterprise GEO Frontend Workspace."""
    store = get_geo_store()
    tenant = _tenant(user)
    builder = GEOReportBuilder(store=store)
    try:
        dataset = builder.build_canonical_dataset(tenant, audit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="GEO audit not found.")
    conn_mgr = GEOConnectorManager(store=store)
    dataset["connector_statuses"] = conn_mgr.list_connections_status(tenant)
    dataset["external_connectors"] = conn_mgr.get_external_connector_summary()
    dataset["capability_matrix"] = conn_mgr.capability_matrix()
    dataset["report_profiles"] = GEO_REPORT_PROFILES
    dataset["monitoring_schedules"] = [s.model_dump() for s in store.list_schedules(tenant, domain=dataset["audit"]["domain"])]
    dataset["monitoring_alerts"] = [a.model_dump() for a in store.list_alerts(tenant, domain=dataset["audit"]["domain"])]
    dataset["monitoring_history"] = GEOMonitoringEngine(store=store).build_monitoring_history(tenant, domain=dataset["audit"]["domain"])
    return dataset


@router.post("/audits/{audit_id}/cancel")
def cancel_geo_audit(audit_id: str, user: UserIdentity = Depends(require_permission("audit:create"))) -> Dict[str, Any]:
    key = f"{_tenant(user)}:{audit_id}"
    orch = ACTIVE_GEO_ORCHESTRATORS.get(key)
    if orch:
        orch.cancel()
        return {"audit_id": audit_id, "status": "cancelled"}
    store = get_geo_store()
    audit = store.get_audit(_tenant(user), audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="GEO audit not found.")
    audit.status = "cancelled"
    store.save_audit(audit)
    return {"audit_id": audit_id, "status": "cancelled"}


@router.get("/audits/{audit_id}/progress")
async def stream_geo_progress(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))):
    import asyncio
    import json as _json

    tenant = _tenant(user)
    store = get_geo_store()
    audit = store.get_audit(tenant, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="GEO audit not found.")
    orch = ACTIVE_GEO_ORCHESTRATORS.get(f"{tenant}:{audit_id}")
    terminal_events = {
        "geo.audit.completed",
        "geo.audit.partial",
        "geo.audit.failed",
        "AUDIT_COMPLETED",
        "AUDIT_FAILED",
        "AUDIT_CANCELLED",
    }
    if orch:
        async def _geo_sse():
            q: asyncio.Queue = asyncio.Queue(maxsize=200)
            for past in orch.events.get_history():
                yield f"data: {_json.dumps(past)}\n\n"
                if past.get("type") in terminal_events:
                    return
            orch.events._subscribers.add(q)
            try:
                while True:
                    ev = await q.get()
                    yield f"data: {_json.dumps(ev)}\n\n"
                    if ev.get("type") in terminal_events:
                        break
            finally:
                orch.events._subscribers.discard(q)

        return StreamingResponse(_geo_sse(), media_type="text/event-stream")
    # Replay completed checkpoint state if orchestrator is no longer resident
    execs = store.list_agent_executions(tenant, audit_id)
    return {
        "audit_id": audit_id,
        "status": audit.status,
        "publication_status": audit.publication_status,
        "current_stage": audit.current_stage,
        "checkpoints": execs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Audit Sub-Resources (All Phase 27 Read Endpoints)
# ─────────────────────────────────────────────────────────────────────────────


def _require_audit(tenant: str, audit_id: str):
    store = get_geo_store()
    audit = store.get_audit(tenant, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="GEO audit not found.")
    return store, audit


@router.get("/audits/{audit_id}/platforms")
def get_audit_platforms(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    items = store.list_platforms(_tenant(user), audit_id)
    return {"audit_id": audit_id, "platforms": [p.model_dump() for p in items]}


@router.get("/audits/{audit_id}/prompts")
def get_audit_prompts(
    audit_id: str,
    is_branded: Optional[bool] = Query(default=None),
    approval_status: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    items = store.list_prompts(_tenant(user), audit_id=audit_id, is_branded=is_branded, approval_status=approval_status)
    return {
        "audit_id": audit_id,
        "prompts": [p.model_dump() for p in items],
        "coverage": store.get_artifact(_tenant(user), audit_id, "prompt_coverage"),
    }


@router.get("/audits/{audit_id}/responses")
def get_audit_responses(
    audit_id: str,
    platform_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    resps = store.list_responses(_tenant(user), audit_id, platform_id=platform_id)
    runs = {r.run_id: r.model_dump() for r in store.list_prompt_runs(_tenant(user), audit_id)}
    mentions = store.list_mentions(_tenant(user), audit_id)
    return {
        "audit_id": audit_id,
        "responses": [r.model_dump() for r in resps],
        "runs_by_id": runs,
        "mentions": [m.model_dump() for m in mentions],
    }


@router.get("/audits/{audit_id}/visibility")
def get_audit_visibility(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    dept = store.get_artifact(_tenant(user), audit_id, "department_artifacts") or {}
    return {
        "audit_id": audit_id,
        "visibility": dept.get("department_b") or {},
        "market_intent": dept.get("department_h") or {},
        "mentions": [m.model_dump() for m in store.list_mentions(_tenant(user), audit_id)],
    }


@router.get("/audits/{audit_id}/citations")
def get_audit_citations(
    audit_id: str,
    platform_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    return {
        "audit_id": audit_id,
        "citations": [c.model_dump() for c in store.list_citations(_tenant(user), audit_id, platform_id=platform_id)],
        "citation_graph": store.get_artifact(_tenant(user), audit_id, "citation_graph") or {},
    }


@router.get("/audits/{audit_id}/entities")
def get_audit_entities(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    dept = store.get_artifact(_tenant(user), audit_id, "department_artifacts") or {}
    return {
        "audit_id": audit_id,
        "entities": [e.model_dump() for e in store.list_entities(_tenant(user), audit_id=audit_id)],
        "summary": dept.get("department_a") or {},
    }


@router.get("/audits/{audit_id}/sources")
def get_audit_sources(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    dept = store.get_artifact(_tenant(user), audit_id, "department_artifacts") or {}
    return {
        "audit_id": audit_id,
        "sources": [s.model_dump() for s in store.list_external_sources(_tenant(user), audit_id)],
        "reputation_summary": dept.get("department_f") or {},
    }


@router.get("/audits/{audit_id}/competitors")
def get_audit_competitors(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    dept = store.get_artifact(_tenant(user), audit_id, "department_artifacts") or {}
    return {"audit_id": audit_id, "competitive": dept.get("department_g") or {}}


@router.get("/audits/{audit_id}/findings")
def get_audit_findings(
    audit_id: str,
    severity: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("findings:read")),
) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    items = store.list_findings(_tenant(user), audit_id, severity=severity, category=category)
    return {"audit_id": audit_id, "findings": [f.model_dump() for f in items], "count": len(items)}


@router.get("/audits/{audit_id}/scores")
def get_audit_scores(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    return {"audit_id": audit_id, "scorecard": store.get_artifact(_tenant(user), audit_id, "scorecard") or {}}


@router.get("/audits/{audit_id}/evidence")
def get_audit_evidence(audit_id: str, user: UserIdentity = Depends(require_permission("evidence:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    return {
        "audit_id": audit_id,
        "snapshots": [s.model_dump() for s in store.list_snapshots(_tenant(user), audit_id)],
        "pages": [p.model_dump() for p in store.list_pages(_tenant(user), audit_id)],
    }


@router.get("/audits/{audit_id}/recommendations")
def get_audit_recommendations(audit_id: str, user: UserIdentity = Depends(require_permission("findings:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    return {"audit_id": audit_id, "recommendations": [r.model_dump() for r in store.list_recommendations(_tenant(user), audit_id)]}


@router.get("/audits/{audit_id}/remediation")
def get_audit_remediation(audit_id: str, user: UserIdentity = Depends(require_permission("findings:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    pack = store.get_remediation_pack(_tenant(user), audit_id)
    verifs = store.list_verifications(_tenant(user), audit_id=audit_id)
    return {
        "audit_id": audit_id,
        "remediation_pack": pack.model_dump() if pack else None,
        "verifications": [v.model_dump() for v in verifs],
    }


@router.get("/audits/{audit_id}/reports")
def get_audit_reports(audit_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    store, _ = _require_audit(_tenant(user), audit_id)
    return {
        "audit_id": audit_id,
        "reports": [r.model_dump() for r in store.list_reports(_tenant(user), audit_id=audit_id)],
        "profiles": GEO_REPORT_PROFILES,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Prompt Intelligence & Prompt Test Lab
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/prompts/generate")
def generate_prompts_endpoint(
    req: GeneratePromptsRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    store = get_geo_store()
    scope = GEOAuditScope(
        tenant_id=_tenant(user),
        audit_id=req.audit_id,
        domain=req.domain.lower().strip(),
        website_url=req.website_url or f"https://{req.domain.lower().strip()}/",
        brand_name=req.brand_name,
        industry=req.industry,
        products=req.products,
        services=req.services,
        competitors=req.competitors,
        markets=req.markets,
        languages=req.languages,
        target_audience=req.target_audience,
        max_prompts=req.max_prompts,
    )
    prompts = generate_prompt_suite(scope, audit_id=req.audit_id, version=req.version)
    for p in prompts:
        store.save_prompt(p)
    return {"prompts": [p.model_dump() for p in prompts], "count": len(prompts), "version": req.version}


@router.post("/prompts/validate")
def validate_prompt_endpoint(
    req: ValidatePromptRequest,
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    valid, flags = validate_prompt_quality(
        req.question,
        brand_name=req.brand_name,
        category=req.category,
        is_branded=req.is_branded,
        existing_questions=req.existing_questions,
    )
    return {"valid": valid, "quality_flags": flags, "normalized_question": normalize_prompt_text(req.question)}


@router.post("/prompts/approve")
def approve_prompt_endpoint(
    req: ApprovePromptRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    store = get_geo_store()
    tenant = _tenant(user)
    if req.prompt_id:
        prompt = store.get_prompt(tenant, req.prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found.")
        if req.question:
            prompt.question = req.question
            prompt.normalized_question = normalize_prompt_text(req.question)
            prompt.version += 1
        prompt.approval_status = req.approval_status
        prompt.is_branded = req.is_branded
        prompt.category = req.category
        store.save_prompt(prompt)
        return {"prompt": prompt.model_dump()}

    if not req.question:
        raise HTTPException(status_code=422, detail="Either prompt_id or question is required.")
    prompt = GEOTestPrompt(
        tenant_id=tenant,
        audit_id=req.audit_id,
        question=req.question,
        normalized_question=normalize_prompt_text(req.question),
        category=req.category,
        intent=CATEGORY_INTENT_MAP[req.category],
        is_branded=req.is_branded,
        target_brand=req.target_brand,
        market=req.market,
        language=req.language,
        approval_status=req.approval_status,
    )
    store.save_prompt(prompt)
    return {"prompt": prompt.model_dump()}


@router.get("/prompts/versions")
def list_prompt_versions(
    audit_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store = get_geo_store()
    prompts = store.list_prompts(_tenant(user), audit_id=audit_id)
    by_ver: Dict[int, int] = {}
    for p in prompts:
        by_ver[p.version] = by_ver.get(p.version, 0) + 1
    return {
        "versions": [{"version": v, "prompt_count": c} for v, c in sorted(by_ver.items())],
        "total_prompts": len(prompts),
    }


@router.post("/prompts/run")
async def run_prompt_test_lab(
    req: RunLabPromptRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    """Prompt Test Lab: executes one prompt side-by-side across selected platforms and returns verbatim outputs."""
    store = get_geo_store()
    tenant = _tenant(user)
    conn_mgr = GEOConnectorManager(store=store)
    clean_prompt, pii_redacted = redact_prompt_pii(req.prompt) if req.pii_redaction_enabled else (req.prompt, [])
    scope = GEOAuditScope(
        tenant_id=tenant,
        audit_id=req.audit_id,
        domain=req.domain.lower().strip(),
        website_url=f"https://{req.domain.lower().strip()}/",
        brand_name=req.brand_name,
        competitors=req.competitors,
        platforms_requested=req.platforms,
    )
    results: List[Dict[str, Any]] = []
    for pid in req.platforms:
        ad = conn_mgr.resolve_adapter_for_tenant(tenant, pid)
        if ad is None or not ad.is_configured():
            results.append({
                "platform_id": pid,
                "display_name": ad.display_name if ad else pid,
                "status": GEODataQualityState.NOT_CONFIGURED.value,
                "testing_mode": ad.default_testing_mode.value if ad else GEOTestingMode.API_MODEL_ONLY.value,
                "response_text": None,
                "error": f"Provider '{pid}' is not configured. Add credentials in GEO Connectors.",
            })
            continue
        raw = await ad.execute_prompt(EnginePromptRequest(prompt=clean_prompt, enable_search=ad.supports_web_search))
        run_status = GEODataQualityState.OBSERVED if (raw.is_live and raw.raw_content.strip()) else GEODataQualityState.FAILED
        run = GEOPromptRun(
            tenant_id=tenant,
            audit_id=req.audit_id or "lab",
            prompt_id="lab_prompt",
            original_prompt=req.prompt,
            normalized_prompt=clean_prompt,
            platform_id=pid,
            platform_name=raw.engine_name,
            model_name=ad.model,
            model_version=raw.model_version,
            testing_mode=raw.testing_mode,
            status=run_status,
            latency_ms=raw.latency_ms,
            cost_usd=raw.estimated_cost_usd,
            error_message=raw.error,
            data_quality_state=run_status,
        )
        if run_status == GEODataQualityState.OBSERVED:
            resp_obj, ments, cits = analyze_prompt_run_response(
                run=run,
                raw_text=raw.raw_content,
                raw_citations=ad.extract_citations(raw),
                tool_use_metadata=raw.tool_use_metadata,
                scope=scope,
            )
            results.append({
                "platform_id": pid,
                "display_name": raw.engine_name,
                "model_version": raw.model_version,
                "testing_mode": raw.testing_mode.value,
                "status": GEODataQualityState.OBSERVED.value,
                "latency_ms": raw.latency_ms,
                "cost_usd": raw.estimated_cost_usd,
                "response": resp_obj.model_dump(),
                "mentions": [m.model_dump() for m in ments],
                "citations": [c.model_dump() for c in cits],
            })
        else:
            results.append({
                "platform_id": pid,
                "display_name": raw.engine_name,
                "model_version": raw.model_version,
                "testing_mode": raw.testing_mode.value,
                "status": GEODataQualityState.FAILED.value,
                "error": raw.error,
            })

    return {"prompt": req.prompt, "pii_redacted": pii_redacted, "results": results}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Platforms & Encrypted Provider Connections
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/platforms/available")
def list_available_platforms(user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    conn_mgr = GEOConnectorManager(store=get_geo_store())
    return {
        "platforms": conn_mgr.list_connections_status(_tenant(user)),
        "external_connectors": conn_mgr.get_external_connector_summary(),
    }


@router.get("/platforms/capabilities")
def get_platform_capabilities(user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    return {"capabilities": GEOConnectorManager.capability_matrix()}


@router.get("/platforms/connections")
def get_platform_connections(user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    conn_mgr = GEOConnectorManager(store=get_geo_store())
    return {"connections": conn_mgr.list_connections_status(_tenant(user))}


@router.post("/platforms/connections")
def connect_platform_endpoint(
    req: ConnectPlatformRequest,
    user: UserIdentity = Depends(require_permission("policy:manage")),
) -> Dict[str, Any]:
    conn_mgr = GEOConnectorManager(store=get_geo_store())
    try:
        conn = conn_mgr.connect_provider(
            tenant_id=_tenant(user),
            platform_id=req.platform_id,
            api_key=req.api_key,
            model=req.model,
            endpoint_url=req.endpoint_url,
            testing_mode=req.testing_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _audit_log(user, "geo.platform.connect", "geo_provider_connection", conn.connection_id, {"platform_id": conn.platform_id})
    return {"connection": conn.model_dump()}


@router.delete("/platforms/connections/{platform_id}")
def disconnect_platform_endpoint(
    platform_id: str,
    user: UserIdentity = Depends(require_permission("policy:manage")),
) -> Dict[str, Any]:
    store = get_geo_store()
    deleted = store.delete_provider_connection(_tenant(user), platform_id.lower().strip())
    return {"platform_id": platform_id, "deleted": deleted}


@router.post("/platforms/test")
async def test_platform_connection(
    req: TestPlatformRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    conn_mgr = GEOConnectorManager(store=get_geo_store())
    ad = conn_mgr.resolve_adapter_for_tenant(_tenant(user), req.platform_id)
    if ad is None:
        raise HTTPException(status_code=404, detail=f"Unknown GEO platform '{req.platform_id}'.")
    if not ad.is_configured():
        return {
            "platform_id": ad.engine_id,
            "connected": False,
            "status": GEODataQualityState.NOT_CONFIGURED.value,
            "capabilities": ad.get_capabilities().model_dump(),
            "message": "No credentials configured for this platform.",
        }
    raw = await ad.execute_prompt(EnginePromptRequest(prompt=req.prompt, max_tokens=64))
    return {
        "platform_id": ad.engine_id,
        "connected": raw.is_live,
        "status": GEODataQualityState.OBSERVED.value if raw.is_live else GEODataQualityState.FAILED.value,
        "model_version": raw.model_version,
        "testing_mode": raw.testing_mode.value,
        "latency_ms": raw.latency_ms,
        "error": raw.error,
        "capabilities": ad.get_capabilities().model_dump(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Brand Knowledge Profile Approval
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/entities/approve")
def approve_brand_entity_fact(
    req: ApproveEntityFactRequest,
    user: UserIdentity = Depends(require_permission("findings:approve")),
) -> Dict[str, Any]:
    """Approve an official brand fact and lock it against automatic AI overwrites."""
    store = get_geo_store()
    tenant = _tenant(user)
    if req.entity_id:
        ent = store.get_entity(tenant, req.entity_id)
        if not ent:
            raise HTTPException(status_code=404, detail="GEO entity record not found.")
        approve_brand_fact(ent, new_value=req.value, approved_by=user.email)
    else:
        ent = GEOEntity(
            tenant_id=tenant,
            audit_id=req.audit_id,
            entity_type=req.entity_type,
            entity_name=req.entity_name,
            attribute=req.attribute,
            value=req.value,
            fact_status=GEOEntityFactStatus.CONFIRMED,
        )
        approve_brand_fact(ent, new_value=req.value, approved_by=user.email)
    store.save_entity(ent)
    _audit_log(user, "geo.entity.approve", "geo_entity", ent.entity_id, {"attribute": ent.attribute})
    return {"entity": ent.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Findings & Consolidated Remediation / Role-Gated Independent Verification
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/findings/{finding_id}")
def get_geo_finding(finding_id: str, user: UserIdentity = Depends(require_permission("findings:read"))) -> Dict[str, Any]:
    store = get_geo_store()
    f = store.get_finding(_tenant(user), finding_id)
    if not f:
        raise HTTPException(status_code=404, detail="GEO finding not found.")
    return {"finding": f.model_dump()}


@router.get("/findings/{finding_id}/tasks")
def get_finding_tasks(finding_id: str, user: UserIdentity = Depends(require_permission("findings:read"))) -> Dict[str, Any]:
    store = get_geo_store()
    tasks = [t.model_dump() for t in store.list_remediation_tasks(_tenant(user)) if finding_id in t.finding_ids]
    return {"finding_id": finding_id, "tasks": tasks}


@router.get("/remediation/packs")
def list_remediation_packs(user: UserIdentity = Depends(require_permission("findings:read"))) -> Dict[str, Any]:
    store = get_geo_store()
    return {"packs": [p.model_dump() for p in store.list_remediation_packs(_tenant(user))]}


@router.get("/remediation/tasks")
def list_remediation_tasks(
    audit_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    department: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("findings:read")),
) -> Dict[str, Any]:
    store = get_geo_store()
    tasks = store.list_remediation_tasks(_tenant(user), audit_id=audit_id, status=status_filter, department=department)
    return {"tasks": [t.model_dump() for t in tasks], "count": len(tasks)}


@router.get("/remediation/tasks/{task_id}")
def get_remediation_task(task_id: str, user: UserIdentity = Depends(require_permission("findings:read"))) -> Dict[str, Any]:
    store = get_geo_store()
    task = store.get_remediation_task(_tenant(user), task_id)
    if not task:
        raise HTTPException(status_code=404, detail="GEO remediation task not found.")
    verifs = store.list_verifications(_tenant(user), task_id=task_id)
    return {"task": task.model_dump(), "verifications": [v.model_dump() for v in verifs]}


@router.patch("/remediation/tasks/{task_id}")
def update_remediation_task(
    task_id: str,
    req: UpdateTaskStatusRequest,
    user: UserIdentity = Depends(require_permission("patches:generate")),
) -> Dict[str, Any]:
    """Developers/analysts can update work status (open/in_progress/blocked) — NEVER verified."""
    store = get_geo_store()
    task = store.get_remediation_task(_tenant(user), task_id)
    if not task:
        raise HTTPException(status_code=404, detail="GEO remediation task not found.")
    task.status = req.status
    if req.owner:
        task.owner = req.owner
    store.save_remediation_task(task)
    return {"task": task.model_dump()}


@router.post("/remediation/tasks/{task_id}/approve")
def approve_remediation_task(
    task_id: str,
    user: UserIdentity = Depends(require_permission("findings:approve")),
) -> Dict[str, Any]:
    store = get_geo_store()
    task = store.get_remediation_task(_tenant(user), task_id)
    if not task:
        raise HTTPException(status_code=404, detail="GEO remediation task not found.")
    GEORemediationCenter.approve_task(task, approved_by=user.email)
    store.save_remediation_task(task)
    _audit_log(user, "geo.remediation.approve", "geo_remediation_task", task_id, {"approved_by": user.email})
    return {"task": task.model_dump()}


@router.post("/remediation/tasks/{task_id}/deploy")
def deploy_remediation_task(
    task_id: str,
    req: DeployTaskRequest,
    user: UserIdentity = Depends(require_permission("patches:generate")),
) -> Dict[str, Any]:
    """Developer records deployment reference; task stays DEPLOYED until independently verified."""
    store = get_geo_store()
    task = store.get_remediation_task(_tenant(user), task_id)
    if not task:
        raise HTTPException(status_code=404, detail="GEO remediation task not found.")
    GEORemediationCenter.mark_deployed(task, deployment_ref=req.deployment_ref, deployed_by=user.email)
    store.save_remediation_task(task)
    _audit_log(user, "geo.remediation.deploy", "geo_remediation_task", task_id, {"deployment_ref": req.deployment_ref})
    return {"task": task.model_dump()}


@router.post("/remediation/tasks/{task_id}/verify")
async def verify_remediation_task(
    task_id: str,
    req: VerifyTaskRequest,
    user: UserIdentity = Depends(require_permission("provenance:verify")),
) -> Dict[str, Any]:
    """Independent verification endpoint: requires `provenance:verify` (auditor/admin/owner). Developers cannot self-verify."""
    store = get_geo_store()
    tenant = _tenant(user)
    task = store.get_remediation_task(tenant, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="GEO remediation task not found.")
    ver = await GEOIndependentVerificationEngine.verify_task(
        task=task,
        verified_by=user.email,
        before_html=req.before_html,
        after_html=req.after_html,
        target_url=req.target_url or (task.affected_pages[0] if task.affected_pages else None),
        expected_text_present=req.expected_text_present,
        expected_schema_type=req.expected_schema_type,
        pre_prompt_metrics=req.pre_prompt_metrics,
        post_prompt_metrics=req.post_prompt_metrics,
        retest_metadata=req.retest_metadata,
        live_recrawl=req.live_recrawl,
    )
    store.save_verification(ver)
    store.save_remediation_task(task)
    _audit_log(
        user,
        "geo.remediation.verify",
        "geo_verification",
        ver.verification_id,
        {
            "task_id": task_id,
            "implementation_verified": ver.implementation_verified,
            "outcome_improved": ver.outcome_improved,
            "overall_status": ver.overall_status,
        },
    )
    return {"task": task.model_dump(), "verification": ver.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Controlled Experiments & Scheduled Monitoring
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/experiments/create", status_code=status.HTTP_201_CREATED)
def create_geo_experiment(
    req: CreateExperimentRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    eng = GEOExperimentationEngine(store=get_geo_store())
    exp = eng.create_experiment(
        tenant_id=_tenant(user),
        audit_id=req.audit_id,
        title=req.title,
        hypothesis=req.hypothesis,
        target_urls=req.target_urls,
        target_entities=req.target_entities,
        change_description=req.change_description,
        prompt_suite_version=req.prompt_suite_version,
        platforms_tested=req.platforms_tested,
        repetitions=req.repetitions,
        baseline_metrics=req.baseline_metrics,
    )
    return {"experiment": exp.model_dump()}


@router.get("/experiments")
def list_geo_experiments(
    audit_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store = get_geo_store()
    return {"experiments": [e.model_dump() for e in store.list_experiments(_tenant(user), audit_id=audit_id)]}


@router.get("/experiments/{experiment_id}")
def get_geo_experiment(experiment_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    exp = get_geo_store().get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="GEO experiment not found.")
    return {"experiment": exp.model_dump()}


@router.post("/experiments/{experiment_id}/results")
def record_geo_experiment_results(
    experiment_id: str,
    req: RecordExperimentResultRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    eng = GEOExperimentationEngine(store=get_geo_store())
    try:
        exp = eng.record_retest_results(
            tenant_id=_tenant(user),
            experiment_id=experiment_id,
            retest_metrics=req.retest_metrics,
            deployment_ref=req.deployment_ref,
            platforms_tested=req.platforms_tested,
            model_version_changed=req.model_version_changed,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="GEO experiment not found.")
    return {"experiment": exp.model_dump()}


@router.get("/experiments/{experiment_id}/results")
def get_geo_experiment_results(experiment_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    exp = get_geo_store().get_experiment(_tenant(user), experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="GEO experiment not found.")
    return {
        "experiment_id": exp.experiment_id,
        "status": exp.status,
        "baseline_metrics": exp.baseline_metrics,
        "retest_metrics": exp.retest_metrics,
        "observed_delta": exp.observed_delta,
        "causation_disclaimer": exp.causation_disclaimer,
        "limitations": exp.limitations,
    }


@router.get("/monitoring/schedules")
def list_monitoring_schedules(
    domain: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store = get_geo_store()
    return {"schedules": [s.model_dump() for s in store.list_schedules(_tenant(user), domain=domain)]}


@router.post("/monitoring/schedules", status_code=status.HTTP_201_CREATED)
def create_monitoring_schedule(
    req: CreateScheduleRequest,
    user: UserIdentity = Depends(require_permission("audit:create")),
) -> Dict[str, Any]:
    eng = GEOMonitoringEngine(store=get_geo_store())
    sched = eng.create_schedule(
        tenant_id=_tenant(user),
        domain=req.domain,
        brand_name=req.brand_name,
        cadence=req.cadence,
        platforms=req.platforms,
        max_budget_per_run_usd=req.max_budget_per_run_usd,
        checks_enabled=req.checks_enabled,
    )
    return {"schedule": sched.model_dump()}


@router.get("/monitoring/alerts")
def list_monitoring_alerts(
    domain: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    store = get_geo_store()
    return {"alerts": [a.model_dump() for a in store.list_alerts(_tenant(user), domain=domain)]}


@router.get("/monitoring/history")
def get_monitoring_history(
    domain: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    eng = GEOMonitoringEngine(store=get_geo_store())
    return {"history": eng.build_monitoring_history(_tenant(user), domain=domain, limit=limit)}


# ─────────────────────────────────────────────────────────────────────────────
# 8. Canonical GEO Reports (10 Dynamic Profiles: HTML / JSON / PDF)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/reports/generate", status_code=status.HTTP_201_CREATED)
async def generate_geo_report(
    req: GenerateReportRequest,
    user: UserIdentity = Depends(require_permission("audit:read")),
) -> Dict[str, Any]:
    if req.profile not in GEO_REPORT_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown report profile '{req.profile}'.")
    store = get_geo_store()
    tenant = _tenant(user)
    if not store.get_audit(tenant, req.audit_id):
        raise HTTPException(status_code=404, detail="GEO audit not found.")
    builder = GEOReportBuilder(store=store)
    rep, raw_bytes = await builder.publish_report(
        tenant_id=tenant,
        audit_id=req.audit_id,
        profile=req.profile,
        fmt=req.format,
    )
    _audit_log(user, "geo.report.generate", "geo_report", rep.report_id, {"profile": req.profile, "format": req.format})
    return {"report": rep.model_dump(), "byte_size": len(raw_bytes)}


@router.get("/reports/{report_id}")
def get_geo_report(report_id: str, user: UserIdentity = Depends(require_permission("audit:read"))) -> Dict[str, Any]:
    rep = get_geo_store().get_report(_tenant(user), report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="GEO report not found.")
    return {"report": rep.model_dump()}


@router.get("/reports/{report_id}/download")
def download_geo_report(report_id: str, user: UserIdentity = Depends(require_permission("audit:read"))):
    store = get_geo_store()
    rep = store.get_report(_tenant(user), report_id)
    if not rep or not rep.storage_uri:
        raise HTTPException(status_code=404, detail="GEO report artifact not found.")
    raw = store.read_snapshot_bytes(rep.storage_uri)
    if raw is None:
        raise HTTPException(status_code=404, detail="GEO report snapshot missing from CAS.")
    media = {
        "pdf": "application/pdf",
        "html": "text/html; charset=utf-8",
        "json": "application/json",
    }.get(rep.format, "application/octet-stream")
    fname = f"dristik_geo_{rep.domain}_{rep.profile}.{rep.format}"
    return Response(content=raw, media_type=media, headers={"Content-Disposition": f'attachment; filename="{fname}"'})
