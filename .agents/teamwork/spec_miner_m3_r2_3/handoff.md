# Specification Mining & Test Blueprint Handoff — Milestone M3 Iteration 2

**Agent**: `spec_miner_m3_r2_3` (teamwork_preview_spec_miner)  
**Parent Agent**: `c6f6f3f2-acb1-4d19-b16f-9f0aba77d9f4`  
**Milestone**: M3 Iteration 2 (Defect Remediation & Invariant Verification)  
**Blueprint Artifact**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_r2_3/test_blueprint_m3_r2.md`  
**Target Codebase Location**: `backend/tests/test_tenant_isolation.py` (Suite 7)  
**Date**: 2026-11-01  

---

## 1. Observation

### Obs 1.1: Verification of Baseline Test Suite
- Executed: `pytest backend/tests/test_tenant_isolation.py -v`
- Result:
  ```text
  ======================= 40 passed, 3 warnings in 10.71s ========================
  ```
- Confirmed: Existing Suites 1 through 6 pass cleanly without regressions.

### Obs 1.2: Empirical Reproduction of AuditRepository SQL Schema Defect (Challenger Obs 1.3)
- Inspected `backend/app/db/repository.py:201-205`:
  ```python
  if workspace_id:
      cur = conn.execute(
          "SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?",
          (clean_org_id, workspace_id, limit),
      )
  ```
- Inspected `backend/app/db/schema.py:14-37`: `SQLITE_SCHEMA` table `audits` contains:
  `analysis_id, org_id, user_id, website_url, domain, status, progress, stage, max_pages, score_overall, score_human, score_google, score_ai_readiness, score_ai_visibility, score_band, started_at, completed_at, input_hash, output_hash, raw_report_json, error_message, created_at`.
  Column `workspace_id` is missing.
- Inspected `backend/app/db/repository.py:86-96`: `save_run` omits `workspace_id` from the SQL `INSERT` statement and `params` dictionary.
- Executed direct probe:
  ```python
  from app.db.repository import AuditRepository
  repo = AuditRepository(db_path=tmp_db_path)
  repo.list_runs("org_alpha", workspace_id="ws_alpha")
  ```
  Result:
  ```text
  OperationalError: no such column: workspace_id
  ```

### Obs 1.3: Empirical Reproduction of Insecure Identifier Leaks (Challenger Obs 1.2)
- Ran validation probe across all 6 models with `org_id="ws_default"`:
  ```text
  AnalysisRun org_id=ws_default: ALLOWED
  AnalysisRequest org_id=ws_default: ALLOWED
  Finding org_id=ws_default: ALLOWED
  ExecutiveReport org_id=ws_default: ALLOWED
  MissionState org_id=ws_default: ALLOWED
  Integration org_id=ws_default: ALLOWED
  ```
- Ran validation probe with `workspace_id="org_default"` and whitespace-only `workspace_id="   "`:
  ```text
  AnalysisRun workspace_id=org_default: ALLOWED
  AnalysisRun workspace_id=whitespace: ALLOWED
  AnalysisRequest workspace_id=org_default: ALLOWED
  AnalysisRequest workspace_id=whitespace: ALLOWED
  Finding workspace_id=org_default: ALLOWED
  Finding workspace_id=whitespace: ALLOWED
  ExecutiveReport workspace_id=org_default: ALLOWED
  ExecutiveReport workspace_id=whitespace: ALLOWED
  MissionState workspace_id=org_default: ALLOWED
  MissionState workspace_id=whitespace: ALLOWED
  Integration workspace_id=org_default: ALLOWED
  Integration workspace_id=whitespace: ALLOWED
  ```
- Inspected model validator definitions:
  - `backend/app/domain/models.py:146, 359, 2656, 2786, 2823` and `backend/app/orchestration/mission/state.py:111` inspect only `if cleaned in ("org_default", "default"):`.
  - `backend/app/domain/models.py:153, 367, 2663, 2794, 2830` and `backend/app/orchestration/mission/state.py:118` inspect only `if v is not None and v.strip() == "ws_default":`.

### Obs 1.4: Empirical Reproduction of Orchestrator Guards (Challenger Obs 1.4)
- Probed `AnalysisOrchestrator.create_run(website_url="https://example.com", org_id="ws_default")`:
  Returned instance with `org_id="ws_default"` without error.
- Probed `AnalysisOrchestrator.execute_analysis_pipeline` guard (line 310):
  `if not run or not run.org_id or run.org_id in ("org_default", "default"):` allowed `run.org_id="ws_default"` to pass to pipeline execution.

### Obs 1.5: Reviewer 2 Hardening Findings
- `backend/app/api/routes/platform/workspaces.py:58-72`: `list_workspaces` does not invoke `require_org_context(user)`. Calling it with `user.org_id = "org_default"` auto-creates `ws_default_org_default` and returns 200 OK.
- `backend/app/api/routes/platform/workspaces.py:44`: `_owned_workspace` returns `403 Forbidden` on cross-tenant lookup rather than `404 Not Found`.

---

## 2. Logic Chain

1. From Obs 1.1, the 40 existing tests across Suites 1-6 pass, establishing that previous milestone isolation mechanics remain operational.
2. From Obs 1.2, `AuditRepository.list_runs` expects `workspace_id` to exist in `audits` table when filtered by workspace. Because the SQLite schema omitted this column, calling `list_runs(org_id, workspace_id)` consistently crashes with `sqlite3.OperationalError`. Simultaneously, `save_run` drops `workspace_id` and `get_run` returns `None`. A pair of dedicated unit tests (`test_repository_list_runs_workspace_filtering_no_operational_error` and `test_repository_save_run_and_get_run_persists_workspace_id`) will verify schema presence, insertion, retrieval, and filtering.
3. From Obs 1.3, an asymmetrical gap exists where `org_id` rejects `"org_default"` but permits `"ws_default"`, and `workspace_id` rejects `"ws_default"` but permits `"org_default"` and `"   "`. Because both tokens represent unauthenticated or insecure fallback tenants, all 6 models must reject them symmetrically. Parameterized adversarial tests (`test_models_reject_ws_default_as_org_id` and `test_models_reject_org_default_and_whitespace_as_workspace_id`) comprehensively cover every model and input permutation.
4. From Obs 1.4, `AnalysisOrchestrator` fails to guard against `ws_default` at both run creation and pipeline execution entrypoints. Tests `test_orchestrator_create_run_rejects_ws_default_as_org_id` and `test_orchestrator_execute_analysis_pipeline_rejects_ws_default_org_id` enforce that these entry gates raise `ValueError`.
5. From Obs 1.5, reviewer hardening tests (`test_api_list_workspaces_rejects_insecure_default_org` and `test_api_workspace_cross_tenant_returns_404`) ensure REST endpoints do not auto-create workspaces for invalid orgs or leak workspace existence across tenants.
6. Therefore, the blueprint designed in `test_blueprint_m3_r2.md` provides an unambiguous, empirically verified specification for Milestone M3 Iteration 2.

---

## 3. Caveats

- **Test Isolation**: Tests using `AuditRepository` must utilize the `isolated_repo` fixture (with temporary SQLite files) to ensure clean schema initialization without interfering with the local dev database (`data/dristik_audits.db`).
- **Async Execution**: `test_orchestrator_execute_analysis_pipeline_rejects_ws_default_org_id` requires `@pytest.mark.asyncio`. Using `AnalysisRun.model_construct` bypasses Pydantic model validation so the pipeline's own guard on line 310 can be tested independently of model instantiation.
- **Model Construction Completeness**: All 6 domain models require specific mandatory fields (e.g. `scores` on `ExecutiveReport`, `target` and `objective` on `MissionState`, `category` and `severity` on `Finding`). The blueprint supplies complete, valid kwargs so tests isolate validation logic without raising schema structure errors.

---

## 4. Conclusion

The specification and test blueprint for Milestone M3 Iteration 2 is complete and committed to:
`/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_r2_3/test_blueprint_m3_r2.md`.

It specifies 8 concrete test functions for `backend/tests/test_tenant_isolation.py` (Suite 7: T-TI-07.1 through T-TI-07.8):
1. `test_repository_list_runs_workspace_filtering_no_operational_error`
2. `test_repository_save_run_and_get_run_persists_workspace_id`
3. `test_models_reject_ws_default_as_org_id` (parameterized across 6 models and padded variants)
4. `test_models_reject_org_default_and_whitespace_as_workspace_id` (parameterized across 6 models and 4 invalid string variants)
5. `test_orchestrator_create_run_rejects_ws_default_as_org_id`
6. `test_orchestrator_execute_analysis_pipeline_rejects_ws_default_org_id`
7. `test_api_list_workspaces_rejects_insecure_default_org`
8. `test_api_workspace_cross_tenant_returns_404`

In addition, the blueprint includes exact code diffs and implementation guidance for worker agents across `schema.py`, `repository.py`, `models.py`, `state.py`, `orchestrator.py`, and `workspaces.py`.

---

## 5. Verification Method

To verify the blueprint and its reproduction steps:

```bash
# 1. Run baseline tenant isolation suite
pytest backend/tests/test_tenant_isolation.py -v

# 2. Run independent defect probe to verify existing failure modes
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -c "
import sys, tempfile, os
sys.path.insert(0, 'backend')
from app.db.repository import AuditRepository
from app.domain.models import AnalysisRun

with tempfile.TemporaryDirectory() as td:
    repo = AuditRepository(db_path=os.path.join(td, 'test.db'))
    try:
        repo.list_runs('org_alpha', workspace_id='ws_alpha')
        print('UNEXPECTED: list_runs succeeded without schema column')
    except Exception as e:
        print('CONFIRMED REPRODUCER (Obs 1.2):', type(e).__name__, str(e))
"

# 3. Post-remediation verification:
# After worker implements the changes and appends Suite 7 to test_tenant_isolation.py:
pytest backend/tests/test_tenant_isolation.py -k "T-TI-07 or test_models_reject or test_repository" -v
```

**Invalidation Conditions**:
- Any regression in Suites 1 through 6 in `test_tenant_isolation.py`.
- Any model accepting `org_id="ws_default"` or `workspace_id in ("org_default", "default", "   ")`.
- `AuditRepository.list_runs(org_id, workspace_id)` raising `sqlite3.OperationalError`.
