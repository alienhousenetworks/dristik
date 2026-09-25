"""
Enterprise Multi-Tenant Workspace & Domain Hierarchy API Routes.
Implements:
- Workspaces listing and creation
- Monitored domains management
- Audit run historical timeline
- Incremental regression diffing
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit.regression_engine import get_regression_engine
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional, require_permission

router = APIRouter(prefix="/workspaces", tags=["Enterprise Workspaces"])


class WorkspaceCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None


class DomainCreateRequest(BaseModel):
    hostname: str
    site_type: str = "b2b_saas"
    crawl_frequency: str = "weekly"
    max_pages: int = 500


# In-memory storage with persistence fallback for dev/testing
_WORKSPACES_STORE = {}
_DOMAINS_STORE = {}
_DOMAIN_RUNS_STORE = {}


@router.get("")
async def list_workspaces(user: Optional[UserIdentity] = Depends(get_current_user_optional)):
    org_id = user.org_id if user else "org_default"
    org_workspaces = [w for w in _WORKSPACES_STORE.values() if w.get("org_id") == org_id]
    if not org_workspaces:
        # Default workspace if none exist yet
        default_ws = {
            "id": "ws_default",
            "org_id": org_id,
            "name": "Default Workspace",
            "slug": "default",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _WORKSPACES_STORE["ws_default"] = default_ws
        org_workspaces = [default_ws]
    return {"workspaces": org_workspaces}


@router.post("")
async def create_workspace(
    req: WorkspaceCreateRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    org_id = user.org_id if user else "org_default"
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
    return ws


@router.get("/{workspace_id}/domains")
async def list_domains(
    workspace_id: str,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    if workspace_id not in _WORKSPACES_STORE and workspace_id != "ws_default":
        raise HTTPException(status_code=404, detail="Workspace not found.")
    domains = [d for d in _DOMAINS_STORE.values() if d.get("workspace_id") == workspace_id]
    return {"workspace_id": workspace_id, "domains": domains}


@router.post("/{workspace_id}/domains")
async def add_domain(
    workspace_id: str,
    req: DomainCreateRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    if workspace_id not in _WORKSPACES_STORE and workspace_id != "ws_default":
        raise HTTPException(status_code=404, detail="Workspace not found.")
    
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
    return domain


@router.get("/{workspace_id}/domains/{domain_id}/history")
async def get_domain_history(
    workspace_id: str,
    domain_id: str,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    if domain_id not in _DOMAINS_STORE:
        raise HTTPException(status_code=404, detail="Domain not found.")
    runs = _DOMAIN_RUNS_STORE.get(domain_id, [])
    return {"domain_id": domain_id, "total_runs": len(runs), "runs": runs}


@router.get("/{workspace_id}/domains/{domain_id}/diff")
async def get_domain_regression_diff(
    workspace_id: str,
    domain_id: str,
    audit_id: Optional[str] = None,
    baseline_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    if domain_id not in _DOMAINS_STORE:
        raise HTTPException(status_code=404, detail="Domain not found.")
    
    runs = _DOMAIN_RUNS_STORE.get(domain_id, [])
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
