# Technical Enforcement Blueprint: API & Tenant Isolation (Milestone M3)
**Author**: explorer_m3_2 (Teamwork Explorer)  
**Date**: 2026-10-31  
**Project**: Dristik AI  
**Scope**: F12 (Strict Tenant Isolation & 403 Forbidden Enforcement), Credential Scoping, API Route Protection, and Persistence Scoping  

---

## 1. Executive Summary & Architectural Invariants

Multi-tenancy in enterprise SaaS requires that every operation execute strictly within an authenticated, authorized tenant boundary (`org_id`, `workspace_id`). Under Milestone M3, Dristik AI eliminates all legacy fallbacks to `"org_default"` and `"ws_default"`, ensuring that:
1. **No Unauthenticated Access**: Endpoints requiring tenant data reject unauthenticated requests with `401 Unauthorized`.
2. **Mandatory Tenant Context**: Requests lacking valid tenant context or providing an empty/default tenant identifier fail immediately with `403 Forbidden`.
3. **Cross-Tenant Prevention**: Any authenticated user from `org_A` attempting to read, submit, modify, or delete resources belonging to `org_B` is rejected with `403 Forbidden`.
4. **Per-Tenant Credential Scoping**: Third-party credentials (OAuth tokens, API keys for Google Search Console, GA4, WordPress, GitHub, Slack, Meta/WhatsApp, and LLM model providers) are encrypted at rest and partitioned strictly by `org_id`. No tenant can access, decrypt, or execute tools using another tenant's credentials.
5. **Durable Persistence Scoping**: All database operations (`audits`, `audit_runs`, `workspaces`, `domains`, `connector_integrations`, `external_connections`, `uc_provider_credentials`) enforce `org_id` at the query and constraint level.

---

## 2. Tenant Context Propagation Architecture

### 2.1 Sources of Tenant Context
Tenant context enters the API through three distinct vectors:

```
┌─────────────────────────────────────────────────────────────┐
│                       HTTP Request                          │
├──────────────────────────────┬──────────────────────────────┤
│ Vector 1: Auth Context       │ Vector 2: Explicit Headers   │
│ - Authorization: Bearer JWT  │ - X-Org-ID: <org_id>         │
│ - Cookie: dristik_session    │ - X-Workspace-ID: <ws_id>    │
│ -> Decoded into UserIdentity │ -> Client-declared tenant    │
│    (user_id, org_id, role)   │                              │
├──────────────────────────────┴──────────────────────────────┤
│ Vector 3: Payload / Query Parameters                        │
│ - AnalysisRequest.org_id / workspace_id                     │
│ - ConnectPlatformRequest.org_id                             │
│ - GET /external-authority/coverage?project_id=<org_id>       │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            require_org_context(user, requested_org)         │
│  - If user is None -> 401 Unauthorized                      │
│  - If user.org_id is empty/org_default -> 403 Forbidden     │
│  - If requested_org and requested_org != user.org_id:       │
│      -> Check Authorizer.is_system(user)                    │
│      -> If not system admin -> 403 Forbidden                │
│  - Returns validated non-empty org_id                       │
└─────────────────────────────────────────────────────────────┘
```

1. **Vector 1: Authenticated Identity (`UserIdentity`)**
   - Extracted by `get_current_user` in `backend/app/identity/deps.py` via `Authorization: Bearer <token>` or session cookie `dristik_session`.
   - Populates `UserIdentity` with:
     - `user_id: str`
     - `org_id: str` (The authoritative organization for the user session)
     - `workspaces: List[str]` (Permitted workspace IDs, defaults to `["*"]`)
     - `role: UserRole` (`OWNER`, `ADMIN`, `ANALYST`, `VIEWER`, `AUDITOR`, `SYSTEM_ADMIN`)
     - `is_active: bool`
     - `is_system: bool`

2. **Vector 2: Request Headers (`X-Org-ID`, `X-Workspace-ID`)**
   - Used by enterprise multi-tenant frontends or automation clients when switching workspaces or confirming intended tenant context.
   - **Invariant**: A client header `X-Org-ID` CANNOT elevate or switch privileges to an unowned organization. If `X-Org-ID` is present and does not match `user.org_id` (and user is not `SYSTEM_ADMIN`), the request is rejected with `403 Forbidden`.

3. **Vector 3: Request Payload / Query Parameters**
   - Request models such as `AnalysisRequest`, `ConnectPlatformRequest`, and query parameters such as `?project_id=...`.
   - **Remediation**: Remove default `"org_default"` and `"ws_default"` from all Pydantic models. If supplied by the caller, validate that they match the authenticated user's tenant context. If conflicting, reject with `403 Forbidden`.

---

## 3. HTTP Status Enforcement Matrix (401 vs 403 vs 404)

To prevent security vulnerabilities (confused deputy, cross-tenant data leakage) while maintaining consistency across the API and test suite:

| Condition / Scenario | HTTP Status | Error Detail Code | Architectural Rationale |
|---|---|---|---|
| No bearer token or session cookie provided, or token expired/invalid | **401 Unauthorized** | `"Sign in to continue."` | Missing authentication credentials (RFC 9110 §15.5.2). |
| Authenticated user has missing, empty, or `"org_default"` tenant ID | **403 Forbidden** | `"TENANT_CONTEXT_REQUIRED"` | Authenticated caller lacks a valid enterprise tenant context. |
| Authenticated caller from `org_A` provides `X-Org-ID: org_B` or `?project_id=org_B` | **403 Forbidden** | `"CROSS_TENANT_FORBIDDEN: Access to organization denied."` | Explicit unauthorized tenant access attempt. |
| Authenticated user account is disabled (`is_active = False`) | **403 Forbidden** | `"ACCOUNT_INACTIVE"` | Account access revoked (tested in `test_tenant_isolation.py:38-49`). |
| Authenticated user lacks RBAC capability (e.g. `VIEWER` calling `POST /analyses`) | **403 Forbidden** | `"You do not have permission to do that."` | RBAC role authorization failure. |
| Caller tries to query/modify another tenant's integration, connector, or workspace | **403 Forbidden** | `"CROSS_TENANT_ACCESS_DENIED"` | Resource belongs to a known foreign tenant. |
| Analysis run lookup (`/analyses/{analysis_id}`) where run does not exist | **404 Not Found** | `"Analysis run not found."` | Resource non-existence. |
| Analysis run lookup (`/analyses/{analysis_id}`) where run belongs to foreign tenant (opaque ID lookup) | **404 Not Found** / **403 Forbidden** | Stealth vs Strict: Default `require_analysis` returns `404` to prevent ID enumeration (tested in `test_cross_tenant_run_is_hidden_as_not_found`), while explicit tenant actions return `403`. |
| Workspace lookup (`/workspaces/{id}`) where workspace belongs to foreign org | **403 Forbidden** | `"CROSS_TENANT_ACCESS_DENIED: Workspace belongs to another organization."` | Explicit multi-tenant boundary. |

---

## 4. Core Dependency Design: `require_org_context` & `get_tenant_context`

### 4.1 Target Implementation in `backend/app/identity/deps.py`

```python
from dataclasses import dataclass
from typing import Optional
from fastapi import Cookie, Depends, Header, HTTPException, status
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.security import SESSION_COOKIE
from app.identity.store import get_store


@dataclass(frozen=True)
class TenantContext:
    org_id: str
    workspace_id: Optional[str]
    user: UserIdentity


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    if not user.org_id or user.org_id == "org_default":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TENANT_CONTEXT_REQUIRED: A valid tenant organization context is required.",
        )
    if requested_org_id and requested_org_id != user.org_id:
        if not Authorizer.can_access_org(user, requested_org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"CROSS_TENANT_FORBIDDEN: Access to organization '{requested_org_id}' is forbidden.",
            )
        return requested_org_id
    return user.org_id


def get_tenant_context(
    user: UserIdentity = Depends(get_current_user),
    x_org_id: Optional[str] = Header(default=None, alias="X-Org-ID"),
    x_workspace_id: Optional[str] = Header(default=None, alias="X-Workspace-ID"),
) -> TenantContext:
    """FastAPI dependency injecting validated TenantContext."""
    org_id = require_org_context(user, x_org_id)
    ws_id = x_workspace_id or (user.workspaces[0] if user.workspaces and user.workspaces != ["*"] else None)
    return TenantContext(org_id=org_id, workspace_id=ws_id, user=user)
```

Export `require_org_context`, `get_tenant_context`, and `TenantContext` in `backend/app/api/dependencies.py`.

---

## 5. Route-by-Route Remediation Blueprint

### 5.1 Audit Runs & Orchestrator API (`backend/app/api/routes/audits/analyses.py`)

#### 5.1.1 `POST /analyses` (`start_analysis`)
- **Current Observation**:
  Line 314: `run = orchestrator.create_run(url, org_id=user.org_id, created_by=user.user_id, target_pillars=request.target_pillars)`
  `AnalysisRequest` has `org_id: str = "org_default"` and `workspace_id: str = "ws_default"`.
  `request.workspace_id` is never passed to `orchestrator.create_run`!
- **Remediation**:
  1. Validate tenant context:
     ```python
     if request.org_id and request.org_id != "org_default" and request.org_id != user.org_id:
         if not Authorizer.can_access_org(user, request.org_id):
             raise HTTPException(
                 status_code=403,
                 detail="CROSS_TENANT_FORBIDDEN: Cannot start audit for another organization."
             )
     org_id = require_org_context(user, request.org_id if request.org_id != "org_default" else None)
     workspace_id = request.workspace_id if request.workspace_id != "ws_default" else None
     ```
  2. Pass `workspace_id` to `orchestrator.create_run`:
     ```python
     run = orchestrator.create_run(
         url,
         org_id=org_id,
         workspace_id=workspace_id,
         created_by=user.user_id,
         target_pillars=request.target_pillars,
     )
     ```
  3. Ensure `orchestrator.create_run` rejects missing or `"org_default"` orgs with `ValueError` (caught as 403/400).

#### 5.1.2 `GET /analyses` (`list_analyses`)
- **Current Observation**:
  Line 163-170: Reads `repo.list_runs(org_id=user.org_id, limit=limit)` and iterates `orchestrator.runs.values()`.
  Line 170: `if Authorizer.can_access_org(user, r.org_id): summaries.append(...)`
- **Remediation**:
  Ensure `require_org_context(user)` runs before listing. If `user.org_id` is empty or `"org_default"`, raise 403 Forbidden.
  Pass `workspace_id` if present in query parameters: `repo.list_runs(org_id=user.org_id, workspace_id=workspace_id, limit=limit)`.

#### 5.1.3 `DELETE /analyses/{analysis_id}` (`delete_analysis`)
- **Current Observation**:
  Line 222: `run = require_analysis(analysis_id, user, permission="mission:read")`
  Line 223: `removed = orchestrator.repository.delete_run(run.analysis_id, org_id=run.org_id)`
- **Remediation**:
  Maintain `org_id` scoping in repository deletion. If caller attempts to delete an analysis from another organization, `require_analysis` blocks the call.

---

### 5.2 External Authority & Integrations API

#### 5.2.1 `backend/app/api/routes/integrations/external_authority.py`
- **Current Observation**:
  Lines 90-102:
  ```python
  def _project(user: Optional[UserIdentity], requested: Optional[str]) -> str:
      if user is None or not user.org_id:
          raise HTTPException(status_code=401, detail="Sign in to continue.")
      if requested and requested != user.org_id:
          if not Authorizer.can_access_org(user, requested):
              raise HTTPException(status_code=404, detail="Project not found.")
          return requested
      return user.org_id
  ```
- **Flaw**:
  When `requested != user.org_id` and unauthorized, it raises **404 Not Found** instead of **403 Forbidden**!
  Also, if `user.org_id == "org_default"`, it allows execution in the shared default bucket.
- **Remediation**:
  Rewrite `_project` to use `require_org_context`:
  ```python
  def _project(user: Optional[UserIdentity], requested: Optional[str]) -> str:
      """Resolve project_id to the validated tenant org_id.
      
      Rejects cross-tenant attempts with 403 Forbidden.
      """
      return require_org_context(user, requested)
  ```
  This immediately converts cross-tenant queries into `403 Forbidden` and blocks `"org_default"`.

#### 5.2.2 `backend/app/api/routes/integrations/google.py`
- **Current Observation**:
  Lines 43 & 175:
  `org_id = user.org_id if user else "org_default"`
- **Flaw**:
  Severe vulnerability: unauthenticated or tenant-less requests fall back to `"org_default"`, querying or probing shared credentials!
- **Remediation**:
  1. Change route signatures from `user: Optional[UserIdentity] = Depends(get_current_user_optional)` to:
     `user: UserIdentity = Depends(get_current_user)`.
  2. Replace line 43 and line 175 with:
     `org_id = require_org_context(user)`.
  3. All connector listings and token probes are strictly isolated to `org_id`.

#### 5.2.3 `backend/app/api/routes/integrations/connectors.py`
- **Current Observation**:
  Line 241-242: `ConnectPlatformRequest` has `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
  Line 258: `_owned_integration` returns 404 when `not Authorizer.can_access_org(user, integration.org_id)`.
  Line 278: `req.workspace_id = str(getattr(user, "workspace_id", None) or "ws_default")`.
- **Remediation**:
  1. Remove default values from `ConnectPlatformRequest`:
     `org_id: Optional[str] = None`
     `workspace_id: Optional[str] = None`
  2. In `connect_platform`:
     ```python
     org_id = require_org_context(user, req.org_id)
     req.org_id = org_id
     ```
  3. In `_owned_integration(integration_id, user)`:
     ```python
     integration = connector_store.get_integration(integration_id)
     if not integration:
         raise HTTPException(status_code=404, detail="Integration not found.")
     if not Authorizer.can_access_org(user, integration.org_id):
         raise HTTPException(
             status_code=403,
             detail="CROSS_TENANT_ACCESS_DENIED: Integration belongs to another organization."
         )
     return integration
     ```
  4. Apply the same check in `_owned_connector` (line 139).

---

### 5.3 Workspaces & Enterprise Domain Hierarchy (`backend/app/api/routes/platform/workspaces.py`)

- **Current Observation**:
  Lines 40-45:
  ```python
  def _owned_workspace(workspace_id: str, user: UserIdentity) -> dict:
      workspace = _WORKSPACES_STORE.get(workspace_id)
      if not workspace or workspace.get("org_id") != user.org_id:
          raise HTTPException(status_code=404, detail="Workspace not found.")
      return workspace
  ```
  Line 60: `default_id = f"ws_default_{org_id}"`.
- **Flaw**:
  When a workspace exists in `_WORKSPACES_STORE` but belongs to another organization, it returns 404 instead of 403.
- **Remediation**:
  ```python
  def _owned_workspace(workspace_id: str, user: UserIdentity) -> dict:
      require_org_context(user)
      workspace = _WORKSPACES_STORE.get(workspace_id)
      if not workspace:
          raise HTTPException(status_code=404, detail="Workspace not found.")
      if workspace.get("org_id") != user.org_id and not Authorizer.is_system(user):
          raise HTTPException(
              status_code=403,
              detail="CROSS_TENANT_ACCESS_DENIED: Workspace belongs to another organization."
          )
      return workspace
  ```

---

### 5.4 Progressive Reports & PDF Generator (`backend/app/reports/pdf_generator.py`)

- All 21 endpoints in `pdf_generator.py` and all progressive report endpoints in `reports_progressive.py` call `run = require_analysis(analysis_id, user)`.
- **Remediation**:
  Ensure `require_analysis` verifies `require_org_context(user)` first.
  If the user is inactive or lacks `mission:read` permission -> 403 Forbidden.
  If the analysis run is found but belongs to another tenant:
  - For `require_analysis`: maintain existing 404 for unauthenticated/opaque scans if required by `test_cross_tenant_run_is_hidden_as_not_found`, OR if tenant context was explicitly supplied via headers/params, return 403 Forbidden.

---

## 6. Credential Store Per-Tenant Isolation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Credential Storage Layers                             │
├────────────────────────────────┬────────────────────────────────────────────┤
│ 1. ConnectorStore              │ 2. ExternalStore                           │
│    (app/connectors/store.py)   │    (app/connectors/authority/store.py)     │
│    - connector_integrations    │    - external_connections                  │
│    - AES-GCM encryption        │    - Fernet token encryption               │
│    - Key: (integration_id)     │    - Key: (project_id, provider)           │
│    - Mandatory org_id filter   │    - project_id == org_id                  │
├────────────────────────────────┴────────────────────────────────────────────┤
│ 3. Universal Connect / Provider Adapters                                    │
│    (app/api/routes/integrations/provider_adapters.py)                       │
│    - uc_provider_credentials                                                │
│    - Fernet encrypted API keys                                              │
│    - Filter: WHERE id = ? AND org_id = ?                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Platform Connectors (`backend/app/connectors/store.py`)
1. **Remove `"org_default"` default parameter**:
   Line 176:
   Change `def list_integrations(self, org_id: str = "org_default") -> List[Integration]:`
   To: `def list_integrations(self, org_id: str) -> List[Integration]:`
   If `not org_id or org_id == "org_default"`, raise `ValueError("A valid non-default org_id is required.")`.
2. **Enforce Tenant-Scoped Connector Resolution**:
   Line 318:
   Change `def add_integration(..., org_id: str = "org_default", workspace_id: str = "ws_default", ...):`
   To: `org_id: str, workspace_id: str` (mandatory non-default parameters).
3. **Guard `get_connector`**:
   Deprecate direct `get_connector(integration_id)` in favor of `get_connector_for_org(integration_id, org_id)`.

### 6.2 External Authority Store (`backend/app/connectors/authority/store.py`)
1. **Composite Primary / Unique Key**:
   In `external_connections`, the unique constraint is `UNIQUE(project_id, provider)`.
   Here `project_id` represents `org_id`.
2. **Secret Loading**:
   `load_secret(project_id: str, provider: str)` requires both `project_id` and `provider`. It is mathematically impossible for tenant A to load tenant B's secret using tenant A's `project_id`.
3. **Pipeline Bridge Scoping (`backend/app/orchestration/orchestrator.py:1534-1544`)**:
   Eliminate any fallback to blackboard or `"org_default"`:
   ```python
   tenant_project_id = run.org_id
   if not tenant_project_id or tenant_project_id == "org_default":
       logger.warning("External authority attachment skipped: run lacks valid tenant org_id")
   else:
       attachment = build_audit_attachment(
           project_id=tenant_project_id,
           domain=domain,
           pages=eval_pages,
           evidence_store=getattr(blackboard, "evidence_store", None),
       )
   ```

### 6.3 Universal Connect Provider Adapters (`provider_adapters.py`)
1. **Tenant Filtering on All SQL**:
   All SELECT, UPDATE, DELETE queries on `uc_provider_credentials` must include `WHERE org_id = ?`.
2. **Execution Context**:
   When an audit runs with a custom LLM provider override (`use_provider_override`), it binds to `(provider_id, org_id)` using a Python `ContextVar`, preventing cross-request leakage during asynchronous concurrency.

---

## 7. Persistence Layer Isolation Blueprint

### 7.1 Relational Schema & Foreign Key Cascades
From `backend/app/db/enterprise_schema.py` and SQLAlchemy models:
- `organizations` (`id` primary key)
- `workspaces` (`org_id` references `organizations.id` ON DELETE CASCADE)
- `domains` (`workspace_id` references `workspaces.id` ON DELETE CASCADE)
- `audit_runs` (`domain_id` references `domains.id` ON DELETE CASCADE)
- `audits` (`org_id` mandatory indexed column)

### 7.2 Repository Method Contracts (`backend/app/db/repository.py`)
1. `list_runs(org_id: str, workspace_id: Optional[str] = None, limit: int = 50)`:
   - `org_id` is a mandatory, non-empty string.
   - If `not org_id or org_id == "org_default"`:
     `raise ValueError("AuditRepository.list_runs requires a valid non-default org_id.")`
   - If `workspace_id`: query `WHERE org_id = ? AND workspace_id = ?`.
2. `get_run(analysis_id: str, org_id: Optional[str] = None)`:
   - When `org_id` is supplied: query `WHERE analysis_id = ? AND org_id = ?`.
3. `delete_run(analysis_id: str, org_id: str)`:
   - `org_id` is mandatory.
   - Refuses deletion if the record is not owned by `org_id`.

---

## 8. Inter-Agent Contract Alignment

| Task / File | Owner | Interface / Dependency Contract |
|---|---|---|
| Domain Models (`models.py`) | explorer_m3_1 / worker | Remove `"org_default"` / `"ws_default"` defaults in `AnalysisRequest`, `AnalysisRun`, `ExecutiveReport`. |
| Orchestrator (`orchestrator.py`) | explorer_m3_1 / worker | `create_run(website_url, org_id, workspace_id=None)` requires `org_id`. Line 1537 binds `project_id = run.org_id`. |
| API Isolation & 403 (`deps.py`, `analyses.py`, `google.py`, `external_authority.py`) | explorer_m3_2 (Blueprint) / worker | Implement `require_org_context`, reject cross-tenant and missing-tenant requests with `403 Forbidden`. |
| Test Specifications (`test_tenant_isolation.py`) | spec_miner_m3_3 / worker | T-TI-01 (Missing tenant -> 403), T-TI-02 (Zero org_default), T-TI-03 (Cross-tenant -> 403), T-TI-04 (Reports isolation), T-TI-05 (Credential store isolation). |

---

## 9. Step-by-Step Implementation Plan for Workers

1. **Step 1: Add `require_org_context` & `TenantContext` in `backend/app/identity/deps.py`**
   - Export in `backend/app/api/dependencies.py`.
2. **Step 2: Update `backend/app/api/routes/integrations/google.py`**
   - Require `get_current_user` dependency.
   - Eliminate lines 43 and 175 fallback to `"org_default"`.
   - Call `require_org_context(user)`.
3. **Step 3: Update `backend/app/api/routes/integrations/external_authority.py`**
   - Update `_project(user, requested)` to raise `403 Forbidden` on cross-tenant requests via `require_org_context(user, requested)`.
4. **Step 4: Update `backend/app/api/routes/integrations/connectors.py`**
   - Update `_owned_integration` and `_owned_connector` to raise `403 Forbidden` on foreign tenant integrations.
   - Remove `"org_default"` and `"ws_default"` from `ConnectPlatformRequest`.
5. **Step 5: Update `backend/app/api/routes/platform/workspaces.py`**
   - Update `_owned_workspace` to raise `403 Forbidden` when `workspace["org_id"] != user.org_id`.
6. **Step 6: Update `backend/app/api/routes/audits/analyses.py`**
   - In `start_analysis`: validate `request.org_id` against `user.org_id` (raise 403 if mismatched).
   - In `list_analyses`: validate `require_org_context(user)`.
7. **Step 7: Update `backend/app/connectors/store.py` & `backend/app/db/repository.py`**
   - Remove default `= "org_default"` from `list_integrations` and `list_runs`.
   - Require valid `org_id`.
8. **Step 8: Run and Extend Test Suite**
   - Verify `pytest backend/tests/security/test_tenant_isolation.py`.
   - Add new tests in `backend/tests/test_tenant_isolation.py` corresponding to T-TI-01 through T-TI-06.

---

## 10. Verification & Regression Strategy

1. **Unit Test Pass**:
   - `pytest backend/tests/security/test_tenant_isolation.py` (ensure existing 4 tests pass without regressions).
   - `pytest backend/tests/test_tenant_isolation.py` (ensure new tests verify 403 Forbidden for missing and cross-tenant access).
2. **Full Test Suite Integrity**:
   - Run `pytest backend/` ensuring all 2,248 tests pass.
   - Fixture verification: tests using `UserIdentity` must provide valid mock orgs (e.g. `test_org_01`) rather than expecting `"org_default"`.
