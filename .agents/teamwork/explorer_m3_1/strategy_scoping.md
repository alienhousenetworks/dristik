# Technical Remediation Strategy: Milestone M3 — Domain & Orchestrator Scoping
## Elimination of `org_default` and `ws_default` with Strict Multi-Tenant Enforcement

**Author**: `explorer_m3_1`  
**Date**: 2026-10-31  
**Project**: Dristik AI  
**Milestone**: M3 (Features F11, F12, F13)  
**Status**: APPROVED TECHNICAL BLUEPRINT  

---

## 1. Executive Summary & Problem Diagnosis

### 1.1 The Vulnerability
In the legacy codebase, multiple domain models, orchestrator execution pipelines, connector stores, and database repository methods used `"org_default"` and `"ws_default"` as default string literals. When requests or background jobs executed without explicit tenant context, the system silently defaulted to this shared pseudo-tenant.

This created three severe architectural and security risks:
1. **Cross-Tenant Data Leakage**: Audit runs, external authority snapshots (Google Search Console, Google Analytics 4, PageSpeed), and platform connectors inadvertently shared the `"org_default"` partition.
2. **Authorization Bypass**: Unauthenticated HTTP callers hitting endpoints like `/api/v1/integrations/status` or `/api/v1/integrations/probe-ga4` received HTTP 200 responses reflecting `"org_default"` credentials rather than failing fast with `401 Unauthorized` or `403 Forbidden`.
3. **Repository Cross-Tenant Leaks**: `AuditRepository.list_runs()` defaulted to `org_id=None`, executing `SELECT * FROM audits ORDER BY created_at DESC LIMIT ?`, which exposed all audits across all organizations to any caller omitting an `org_id`.

### 1.2 Objective
Completely eliminate all silent fallbacks to `"org_default"` and `"ws_default"` across:
- `backend/app/domain/models.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/api/routes/integrations/google.py`
- `backend/app/api/routes/integrations/connectors.py`
- `backend/app/db/repository.py`
- `backend/app/connectors/store.py`
- `backend/app/identity/tenancy/manager.py`
- `backend/app/core/monitoring/radar.py`
- `backend/app/orchestration/mission/state.py` and `director.py`

Enforce strict multi-tenant isolation where:
- Unauthenticated requests fail immediately with `401 Unauthorized`.
- Missing or unauthorized tenant context fails immediately with `403 Forbidden` (at HTTP level) or `ValueError` (at repository/domain level).
- All 2,248 existing tests pass without regressions by explicitly supplying valid test tenant IDs (e.g., `'test_org_01'`).

---

## 2. Exhaustive Audit of Occurrences in `backend/app/`

| File Path | Line(s) | Code Snippet | Issue / Remediation |
|-----------|---------|--------------|---------------------|
| `backend/app/domain/models.py` | 125–126 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` in `Integration` | Remove defaults; require non-empty tenant strings with validation. |
| `backend/app/domain/models.py` | 333–334 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` in `Finding` | Change to `Optional[str] = None` to avoid breaking 300+ unit tests that test heuristic logic without persisting, while stamping tenant context during pipeline execution. |
| `backend/app/domain/models.py` | 2609–2610 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` in `ExecutiveReport` | Require valid tenant strings stamped from `AnalysisRun`. |
| `backend/app/domain/models.py` | 2716–2717 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`, `project_id = "proj_default"` in `AnalysisRequest` | Change to `Optional[str] = None`. In API handler, resolve from authenticated session (`user.org_id`). Reject client overrides unless system admin. |
| `backend/app/domain/models.py` | 2733–2734 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` in `AnalysisRun` | Require `org_id: str` without default. Add validator forbidding `"org_default"`. |
| `backend/app/orchestration/orchestrator.py` | 99 | `def create_run(..., org_id: str = "org_default", ...)` | Remove default `org_id`. Require mandatory `org_id: str`. |
| `backend/app/orchestration/orchestrator.py` | 282+ | `execute_analysis_pipeline(...)` | Add pre-flight guard: if `not run.org_id` or `run.org_id == "org_default"`, fail fast with `ValueError`. |
| `backend/app/orchestration/orchestrator.py` | 1533–1538, 1571 | `# Strict tenant context resolution: avoid leaking or querying shared "org_default" bucket` | Enforce clean guard: if `not tenant_project_id` or `tenant_project_id == "org_default"`, skip and log warning. |
| `backend/app/orchestration/orchestrator.py` | 2751 | `run = self.create_run(website_url=url)` in `resume_analysis_pipeline` | Bug fix: must pass `org_id=stored["org_id"]` from SQLite record. |
| `backend/app/orchestration/orchestrator.py` | 3034–3035 | `if tenant_id and tenant_id != "org_default" and domain_val:` | Retain strict check in DAG runner `node_honest_scoring`. |
| `backend/app/api/routes/integrations/google.py` | 43 | `org_id = user.org_id if user else "org_default"` in `get_integrations_status` | Replace `Depends(get_current_user_optional)` with `Depends(get_current_user)`. Fails unauthenticated requests with `401`. |
| `backend/app/api/routes/integrations/google.py` | 175 | `org_id = user.org_id if user else "org_default"` in `probe_ga4_status` | Replace `Depends(get_current_user_optional)` with `Depends(get_current_user)`. Fails unauthenticated requests with `401`. |
| `backend/app/api/routes/integrations/connectors.py` | 241–242 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` in `ConnectPlatformRequest` | Change to `Optional[str] = None`. Always bind to `user.org_id` in `connect_platform`. |
| `backend/app/api/routes/integrations/connectors.py` | 278 | `req.workspace_id = str(getattr(user, "workspace_id", None) or "ws_default")` | Use `f"ws_default_{user.org_id}"` instead of shared global `"ws_default"`. |
| `backend/app/api/routes/integrations/connectors.py` | 952–958 | `connector_store.add_integration(...)` in legacy `google_oauth_callback` | Extract `session_user` from cookie / session token; require `session_user.org_id` or abort. |
| `backend/app/db/repository.py` | 183–197 | `def list_runs(self, org_id: Optional[str] = None, limit: int = 50)` | Update to `def list_runs(self, org_id: str, workspace_id: Optional[str] = None, limit: int = 50)`. Require non-empty `org_id`; reject `None` or `"org_default"` with `ValueError`. |
| `backend/app/db/repository.py` | 174–181 | `def get_run(self, analysis_id: str)` | Add optional `org_id: Optional[str] = None`. When passed, verify run belongs to `org_id`. |
| `backend/app/db/repository.py` | 199–224 | `def delete_run(self, analysis_id: str, org_id: Optional[str] = None)` | Make `org_id: str` mandatory. Reject cross-tenant or unpartitioned deletes with `ValueError`. |
| `backend/app/connectors/store.py` | 176 | `def list_integrations(self, org_id: str = "org_default")` | Remove default `org_id`. Require `org_id: str`. If `not org_id` or `org_id == "org_default"`, return empty list. |
| `backend/app/connectors/store.py` | 318–319 | `def add_integration(..., org_id: str = "org_default", workspace_id: str = "ws_default", ...)` | Remove defaults. Require `org_id: str` and `workspace_id: Optional[str] = None`. Validate `org_id != "org_default"`. |
| `backend/app/identity/tenancy/manager.py` | 20–37 | Pre-seeding `org_default` and `ws_default` in `TenantManager.__init__` | Remove pre-seeded default org/workspace. Initialize registry clean and empty. |
| `backend/app/core/monitoring/radar.py` | 16, 354 | `org_id: str = "org_default"` in `RadarSubscription` and `create_subscription` | Remove default. Require `org_id: str`. Validate `org_id != "org_default"`. |
| `backend/app/orchestration/mission/state.py` | 103–104 | `org_id: str = "org_default"`, `workspace_id: str = "ws_default"` in `MissionState` | Require `org_id: str` and `workspace_id: str`. |
| `backend/app/orchestration/mission/director.py` | 26–27 | `def create_mission(..., org_id: str = "org_default", workspace_id: str = "ws_default")` | Remove defaults. Require `org_id: str` and `workspace_id: str`. In `orchestrator.py:349`, pass `run.org_id` and `run.workspace_id`. |
| `backend/app/crawl/audit/ledger.py` | 16, 40 | `workspace_id: str = "ws_default"` in `AuditEvent` and `record_event` | Change to `workspace_id: Optional[str] = None`. |

---

## 3. Domain Models Scoping Architecture (`models.py`)

### 3.1 Field Validation & Invariants
Domain entities that represent persisted tenant assets (`AnalysisRun`, `Integration`, `ExecutiveReport`) must enforce non-empty tenant scoping and explicitly reject `"org_default"`:

```python
from pydantic import BaseModel, Field, field_validator

def validate_tenant_org_id(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip():
        raise ValueError("Tenant org_id is required and cannot be empty.")
    cleaned = v.strip()
    if cleaned in ("org_default", "default"):
        raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
    return cleaned
```

### 3.2 The Critical `Finding` Model Insight
- **Observation**: Over 300 unit tests in `backend/tests/` instantiate `Finding(...)` directly without passing `org_id` or `workspace_id` (e.g. testing specialist heuristic rules, AST extractions, severity adjustments).
- **Database Schema**: The `audit_findings` database table does not store `org_id`; it references `analysis_id` (`FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id)`).
- **Strategy**: In `Finding`:
  ```python
  class Finding(BaseModel):
      finding_id: str
      org_id: Optional[str] = None
      workspace_id: Optional[str] = None
  ```
  - Removes `"org_default"` and `"ws_default"`.
  - Retains backward compatibility for unit tests creating standalone finding objects.
  - When emitted in a pipeline run, `run.org_id` is automatically propagated into findings during persistence or serialization.
  - If `org_id` is passed, validator ensures it is not `"org_default"`.

### 3.3 `AnalysisRequest` vs `AnalysisRun`
- In `AnalysisRequest`:
  ```python
  class AnalysisRequest(BaseModel):
      website_url: str
      org_id: Optional[str] = None
      workspace_id: Optional[str] = None
      project_id: Optional[str] = None
      ...
  ```
  Clients submitting audits via JSON do not need to send `org_id`; the API endpoint extracts the authenticated user's `user.org_id`. If a non-admin client sends an `org_id` differing from their own, the endpoint rejects it with `403 Forbidden`.
- In `AnalysisRun`:
  ```python
  class AnalysisRun(BaseModel):
      analysis_id: str
      org_id: str
      workspace_id: str = "default"
      website_url: str
      ...

      @field_validator("org_id")
      @classmethod
      def check_org_id(cls, v: str) -> str:
          return validate_tenant_org_id(cls, v)
  ```

---

## 4. Orchestrator Pipeline Scoping Architecture (`orchestrator.py`)

### 4.1 `orchestrator.create_run`
Signature update:
```python
def create_run(
    self,
    website_url: str,
    org_id: str,
    created_by: Optional[str] = None,
    target_pillars: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
) -> AnalysisRun:
    if not org_id or org_id == "org_default":
        raise ValueError("Cannot create AnalysisRun: valid tenant org_id required ('org_default' rejected).")
    
    analysis_id = f"run_{uuid.uuid4().hex[:10]}"
    now_str = datetime.now().isoformat()
    norm_pillars = [p.strip().lower() for p in target_pillars if p and p.strip().lower() in PILLAR_TO_SECTION] if target_pillars else None

    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id=org_id,
        workspace_id=workspace_id or f"ws_default_{org_id}",
        website_url=website_url,
        status=AnalysisStage.QUEUED,
        progress_percentage=0,
        current_step="Analysis Queued",
        created_at=now_str,
        updated_at=now_str,
        target_pillars=norm_pillars,
    )
    self.runs[analysis_id] = run
    try:
        self.repository.save_run(run)
    except Exception as e:
        logger.warning(f"Failed to persist initial audit run {analysis_id}: {e}")
    return run
```

### 4.2 Fail-Fast in `execute_analysis_pipeline`
At the beginning of `execute_analysis_pipeline`:
```python
run = self.runs.get(analysis_id)
if not run:
    stored = self.repository.get_run(analysis_id)
    if stored:
        run = self.get_run(analysis_id)

if not run or not run.org_id or run.org_id == "org_default":
    raise ValueError(f"Cannot execute pipeline for analysis {analysis_id}: valid tenant org_id required, 'org_default' rejected.")
```

### 4.3 Bug Fix in `resume_analysis_pipeline` (Line 2751)
In `resume_analysis_pipeline`:
```python
run = self.runs.get(analysis_id)
if not run:
    stored = self.repository.get_run(analysis_id)
    if not stored:
        return False
    run = self.create_run(website_url=url, org_id=stored["org_id"])
    run.analysis_id = analysis_id
    self.runs[analysis_id] = run
```

### 4.4 Mission Director Invocation (Line 349)
Update from:
```python
mission_state = self.mission_director.create_mission(
    target_url=website_url,
    audit_type="standard_growth",
    max_pages=crawl_limit
)
```
To:
```python
mission_state = self.mission_director.create_mission(
    target_url=website_url,
    audit_type="standard_growth",
    max_pages=crawl_limit,
    org_id=run.org_id,
    workspace_id=run.workspace_id,
)
```

---

## 5. Connectors & External Authority Scoping Architecture

### 5.1 Google Integration Routes (`backend/app/api/routes/integrations/google.py`)
Lines 37–44 and 165–176 previously had:
```python
@router.get("/status")
def get_integrations_status(user: Optional[UserIdentity] = Depends(get_current_user_optional)):
    org_id = user.org_id if user else "org_default"
```
Remediation:
```python
@router.get("/status")
def get_integrations_status(user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    """Returns provider status for the signed-in organization."""
    if not user.org_id or user.org_id == "org_default":
        raise HTTPException(status_code=403, detail="Valid organization context required.")
    
    from app.connectors.store import connector_store
    from app.domain.enums import ConnectorType, ConnectorHealthStatus

    org_id = user.org_id
    integrations = connector_store.list_integrations(org_id)
    ...
```
Apply the identical pattern to `probe_ga4_status` at line 175. This immediately rejects unauthenticated callers with `401 Unauthorized` and tenant-less callers with `403 Forbidden`.

### 5.2 External Authority Audit Bridge (`audit_bridge.py`)
In `backend/app/connectors/authority/audit_bridge.py`:
```python
def build_audit_attachment(
    *,
    project_id: str,
    domain: str,
    period_days: int = 28,
    pages: Optional[List[Any]] = None,
    evidence_store: Any = None,
) -> Dict[str, Any]:
    if not project_id or project_id == "org_default":
        logger.info("External authority attachment skipped: invalid or 'org_default' project_id.")
        return {
            "report": _unavailable("missing_tenant_context"),
            "domain_findings": [],
        }
```

### 5.3 Connector Store (`backend/app/connectors/store.py`)
- `list_integrations`:
  ```python
  def list_integrations(self, org_id: str) -> List[Integration]:
      if not org_id or org_id == "org_default":
          return []
      return [i for i in self._integrations.values() if i.org_id == org_id]
  ```
- `add_integration`:
  ```python
  def add_integration(
      self,
      provider: ConnectorType,
      name: str,
      target_url: str,
      credentials: ConnectorCredentials,
      repository: Optional[str] = None,
      branch: Optional[str] = "main",
      org_id: str,
      workspace_id: Optional[str] = None,
      settings: Optional[Dict[str, Any]] = None
  ) -> Integration:
      if not org_id or org_id == "org_default":
          raise ValueError("Valid tenant org_id required for integration; 'org_default' rejected.")
  ```

---

## 6. Database & Repository Scoping Architecture (`repository.py`)

### 6.1 `AuditRepository.list_runs` Invariant
Contract specified in `PROJECT.md`:
`- AuditRepository.list_runs(org_id: str, workspace_id: Optional[str])`
- Invariant: `org_id` is mandatory non-empty string. Rejects empty/None `org_id` with `ValueError` or `Forbidden`.

Implementation:
```python
def list_runs(
    self,
    org_id: str,
    workspace_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lists recent audit runs strictly partitioned by org_id."""
    if not org_id or not isinstance(org_id, str) or not org_id.strip() or org_id.strip() == "org_default":
        raise ValueError("org_id is mandatory and non-empty for list_runs; fallback to all tenants or 'org_default' is forbidden.")
    
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
```

### 6.2 `AuditRepository.get_run`
Update `get_run` to accept optional `org_id: Optional[str] = None`:
```python
def get_run(self, analysis_id: str, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches an audit record by analysis_id, optionally verifying org_id ownership."""
    with self._lock:
        with self._get_conn() as conn:
            if org_id:
                cur = conn.execute(
                    "SELECT * FROM audits WHERE analysis_id = ? AND org_id = ?",
                    (analysis_id, org_id),
                )
            else:
                cur = conn.execute("SELECT * FROM audits WHERE analysis_id = ?", (analysis_id,))
            row = cur.fetchone()
            return dict(row) if row else None
```

### 6.3 `AuditRepository.delete_run`
Make `org_id: str` mandatory:
```python
def delete_run(self, analysis_id: str, org_id: str) -> bool:
    """Deletes one audit and its child records, strictly requiring matching org_id ownership."""
    if not org_id or org_id == "org_default":
        raise ValueError("org_id is mandatory to delete an audit run; unauthenticated deletion forbidden.")
    
    child_tables = (
        "audit_checkpoints",
        "audit_pages",
        "audit_evidence",
        "audit_claims",
        "audit_findings",
        "agent_telemetry",
    )
    with self._lock:
        with self._get_conn() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            owned = conn.execute(
                "SELECT 1 FROM audits WHERE analysis_id = ? AND org_id = ?",
                (analysis_id, org_id),
            ).fetchone()
            if not owned:
                return False
            for table in child_tables:
                conn.execute(f"DELETE FROM {table} WHERE analysis_id = ?", (analysis_id,))
            cur = conn.execute("DELETE FROM audits WHERE analysis_id = ? AND org_id = ?", (analysis_id, org_id))
            conn.commit()
            return cur.rowcount > 0
```

---

## 7. HTTP Route & Fast-Fail Invariant Enforcement

### 7.1 `require_org_context` Helper Function
In `backend/app/identity/access.py` (and re-exported on `deps.py`):
```python
def require_org_context(user: Optional[UserIdentity], org_id: Optional[str]) -> str:
    """
    Enforces tenant context invariant:
    - If user is missing/unauthenticated: raises 401 Unauthorized
    - If org_id is missing or user cannot access org_id: raises 403 Forbidden
    """
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    if not org_id or org_id == "org_default":
        raise HTTPException(status_code=403, detail="Valid organization context required.")
    if not Authorizer.can_access_org(user, org_id):
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden.")
    return org_id
```

### 7.2 API Endpoint Updates
- `backend/app/api/routes/audits/analyses.py`:
  - `start_analysis`:
    ```python
    org_id = user.org_id
    if request.org_id and request.org_id != user.org_id:
        if not Authorizer.is_system(user):
            raise HTTPException(status_code=403, detail="Cross-tenant audit creation forbidden.")
        org_id = request.org_id
    
    run = orchestrator.create_run(
        url,
        org_id=org_id,
        created_by=user.user_id,
        target_pillars=request.target_pillars,
    )
    ```
  - `list_analyses`:
    ```python
    org_id = require_org_context(user, user.org_id)
    runs = repo.list_runs(org_id=org_id, limit=limit)
    ```
  - `delete_analysis`:
    ```python
    run = require_analysis(analysis_id, user, permission="mission:delete")
    removed = orchestrator.repository.delete_run(run.analysis_id, org_id=user.org_id)
    ```

---

## 8. Test Suite Remediation Strategy (Non-Regression)

### 8.1 Callers Requiring Explicit Test Tenant (`'test_org_01'`)
Below is the precise list of test files and lines where callers previously omitted `org_id` and relied on default fallback:

1. **`backend/tests/test_audit_persistence_and_restore.py`**:
   - Line 81: `AnalysisRun(analysis_id=analysis_id, website_url="https://acme-test.org", ...)`
     → Add `org_id="test_org_01"`
   - Line 111: `runs = repo.list_runs(limit=20)`
     → Update to `runs = repo.list_runs(org_id="test_org_01", limit=20)`
2. **`backend/tests/test_selective_pillars.py`**:
   - Line 41: `AnalysisRun(analysis_id="run_test_pillars", website_url="https://example.com", ...)`
     → Add `org_id="test_org_01"`
   - Line 85: `orchestrator.create_run("https://example.com", target_pillars=["seo"])`
     → Add `org_id="test_org_01"`
3. **`backend/tests/test_pipeline.py`**:
   - Line 349: `orchestrator.create_run("https://dristik-demo.ai")`
     → Update to `orchestrator.create_run("https://dristik-demo.ai", org_id="test_org_01")`
4. **`backend/tests/test_multi_page.py`**:
   - Line 116: `orchestrator.create_run("https://supabase.com")`
     → Update to `orchestrator.create_run("https://supabase.com", org_id="test_org_01")`
5. **`backend/tests/test_scoring_timing_and_honest_flag.py`**:
   - Lines 453, 565, 696: `test_orch.create_run(...)`
     → Add `org_id="test_org_01"`
   - Lines 224–235: `test_external_authority_skipped_when_tenant_is_org_default`:
     Update to verify that passing `"org_default"` to `AnalysisRun` or `orchestrator.create_run` raises `ValueError`, or verify external authority attachment refuses `'org_default'`.
6. **`backend/tests/test_visual_ux_and_analytics_connectors.py`**:
   - Line 175: `connector_store.add_integration(...)`
     → Add `org_id="test_org_01", workspace_id="ws_test_01"`
7. **`backend/tests/test_google_connectors.py`**:
   - Line 135: `connector_store.add_integration(...)`
     → Add `org_id="test_org_01", workspace_id="ws_test_01"`
8. **`backend/tests/test_mission_director.py`**:
   - Lines 15, 54: `director.create_mission(...)`
     → Add `org_id="test_org_01", workspace_id="ws_test_01"`
9. **`backend/tests/test_radar_pulse.py`**:
   - Lines 24, 33, 75: `service.create_subscription(...)`
     → Add `org_id="test_org_01"`

### 8.2 New Tenant Isolation Unit Tests to Add
Add `backend/tests/test_tenant_isolation_scoping.py` testing:
1. `test_analysis_run_rejects_org_default_and_empty`:
   - Instantiating `AnalysisRun` with `org_id="org_default"` or `""` raises `ValidationError` / `ValueError`.
2. `test_audit_repository_list_runs_requires_valid_org_id`:
   - Calling `repo.list_runs(None)` or `repo.list_runs("org_default")` raises `ValueError`.
3. `test_cross_tenant_audit_access_forbidden`:
   - Client authenticated as Tenant A requesting Tenant B's audit receives `404 Not Found` (or `403 Forbidden`).
4. `test_unauthenticated_integrations_returns_401`:
   - Calling `GET /api/v1/integrations/status` without cookie/token returns `401 Unauthorized` instead of falling back to `"org_default"`.
5. `test_connector_store_rejects_org_default`:
   - Calling `connector_store.add_integration(..., org_id="org_default")` raises `ValueError`.

---

## 9. Implementation Checklist for Fixer Agent

- [ ] **Step 1**: Update `backend/app/domain/models.py`:
  - `Integration`: remove default `org_id` and `workspace_id`.
  - `Finding`: change `org_id` and `workspace_id` to `Optional[str] = None`.
  - `ExecutiveReport`: require `org_id: str`.
  - `AnalysisRequest`: change `org_id`, `workspace_id`, `project_id` to `Optional[str] = None`.
  - `AnalysisRun`: require `org_id: str`, add validator rejecting `"org_default"`.
- [ ] **Step 2**: Update `backend/app/orchestration/orchestrator.py`:
  - `create_run`: make `org_id: str` required without default.
  - `execute_analysis_pipeline`: add fail-fast check if `not run.org_id or run.org_id == "org_default"`.
  - `resume_analysis_pipeline`: pass `org_id=stored["org_id"]` at line 2751.
  - `create_mission` call at line 349: pass `run.org_id` and `run.workspace_id`.
- [ ] **Step 3**: Update `backend/app/connectors/authority/audit_bridge.py`:
  - Reject `project_id == "org_default"` or empty `project_id`.
- [ ] **Step 4**: Update `backend/app/api/routes/integrations/google.py`:
  - Change `get_current_user_optional` to `get_current_user` on `/status` and `/probe-ga4`.
  - Remove `"org_default"` fallback.
- [ ] **Step 5**: Update `backend/app/db/repository.py`:
  - `list_runs`: make `org_id: str` required; raise `ValueError` on empty or `"org_default"`.
  - `delete_run`: make `org_id: str` required.
  - `get_run`: support optional `org_id` filtering.
- [ ] **Step 6**: Update `backend/app/connectors/store.py`:
  - Remove defaults from `list_integrations` and `add_integration`.
- [ ] **Step 7**: Update `backend/app/identity/tenancy/manager.py`:
  - Remove pre-seeded `org_default` and `ws_default`.
- [ ] **Step 8**: Update `backend/app/core/monitoring/radar.py`, `mission/state.py`, `director.py`, `crawl/audit/ledger.py`.
- [ ] **Step 9**: Update test callers in `backend/tests/` that omitted `org_id` to pass `'test_org_01'`.
- [ ] **Step 10**: Add new test suite `backend/tests/test_tenant_isolation_scoping.py`.
- [ ] **Step 11**: Run full pytest test suite across `backend/` and verify all tests pass.
