"""
Agency White-Labeling & Custom Domain Branding Engine.
Supports custom CNAME domain mappings, white-labeled client portals, and customized report styling.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional, require_permission

router = APIRouter(prefix="/tenancy/white-label", tags=["Agency White-Labeling"])

_WHITE_LABEL_CONFIGS: Dict[str, Dict[str, Any]] = {}


class WhiteLabelConfigRequest(BaseModel):
    custom_domain: Optional[str] = None  # e.g. "intelligence.agency.com"
    brand_name: str
    logo_url: Optional[str] = None
    primary_color: str = "#38bdf8"
    footer_text: Optional[str] = "Powered by Dristik Intelligence Engine"
    custom_css: Optional[str] = None
    is_enabled: bool = True


@router.get("")
async def get_white_label_config(
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    org_id = user.org_id if user else "org_default"
    config = _WHITE_LABEL_CONFIGS.get(org_id)
    if not config:
        config = {
            "org_id": org_id,
            "brand_name": "Dristik AI",
            "custom_domain": None,
            "logo_url": None,
            "primary_color": "#38bdf8",
            "footer_text": "Powered by Dristik Cognitive Audit Engine",
            "is_enabled": False,
        }
    return config


@router.put("")
async def update_white_label_config(
    req: WhiteLabelConfigRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    org_id = user.org_id if user else "org_default"
    cfg = {
        "org_id": org_id,
        "brand_name": req.brand_name,
        "custom_domain": req.custom_domain,
        "logo_url": req.logo_url,
        "primary_color": req.primary_color,
        "footer_text": req.footer_text,
        "custom_css": req.custom_css,
        "is_enabled": req.is_enabled,
    }
    _WHITE_LABEL_CONFIGS[org_id] = cfg
    return {
        "status": "UPDATED",
        "config": cfg,
    }
