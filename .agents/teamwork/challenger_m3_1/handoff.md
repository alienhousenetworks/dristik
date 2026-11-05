# Empirical Challenge Report & Handoff — Milestone M3

**Challenger**: challenger_m3_1 (empirical challenger / critic / specialist)  
**Parent Agent**: c6f6f3f2-acb1-4d19-b16f-9f0aba77d9f4  
**Target Milestone**: M3 (Domain, Repository, and Pipeline Isolation)  
**Worker Under Review**: worker_m3_4 (`.agents/teamwork/worker_m3_4/handoff.md`)  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### Obs 1.1: Verification of Existing and Required Suites
- `pytest backend/tests/test_tenant_isolation.py -v`:
  Executed across all 40 tests:
  ```text
  ======================= 40 passed, 3 warnings in 39.98s ========================
  ```
- `pytest backend/tests/security/test_tenant_isolation.py -v`:
  ```text
  ======================== 4 passed, 2 warnings in 0.82s =========================
  ```
- Dependent caller suites regression check:
  `pytest backend/tests/test_audit_persistence_and_restore.py backend/tests/test_scoring_timing_and_honest_flag.py backend/tests/test_selective_pillars.py backend/tests/test_pipeline.py backend/tests/test_visual_ux_and_analytics_connectors.py backend/tests/test_google_connectors.py backend/tests/test_mission_director.py backend/tests/test_radar_pulse.py -v`
  ```text
  ======================= 43 passed, 57 warnings in 17.23s =======================
  ```
- Database session, CAS, and external authority suites:
  `pytest backend/tests/test_db_session_and_fail_fast.py backend/tests/test_audit_persistence_and_checkpoints.py backend/tests/test_enterprise_schema_and_cas.py backend/tests/test_external_authority.py -v`
  ```text
  ======================== 41 passed, 7 warnings in 3.43s ========================
  ```
- Multi-page orchestration suite:
  `pytest backend/tests/test_multi_page.py -v`
  ```text
  ======================= 2 passed, 37 warnings in 29.10s ========================
  ```
- Code style check: `flake8 backend/tests/test_tenant_isolation.py --ignore=E501` exited with code 0.

---

### Obs 1.2: Empirical Probing of Domain Models (`AnalysisRun`, `AnalysisRequest`, `Finding`, `ExecutiveReport`, `MissionState`)
Adversarial harness probe results:
- **`org_id` Rejections**:
  - `org_default`: Rejected by all models (`ValidationError: Insecure fallback tenant 'org_default' is forbidden.`).
  - Whitespace-only (`'   '`): Rejected by all models (`ValidationError: Tenant org_id is required and cannot be empty.` or `Insecure fallback tenant '   ' is forbidden.`).
  - Empty string (`''`): Rejected by all models (`ValidationError: Tenant org_id is required and cannot be empty.` or `Insecure fallback tenant '' is forbidden.`).
  - `None`: Rejected by `AnalysisRun`, `ExecutiveReport`, and `MissionState`. Allowed by `AnalysisRequest` and `Finding` (where `org_id: Optional[str] = None` by design).
- **Asymmetric Fallback Leak (`org_id='ws_default'`)**:
  - Running:
    ```python
    AnalysisRun(analysis_id='run_1', org_id='ws_default', website_url='https://example.com', created_at='2026-11-01T00:00:00Z', updated_at='2026-11-01T00:00:00Z')
    ```
    **ALLOWED**: Returned instance with `org_id='ws_default'`.
  - Same vulnerability reproduced on `AnalysisRequest`, `Finding`, `ExecutiveReport`, and `MissionState`.
  - Root cause: `backend/app/domain/models.py:146, 359, 2656, 2786, 2823` and `backend/app/orchestration/mission/state.py:111` only inspect `if cleaned in ("org_default", "default"):`, omitting `"ws_default"`.
- **Asymmetric Fallback Leak (`workspace_id='org_default'` & whitespace-only)**:
  - Running:
    ```python
    AnalysisRun(analysis_id='run_1', org_id='org_valid', workspace_id='org_default', website_url='https://example.com', created_at='2026-11-01T00:00:00Z', updated_at='2026-11-01T00:00:00Z')
    ```
    **ALLOWED**: Returned instance with `workspace_id='org_default'`.
  - Running with `workspace_id='   '`:
    **ALLOWED**: Returned instance with `workspace_id='   '`.
  - Same behavior observed on `AnalysisRequest`, `Finding`, `ExecutiveReport`, and `MissionState`.
  - Root cause: `backend/app/domain/models.py:153, 367, 2663, 2794, 2830` and `backend/app/orchestration/mission/state.py:118` only validate `if v is not None and v.strip() == "ws_default":`, omitting `"org_default"`, `"default"`, and whitespace/empty sanitization.

---

### Obs 1.3: Runtime Crash in `AuditRepository.list_runs` with `workspace_id`
- Code inspected in `backend/app/db/repository.py:201-205`:
  ```python
  if workspace_id:
      cur = conn.execute(
          "SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?",
          (clean_org_id, workspace_id, limit),
      )
  ```
- Code inspected in `backend/app/db/schema.py:14-37` (`SQLITE_SCHEMA`):
  The `audits` table schema contains columns:
  `analysis_id`, `org_id`, `user_id`, `website_url`, `domain`, `status`, `progress`, `stage`, `max_pages`, `score_overall`, `score_human`, `score_google`, `score_ai_readiness`, `score_ai_visibility`, `score_band`, `started_at`, `completed_at`, `input_hash`, `output_hash`, `raw_report_json`, `error_message`, `created_at`.
  Column `workspace_id` is completely missing from `audits`.
- Empirical execution:
  ```python
  from app.db.repository import AuditRepository
  repo = AuditRepository(db_path=":memory:")
  repo.list_runs("tenant_A", workspace_id="ws_1")
  ```
  Result:
  ```text
  sqlite3.OperationalError: no such column: workspace_id
  ```

---

### Obs 1.4: Orchestrator `create_run` and `execute_analysis_pipeline` Probes
- `orchestrator.create_run`:
  - `org_id=None`, `""`, `"   "` -> Correctly raised `ValueError: Tenant org_id is required and cannot be empty.`
  - `org_id="org_default"`, `"default"` -> Correctly raised `ValueError: Disallowed tenant identifier ...`
  - `workspace_id="ws_default"` -> Correctly raised `ValidationError: Insecure fallback workspace 'ws_default' is forbidden.`
  - `org_id="ws_default"` -> **ALLOWED** (returned run with `org_id="ws_default"`).
- `orchestrator.execute_analysis_pipeline`:
  - Non-existent run, `org_id="org_default"`, `org_id=""`, `org_id="default"` -> Correctly raised `ValueError: Cannot execute pipeline for analysis ...: valid tenant org_id required, 'org_default' rejected.`
  - Run with `org_id="ws_default"`:
    Inspected `backend/app/orchestration/orchestrator.py:310`:
    ```python
    if not run or not run.org_id or run.org_id in ("org_default", "default"):
        raise ValueError(...)
    ```
    Execution empirical test: Line 310 does NOT reject `run.org_id="ws_default"`; pipeline execution proceeds.

---

### Obs 1.5: Worker Handoff Documentation Discrepancy
- `worker_m3_4/handoff.md:13` claims:
  `backend/app/orchestration/mission/state.py: Lines 33-43 implement @field_validator on MissionExecutionState rejecting empty, whitespace, and org_default/ws_default values.`
- In reality:
  - `MissionExecutionState` does not exist in the codebase.
  - The actual state model is `MissionState` defined at line 101.
  - Lines 33-43 define `MissionObjective`.
  - Claimed exception `ValueError("FORBIDDEN_DEFAULT_TENANT: ...")` does not match the actual code (`ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")`).

---

## 2. Logic Chain

1. From Obs 1.1, all baseline suites in `backend/tests/` pass (40 tests in `test_tenant_isolation.py`, 4 in `security/test_tenant_isolation.py`, 43 in dependent suites, 41 in DB suites, 2 in multi-page). Multi-tenant isolation at the HTTP and API level is strictly enforced (cross-tenant calls return 404, unauthenticated returns 401, missing org returns 403).
2. From Obs 1.3, worker modified `AuditRepository.list_runs` to support `workspace_id: Optional[str] = None` and execute `SELECT ... WHERE org_id = ? AND workspace_id = ?`. However, `SQLITE_SCHEMA` in `backend/app/db/schema.py` does not contain a `workspace_id` column on the `audits` table, nor does `save_run` persist `workspace_id`. Calling `repo.list_runs(org_id, workspace_id)` crashes at runtime with `sqlite3.OperationalError: no such column: workspace_id`. Because the worker's unit tests only called `list_runs(org_id)` without `workspace_id`, this runtime SQL failure went undetected.
3. From Obs 1.2 and Obs 1.4, while `"org_default"` is blocked on `org_id` and `"ws_default"` is blocked on `workspace_id`, cross-fallback values are permitted: `org_id="ws_default"` is accepted by all 5 domain models, passes `orchestrator.create_run`, and executes through `orchestrator.execute_analysis_pipeline`. Additionally, `workspace_id="org_default"` and whitespace-only `workspace_id="   "` are accepted by all models.
4. From Obs 1.5, the worker handoff contains factual errors regarding non-existent class `MissionExecutionState` and line ranges in `mission/state.py`.
5. Therefore, while core isolation mechanisms are functional and robust across happy paths, the runtime SQL crash on `list_runs(workspace_id=...)` and validator bypass for `ws_default` on `org_id` represent defects requiring remediation.

---

## 3. Caveats

- In production usage, existing HTTP endpoints (`app/api/routes/audits/analyses.py` and `app/identity/service.py`) currently call `repo.list_runs(org_id=...)` without passing `workspace_id`. The crash only manifests when callers pass the `workspace_id` parameter exposed in the public method signature.
- `org_id="ws_default"` cannot easily be injected via the public REST API because `require_org_context` validates against `user.org_id` in `TenantManager`, which does not seed `"ws_default"`. However, domain model and pipeline interfaces accept it directly, violating invariant isolation.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone M3 has made excellent progress: hardcoded default parameters were removed, tenant scoping is enforced across REST routes with 403/404 semantics, and 126+ tests pass. However, before M3 can be approved and closed, the following fixes are requested:

1. **Fix `AuditRepository.list_runs` SQL Schema Mismatch**:
   - Add `workspace_id TEXT` column to the `audits` table in `backend/app/db/schema.py` (`SQLITE_SCHEMA`) and persist `run.workspace_id` in `save_run`, OR defensively handle `workspace_id` query execution when the column exists/does not exist.
   - Add a unit test in `backend/tests/test_tenant_isolation.py` calling `repo.list_runs("org_alpha", workspace_id="ws_alpha")` verifying it returns filtered results without throwing `OperationalError`.
2. **Harmonize Insecure Default Validation Across Models & Pipeline**:
   - Define a shared set `FORBIDDEN_TENANT_IDENTIFIERS = {"org_default", "ws_default", "default"}`.
   - In `@field_validator("org_id")` and `@field_validator("workspace_id")` across `AnalysisRun`, `AnalysisRequest`, `Finding`, `ExecutiveReport`, `MissionState`, and `Integration`: reject any value in `FORBIDDEN_TENANT_IDENTIFIERS`.
   - In `@field_validator("workspace_id")`: reject whitespace-only strings `not v.strip()`.
   - In `orchestrator.create_run` and `orchestrator.execute_analysis_pipeline`: reject `clean_org in FORBIDDEN_TENANT_IDENTIFIERS`.
3. **Correct Worker Handoff Documentation**:
   - Update `worker_m3_4/handoff.md` to reference `MissionState` (lines 101-121) instead of `MissionExecutionState`.

---

## 5. Verification Method

To independently reproduce the findings and verify subsequent fixes:

```bash
# 1. Reproduce AuditRepository.list_runs crash with workspace_id
python3 -c "
import sys; sys.path.insert(0, 'backend')
from app.db.repository import AuditRepository
repo = AuditRepository(db_path=':memory:')
try:
    repo.list_runs('org_alpha', workspace_id='ws_alpha')
    print('PASS: list_runs with workspace_id succeeded')
except Exception as e:
    print('BUG CONFIRMED:', type(e), e)
"

# 2. Reproduce org_id='ws_default' leak in AnalysisRun & orchestrator
python3 -c "
import sys; sys.path.insert(0, 'backend')
from app.domain.models import AnalysisRun
from app.orchestration.orchestrator import AnalysisOrchestrator
try:
    r = AnalysisRun(analysis_id='r1', org_id='ws_default', website_url='https://example.com', created_at='..', updated_at='..')
    print('LEAK CONFIRMED: AnalysisRun accepted org_id=\"ws_default\"')
except Exception as e:
    print('REJECTED:', e)

orch = AnalysisOrchestrator()
try:
    run = orch.create_run('https://example.com', org_id='ws_default')
    print('LEAK CONFIRMED: orchestrator.create_run accepted org_id=\"ws_default\"')
except Exception as e:
    print('REJECTED:', e)
"

# 3. Run full tenant isolation test suite
pytest backend/tests/test_tenant_isolation.py -v
```

**Invalidation Conditions**:
- `repo.list_runs(org_id, workspace_id)` executes cleanly without `OperationalError`.
- `AnalysisRun(..., org_id='ws_default')` raises `ValidationError`.
- `AnalysisRun(..., workspace_id='org_default')` raises `ValidationError`.
- `AnalysisRun(..., workspace_id='   ')` raises `ValidationError`.
- `orchestrator.create_run(..., org_id='ws_default')` raises `ValueError`.
- All 40 tests in `test_tenant_isolation.py` and dependent regression suites continue to pass.
