"""
SEO Connectors REST API Router.
Authenticated, workspace-scoped endpoints to list connectors, store encrypted OAuth/API credentials,
check quotas/freshness, and disconnect providers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.connectors.seo_connector_manager import ConnectorStatus, seo_connector_manager
from app.identity.access import require_org_context
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user

router = APIRouter(prefix="/seo/connectors", tags=["SEO Connectors"])


def _resolve_workspace(user: UserIdentity, workspace_id: Optional[str]) -> tuple[str, str]:
    org_id = require_org_context(user)
    ws_id = (workspace_id or f"ws_{org_id}").strip()
    return org_id, ws_id


@router.get("", response_model=List[ConnectorStatus])
async def list_connectors(
    workspace_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> List[ConnectorStatus]:
    org_id, ws_id = _resolve_workspace(user, workspace_id)
    return seo_connector_manager.list_all_connectors(workspace_id=ws_id, org_id=org_id)


@router.get("/{provider_id}", response_model=ConnectorStatus)
async def get_connector(
    provider_id: str,
    workspace_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> ConnectorStatus:
    org_id, ws_id = _resolve_workspace(user, workspace_id)
    if provider_id not in seo_connector_manager.PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return seo_connector_manager.get_connector_status(provider_id, workspace_id=ws_id, org_id=org_id)


@router.post("/{provider_id}/connect", response_model=ConnectorStatus)
async def connect_connector(
    provider_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    workspace_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> ConnectorStatus:
    org_id, ws_id = _resolve_workspace(user, workspace_id)
    try:
        return seo_connector_manager.connect_provider(
            provider_id, payload, workspace_id=ws_id, org_id=org_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{provider_id}/disconnect")
async def disconnect_connector(
    provider_id: str,
    workspace_id: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    org_id, ws_id = _resolve_workspace(user, workspace_id)
    success = seo_connector_manager.disconnect_provider(provider_id, workspace_id=ws_id, org_id=org_id)
    return {"provider_id": provider_id, "workspace_id": ws_id, "disconnected": success}
