# Phase 1 Codebase Survey Handoff Report

**Agent**: `explorer_survey_3`  
**Working Directory**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_survey_3`  
**Milestone**: Phase 1 (Unified Enterprise Persistence & Strict Multi-Tenancy Isolation) Survey  
**Report Artifact**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_survey_3/survey_phase1_report.md`

---

## 1. Observation

### 1.1 Database Session & Mock Fallback
- `backend/app/db/session.py:6`: `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dristik.db")`
- `backend/app/db/session.py:28-74`: Under `except ImportError:`, `class MockSession` is defined. Methods: `query()`, `filter()`, `first() -> None`, `all() -> []`, `add(obj) -> pass`, `refresh(obj) -> pass`. Session is aliased to `MockSession`, resulting in silent no-op writes and empty queries.
- `backend/app/core/config.py`: `DATABASE_URL` is completely absent from `Settings`. Only `AUTH_DATABASE_PATH: str = Field(default="data/dristik.db")` (line 287) and `EXTERNAL_AUTHORITY_DB_PATH: str = "data/external_authority.db"` (line 427) are declared.

### 1.2 Fragmented SQLite Files & In-Memory Stores
- `dristik.db`: Created by `app/identity/store.py` (`IdentityStore.__init__` lines 91-100) and accessed by `app/connectors/store.py`, `app/crawl/vector_store.py`, and `app/api/routes/audits/deep_crawls.py`. Stores `organizations`, `users`, `sessions`, `password_resets`, `contacts`, `audits` (summary), and connector credentials.
- `dristik_audits.db`: Created by `app/db/repository.py` (`AuditRepository.__init__` line 40) using `SQLITE_SCHEMA`. Stores `organizations` (duplicated), `audits` (full runs), `audit_checkpoints`, `audit_pages`, `audit_evidence`, `audit_claims`, `audit_findings`, `agent_telemetry`, and keyword tracking tables.
- `external_authority.db`: Created by `app/connectors/authority/store.py` (`ExternalStore.__init__` line 26) running SQL migrations `001_external_authority.sql` and `002_keyword_tracking.sql`. Stores provider connections, encrypted credentials, snapshots, records, and duplicated keyword tracking tables.
- `geo_aeo_pipeline.db`: Created by `app/geo/pipeline_store.py:30` storing `geo_queries` and `geo_snapshots`.
- In-memory dicts: `backend/app/api/routes/platform/workspaces.py:35-37` defines `_WORKSPACES_STORE = {}`, `_DOMAINS_STORE = {}`, and `_DOMAIN_RUNS_STORE = {}` instead of persisting to a database.

### 1.3 Multi-Tenancy Leaks & `org_default` Fallbacks
- `backend/app/orchestration/orchestrator.py:1537`: `project_id=getattr(run, "org_id", None) or "org_default"` — external authority attachment silently pulls authority records from `"org_default"` if `run.org_id` is missing.
- `backend/app/api/routes/integrations/google.py:43` & `line 175`: `org_id = user.org_id if user else "org_default"` — unauthenticated requests read and probe connectors belonging to `"org_default"`.
- `backend/app/domain/models.py`: Lines 125, 333, 2609, 2716, 2733 default `org_id` to `"org_default"` and `workspace_id` to `"ws_default"` on `Integration`, `Finding`, `CompetitorBakeoffRun`, `RadarTarget`, and `AnalysisRun`.
- `backend/app/orchestration/orchestrator.py:99`: `create_run(..., org_id: str = "org_default", ...)` defaults to `"org_default"`.
- `backend/app/db/repository.py:183-197`: `list_runs(org_id: Optional[str] = None)`: If `org_id` is None, runs `SELECT * FROM audits` without tenant filtering.

### 1.4 Test Suite Import Failure
- Running `pytest tests/test_audit_persistence_and_checkpoints.py` failed with:
  `ModuleNotFoundError: No module named 'app.persistence.models'`
  Trace: `test_audit_persistence_and_checkpoints.py:9` -> `from app.persistence.repository import AuditRepository` -> `app/persistence.py:11` (`from app.db import ..., repository`) -> `app/db/repository.py:18` (`from app.core.config import settings`) -> `app.core` -> `app.domain` -> `app/domain/scoring/score_explanations.py:6` (`from app.persistence.models import ScoreExplanation, ScoreExplanationDimension`).
  At that moment, `sys.modules["app.persistence.models"]` has not executed yet because it is on line 19 of `app/persistence.py`.
- Running `pytest tests/test_external_authority.py` failed with:
  `ModuleNotFoundError: No module named 'app.external_authority'`
  Because `app.connectors` was not pre-imported to populate `sys.modules["app.external_authority*"]`.
- Verified Fix: When pre-loading `app.domain` and `app.connectors`:
  - `tests/test_audit_persistence_and_checkpoints.py` -> 5 passed (100%).
  - `tests/test_enterprise_schema_and_cas.py` -> 4 passed (100%).
  - `tests/test_external_authority.py` -> 16 passed (100%).
  - `tests/test_audit_persistence_and_restore.py` -> 2 passed (100%).

---

## 2. Logic Chain

1. **Premise**: `backend/app/db/session.py` defines `MockSession` to prevent import crashes when SQLAlchemy is unavailable.
   **Observation**: `MockSession` methods silently discard writes (`add -> pass`, `commit -> conn.commit()` on empty queries) and return empty lists for queries.
   **Inference**: Any database failure or dependency issue fails silently, resulting in phantom execution and data loss.
   **Remediation**: Remove `MockSession` entirely, enforce `pool_pre_ping=True`, and fail fast on engine connection failures during startup.

2. **Premise**: The application splits relational data into 4 SQLite files (`dristik.db`, `dristik_audits.db`, `external_authority.db`, `geo_aeo_pipeline.db`).
   **Observation**: Entities like `organizations`, `audits`, and keyword tracking tables are duplicated across stores, while `workspaces` and `domains` exist only in in-memory dictionaries.
   **Inference**: Data between stores cannot be queried transactionally, schema integrity cannot be enforced via foreign keys, and restarting the service wipes workspace domains.
   **Remediation**: Establish a unified SQLAlchemy relational schema mapped to a single `DATABASE_URL` managed via Alembic migrations, supporting both PostgreSQL in production and SQLite in test environments.

3. **Premise**: Multi-tenant isolation requires complete scoping of data and operations to an authenticated tenant.
   **Observation**: Models and services systematically fall back to `"org_default"` and `"ws_default"`. `google.py` allows unauthenticated callers to query `"org_default"` credentials, and `orchestrator.py:1537` attaches `"org_default"` authority data when `run.org_id` is missing.
   **Inference**: Fallback to `"org_default"` creates data leakage across tenants and allows unauthorized requests to pollute the demo tenant.
   **Remediation**: Eliminate all `"org_default"` and `"ws_default"` defaults. Require valid tenant context, reject unauthorized access with `403 Forbidden` / `401 Unauthorized`, and leave authority data unattached if tenant context is missing.

4. **Premise**: CI and local test harnesses rely on `pytest tests/` passing 2,248 tests.
   **Observation**: Pytest collection currently breaks on `ModuleNotFoundError` due to an import cycle between `app.persistence` and `app.domain.scoring.score_explanations`.
   **Inference**: Fixing `backend/app/domain/scoring/score_explanations.py:6` to import from `app.db.models.audit` and ensuring compatibility shims are initialized in `backend/conftest.py` restores 100% pass rates across persistence, CAS, and authority test suites.

---

## 3. Caveats

- **Existing Demo Data**: `backend/scripts/enrich_demo_data.py` currently seeds records specifically under `org_id = 'org_default'`. While production must eliminate `"org_default"` fallbacks for real tenant workflows, developer demo seeding scripts should explicitly specify an organization fixture rather than relying on silent fallbacks.
- **Production PostgreSQL Migration**: Running against a live PostgreSQL instance requires installing `psycopg2-binary` or `asyncpg` and configuring connection credentials via `DATABASE_URL=postgresql://...`.
- **Database Table Naming**: Existing models in `backend/app/db/models/` use table names `audit_runs`, `crawl_pages`, `evidence`, `findings`, while `AuditRepository` uses `audits`, `audit_pages`, `audit_evidence`, `audit_findings`. Unification must align either repository queries or table mappings.

---

## 4. Conclusion

Phase 1 investigation is complete and actionable:
1. **Persistence**: Remove `MockSession` in `session.py`, declare `DATABASE_URL` in `Settings`, and consolidate the 4 SQLite stores into a unified PostgreSQL/SQLite schema managed via Alembic.
2. **Multi-Tenancy**: Eliminate all `"org_default"` and `"ws_default"` literals, enforce `org_id` and `workspace_id` parameters across models and repositories, and return `403 Forbidden` for tenant-less or cross-tenant requests.
3. **Test Suite**: Break the circular import in `app.domain.scoring.score_explanations` / `app.persistence.py` and register compatibility shims in `backend/conftest.py` to ensure all 2,248 tests pass cleanly.

---

## 5. Verification Method

### 5.1 Verification Commands
Run from `/Users/sayantande/Downloads/dristik-main/backend`:
```bash
# 1. Verify RBAC and Auth tests
pytest tests/test_auth_rbac.py -v

# 2. Verify Workspace hierarchy tests
pytest tests/test_workspace_hierarchy_routes.py -v

# 3. Verify Persistence, Checkpoints, and CAS tests (with pre-imported shims)
python3.12 -c "import app.domain; import app.connectors; import pytest; exit(pytest.main(['tests/test_audit_persistence_and_checkpoints.py', 'tests/test_enterprise_schema_and_cas.py', 'tests/test_audit_persistence_and_restore.py', 'tests/test_external_authority.py']))"
```

### 5.2 Files to Inspect
- Report: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_survey_3/survey_phase1_report.md`
- Database session: `backend/app/db/session.py` (lines 1-74)
- Config: `backend/app/core/config.py` (lines 287, 427)
- Repositories: `backend/app/db/repository.py`, `backend/app/identity/store.py`, `backend/app/connectors/authority/store.py`
- Tenancy fallbacks: `backend/app/domain/models.py`, `backend/app/orchestration/orchestrator.py:1537`, `backend/app/api/routes/integrations/google.py:43, 175`
- Circular import: `backend/app/persistence.py:11`, `backend/app/domain/scoring/score_explanations.py:6`

### 5.3 Invalidation Conditions
- If `pytest tests/test_audit_persistence_and_checkpoints.py` fails after updating `conftest.py` and `score_explanations.py`.
- If removing `MockSession` causes runtime errors under normal SQLAlchemy operations.
- If removing `"org_default"` breaks authenticated user audit flows where `user.org_id` is properly populated.
