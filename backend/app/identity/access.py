"""Organization-scoped access to stored audits."""
from __future__ import annotations
from typing import Optional

from fastapi import HTTPException

from app.identity.authorizer import Authorizer, UserIdentity
from app.orchestration.orchestrator import orchestrator


def require_org_context(
    user: Optional[UserIdentity],
    requested_org_id: Optional[str] = None,
) -> str:
    """Enforces strict tenant context invariants:
    1. If user is None -> 401 Unauthorized.
    2. If user is inactive -> 403 Forbidden.
    3. If user.org_id is empty, None, or 'org_default' -> 403 Forbidden.
    4. If requested_org_id is provided and does not match user.org_id:
       - If not Authorizer.can_access_org(user, requested_org_id) -> 403 Forbidden.
    5. Returns the validated, authoritative org_id.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive.")
    org_id = getattr(user, "org_id", None)
    if not org_id or org_id in ("org_default", "default"):
        raise HTTPException(
            status_code=403,
            detail="TENANT_CONTEXT_REQUIRED: A valid tenant organization context is required.",
        )
    if requested_org_id and requested_org_id != org_id:
        if not Authorizer.can_access_org(user, requested_org_id):
            raise HTTPException(
                status_code=403,
                detail=f"CROSS_TENANT_FORBIDDEN: Access to organization '{requested_org_id}' is forbidden.",
            )
        return requested_org_id
    return org_id


def require_analysis(analysis_id: str, user: UserIdentity, permission: str = "mission:read"):
    """Return the run owned by the caller's organization.

    A missing session is handled by the auth dependency. A run that belongs
    to another organization is reported as not found.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive.")
    if not Authorizer.can_perform(user, permission):
        raise HTTPException(status_code=403, detail="You do not have permission to do that.")
    run = orchestrator.get_run(analysis_id)
    if not run:
        for candidate in orchestrator.runs.values():
            report = getattr(candidate, "report", None)
            if report and (
                getattr(report, "report_id", None) == analysis_id
                or getattr(report, "analysis_id", None) == analysis_id
            ):
                run = candidate
                break
    if not run or not Authorizer.can_access_org(user, getattr(run, "org_id", "") or ""):
        raise HTTPException(status_code=404, detail="Analysis run not found.")
    return run
