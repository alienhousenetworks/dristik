"""
FastAPI Router for the Central SEO Orchestrator & Multi-Agent Workflow Engine.
Authenticated, tenant-isolated, DB-backed REST & SSE endpoints.
Zero hardcoded fallback pages or synthetic scores.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.db.seo_orchestrator_schema import default_seo_db_path, init_seo_orchestrator_schema
from app.identity.access import require_analysis, require_org_context
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user
from app.seo.audit.internal_links.link_graph_engine import build_internal_link_graph
from app.seo.audit.orchestration.execution_state import AuditConfiguration, AuditMode
from app.seo.audit.orchestrator import SEOAuditOrchestrator

router = APIRouter(prefix="/api/v1/seo/orchestrator", tags=["SEO Orchestrator"])

# Process-local cache of live running orchestrators (durable state persisted in SQLite)
ACTIVE_ORCHESTRATORS: Dict[str, SEOAuditOrchestrator] = {}


class StartAuditRequest(BaseModel):
    domain: str = Field(..., json_schema_extra={"example": "example.com"})
    mode: AuditMode = Field(default=AuditMode.STANDARD, json_schema_extra={"example": "STANDARD"})
    workspace_id: Optional[str] = None
    target_url: Optional[str] = None
    max_pages: Optional[int] = None
    render_javascript: bool = True
    respect_robots_txt: str = "OBEY"
    live_crawl: bool = False


class AuditStatusResponse(BaseModel):
    audit_id: str
    domain: str
    mode: str
    status: str
    current_stage: str
    completed_tasks: int
    failed_tasks: int
    total_tasks: int
    elapsed_time_sec: float


def _load_run_row(audit_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    db_path = default_seo_db_path()
    init_seo_orchestrator_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM seo_audit_runs WHERE id = ?", (audit_id,)).fetchone()
        if not row:
            return None
        row_org = row["org_id"] or ""
        if row_org and row_org != org_id:
            return None
        return dict(row)
    finally:
        conn.close()


def _verify_orchestrator_access(orch: SEOAuditOrchestrator, user: UserIdentity) -> None:
    if orch.config.org_id and not Authorizer.can_access_org(user, orch.config.org_id):
        raise HTTPException(status_code=404, detail=f"Audit execution '{orch.audit_id}' not found.")


@router.post("/audits", status_code=status.HTTP_202_ACCEPTED)
async def start_seo_audit(
    req: StartAuditRequest,
    background_tasks: BackgroundTasks,
    user: UserIdentity = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    """Initiates an authenticated, tenant-scoped multi-agent SEO audit workflow."""
    org_id = require_org_context(user)
    if not Authorizer.can_perform(user, "mission:create"):
        raise HTTPException(status_code=403, detail="Permission 'mission:create' required.")

    clean_domain = req.domain.replace("https://", "").replace("http://", "").rstrip("/")
    ws_id = (req.workspace_id or f"ws_{org_id}").strip()

    # Idempotency check
    if idempotency_key:
        db_path = default_seo_db_path()
        init_seo_orchestrator_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            existing = conn.execute(
                "SELECT id, domain, mode, status FROM seo_audit_runs WHERE org_id = ? AND idempotency_key = ?",
                (org_id, idempotency_key),
            ).fetchone()
            if existing:
                return {
                    "audit_id": existing["id"],
                    "domain": existing["domain"],
                    "mode": existing["mode"],
                    "status": existing["status"],
                    "idempotent_replay": True,
                    "stream_url": f"/api/v1/seo/orchestrator/audits/{existing['id']}/events",
                    "status_url": f"/api/v1/seo/orchestrator/audits/{existing['id']}/status",
                }
        finally:
            conn.close()

    audit_id = f"seo_{clean_domain.replace('.', '_')}_{uuid.uuid4().hex[:8]}"
    config = AuditConfiguration(
        target_url=req.target_url or f"https://{clean_domain}/",
        mode=req.mode,
        org_id=org_id,
        workspace_id=ws_id,
        max_pages=req.max_pages,
        respect_robots_txt=req.respect_robots_txt,
        render_javascript=req.render_javascript,
        live_crawl=req.live_crawl,
        idempotency_key=idempotency_key,
    )

    orchestrator = SEOAuditOrchestrator(audit_id=audit_id, domain=clean_domain, config=config)
    ACTIVE_ORCHESTRATORS[audit_id] = orchestrator

    async def _run_in_background():
        try:
            await orchestrator.run()
        except Exception:
            pass

    background_tasks.add_task(_run_in_background)

    return {
        "audit_id": audit_id,
        "domain": clean_domain,
        "mode": req.mode.value,
        "status": "QUEUED",
        "stream_url": f"/api/v1/seo/orchestrator/audits/{audit_id}/events",
        "status_url": f"/api/v1/seo/orchestrator/audits/{audit_id}/status",
    }


@router.get("/audits/{audit_id}/events")
async def stream_audit_events(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Real-time Server-Sent Events (SSE) stream broadcasting workflow task progression."""
    require_org_context(user)
    orchestrator = ACTIVE_ORCHESTRATORS.get(audit_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Audit execution '{audit_id}' not found.")
    _verify_orchestrator_access(orchestrator, user)

    return StreamingResponse(
        orchestrator.events.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/audits/{audit_id}/status", response_model=AuditStatusResponse)
async def get_audit_status(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> AuditStatusResponse:
    org_id = require_org_context(user)
    orchestrator = ACTIVE_ORCHESTRATORS.get(audit_id)
    if orchestrator:
        _verify_orchestrator_access(orchestrator, user)
        return AuditStatusResponse(
            audit_id=orchestrator.audit_id,
            domain=orchestrator.domain,
            mode=orchestrator.config.mode.value,
            status=orchestrator.state.status.value,
            current_stage=orchestrator.state.current_stage,
            completed_tasks=len(orchestrator.state.completed_tasks),
            failed_tasks=len(orchestrator.state.failed_tasks),
            total_tasks=len(orchestrator.dag.nodes),
            elapsed_time_sec=orchestrator.state.elapsed_time_sec,
        )

    row = _load_run_row(audit_id, org_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Audit execution '{audit_id}' not found.")
    return AuditStatusResponse(
        audit_id=row["id"],
        domain=row["domain"],
        mode=row["mode"],
        status=row["status"],
        current_stage=row["current_stage"],
        completed_tasks=int(row["completed_tasks"] or 0),
        failed_tasks=int(row["failed_tasks"] or 0),
        total_tasks=int(row["total_tasks"] or 0),
        elapsed_time_sec=float(row["elapsed_time_sec"] or 0.0),
    )


@router.post("/audits/{audit_id}/cancel")
async def cancel_audit(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    require_org_context(user)
    orchestrator = ACTIVE_ORCHESTRATORS.get(audit_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Audit execution '{audit_id}' not found.")
    _verify_orchestrator_access(orchestrator, user)
    orchestrator.cancel()
    return {"audit_id": audit_id, "status": "CANCELLED"}


@router.post("/audits/{audit_id}/resume")
async def resume_audit(
    audit_id: str,
    background_tasks: BackgroundTasks,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    org_id = require_org_context(user)
    orchestrator = ACTIVE_ORCHESTRATORS.get(audit_id)
    if orchestrator:
        _verify_orchestrator_access(orchestrator, user)
    else:
        row = _load_run_row(audit_id, org_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Audit execution '{audit_id}' not found.")
        cfg = AuditConfiguration(
            target_url=f"https://{row['domain']}/",
            mode=AuditMode(row["mode"]),
            org_id=row["org_id"] or org_id,
            workspace_id=row["workspace_id"],
        )
        orchestrator = SEOAuditOrchestrator(audit_id=audit_id, domain=row["domain"], config=cfg)
        ACTIVE_ORCHESTRATORS[audit_id] = orchestrator

    async def _resume_in_background():
        try:
            await orchestrator.resume()
        except Exception:
            pass

    background_tasks.add_task(_resume_in_background)
    return {"audit_id": audit_id, "status": "RESUMING"}


@router.get("/audits/{audit_id}/link-graph")
@router.get("/reports/{audit_id}/internal-link-graph")
async def get_internal_link_graph(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Computes and returns the directed internal link graph strictly from real crawled pages
    (never falls back to fabricated demo URLs).
    """
    org_id = require_org_context(user)
    domain = ""
    pages = []

    orchestrator = ACTIVE_ORCHESTRATORS.get(audit_id)
    if orchestrator:
        _verify_orchestrator_access(orchestrator, user)
        if orchestrator.link_graph:
            return orchestrator.link_graph
        domain = orchestrator.domain
        pages = list(orchestrator.state.crawled_pages or [])
    else:
        row = _load_run_row(audit_id, org_id)
        if row:
            domain = row["domain"]
            if row.get("canonical_assessment_json"):
                parsed = json.loads(row["canonical_assessment_json"])
                if parsed.get("internal_link_graph"):
                    return parsed["internal_link_graph"]
            db_path = default_seo_db_path()
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                p_rows = conn.execute(
                    "SELECT page_payload_json FROM seo_crawl_pages WHERE audit_id = ?", (audit_id,)
                ).fetchall()
                pages = [json.loads(r["page_payload_json"]) for r in p_rows if r["page_payload_json"]]
            finally:
                conn.close()
        else:
            # Resolve from canonical AuditRepository for existing analyses
            run = require_analysis(audit_id, user)
            report = getattr(run, "report", None)
            domain = getattr(report, "domain", None) or getattr(run, "website_url", "")
            manifest = getattr(report, "crawl_manifest", None)
            raw_pages = (getattr(manifest, "pages", None) if manifest else None) or getattr(report, "page_reports", None) or []
            pages = [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in raw_pages]

    if not pages:
        return {
            "domain": domain,
            "homepage_url": f"https://{domain}/" if domain else "",
            "nodes": [],
            "edges": [],
            "clusters": [],
            "suggested_links": [],
            "broken_links": [],
            "summary": {
                "total_pages": 0,
                "total_internal_links": 0,
                "orphan_count": 0,
                "deep_count": 0,
                "weak_count": 0,
                "broken_count": 0,
                "max_click_depth": 0,
                "avg_inlinks_per_page": 0.0,
            },
        }

    return build_internal_link_graph(pages, domain=domain)
