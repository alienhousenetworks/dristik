"""External Authority integrations.

Customer tokens stay in the encrypted store. Responses never include them.
A missing provider is NOT_CONNECTED, not an audit failure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.connectors.authority.crypto import EncryptionKeyMissing
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user_optional

router = APIRouter(prefix="/external-authority", tags=["External Authority"])


class OAuthStartRequest(BaseModel):
    provider: str
    domain: Optional[str] = None
    project_id: Optional[str] = None


class ApiKeyConnectRequest(BaseModel):
    provider: str
    domain: Optional[str] = None
    project_id: Optional[str] = None
    api_key: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None


class ProviderRequest(BaseModel):
    provider: str
    project_id: Optional[str] = None


class PropertySelectRequest(BaseModel):
    provider: str
    property_id: str
    label: Optional[str] = None
    project_id: Optional[str] = None


class BrandRequest(BaseModel):
    name: str = ""
    aliases: List[str] = Field(default_factory=list)
    project_id: Optional[str] = None


class CompetitorItem(BaseModel):
    name: Optional[str] = None
    domain: str


class CompetitorsRequest(BaseModel):
    competitors: List[CompetitorItem] = Field(default_factory=list)
    project_id: Optional[str] = None


class LocalBusinessRequest(BaseModel):
    applicability: str = "UNKNOWN"
    name: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    category: str = ""
    expected_directories: List[str] = Field(default_factory=list)
    project_id: Optional[str] = None


class SyncRequest(BaseModel):
    domain: str
    project_id: Optional[str] = None
    job_types: Optional[List[str]] = None
    periods: Optional[List[int]] = None
    run: bool = True
    force: bool = False


def _service():
    from app.connectors.authority.service import get_service
    return get_service()


def _project(user: Optional[UserIdentity], requested: Optional[str]) -> str:
    """Stored connector data belongs to the signed-in organization.

    A caller-supplied project id cannot select another organization's records.
    """
    if user is None or not user.org_id:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    if requested and requested != user.org_id:
        if not Authorizer.can_access_org(user, requested):
            raise HTTPException(status_code=404, detail="Project not found.")
        return requested
    return user.org_id


def _guard(exc: Exception) -> None:
    if isinstance(exc, EncryptionKeyMissing):
        raise HTTPException(status_code=503, detail="Credential storage is not configured.") from exc
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail="Unknown provider.") from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("/providers")
def list_providers() -> Dict[str, Any]:
    return {"providers": _service().providers()}


@router.get("/coverage")
def coverage(
    domain: str = Query(""),
    period_days: int = Query(28),
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().coverage(_project(user, project_id), domain, period_days)


@router.get("/health")
def health(
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    project = _project(user, project_id)
    return {"project_id": project, "connectors": _service().health(project)}


@router.post("/oauth/start")
def oauth_start(
    body: OAuthStartRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, str]:
    try:
        return _service().start_oauth(_project(user, body.project_id), body.provider, body.domain)
    except Exception as exc:
        _guard(exc)
        raise


@router.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """Google's client allows only this callback.

    Sign-in and connector consent land here too. Their state is a signed
    payload. External-authority consent uses an opaque stored state.
    """
    from app.connectors.oauth_providers import PROVIDERS, peek_signed_state

    payload = peek_signed_state(state)
    provider = str((payload or {}).get("provider") or "")
    if payload and provider in {"google", "github"} and "nonce" in payload:
        from fastapi import Response
        from app.api.routes.identity.auth import oauth_sso_callback
        return await oauth_sso_callback(
            provider,
            Response(),
            code or None,
            state or None,
            error or None,
        )
    if payload and provider in PROVIDERS:
        from app.connectors.oauth_providers import oauth_callback as connector_oauth_callback
        return await connector_oauth_callback(
            request,
            code or None,
            state or None,
            error or None,
            None,
        )

    frontend = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    try:
        result = _service().finish_oauth(code, state)
    except Exception as exc:
        if isinstance(exc, EncryptionKeyMissing):
            detail = "storage"
        elif isinstance(exc, ValueError):
            detail = "state"
        else:
            detail = type(exc).__name__
        return RedirectResponse(f"{frontend}/?external=error&reason={detail}")
    return RedirectResponse(f"{frontend}/?external=connected&provider={result['provider']}")


@router.post("/connect")
def connect_api_key(
    body: ApiKeyConnectRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    secret = {key: value for key, value in {
        "api_key": body.api_key,
        "login": body.login,
        "password": body.password,
    }.items() if value}
    try:
        return _service().connect_api_key(_project(user, body.project_id), body.provider, secret, body.domain)
    except Exception as exc:
        _guard(exc)
        raise


@router.post("/disconnect")
def disconnect(
    body: ProviderRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, str]:
    try:
        return _service().disconnect(_project(user, body.project_id), body.provider)
    except Exception as exc:
        _guard(exc)
        raise


@router.get("/properties")
def properties(
    provider: str,
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    project = _project(user, project_id)
    rows = _service().store.list_properties(project, provider)
    public = []
    for row in rows:
        public.append({
            "property_id": row.get("external_property_id"),
            "label": row.get("label"),
            "domain": row.get("domain"),
            "provider": row.get("provider"),
        })
    return {"properties": public}


@router.post("/properties/select")
def select_property(
    body: PropertySelectRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, str]:
    return _service().select_property(_project(user, body.project_id), body.provider, body.property_id, body.label)


@router.put("/brand")
def save_brand(
    body: BrandRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().save_brand(_project(user, body.project_id), body.name, body.aliases)


@router.get("/brand")
def get_brand(
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().store.get_profile(_project(user, project_id), "brand")


@router.put("/competitors")
def save_competitors(
    body: CompetitorsRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().save_competitors(
        _project(user, body.project_id),
        [item.model_dump() for item in body.competitors],
    )


@router.get("/competitors")
def get_competitors(
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().store.get_profile(_project(user, project_id), "competitors")


@router.put("/local-business")
def save_local(
    body: LocalBusinessRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    try:
        return _service().save_local_business(_project(user, body.project_id), body.model_dump())
    except Exception as exc:
        _guard(exc)
        raise


@router.get("/local-business")
def get_local(
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().store.get_profile(_project(user, project_id), "local_business")


@router.post("/sync")
def sync(
    body: SyncRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    project = _project(user, body.project_id)
    try:
        jobs = _service().enqueue(project, body.domain, body.job_types, body.periods, force=body.force, automatic=False)
    except Exception as exc:
        _guard(exc)
        raise
    outcomes = _service().run_due_jobs() if body.run else []
    return {"jobs": jobs, "results": outcomes}


@router.get("/jobs")
def jobs(
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return {"jobs": _service().store.list_jobs(_project(user, project_id))}


@router.get("/jobs/{job_id}")
def job(
    job_id: str,
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    found = _service().store.get_job(job_id)
    if not found or found.get("project_id") != _project(user, project_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return found


@router.get("/report")
def report(
    domain: str = Query(...),
    period_days: int = Query(28),
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    return _service().report(_project(user, project_id), domain, period_days)


@router.get("/findings")
def findings(
    domain: str = Query(...),
    period_days: int = Query(28),
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    payload = _service().report(_project(user, project_id), domain, period_days)
    return {
        "universal_authority_score": None,
        "findings": payload.get("findings") or [],
        "coverage": payload.get("coverage") or [],
    }


@router.get("/snapshots")
def snapshots(
    domain: str = Query(...),
    provider: Optional[str] = None,
    period_days: int = Query(28),
    project_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    project = _project(user, project_id)
    history = _service().store.snapshot_history(project, domain, period_days)
    if provider:
        history = [row for row in history if row.get("provider") == provider]
    return {"snapshots": history}
