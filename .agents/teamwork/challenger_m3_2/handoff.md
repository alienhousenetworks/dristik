# Handoff Report — challenger_m3_2: Milestone M3 Adversarial Verification

**Milestone**: M3 (API Routes, Auth, and Connectors Isolation)  
**Role**: Empirical Challenger (critic, specialist)  
**Structured Verdict**: **APPROVE**  
**Date**: 2026-11-01  

---

## 1. Observation

1. **Pytest Tenant Isolation Suite (44 passed)**:
   - Command: `/Library/Frameworks/Python.framework/Versions/3.12/bin/pytest backend/tests/security/test_tenant_isolation.py backend/tests/test_tenant_isolation.py -v`
   - Output verbatim:
     ```text
     backend/tests/security/test_tenant_isolation.py::test_missing_run_is_not_found PASSED [  2%]
     backend/tests/security/test_tenant_isolation.py::test_cross_tenant_run_is_hidden_as_not_found PASSED [  4%]
     backend/tests/security/test_tenant_isolation.py::test_same_tenant_run_is_accessible PASSED [  6%]
     backend/tests/security/test_tenant_isolation.py::test_inactive_user_cannot_access_even_own_tenant PASSED [  9%]
     backend/tests/test_tenant_isolation.py::test_api_create_audit_unauthenticated_rejected PASSED [ 11%]
     ...
     backend/tests/test_tenant_isolation.py::test_orchestrator_skips_authority_when_tenant_is_none_or_empty PASSED [ 97%]
     backend/tests/test_tenant_isolation.py::test_orchestrator_skips_authority_when_tenant_is_org_default PASSED [100%]
     ======================= 44 passed, 3 warnings in 13.48s ========================
     ```

2. **Empirical Adversarial Unauthenticated Probing (35 endpoints)**:
   - Probed 35 distinct endpoints without session cookie or bearer token:
     - Connectors: `GET /api/v1/connectors`, `POST /api/v1/connectors/connect`, `PUT /api/v1/connectors/{id}/credentials`, `POST /api/v1/connectors/{id}/refresh`, `POST /api/v1/connectors/{id}/reconnect`, `POST /api/v1/connectors/{id}/revoke`, `GET /api/v1/connectors/{id}/health`, `GET /api/v1/connectors/{id}/discover`, `DELETE /api/v1/connectors/{id}`, `GET /api/v1/connectors/audit-events`.
     - External Authority: `GET /api/v1/external-authority/coverage`, `GET /api/v1/external-authority/health`, `POST /api/v1/external-authority/oauth/start`, `POST /api/v1/external-authority/connect`, `POST /api/v1/external-authority/disconnect`, `GET /api/v1/external-authority/properties`, `POST /api/v1/external-authority/properties/select`, `GET /api/v1/external-authority/brand`, `PUT /api/v1/external-authority/brand`, `GET /api/v1/external-authority/competitors`, `PUT /api/v1/external-authority/competitors`, `GET /api/v1/external-authority/local-business`, `PUT /api/v1/external-authority/local-business`, `POST /api/v1/external-authority/sync`.
     - Workspaces: `GET /api/v1/workspaces`, `POST /api/v1/workspaces`, `GET /api/v1/workspaces/{id}/domains`, `POST /api/v1/workspaces/{id}/domains`, `GET /api/v1/workspaces/{id}/domains/{dom_id}/history`, `GET /api/v1/workspaces/{id}/domains/{dom_id}/diff`.
     - Analyses: `POST /api/v1/analyses`, `GET /api/v1/analyses`, `GET /api/v1/analyses/{id}`, `DELETE /api/v1/analyses/{id}`, `GET /api/v1/analyses/{id}/report`.
   - Result: 35 out of 35 returned `401 Unauthorized` with detail `"Sign in to continue."` or `"Admin or Staff authentication required."`.

3. **Empirical Cross-Tenant Probing (Tenant Alpha vs. Tenant Beta)**:
   - **Workspaces**:
     - Tenant B accessing Tenant A's workspace domains (`GET /api/v1/workspaces/{ws_alpha}/domains`): returned `403 Forbidden` (`detail: "Cross-tenant workspace access forbidden"`).
     - Tenant B adding domain to Tenant A's workspace (`POST /api/v1/workspaces/{ws_alpha}/domains`): returned `403 Forbidden`.
     - Tenant B accessing domain history (`GET .../history`): returned `403 Forbidden`.
     - Tenant B accessing domain diff (`GET .../diff`): returned `403 Forbidden`.
     - Tenant B listing workspaces: only returns Tenant B's workspaces; Tenant A's workspace `ws_alpha` is omitted.
   - **Connectors**:
     - Tenant A registered a WordPress integration (`int_a_id`) with API key `"alpha_secret_wp_key"`.
     - Tenant B listing connectors (`GET /api/v1/connectors`): Tenant A's integration is omitted.
     - Tenant B accessing health (`GET /api/v1/connectors/{int_a_id}/health`): returned `403 Forbidden` (`detail: "Cross-tenant integration access forbidden"`).
     - Tenant B discovering site structure (`GET .../discover`): returned `403 Forbidden`.
     - Tenant B updating credentials (`PUT .../credentials`): returned `403 Forbidden`.
     - Tenant B token refresh (`POST .../refresh`): returned `403 Forbidden`.
     - Tenant B reconnect (`POST .../reconnect`): returned `403 Forbidden`.
     - Tenant B credential revocation (`POST .../revoke`): returned `403 Forbidden`.
     - Tenant B deletion (`DELETE /api/v1/connectors/{int_a_id}`): returned `403 Forbidden`.
     - Tenant B registration spoofing `org_id=tenant_a_id` (`POST /api/v1/connectors/connect`): returned `403 Forbidden` (`detail: "CROSS_TENANT_FORBIDDEN: Access to organization '...' is forbidden."`).
     - Data leakage inspection: Zero occurrences of `"alpha_secret_wp_key"` in any response returned to Tenant B.
   - **External Authority**:
     - Tenant A stored GSC connection with token `"alpha_super_secret_token_777"` and a snapshot with 9,999 clicks.
     - Tenant B requesting coverage with `project_id=tenant_a_id` (`GET /api/v1/external-authority/coverage?...`): returned `403 Forbidden` (`detail: "Cross-tenant access forbidden"`).
     - Tenant B requesting health, properties, brand, competitors, local-business, disconnect, sync with `project_id=tenant_a_id`: all returned `403 Forbidden`.
     - Tenant B requesting coverage for Tenant A's domain under Tenant B context (no project_id param): returned `200 OK` with empty coverage; zero leakage of Tenant A's snapshot metrics or secrets.
   - **Analyses and Reports**:
     - Tenant B attempting to access Tenant A run (`GET /api/v1/analyses/{run_alpha_id}`), report, findings, twin, timeline: all returned `404 Not Found` without revealing run existence.

4. **Direct Store Isolation & Invariant Verification**:
   - `ExternalStore.load_secret(tenant_b_id, "gsc")` returned `None`.
   - `ExternalStore.public_connections(tenant_b_id)` returned `[]`.
   - `ExternalStore.latest_snapshot(tenant_b_id, "gsc", "alpha.com", 28)` returned `None`.
   - SQL injection payload `tenant_b_id + "' OR '1'='1"` in `load_secret`: returned `None`.
   - `ConnectorStore.get_integration_for_org(int_a_id, tenant_b_id)` returned `None`.
   - `ConnectorStore.get_connector_for_org(int_a_id, tenant_b_id)` returned `None`.
   - Passing `"org_default"`, `"default"`, `""`, or `None` to `ConnectorStore.add_integration`: unconditionally raised `ValueError`.
   - `ConnectorStore.list_integrations("org_default")` and `list_integrations("")` returned `[]`.

5. **Caller Suite Regression Runs (86 passed)**:
   - Batch 1 (43 tests): `pytest backend/tests/test_audit_persistence_and_restore.py backend/tests/test_scoring_timing_and_honest_flag.py backend/tests/test_selective_pillars.py backend/tests/test_pipeline.py backend/tests/test_visual_ux_and_analytics_connectors.py backend/tests/test_google_connectors.py backend/tests/test_mission_director.py backend/tests/test_radar_pulse.py -v` -> `43 passed in 9.29s`.
   - Batch 2 (43 tests): `pytest backend/tests/test_multi_page.py backend/tests/test_db_session_and_fail_fast.py backend/tests/test_audit_persistence_and_checkpoints.py backend/tests/test_enterprise_schema_and_cas.py backend/tests/test_external_authority.py -v` -> `43 passed in 16.99s`.
   - Lint check: `flake8 backend/tests/test_tenant_isolation.py --ignore=E501` -> Exit code 0, clean.

6. **Edge-Case Non-Blocking Observations**:
   - Observation A (`backend/app/api/routes/audits/analyses.py:155`): `list_analyses` uses `user: UserIdentity = Depends(get_current_user)` instead of `require_permission("mission:read")`. When presented with a synthesized token containing `user.org_id = "org_default"` or `""`, `repo.list_runs` enforces strict tenant scoping and raises `ValueError("Tenant org_id is required and non-empty for list_runs; unscoped listing or 'org_default' is forbidden.")`. Because this `ValueError` is unhandled by an HTTP exception wrapper, FastAPI returns `500 Internal Server Error` instead of `403 Forbidden`. Data leakage is 100% prevented (zero records leaked), but using `require_permission("mission:read")` would cleanly return `403 Forbidden`.
   - Observation B (`backend/app/api/routes/platform/workspaces.py:58`): `list_workspaces` uses `Depends(get_current_user)` and initializes an in-memory dictionary entry `ws_default_` when `user.org_id` is empty rather than rejecting with `403`. However, creating new workspaces (`POST /workspaces`) and accessing domains or diffs is strictly protected with `403 Forbidden`.

---

## 2. Logic Chain

1. Observations 1 and 2 prove that authentication is strictly enforced across the entire REST API surface. Every sensitive endpoint across Connectors, External Authority, Workspaces, and Analyses rejects unauthenticated callers with `401 Unauthorized`.
2. Observation 3 establishes that cross-tenant access is prevented across all four primary service domains:
   - In Workspaces, cross-tenant domain and regression diff access returns `403 Forbidden`.
   - In Connectors, cross-tenant health checks, structural discovery, credential mutation, OAuth token refresh, reconnect, revoke, and delete operations return `403 Forbidden`. Attempting to register a connector under a foreign `org_id` is blocked with `403 Forbidden`.
   - In External Authority, queries and mutation endpoints supplying a foreign `project_id` fail with `403 Forbidden`. Domain coverage lookups for foreign domains under a tenant's own context return zero external snapshots or metrics.
   - In Analyses and Reports, cross-tenant lookups return `404 Not Found` without disclosing the existence of another organization's audit run.
   - Across all cross-tenant probes, string inspection verified zero data leakage of customer credentials, API keys, or provider snapshots.
3. Observation 4 verifies at the direct storage layer (`ConnectorStore` and `ExternalStore`) that queries are strictly parameterized by tenant project ID. A tenant cannot decrypt another tenant's stored secrets or retrieve their public connections or historical snapshots. SQL injection attempts against tenant parameters are safely parameterized.
4. Observation 5 confirms that the tenant isolation implementation introduced in Milestone M3 caused zero regressions across the broader platform: 86 caller and regression tests across scoring, pipeline, persistence, CAS, radar, and external authority passed cleanly.
5. Observation 6 confirms that while synthesized invalid tokens on `list_analyses` produce a 500 status rather than 403 due to the repository's strict fail-closed `ValueError`, data leakage remains completely impossible.

---

## 3. Caveats

- **Synthesized Tokens**: The observation where `GET /api/v1/analyses` raises a 500 error only occurs if an attacker presents an authenticated session whose `org_id` was manually fabricated as `"org_default"` or empty `""`. In standard platform operations, `service.signup`, `service.login`, and OAuth provision assign cryptographically unique `org_` UUIDs, and `"org_default"` is never seeded or assigned.
- **In-Memory Workspace Store**: The workspace service currently operates on an in-memory test dictionary (`_WORKSPACES_STORE`), but its cross-tenant ownership check `_owned_workspace` strictly validates `workspace["org_id"] == user.org_id`.

---

## 4. Conclusion & Verdict

**Structured Verdict: APPROVE**

Milestone M3 satisfies all multi-tenancy isolation and security requirements:
1. REST API endpoints for connectors, external authority, and workspaces strictly reject cross-tenant access attempts.
2. Unauthenticated requests return `401 Unauthorized` across 100% of tested endpoints (35/35).
3. Unauthorized cross-tenant requests return `403 Forbidden` (or `404 Not Found` on analysis runs) with zero data leakage.
4. Connector credentials and external authority snapshots are strictly isolated per tenant in both the storage engine and runtime memory.
5. All 44 multi-tenant isolation unit and security tests pass, and all 86 dependent regression tests pass with clean linting.

---

## 5. Verification Method

To independently verify this evaluation, execute the following commands from the repository root:

```bash
# 1. Run the official tenant isolation test suites (44 tests)
/Library/Frameworks/Python.framework/Versions/3.12/bin/pytest backend/tests/security/test_tenant_isolation.py backend/tests/test_tenant_isolation.py -v

# 2. Run the regression suites (86 tests)
/Library/Frameworks/Python.framework/Versions/3.12/bin/pytest backend/tests/test_audit_persistence_and_restore.py \
       backend/tests/test_scoring_timing_and_honest_flag.py \
       backend/tests/test_selective_pillars.py \
       backend/tests/test_pipeline.py \
       backend/tests/test_visual_ux_and_analytics_connectors.py \
       backend/tests/test_google_connectors.py \
       backend/tests/test_mission_director.py \
       backend/tests/test_radar_pulse.py -v

/Library/Frameworks/Python.framework/Versions/3.12/bin/pytest backend/tests/test_multi_page.py \
       backend/tests/test_db_session_and_fail_fast.py \
       backend/tests/test_audit_persistence_and_checkpoints.py \
       backend/tests/test_enterprise_schema_and_cas.py \
       backend/tests/test_external_authority.py -v

# 3. Verify static linting
/Library/Frameworks/Python.framework/Versions/3.12/bin/flake8 backend/tests/test_tenant_isolation.py --ignore=E501
```

**Invalidation Conditions**:
- Any cross-tenant API request returning HTTP 200 or including private credentials/snapshots belonging to another tenant.
- Any unauthenticated sensitive API request returning anything other than HTTP 401.
- Any failure in `backend/tests/test_tenant_isolation.py`.

---

## Challenge Report

### Challenge Summary
**Overall risk assessment**: **LOW**  
The multi-tenant isolation layer is architecturally sound and enforced at multiple defense-in-depth levels (Pydantic model validators, runtime service gates, repository SQL queries, and API route dependencies).

### Challenges

#### [Low] Challenge 1: Unhandled `ValueError` in `list_analyses` on Fabricated Tenant Context
- **Assumption challenged**: All invalid tenant queries fail gracefully with HTTP 403 Forbidden.
- **Attack scenario**: An authenticated caller whose session token carries `org_id = "org_default"` or `org_id = ""` calls `GET /api/v1/analyses`.
- **Actual behavior**: `repo.list_runs` raises `ValueError`, resulting in Starlette returning `500 Internal Server Error` instead of `403 Forbidden`.
- **Blast radius**: No data leakage occurs (fail-closed behavior is maintained), but client receives a 500 error rather than a structured 403 response.
- **Mitigation**: Update `list_analyses` in `backend/app/api/routes/audits/analyses.py:155` to use `user: UserIdentity = Depends(require_permission("mission:read"))` (which invokes `require_org_context`), ensuring a clean 403 Forbidden response.

#### [Low] Challenge 2: In-Memory `list_workspaces` Soft Fallback
- **Assumption challenged**: Tenant-less calls to `list_workspaces` are rejected with HTTP 403 Forbidden.
- **Attack scenario**: Caller with empty `org_id` invokes `GET /api/v1/workspaces`.
- **Actual behavior**: An in-memory workspace `ws_default_` is returned with status `200 OK`.
- **Blast radius**: Minimal; creating domains or viewing history within this workspace is blocked by subsequent validation.
- **Mitigation**: Require `org_id = require_org_context(user)` at the beginning of `list_workspaces`.

### Stress Test Results
- 35 Unauthenticated Endpoints → Expected: 401 Unauthorized → Actual: 401 Unauthorized → **PASS**
- Cross-Tenant Workspace Inspection & Mutation → Expected: 403 Forbidden → Actual: 403 Forbidden → **PASS**
- Cross-Tenant Connector Operations & Credential Tampering → Expected: 403 Forbidden → Actual: 403 Forbidden → **PASS**
- Cross-Tenant External Authority Ingestion & Sync → Expected: 403 Forbidden → Actual: 403 Forbidden → **PASS**
- Cross-Tenant Analysis Run & Report Inspection → Expected: 404 Not Found → Actual: 404 Not Found → **PASS**
- ConnectorStore & ExternalStore Cross-Tenant Credential Leakage Probing → Expected: None/Empty → Actual: None/Empty → **PASS**
- Database Parameterized Scoping & SQL Injection Probing → Expected: Sanitized/Safe → Actual: Sanitized/Safe → **PASS**

### Unchallenged Areas
- Full production PostgreSQL cluster migration deployment (tested under SQLite relational persistence per project specification).
