# Milestone M3: Strict Multi-Tenancy Isolation — Test Specification Blueprint

**File Target**: `backend/tests/test_tenant_isolation.py`  
**Milestone**: M3 (Strict Multi-Tenancy Isolation & Tenant Scoping)  
**Author**: `spec_miner_m3_3` (Specification Miner)  
**Date**: 2026-10-31  

---

## 1. Executive Summary & Architecture Overview

Milestone M3 establishes unbreakable tenant boundaries across Dristik AI by eliminating all legacy fallback mechanisms (such as `"org_default"` and `"ws_default"`) and enforcing mandatory, cryptographically secure tenant scoping across domain models, execution orchestrators, durable persistence repositories, report generation endpoints, and external authority credential stores.

This blueprint specifies the exhaustive test suite to be implemented in `backend/tests/test_tenant_isolation.py`. The suite rigorously tests:
1. **T-TI-01**: Rejection of audit requests without valid tenant context (HTTP 401/403 or `ValueError`).
2. **T-TI-02**: Zero tolerance for `"org_default"` and `"ws_default"` via both static code inspection (AST & signature reflection) and runtime assertions.
3. **T-TI-03**: Cross-tenant isolation for audit runs (in-memory registry, database persistence, lifecycle controls).
4. **T-TI-04**: Cross-tenant isolation for reports, findings, evidence taxonomies, and presentation decks.
5. **T-TI-05**: Tenant isolation across external authority and connector credential stores (encrypted token boundaries, snapshot scoping).
6. **T-TI-06**: External authority attachment in orchestrator strictly honoring caller tenant context with zero leakage during same-domain multi-tenant collisions.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Auth & Tenancy | Mandatory Tenant Context on Run Creation | Requests creating audit runs must supply valid, non-empty `org_id` and `workspace_id`. | `AnalysisRequest`, `orchestrator.create_run` | `AnalysisRun` with matching tenant ID | HTTP 401 (unauthenticated), HTTP 403 (invalid/missing org), `ValueError` on empty/None org | `app/api/routes/audits/analyses.py:229`, `app/orchestration/orchestrator.py:96` |
| 2 | Persistence | Repository Tenant-Scoped Listing | `AuditRepository.list_runs` requires non-empty `org_id`. Listing without `org_id` is prohibited to prevent leaking all cross-tenant runs. | `org_id: str`, `limit: int` | `List[Dict[str, Any]]` strictly matching `org_id` | `ValueError` if `org_id` is `None`, empty `""`, or `"org_default"` | `app/db/repository.py:183`, `PROJECT.md:49-50` |
| 3 | Persistence | Repository Tenant-Scoped Deletion | `AuditRepository.delete_run` requires matching `org_id` to delete audit and associated child records. | `analysis_id: str`, `org_id: str` | `bool` (`True` if deleted, `False` if not owned) | `ValueError` if `org_id` is missing/None; returns `False` if cross-tenant | `app/db/repository.py:199` |
| 4 | Security | Zero Tolerance for `org_default` / `ws_default` | Neither string may exist as a default in domain models, function signatures, or fallback assignments. | Model instantiation, AST inspection | Models require explicit tenant IDs or refuse default | `ValueError` / schema validation error if `"org_default"` or `"ws_default"` is passed | `app/domain/models.py:125,333,2609,2716,2733`, `PROJECT.md §F11` |
| 5 | Orchestration | In-Memory Run Isolation | `orchestrator.runs` dictionary filters access based on caller's `org_id`. | `analysis_id`, `UserIdentity` | `AnalysisRun` if caller matches `run.org_id` | HTTP 404 (hides existence of cross-tenant run) via `require_analysis` | `app/identity/access.py:10`, `app/orchestration/orchestrator.py` |
| 6 | Sub-Resources | Cross-Tenant Report & Finding Access Block | Reports, findings, manifests, twins, graphs, patch packs, and books are inaccessible across organizations. | `analysis_id`, `UserIdentity` | Report / Finding payloads if owned | HTTP 404 Not Found for cross-tenant callers | `app/api/routes/audits/analyses.py`, `app/reports/pdf_generator.py` |
| 7 | Credential Store | External Authority Secret Isolation | `ExternalStore.load_secret` decrypts tokens only for the exact matching `project_id`. | `project_id: str`, `provider: str` | Decrypted secret dictionary | Returns `None` if `project_id` does not match; no cross-tenant leakage | `app/connectors/authority/store.py:146` |
| 8 | Credential Store | Connector Store Tenant Boundary | `ConnectorStore.get_integration_for_org` and `get_connector_for_org` enforce tenant match. | `integration_id: str`, `org_id: str` | `Integration` / `BaseConnector` | Returns `None` if integration belongs to another org | `app/connectors/store.py:239,304` |
| 9 | Authority Bridge | Tenant-Scoped Authority Attachment | `build_audit_attachment` scopes evidence queries by `project_id`. | `project_id: str`, `domain: str` | Coverage report and domain findings | Fallback skipped if `project_id` is missing or `"org_default"`; returns unattached placeholder | `app/connectors/authority/audit_bridge.py:16`, `app/orchestration/orchestrator.py:1533` |
| 10 | Authority Bridge | Multi-Tenant Domain Collision Isolation | When two tenants audit the same domain, authority findings from Tenant A do not leak into Tenant B's report. | Same `domain`, different `project_id` | Separate, isolated reports and findings | Tenant B receives zero domain findings from Tenant A's external snapshots | `app/orchestration/orchestrator.py:1538` |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Run Creation | `org_id=None` or `org_id=""` passed to `orchestrator.create_run` | Must raise `ValueError("Tenant org_id is required")` immediately rather than creating an un-owned or orphan run. |
| 2 | Run Creation | Whitespace-only `org_id="   "` passed to `orchestrator.create_run` | Stripped and evaluated as empty -> raises `ValueError`. |
| 3 | Model Validation | `AnalysisRequest(website_url="https://example.com")` with no `org_id` | Must fail validation or require explicit tenant context (no silent `"org_default"` fallback). |
| 4 | Legacy Fallback | Passing `org_id="org_default"` to `orchestrator.create_run` | Raises `ValueError("Disallowed tenant identifier 'org_default'")`. |
| 5 | Repository Listing | `AuditRepository.list_runs(org_id=None)` | Raises `ValueError("Tenant org_id is required; unscoped listing is forbidden")`. |
| 6 | Repository Listing | `AuditRepository.list_runs(org_id="org_default")` | Raises `ValueError` or returns empty list `[]`; never scans unscoped database rows. |
| 7 | Cross-Tenant Delete | Tenant A deletes `analysis_id` belonging to Tenant B | `repo.delete_run(run_B, org_id="org_A")` returns `False`; record remains intact in SQLite/PostgreSQL. |
| 8 | Cross-Tenant API Access | Tenant A requests `GET /analyses/{run_B}/report` | `require_analysis` raises `HTTPException(status_code=404, detail="Analysis run not found.")` (hiding cross-tenant existence). |
| 9 | Inactive User Access | Active tenant user with `is_active=False` attempts to access own tenant's run | `Authorizer.can_access_org` returns `False` -> HTTP 403 Forbidden. |
| 10 | System Admin Access | User with `UserRole.SYSTEM_ADMIN` accesses tenant run | `Authorizer.is_system(user)` is `True` -> permitted for administrative operations only. |
| 11 | External Authority Secret | Tenant B queries `ExternalStore.load_secret("tenant_B", "gsc")` where only `tenant_A` configured GSC | Returns `None`; ciphertext for Tenant A is not decrypted or touched. |
| 12 | Same Domain Collisions | Tenant A has GSC connected for `example.com`; Tenant B runs audit on `example.com` | Tenant B gets `external_authority_connected=False`, 0 domain findings, empty coverage. |
| 13 | Cross-Workspace Access | User with `workspaces=["ws_1"]` accesses `ws_2` domain in same org | `_owned_workspace` in `workspaces.py` raises `HTTPException(404, detail="Workspace not found.")`. |

---

## 4. Test Specifications for `backend/tests/test_tenant_isolation.py`

### 4.1 Test Module Structure
The test module `backend/tests/test_tenant_isolation.py` must be structured into 6 primary test suites matching T-TI-01 through T-TI-06, supported by shared fixtures.

```
backend/tests/test_tenant_isolation.py
├── Fixtures:
│   ├── tenant_a_context / tenant_b_context
│   ├── mock_user_tenant_a / mock_user_tenant_b
│   ├── isolated_repo (tmp_path SQLite DB)
│   ├── isolated_external_store (tmp_path ExternalStore)
│   └── isolated_connector_store
├── Suite 1: T-TI-01 Rejection of Audit Requests Without Valid Tenant Context
├── Suite 2: T-TI-02 Zero Tolerance for org_default and ws_default
├── Suite 3: T-TI-03 Cross-Tenant Isolation for Audit Runs
├── Suite 4: T-TI-04 Cross-Tenant Isolation for Reports and Findings
├── Suite 5: T-TI-05 External Authority Credential Store Tenant Isolation
└── Suite 6: T-TI-06 External Authority Attachment in Orchestrator Honors Caller Tenant
```

---

### 4.2 Test Specifications Breakdown

#### T-TI-01: Rejection of Audit Requests Without Valid Tenant Context
*Goal: Guarantee that every entrypoint to audit execution, persistence, and querying strictly requires a valid, authenticated, non-empty tenant identifier.*

1. **`test_api_create_audit_unauthenticated_rejected`**
   - **Interface**: `POST /analyses`
   - **Setup**: Send request without auth cookie or Authorization header.
   - **Payload**: `{"website_url": "https://example.com"}`
   - **Assertion**: HTTP 401 Unauthorized (`{"detail": "Sign in to continue."}`).

2. **`test_api_create_audit_missing_tenant_org_rejected`**
   - **Interface**: `POST /analyses`
   - **Setup**: Authenticate as user with `org_id=""` or `org_id=None`.
   - **Assertion**: HTTP 403 Forbidden or 401.

3. **`test_orchestrator_create_run_none_org_raises_value_error`**
   - **Interface**: `orchestrator.create_run(website_url="https://example.com", org_id=None)`
   - **Assertion**: Raises `ValueError` with descriptive message matching `"tenant"` or `"org_id"`.

4. **`test_orchestrator_create_run_empty_org_raises_value_error`**
   - **Interface**: `orchestrator.create_run(website_url="https://example.com", org_id="")` and `org_id="   "`
   - **Assertion**: Raises `ValueError` with descriptive message.

5. **`test_repository_list_runs_without_org_raises_value_error`**
   - **Interface**: `AuditRepository.list_runs(org_id=None)`
   - **Assertion**: Raises `ValueError` (e.g., `"Tenant org_id is required"`). Prohibits unscoped table scans.

6. **`test_repository_list_runs_empty_org_raises_value_error`**
   - **Interface**: `AuditRepository.list_runs(org_id="")`
   - **Assertion**: Raises `ValueError`.

7. **`test_repository_delete_run_without_org_raises_value_error`**
   - **Interface**: `AuditRepository.delete_run(analysis_id="run_123", org_id=None)`
   - **Assertion**: Raises `ValueError`.

8. **`test_analysis_request_model_requires_valid_tenant`**
   - **Interface**: `AnalysisRequest`
   - **Assertion**: Instantiating without tenant or with invalid tenant context fails validation or raises `ValueError`.

---

#### T-TI-02: Zero Tolerance for `org_default` and `ws_default`
*Goal: Provide unbreakable static AST/reflection guarantees and runtime enforcement that neither `"org_default"` nor `"ws_default"` exists as a fallback anywhere in the system.*

1. **`test_static_models_do_not_contain_org_default_defaults`**
   - **Target**: `backend/app/domain/models.py`
   - **Mechanism**: Inspect Pydantic `model_fields`:
     - `AnalysisRequest.model_fields['org_id'].default != "org_default"`
     - `AnalysisRequest.model_fields['workspace_id'].default != "ws_default"`
     - `AnalysisRun.model_fields['org_id'].default != "org_default"`
     - `AnalysisRun.model_fields['workspace_id'].default != "ws_default"`
     - `Finding.model_fields['org_id'].default != "org_default"`
     - `Finding.model_fields['workspace_id'].default != "ws_default"`
     - `ExecutiveReport.model_fields['org_id'].default != "org_default"`
     - `ExecutiveReport.model_fields['workspace_id'].default != "ws_default"`
     - `Integration.model_fields['org_id'].default != "org_default"`
     - `Integration.model_fields['workspace_id'].default != "ws_default"`
   - **Assertion**: All assertions pass.

2. **`test_static_orchestrator_create_run_signature_no_org_default`**
   - **Target**: `app.orchestration.orchestrator.Orchestrator.create_run`
   - **Mechanism**: `inspect.signature(orchestrator.create_run).parameters['org_id'].default`
   - **Assertion**: Default is `inspect.Parameter.empty` or not equal to `"org_default"`.

3. **`test_static_connector_store_signatures_no_default_fallbacks`**
   - **Target**: `app.connectors.store.ConnectorStore.add_integration`
   - **Mechanism**: Check `org_id` and `workspace_id` parameter defaults.
   - **Assertion**: Neither equals `"org_default"` or `"ws_default"`.

4. **`test_static_tenant_manager_does_not_seed_org_default`**
   - **Target**: `app.identity.tenancy.manager.TenantManager`
   - **Mechanism**: Instantiate fresh `TenantManager()`.
   - **Assertion**: `"org_default" not in tm._orgs` and `"ws_default" not in tm._workspaces`.

5. **`test_static_codebase_ast_scan_no_org_default_fallbacks`**
   - **Target**: All `.py` files in `backend/app/`
   - **Mechanism**: AST parse all files. Search for:
     - `Constant(value="org_default")` in assignments, default arguments, and boolean fallbacks (`or "org_default"`).
     - `Constant(value="ws_default")`.
   - **Assertion**: Zero AST matches in core runtime code (excluding explicit validation checks / migrations).

6. **`test_runtime_orchestrator_rejects_org_default`**
   - **Interface**: `orchestrator.create_run(website_url="https://example.com", org_id="org_default")`
   - **Assertion**: Raises `ValueError("Disallowed tenant identifier 'org_default'")`.

7. **`test_runtime_repository_list_runs_rejects_org_default`**
   - **Interface**: `repo.list_runs(org_id="org_default")`
   - **Assertion**: Raises `ValueError` or returns empty `[]`.

8. **`test_runtime_external_authority_attachment_skips_org_default`**
   - **Interface**: `build_audit_attachment(project_id="org_default", domain="example.com")`
   - **Assertion**: Skips execution, returns unattached placeholder (`universal_authority_score=None`, empty findings).

---

#### T-TI-03: Cross-Tenant Isolation for Audit Runs
*Goal: Ensure Tenant A and Tenant B have hermetically sealed execution, storage, and management partitions.*

1. **`test_in_memory_runs_list_cross_tenant_isolation`**
   - **Setup**:
     - Register `run_alpha` (`org_id="org_alpha"`) in `orchestrator.runs`.
     - Register `run_beta` (`org_id="org_beta"`) in `orchestrator.runs`.
   - **Action**: Authenticate as User A (`org_alpha`) and call `GET /analyses`.
   - **Assertion**: Response list contains `run_alpha`, strictly excludes `run_beta`.
   - **Action**: Authenticate as User B (`org_beta`) and call `GET /analyses`.
   - **Assertion**: Response list contains `run_beta`, strictly excludes `run_alpha`.

2. **`test_in_memory_run_detail_cross_tenant_returns_404`**
   - **Setup**: `run_beta` belongs to `org_beta`.
   - **Action**: User A (`org_alpha`) calls `GET /analyses/{run_beta.analysis_id}`.
   - **Assertion**: HTTP 404 Not Found (verifying tenant existence masking).

3. **`test_database_list_runs_strict_tenant_filtering`**
   - **Setup**: In isolated SQLite repository, persist 3 runs: 2 for `org_alpha`, 1 for `org_beta`.
   - **Action**: `repo.list_runs(org_id="org_alpha")`
   - **Assertion**: Returns exactly 2 records, both with `org_id == "org_alpha"`.
   - **Action**: `repo.list_runs(org_id="org_beta")`
   - **Assertion**: Returns exactly 1 record with `org_id == "org_beta"`.

4. **`test_database_delete_run_cross_tenant_blocked`**
   - **Setup**: Persist `run_beta` under `org_beta`.
   - **Action**: Call `repo.delete_run(run_beta.analysis_id, org_id="org_alpha")`.
   - **Assertion**: Returns `False`.
   - **Verification**: Query `run_beta.analysis_id` -> record is still present in database.

5. **`test_api_delete_run_cross_tenant_returns_404`**
   - **Setup**: `run_beta` owned by `org_beta`.
   - **Action**: User A (`org_alpha`) sends `DELETE /analyses/{run_beta.analysis_id}`.
   - **Assertion**: HTTP 404 Not Found; `run_beta` remains in `orchestrator.runs` and DB.

6. **`test_lifecycle_control_cross_tenant_blocked`**
   - **Action**: User A (`org_alpha`) sends:
     - `POST /analyses/{run_beta.analysis_id}/pause`
     - `POST /analyses/{run_beta.analysis_id}/resume`
     - `POST /analyses/{run_beta.analysis_id}/nodes/node_scoring/run`
   - **Assertion**: All return HTTP 404 Not Found.

---

#### T-TI-04: Cross-Tenant Isolation for Reports and Findings
*Goal: Ensure executive reports, findings, presentation decks, and exported artifacts are unreachable across tenant boundaries.*

1. **`test_report_endpoint_cross_tenant_returns_404`**
   - **Setup**: `run_alpha` has completed report with scores and findings.
   - **Action**: User B (`org_beta`) calls `GET /analyses/{run_alpha.analysis_id}/report`.
   - **Assertion**: HTTP 404 Not Found.

2. **`test_findings_endpoint_cross_tenant_returns_404`**
   - **Action**: User B (`org_beta`) calls `GET /analyses/{run_alpha.analysis_id}/findings`.
   - **Assertion**: HTTP 404 Not Found.

3. **`test_manifest_and_twin_endpoints_cross_tenant_returns_404`**
   - **Action**: User B calls:
     - `GET /analyses/{run_alpha.analysis_id}/manifest`
     - `GET /analyses/{run_alpha.analysis_id}/twin`
     - `GET /analyses/{run_alpha.analysis_id}/intent-graph`
     - `GET /analyses/{run_alpha.analysis_id}/remediation`
     - `GET /analyses/{run_alpha.analysis_id}/timeline`
   - **Assertion**: All return HTTP 404 Not Found.

4. **`test_evidence_explorer_and_graph_cross_tenant_returns_404`**
   - **Action**: User B calls:
     - `GET /analyses/{run_alpha.analysis_id}/evidence-explorer`
     - `GET /analyses/{run_alpha.analysis_id}/evidence-graph`
     - `GET /analyses/{run_alpha.analysis_id}/score-explanation`
     - `GET /analyses/{run_alpha.analysis_id}/checkpoints`
   - **Assertion**: All return HTTP 404 Not Found.

5. **`test_adaptive_audit_book_html_pdf_cross_tenant_returns_404`**
   - **Action**: User B calls:
     - `GET /reports/{run_alpha.analysis_id}/audit-book?format=html`
     - `GET /reports/{run_alpha.analysis_id}/audit-book?format=json`
     - `GET /reports/{run_alpha.analysis_id}/audit-book?format=pdf`
   - **Assertion**: All return HTTP 404 Not Found.

6. **`test_section_deck_cross_tenant_returns_404`**
   - **Action**: User B calls `GET /reports/{run_alpha.analysis_id}/section-deck/seo`.
   - **Assertion**: HTTP 404 Not Found.

7. **`test_patch_pack_downloads_cross_tenant_returns_404`**
   - **Action**: User B calls:
     - `GET /analyses/{run_alpha.analysis_id}/patch-pack/zip`
     - `GET /analyses/{run_alpha.analysis_id}/patch-pack/files`
     - `GET /analyses/{run_alpha.analysis_id}/patch-pack/notion`
     - `GET /analyses/{run_alpha.analysis_id}/whatsapp-summary`
   - **Assertion**: All return HTTP 404 Not Found.

8. **`test_finding_model_scoping_invariant`**
   - **Setup**: Generate finding set for `run_alpha`.
   - **Assertion**: Every `finding.org_id == "org_alpha"`. Repository query for `org_id="org_beta"` returns 0 findings.

---

#### T-TI-05: External Authority Credential Store Tenant Isolation
*Goal: Ensure encrypted provider tokens, account metadata, catalog properties, and historical snapshots belonging to Tenant A can never be inspected or decrypted by Tenant B.*

1. **`test_external_store_secret_decryption_isolated_per_tenant`**
   - **Setup**: In isolated `ExternalStore`, upsert connection for `project_id="org_alpha"`, provider `"gsc"`, with encrypted token `{"client_secret": "alpha_secret_token"}`.
   - **Action**: `store.load_secret("org_alpha", "gsc")`
   - **Assertion**: Successfully returns `{"client_secret": "alpha_secret_token"}`.
   - **Action**: `store.load_secret("org_beta", "gsc")`
   - **Assertion**: Returns `None`. Secret is completely unreachable.

2. **`test_external_store_public_connections_isolated_per_tenant`**
   - **Setup**:
     - `org_alpha` has `"gsc"` connection.
     - `org_beta` has `"ahrefs"` connection.
   - **Action**: `store.public_connections("org_alpha")`
   - **Assertion**: Contains `"gsc"`, contains zero occurrences of `"ahrefs"`.
   - **Action**: `store.public_connections("org_beta")`
   - **Assertion**: Contains `"ahrefs"`, contains zero occurrences of `"gsc"`.

3. **`test_external_store_snapshots_isolated_per_tenant`**
   - **Setup**: Save snapshot for domain `"example.com"` with `project_id="org_alpha"`.
   - **Action**: `store.latest_snapshots("org_alpha", "example.com")`
   - **Assertion**: Returns 1 snapshot record.
   - **Action**: `store.latest_snapshots("org_beta", "example.com")`
   - **Assertion**: Returns empty list `[]`.

4. **`test_connector_store_integration_lookup_isolated_per_tenant`**
   - **Setup**: Add WordPress integration with `org_id="org_alpha"`.
   - **Action**: `connector_store.get_integration_for_org(int_id, org_id="org_alpha")`
   - **Assertion**: Returns integration.
   - **Action**: `connector_store.get_integration_for_org(int_id, org_id="org_beta")`
   - **Assertion**: Returns `None`.
   - **Action**: `connector_store.get_connector_for_org(int_id, org_id="org_beta")`
   - **Assertion**: Returns `None`.

5. **`test_api_external_authority_health_cross_tenant_rejected`**
   - **Setup**: User B (`org_beta`) calls `GET /api/external-authority/health?project_id=org_alpha`.
   - **Assertion**: HTTP 404 Not Found (or 403 Forbidden).

6. **`test_api_external_authority_coverage_cross_tenant_rejected`**
   - **Setup**: User B (`org_beta`) calls `GET /api/external-authority/coverage?domain=example.com&project_id=org_alpha`.
   - **Assertion**: HTTP 404 Not Found (or 403 Forbidden).

---

#### T-TI-06: External Authority Attachment in Orchestrator Honors Caller Tenant Context
*Goal: Ensure orchestrator external authority attachment strictly uses the caller's tenant org ID, prevents cross-tenant data leakage during same-domain multi-tenant audits, and safely fails closed on missing tenant context.*

1. **`test_orchestrator_passes_exact_tenant_org_id_to_audit_bridge`**
   - **Setup**: Create run with `org_id="org_enterprise_alpha"`.
   - **Action**: Mock `build_audit_attachment` and execute external authority stage in orchestrator.
   - **Assertion**: `build_audit_attachment.assert_called_once()`. Keyword argument `project_id` must equal `"org_enterprise_alpha"` exactly.

2. **`test_multi_tenant_same_domain_collision_zero_leakage`**
   - **Scenario**: Two independent enterprises audit the same public domain `enterprise-target.com`.
     - `org_alpha` has connected Google Search Console credentials and cached snapshot with 5 crawl findings.
     - `org_beta` has NOT connected any external credentials.
   - **Execution**:
     - Run analysis pipeline for `org_alpha`:
       - `external_authority.coverage` shows `CONNECTED`.
       - `has_external_authority_connected == True`.
       - `report.honest_scores` reflects external authority connection.
       - Report contains the 5 external domain findings.
     - Run analysis pipeline for `org_beta`:
       - `external_authority.coverage` is empty.
       - `has_external_authority_connected == False`.
       - `report.honest_scores` reflects external authority NOT connected.
       - Report contains ZERO findings from `org_alpha`.
   - **Assertion**: Complete isolation verified on same-domain multi-tenant audits.

3. **`test_orchestrator_skips_authority_when_tenant_is_none_or_empty`**
   - **Setup**: Run object has `org_id=None` or `org_id=""`.
   - **Action**: Execute external authority attachment logic.
   - **Assertion**: `build_audit_attachment` is NEVER called. `external_authority_payload["notes"]` contains `"External authority was not attached: valid tenant context required."`.

4. **`test_orchestrator_skips_authority_when_tenant_is_org_default`**
   - **Setup**: Run object has `org_id="org_default"`.
   - **Action**: Execute external authority attachment logic.
   - **Assertion**: `build_audit_attachment` is NEVER called; refuses `"org_default"` fallback.

---

## 5. Fixture Architecture & Implementation Details

To ensure clean isolation and fast test runs without polluting persistent databases, `backend/tests/test_tenant_isolation.py` must define the following fixtures:

```python
import os
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.domain.enums import UserRole
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, get_current_user_optional
from app.orchestration.orchestrator import orchestrator
from app.db.repository import AuditRepository
from app.connectors.authority.store import ExternalStore
from app.connectors.store import ConnectorStore

@pytest.fixture
def tenant_a_id():
    return f"org_alpha_{uuid.uuid4().hex[:6]}"

@pytest.fixture
def tenant_b_id():
    return f"org_beta_{uuid.uuid4().hex[:6]}"

@pytest.fixture
def user_a(tenant_a_id):
    return UserIdentity(
        user_id=f"usr_a_{uuid.uuid4().hex[:6]}",
        org_id=tenant_a_id,
        email="admin@alpha.test",
        role=UserRole.ADMIN,
        is_active=True,
    )

@pytest.fixture
def user_b(tenant_b_id):
    return UserIdentity(
        user_id=f"usr_b_{uuid.uuid4().hex[:6]}",
        org_id=tenant_b_id,
        email="admin@beta.test",
        role=UserRole.ADMIN,
        is_active=True,
    )

@pytest.fixture
def auth_client():
    """Client helper with context-manager for overriding authenticated user."""
    class AuthClient:
        def __init__(self):
            self.client = TestClient(app)

        def as_user(self, user: UserIdentity):
            class UserContext:
                def __enter__(_self):
                    app.dependency_overrides[get_current_user] = lambda: user
                    app.dependency_overrides[get_current_user_optional] = lambda: user
                    return self.client

                def __exit__(_self, exc_type, exc_val, exc_tb):
                    app.dependency_overrides.clear()

            return UserContext()

    return AuthClient()

@pytest.fixture
def isolated_repo(tmp_path):
    """Hermetic SQLite repository for audit persistence."""
    db_path = str(tmp_path / "test_audits.db")
    repo = AuditRepository(db_path=db_path)
    return repo

@pytest.fixture
def isolated_external_store(tmp_path):
    """Hermetic ExternalStore for external authority credentials."""
    db_path = str(tmp_path / "test_authority.db")
    return ExternalStore(path=db_path)
```

---

## 6. Verification & Test Execution Guide

When Milestone M3 code modifications are applied, the test suite can be verified with:

```bash
# Run the newly designed tenant isolation test suite
pytest backend/tests/test_tenant_isolation.py -v

# Run the existing security tenant isolation suite
pytest backend/tests/security/test_tenant_isolation.py -v

# Verify no regression across whole persistence and scoring test suites
pytest backend/tests/test_db_session_and_fail_fast.py backend/tests/test_scoring_timing_and_honest_flag.py -v
```

All assertions must pass cleanly with 0 failures, 0 regressions, and strict adherence to codebase-first and ponytail principles (smallest complete change, zero bloat).
