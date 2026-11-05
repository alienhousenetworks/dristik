# Phase 1 Codebase Survey Report: Unified Enterprise Persistence & Strict Multi-Tenancy Isolation

**Author**: `explorer_survey_3`  
**Date**: 2026-10-31  
**Working Directory**: `/Users/sayantande/Downloads/dristik-main`  
**Target Milestone**: Phase 1 — Unified Enterprise Persistence & Strict Multi-Tenancy Isolation  
**Reference Document**: `.agents/teamwork/ORIGINAL_REQUEST.md`, `DRISTIK_WORKING_FLOW_AGENTS_GAPS.md`, `docs/ENTERPRISE_AUDIT_INTEGRITY_REMEDIATION.md`

---

## 1. Executive Summary

Dristik's persistence architecture currently suffers from fragmented storage across four distinct SQLite databases (`dristik.db`, `dristik_audits.db`, `external_authority.db`, and `geo_aeo_pipeline.db`), an in-memory dictionary layer (`_WORKSPACES_STORE`, `_DOMAINS_STORE`), and a dangerous `MockSession` fallback in `backend/app/db/session.py`. 

Furthermore, tenant isolation contains significant loopholes: multiple domain models and services default `org_id` to `"org_default"` and `workspace_id` to `"ws_default"`. When external authority data is attached or integrations are queried without an authenticated user, the system silently defaults to `"org_default"` instead of failing with `403 Forbidden` / `401 Unauthorized`.

Additionally, the test suite (`pytest` in `backend/`) currently encounters circular import errors during test module collection due to premature import of `app.db.repository` inside `backend/app/persistence.py` before `sys.modules["app.persistence.models"]` is initialized.

This survey establishes the complete evidence base, exact file paths, line numbers, root cause analyses, unified schema architecture, and concrete remediation steps required for Phase 1 execution.

---

## 2. Persistence Layer Investigation

### 2.1 Database Session & Connection Handling (`backend/app/db/session.py`)

#### Current Implementation (`backend/app/db/session.py:1-74`)
- Line 6: `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dristik.db")`
- Lines 12-16: Creates a SQLAlchemy engine and sessionmaker:
  ```python
  engine = create_engine(
      DATABASE_URL,
      connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
  )
  SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  ```
- Lines 28-74: Implements a silent `MockSession` fallback when `ImportError` occurs:
  ```python
  except ImportError:
      class MockSession:
          def __init__(self):
              db_path = "dristik.db" if "sqlite:///" not in DATABASE_URL else DATABASE_URL.replace("sqlite:///", "")
              self.conn = sqlite3.connect(db_path)
              self.conn.row_factory = sqlite3.Row
          def query(self, *args, **kwargs): return self
          def filter(self, *args, **kwargs): return self
          def first(self): return None
          def all(self): return []
          def add(self, obj): pass
          def commit(self): self.conn.commit()
          def refresh(self, obj): pass
          def close(self): self.conn.close()
  ```

#### Identified Architectural Flaws
1. **Silent Failure and Data Loss**: `MockSession` stubs out write operations (`add` and `refresh` are no-ops) and query operations (`first()` returns `None`, `all()` returns `[]`). If SQLAlchemy import fails or dependencies are improperly bundled, the application silently runs without writing audit runs, users, or reports, creating phantom successes while losing data.
2. **Missing Configuration in `Settings`**: In `backend/app/core/config.py`, `DATABASE_URL` is completely absent from `Settings`. The application only defines `AUTH_DATABASE_PATH: str = Field(default="data/dristik.db")` (line 287) and `EXTERNAL_AUTHORITY_DB_PATH: str = "data/external_authority.db"` (line 427).
3. **No Connection Pool Health Check**: `create_engine` lacks `pool_pre_ping=True`, which is essential for PostgreSQL in production to reconnect after stale or severed network connections.
4. **No Fail-Fast Diagnostics**: If the PostgreSQL instance specified by `DATABASE_URL` is unreachable or misconfigured, the application does not fail fast at startup with diagnostic errors.

#### Required Remediation
- Add `DATABASE_URL: str = Field(default="sqlite:///data/dristik.db")` to `Settings` in `backend/app/core/config.py`.
- Delete `MockSession` entirely from `backend/app/db/session.py`.
- Configure `create_engine` with `pool_pre_ping=True` and conditional `connect_args={"check_same_thread": False}` only for SQLite URLs.
- Implement an explicit `verify_database_connection()` function executed during FastAPI startup (`@app.on_event("startup")` or lifespan context) that performs a lightweight probe (`SELECT 1`) and raises a fatal `RuntimeError` with connection diagnostics if unreachable.

---

### 2.2 Fragmented SQLite Store Mapping

The application splits persistence across 4 independent SQLite database files and 1 in-memory storage dictionary:

| Database File | Default Path | Owner Module | Key Tables & Responsibilities | Duplicated Data |
|---|---|---|---|---|
| `dristik.db` | `data/dristik.db` (`AUTH_DATABASE_PATH`) | `app/identity/store.py`, `app/connectors/store.py`, `app/crawl/vector_store.py` | `organizations`, `users`, `sessions`, `password_resets`, `contacts`, `audits` (lightweight), `integrations`, `connector_credentials`, `connector_action_runs`, `connector_events`, `uc_provider_credentials`, `uc_ai_connections`, `page_embeddings` | `organizations` duplicated with `dristik_audits.db`; `audits` summary duplicated with full run in `dristik_audits.db` |
| `dristik_audits.db` | `data/dristik_audits.db` (`AUDIT_DATABASE_PATH`) | `app/db/repository.py` (`AuditRepository`) | `organizations`, `audits` (full run & `raw_report_json`), `audit_checkpoints`, `audit_pages`, `audit_evidence`, `audit_claims`, `audit_findings`, `agent_telemetry`, `project_keywords`, `keyword_serp_history`, `keyword_competitors` | `organizations`, `audits`, and keyword tables (`project_keywords`, `keyword_serp_history`, `keyword_competitors`) duplicated with `external_authority.db` |
| `external_authority.db` | `data/external_authority.db` (`EXTERNAL_AUTHORITY_DB_PATH`) | `app/connectors/authority/store.py` (`ExternalStore`) | `schema_migrations`, `external_connections`, `external_accounts`, `external_properties`, `external_snapshots`, `external_raw_payloads`, `external_records`, `project_keywords`, `keyword_serp_history`, `keyword_competitors` | Keyword tracking tables duplicated with `dristik_audits.db` |
| `geo_aeo_pipeline.db` | `data/geo_aeo_pipeline.db` | `app/geo/pipeline_store.py` | `geo_queries`, `geo_snapshots` | - |
| In-Memory Dicts | Process Memory | `app/api/routes/platform/workspaces.py:35-37` | `_WORKSPACES_STORE`, `_DOMAINS_STORE`, `_DOMAIN_RUNS_STORE` | Workspaces and monitored domains defined in memory rather than persisted |

#### Key Observations:
1. **Three Repositories Using Raw SQLite**: `AuditRepository`, `ExternalStore`, and `IdentityStore` all execute direct raw `sqlite3.connect()` calls with custom SQL DDL scripts (`SQLITE_SCHEMA`, `migrations/001_external_authority.sql`, `IdentityStore.SCHEMA`).
2. **Duplicate Entity Definitions**:
   - `organizations` table exists in `dristik.db` (columns: `org_id, name, slug, plan, is_system, is_active, created_at, deleted_at`) and in `dristik_audits.db` (columns: `org_id, name, plan, created_at`).
   - `audits` table exists in `dristik.db` (columns: `analysis_id, org_id, user_id, website_url, status, page_count, overall_score, created_at, updated_at`) and in `dristik_audits.db` (columns: `analysis_id, org_id, user_id, website_url, domain, status, progress, stage, max_pages, score_overall, score_human, score_google, score_ai_readiness, score_ai_visibility, score_band, started_at, completed_at, input_hash, output_hash, raw_report_json, error_message, created_at`).
   - Keyword tracking tables (`project_keywords`, `keyword_serp_history`, `keyword_competitors`) are defined both in `backend/app/db/schema.py` and in `backend/app/connectors/authority/migrations/002_keyword_tracking.sql`.
3. **Data Divergence Risk**: `backend/scripts/enrich_demo_data.py` (lines 52-59, 346, 568-588) must execute writes across multiple SQLite databases simultaneously to prevent the UI from desynchronizing.

---

### 2.3 Existing SQLAlchemy Models & Alembic Configuration

#### SQLAlchemy Models (`backend/app/db/models/`)
The repository contains 11 declarative models under `backend/app/db/models/`:
- `Organization` (`organization.py`): Table `organizations`
- `User` (`user.py`): Table `users`
- `AuditRun` (`audit_run.py`): Table `audit_runs` (Note: Table name is `audit_runs`, whereas `AuditRepository` expects `audits`!)
- `CrawlPage` (`crawl_page.py`): Table `crawl_pages` (Note: `AuditRepository` expects `audit_pages`!)
- `Evidence` (`evidence.py`): Table `evidence` (Note: `AuditRepository` expects `audit_evidence`!)
- `Finding` (`finding.py`): Table `findings` (Note: `AuditRepository` expects `audit_findings`!)
- `Remediation` (`remediation.py`): Table `remediations`
- `Report` (`report.py`): Table `reports`
- `Scorecard` (`scorecard.py`): Table `scorecards`
- `Integration` (`integration.py`): Table `integrations`
- `AgentExecution` (`agent_execution.py`): Table `agent_executions` (Note: `AuditRepository` expects `agent_telemetry`!)

#### Enterprise Schema DDL (`backend/app/db/enterprise_schema.py`)
Defines `ENTERPRISE_POSTGRES_SCHEMA` and `ENTERPRISE_SQLITE_SCHEMA` with 8 tables:
1. `organizations`
2. `workspaces`
3. `domains`
4. `audit_runs`
5. `evidence_nodes`
6. `findings`
7. `ai_citations`
8. `enterprise_audit_logs`

#### Alembic Configuration
- `backend/alembic.ini`:
  - Line 2: `script_location = migrations`
  - Line 6: `sqlalchemy.url = sqlite:///dristik.db` (Hardcoded SQLite path)
- `backend/migrations/env.py`:
  - Line 13-14: `from app.db.base import Base; target_metadata = Base.metadata`
  - Connects using `sqlalchemy.url` from `alembic.ini`.
- `backend/migrations/versions`: **Does not exist**. No migration scripts have been created yet.

---

### 2.4 Unified PostgreSQL-Compatible Relational Model & SQLite Compatibility

To consolidate all stores into one unified database while retaining SQLite compatibility for local development and test execution:

1. **Unified Schema Strategy**:
   - Establish a canonical set of SQLAlchemy declarative models registered with `Base.metadata`.
   - Reconcile table naming discrepancies:
     - The operational pipeline in `backend/app/db/repository.py` uses `audits`, `audit_checkpoints`, `audit_pages`, `audit_evidence`, `audit_claims`, `audit_findings`, `agent_telemetry`.
     - The auth layer in `backend/app/identity/store.py` uses `organizations`, `users`, `sessions`, `password_resets`, `contacts`.
     - The external authority store in `backend/app/connectors/authority/store.py` uses `external_connections`, `external_accounts`, `external_properties`, `external_snapshots`, `external_raw_payloads`, `external_records`.
     - The workspace layer in `backend/app/db/enterprise_schema.py` uses `workspaces`, `domains`.
     - The keyword tracking layer uses `project_keywords`, `keyword_serp_history`, `keyword_competitors`.
2. **Cross-Engine Type Compatibility**:
   - `JSON`: SQLAlchemy's `JSON` type automatically generates `JSONB` on PostgreSQL and `TEXT` on SQLite.
   - `DateTime`: Use `DateTime(timezone=True)`, which maps to `TIMESTAMPTZ` on PostgreSQL and ISO-formatted strings on SQLite.
   - `Boolean`: Maps to `BOOLEAN` on PostgreSQL and `INTEGER` (0/1) on SQLite.
   - `String`: Explicit lengths (e.g. `String(64)`, `String(255)`) map to `VARCHAR(n)` on PostgreSQL and `TEXT` on SQLite.
3. **Database URL Routing**:
   - When `DATABASE_URL` is set (e.g., `sqlite:///data/dristik.db` or `postgresql://...`), all repositories (`AuditRepository`, `IdentityStore`, `ExternalStore`, `ConnectorStore`) route to this single database.
   - In SQLite mode, all stores point to the same SQLite database file (e.g., `data/dristik.db`) rather than 4 separate files.
   - In PostgreSQL mode, all stores connect via SQLAlchemy engine / connection pool.
4. **Alembic Modernization**:
   - Update `backend/migrations/env.py` to dynamically load `DATABASE_URL` from `app.core.config.settings.DATABASE_URL`.
   - Generate initial migration `backend/migrations/versions/001_initial_unified_schema.py` covering all tables.

---

## 3. Multi-Tenancy & Tenant Scoping Investigation

### 3.1 Tenancy Architecture Overview

In Dristik's tenancy model:
- `Organization` (`org_id`): Top-level customer boundary (e.g., `org_acme`).
- `Workspace` (`workspace_id`): Division/team boundary within an organization (e.g., `ws_marketing`).
- `Domain` (`domain_id`): Monitored web property belonging to a workspace.
- `User` (`user_id`): User identity bound to an `org_id` with a specific role (`SYSTEM_ADMIN`, `OWNER`, `ADMIN`, `ANALYST`, `VIEWER`, `AUDITOR`).

Access control rules:
- An authenticated user belongs to exactly one `org_id`.
- Users cannot access resources (`audits`, `reports`, `integrations`, `credentials`) belonging to another `org_id`.
- System administrators (`is_system=True` or `role=SYSTEM_ADMIN`) have global inspection privileges.

### 3.2 Audit of `org_default` and `ws_default` Fallbacks

The string literal `"org_default"` is used in multiple locations across the codebase as a fallback. Below is the comprehensive inventory:

| Location | Code Snippet | Flaw / Impact | Required Remediation |
|---|---|---|---|
| `backend/app/domain/models.py:125-126` | `class Integration(BaseModel): org_id: str = "org_default"; workspace_id: str = "ws_default"` | Model permits instantiation without explicit tenant binding; defaults to shared demo tenant. | Remove default values. Require mandatory `org_id` and `workspace_id`. |
| `backend/app/domain/models.py:333-334` | `class Finding(BaseModel): org_id: str = "org_default"; workspace_id: str = "ws_default"` | Findings created by specialists can default to `"org_default"`. | Remove default values. Propagate run's `org_id` and `workspace_id`. |
| `backend/app/domain/models.py:2733-2734` | `class AnalysisRun(BaseModel): org_id: str = "org_default"; workspace_id: str = "ws_default"` | Audit runs default to `"org_default"`, allowing unauthenticated/malformed requests to execute under demo tenant. | Remove defaults. Fail validation if `org_id` is missing. |
| `backend/app/domain/models.py:2609, 2716, 2733` | `CompetitorBakeoffRun.org_id = "org_default"`, `RadarTarget.org_id = "org_default"` | Background tracking jobs execute in `"org_default"`. | Require explicit `org_id`. |
| `backend/app/orchestration/orchestrator.py:99` | `def create_run(self, website_url: str, org_id: str = "org_default", ...)` | Creating an audit run falls back to `"org_default"` if omitted. | Remove default; require `org_id: str`. |
| `backend/app/orchestration/orchestrator.py:1537` | `project_id=getattr(run, "org_id", None) or "org_default"` | External authority attachment silently attaches snapshots from `"org_default"` if `run.org_id` is unset! | Remove fallback. If `run.org_id` is unset/empty, skip attachment with an explicit empty/unattached status. |
| `backend/app/orchestration/mission/director.py:26` | `def create_mission(..., org_id: str = "org_default", workspace_id: str = "ws_default")` | Mission director initializes runs in `"org_default"`. | Remove defaults; require explicit tenant IDs. |
| `backend/app/orchestration/mission/state.py:103-104` | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` | State machine checkpoints in demo tenant. | Remove defaults. |
| `backend/app/api/routes/integrations/google.py:43` | `org_id = user.org_id if user else "org_default"` in `GET /status` | Unauthenticated callers query Google connector credentials belonging to `"org_default"`. | Require authenticated user (`user: UserIdentity = Depends(get_current_user)`). If unauthenticated or no `org_id`, fail with `401 Unauthorized` / `403 Forbidden`. |
| `backend/app/api/routes/integrations/google.py:175` | `org_id = user.org_id if user else "org_default"` in `POST /probe/ga4` | Allows unauthorized GA4 credential probing against `"org_default"`. | Require authenticated user; fail with `403 Forbidden` if missing org context. |
| `backend/app/connectors/store.py:176` | `def list_integrations(self, org_id: str = "org_default")` | Listing integrations without `org_id` leaks `"org_default"` credentials. | Require explicit `org_id`. |
| `backend/app/connectors/store.py:318-319` | `def save_integration(..., org_id: str = "org_default", workspace_id: str = "ws_default")` | New integrations default to `"org_default"`. | Require explicit `org_id` and `workspace_id`. |
| `backend/app/db/repository.py:183-197` | `def list_runs(self, org_id: Optional[str] = None, limit: int = 50)` | If `org_id` is None, `SELECT * FROM audits` queries all audits across all organizations! | Require `org_id` unless caller is explicitly verified as `is_system=True`. |

### 3.3 Access Enforcement and 403 Forbidden Behavior

In `backend/app/identity/access.py`:
- `require_analysis(analysis_id: str, user: UserIdentity, permission: str = "mission:read")`:
  - Line 16: If `not Authorizer.can_perform(user, permission)`, raises `HTTPException(status_code=403, detail="You do not have permission to do that.")`.
  - Line 28: If `not Authorizer.can_access_org(user, getattr(run, "org_id", "") or "")`, raises `HTTPException(status_code=404, detail="Analysis run not found.")`.
- In `backend/app/identity/authorization.py:97-102`:
  ```python
  @staticmethod
  def can_access_org(user: UserIdentity, org_id: str) -> bool:
      if not user.is_active: return False
      if Authorizer.is_system(user): return True
      return user.org_id == org_id
  ```

#### Required Security Enhancements:
1. **Background Tasks & Pipeline Execution**: When `execute_analysis_pipeline` or scheduled tasks execute, they must validate that `run.org_id` is set to a non-empty, non-`"org_default"` tenant ID. If invalid, the run must terminate with status `FAILED` and error `"TENANT_CONTEXT_REQUIRED"`.
2. **Connector & Authority Probes**: Replace all `user.org_id if user else "org_default"` guards in `backend/app/api/routes/integrations/google.py` and `connectors.py` with strict dependencies `Depends(get_current_user)` and raise `HTTPException(status_code=403, detail="Tenant context required")`.
3. **Workspace Isolation**: In `backend/app/api/routes/platform/workspaces.py`, replace the in-memory `_WORKSPACES_STORE` and `_DOMAINS_STORE` with queries against the persistent database, filtering strictly by `workspace.org_id == user.org_id`.

---

## 4. Test Suite Investigation

### 4.1 Pytest Configuration & Test Execution

- Configuration file: `backend/pytest.ini`
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  ```
- Test runner environment:
  - System Python: Python 3.12.6, pytest 8.2.2, pytest-asyncio 0.23.7.
  - Test suite scope: 285 test files in `backend/tests/` containing ~2,248 individual test cases.
- Test commands verified working:
  - `pytest tests/test_auth_rbac.py` -> 12 passed in 9.84s.
  - `pytest tests/test_workspace_hierarchy_routes.py` -> 1 passed in 2.95s.

### 4.2 Root Cause Analysis: Test Collection Circular Import Bug

When running pytest on persistence or authority tests (e.g. `pytest tests/test_audit_persistence_and_checkpoints.py` or `pytest tests/test_enterprise_schema_and_cas.py`), test collection fails immediately with:
```
ModuleNotFoundError: No module named 'app.persistence.models'
```

#### Detailed Execution Trace
1. `tests/test_audit_persistence_and_checkpoints.py:9` executes:
   `from app.persistence.repository import AuditRepository`
2. Python imports `app/persistence.py`.
3. Inside `app/persistence.py`:
   - Line 11: `from app.db import storage_cas, enterprise_schema, schema, repository`
4. Importing `app.db.repository` (`backend/app/db/repository.py`):
   - Line 18: `from app.core.config import settings`
   - `app/core/config.py` triggers import of `app.core` -> `app.domain` -> `app.domain.scoring.score_explanations`.
5. Inside `backend/app/domain/scoring/score_explanations.py`:
   - Line 6: `from app.persistence.models import ScoreExplanation, ScoreExplanationDimension`
6. At this exact moment, `app.persistence` is still midway through executing line 11!
7. The assignment `sys.modules["app.persistence.models"] = models` is on line 19 of `app/persistence.py`, which has not yet executed.
8. Python cannot find `app.persistence.models` and raises `ModuleNotFoundError`.

#### Second Bug: Missing Pre-import of Compatibility Shims
When running `pytest tests/test_external_authority.py`, collection fails with:
```
ModuleNotFoundError: No module named 'app.external_authority'
```
Because `backend/app/connectors/__init__.py` registers `sys.modules["app.external_authority*"]`, but `app.connectors` has not been imported before `test_external_authority.py` executes.

#### Third Bug: `test_matomo_report.py` Script Execution
In `backend/tests/scripts/matomo_auth.py`, top-level code calls `sys.exit(1)` when environment credentials are unset, causing pytest collection to abort with `SystemExit: 1`.

#### Verification of Root Cause Resolution
We verified using Python 3.12 inline commands:
1. When `app.domain` and `app.connectors` are pre-loaded in `backend/conftest.py`:
   - `tests/test_audit_persistence_and_checkpoints.py` -> **5 passed** (100%).
   - `tests/test_enterprise_schema_and_cas.py` -> **4 passed** (100%).
   - `tests/test_external_authority.py` -> **16 passed** (100%).
   - `tests/test_audit_persistence_and_restore.py` -> **2 passed** (100%).
2. In `backend/app/domain/scoring/score_explanations.py`, line 6 should import directly from `app.db.models.audit`:
   `from app.db.models.audit import ScoreExplanation, ScoreExplanationDimension`
   This cleanly breaks the circular dependency without relying on import order.

---

### 4.3 PostgreSQL and SQLite Test Compatibility

To ensure the test suite executes against SQLite locally while maintaining full PostgreSQL production parity:

1. **Test Database Engine Fixture**:
   - In `backend/conftest.py`, define a session-scoped database fixture:
     ```python
     @pytest.fixture(scope="session")
     def db_engine():
         test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
         engine = create_engine(
             test_db_url,
             connect_args={"check_same_thread": False} if "sqlite" in test_db_url else {}
         )
         Base.metadata.create_all(bind=engine)
         yield engine
         Base.metadata.drop_all(bind=engine)
     ```
2. **Transaction Rollback per Test**:
   - For tests that modify database state, wrap each test in a transaction that rolls back upon completion (`connection.begin_nested()`), ensuring zero side-effects between test runs.
3. **Repository Injection**:
   - Update `AuditRepository`, `IdentityStore`, and `ExternalStore` to accept an optional SQLAlchemy `engine` or `session` parameter, allowing test fixtures to supply in-memory test databases seamlessly.

---

## 5. Concrete Phase 1 Implementation Plan

Based on these findings, Phase 1 implementation should follow this sequenced roadmap:

### Step 1: Configuration & Connection Hardening
- In `backend/app/core/config.py`:
  - Add `DATABASE_URL: str = Field(default="sqlite:///data/dristik.db")`.
- In `backend/app/db/session.py`:
  - Delete `MockSession` completely.
  - Implement fail-fast connection verification with diagnostic error logging.
  - Enable `pool_pre_ping=True`.

### Step 2: Fix Import Cycles & Test Harness Pre-requisites
- In `backend/app/domain/scoring/score_explanations.py:6`:
  - Change `from app.persistence.models import ...` to `from app.db.models.audit import ScoreExplanation, ScoreExplanationDimension`.
- In `backend/app/persistence.py`:
  - Re-order imports so `models` and `sys.modules["app.persistence.models"]` are set before importing `repository`.
- In `backend/conftest.py`:
  - Pre-import `app.connectors` and `app.persistence` to register compatibility shims before tests execute.

### Step 3: Unified Schema & Alembic Migrations
- In `backend/app/db/models/`:
  - Ensure all tables from `SQLITE_SCHEMA`, `ENTERPRISE_POSTGRES_SCHEMA`, and `001_external_authority.sql` have corresponding SQLAlchemy declarative models.
- In `backend/alembic.ini` and `backend/migrations/env.py`:
  - Wire `env.py` to `settings.DATABASE_URL`.
  - Create `backend/migrations/versions/001_initial_unified_schema.py`.

### Step 4: Storage Consolidation
- Update `AuditRepository`, `IdentityStore`, `ExternalStore`, and `ConnectorStore` to route queries to `settings.DATABASE_URL`.
- In `backend/app/api/routes/platform/workspaces.py`:
  - Replace `_WORKSPACES_STORE` and `_DOMAINS_STORE` with database-backed repository queries.

### Step 5: Strict Multi-Tenancy & Elimination of `org_default`
- Remove all `org_id = "org_default"` and `workspace_id = "ws_default"` defaults in:
  - `backend/app/domain/models.py` (`AnalysisRequest`, `AnalysisRun`, `Finding`, `Integration`, `CompetitorBakeoffRun`, `RadarTarget`).
  - `backend/app/orchestration/orchestrator.py` (`create_run`, `execute_analysis_pipeline`).
  - `backend/app/orchestration/mission/director.py` and `state.py`.
  - `backend/app/connectors/store.py` (`list_integrations`, `save_integration`).
- In `backend/app/orchestration/orchestrator.py:1537`:
  - Do NOT fall back to `"org_default"` during external authority attachment. If `run.org_id` is missing, mark attachment as unconfigured/empty.
- In `backend/app/api/routes/integrations/google.py` lines 43 and 175:
  - Replace fallback with `HTTPException(status_code=403, detail="Tenant context required")`.
- In `backend/app/db/repository.py`:
  - Enforce `org_id` requirement on `list_runs`.

### Step 6: Test Suite Verification
- Run full unit and regression test suite:
  - Verify all existing tests pass with `pytest tests/`.
  - Add regression tests verifying:
    1. Cross-tenant access attempts return `403 Forbidden` / `404 Not Found`.
    2. Background pipeline runs without valid tenant context fail closed.
    3. External authority attachment without tenant context leaves data unattached rather than pulling `"org_default"`.
    4. Database connection failure raises immediate startup exception.
