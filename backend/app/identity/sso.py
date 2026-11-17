"""
Enterprise IAM: SAML 2.0 / OIDC SSO & SCIM 2.0 Directory Sync.
Implements RFC 7644 SCIM 2.0 User & Group Provisioning with SQLite persistence.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.enterprise_schema import init_enterprise_schema
from app.domain.enums import UserRole
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission

router = APIRouter(tags=["Enterprise IAM & SCIM 2.0"])

_SSO_DB_PATH: str = "data/dristik_enterprise.db"

# Tenant-scoped SAML & SCIM stores (org_id -> {id -> resource})
_SAML_CONFIGS: Dict[str, Dict[str, Any]] = {}
_SCIM_USERS: Dict[str, Dict[str, Any]] = {}
_SCIM_GROUPS: Dict[str, Dict[str, Any]] = {}


def set_sso_db_path(db_path: str) -> None:
    global _SSO_DB_PATH
    _SSO_DB_PATH = db_path
    init_enterprise_schema(_SSO_DB_PATH)


def _get_sso_conn() -> sqlite3.Connection:
    init_enterprise_schema(_SSO_DB_PATH)
    conn = sqlite3.connect(_SSO_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _persist_saml_config(org_id: str, config_payload: Dict[str, Any]) -> None:
    try:
        conn = _get_sso_conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO enterprise_saml_configs (
                    org_id, idp_entity_id, sso_url, certificate,
                    attribute_mapping, acs_url, entity_id, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    org_id,
                    config_payload["idp_entity_id"],
                    config_payload["sso_url"],
                    config_payload.get("certificate", ""),
                    json.dumps(config_payload.get("attribute_mapping") or {}),
                    config_payload.get("acs_url"),
                    config_payload.get("entity_id"),
                    config_payload.get("status", "CONFIGURED"),
                    config_payload["updated_at"],
                ),
            )
        conn.close()
    except Exception:
        pass


def get_saml_config(org_id: str) -> Optional[Dict[str, Any]]:
    try:
        conn = _get_sso_conn()
        row = conn.execute(
            """
            SELECT org_id, idp_entity_id, sso_url, certificate,
                   attribute_mapping, acs_url, entity_id, status, updated_at
            FROM enterprise_saml_configs
            WHERE org_id = ?
            """,
            (org_id,),
        ).fetchone()
        conn.close()
        if row:
            mapping = json.loads(row["attribute_mapping"]) if row["attribute_mapping"] else {}
            cfg = {
                "org_id": row["org_id"],
                "status": row["status"],
                "idp_entity_id": row["idp_entity_id"],
                "sso_url": row["sso_url"],
                "certificate": row["certificate"],
                "attribute_mapping": mapping,
                "acs_url": row["acs_url"],
                "entity_id": row["entity_id"],
                "updated_at": row["updated_at"],
            }
            _SAML_CONFIGS[org_id] = cfg
            return cfg
    except Exception:
        pass
    return _SAML_CONFIGS.get(org_id)


def _persist_scim_user(org_id: str, scim_obj: Dict[str, Any]) -> None:
    try:
        conn = _get_sso_conn()
        now = scim_obj.get("meta", {}).get("lastModified") or datetime.now(timezone.utc).isoformat()
        created = scim_obj.get("meta", {}).get("created") or now
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO enterprise_scim_users (
                    id, org_id, user_name, display_name, active, payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scim_obj["id"],
                    org_id,
                    scim_obj.get("userName", ""),
                    scim_obj.get("displayName", ""),
                    1 if scim_obj.get("active", True) else 0,
                    json.dumps(scim_obj),
                    created,
                    now,
                ),
            )
        conn.close()
    except Exception:
        pass


def _load_scim_users_for_org(org_id: str) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    try:
        conn = _get_sso_conn()
        rows = conn.execute(
            "SELECT id, payload FROM enterprise_scim_users WHERE org_id = ? ORDER BY created_at ASC",
            (org_id,),
        ).fetchall()
        conn.close()
        for r in rows:
            try:
                merged[r["id"]] = json.loads(r["payload"])
            except Exception:
                pass
    except Exception:
        pass
    for uid, uobj in (_SCIM_USERS.get(org_id) or {}).items():
        merged[uid] = uobj
    if merged:
        _SCIM_USERS[org_id] = dict(merged)
    return merged


def _delete_scim_user_from_db(org_id: str, user_id: str) -> None:
    try:
        conn = _get_sso_conn()
        with conn:
            conn.execute(
                "DELETE FROM enterprise_scim_users WHERE org_id = ? AND id = ?",
                (org_id, user_id),
            )
        conn.close()
    except Exception:
        pass


def _persist_scim_group(org_id: str, group_obj: Dict[str, Any]) -> None:
    try:
        conn = _get_sso_conn()
        now = group_obj.get("meta", {}).get("lastModified") or datetime.now(timezone.utc).isoformat()
        created = group_obj.get("meta", {}).get("created") or now
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO enterprise_scim_groups (
                    id, org_id, display_name, payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    group_obj["id"],
                    org_id,
                    group_obj.get("displayName", ""),
                    json.dumps(group_obj),
                    created,
                    now,
                ),
            )
        conn.close()
    except Exception:
        pass


def _load_scim_groups_for_org(org_id: str) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    try:
        conn = _get_sso_conn()
        rows = conn.execute(
            "SELECT id, payload FROM enterprise_scim_groups WHERE org_id = ? ORDER BY created_at ASC",
            (org_id,),
        ).fetchall()
        conn.close()
        for r in rows:
            try:
                merged[r["id"]] = json.loads(r["payload"])
            except Exception:
                pass
    except Exception:
        pass
    for gid, gobj in (_SCIM_GROUPS.get(org_id) or {}).items():
        merged[gid] = gobj
        _persist_scim_group(org_id, gobj)
    if merged:
        _SCIM_GROUPS[org_id] = dict(merged)
    return merged


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


class SCIMGroupCreateRequest(BaseModel):
    schemas: List[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:Group"])
    displayName: str
    members: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SAML / OIDC SSO Configuration
# ---------------------------------------------------------------------------

@router.post("/api/v1/auth/sso/saml/configure")
async def configure_saml(
    req: SAMLConfigRequest,
    user: UserIdentity = Depends(require_permission("org:manage"))
):
    """Configures enterprise SAML 2.0 IDP connection and persists to SQLite."""
    if not req.sso_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="SSO URL must use HTTPS.")
    if "BEGIN CERTIFICATE" not in req.certificate:
        raise HTTPException(status_code=400, detail="Invalid X.509 Certificate format.")

    now = datetime.now(timezone.utc).isoformat()
    cfg = {
        "status": "CONFIGURED",
        "idp_entity_id": req.idp_entity_id,
        "sso_url": req.sso_url,
        "certificate": req.certificate,
        "attribute_mapping": req.attribute_mapping,
        "acs_url": "https://api.dristik.ai/api/v1/auth/sso/saml/acs",
        "entity_id": "urn:dristik:sp",
        "updated_at": now,
    }
    _SAML_CONFIGS[user.org_id] = cfg
    _persist_saml_config(user.org_id, cfg)
    return {
        "status": cfg["status"],
        "idp_entity_id": cfg["idp_entity_id"],
        "sso_url": cfg["sso_url"],
        "acs_url": cfg["acs_url"],
        "entity_id": cfg["entity_id"],
        "updated_at": cfg["updated_at"],
    }


@router.get("/api/v1/auth/sso/saml/config")
async def read_saml_config(
    user: UserIdentity = Depends(require_permission("org:manage"))
):
    cfg = get_saml_config(user.org_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="SAML SSO not configured for organization.")
    return cfg


# ---------------------------------------------------------------------------
# SCIM 2.0 Directory Sync Endpoints (RFC 7644)
# ---------------------------------------------------------------------------

@router.get("/scim/v2/Users")
async def list_scim_users(user: UserIdentity = Depends(require_permission("org:manage"))):
    org_users = _load_scim_users_for_org(user.org_id)
    users_list = list(org_users.values())
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users_list),
        "startIndex": 1,
        "itemsPerPage": len(users_list),
        "Resources": users_list,
    }


@router.post("/scim/v2/Users", status_code=201)
async def create_scim_user(
    req: SCIMUserCreateRequest,
    user: UserIdentity = Depends(require_permission("org:manage")),
):
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
    _SCIM_USERS.setdefault(user.org_id, {})[user_id] = scim_obj
    _persist_scim_user(user.org_id, scim_obj)
    return scim_obj


@router.get("/scim/v2/Users/{user_id}")
async def get_scim_user(
    user_id: str,
    user: UserIdentity = Depends(require_permission("org:manage")),
):
    org_users = _load_scim_users_for_org(user.org_id)
    if user_id not in org_users:
        raise HTTPException(status_code=404, detail="SCIM User not found.")
    return org_users[user_id]


@router.delete("/scim/v2/Users/{user_id}", status_code=204)
async def delete_scim_user(
    user_id: str,
    user: UserIdentity = Depends(require_permission("org:manage")),
):
    org_users = _SCIM_USERS.get(user.org_id, {})
    if user_id in org_users:
        del org_users[user_id]
    _delete_scim_user_from_db(user.org_id, user_id)
    return None


@router.get("/scim/v2/Groups")
async def list_scim_groups(user: UserIdentity = Depends(require_permission("org:manage"))):
    org_groups = _load_scim_groups_for_org(user.org_id)
    groups_list = list(org_groups.values())
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(groups_list),
        "startIndex": 1,
        "itemsPerPage": len(groups_list),
        "Resources": groups_list,
    }


@router.post("/scim/v2/Groups", status_code=201)
async def create_scim_group(
    req: SCIMGroupCreateRequest,
    user: UserIdentity = Depends(require_permission("org:manage")),
):
    group_id = f"grp_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    group_obj = {
        "schemas": req.schemas,
        "id": group_id,
        "displayName": req.displayName,
        "members": req.members,
        "meta": {
            "resourceType": "Group",
            "created": now,
            "lastModified": now,
            "location": f"/scim/v2/Groups/{group_id}",
        },
    }
    _SCIM_GROUPS.setdefault(user.org_id, {})[group_id] = group_obj
    _persist_scim_group(user.org_id, group_obj)
    return group_obj
