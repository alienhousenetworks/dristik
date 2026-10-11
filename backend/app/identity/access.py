"""Organization-scoped access to stored audits."""
from __future__ import annotations

from fastapi import HTTPException

from app.identity.authorizer import Authorizer, UserIdentity
from app.orchestration.orchestrator import orchestrator


def require_analysis(analysis_id: str, user: UserIdentity, permission: str = "mission:read"):
    """Return the run owned by the caller's organization.

    A missing session is handled by the auth dependency. A run that belongs
    to another organization is reported as not found.
    """
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
