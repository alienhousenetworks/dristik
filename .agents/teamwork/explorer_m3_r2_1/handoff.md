# Handoff Report — explorer_m3_r2_1: Remediation Strategy for Defect 1

**Agent**: `explorer_m3_r2_1` (Teamwork Explorer)  
**Parent Agent**: `c6f6f3f2-acb1-4d19-b16f-9f0aba77d9f4`  
**Milestone**: M3 Remediation (Domain, Repository, and Pipeline Tenant Isolation)  
**Type**: Hard Handoff (Investigation & Strategy Complete)  
**Strategy Document**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m3_r2_1/strategy_repo_schema.md`  

---

## 1. Observation

1. **Empirical Reproduction of `AuditRepository.list_runs` Crash**:
   Running:
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -c "
   import sys, tempfile, os
   sys.path.insert(0, 'backend')
   from app.db.repository import AuditRepository
   with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
       db_path = tf.name
   try:
       repo = AuditRepository(db_path=db_path)
       repo.list_runs('tenant_A', workspace_id='ws_1')
   finally:
       if os.path.exists(db_path):
           os.remove(db_path)
   "
   ```
   Directly outputs:
   ```text
   sqlite3.OperationalError: no such column: workspace_id
   ```
2. **`audits` Table Schema Missing `workspace_id`**:
   In `backend/app/db/schema.py:14-37`, `SQLITE_SCHEMA` defines `audits` with columns:
   `analysis_id`, `org_id`, `user_id`, `website_url`, `domain`, `status`, `progress`, `stage`, `max_pages`, `score_overall`, `score_human`, `score_google`, `score_ai_readiness`, `score_ai_visibility`, `score_band`, `started_at`, `completed_at`, `input_hash`, `output_hash`, `raw_report_json`, `error_message`, `created_at`.
   Neither `workspace_id` column nor workspace-related indexes exist in `SQLITE_SCHEMA` or `POSTGRES_SCHEMA` (lines 222-245).
3. **`AuditRepository.save_run` Silently Drops `workspace_id`**:
   In `backend/app/db/repository.py:85-135`, `save_run` inserts 21 named parameters into `audits`. `workspace_id` is omitted from `INSERT`, `ON CONFLICT DO UPDATE SET`, and `params`. Empirical execution showed that saving an `AnalysisRun` with `workspace_id="ws_alpha"` results in `repo.get_run()` returning a dictionary without `workspace_id`.
4. **`orchestrator.get_run()` Drops `workspace_id` on DB Fallback**:
   In `backend/app/orchestration/orchestrator.py:160-173`, the DB fallback instantiates `AnalysisRun` directly from `stored` dict without passing `workspace_id=stored.get("workspace_id")`, resulting in any restored run losing its workspace binding.
5. **Existing Database Backward Compatibility Limitation**:
   In `backend/app/db/repository.py:44-50`, `_init_sqlite()` executes `conn.executescript(SQLITE_SCHEMA)`. In SQLite, `CREATE TABLE IF NOT EXISTS` is a no-op if the table already exists. Testing on a pre-existing database file without `workspace_id` confirmed that updating `SQLITE_SCHEMA` alone fails with `sqlite3.OperationalError: table audits has no column named workspace_id` upon `save_run`.
6. **Caller Contract Inspection**:
   In `backend/app/api/routes/audits/analyses.py:165` and `backend/app/identity/service.py:201`, existing callers invoke `repo.list_runs(org_id=...)` and index rows as dictionaries (e.g., `row["analysis_id"]`). Returning `AnalysisRun` domain models instead of `List[Dict[str, Any]]` breaks existing callers with `TypeError: 'AnalysisRun' object is not subscriptable`.

---

## 2. Logic Chain

1. From Observation 1 and 2, `AuditRepository.list_runs` queries `WHERE org_id = ? AND workspace_id = ?`, but the `audits` table lacks `workspace_id`. Therefore, `workspace_id TEXT` must be added to `SQLITE_SCHEMA` and `POSTGRES_SCHEMA` in `backend/app/db/schema.py`, accompanied by a composite index `(org_id, workspace_id)`.
2. From Observation 3, adding the column to the schema is insufficient if `save_run` does not write the value. Therefore, `save_run` in `backend/app/db/repository.py` must include `workspace_id` in the `INSERT` column list, the bound `params` mapping (`run.workspace_id`), and `ON CONFLICT DO UPDATE SET workspace_id = COALESCE(excluded.workspace_id, audits.workspace_id)` so workspace attribution is durably preserved across updates.
3. From Observation 5, pre-existing database files on disk will not receive the new column from `CREATE TABLE IF NOT EXISTS`. Therefore, `_init_sqlite()` must call an idempotent migration helper `_migrate_sqlite()` that inspects `PRAGMA table_info(audits)` and executes `ALTER TABLE audits ADD COLUMN workspace_id TEXT` if missing.
4. From Observation 6, `list_runs` must preserve its return signature of `List[Dict[str, Any]]` to prevent breaking existing endpoints and services, while ensuring `workspace_id` validation rejects forbidden default tenant IDs (`org_default`, `ws_default`, `default`) and whitespace-only strings.
5. From Observation 4, to prevent caller duplication and restore consistency, `AuditRepository` should expose a static helper `_row_to_run(row: sqlite3.Row | Dict[str, Any]) -> AnalysisRun` mapping `workspace_id=d.get("workspace_id")`, allowing `orchestrator.get_run()` to deserialize stored runs cleanly.

---

## 3. Caveats

- **No Caveats**: The remediation does not require destructive database migrations or changes to external dependencies. It preserves backward compatibility for all existing callers and database files on disk.

---

## 4. Conclusion

The strategy for remediating Defect 1 has been formulated, tested against standalone prototypes, and fully documented in:
`/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m3_r2_1/strategy_repo_schema.md`

Summary of required implementation changes:
1. **`backend/app/db/schema.py`**:
   - Add `workspace_id TEXT,` to `SQLITE_SCHEMA` (`audits` table).
   - Add `workspace_id VARCHAR(64),` to `POSTGRES_SCHEMA` (`audits` table).
   - Add composite index `idx_audits_org_workspace ON audits(org_id, workspace_id)` to both schemas.
2. **`backend/app/db/repository.py`**:
   - Add `_migrate_sqlite(self, conn)` to `_init_sqlite()` to dynamically run `ALTER TABLE audits ADD COLUMN workspace_id TEXT` on legacy databases.
   - Update `save_run()` to persist `workspace_id` with `COALESCE(excluded.workspace_id, audits.workspace_id)`.
   - Update `list_runs()` to validate `workspace_id` against forbidden defaults and whitespace, querying `WHERE org_id = ? AND workspace_id = ?` when supplied.
   - Add `_row_to_run(row)` helper to deserialize `audits` rows into `AnalysisRun` domain models with `workspace_id` preserved.
3. **`backend/app/orchestration/orchestrator.py`**:
   - Update `get_run()` to delegate DB deserialization to `self.repository._row_to_run(stored)`.
4. **`backend/tests/test_tenant_isolation.py`**:
   - Add Suite 7 with 4 new unit tests covering workspace filtering, default identifier rejection, serialization/hydration, and legacy database auto-migration.

---

## 5. Verification Method

To verify the strategy and subsequent implementation:

```bash
# 1. Verify list_runs with workspace_id runs without OperationalError
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -c "
import sys, tempfile, os
sys.path.insert(0, 'backend')
from app.db.repository import AuditRepository
from app.domain.models import AnalysisRun
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
    db_path = tf.name
try:
    repo = AuditRepository(db_path=db_path)
    run = AnalysisRun(
        analysis_id='run_v1',
        org_id='org_alpha',
        workspace_id='ws_alpha',
        website_url='https://example.com',
        created_at='2026-11-01T00:00:00Z',
        updated_at='2026-11-01T00:00:00Z',
    )
    repo.save_run(run)
    res = repo.list_runs('org_alpha', workspace_id='ws_alpha')
    assert len(res) == 1
    assert res[0]['workspace_id'] == 'ws_alpha'
    print('PASS: list_runs with workspace_id succeeded and returned persisted workspace')
finally:
    if os.path.exists(db_path):
        os.remove(db_path)
"

# 2. Run the tenant isolation suite
pytest backend/tests/test_tenant_isolation.py -v

# 3. Run persistence regression suites
pytest backend/tests/test_audit_persistence_and_restore.py backend/tests/test_audit_persistence_and_checkpoints.py -v
```

**Invalidation Conditions**:
- `AuditRepository.list_runs(org_id, workspace_id)` throws `sqlite3.OperationalError: no such column: workspace_id`.
- `repo.save_run(run)` drops `run.workspace_id`.
- Pre-existing database files crash upon initialization or querying.
- `list_runs` return type changes from `List[Dict[str, Any]]`, breaking dependent endpoints.
