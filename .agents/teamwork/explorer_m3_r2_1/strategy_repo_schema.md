# Remediation Strategy: Defect 1 — AuditRepository `workspace_id` Schema Mismatch

**Author**: `explorer_m3_r2_1` (Teamwork Explorer)  
**Parent Agent**: `c6f6f3f2-acb1-4d19-b16f-9f0aba77d9f4`  
**Target Milestone**: M3 Remediation (Domain, Repository, and Pipeline Tenant Isolation)  
**Target Files**:
- `backend/app/db/schema.py`
- `backend/app/db/repository.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/tests/test_tenant_isolation.py`

---

## 1. Executive Summary

During Milestone M3, multi-tenant scoping was introduced to `AuditRepository.list_runs` by adding `workspace_id: Optional[str] = None` and executing:
```sql
SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?
```
However, the underlying database schema definitions (`SQLITE_SCHEMA` and `POSTGRES_SCHEMA` in `backend/app/db/schema.py`) were never updated to include the `workspace_id` column on the `audits` table. Furthermore, `AuditRepository.save_run` never writes `run.workspace_id` into the database, and `orchestrator.get_run()` drops `workspace_id` when hydrating `AnalysisRun` instances from the database.

Consequently:
1. Calling `repo.list_runs(org_id, workspace_id="ws_1")` unconditionally crashes at runtime with:
   `sqlite3.OperationalError: no such column: workspace_id`
2. Audit runs saved with a workspace identifier lose their workspace binding upon persistent serialization.
3. Existing SQLite databases on disk (such as `data/dristik_audits.db`) cannot be updated by `CREATE TABLE IF NOT EXISTS`, requiring an in-place column migration check.

This strategy document specifies the precise, backward-compatible remediation across the schema, repository persistence layer, domain mapping helper, and test verification suite.

---

## 2. Root Cause Analysis

### 2.1 Empirical Verification of Failure
Executing `repo.list_runs('tenant_A', workspace_id='ws_1')` on a repository initialized from `SQLITE_SCHEMA` raises:
```text
sqlite3.OperationalError: no such column: workspace_id
```
In `backend/app/db/repository.py:201-205`:
```python
if workspace_id:
    cur = conn.execute(
        "SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?",
        (clean_org_id, workspace_id, limit),
    )
```
The query references column `workspace_id`, which does not exist in `audits`.

### 2.2 Persistence Gap in `save_run`
In `backend/app/db/repository.py:85-135`, `save_run` executes:
```sql
INSERT INTO audits (
    analysis_id, org_id, user_id, website_url, domain, status, progress,
    stage, max_pages, score_overall, score_human, score_google,
    score_ai_readiness, score_ai_visibility, score_band, started_at,
    completed_at, input_hash, output_hash, raw_report_json, error_message
) VALUES (...)
```
Notice `workspace_id` is omitted from `INSERT`, `ON CONFLICT DO UPDATE SET`, and the bound `params` dictionary. Even if `run.workspace_id` is populated on the domain object, it is silently dropped upon persistence.

### 2.3 Hydration Gap in `orchestrator.get_run`
In `backend/app/orchestration/orchestrator.py:160-173`, when retrieving a stored run from SQLite:
```python
run = AnalysisRun(
    analysis_id=stored["analysis_id"],
    org_id=stored["org_id"],
    # workspace_id is omitted; defaults to None!
    website_url=stored["website_url"],
    ...
)
```
Because `AuditRepository` lacks a centralized `_row_to_run` mapping helper, callers duplicate row deserialization logic and inadvertently drop attributes like `workspace_id`.

### 2.4 Existing Database Backward-Compatibility Gap
`AuditRepository._init_sqlite()` calls:
```python
conn.executescript(SQLITE_SCHEMA)
```
`CREATE TABLE IF NOT EXISTS audits (...)` does **not** alter an existing SQLite table if it already exists on disk. Any deployment with an existing database file will crash on `save_run` or `list_runs` unless an automatic column check/migration is executed on startup.

---

## 3. Remediation Strategy & Architecture

### 3.1 Schema Definition (`backend/app/db/schema.py`)

1. **`SQLITE_SCHEMA`**:
   - Add `workspace_id TEXT` (nullable) immediately following `org_id TEXT NOT NULL,`.
   - Add index: `CREATE INDEX IF NOT EXISTS idx_audits_workspace ON audits(workspace_id);`
   - Add composite index: `CREATE INDEX IF NOT EXISTS idx_audits_org_workspace ON audits(org_id, workspace_id);`
   The composite index optimizes `SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?` by providing direct B-tree lookup without scanning.

2. **`POSTGRES_SCHEMA`**:
   - Add `workspace_id VARCHAR(64)` immediately following `org_id VARCHAR(64) NOT NULL,`.
   - Add composite index: `CREATE INDEX IF NOT EXISTS idx_audits_org_workspace ON audits(org_id, workspace_id);`

### 3.2 In-Place Migration for Existing SQLite Databases (`AuditRepository._init_sqlite`)

To ensure 100% backward compatibility for existing SQLite database files without requiring manual schema drop or data loss:
- Implement `self._migrate_sqlite(conn)` called within `_init_sqlite()` under the lock:
```python
def _migrate_sqlite(self, conn: sqlite3.Connection) -> None:
    """Applies non-destructive schema migrations for existing SQLite databases."""
    try:
        cur = conn.execute("PRAGMA table_info(audits)")
        columns = {row[1] for row in cur.fetchall()}
        if columns and "workspace_id" not in columns:
            conn.execute("ALTER TABLE audits ADD COLUMN workspace_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_org_workspace ON audits(org_id, workspace_id)")
    except Exception as e:
        logger.warning(f"Failed to check or migrate audits table schema: {e}")
```
SQLite supports `ALTER TABLE <tbl> ADD COLUMN <col> <type>` natively. This operation is idempotent and instantaneous.

### 3.3 Persistence in `AuditRepository.save_run`

Update `save_run` to persist `run.workspace_id`:
1. Include `workspace_id` in `INSERT INTO audits`:
   ```sql
   INSERT INTO audits (
       analysis_id, org_id, workspace_id, user_id, website_url, domain, status, progress,
       stage, max_pages, score_overall, score_human, score_google,
       score_ai_readiness, score_ai_visibility, score_band, started_at,
       completed_at, input_hash, output_hash, raw_report_json, error_message
   ) VALUES (
       :analysis_id, :org_id, :workspace_id, :user_id, :website_url, :domain, :status, :progress,
       :stage, :max_pages, :score_overall, :score_human, :score_google,
       :score_ai_readiness, :score_ai_visibility, :score_band, :started_at,
       :completed_at, :input_hash, :output_hash, :raw_report_json, :error_message
   )
   ON CONFLICT(analysis_id) DO UPDATE SET
       workspace_id = COALESCE(excluded.workspace_id, audits.workspace_id),
       status = excluded.status,
       progress = excluded.progress,
       ...
   ```
2. Bind in `params`:
   ```python
   "workspace_id": getattr(run, "workspace_id", None),
   ```
Using `COALESCE(excluded.workspace_id, audits.workspace_id)` guarantees that updating an existing audit with progress or report updates will not inadvertently overwrite an established `workspace_id` with `None`.

### 3.4 Clean Querying & Validation in `AuditRepository.list_runs`

Enforce strict multi-tenant boundary checks in `list_runs`:
1. **`org_id` validation**:
   - Rejects empty, whitespace, and forbidden defaults: `{"org_default", "default", "ws_default"}`.
2. **`workspace_id` validation**:
   - If `workspace_id is not None`:
     - Reject if not `isinstance(workspace_id, str)`.
     - Reject if whitespace-only: `not workspace_id.strip()` -> `ValueError("workspace_id cannot be whitespace-only.")`
     - Reject if forbidden default: `workspace_id.strip() in ("ws_default", "org_default", "default")` -> `ValueError(f"Insecure fallback workspace '{workspace_id.strip()}' is forbidden.")`
     - Strip valid string: `clean_workspace_id = workspace_id.strip()`
3. **Execution**:
   - If `clean_workspace_id`:
     `SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?`
   - Else:
     `SELECT * FROM audits WHERE org_id = ? ORDER BY created_at DESC LIMIT ?`
4. **Return type**:
   - Returns `List[Dict[str, Any]]`: `[dict(r) for r in cur.fetchall()]`.
   - All existing callers (`analyses.py`, `service.py`, tests) consume dictionaries via key indexing (e.g., `row["analysis_id"]`). `dict(r)` automatically includes `"workspace_id"`, ensuring full caller compatibility.

### 3.5 Domain Model Translation via `_row_to_run`

Add `_row_to_run` to `AuditRepository`:
```python
@staticmethod
def _row_to_run(row: sqlite3.Row | Dict[str, Any]) -> AnalysisRun:
    """Converts a database row or dict from the audits table into an AnalysisRun domain model."""
    d = dict(row)
    report_obj = None
    raw_json = d.get("raw_report_json")
    if raw_json:
        try:
            from app.domain.models import ExecutiveReport
            report_obj = ExecutiveReport.model_validate_json(raw_json)
        except Exception as e:
            logger.warning(f"Failed to deserialize report for {d.get('analysis_id')}: {e}")

    status_val = d.get("status", "queued")
    stage_enum = AnalysisStage.QUEUED
    for s in AnalysisStage:
        if s.value == status_val or str(s) == status_val:
            stage_enum = s
            break

    return AnalysisRun(
        analysis_id=d["analysis_id"],
        org_id=d["org_id"],
        workspace_id=d.get("workspace_id"),
        website_url=d["website_url"],
        status=stage_enum,
        progress_percentage=d.get("progress", 100 if report_obj else 0),
        current_step=d.get("stage", "Completed" if report_obj else "Queued"),
        score_band=d.get("score_band") or "Pending Evaluation",
        created_at=d.get("started_at") or d.get("created_at") or datetime.now(timezone.utc).isoformat(),
        updated_at=d.get("completed_at") or d.get("started_at") or datetime.now(timezone.utc).isoformat(),
        completed_at=d.get("completed_at"),
        report=report_obj,
    )
```

In `backend/app/orchestration/orchestrator.py:get_run`:
Simplify fallback loading:
```python
stored = self.repository.get_run(analysis_id)
if stored:
    run = self.repository._row_to_run(stored)
    self.runs[analysis_id] = run
    return run
```
This guarantees `workspace_id` is preserved whenever a run is restored from persistent storage.

---

## 4. Concrete Code Snippets & Diff Specifications

### 4.1 Changes to `backend/app/db/schema.py`

```python
<<<<
CREATE TABLE IF NOT EXISTS audits (
    analysis_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
====
CREATE TABLE IF NOT EXISTS audits (
    analysis_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    workspace_id TEXT,
    user_id TEXT NOT NULL,
>>>>
```

And in SQLite indexes:
```python
<<<<
CREATE INDEX IF NOT EXISTS idx_audits_org ON audits(org_id);
CREATE INDEX IF NOT EXISTS idx_audits_domain ON audits(domain);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);
====
CREATE INDEX IF NOT EXISTS idx_audits_org ON audits(org_id);
CREATE INDEX IF NOT EXISTS idx_audits_domain ON audits(domain);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);
CREATE INDEX IF NOT EXISTS idx_audits_workspace ON audits(workspace_id);
CREATE INDEX IF NOT EXISTS idx_audits_org_workspace ON audits(org_id, workspace_id);
>>>>
```

And in `POSTGRES_SCHEMA`:
```python
<<<<
CREATE TABLE IF NOT EXISTS audits (
    analysis_id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
====
CREATE TABLE IF NOT EXISTS audits (
    analysis_id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL,
    workspace_id VARCHAR(64),
    user_id VARCHAR(64) NOT NULL,
>>>>
```
And Postgres index:
```python
CREATE INDEX IF NOT EXISTS idx_audits_org_workspace ON audits(org_id, workspace_id);
```

### 4.2 Changes to `backend/app/db/repository.py`

#### A. Database Initialization & Migration
```python
<<<<
    def _init_sqlite(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._lock:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.executescript(SQLITE_SCHEMA)
                conn.commit()
====
    def _init_sqlite(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._lock:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.executescript(SQLITE_SCHEMA)
                self._migrate_sqlite(conn)
                conn.commit()

    def _migrate_sqlite(self, conn: sqlite3.Connection) -> None:
        """Applies backward-compatible column migrations for existing SQLite databases."""
        try:
            cur = conn.execute("PRAGMA table_info(audits)")
            columns = {row[1] for row in cur.fetchall()}
            if columns and "workspace_id" not in columns:
                conn.execute("ALTER TABLE audits ADD COLUMN workspace_id TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_org_workspace ON audits(org_id, workspace_id)")
        except Exception as e:
            logger.warning(f"Failed to check or alter audits table schema: {e}")
>>>>
```

#### B. `save_run` Persistence
```python
<<<<
        sql = """
        INSERT INTO audits (
            analysis_id, org_id, user_id, website_url, domain, status, progress,
            stage, max_pages, score_overall, score_human, score_google,
            score_ai_readiness, score_ai_visibility, score_band, started_at,
            completed_at, input_hash, output_hash, raw_report_json, error_message
        ) VALUES (
            :analysis_id, :org_id, :user_id, :website_url, :domain, :status, :progress,
            :stage, :max_pages, :score_overall, :score_human, :score_google,
            :score_ai_readiness, :score_ai_visibility, :score_band, :started_at,
            :completed_at, :input_hash, :output_hash, :raw_report_json, :error_message
        )
        ON CONFLICT(analysis_id) DO UPDATE SET
            status = excluded.status,
====
        sql = """
        INSERT INTO audits (
            analysis_id, org_id, workspace_id, user_id, website_url, domain, status, progress,
            stage, max_pages, score_overall, score_human, score_google,
            score_ai_readiness, score_ai_visibility, score_band, started_at,
            completed_at, input_hash, output_hash, raw_report_json, error_message
        ) VALUES (
            :analysis_id, :org_id, :workspace_id, :user_id, :website_url, :domain, :status, :progress,
            :stage, :max_pages, :score_overall, :score_human, :score_google,
            :score_ai_readiness, :score_ai_visibility, :score_band, :started_at,
            :completed_at, :input_hash, :output_hash, :raw_report_json, :error_message
        )
        ON CONFLICT(analysis_id) DO UPDATE SET
            workspace_id = COALESCE(excluded.workspace_id, audits.workspace_id),
            status = excluded.status,
>>>>
```

And in `params`:
```python
<<<<
            "analysis_id": run.analysis_id,
            "org_id": run.org_id,
            "user_id": user_id_val,
====
            "analysis_id": run.analysis_id,
            "org_id": run.org_id,
            "workspace_id": getattr(run, "workspace_id", None),
            "user_id": user_id_val,
>>>>
```

#### C. `list_runs` Querying & Validation
```python
<<<<
    def list_runs(
        self,
        org_id: str,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists recent audit runs strictly partitioned by org_id."""
        if not org_id or not isinstance(org_id, str) or not org_id.strip() or org_id.strip() in ("org_default", "default"):
            raise ValueError("Tenant org_id is required and non-empty for list_runs; unscoped listing or 'org_default' is forbidden.")

        clean_org_id = org_id.strip()
        with self._lock:
            with self._get_conn() as conn:
                if workspace_id:
                    cur = conn.execute(
                        "SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?",
                        (clean_org_id, workspace_id, limit),
                    )
                else:
                    cur = conn.execute(
                        "SELECT * FROM audits WHERE org_id = ? ORDER BY created_at DESC LIMIT ?",
                        (clean_org_id, limit),
                    )
                return [dict(r) for r in cur.fetchall()]
====
    def list_runs(
        self,
        org_id: str,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists recent audit runs strictly partitioned by org_id and optionally workspace_id."""
        if not org_id or not isinstance(org_id, str) or not org_id.strip() or org_id.strip() in ("org_default", "default", "ws_default"):
            raise ValueError("Tenant org_id is required and non-empty for list_runs; unscoped listing or insecure default tenant is forbidden.")

        clean_org_id = org_id.strip()
        clean_workspace_id: Optional[str] = None
        if workspace_id is not None:
            if not isinstance(workspace_id, str):
                raise ValueError("workspace_id must be a string if provided.")
            if not workspace_id.strip():
                raise ValueError("workspace_id cannot be whitespace-only.")
            clean_ws = workspace_id.strip()
            if clean_ws in ("ws_default", "org_default", "default"):
                raise ValueError(f"Insecure fallback workspace '{clean_ws}' is forbidden.")
            clean_workspace_id = clean_ws

        with self._lock:
            with self._get_conn() as conn:
                if clean_workspace_id:
                    cur = conn.execute(
                        "SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?",
                        (clean_org_id, clean_workspace_id, limit),
                    )
                else:
                    cur = conn.execute(
                        "SELECT * FROM audits WHERE org_id = ? ORDER BY created_at DESC LIMIT ?",
                        (clean_org_id, limit),
                    )
                return [dict(r) for r in cur.fetchall()]
>>>>
```

#### D. Helper Method `_row_to_run`
```python
    @staticmethod
    def _row_to_run(row: sqlite3.Row | Dict[str, Any]) -> AnalysisRun:
        """Converts an audit row or dict into an AnalysisRun domain model."""
        d = dict(row)
        report_obj = None
        raw_json = d.get("raw_report_json")
        if raw_json:
            try:
                from app.domain.models import ExecutiveReport
                report_obj = ExecutiveReport.model_validate_json(raw_json)
            except Exception as e:
                logger.warning(f"Failed to deserialize report for {d.get('analysis_id')}: {e}")

        status_val = d.get("status", "queued")
        stage_enum = AnalysisStage.QUEUED
        for s in AnalysisStage:
            if s.value == status_val or str(s) == status_val:
                stage_enum = s
                break

        return AnalysisRun(
            analysis_id=d["analysis_id"],
            org_id=d["org_id"],
            workspace_id=d.get("workspace_id"),
            website_url=d["website_url"],
            status=stage_enum,
            progress_percentage=d.get("progress", 100 if report_obj else 0),
            current_step=d.get("stage", "Completed" if report_obj else "Queued"),
            score_band=d.get("score_band") or "Pending Evaluation",
            created_at=d.get("started_at") or d.get("created_at") or datetime.now(timezone.utc).isoformat(),
            updated_at=d.get("completed_at") or d.get("started_at") or datetime.now(timezone.utc).isoformat(),
            completed_at=d.get("completed_at"),
            report=report_obj,
        )
```

### 4.3 Changes to `backend/app/orchestration/orchestrator.py`

In `AnalysisOrchestrator.get_run`:
```python
<<<<
        # Durable DB fallback
        try:
            stored = self.repository.get_run(analysis_id)
            if stored:
                report_obj = None
                raw_json = stored.get("raw_report_json")
                if raw_json:
                    try:
                        report_obj = ExecutiveReport.model_validate_json(raw_json)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize report for {analysis_id}: {e}")

                status_val = stored["status"]
                stage_enum = AnalysisStage.QUEUED
                for s in AnalysisStage:
                    if s.value == status_val or str(s) == status_val:
                        stage_enum = s
                        break

                run = AnalysisRun(
                    analysis_id=stored["analysis_id"],
                    org_id=stored["org_id"],
                    website_url=stored["website_url"],
                    status=stage_enum,
                    progress_percentage=stored.get("progress", 100 if report_obj else 0),
                    current_step=stored.get("stage", "Completed" if report_obj else "Queued"),
                    score_band=stored.get("score_band") or "Pending Evaluation",
                    created_at=stored.get("started_at") or stored.get("created_at") or datetime.now().isoformat(),
                    updated_at=stored.get("completed_at") or stored.get("started_at") or datetime.now().isoformat(),
                    completed_at=stored.get("completed_at"),
                    report=report_obj
                )
                self.runs[analysis_id] = run
                return run
====
        # Durable DB fallback
        try:
            stored = self.repository.get_run(analysis_id)
            if stored:
                run = self.repository._row_to_run(stored)
                self.runs[analysis_id] = run
                return run
>>>>
```

---

## 5. Test Suite Verification Plan

Add the following 4 tests into `backend/tests/test_tenant_isolation.py` under a dedicated suite header:

```python
# =============================================================================
# Suite 7: T-TI-07 AuditRepository Workspace Scoping and Migration
# =============================================================================

def test_repository_list_runs_with_workspace_id_filtering(isolated_repo):
    """Verifies that list_runs filters accurately by workspace_id without runtime errors."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    
    # Create 2 runs for workspace_alpha
    for i in range(2):
        isolated_repo.save_run(AnalysisRun(
            analysis_id=f"run_alpha_{i}",
            org_id="org_multi",
            workspace_id="ws_alpha",
            website_url=f"https://alpha-{i}.example",
            created_at=now,
            updated_at=now,
        ))
    
    # Create 1 run for workspace_beta in the same org
    isolated_repo.save_run(AnalysisRun(
        analysis_id="run_beta_0",
        org_id="org_multi",
        workspace_id="ws_beta",
        website_url="https://beta.example",
        created_at=now,
        updated_at=now,
    ))

    # Query workspace_alpha
    alpha_runs = isolated_repo.list_runs("org_multi", workspace_id="ws_alpha")
    assert len(alpha_runs) == 2
    assert all(r["workspace_id"] == "ws_alpha" for r in alpha_runs)

    # Query workspace_beta
    beta_runs = isolated_repo.list_runs("org_multi", workspace_id="ws_beta")
    assert len(beta_runs) == 1
    assert beta_runs[0]["workspace_id"] == "ws_beta"

    # Query entire org (workspace_id=None) returns all 3
    all_runs = isolated_repo.list_runs("org_multi")
    assert len(all_runs) == 3


def test_repository_list_runs_rejects_insecure_workspace_defaults(isolated_repo):
    """Verifies that list_runs blocks insecure workspace default identifiers and whitespace."""
    with pytest.raises(ValueError, match="(?i)forbidden|workspace"):
        isolated_repo.list_runs("org_multi", workspace_id="ws_default")
    with pytest.raises(ValueError, match="(?i)forbidden|workspace"):
        isolated_repo.list_runs("org_multi", workspace_id="org_default")
    with pytest.raises(ValueError, match="(?i)whitespace|workspace"):
        isolated_repo.list_runs("org_multi", workspace_id="   ")


def test_repository_save_and_row_to_run_hydrates_workspace_id(isolated_repo):
    """Verifies that save_run persists workspace_id and _row_to_run restores it."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    
    run = AnalysisRun(
        analysis_id="run_hydrate_test",
        org_id="org_custom",
        workspace_id="ws_custom_finance",
        website_url="https://finance.example",
        created_at=now,
        updated_at=now,
    )
    isolated_repo.save_run(run)
    
    # get_run dict
    stored_dict = isolated_repo.get_run("run_hydrate_test", org_id="org_custom")
    assert stored_dict is not None
    assert stored_dict["workspace_id"] == "ws_custom_finance"

    # _row_to_run domain model
    restored_run = isolated_repo._row_to_run(stored_dict)
    assert restored_run.analysis_id == "run_hydrate_test"
    assert restored_run.workspace_id == "ws_custom_finance"


def test_repository_backward_compatible_existing_db_migration(tmp_path):
    """Verifies that existing SQLite databases lacking workspace_id column are migrated cleanly."""
    import sqlite3
    db_file = tmp_path / "legacy_audit.db"
    
    # Create legacy table without workspace_id
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
        CREATE TABLE audits (
            analysis_id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            website_url TEXT NOT NULL,
            domain TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()

    # Instantiate AuditRepository on legacy database
    from app.db.repository import AuditRepository
    legacy_repo = AuditRepository(db_path=str(db_file))

    # Verify column was added automatically
    with sqlite3.connect(db_file) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(audits)").fetchall()}
        assert "workspace_id" in cols

    # Verify querying workspace_id succeeds without OperationalError
    results = legacy_repo.list_runs("org_test", workspace_id="ws_test")
    assert results == []
```

---

## 6. Verification Commands & Invalidation Conditions

### Independent Reproduction Command:
```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -c "
import sys, tempfile, os
sys.path.insert(0, 'backend')
from app.db.repository import AuditRepository
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
    db_path = tf.name
try:
    repo = AuditRepository(db_path=db_path)
    res = repo.list_runs('tenant_A', workspace_id='ws_1')
    print('SUCCESS: list_runs with workspace_id returned', res)
except Exception as e:
    print('FAILURE:', type(e), e)
finally:
    if os.path.exists(db_path):
        os.remove(db_path)
"
```

### Full Regression Test Command:
```bash
pytest backend/tests/test_tenant_isolation.py -v
pytest backend/tests/test_audit_persistence_and_restore.py backend/tests/test_audit_persistence_and_checkpoints.py backend/tests/test_enterprise_schema_and_cas.py -v
```

### Invalidation Conditions:
1. If `AuditRepository.list_runs(org_id, workspace_id)` raises `OperationalError: no such column: workspace_id`.
2. If `AuditRepository.save_run(run)` drops `run.workspace_id`.
3. If `orchestrator.get_run()` drops `workspace_id` when loading an audit from persistent SQLite storage.
4. If initializing `AuditRepository` against a pre-existing SQLite database fails or loses existing data.
5. If `list_runs` returns domain model objects instead of `List[Dict[str, Any]]`, breaking dependent caller endpoints (`app/api/routes/audits/analyses.py` and `app/identity/service.py`).
