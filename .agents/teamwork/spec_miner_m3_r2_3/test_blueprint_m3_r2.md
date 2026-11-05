# Test Specification Blueprint — Milestone M3 Iteration 2
**Document**: `test_blueprint_m3_r2.md`  
**Author**: `spec_miner_m3_r2_3` (teamwork_preview_spec_miner)  
**Parent Agent**: `c6f6f3f2-acb1-4d19-b16f-9f0aba77d9f4`  
**Target Milestone**: M3 Iteration 2 (Defect Remediation & Invariant Verification)  
**Target File**: `backend/tests/test_tenant_isolation.py` (Suite 7)  
**Date**: 2026-11-01  

---

## 1. Executive Summary & Root Cause Analysis

Following the empirical audits by `challenger_m3_1` and `reviewer_m3_2`, Milestone M3 reached 100% pass rates across existing Suites 1-6 (40 tests), but revealed 4 critical defects and 2 hardening gaps:

1. **SQL Schema & Repository Desynchronization (Challenger Obs 1.3)**:
   - `AuditRepository.list_runs(org_id, workspace_id=...)` executes `SELECT * FROM audits WHERE org_id = ? AND workspace_id = ? ...`.
   - `SQLITE_SCHEMA` in `backend/app/db/schema.py` omitted column `workspace_id` from table `audits`.
   - `AuditRepository.save_run` never persisted `workspace_id`.
   - At runtime, calling `repo.list_runs("org_alpha", workspace_id="ws_1")` crashed with `sqlite3.OperationalError: no such column: workspace_id`.

2. **Asymmetric Insecure Identifier Leak (`org_id='ws_default'`) (Challenger Obs 1.2 & 1.4)**:
   - Validators across `AnalysisRun`, `AnalysisRequest`, `Finding`, `ExecutiveReport`, `MissionState`, `Integration`, and `AnalysisOrchestrator` only checked `in ("org_default", "default")`.
   - Providing `org_id="ws_default"` completely bypassed all tenant checks, allowing audit creation, domain entity instantiation, and pipeline execution under an insecure fallback identifier.

3. **Permissive Workspace Fallbacks (`workspace_id='org_default'` & whitespace-only) (Challenger Obs 1.2)**:
   - Validators on `workspace_id` only checked `v.strip() == "ws_default"`.
   - Passing `workspace_id="org_default"`, `workspace_id="default"`, or whitespace-only `workspace_id="   "` was accepted across all models.

4. **Orchestrator Pipeline Guard Gap (Challenger Obs 1.4)**:
   - `AnalysisOrchestrator.create_run` and `execute_analysis_pipeline` allowed runs with `org_id="ws_default"`.

5. **Workspace Route Gaps (Reviewer 2 Findings 1 & 3)**:
   - `list_workspaces` in `backend/app/api/routes/platform/workspaces.py` omitted `require_org_context(user)`.
   - `_owned_workspace` returned 403 on cross-tenant lookup instead of 404, allowing workspace enumeration.

---

## 2. Features Discovered & Invariant Matrix

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Persistence | `AuditRepository.list_runs` with `workspace_id` | Scopes recent audits to matching `org_id` and optional `workspace_id` | `org_id: str`, `workspace_id: Optional[str]`, `limit: int` | `List[Dict[str, Any]]` | Raises `ValueError` on empty/forbidden `org_id`; must NOT crash with `sqlite3.OperationalError` | Challenger Obs 1.3 / Repo source line 201 |
| 2 | Persistence | `AuditRepository.save_run` & `get_run` | Atomically persists audit run including `workspace_id`, and restores it on retrieval | `run: AnalysisRun` | None / `Optional[Dict[str, Any]]` | Preserves `workspace_id` across database writes and reads | Challenger Obs 1.3 / Repo source line 86 |
| 3 | Domain Model | `AnalysisRun` Tenant Guard | Rejects insecure fallback tokens (`org_default`, `ws_default`, `default`) on `org_id` and `workspace_id` | `org_id: str`, `workspace_id: Optional[str]` | Instantiated `AnalysisRun` | Raises `ValueError` on empty, whitespace, or forbidden fallback tokens | Challenger Obs 1.2 / Models line 2817 |
| 4 | Domain Model | `AnalysisRequest` Tenant Guard | Rejects insecure fallback tokens (`org_default`, `ws_default`, `default`) on `org_id` and `workspace_id` | `org_id: Optional[str]`, `workspace_id: Optional[str]` | Instantiated `AnalysisRequest` | Raises `ValueError` on empty, whitespace, or forbidden fallback tokens | Challenger Obs 1.2 / Models line 2782 |
| 5 | Domain Model | `Finding` Tenant Guard | Rejects insecure fallback tokens on `org_id` and `workspace_id` | `org_id: Optional[str]`, `workspace_id: Optional[str]` | Instantiated `Finding` | Raises `ValueError` on empty, whitespace, or forbidden fallback tokens | Challenger Obs 1.2 / Models line 355 |
| 6 | Domain Model | `ExecutiveReport` Tenant Guard | Rejects insecure fallback tokens on `org_id` and `workspace_id` | `org_id: str`, `workspace_id: Optional[str]` | Instantiated `ExecutiveReport` | Raises `ValueError` on empty, whitespace, or forbidden fallback tokens | Challenger Obs 1.2 / Models line 2650 |
| 7 | Orchestration | `MissionState` Tenant Guard | Rejects insecure fallback tokens on `org_id` and `workspace_id` | `org_id: str`, `workspace_id: str` | Instantiated `MissionState` | Raises `ValueError` on empty, whitespace, or forbidden fallback tokens | Challenger Obs 1.2 / State line 108 |
| 8 | Connectors | `Integration` Tenant Guard | Rejects insecure fallback tokens on `org_id` and `workspace_id` | `org_id: str`, `workspace_id: Optional[str]` | Instantiated `Integration` | Raises `ValueError` on empty, whitespace, or forbidden fallback tokens | Challenger Obs 1.2 / Models line 140 |
| 9 | Orchestration | `AnalysisOrchestrator.create_run` Guard | Rejects `org_id in ("org_default", "ws_default", "default")` | `website_url: str`, `org_id: str`, `workspace_id: Optional[str]` | `AnalysisRun` | Raises `ValueError` with descriptive diagnostic | Challenger Obs 1.4 / Orchestrator line 104 |
| 10 | Orchestration | `AnalysisOrchestrator.execute_analysis_pipeline` Guard | Rejects pipeline execution when `run.org_id in ("org_default", "ws_default", "default")` | `analysis_id: str`, `website_url: str` | Executes pipeline or raises | Raises `ValueError` before crawler/controller initialization | Challenger Obs 1.4 / Orchestrator line 310 |
| 11 | API Route | `list_workspaces` Auth Guard | Rejects unauthenticated or forbidden `org_default` tenant sessions | `user: UserIdentity` | `{"workspaces": [...]}` | Raises 403 Forbidden via `require_org_context` | Reviewer 2 Finding 1 / Workspaces line 58 |
| 12 | API Route | `_owned_workspace` Enumeration Guard | Returns 404 Not Found on cross-tenant workspace lookup | `workspace_id: str`, `user: UserIdentity` | Workspace record | Raises 404 Not Found (zero tenant enumeration) | Reviewer 2 Finding 3 / Workspaces line 44 |

---

## 3. Edge Cases Matrix

| # | Feature | Input | Observed Behavior (Pre-Remediation) | Required Behavior (Post-Remediation) |
|---|---------|-------|------------------------------------|--------------------------------------|
| 1 | `AuditRepository.list_runs` | `workspace_id="ws_alpha"` | Crashes with `sqlite3.OperationalError: no such column: workspace_id` | Executes `SELECT`, returns only runs matching `org_id` AND `workspace_id` |
| 2 | `AuditRepository.list_runs` | `workspace_id="ws_nonexistent"` | Crashes with `sqlite3.OperationalError` | Returns empty list `[]` |
| 3 | `AuditRepository.save_run` | `run.workspace_id="ws_east"` | Saves row, but drops `workspace_id` | Column `workspace_id` is populated in `audits` table |
| 4 | `AuditRepository.get_run` | `analysis_id="run_1"` | Returns dict with `workspace_id=None` | Returns dict with `workspace_id="ws_east"` |
| 5 | `AnalysisRun` | `org_id="ws_default"` | Allowed (bypasses validator) | Raises `ValueError: Insecure fallback tenant 'ws_default' is forbidden.` |
| 6 | `AnalysisRun` | `workspace_id="org_default"` | Allowed (bypasses validator) | Raises `ValueError: Insecure fallback workspace 'org_default' is forbidden.` |
| 7 | `AnalysisRun` | `workspace_id="   "` | Allowed (whitespace preserved) | Raises `ValueError: Insecure fallback workspace '   ' is forbidden.` |
| 8 | `AnalysisRequest` | `org_id="ws_default"` | Allowed | Raises `ValueError` |
| 9 | `AnalysisRequest` | `workspace_id="org_default"` | Allowed | Raises `ValueError` |
| 10 | `AnalysisRequest` | `workspace_id="   "` | Allowed | Raises `ValueError` |
| 11 | `Finding` | `org_id="ws_default"` | Allowed | Raises `ValueError` |
| 12 | `Finding` | `workspace_id="org_default"` | Allowed | Raises `ValueError` |
| 13 | `Finding` | `workspace_id="   "` | Allowed | Raises `ValueError` |
| 14 | `ExecutiveReport` | `org_id="ws_default"` | Allowed | Raises `ValueError` |
| 15 | `ExecutiveReport` | `workspace_id="org_default"` | Allowed | Raises `ValueError` |
| 16 | `ExecutiveReport` | `workspace_id="   "` | Allowed | Raises `ValueError` |
| 17 | `MissionState` | `org_id="ws_default"` | Allowed | Raises `ValueError` |
| 18 | `MissionState` | `workspace_id="org_default"` | Allowed | Raises `ValueError` |
| 19 | `MissionState` | `workspace_id="   "` | Allowed | Raises `ValueError` |
| 20 | `Integration` | `org_id="ws_default"` | Allowed | Raises `ValueError` |
| 21 | `Integration` | `workspace_id="org_default"` | Allowed | Raises `ValueError` |
| 22 | `Integration` | `workspace_id="   "` | Allowed | Raises `ValueError` |
| 23 | `orchestrator.create_run` | `org_id="ws_default"` | Allowed (creates run) | Raises `ValueError: Disallowed tenant identifier 'ws_default'.` |
| 24 | `orchestrator.create_run` | `org_id="  ws_default  "` | Allowed | Raises `ValueError` after strip |
| 25 | `orchestrator.execute_analysis_pipeline` | `run.org_id="ws_default"` | Allowed (pipeline runs) | Raises `ValueError: Cannot execute pipeline ... 'ws_default' rejected.` |
| 26 | `GET /api/v1/workspaces` | User with `org_id="org_default"` | Returns 200 OK & auto-creates `ws_default_org_default` | Returns 403 Forbidden |
| 27 | `GET /api/v1/workspaces/{id}` | Foreign tenant user | Returns 403 Forbidden | Returns 404 Not Found |

---

## 4. Test Suite 7 Code Blueprint for `backend/tests/test_tenant_isolation.py`

Below is the concrete, production-ready Python code to be appended to `backend/tests/test_tenant_isolation.py`.

### Required Imports Addition
Add to the top of `backend/tests/test_tenant_isolation.py` (if not already imported):
```python
from app.orchestration.mission.state import MissionState, WebsiteTarget, MissionObjective
```

### Suite 7 Code Block
```python
# =============================================================================
# Suite 7: T-TI-07 Defect Remediation & Invariant Verification (Iteration 2)
# =============================================================================

def test_repository_list_runs_workspace_filtering_no_operational_error(isolated_repo):
    """
    T-TI-07.1: Verify that AuditRepository.list_runs with workspace_id executes cleanly
    without sqlite3.OperationalError: no such column: workspace_id,
    and returns only records partitioned to the requested workspace.
    """
    now = datetime.now(timezone.utc).isoformat()
    run_ws1 = AnalysisRun(
        analysis_id=f"run_alpha_ws1_{uuid.uuid4().hex[:6]}",
        org_id="org_alpha_repo_test",
        workspace_id="ws_alpha_1",
        website_url="https://alpha1.example.com",
        created_at=now,
        updated_at=now,
    )
    run_ws2 = AnalysisRun(
        analysis_id=f"run_alpha_ws2_{uuid.uuid4().hex[:6]}",
        org_id="org_alpha_repo_test",
        workspace_id="ws_alpha_2",
        website_url="https://alpha2.example.com",
        created_at=now,
        updated_at=now,
    )
    run_beta = AnalysisRun(
        analysis_id=f"run_beta_ws1_{uuid.uuid4().hex[:6]}",
        org_id="org_beta_repo_test",
        workspace_id="ws_alpha_1",
        website_url="https://beta1.example.com",
        created_at=now,
        updated_at=now,
    )

    isolated_repo.save_run(run_ws1)
    isolated_repo.save_run(run_ws2)
    isolated_repo.save_run(run_beta)

    # 1. Matching workspace for org_alpha returns only ws_alpha_1
    res_ws1 = isolated_repo.list_runs("org_alpha_repo_test", workspace_id="ws_alpha_1")
    assert len(res_ws1) == 1
    assert res_ws1[0]["analysis_id"] == run_ws1.analysis_id
    assert res_ws1[0]["workspace_id"] == "ws_alpha_1"
    assert res_ws1[0]["org_id"] == "org_alpha_repo_test"

    # 2. Matching workspace for org_alpha returns only ws_alpha_2
    res_ws2 = isolated_repo.list_runs("org_alpha_repo_test", workspace_id="ws_alpha_2")
    assert len(res_ws2) == 1
    assert res_ws2[0]["analysis_id"] == run_ws2.analysis_id
    assert res_ws2[0]["workspace_id"] == "ws_alpha_2"

    # 3. Non-matching workspace returns empty list
    res_foreign = isolated_repo.list_runs("org_alpha_repo_test", workspace_id="ws_nonexistent")
    assert res_foreign == []

    # 4. Strict tenant isolation: org_alpha list does NOT include org_beta run even with same workspace_id
    assert all(r["org_id"] == "org_alpha_repo_test" for r in res_ws1)

    # 5. Unscoped workspace listing returns all runs for the org
    res_all_org = isolated_repo.list_runs("org_alpha_repo_test")
    assert len(res_all_org) == 2
    assert {r["analysis_id"] for r in res_all_org} == {run_ws1.analysis_id, run_ws2.analysis_id}


def test_repository_save_run_and_get_run_persists_workspace_id(isolated_repo):
    """
    T-TI-07.2: Verify that AuditRepository.save_run persists workspace_id to the database
    and get_run restores the workspace_id correctly.
    """
    now = datetime.now(timezone.utc).isoformat()
    analysis_id = f"run_persist_{uuid.uuid4().hex[:6]}"
    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id="org_persist_test",
        workspace_id="workspace_prod_east",
        website_url="https://persisted.example.com",
        created_at=now,
        updated_at=now,
    )
    isolated_repo.save_run(run)

    # Retrieve by analysis_id
    record = isolated_repo.get_run(analysis_id)
    assert record is not None
    assert record["analysis_id"] == analysis_id
    assert record["org_id"] == "org_persist_test"
    assert record["workspace_id"] == "workspace_prod_east"

    # Retrieve with org_id scoping
    scoped = isolated_repo.get_run(analysis_id, org_id="org_persist_test")
    assert scoped is not None
    assert scoped["workspace_id"] == "workspace_prod_east"

    # Retrieve with foreign org_id scoping returns None
    foreign = isolated_repo.get_run(analysis_id, org_id="org_foreign")
    assert foreign is None

    # Update workspace_id on conflict
    run.workspace_id = "workspace_prod_west"
    isolated_repo.save_run(run)
    updated = isolated_repo.get_run(analysis_id)
    assert updated["workspace_id"] == "workspace_prod_west"


@pytest.mark.parametrize("model_cls,model_kwargs", [
    (
        AnalysisRun,
        {
            "analysis_id": "run_bad_org",
            "org_id": "ws_default",
            "website_url": "https://example.com",
            "created_at": "2026-11-01T00:00:00Z",
            "updated_at": "2026-11-01T00:00:00Z",
        },
    ),
    (
        AnalysisRequest,
        {
            "website_url": "https://example.com",
            "org_id": "ws_default",
        },
    ),
    (
        Finding,
        {
            "finding_id": "f_bad_org",
            "org_id": "ws_default",
            "category": Category.TECHNICAL_SEO,
            "severity": Severity.MEDIUM,
        },
    ),
    (
        ExecutiveReport,
        {
            "report_id": "rep_bad_org",
            "org_id": "ws_default",
            "website_url": "https://example.com",
            "domain": "example.com",
            "scores": OverallScoreResult(
                overall_score=80.0,
                grade="B",
                category_scores={
                    Category.TECHNICAL_SEO: CategoryScore(
                        category=Category.TECHNICAL_SEO,
                        score=80.0,
                        weight=1.0,
                        weighted_score=80.0,
                        summary="s",
                    )
                },
            ),
            "story_summary": "summary",
            "primary_strategic_opportunity": "opp",
            "consultant_advice_what_to_ignore": "ign",
        },
    ),
    (
        MissionState,
        {
            "mission_id": "m_bad_org",
            "org_id": "ws_default",
            "workspace_id": "ws_valid",
            "target": WebsiteTarget(url="https://example.com", domain="example.com"),
            "objective": MissionObjective(),
        },
    ),
    (
        Integration,
        {
            "integration_id": "int_bad_org",
            "org_id": "ws_default",
            "name": "Integration Bad Org",
            "target_url": "https://example.com",
            "created_at": "2026-11-01T00:00:00Z",
        },
    ),
])
def test_models_reject_ws_default_as_org_id(model_cls, model_kwargs):
    """
    T-TI-07.3: Verify that org_id='ws_default' (and padded variants) is rejected
    with ValueError across AnalysisRun, AnalysisRequest, Finding, ExecutiveReport,
    MissionState, and Integration.
    """
    with pytest.raises(ValueError, match="(?i)forbidden|tenant|insecure|disallowed"):
        model_cls(**model_kwargs)

    # Test padded variant
    padded_kwargs = dict(model_kwargs)
    padded_kwargs["org_id"] = "   ws_default   "
    with pytest.raises(ValueError, match="(?i)forbidden|tenant|insecure|disallowed"):
        model_cls(**padded_kwargs)


@pytest.mark.parametrize("model_cls,base_kwargs", [
    (
        AnalysisRun,
        {
            "analysis_id": "run_bad_ws",
            "org_id": "org_valid",
            "website_url": "https://example.com",
            "created_at": "2026-11-01T00:00:00Z",
            "updated_at": "2026-11-01T00:00:00Z",
        },
    ),
    (
        AnalysisRequest,
        {
            "website_url": "https://example.com",
            "org_id": "org_valid",
        },
    ),
    (
        Finding,
        {
            "finding_id": "f_bad_ws",
            "org_id": "org_valid",
            "category": Category.TECHNICAL_SEO,
            "severity": Severity.MEDIUM,
        },
    ),
    (
        ExecutiveReport,
        {
            "report_id": "rep_bad_ws",
            "org_id": "org_valid",
            "website_url": "https://example.com",
            "domain": "example.com",
            "scores": OverallScoreResult(
                overall_score=80.0,
                grade="B",
                category_scores={
                    Category.TECHNICAL_SEO: CategoryScore(
                        category=Category.TECHNICAL_SEO,
                        score=80.0,
                        weight=1.0,
                        weighted_score=80.0,
                        summary="s",
                    )
                },
            ),
            "story_summary": "summary",
            "primary_strategic_opportunity": "opp",
            "consultant_advice_what_to_ignore": "ign",
        },
    ),
    (
        MissionState,
        {
            "mission_id": "m_bad_ws",
            "org_id": "org_valid",
            "target": WebsiteTarget(url="https://example.com", domain="example.com"),
            "objective": MissionObjective(),
        },
    ),
    (
        Integration,
        {
            "integration_id": "int_bad_ws",
            "org_id": "org_valid",
            "name": "Integration Bad WS",
            "target_url": "https://example.com",
            "created_at": "2026-11-01T00:00:00Z",
        },
    ),
])
@pytest.mark.parametrize("forbidden_ws", ["org_default", "  org_default  ", "default", "   "])
def test_models_reject_org_default_and_whitespace_as_workspace_id(model_cls, base_kwargs, forbidden_ws):
    """
    T-TI-07.4: Verify that workspace_id='org_default', 'default', and whitespace-only
    are strictly rejected with ValueError across all 6 models.
    """
    kwargs = dict(base_kwargs)
    kwargs["workspace_id"] = forbidden_ws
    with pytest.raises(ValueError, match="(?i)forbidden|workspace|insecure|empty"):
        model_cls(**kwargs)


def test_orchestrator_create_run_rejects_ws_default_as_org_id():
    """
    T-TI-07.5: Verify that AnalysisOrchestrator.create_run rejects org_id='ws_default'
    and padded variations with ValueError.
    """
    orch = AnalysisOrchestrator()
    with pytest.raises(ValueError, match="(?i)disallowed|forbidden|ws_default|tenant"):
        orch.create_run(website_url="https://example.com", org_id="ws_default")

    with pytest.raises(ValueError, match="(?i)disallowed|forbidden|ws_default|tenant"):
        orch.create_run(website_url="https://example.com", org_id="   ws_default   ")


@pytest.mark.asyncio
async def test_orchestrator_execute_analysis_pipeline_rejects_ws_default_org_id():
    """
    T-TI-07.6: Verify that AnalysisOrchestrator.execute_analysis_pipeline rejects
    pipeline execution when run.org_id is 'ws_default' with ValueError.
    """
    orch = AnalysisOrchestrator()
    # Construct using model_construct to simulate legacy or corrupt record bypass
    run = AnalysisRun.model_construct(
        analysis_id=f"run_pipe_{uuid.uuid4().hex[:6]}",
        org_id="ws_default",
        workspace_id="ws_valid",
        website_url="https://example.com",
        status=AnalysisStage.QUEUED,
        created_at="2026-11-01T00:00:00Z",
        updated_at="2026-11-01T00:00:00Z",
    )
    orch.runs[run.analysis_id] = run

    with pytest.raises(ValueError, match="(?i)valid tenant org_id required|disallowed|forbidden|ws_default"):
        await orch.execute_analysis_pipeline(run.analysis_id, "https://example.com", max_pages=1)


def test_api_list_workspaces_rejects_insecure_default_org(auth_client):
    """
    T-TI-07.7 (Hardening): Verify that calling GET /api/v1/workspaces with
    user.org_id='org_default' is rejected with 403 Forbidden via require_org_context.
    """
    bad_user = UserIdentity(
        user_id="usr_insecure_default",
        org_id="org_default",
        email="insecure@test.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    with auth_client.as_user(bad_user) as client:
        resp = client.get("/api/v1/workspaces")
        assert resp.status_code == 403


def test_api_workspace_cross_tenant_returns_404(auth_client, user_a, user_b):
    """
    T-TI-07.8 (Hardening): Verify that accessing a workspace owned by Tenant A
    from Tenant B's context returns 404 Not Found to prevent workspace enumeration.
    """
    with auth_client.as_user(user_a) as client_a:
        resp = client_a.post("/api/v1/workspaces", json={"name": "Alpha Private", "slug": "alpha-priv"})
        assert resp.status_code == 200
        ws_id = resp.json()["id"]

    with auth_client.as_user(user_b) as client_b:
        resp = client_b.get(f"/api/v1/workspaces/{ws_id}")
        assert resp.status_code == 404
```

---

## 5. Remediation Implementation Guide for Workers

To make Suite 7 pass with 100% green tests, the worker agent must implement the following unified changes:

### 1. Define Canonical `FORBIDDEN_TENANT_IDENTIFIERS`
In `backend/app/domain/models.py`:
```python
FORBIDDEN_TENANT_IDENTIFIERS = frozenset({"org_default", "ws_default", "default"})
```

### 2. Update Validators in `backend/app/domain/models.py`
For `org_id` on `AnalysisRun`, `AnalysisRequest`, `Finding`, `ExecutiveReport`, `Integration`:
```python
if cleaned in FORBIDDEN_TENANT_IDENTIFIERS:
    raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
```
For `workspace_id` on all models:
```python
if v is not None:
    if not isinstance(v, str) or not v.strip() or v.strip() in FORBIDDEN_TENANT_IDENTIFIERS:
        raise ValueError(f"Insecure fallback workspace '{v}' is forbidden.")
    return v.strip()
return v
```

### 3. Update Validators in `backend/app/orchestration/mission/state.py`
In `MissionState`:
```python
FORBIDDEN_TENANT_IDENTIFIERS = {"org_default", "ws_default", "default"}

@field_validator("org_id")
@classmethod
def check_mission_org_id(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip() or v.strip() in FORBIDDEN_TENANT_IDENTIFIERS:
        raise ValueError(f"Insecure fallback tenant '{v}' is forbidden.")
    return v.strip()

@field_validator("workspace_id")
@classmethod
def check_mission_workspace_id(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip() or v.strip() in FORBIDDEN_TENANT_IDENTIFIERS:
        raise ValueError(f"Insecure fallback workspace '{v}' is forbidden.")
    return v.strip()
```

### 4. Update Schema in `backend/app/db/schema.py`
In `SQLITE_SCHEMA`:
```sql
CREATE TABLE IF NOT EXISTS audits (
    analysis_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    workspace_id TEXT,
    user_id TEXT NOT NULL,
    ...
);
CREATE INDEX IF NOT EXISTS idx_audits_org ON audits(org_id);
CREATE INDEX IF NOT EXISTS idx_audits_workspace ON audits(workspace_id);
```

### 5. Update Repository in `backend/app/db/repository.py`
In `save_run`:
Include `workspace_id` in SQL insert and update:
```sql
INSERT INTO audits (
    analysis_id, org_id, workspace_id, user_id, website_url, domain, ...
) VALUES (
    :analysis_id, :org_id, :workspace_id, :user_id, :website_url, :domain, ...
)
ON CONFLICT(analysis_id) DO UPDATE SET
    workspace_id = excluded.workspace_id,
    ...
```
In `params`:
```python
"workspace_id": getattr(run, "workspace_id", None),
```

### 6. Update Orchestrator in `backend/app/orchestration/orchestrator.py`
In `create_run`:
```python
clean_org = org_id.strip()
if clean_org in ("org_default", "ws_default", "default"):
    raise ValueError(f"Disallowed tenant identifier '{clean_org}'.")
```
In `execute_analysis_pipeline`:
```python
if not run or not run.org_id or run.org_id in ("org_default", "ws_default", "default"):
    raise ValueError(f"Cannot execute pipeline for analysis {analysis_id}: valid tenant org_id required, '{getattr(run, 'org_id', None)}' rejected.")
```

### 7. Update Workspaces Route in `backend/app/api/routes/platform/workspaces.py`
In `list_workspaces`:
```python
@router.get("")
async def list_workspaces(user: UserIdentity = Depends(get_current_user)):
    org_id = require_org_context(user)
    ...
```
In `_owned_workspace`:
```python
if workspace.get("org_id") != user.org_id and not Authorizer.is_system(user):
    raise HTTPException(status_code=404, detail="Workspace not found.")
```

---

## 6. Verification and Regression Commands

To verify before and after implementation:

```bash
# 1. Run all tenant isolation suites (Suites 1-6 + Suite 7)
pytest backend/tests/test_tenant_isolation.py -v

# 2. Run security suite
pytest backend/tests/security/test_tenant_isolation.py -v

# 3. Run regression across dependent caller suites
pytest backend/tests/test_visual_ux_and_analytics_connectors.py \
       backend/tests/test_google_connectors.py \
       backend/tests/test_radar_pulse.py \
       backend/tests/test_mission_director.py \
       backend/tests/test_external_authority.py \
       backend/tests/test_db_session_and_fail_fast.py -v
```
