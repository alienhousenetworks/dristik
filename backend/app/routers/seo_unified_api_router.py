"""
Unified Stable SEO REST API & SSE Router (Phase 19).
Authoritative, authenticated, tenant-isolated, DB-backed API surface across:
audits, progress, SSE events, 6-tier URL inventory (13 filters), canonical findings,
9-dimension scorecards, 14-field evidence register, 40-specialist agent manifest,
remediation tasks, live re-crawl verification (Fixed != Verified), audit history,
internal link graph, and fail-closed QA-gated PDF/HTML report publications.
Zero hardcoded placeholder scores, findings, or URLs.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.connectors.seo_connector_manager import seo_connector_manager
from app.db.seo_orchestrator_schema import default_seo_db_path, init_seo_orchestrator_schema
from app.identity.access import require_analysis, require_org_context
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user
from app.orchestration.orchestrator import orchestrator as main_orchestrator
from app.routers.seo_orchestrator_router import ACTIVE_ORCHESTRATORS
from app.seo.audit.internal_links.link_graph_engine import build_internal_link_graph
from app.seo.audit.orchestration.execution_state import AuditConfig, AuditMode
from app.seo.audit.orchestrator import SEOAuditOrchestrator
from app.seo.audit.qa.seo_qa_validator import SeoQaValidator
from app.seo.audit.remediation.post_audit_remediation_engine import PostAuditRemediationEngine
from app.seo.audit.scoring.mathematical_score_engine import MathematicalScoreEngine
from app.seo.enterprise.assess import build_enterprise_seo
from app.seo.reporting.enterprise_pdf_engine import enterprise_pdf_engine

router = APIRouter(prefix="/seo", tags=["SEO Unified API"])

ALLOWED_FINDING_STATES = {
    "DETECTED", "EVIDENCE_VALIDATION", "VERIFIED", "PRIORITIZED",
    "REMEDIATION_PLANNED", "IN_PROGRESS", "FIX_SUBMITTED", "RETESTING",
    "FALSE_POSITIVE", "ACCEPTED_RISK", "DEFERRED", "REOPENED", "BLOCKED", "NOT_REPRODUCIBLE",
}


class StartAuditRequest(BaseModel):
    domain: str = Field(..., description="Target domain, e.g. example.com")
    mode: AuditMode = Field(default=AuditMode.STANDARD)
    workspace_id: Optional[str] = None
    max_pages: Optional[int] = None
    custom_seed_urls: Optional[List[str]] = None
    live_crawl: bool = False


class FindingUpdateRequest(BaseModel):
    status: Optional[str] = None
    assigned_owner: Optional[str] = None
    note: Optional[str] = None


class CreateTaskRequest(BaseModel):
    audit_id: Optional[str] = None
    assignee: str = "Engineering Lead"
    department: str = "Engineering"
    priority: str = "P1"
    due_date: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    approval_status: Optional[str] = None
    assigned_owner: Optional[str] = None
    due_date: Optional[str] = None


class VerifyTaskRequest(BaseModel):
    target_url: Optional[str] = None
    rule_id: Optional[str] = None


class GenerateReportRequest(BaseModel):
    profile: str = "complete_book"
    selected_chapters: Optional[List[int]] = None
    tone: str = "executive"
    allow_draft_on_qa_block: bool = False


def _db_conn() -> sqlite3.Connection:
    db_path = default_seo_db_path()
    init_seo_orchestrator_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_audit_bundle(audit_id: str, user: UserIdentity) -> Dict[str, Any]:
    """
    Single-source-of-truth resolver for an SEO audit across:
    1. Live ACTIVE_ORCHESTRATORS (tenant-checked)
    2. Persisted seo_audit_runs / seo_* relational tables (tenant-checked)
    3. Main Dristik AuditRepository via require_analysis() (hydrated deterministically)
    """
    org_id = require_org_context(user)
    ws_default = f"ws_{org_id}"

    # 1. Active in-memory orchestrator
    orch = ACTIVE_ORCHESTRATORS.get(audit_id)
    if orch is not None:
        if orch.config.org_id and not Authorizer.can_access_org(user, orch.config.org_id):
            raise HTTPException(status_code=404, detail=f"Audit '{audit_id}' not found.")
        return {
            "source": "active_orchestrator",
            "audit_id": orch.audit_id,
            "domain": orch.domain,
            "org_id": orch.config.org_id or org_id,
            "workspace_id": orch.config.workspace_id,
            "status": orch.state.status.value,
            "current_stage": orch.state.current_stage,
            "completed_tasks": len(orch.state.completed_tasks),
            "failed_tasks": len(orch.state.failed_tasks),
            "total_tasks": len(orch.dag.nodes),
            "elapsed_seconds": orch.state.elapsed_time_sec,
            "pages": list(orch.state.crawled_pages or []),
            "assessment": orch.canonical_assessment or {},
            "findings": list((orch.canonical_assessment or {}).get("canonical_findings") or []),
            "evidence": list((orch.canonical_assessment or {}).get("canonical_evidence") or []),
            "scorecard": orch.scorecard.model_dump() if orch.scorecard else (orch.canonical_assessment or {}).get("mathematical_scorecard"),
            "tasks": [t.model_dump() for t in orch.remediation_tasks],
            "agents": (orch.canonical_assessment or {}).get("agent_executions") or [],
            "qa": orch.qa_report.model_dump() if orch.qa_report else None,
            "link_graph": orch.link_graph,
        }

    # 2. Persisted seo_audit_runs table
    with _db_conn() as conn:
        row = conn.execute("SELECT * FROM seo_audit_runs WHERE id = ?", (audit_id,)).fetchone()
        if row:
            if row["org_id"] and not Authorizer.can_access_org(user, row["org_id"]):
                raise HTTPException(status_code=404, detail=f"Audit '{audit_id}' not found.")
            assessment = json.loads(row["canonical_assessment_json"]) if row["canonical_assessment_json"] else {}
            p_rows = conn.execute("SELECT page_payload_json FROM seo_crawl_pages WHERE audit_id = ?", (audit_id,)).fetchall()
            pages = [json.loads(r["page_payload_json"]) for r in p_rows if r["page_payload_json"]]
            sc_row = conn.execute("SELECT raw_json FROM seo_scorecards WHERE audit_id = ?", (audit_id,)).fetchone()
            scorecard = json.loads(sc_row["raw_json"]) if sc_row and sc_row["raw_json"] else assessment.get("mathematical_scorecard")
            return {
                "source": "seo_db",
                "audit_id": row["id"],
                "domain": row["domain"],
                "org_id": row["org_id"] or org_id,
                "workspace_id": row["workspace_id"],
                "status": row["status"],
                "current_stage": row["current_stage"],
                "completed_tasks": int(row["completed_tasks"] or 0),
                "failed_tasks": int(row["failed_tasks"] or 0),
                "total_tasks": int(row["total_tasks"] or 46),
                "elapsed_seconds": float(row["elapsed_time_sec"] or 0.0),
                "pages": pages,
                "assessment": assessment,
                "findings": assessment.get("canonical_findings") or [],
                "evidence": assessment.get("canonical_evidence") or [],
                "scorecard": scorecard,
                "tasks": assessment.get("remediation_tasks") or [],
                "agents": assessment.get("agent_executions") or [],
                "qa": assessment.get("qa_certification"),
                "link_graph": assessment.get("internal_link_graph"),
            }

    # 3. Main AuditRepository (existing Dristik analyses)
    run = require_analysis(audit_id, user)
    report = getattr(run, "report", None)
    if not report:
        raise HTTPException(status_code=404, detail=f"Audit '{audit_id}' report not ready.")

    rep_dict = report.model_dump() if hasattr(report, "model_dump") else dict(report)
    manifest = rep_dict.get("crawl_manifest") or {}
    pages = list(manifest.get("pages") or rep_dict.get("page_reports") or [])
    domain = str(rep_dict.get("domain") or urlparse(getattr(run, "website_url", "")).netloc or "")
    ws_id = getattr(run, "workspace_id", None) or ws_default

    enterprise_obj = build_enterprise_seo(report)
    assessment = enterprise_obj.model_dump()

    from app.seo.reporting.canonical_seo_pdf_bridge import (
        collect_unified_seo_pdf_bundle,
    )

    unified = collect_unified_seo_pdf_bundle(
        report=report,
        assessment=assessment,
        audit_id=audit_id,
        org_id=getattr(run, "org_id", org_id),
        workspace_id=ws_id,
    )
    findings = unified["findings"]
    evidence = unified["evidence"]
    scorecard = unified["scorecard"]
    tasks = unified["tasks"]
    link_graph = unified["link_graph"]
    connectors = unified["connectors"]
    verification_runs = unified["verification_runs"]
    assessment["findings"] = findings
    assessment["canonical_findings"] = findings
    assessment["evidence"] = evidence
    assessment["canonical_evidence"] = evidence
    assessment["mathematical_scorecard"] = scorecard
    assessment["remediation_tasks"] = tasks
    assessment["verification_runs"] = verification_runs
    assessment["connectors"] = connectors
    assessment["internal_link_graph"] = link_graph

    qa_rep = SeoQaValidator().validate(assessment, {
        **rep_dict,
        "findings": findings,
        "evidence": evidence,
        "mathematical_scorecard": scorecard,
        "methodology_version": (scorecard or {}).get("methodology_version", "dristik_seo_v3.0"),
        "executive_summary_finding_count": len(findings),
    }).model_dump()
    assessment["qa_certification"] = qa_rep

    return {
        "source": "audit_repository",
        "audit_id": audit_id,
        "domain": domain,
        "org_id": getattr(run, "org_id", org_id),
        "workspace_id": ws_id,
        "status": str(getattr(run.status, "value", run.status)),
        "current_stage": getattr(run, "current_step", "COMPLETED"),
        "completed_tasks": len(assessment.get("agents") or []),
        "failed_tasks": 0,
        "total_tasks": len(assessment.get("agents") or []),
        "elapsed_seconds": 0.0,
        "pages": pages,
        "assessment": assessment,
        "findings": findings,
        "evidence": evidence,
        "scorecard": scorecard,
        "tasks": tasks,
        "verification_runs": verification_runs,
        "agents": assessment.get("agents") or [],
        "qa": qa_rep,
        "link_graph": link_graph,
        "raw_report": rep_dict,
        "legacy_sections": unified["legacy_sections"],
    }


@router.post("/audits", status_code=status.HTTP_202_ACCEPTED)
async def start_seo_audit(
    req: StartAuditRequest,
    background_tasks: BackgroundTasks,
    user: UserIdentity = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    """Starts an authenticated, tenant-isolated enterprise SEO audit run."""
    org_id = require_org_context(user)
    if not Authorizer.can_perform(user, "mission:create"):
        raise HTTPException(status_code=403, detail="Permission 'mission:create' required.")

    clean_domain = req.domain.replace("https://", "").replace("http://", "").rstrip("/")
    ws_id = (req.workspace_id or f"ws_{org_id}").strip()

    if idempotency_key:
        with _db_conn() as conn:
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
                    "events_url": f"/api/v1/seo/audits/{existing['id']}/events",
                }

    audit_id = f"seo_{clean_domain.replace('.', '_')}_{uuid.uuid4().hex[:8]}"
    config = AuditConfig(
        target_url=f"https://{clean_domain}/",
        mode=req.mode,
        org_id=org_id,
        workspace_id=ws_id,
        max_pages=req.max_pages,
        custom_seed_urls=req.custom_seed_urls or [],
        live_crawl=req.live_crawl,
        idempotency_key=idempotency_key,
    )

    orch = SEOAuditOrchestrator(audit_id=audit_id, domain=clean_domain, config=config)
    ACTIVE_ORCHESTRATORS[audit_id] = orch
    background_tasks.add_task(orch.run)

    return {
        "audit_id": audit_id,
        "domain": clean_domain,
        "mode": req.mode.value,
        "status": "QUEUED",
        "events_url": f"/api/v1/seo/audits/{audit_id}/events",
    }


@router.get("/audits/{audit_id}/events")
async def stream_unified_audit_events(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """SSE event stream for live SEO audit progression."""
    require_org_context(user)
    orch = ACTIVE_ORCHESTRATORS.get(audit_id)
    if not orch:
        raise HTTPException(status_code=404, detail=f"Live SSE stream for audit '{audit_id}' not found.")
    if orch.config.org_id and not Authorizer.can_access_org(user, orch.config.org_id):
        raise HTTPException(status_code=404, detail=f"Audit '{audit_id}' not found.")
    return StreamingResponse(
        orch.events.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/audits/{audit_id}")
async def get_audit_overview(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    bundle = _resolve_audit_bundle(audit_id, user)
    return {
        "audit_id": bundle["audit_id"],
        "domain": bundle["domain"],
        "status": bundle["status"],
        "current_stage": bundle["current_stage"],
        "completed_tasks": bundle["completed_tasks"],
        "failed_tasks": bundle["failed_tasks"],
        "total_tasks": bundle["total_tasks"],
        "elapsed_seconds": bundle["elapsed_seconds"],
        "coverage": (bundle["assessment"] or {}).get("coverage"),
        "scorecard": bundle["scorecard"],
        "qa_certification": bundle["qa"],
        "findings_count": len(bundle["findings"]),
        "evidence_count": len(bundle["evidence"]),
        "tasks_count": len(bundle["tasks"]),
    }


@router.get("/audits/{audit_id}/progress")
async def get_audit_progress(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    bundle = _resolve_audit_bundle(audit_id, user)
    total = bundle["total_tasks"] or 1
    done = bundle["completed_tasks"]
    return {
        "audit_id": bundle["audit_id"],
        "status": bundle["status"],
        "progress_pct": round((done / total) * 100.0, 1),
        "current_stage": bundle["current_stage"],
        "completed_tasks": done,
        "failed_tasks": bundle["failed_tasks"],
        "total_tasks": total,
    }


@router.get("/audits/{audit_id}/urls")
async def get_audit_urls(
    audit_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = None,
    indexability: Optional[str] = None,
    page_type: Optional[str] = None,
    directory: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query(default="url"),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns real paginated & filtered URL inventory (never fabricates demo URLs)."""
    bundle = _resolve_audit_bundle(audit_id, user)
    pages = list(bundle["pages"])

    if status_filter:
        sf = status_filter.lower()
        pages = [
            p for p in pages
            if (sf == "2xx" and 200 <= int(p.get("status_code") or 0) < 300)
            or (sf == "3xx" and 300 <= int(p.get("status_code") or 0) < 400)
            or (sf == "4xx" and 400 <= int(p.get("status_code") or 0) < 500)
            or (sf == "5xx" and int(p.get("status_code") or 0) >= 500)
            or str(p.get("status_code")) == status_filter
        ]
    if indexability:
        idx_l = indexability.lower()
        pages = [
            p for p in pages
            if (idx_l == "noindex" and "noindex" in str(p.get("robots_meta") or "").lower())
            or (idx_l == "indexable" and "noindex" not in str(p.get("robots_meta") or "").lower() and 200 <= int(p.get("status_code") or 0) < 300)
        ]
    if page_type:
        pages = [p for p in pages if str(p.get("page_type") or "").lower() == page_type.lower()]
    if directory:
        pages = [p for p in pages if urlparse(str(p.get("url") or "")).path.startswith(directory)]
    if search:
        q = search.lower()
        pages = [p for p in pages if q in str(p.get("url") or "").lower() or q in str(p.get("title") or "").lower()]

    if sort_by in ("url", "status_code", "word_count", "ttfb_ms"):
        pages.sort(key=lambda p: (p.get(sort_by) is None, p.get(sort_by) or 0))

    return {
        "audit_id": audit_id,
        "total": len(pages),
        "limit": limit,
        "offset": offset,
        "urls": pages[offset:offset + limit],
    }


@router.get("/audits/{audit_id}/findings")
async def get_audit_findings(
    audit_id: str,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    root_cause_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    bundle = _resolve_audit_bundle(audit_id, user)
    findings = list(bundle["findings"])

    # Overlay persisted status/owner mutations from seo_findings table
    with _db_conn() as conn:
        rows = conn.execute(
            "SELECT id, status, assigned_owner, status_history_json FROM seo_findings WHERE audit_id = ?",
            (audit_id,),
        ).fetchall()
    persisted = {r["id"].split(":")[-1]: dict(r) for r in rows}
    merged = []
    for f in findings:
        item = dict(f)
        fid = str(item.get("finding_id") or item.get("id") or "")
        if fid in persisted:
            item["status"] = persisted[fid]["status"]
            item["resolution_status"] = persisted[fid]["status"]
            item["assigned_owner"] = persisted[fid]["assigned_owner"]
            try:
                item["status_history"] = json.loads(persisted[fid]["status_history_json"] or "[]")
            except Exception:
                item["status_history"] = []
        merged.append(item)

    if severity:
        merged = [f for f in merged if str(f.get("severity") or "").upper() == severity.upper()]
    if category:
        merged = [f for f in merged if str(f.get("category") or "").upper() == category.upper()]
    if status_filter:
        merged = [f for f in merged if str(f.get("status") or f.get("verification_status") or "").upper() == status_filter.upper()]
    if root_cause_id:
        merged = [f for f in merged if str(f.get("root_cause_id") or "") == root_cause_id]

    return {
        "audit_id": audit_id,
        "count": len(merged),
        "limit": limit,
        "offset": offset,
        "findings": merged[offset:offset + limit],
    }


@router.patch("/findings/{finding_id}")
async def update_finding_state(
    finding_id: str,
    req: FindingUpdateRequest,
    audit_id: str = Query(...),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Persists finding lifecycle transitions; strictly blocks setting VERIFIED_FIXED manually."""
    bundle = _resolve_audit_bundle(audit_id, user)
    if req.status:
        st = req.status.upper()
        if st == "VERIFIED_FIXED":
            raise HTTPException(
                status_code=400,
                detail="Fixed is not Verified: VERIFIED_FIXED can only be set by passing POST /api/v1/seo/tasks/{task_id}/verify.",
            )
        if st not in ALLOWED_FINDING_STATES:
            raise HTTPException(status_code=400, detail=f"Invalid lifecycle state '{st}'.")

    pk = f"{audit_id}:{finding_id}"
    now = datetime.now(timezone.utc).isoformat()
    with _db_conn() as conn:
        row = conn.execute("SELECT status, assigned_owner, status_history_json FROM seo_findings WHERE id = ?", (pk,)).fetchone()
        history = []
        if row and row["status_history_json"]:
            try:
                history = json.loads(row["status_history_json"])
            except Exception:
                history = []
        new_status = (req.status or (row["status"] if row else "VERIFIED")).upper()
        new_owner = req.assigned_owner if req.assigned_owner is not None else (row["assigned_owner"] if row else None)
        history.append({"status": new_status, "owner": new_owner, "note": req.note, "by": user.email, "at": now})

        if row:
            conn.execute(
                "UPDATE seo_findings SET status = ?, assigned_owner = ?, status_history_json = ?, updated_at = ? WHERE id = ?",
                (new_status, new_owner, json.dumps(history), now, pk),
            )
        else:
            match = next((f for f in bundle["findings"] if str(f.get("finding_id") or f.get("id")) == finding_id), None)
            if not match:
                raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found in audit '{audit_id}'.")
            conn.execute(
                """
                INSERT INTO seo_findings (
                    id, audit_id, org_id, workspace_id, rule_id, root_cause_id, category,
                    severity, title, description, recommendation, affected_urls_json,
                    affected_urls_count, evidence_ids_json, status, assigned_owner,
                    status_history_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pk, audit_id, bundle["org_id"], bundle["workspace_id"],
                    str(match.get("rule_id") or finding_id), match.get("root_cause_id"),
                    str(match.get("category") or "TECHNICAL_SEO"), str(match.get("severity") or "MEDIUM"),
                    str(match.get("title") or finding_id), match.get("description"), match.get("recommendation"),
                    json.dumps(match.get("affected_urls") or []), len(match.get("affected_urls") or []),
                    json.dumps(match.get("evidence_ids") or match.get("evidence_refs") or []),
                    new_status, new_owner, json.dumps(history), now,
                ),
            )
        conn.commit()
    return {"finding_id": finding_id, "audit_id": audit_id, "status": new_status, "assigned_owner": new_owner, "status_history": history}


@router.get("/audits/{audit_id}/scores")
async def get_audit_scores(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns canonical 100-point 9-dimension mathematical scorecard (never hardcoded)."""
    bundle = _resolve_audit_bundle(audit_id, user)
    sc = bundle["scorecard"]
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scorecard not yet computed for audit '{audit_id}'.")
    return {"audit_id": audit_id, **sc}


@router.get("/audits/{audit_id}/evidence")
async def get_audit_evidence(
    audit_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    bundle = _resolve_audit_bundle(audit_id, user)
    records = list(bundle["evidence"])
    return {"audit_id": audit_id, "count": len(records), "records": records[offset:offset + limit]}


@router.get("/audits/{audit_id}/agents")
async def get_agent_execution_results(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    bundle = _resolve_audit_bundle(audit_id, user)
    agents = list(bundle["agents"])
    completed = sum(1 for a in agents if str(a.get("status", "")).upper() in ("COMPLETED", "SKIPPED"))
    return {
        "audit_id": audit_id,
        "total_agents": len(agents),
        "completed_agents": completed,
        "agents": agents,
    }


@router.get("/audits/{audit_id}/recommendations")
@router.get("/audits/{audit_id}/tasks")
async def get_recommendations_and_tasks(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    bundle = _resolve_audit_bundle(audit_id, user)
    tasks_map: Dict[str, Dict[str, Any]] = {str(t.get("task_id")): dict(t) for t in bundle["tasks"]}

    with _db_conn() as conn:
        rows = conn.execute("SELECT * FROM seo_remediation_tasks WHERE audit_id = ?", (audit_id,)).fetchall()
        for r in rows:
            tid = r["id"].split(":")[-1]
            verif_rows = conn.execute(
                "SELECT * FROM seo_verification_runs WHERE remediation_task_id = ? ORDER BY executed_at DESC LIMIT 1",
                (r["id"],),
            ).fetchall()
            latest_verif = dict(verif_rows[0]) if verif_rows else None
            base = tasks_map.get(tid, {})
            base.update({
                "task_id": tid,
                "finding_id": r["finding_id"] or base.get("finding_id"),
                "problem": r["title"] or base.get("problem"),
                "fix_type": r["fix_type"] or base.get("fix_type"),
                "priority": r["priority"] or base.get("priority", "P1"),
                "status": r["status"],
                "approval_status": r["approval_status"],
                "owner": r["assigned_owner"] or base.get("owner"),
                "department": r["department"] or base.get("department", "Engineering"),
                "effort": r["effort"] or base.get("effort"),
                "due_date": r["due_date"],
                "acceptance_criteria": r["acceptance_criteria"] or base.get("acceptance_criteria"),
                "verification_protocol": r["verification_protocol"] or base.get("verification_protocol"),
                "verification_status": latest_verif["status"] if latest_verif else base.get("verification_status", "UNVERIFIED"),
                "before_evidence": json.loads(r["before_evidence_json"] or "{}"),
                "after_evidence": json.loads(r["after_evidence_json"] or "{}"),
                "latest_verification": latest_verif,
            })
            if r["implementation_json"] and r["implementation_json"] != "{}":
                base["implementation"] = json.loads(r["implementation_json"])
            if r["affected_scope_json"] and r["affected_scope_json"] != "{}":
                base["affected_scope"] = json.loads(r["affected_scope_json"])
            tasks_map[tid] = base

    items = list(tasks_map.values())
    return {"audit_id": audit_id, "count": len(items), "recommendations": items, "tasks": items}


@router.post("/findings/{finding_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_remediation_task(
    finding_id: str,
    req: CreateTaskRequest = Body(default_factory=CreateTaskRequest),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Creates and persists a remediation task linked to a canonical finding."""
    org_id = require_org_context(user)
    audit_id = req.audit_id or ""
    ws_id = f"ws_{org_id}"
    if audit_id:
        bundle = _resolve_audit_bundle(audit_id, user)
        ws_id = bundle["workspace_id"]

    task_id = f"REM_{finding_id}"
    pk = f"{audit_id}:{task_id}" if audit_id else task_id
    now = datetime.now(timezone.utc).isoformat()
    with _db_conn() as conn:
        if audit_id:
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_remediation_tasks (
                    id, recommendation_id, finding_id, audit_id, org_id, workspace_id,
                    title, priority, status, approval_status, assigned_owner,
                    department, due_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'REMEDIATION_PLANNED', 'APPROVED', ?, ?, ?, ?)
                """,
                (
                    pk, task_id, finding_id, audit_id, org_id, ws_id,
                    f"Remediate finding {finding_id}", req.priority, req.assignee,
                    req.department, req.due_date, now,
                ),
            )
            conn.commit()
    return {
        "task_id": task_id,
        "finding_id": finding_id,
        "audit_id": audit_id,
        "status": "REMEDIATION_PLANNED",
        "assigned_to": req.assignee,
        "department": req.department,
        "priority": req.priority,
    }


@router.patch("/tasks/{task_id}")
async def update_remediation_task(
    task_id: str,
    req: TaskUpdateRequest,
    audit_id: str = Query(...),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    _resolve_audit_bundle(audit_id, user)
    if req.status and req.status.upper() == "VERIFIED_FIXED":
        raise HTTPException(
            status_code=400,
            detail="Fixed is not Verified: run POST /api/v1/seo/tasks/{task_id}/verify to verify fixes.",
        )
    pk = f"{audit_id}:{task_id}"
    now = datetime.now(timezone.utc).isoformat()
    with _db_conn() as conn:
        row = conn.execute("SELECT * FROM seo_remediation_tasks WHERE id = ?", (pk,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Remediation task '{task_id}' not found.")
        conn.execute(
            """
            UPDATE seo_remediation_tasks SET
                status = COALESCE(?, status),
                approval_status = COALESCE(?, approval_status),
                assigned_owner = COALESCE(?, assigned_owner),
                due_date = COALESCE(?, due_date),
                updated_at = ?
            WHERE id = ?
            """,
            (req.status, req.approval_status, req.assigned_owner, req.due_date, now, pk),
        )
        conn.commit()
    return {"task_id": task_id, "audit_id": audit_id, "updated_at": now}


@router.post("/tasks/{task_id}/verify")
async def run_task_verification(
    task_id: str,
    req: VerifyTaskRequest = Body(default_factory=VerifyTaskRequest),
    audit_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Executes REAL independent live re-crawl verification (SSRF-checked) against the target URL,
    evaluates deterministic acceptance criteria, records the verification run in seo_verification_runs,
    and transitions to VERIFIED_FIXED ONLY if acceptance criteria pass.
    """
    org_id = require_org_context(user)
    target_url = req.target_url or ""
    rule_id = req.rule_id or ""
    finding_id = task_id.replace("REM_", "", 1)
    before_snap: Dict[str, Any] = {}
    ws_id = f"ws_{org_id}"

    if audit_id:
        bundle = _resolve_audit_bundle(audit_id, user)
        ws_id = bundle["workspace_id"]
        task_match = next((t for t in bundle["tasks"] if t.get("task_id") == task_id), None)
        if task_match:
            finding_id = str(task_match.get("finding_id") or finding_id)
            scope_urls = (task_match.get("affected_scope") or {}).get("sample_urls") or []
            if not target_url and scope_urls:
                target_url = str(scope_urls[0])
            before_snap = dict(task_match.get("before_evidence") or {})
            if not rule_id:
                rule_id = str(before_snap.get("rule_id") or "")
        if not target_url and bundle["pages"]:
            target_url = str(bundle["pages"][0].get("url") or "")
        if target_url:
            page_match = next((p for p in bundle["pages"] if str(p.get("url") or "").rstrip("/") == target_url.rstrip("/")), None)
            if page_match:
                h1s = page_match.get("h1") if isinstance(page_match.get("h1"), list) else ([page_match.get("h1")] if page_match.get("h1") else [])
                before_snap.setdefault("title", page_match.get("title"))
                before_snap.setdefault("canonical_url", page_match.get("canonical_url"))
                before_snap.setdefault("h1_count", len(h1s))
                before_snap.setdefault("schema_count", len(page_match.get("schema_types") or []))
                before_snap.setdefault("ttfb_ms", page_match.get("ttfb_ms"))

    if not target_url:
        raise HTTPException(status_code=400, detail="A target_url (or valid audit_id with affected URLs) is required for live verification.")

    engine = PostAuditRemediationEngine()
    verif = await engine.verify_task_live(
        task_id=task_id,
        finding_id=finding_id,
        target_url=target_url,
        rule_id=rule_id,
        before_snapshot=before_snap,
    )

    if audit_id:
        pk_task = f"{audit_id}:{task_id}"
        pk_find = f"{audit_id}:{finding_id}"
        with _db_conn() as conn:
            conn.execute(
                """
                INSERT INTO seo_verification_runs (
                    id, remediation_task_id, finding_id, audit_id, org_id, workspace_id,
                    target_url, status, passed, verification_check,
                    before_snapshot_json, after_snapshot_json, diff_summary_json, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"ver_{uuid.uuid4().hex[:12]}", pk_task, finding_id, audit_id, org_id, ws_id,
                    target_url, verif.verification_status, 1 if verif.passed else 0,
                    verif.check_summary, json.dumps(verif.before_snapshot, default=str),
                    json.dumps(verif.after_snapshot, default=str),
                    json.dumps(verif.comparison_rows, default=str), verif.verified_at,
                ),
            )
            conn.execute(
                """
                UPDATE seo_remediation_tasks
                SET status = ?, after_evidence_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (verif.verification_status, json.dumps(verif.after_snapshot, default=str), verif.verified_at, pk_task),
            )
            if verif.passed:
                conn.execute(
                    "UPDATE seo_findings SET status = 'VERIFIED_FIXED', updated_at = ? WHERE id = ?",
                    (verif.verified_at, pk_find),
                )
            conn.commit()

    return verif.model_dump()


@router.get("/audits/{audit_id}/history")
async def get_audit_history(
    audit_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns real historical audit timeline & deltas for the same org and domain (zero fabricated deltas)."""
    bundle = _resolve_audit_bundle(audit_id, user)
    org_id = bundle["org_id"]
    domain = bundle["domain"]
    current_score = (bundle["scorecard"] or {}).get("overall_health_score")

    history_rows: List[Dict[str, Any]] = []
    with _db_conn() as conn:
        seo_rows = conn.execute(
            """
            SELECT id, status, overall_score, completed_at, created_at
            FROM seo_audit_runs
            WHERE org_id = ? AND domain = ? AND id != ?
            ORDER BY created_at DESC LIMIT 20
            """,
            (org_id, domain, audit_id),
        ).fetchall()
        for r in seo_rows:
            history_rows.append({
                "audit_id": r["id"],
                "status": r["status"],
                "overall_score": r["overall_score"],
                "completed_at": r["completed_at"] or r["created_at"],
            })

    try:
        repo_runs = main_orchestrator.repository.list_runs(org_id=org_id, limit=20)
        seen = {h["audit_id"] for h in history_rows}
        for r in repo_runs:
            if r["analysis_id"] != audit_id and r["analysis_id"] not in seen and str(r.get("domain") or "").lower() == domain.lower():
                history_rows.append({
                    "audit_id": r["analysis_id"],
                    "status": r["status"],
                    "overall_score": r.get("score_overall"),
                    "completed_at": r.get("completed_at") or r.get("created_at"),
                })
    except Exception:
        pass

    baseline = history_rows[0] if history_rows else None
    score_delta = None
    if baseline and isinstance(current_score, (int, float)) and isinstance(baseline.get("overall_score"), (int, float)):
        score_delta = round(float(current_score) - float(baseline["overall_score"]), 2)

    return {
        "audit_id": audit_id,
        "domain": domain,
        "has_history": len(history_rows) > 0,
        "baseline_audit_id": baseline["audit_id"] if baseline else None,
        "score_delta": score_delta,
        "historical_runs": history_rows,
    }


@router.post("/audits/{audit_id}/reports")
async def generate_publication_report(
    audit_id: str,
    profile: str = Query(default="complete_book"),
    req: Optional[GenerateReportRequest] = Body(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Runs Independent QA fail-closed validation, renders publication HTML from canonical dataset,
    hashes & archives the publication in seo_report_publications.
    """
    bundle = _resolve_audit_bundle(audit_id, user)
    eff_profile = (req.profile if req else profile) or "complete_book"
    tone = req.tone if req else "executive"
    selected = req.selected_chapters if req else None
    allow_draft = req.allow_draft_on_qa_block if req else False

    report_data = {
        **(bundle.get("raw_report") or {}),
        "domain": bundle["domain"],
        "analysis_id": audit_id,
        "crawl_manifest": {"pages": bundle["pages"]},
        "findings": bundle["findings"],
        "evidence": bundle["evidence"],
        "mathematical_scorecard": bundle["scorecard"],
        "remediation_tasks": bundle["tasks"],
        "verification_runs": bundle.get("verification_runs") or [],
        "internal_link_graph": bundle.get("link_graph"),
        "legacy_sections": bundle.get("legacy_sections") or {},
        "methodology_version": (bundle["scorecard"] or {}).get("methodology_version", "dristik_seo_v3.0"),
        "executive_summary_finding_count": len(bundle["findings"]),
    }

    html_content, qa, sha256_hash = enterprise_pdf_engine.publish_with_qa_gate(
        assessment=bundle["assessment"],
        report_data=report_data,
        profile=eff_profile,
        selected_chapters=selected,
        tone=tone,
    )

    pub_id = f"pub_{uuid.uuid4().hex[:12]}"
    pub_status = "PUBLISHED" if qa.status == "CERTIFIED" else ("PARTIAL_PUBLISHED" if qa.status == "PARTIAL_DISCLOSED" else "DRAFT_BLOCKED")
    now = datetime.now(timezone.utc).isoformat()

    with _db_conn() as conn:
        conn.execute(
            """
            INSERT INTO seo_report_publications (
                id, audit_id, org_id, workspace_id, profile, format, status,
                qa_status, qa_report_json, included_chapters_json,
                sha256_integrity_hash, publication_url, html_content, created_by, published_at
            ) VALUES (?, ?, ?, ?, ?, 'HTML', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pub_id, audit_id, bundle["org_id"], bundle["workspace_id"],
                eff_profile, pub_status, qa.status, qa.model_dump_json(),
                json.dumps(selected or []), sha256_hash,
                f"/api/v1/seo/reports/{pub_id}?format=pdf", html_content, user.email, now,
            ),
        )
        conn.commit()

    if not qa.is_certified and not allow_draft:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PUBLICATION_BLOCKED_BY_QA_GATE",
                "publication_id": pub_id,
                "qa_status": qa.status,
                "blocking_reasons": qa.blocking_reasons,
                "draft_preserved": True,
            },
        )

    return {
        "publication_id": pub_id,
        "audit_id": audit_id,
        "profile": eff_profile,
        "status": pub_status,
        "qa_status": qa.status,
        "sha256_integrity_hash": sha256_hash,
        "download_pdf_url": f"/api/v1/seo/reports/{pub_id}?format=pdf",
        "download_html_url": f"/api/v1/seo/reports/{pub_id}?format=html",
    }


@router.get("/reports/{report_id}")
async def get_report_content(
    report_id: str,
    profile: str = Query(default="complete_book"),
    format: str = Query(default="html"),
    download: bool = Query(default=False),
    user: UserIdentity = Depends(get_current_user),
) -> Response:
    """Returns archived or freshly generated canonical HTML or real Chromium-compiled PDF."""
    org_id = require_org_context(user)
    rendered_html: Optional[str] = None
    domain = "seo_report"
    sha_hash = ""
    qa_status = "CERTIFIED"

    with _db_conn() as conn:
        pub = conn.execute("SELECT * FROM seo_report_publications WHERE id = ?", (report_id,)).fetchone()
        if pub:
            if pub["org_id"] and not Authorizer.can_access_org(user, pub["org_id"]):
                raise HTTPException(status_code=404, detail="Publication not found.")
            if pub["status"] == "DRAFT_BLOCKED" and format.lower() == "pdf":
                raise HTTPException(status_code=422, detail="Blocked draft cannot be exported as a certified PDF.")
            rendered_html = pub["html_content"]
            sha_hash = pub["sha256_integrity_hash"] or ""
            qa_status = pub["qa_status"] or "CERTIFIED"
            run_row = conn.execute("SELECT domain FROM seo_audit_runs WHERE id = ?", (pub["audit_id"],)).fetchone()
            if run_row:
                domain = run_row["domain"]

    if rendered_html is None:
        bundle = _resolve_audit_bundle(report_id, user)
        domain = bundle["domain"]
        report_data = {
            **(bundle.get("raw_report") or {}),
            "domain": domain,
            "analysis_id": report_id,
            "crawl_manifest": {"pages": bundle["pages"]},
            "findings": bundle["findings"],
            "evidence": bundle["evidence"],
            "mathematical_scorecard": bundle["scorecard"],
            "remediation_tasks": bundle["tasks"],
            "verification_runs": bundle.get("verification_runs") or [],
            "internal_link_graph": bundle.get("link_graph"),
            "legacy_sections": bundle.get("legacy_sections") or {},
            "methodology_version": (bundle["scorecard"] or {}).get("methodology_version", "dristik_seo_v3.0"),
            "executive_summary_finding_count": len(bundle["findings"]),
        }
        rendered_html, qa, sha_hash = enterprise_pdf_engine.publish_with_qa_gate(
            assessment=bundle["assessment"],
            report_data=report_data,
            profile=profile,
        )
        qa_status = qa.status
        if not qa.is_certified and format.lower() == "pdf":
            raise HTTPException(status_code=422, detail=f"QA Gate blocked PDF publication: {qa.blocking_reasons}")

    if format.lower() == "pdf":
        pdf_bytes = await enterprise_pdf_engine.render_pdf_bytes(rendered_html)
        if not pdf_bytes:
            raise HTTPException(status_code=503, detail="Headless PDF renderer is currently unavailable.")
        disp = "attachment" if download else "inline"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disp}; filename="{domain}_{profile}_seo_audit.pdf"',
                "X-Dristik-Integrity-SHA256": sha_hash,
                "X-Dristik-QA-Status": qa_status,
            },
        )

    return Response(
        content=rendered_html,
        media_type="text/html",
        headers={"X-Dristik-Integrity-SHA256": sha_hash, "X-Dristik-QA-Status": qa_status},
    )
