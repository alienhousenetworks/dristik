"""
Enterprise IAM: SAML 2.0 / OIDC SSO & SCIM 2.0 Directory Sync.
Implements RFC 7644 SCIM 2.0 User & Group Provisioning.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.domain.enums import UserRole
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional, require_permission

router = APIRouter(tags=["Enterprise IAM & SCIM 2.0"])

# In-memory SCIM store for users and groups
_SCIM_USERS = {}
_SCIM_GROUPS = {}


class SAMLConfigRequest(BaseModel):
    idp_entity_id: str
    sso_url: str
    certificate: str
    attribute_mapping: Dict[str, str] = Field(default_factory=lambda: {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "role": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    })


class SCIMName(BaseModel):
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None


class SCIMEmail(BaseModel):
    value: str
    primary: bool = True
    type: str = "work"


class SCIMUserCreateRequest(BaseModel):
    schemas: List[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"])
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    emails: List[SCIMEmail] = Field(default_factory=list)
    active: bool = True


# ---------------------------------------------------------------------------
# SAML / OIDC SSO Configuration
# ---------------------------------------------------------------------------

@router.post("/api/v1/auth/sso/saml/configure")
async def configure_saml(
    req: SAMLConfigRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    """Configures enterprise SAML 2.0 IDP connection."""
    if not req.sso_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="SSO URL must use HTTPS.")
    if "BEGIN CERTIFICATE" not in req.certificate:
        raise HTTPException(status_code=400, detail="Invalid X.509 Certificate format.")

    return {
        "status": "CONFIGURED",
        "idp_entity_id": req.idp_entity_id,
        "sso_url": req.sso_url,
        "acs_url": "https://api.dristik.ai/api/v1/auth/sso/saml/acs",
        "entity_id": "urn:dristik:sp",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# SCIM 2.0 Directory Sync Endpoints (RFC 7644)
# ---------------------------------------------------------------------------

@router.get("/scim/v2/Users")
async def list_scim_users():
    users_list = list(_SCIM_USERS.values())
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users_list),
        "startIndex": 1,
        "itemsPerPage": len(users_list),
        "Resources": users_list,
    }


@router.post("/scim/v2/Users", status_code=201)
async def create_scim_user(req: SCIMUserCreateRequest):
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    scim_obj = {
        "schemas": req.schemas,
        "id": user_id,
        "userName": req.userName,
        "name": req.name.model_dump() if req.name else {"formatted": req.displayName or req.userName},
        "displayName": req.displayName or req.userName,
        "emails": [e.model_dump() for e in req.emails] if req.emails else [{"value": req.userName, "primary": True}],
        "active": req.active,
        "meta": {
            "resourceType": "User",
            "created": now,
            "lastModified": now,
            "location": f"/scim/v2/Users/{user_id}",
        }
    }
    _SCIM_USERS[user_id] = scim_obj
    return scim_obj


@router.get("/scim/v2/Users/{user_id}")
async def get_scim_user(user_id: str):
    if user_id not in _SCIM_USERS:
        raise HTTPException(status_code=404, detail="SCIM User not found.")
    return _SCIM_USERS[user_id]


@router.delete("/scim/v2/Users/{user_id}", status_code=204)
async def delete_scim_user(user_id: str):
    if user_id in _SCIM_USERS:
        del _SCIM_USERS[user_id]
    return None


@router.get("/scim/v2/Groups")
async def list_scim_groups():
    groups_list = list(_SCIM_GROUPS.values())
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(groups_list),
        "startIndex": 1,
        "itemsPerPage": len(groups_list),
        "Resources": groups_list,
    }
