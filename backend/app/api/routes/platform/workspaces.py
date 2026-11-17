"""
Enterprise Multi-Tenant Workspace & Domain Hierarchy API Routes.
Implements:
- Workspaces listing and creation (persisted to SQLite)
- Monitored domains management (persisted to SQLite)
- Audit run historical timeline
- Incremental regression diffing with fallback to stored analyses runs
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit.regression_engine import get_regression_engine
from app.db.enterprise_schema import init_enterprise_schema
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user, require_permission
from app.orchestration.orchestrator import orchestrator
import app.api.routes.findings  # noqa: F401 - ensures findings & compare routes register on analyses.router
from app.api.routes.findings import _report_to_regression_dict

router = APIRouter(prefix="/workspaces", tags=["Enterprise Workspaces"])

_WORKSPACES_DB_PATH: str = "data/dristik_enterprise.db"


def set_workspaces_db_path(db_path: str) -> None:
    global _WORKSPACES_DB_PATH
    _WORKSPACES_DB_PATH = db_path
    init_enterprise_schema(_WORKSPACES_DB_PATH)


def _get_ws_conn() -> sqlite3.Connection:
    init_enterprise_schema(_WORKSPACES_DB_PATH)
    conn = sqlite3.connect(_WORKSPACES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class WorkspaceCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None


class DomainCreateRequest(BaseModel):
    hostname: str
    site_type: str = "b2b_saas"
    crawl_frequency: str = "weekly"
    max_pages: int = 500


# In-memory storage with SQLite persistence
_WORKSPACES_STORE: Dict[str, Dict[str, Any]] = {}
_DOMAINS_STORE: Dict[str, Dict[str, Any]] = {}
_DOMAIN_RUNS_STORE: Dict[str, List[Dict[str, Any]]] = {}


def _persist_workspace(ws: Dict[str, Any]) -> None:
    try:
        conn = _get_ws_conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workspaces (id, org_id, name, slug, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ws["id"], ws["org_id"], ws["name"], ws["slug"], ws["created_at"]),
            )
        conn.close()
    except Exception:
        pass


def _load_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    if workspace_id in _WORKSPACES_STORE:
        return _WORKSPACES_STORE[workspace_id]
    try:
        conn = _get_ws_conn()
        row = conn.execute(
            "SELECT id, org_id, name, slug, created_at FROM workspaces WHERE id = ?",
            (workspace_id,),
        ).fetchone()
        conn.close()
        if row:
            ws = dict(row)
            _WORKSPACES_STORE[workspace_id] = ws
            return ws
    except Exception:
        pass
    return None


def _load_org_workspaces(org_id: str) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    try:
        conn = _get_ws_conn()
        rows = conn.execute(
            "SELECT id, org_id, name, slug, created_at FROM workspaces WHERE org_id = ? ORDER BY created_at ASC",
            (org_id,),
        ).fetchall()
        conn.close()
        for r in rows:
            ws = dict(r)
            merged[ws["id"]] = ws
            _WORKSPACES_STORE[ws["id"]] = ws
    except Exception:
        pass
    for ws_id, ws in _WORKSPACES_STORE.items():
        if ws.get("org_id") == org_id:
            merged[ws_id] = ws
    return list(merged.values())


def _persist_domain(domain: Dict[str, Any]) -> None:
    try:
        conn = _get_ws_conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO domains (
                    id, workspace_id, hostname, default_scheme, site_type,
                    crawl_frequency, max_pages, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    domain["id"],
                    domain["workspace_id"],
                    domain["hostname"],
                    domain.get("default_scheme", "https"),
                    domain.get("site_type", "b2b_saas"),
                    domain.get("crawl_frequency", "weekly"),
                    int(domain.get("max_pages", 500)),
                    1 if domain.get("is_active", True) else 0,
                    domain["created_at"],
                ),
            )
        conn.close()
    except Exception:
        pass


def _load_domain(domain_id: str) -> Optional[Dict[str, Any]]:
    if domain_id in _DOMAINS_STORE:
        return _DOMAINS_STORE[domain_id]
    try:
        conn = _get_ws_conn()
        row = conn.execute(
            """
            SELECT id, workspace_id, hostname, default_scheme, site_type,
                   crawl_frequency, max_pages, is_active, created_at
            FROM domains WHERE id = ?
            """,
            (domain_id,),
        ).fetchone()
        conn.close()
        if row:
            dom = dict(row)
            dom["is_active"] = bool(dom.get("is_active", 1))
            _DOMAINS_STORE[domain_id] = dom
            return dom
    except Exception:
        pass
    return None


def _load_workspace_domains(workspace_id: str) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    try:
        conn = _get_ws_conn()
        rows = conn.execute(
            """
            SELECT id, workspace_id, hostname, default_scheme, site_type,
                   crawl_frequency, max_pages, is_active, created_at
            FROM domains WHERE workspace_id = ? ORDER BY created_at ASC
            """,
            (workspace_id,),
        ).fetchall()
        conn.close()
        for r in rows:
            dom = dict(r)
            dom["is_active"] = bool(dom.get("is_active", 1))
            merged[dom["id"]] = dom
            _DOMAINS_STORE[dom["id"]] = dom
    except Exception:
        pass
    for dom_id, dom in _DOMAINS_STORE.items():
        if dom.get("workspace_id") == workspace_id:
            merged[dom_id] = dom
    return list(merged.values())


def persist_domain_run(domain_id: str, run_payload: Dict[str, Any]) -> None:
    run_id = str(run_payload.get("audit_id") or run_payload.get("id") or f"run_{uuid.uuid4().hex[:8]}")
    run_payload["audit_id"] = run_id
    existing = _DOMAIN_RUNS_STORE.setdefault(domain_id, [])
    if not any(r.get("audit_id") == run_id for r in existing):
        existing.append(run_payload)
    try:
        conn = _get_ws_conn()
        now = run_payload.get("created_at") or datetime.now(timezone.utc).isoformat()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_runs (
                    id, domain_id, triggered_by, status, stage, pages_crawled,
                    overall_score, confidence_score, evidence_coverage, error_message,
                    started_at, completed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    domain_id,
                    run_payload.get("triggered_by"),
                    run_payload.get("status", "completed"),
                    run_payload.get("stage", "completed"),
                    len(run_payload.get("pages") or []),
                    int(run_payload.get("overall_score") or 0),
                    run_payload.get("confidence_score"),
                    run_payload.get("evidence_coverage"),
                    json.dumps(run_payload),
                    run_payload.get("started_at", now),
                    run_payload.get("completed_at", now),
                    now,
                ),
            )
        conn.close()
    except Exception:
        pass


def _load_domain_runs(domain_id: str, hostname: str, org_id: str) -> List[Dict[str, Any]]:
    merged_by_id: Dict[str, Dict[str, Any]] = {}

    # 1. Load from SQLite audit_runs table
    try:
        conn = _get_ws_conn()
        rows = conn.execute(
            """
            SELECT id, domain_id, status, pages_crawled, overall_score, error_message, created_at
            FROM audit_runs WHERE domain_id = ? ORDER BY created_at ASC
            """,
            (domain_id,),
        ).fetchall()
        conn.close()
        for r in rows:
            raw_json = r["error_message"]
            parsed: Optional[Dict[str, Any]] = None
            if isinstance(raw_json, str) and raw_json.strip().startswith("{"):
                try:
                    parsed = json.loads(raw_json)
                except Exception:
                    parsed = None
            if parsed and isinstance(parsed, dict):
                parsed.setdefault("audit_id", r["id"])
                merged_by_id[r["id"]] = parsed
            else:
                merged_by_id[r["id"]] = {
                    "audit_id": r["id"],
                    "domain_id": r["domain_id"],
                    "status": r["status"],
                    "overall_score": r["overall_score"] or 0,
                    "category_scores": {},
                    "pages": [],
                    "schema_types": [],
                    "created_at": r["created_at"],
                }
    except Exception:
        pass

    # 2. Merge with in-memory _DOMAIN_RUNS_STORE
    for idx, mem_run in enumerate(_DOMAIN_RUNS_STORE.get(domain_id, [])):
        rid = str(mem_run.get("audit_id") or mem_run.get("id") or f"mem_{idx}")
        mem_run["audit_id"] = rid
        if rid in merged_by_id:
            # Persist any in-memory additions not yet in SQLite
            pass
        else:
            persist_domain_run(domain_id, mem_run)
        merged_by_id[rid] = mem_run

    runs_list = list(merged_by_id.values())
    if len(runs_list) >= 2:
        _DOMAIN_RUNS_STORE[domain_id] = runs_list
        return runs_list

    # 3. Fallback: query stored analyses runs for this org & domain
    clean_target = (hostname or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    if clean_target:
        candidate_runs: List[Any] = []
        seen_aids = set()

        for aid, arun in list(orchestrator.runs.items()):
            if getattr(arun, "org_id", None) == org_id:
                r_host = (
                    getattr(arun, "domain", None)
                    or urlparse(str(getattr(arun, "website_url", ""))).netloc
                ).lower().replace("www.", "")
                if r_host == clean_target and getattr(arun, "report", None) is not None:
                    candidate_runs.append(arun)
                    seen_aids.add(aid)

        try:
            db_summaries = orchestrator.repository.list_runs(org_id=org_id, limit=100)
            for row in (db_summaries or []):
                aid = row.get("analysis_id")
                if not aid or aid in seen_aids:
                    continue
                r_host = str(row.get("domain") or urlparse(str(row.get("website_url", ""))).netloc).lower().replace("www.", "")
                if r_host == clean_target:
                    full_run = orchestrator.repository.get_run(aid, org_id=org_id)
                    if full_run and getattr(full_run, "report", None) is not None:
                        candidate_runs.append(full_run)
                        seen_aids.add(aid)
        except Exception:
            pass

        candidate_runs.sort(key=lambda r: str(getattr(r, "started_at", "") or getattr(r, "created_at", "") or ""))
        for arun in candidate_runs:
            aid = arun.analysis_id
            if aid not in merged_by_id and arun.report:
                reg_dict = _report_to_regression_dict(arun.report, aid)
                reg_dict["created_at"] = str(getattr(arun, "started_at", "") or "")
                merged_by_id[aid] = reg_dict

    runs_list = list(merged_by_id.values())
    if runs_list:
        _DOMAIN_RUNS_STORE[domain_id] = runs_list
    return runs_list


def _owned_workspace(workspace_id: str, user: UserIdentity) -> dict:
    workspace = _load_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    if workspace.get("org_id") != user.org_id and not Authorizer.is_system(user):
        raise HTTPException(status_code=403, detail="Cross-tenant workspace access forbidden")
    return workspace


def _owned_domain(workspace_id: str, domain_id: str, user: UserIdentity) -> dict:
    _owned_workspace(workspace_id, user)
    domain = _load_domain(domain_id)
    if not domain or domain.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Domain not found.")
    return domain


@router.get("")
async def list_workspaces(user: UserIdentity = Depends(get_current_user)):
    org_id = user.org_id
    org_workspaces = _load_org_workspaces(org_id)
    if not org_workspaces:
        default_id = f"ws_default_{org_id}"
        default_ws = {
            "id": default_id,
            "org_id": org_id,
            "name": "Default Workspace",
            "slug": "default",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _WORKSPACES_STORE[default_id] = default_ws
        _persist_workspace(default_ws)
        org_workspaces = [default_ws]
    return {"workspaces": org_workspaces}


@router.post("")
async def create_workspace(
    req: WorkspaceCreateRequest,
    user: UserIdentity = Depends(require_permission("org:manage"))
):
    org_id = user.org_id
    ws_id = f"ws_{uuid.uuid4().hex[:8]}"
    slug = req.slug or req.name.lower().replace(" ", "-")
    ws = {
        "id": ws_id,
        "org_id": org_id,
        "name": req.name,
        "slug": slug,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _WORKSPACES_STORE[ws_id] = ws
    _persist_workspace(ws)
    return ws


@router.get("/{workspace_id}/domains")
async def list_domains(
    workspace_id: str,
    user: UserIdentity = Depends(get_current_user)
):
    _owned_workspace(workspace_id, user)
    domains = _load_workspace_domains(workspace_id)
    return {"workspace_id": workspace_id, "domains": domains}


@router.post("/{workspace_id}/domains")
async def add_domain(
    workspace_id: str,
    req: DomainCreateRequest,
    user: UserIdentity = Depends(require_permission("org:manage"))
):
    _owned_workspace(workspace_id, user)
    
    clean_host = req.hostname.replace("https://", "").replace("http://", "").split("/")[0]
    dom_id = f"dom_{uuid.uuid4().hex[:8]}"
    domain = {
        "id": dom_id,
        "workspace_id": workspace_id,
        "hostname": clean_host,
        "default_scheme": "https",
        "site_type": req.site_type,
        "crawl_frequency": req.crawl_frequency,
        "max_pages": req.max_pages,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _DOMAINS_STORE[dom_id] = domain
    _persist_domain(domain)
    return domain


@router.get("/{workspace_id}/domains/{domain_id}/history")
async def get_domain_history(
    workspace_id: str,
    domain_id: str,
    user: UserIdentity = Depends(get_current_user)
):
    ws = _owned_workspace(workspace_id, user)
    domain = _owned_domain(workspace_id, domain_id, user)
    runs = _load_domain_runs(domain_id, domain.get("hostname", ""), ws.get("org_id", user.org_id))
    return {"domain_id": domain_id, "total_runs": len(runs), "runs": runs}


@router.get("/{workspace_id}/domains/{domain_id}/diff")
async def get_domain_regression_diff(
    workspace_id: str,
    domain_id: str,
    audit_id: Optional[str] = None,
    baseline_id: Optional[str] = None,
    user: UserIdentity = Depends(get_current_user)
):
    ws = _owned_workspace(workspace_id, user)
    domain = _owned_domain(workspace_id, domain_id, user)
    
    runs = _load_domain_runs(domain_id, domain.get("hostname", ""), ws.get("org_id", user.org_id))
    if len(runs) < 2 and not (audit_id and baseline_id):
        return {
            "status": "INSUFFICIENT_HISTORY",
            "message": "At least 2 audit runs are required to compute regression diff.",
            "diff": None
        }

    curr = runs[-1] if not audit_id else next((r for r in runs if r.get("audit_id") == audit_id), runs[-1])
    base = runs[-2] if not baseline_id else next((r for r in runs if r.get("audit_id") == baseline_id), runs[-2])

    reg_engine = get_regression_engine()
    diff = reg_engine.compare_audits(curr, base)
    return {
        "status": "COMPUTED",
        "current_audit_id": curr.get("audit_id"),
        "baseline_audit_id": base.get("audit_id"),
        "diff": {
            "overall_score_delta": diff.overall_score_delta,
            "category_deltas": diff.category_deltas,
            "pages_added": diff.pages_added,
            "pages_removed": diff.pages_removed,
            "schema_types_dropped": diff.schema_types_dropped,
            "schema_types_added": diff.schema_types_added,
            "alerts": [
                {
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "url": a.url,
                    "message": a.message,
                }
                for a in diff.alerts
            ]
        }
    }
