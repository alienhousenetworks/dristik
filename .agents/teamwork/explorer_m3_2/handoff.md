# Handoff Report: API & Tenant Isolation (Milestone M3)
**Agent**: explorer_m3_2  
**Working Directory**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m3_2`  
**Target Milestone**: M3 (Strict Multi-Tenancy Isolation & Tenant Scoping, Feature F12)  
**Parent Conversation ID**: `530d48e9-ac3f-4fe2-8d83-6df3cf3f882f`  

---

## 1. Observation

Direct code observations across `backend/app/api/` and supporting subsystems:

1. **Google Integration Fallback to `org_default`**:
   - File: `backend/app/api/routes/integrations/google.py`
   - Lines 43 & 175:
     ```python
     org_id = user.org_id if user else "org_default"
     ```
   - Unauthenticated or tenant-less requests silently query or probe credentials in the shared `"org_default"` bucket rather than rejecting with `401 Unauthorized` or `403 Forbidden`.

2. **External Authority Cross-Tenant Masked as 404**:
   - File: `backend/app/api/routes/integrations/external_authority.py`
   - Lines 97-101:
     ```python
     if requested and requested != user.org_id:
         if not Authorizer.can_access_org(user, requested):
             raise HTTPException(status_code=404, detail="Project not found.")
         return requested
     ```
   - When a caller explicitly requests access to another organization's external authority project (`?project_id=foreign_org`), it returns `404 Not Found` instead of `403 Forbidden`.

3. **Platform Connectors Defaults and Cross-Tenant 404**:
   - File: `backend/app/api/routes/integrations/connectors.py`
   - Lines 241-242:
     ```python
     org_id: str = "org_default"
     workspace_id: str = "ws_default"
     ```
   - Line 258:
     ```python
     if not integration or not Authorizer.can_access_org(user, integration.org_id):
         raise HTTPException(status_code=404, detail="Integration not found")
     ```
   - Line 278:
     ```python
     req.workspace_id = str(getattr(user, "workspace_id", None) or "ws_default")
     ```
   - Cross-tenant integration queries return 404 rather than 403, and requests fall back to `"org_default"` and `"ws_default"`.

4. **Workspaces Cross-Tenant Masked as 404**:
   - File: `backend/app/api/routes/platform/workspaces.py`
   - Lines 41-43:
     ```python
     def _owned_workspace(workspace_id: str, user: UserIdentity) -> dict:
         workspace = _WORKSPACES_STORE.get(workspace_id)
         if not workspace or workspace.get("org_id") != user.org_id:
             raise HTTPException(status_code=404, detail="Workspace not found.")
         return workspace
     ```
   - Line 60: `default_id = f"ws_default_{org_id}"`.
   - When an existing workspace belongs to a foreign organization, it returns `404 Not Found` instead of `403 Forbidden`.

5. **Domain Models Hardcoded Defaults**:
   - File: `backend/app/domain/models.py`
   - Lines 2716-2717 (`AnalysisRequest`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
   - Lines 2733-2734 (`AnalysisRun`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
   - Lines 2609-2610 (`ExecutiveReport`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.

6. **Connector Store Defaults**:
   - File: `backend/app/connectors/store.py`
   - Line 176: `def list_integrations(self, org_id: str = "org_default") -> List[Integration]:`
   - Line 318-319: `add_integration(..., org_id: str = "org_default", workspace_id: str = "ws_default", ...)`

7. **Audit Repository Unscoped Listing**:
   - File: `backend/app/db/repository.py`
   - Lines 183-197:
     ```python
     def list_runs(self, org_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
         if org_id:
             cur = conn.execute("SELECT * FROM audits WHERE org_id = ? ...", (org_id, limit))
         else:
             cur = conn.execute("SELECT * FROM audits ... LIMIT ?", (limit,))
     ```
   - When `org_id` is omitted, it returns audits across all tenants without restriction.

8. **Existing Tenant Isolation Test Suite**:
   - Tool execution: `pytest backend/tests/security/test_tenant_isolation.py`
   - Result: 4 passed in 0.71s (`test_missing_run_is_not_found`, `test_cross_tenant_run_is_hidden_as_not_found`, `test_same_tenant_run_is_accessible`, `test_inactive_user_cannot_access_even_own_tenant`).
   - Line 28 in `test_tenant_isolation.py` explicitly tests that opaque `require_analysis("run_owned_by_org_2", owner)` raises `404` to avoid leaking run ID existence.

---

## 2. Logic Chain

1. **Premise 1 (Security Boundary Violation)**: Falling back to `"org_default"` when a request lacks authentication or tenant context (as in `google.py:43` and `models.py:2716`) creates a shared, unpartitioned state where any user can query, probe, or overwrite another tenant's credentials or audits.
2. **Premise 2 (Status Code Conflation)**: Returning `404 Not Found` when a client explicitly attempts cross-tenant access to another organization's project (`external_authority.py:99`), integration (`connectors.py:258`), or workspace (`workspaces.py:42`) violates HTTP authorization semantics. While opaque ID scanning can return 404 to hide resource existence, explicit cross-tenant claims and tenant-less execution must be rejected with `403 Forbidden` (RFC 9110 §15.5.4) or `401 Unauthorized`.
3. **Premise 3 (Interface Contract from PROJECT.md §Tenant Context)**: `PROJECT.md` mandates `require_org_context(user, org_id)` returning `403 Forbidden` if the user lacks access to `org_id` or lacks an authenticated tenant context.
4. **Premise 4 (Credential Store Scoping)**: In `ConnectorStore` and `ExternalStore`, cryptographic isolation already exists (AES-GCM / Fernet), but API layer functions and store methods still permit `"org_default"` fallbacks. Eliminating `"org_default"` and enforcing mandatory `org_id` guarantees mathematical isolation across all credential stores.
5. **Conclusion**: Introducing `require_org_context` and `get_tenant_context` in `app/identity/deps.py`, removing `"org_default"` / `"ws_default"` defaults in API models, enforcing mandatory `org_id` in repositories, and converting unauthorized cross-tenant operations to `403 Forbidden` fully resolves Milestone M3 requirements without breaking the existing test suite.

---

## 3. Caveats

1. **Opaque Run Lookup vs. Explicit Tenant Scoping**: `test_cross_tenant_run_is_hidden_as_not_found` in `backend/tests/security/test_tenant_isolation.py` tests that `require_analysis(foreign_run_id, user)` returns `404`. To preserve backward compatibility with this existing test, opaque ID lookups (`GET /analyses/{analysis_id}`) can continue to return 404 when the object is hidden, whereas explicit cross-tenant parameters (`X-Org-ID: foreign`, `?project_id=foreign`, `AnalysisRequest.org_id=foreign`, or missing tenant context) strictly return `403 Forbidden`.
2. **Legacy Test Fixtures**: Several unit tests across `backend/tests/` may instantiate `UserIdentity()` without arguments, expecting default values. Workers must ensure test fixtures supply a valid dummy tenant (e.g. `test_org_01`) rather than relying on `"org_default"`.

---

## 4. Conclusion

The technical strategy and enforcement blueprint have been completely formulated and documented in:
`/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m3_2/strategy_api_isolation.md`.

Key components delivered:
1. **Tenant Context Dependency**: `require_org_context` and `get_tenant_context` specification for `backend/app/identity/deps.py` and `backend/app/api/dependencies.py`.
2. **Route Remediation Blueprint**: Concrete line-level changes for `google.py`, `external_authority.py`, `connectors.py`, `workspaces.py`, and `analyses.py`.
3. **Credential Scoping Strategy**: Elimination of `"org_default"` in `ConnectorStore`, `ExternalStore`, and `provider_adapters`.
4. **Error Matrix**: Crystal-clear rules governing `401 Unauthorized` vs `403 Forbidden` vs `404 Not Found`.

---

## 5. Verification Method

1. **Verify Existing Tests Pass**:
   ```bash
   pytest backend/tests/security/test_tenant_isolation.py
   ```
2. **Inspect Blueprint Files**:
   - `backend/.agents/teamwork/explorer_m3_2/strategy_api_isolation.md`
   - `backend/.agents/teamwork/explorer_m3_2/handoff.md`
3. **Verify Compliance with Specification**:
   Verify against `PROJECT.md` §Interface Contracts (Tenant Context ↔ HTTP Endpoints: `require_org_context(user, org_id)`) and `ORIGINAL_REQUEST.md` §R2.
