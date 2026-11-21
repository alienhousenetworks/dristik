"""
SEO Connectors REST API Router
Endpoints to list connectors, trigger authentication, check quotas, and sync data.
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from app.connectors.seo_connector_manager import seo_connector_manager, ConnectorStatus

router = APIRouter(prefix="/seo/connectors", tags=["SEO Connectors"])


@router.get("", response_model=List[ConnectorStatus])
async def list_connectors() -> List[ConnectorStatus]:
    """
    Lists all available SEO external data connectors, connection states, and quota utilization.
    """
    return seo_connector_manager.list_all_connectors()


@router.get("/{provider_id}", response_model=ConnectorStatus)
async def get_connector(provider_id: str) -> ConnectorStatus:
    """
    Gets detailed connection status, scopes, and quota metrics for a single provider.
    """
    status = seo_connector_manager.get_connector_status(provider_id)
    if status.status == "NOT_CONFIGURED" and provider_id not in seo_connector_manager.PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return status


@router.post("/{provider_id}/connect", response_model=ConnectorStatus)
async def connect_connector(
    provider_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict)
) -> ConnectorStatus:
    """
    Authenticates provider via OAuth credentials or API key and performs live handshake.
    """
    try:
        return seo_connector_manager.connect_provider(provider_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{provider_id}/disconnect")
async def disconnect_connector(provider_id: str) -> Dict[str, Any]:
    """
    Disconnects provider and revokes active credentials.
    """
    success = seo_connector_manager.disconnect_provider(provider_id)
    return {"provider_id": provider_id, "disconnected": success}
