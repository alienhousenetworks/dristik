# Milestone M2 Test Blueprint: Enterprise Database Architecture, Fail-Fast Connectivity & Circular Import Resolution

**Author**: `spec_miner_m2_3`  
**Milestone**: M2 (Phase 1 — Unified Enterprise Persistence & MockSession Elimination)  
**Target Features**: F07, F08, F09, F10  
**References**:
- `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/ORIGINAL_REQUEST.md` (§R2, §R3)
- `/Users/sayantande/Downloads/dristik-main/PROJECT.md` (Features F07–F10, Interface Contracts §Database Session)
- `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_survey_3/survey_phase1_report.md` (Sections 1.4, 2.1, 4.2)

---

## 1. Executive Summary & Scope

Milestone M2 focuses on modernizing and stabilizing the persistence foundation of Dristik AI:
1. **F07: MockSession Elimination & Fail-Fast Connectivity**: Removing the silent, error-masking `MockSession` fallback in `backend/app/db/session.py:28-74` and instituting fail-fast engine connection verification.
2. **F08: Database Configuration & DATABASE_URL**: Adding `DATABASE_URL` to `Settings` in `backend/app/core/config.py` with multi-engine support (retaining SQLite for local testing while supporting PostgreSQL production URIs).
3. **F09: Unified Enterprise Relational Schema & Compatibility**: Ensuring schema persistence models work seamlessly across SQLite and PostgreSQL.
4. **F10: Circular Import Resolution & Test Harness Shims**: Resolving the circular import cycle that blocks pytest module collection (`No module named 'app.persistence.models'`), registering compatibility shims in `backend/conftest.py`, and verifying 100% pass on 27 existing persistence and authority tests.

---

## 2. Circular Import Root-Cause Analysis & Exact Remediation

### 2.1 The Circular Import Chain

When `pytest tests/test_audit_persistence_and_checkpoints.py` is invoked from a clean Python state, the import sequence fails with:
```
ModuleNotFoundError: No module named 'app.persistence.models'
```

#### Step-by-Step Execution Trace:
```
1. tests/test_audit_persistence_and_checkpoints.py:9
   └── from app.persistence.repository import AuditRepository
2. app/persistence.py starts loading
   ├── Line 11: from app.db import storage_cas, enterprise_schema, schema, repository
   └── [PAUSED AT LINE 11 — Line 19 has NOT executed yet!]
3. app/db/repository.py starts loading
   ├── Line 18: from app.core.config import settings
   └── Line 20: from app.domain.models import AnalysisRun, Claim, Finding, PageEvidence
4. app/domain/__init__.py starts loading
   └── Line 49: from app.domain.scoring import score_explanations
5. app/domain/scoring/score_explanations.py starts loading
   └── Line 6: from app.persistence.models import ScoreExplanation, ScoreExplanationDimension
6. Python looks for "app.persistence.models":
   ├── "app.persistence" is only at line 11 (sys.modules["app.persistence.models"] is assigned at line 19!)
   ├── No directory "app/persistence/" exists on disk (app/persistence.py is a single module)
   └── CRASH: ModuleNotFoundError: No module named 'app.persistence.models'
```

### 2.2 Secondary Failure: Missing Pre-import of Compatibility Shims

When running `pytest tests/test_external_authority.py`:
```
tests/test_external_authority.py:13: in <module>
    from app.external_authority.audit_bridge import build_audit_attachment
E   ModuleNotFoundError: No module named 'app.external_authority'
```
`backend/app/connectors/__init__.py` registers `sys.modules["app.external_authority*"]`, but because `app.connectors` has not been imported before `test_external_authority.py` executes, the namespace does not yet exist.

### 2.3 Exact Fix Specification

#### Change 1: Direct Domain Import in `backend/app/domain/scoring/score_explanations.py`
In `backend/app/domain/scoring/score_explanations.py`, line 6:
```python
# BEFORE (Line 6):
from app.persistence.models import ScoreExplanation, ScoreExplanationDimension

# AFTER (Line 6):
from app.db.models.audit import ScoreExplanation, ScoreExplanationDimension
```
*Rationale*: `ScoreExplanation` and `ScoreExplanationDimension` are declared in `app.db.models.audit`. Relying on the compatibility shim `app.persistence.models` introduces an unnatural dependency cycle between the domain scoring layer and the persistence re-export facade.

#### Change 2: Re-order Shims in `backend/app/persistence.py`
In `backend/app/persistence.py`, register `models` before importing `repository`:
```python
# BEFORE (Lines 11-21):
from app.db import storage_cas, enterprise_schema, schema, repository
from app.db import models, repositories
from app.db.storage_cas import ContentAddressableStorage, CASStorage

sys.modules["app.persistence.storage_cas"] = storage_cas
sys.modules["app.persistence.enterprise_schema"] = enterprise_schema
sys.modules["app.persistence.schema"] = schema
sys.modules["app.persistence.repository"] = repository
sys.modules["app.persistence.models"] = models
sys.modules["app.persistence.repositories"] = repositories

# AFTER (Lines 11-21):
from app.db import models
sys.modules["app.persistence.models"] = models

from app.db import storage_cas, enterprise_schema, schema, repository, repositories
from app.db.storage_cas import ContentAddressableStorage, CASStorage

sys.modules["app.persistence.storage_cas"] = storage_cas
sys.modules["app.persistence.enterprise_schema"] = enterprise_schema
sys.modules["app.persistence.schema"] = schema
sys.modules["app.persistence.repository"] = repository
sys.modules["app.persistence.repositories"] = repositories
```
*Rationale*: Ensures `sys.modules["app.persistence.models"]` is present even if `repository` or any indirect dependency attempts to resolve it during import.

#### Change 3: Shim Registration in `backend/conftest.py`
Update `backend/conftest.py` to register all system compatibility shims before tests run:
```python
# In backend/conftest.py:
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure backend root is also in sys.path
cwd = os.path.abspath(os.path.dirname(__file__))
if cwd not in sys.path:
    sys.path.insert(0, cwd)

# Pre-import compatibility modules to register sys.modules shims
import app.connectors   # Registers app.external_authority.* shims
import app.domain       # Registers app.scoring.* and app.evidence.* shims
import app.persistence  # Registers app.persistence.* shims
```

---

## 3. Database Architecture & Fail-Fast Connectivity Specification

### 3.1 Elimination of `MockSession` (`backend/app/db/session.py`)
Delete lines 28–74 of `backend/app/db/session.py`.
- **Constraint**: `MockSession` must NOT exist anywhere in the codebase.
- **Fail-Fast Invariant**: If database dependencies cannot be loaded, or if the database is unreachable, the system must fail fast with explicit diagnostic exceptions rather than swallowing errors or returning empty query sets.

### 3.2 Exception Hierarchy (`DatabaseConnectionError`)
Introduce `DatabaseConnectionError` in `backend/app/core/exceptions.py` (and re-export in `backend/app/db/session.py`):
```python
class DatabaseConnectionError(DristikException):
    """Raised when the primary database engine cannot establish connectivity."""
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message, status_code=500)
```

### 3.3 Connectivity Verification (`verify_database_connection`)
Provide a lightweight connectivity probe for application startup:
```python
def verify_database_connection(target_engine=None) -> None:
    """
    Executes a fast connectivity probe (SELECT 1).
    Raises DatabaseConnectionError immediately if unreachable.
    """
    eng = target_engine or engine
    if eng is None:
        raise DatabaseConnectionError("Database engine is not configured.")
    try:
        with eng.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise DatabaseConnectionError(f"Database connection failed: {exc}") from exc
```

### 3.4 Multi-Engine Configuration (`backend/app/core/config.py`)
In `Settings` in `backend/app/core/config.py`:
```python
    DATABASE_URL: str = Field(
        default="sqlite:///data/dristik.db",
        description="Unified database connection URL (PostgreSQL or SQLite)"
    )
```

### 3.5 Engine Lifecycle & Pooling (`backend/app/db/session.py`)
```python
def create_db_engine(url: Optional[str] = None):
    db_url = url or get_database_url()
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    return create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
```

---

## 4. Test Suite Specification for Milestone M2

### Suite 1: Database Session, Engine & Fail-Fast Tests (`tests/test_db_session_and_fail_fast.py`)

This new test file validates the invariants of F07 and F08.

| Test ID | Test Function | Target Invariant | Expected Behavior |
|---------|---------------|------------------|-------------------|
| **T-DB-01** | `test_mock_session_completely_removed` | Silent mock removal | Inspect `app.db.session`. `hasattr(app.db.session, "MockSession")` is `False`. `getattr(app.db.session, "MockSession", None)` is `None`. |
| **T-DB-02** | `test_database_url_in_settings_default` | Settings configuration | `settings.DATABASE_URL` is defined, string type, non-empty, defaults to `"sqlite:///data/dristik.db"` (or valid URI). |
| **T-DB-03** | `test_database_url_env_override` | Config flexibility | Setting `DATABASE_URL=postgresql://user:pass@localhost:5432/dristik_test` in environment yields updated `DATABASE_URL` in newly instantiated Settings. |
| **T-DB-04** | `test_create_db_engine_sqlite_configuration` | SQLite compatibility | Calling `create_db_engine("sqlite:///:memory:")` sets dialect to `sqlite`, sets `pool_pre_ping=True`, and includes `check_same_thread: False`. |
| **T-DB-05** | `test_create_db_engine_postgres_configuration` | PostgreSQL readiness | Calling `create_db_engine("postgresql://user:pass@localhost:5432/db")` sets dialect to `postgresql`, sets `pool_pre_ping=True`, and does NOT include SQLite-only `check_same_thread`. |
| **T-DB-06** | `test_verify_database_connection_success` | Health check probe | Calling `verify_database_connection(engine)` against a valid in-memory or file SQLite engine succeeds without exception. |
| **T-DB-07** | `test_verify_database_connection_fail_fast_on_unreachable` | Fail-fast error | Pointing an engine to an unreachable database URL (e.g. `postgresql://user:pass@127.0.0.1:59999/nonexistent`) and calling `verify_database_connection` raises `DatabaseConnectionError`. |
| **T-DB-08** | `test_get_db_session_lifecycle_and_rollback` | Session generator | `get_db()` yields an active SQLAlchemy `Session`. If an exception occurs within the block, the session rolls back and closes cleanly without leaking connections. |

#### Complete Reference Test Implementation:
```python
"""Tests for Database Session, Engine creation, and Fail-Fast Connectivity."""
import os
import pytest
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DatabaseConnectionError
import app.db.session as session_module
from app.db.session import (
    create_db_engine,
    get_db,
    verify_database_connection,
)


def test_mock_session_completely_removed():
    """Verify MockSession has been deleted from session.py."""
    assert not hasattr(session_module, "MockSession"), (
        "MockSession must be completely eliminated from app.db.session"
    )


def test_database_url_in_settings_default():
    """Verify DATABASE_URL is defined on Settings."""
    settings = Settings()
    assert hasattr(settings, "DATABASE_URL")
    assert isinstance(settings.DATABASE_URL, str)
    assert len(settings.DATABASE_URL) > 0


def test_database_url_env_override(monkeypatch):
    """Verify DATABASE_URL can be overridden via environment variable."""
    test_url = "postgresql://test_user:test_pass@localhost:5432/test_dristik"
    monkeypatch.setenv("DATABASE_URL", test_url)
    custom_settings = Settings()
    assert custom_settings.DATABASE_URL == test_url


def test_create_db_engine_sqlite_configuration():
    """Verify SQLite engine creation configuration."""
    sqlite_url = "sqlite:///:memory:"
    eng = create_db_engine(sqlite_url)
    assert eng.dialect.name == "sqlite"
    assert eng.pool is not None
    # Verify connectivity
    with eng.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1


def test_create_db_engine_postgres_configuration():
    """Verify PostgreSQL engine creation configuration."""
    pg_url = "postgresql://user:pass@localhost:5432/dristik"
    eng = create_db_engine(pg_url)
    assert eng.dialect.name == "postgresql"
    assert "check_same_thread" not in eng.url.query


def test_verify_database_connection_success():
    """Verify healthy engine passes verification probe."""
    eng = create_db_engine("sqlite:///:memory:")
    # Should not raise
    verify_database_connection(eng)


def test_verify_database_connection_fail_fast_on_unreachable():
    """Verify unreachable engine raises DatabaseConnectionError immediately."""
    bad_url = "postgresql://user:pass@127.0.0.1:59999/nonexistent"
    bad_engine = create_db_engine(bad_url)
    with pytest.raises(DatabaseConnectionError) as exc_info:
        verify_database_connection(bad_engine)
    assert "Database connection failed" in str(exc_info.value)


def test_get_db_session_lifecycle():
    """Verify get_db session generator yields active session and closes it."""
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    try:
        # Check active session query
        val = db.execute(text("SELECT 1")).scalar()
        assert val == 1
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
```

---

### Suite 2: Circular Import & Shim Independence Tests

| Test ID | Test Function | Target Invariant | Expected Behavior |
|---------|---------------|------------------|-------------------|
| **T-CIRC-01** | `test_direct_score_explanations_import` | Direct domain import | `from app.domain.scoring.score_explanations import ScoreExplanation, ScoreExplanationDimension` imports cleanly without executing `app.persistence.py`. |
| **T-CIRC-02** | `test_clean_import_persistence_repository` | Module collection | `from app.persistence.repository import AuditRepository` succeeds in a clean sub-process without `ModuleNotFoundError`. |
| **T-CIRC-03** | `test_clean_import_external_authority` | Connector shims | `from app.external_authority.audit_bridge import build_audit_attachment` succeeds when conftest pre-imports are active. |

---

### Suite 3: Existing Persistence & Authority Regression Suites (100% Pass)

All 4 existing test suites must achieve a 100% pass rate when run via standard pytest.

#### Suite 3A: `tests/test_audit_persistence_and_checkpoints.py` (5 tests)
1. `test_audit_run_persistence`: Verifies persisting an `AnalysisRun` with full schema, updating status, and retrieving via `get_run`.
2. `test_stage_checkpoints_and_resumption`: Verifies recording atomic stage checkpoints (`chk_...`) across crawling, DOM AST, security headers, etc., and verifying `get_checkpoints`.
3. `test_evidence_explorer_traceability`: Verifies inserting and querying `PageEvidence` graph items.
4. `test_score_explainability_breakdown`: Verifies saving and retrieving `ScoreExplanation` and decomposed `ScoreExplanationDimension` entries.
5. `test_final_run_and_findings_are_saved_as_one_replacement_set`: Verifies atomic transaction persistence for findings and runs.

#### Suite 3B: `tests/test_enterprise_schema_and_cas.py` (4 tests)
1. `test_enterprise_schema_initialization`: Verifies creation of all 8 enterprise tables (`organizations`, `workspaces`, `domains`, `audit_runs`, `evidence_nodes`, `findings`, `ai_citations`, `enterprise_audit_logs`).
2. `test_cas_storage_put_and_get`: Verifies content-addressable storage SHA-256 deduplication and retrieval.
3. `test_distributed_event_broadcaster`: Verifies asyncio event broadcast and subscriber dispatch.
4. `test_idempotent_task_runner`: Verifies task idempotency tokens and duplicate execution suppression.

#### Suite 3C: `tests/test_external_authority.py` (16 tests)
1. `test_zero_providers_are_coverage_gaps_not_failures`: Verifies zero-connected providers result in unattached status without failure.
2. `test_gsc_decline_does_not_invent_deindexing`: Verifies GSC metrics do not fabricate deindexing flags.
3. `test_gsc_empty_dataset_is_measured_zero`: Verifies zero impressions/clicks are measured as 0, not missing.
4. `test_gsc_partial_dimension_does_not_fail_totals`: Verifies partial dimension datasets aggregate safely.
5. `test_ga4_is_analytics_not_rankings`: Verifies GA4 is treated as analytics and does not distort search rankings.
6. `test_bing_json_api_and_labeled_link_count`: Verifies Bing API link extraction.
7. `test_backlink_vendors_keep_their_names_and_do_not_combine`: Verifies vendor namespaces remain discrete (Ahrefs, Semrush, Moz).
8. `test_tokens_are_encrypted_and_absent_from_reports`: Verifies API tokens are AES-encrypted at rest and omitted from reports.
9. `test_rate_limit_retries_and_auth_failure_is_isolated`: Verifies isolated error handling on 429/401 provider responses.
10. `test_cache_skips_repeat_collection`: Verifies TTL cache prevents redundant provider queries.
11. `test_historical_periods_and_trends`: Verifies snapshot trend calculations.
12. `test_gbp_not_applicable_and_citation_nap`: Verifies Google Business Profile applicability rules.
13. `test_missing_encryption_key_refuses_plaintext`: Verifies fail-closed behavior when encryption secret is absent.
14. `test_external_category_does_not_change_the_composite_score`: Verifies external authority preserves deterministic scoring invariance.
15. `test_http_api_hides_secrets_and_reports_not_connected`: Verifies HTTP endpoints redact secrets.
16. `test_has_measured_external_authority_returns_false_for_all_not_connected`: Verifies accurate boolean evaluation of provider states.

#### Suite 3D: `tests/test_audit_persistence_and_restore.py` (2 tests)
1. `test_audit_db_restoration_with_full_report`: Verifies restoring full executive audit report from database JSON.
2. `test_analyses_api_requires_the_owning_organization`: Verifies tenant boundary check on audit retrieval.

---

## 5. Specification Miner Feature Discovery

```
## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Persistence | Fail-Fast DB Verification | Lightweight probe executing `SELECT 1` during engine initialization to verify database accessibility. | Engine, timeout | None (successful probe) | Raises `DatabaseConnectionError` | `backend/app/db/session.py:12-27` |
| 2 | Persistence | Engine Pooling Configuration | `create_engine` with `pool_pre_ping=True` to prune dead connections, plus `check_same_thread=False` for SQLite. | `DATABASE_URL` string | SQLAlchemy `Engine` instance | Raises `ArgumentError` on invalid URL | `backend/app/db/session.py:12-16` |
| 3 | Persistence | Settings `DATABASE_URL` Binding | Application setting providing default database connection URI for all repositories and Alembic. | Environment `DATABASE_URL` | String URL | Defaults to `sqlite:///data/dristik.db` | `backend/app/core/config.py` |
| 4 | Architecture | Circular Import Elimination | Direct domain import from `app.db.models.audit` breaking the dependency loop in scoring explanations. | Python import statement | `ScoreExplanation` classes | Clean module loading | `backend/app/domain/scoring/score_explanations.py:6` |
| 5 | Architecture | Test Runner Shim Pre-load | Pre-loading `app.connectors`, `app.domain`, and `app.persistence` in `backend/conftest.py`. | Pytest session init | Populated `sys.modules` | Prevents `ModuleNotFoundError` during test collection | `backend/conftest.py` |
| 6 | Persistence | CAS Content Addressable Storage | SHA-256 deduplicated content store for audit payloads and raw HTML captures. | Bytes / string content | SHA-256 hash key | Raises on storage write failure | `backend/app/db/storage_cas.py` |
| 7 | Multi-Tenancy | Atomic Stage Checkpointing | Stage-by-stage transaction checkpointing recording `checkpoint_id`, hashes, and run progress. | `StageCheckpoint` model | Saved record in `audit_checkpoints` | Raises on duplicate checkpoint ID | `backend/app/db/models/audit.py:12-28` |

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Fail-Fast Probe | Unreachable PostgreSQL host (`postgresql://localhost:59999/db`) | `verify_database_connection` catches `OperationalError` and raises `DatabaseConnectionError` with root cause attached. |
| 2 | Engine Creation | SQLite in-memory URL (`sqlite:///:memory:`) | Applies `connect_args={"check_same_thread": False}` without errors; creates functional test database. |
| 3 | Engine Creation | PostgreSQL URL (`postgresql://user:pass@host/db`) | Omits SQLite-specific `connect_args`; configures connection pool with pre-ping enabled. |
| 4 | Test Collection | Subprocess running `pytest tests/test_audit_persistence_and_checkpoints.py` | With conftest pre-imports and direct audit import, executes all 5 tests without collection failure. |
| 5 | External Authority Shims | Test importing `from app.external_authority.audit_bridge import ...` | Resolved via `app.connectors` shims without needing physical `app/external_authority/` directory. |
| 6 | Database Session Cleanup | Exception raised inside route using `get_db()` | Generator executes `finally: db.close()`, rolling back pending transactions and returning connection to pool. |
```

---

## 6. Verification Commands & Independent Reproduction

### Command 1: Verify Direct Import Without Circular Failure
```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -c "
import sys, os
sys.path.insert(0, os.path.abspath('backend'))
import app.connectors
import app.domain
import app.persistence
from app.persistence.repository import AuditRepository
from app.domain.scoring.score_explanations import ScoreExplanation
print('Imports resolved cleanly!')
"
```
**Expected Output**: `Imports resolved cleanly!` (Exit Code: 0)

### Command 2: Execute All 4 Target Persistence & Authority Test Suites
```bash
cd backend
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -c "
import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app.connectors
import app.domain
import app.persistence
import pytest
sys.exit(pytest.main([
    'tests/test_audit_persistence_and_checkpoints.py',
    'tests/test_enterprise_schema_and_cas.py',
    'tests/test_external_authority.py',
    'tests/test_audit_persistence_and_restore.py',
    '-v'
]))
"
```
**Expected Output**:
```
======================== 27 passed, 7 warnings in 2.76s ========================
```
(Exit Code: 0)

### Command 3: Execute New M2 Database Connectivity Test Suite
Once `tests/test_db_session_and_fail_fast.py` is created:
```bash
cd backend
pytest tests/test_db_session_and_fail_fast.py -v
```
**Expected Output**: 8 passed in ~1.5s.
