# Remediation Strategy & Specification: Defect 2 (Asymmetric Insecure Default Validation Leaks)

**Author**: `explorer_m3_r2_2` (Teamwork Explorer / Senior Principal Engineer)  
**Parent Agent**: `c6f6f3f2-acb1-4d19-b16f-9f0aba77d9f4`  
**Target Milestone**: M3 Remediation (Defect 2 Harmonization)  
**Reference Findings**:
- Challenger M3.1 empirical report: `.agents/teamwork/challenger_m3_1/handoff.md` (Observation 1.2, Observation 1.4, Section 4.2)
- Worker M3.4 handoff: `.agents/teamwork/worker_m3_4/handoff.md`

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 The Vulnerability
During empirical validation of Milestone M3, Challenger M3.1 revealed an **asymmetric validation leak** across the domain models, orchestrator runtime entry points, mission state, and the cryptographic audit ledger.

Specifically:
1. **Asymmetric Leak on `org_id`**: While `"org_default"` and `"default"` were blocked on `org_id`, the identifier `"ws_default"` was **completely permitted**. An attacker or misconfigured client could instantiate domain models (`AnalysisRun`, `AnalysisRequest`, `Finding`, `ExecutiveReport`, `Integration`, `MissionState`, `AuditEvent`) with `org_id="ws_default"`.
2. **Orchestrator Pipeline Bypass**: `orchestrator.create_run(..., org_id="ws_default")` and `orchestrator.execute_analysis_pipeline(..., run.org_id="ws_default")` permitted execution because line 107 and line 310 only checked `in ("org_default", "default")`.
3. **Asymmetric Leak on `workspace_id`**: While `"ws_default"` was blocked on `workspace_id`, the identifier `"org_default"` and `"default"` were **completely permitted**.
4. **Whitespace Bypass on `workspace_id`**: `workspace_id` validators only checked `if v is not None and v.strip() == "ws_default":`. Consequently, whitespace-only strings like `"   "` or empty strings `""` were permitted without sanitization or rejection.
5. **Case-Sensitivity Bypass**: None of the validators checked case insensitivity (e.g., `"ORG_DEFAULT"`, `"WS_DEFAULT"`, or `"Default"` would pass).

### 1.2 Empirical Reproduction
An empirical test harness verified that prior to remediation, every single domain model and orchestrator entry point accepted `"ws_default"` as a valid `org_id` and accepted `"org_default"` and `"   "` as a valid `workspace_id`:

```python
# PROBE CONFIRMATION (Observed Vulnerabilities):
AnalysisRun(analysis_id='r1', org_id='ws_default', ...)              # ALLOWED (LEAK)
AnalysisRun(..., org_id='org_valid', workspace_id='org_default')     # ALLOWED (LEAK)
AnalysisRun(..., org_id='org_valid', workspace_id='   ')             # ALLOWED (LEAK)
orchestrator.create_run('https://example.com', org_id='ws_default')   # ALLOWED (LEAK)
Finding(..., org_id='ws_default', workspace_id='org_default')        # ALLOWED (LEAK)
ExecutiveReport(..., org_id='ws_default', workspace_id='org_default') # ALLOWED (LEAK)
Integration(..., org_id='ws_default', workspace_id='org_default')    # ALLOWED (LEAK)
MissionState(..., org_id='ws_default', workspace_id='org_default')   # ALLOWED (LEAK)
AuditEvent(..., org_id='ws_default', workspace_id='org_default')     # ALLOWED (LEAK)
```

### 1.3 Root Cause
The vulnerability stems from **isolated, copy-pasted validation checks** implemented independently in each model and service without a single source of truth or bidirectional symmetry:
- `org_id` validator logic: `if cleaned in ("org_default", "default"):` (missing `"ws_default"`).
- `workspace_id` validator logic: `if v is not None and v.strip() == "ws_default":` (missing `"org_default"`, `"default"`, and `not v.strip()`).
- Each file independently reimplemented slight variations of these checks, resulting in validation drift.

---

## 2. Architecture of Remediation: Unified Symmetric Validation

To guarantee foolproof tenant isolation and eliminate repetitive, brittle checks, the remediation introduces:

1. **Single Source of Truth (`FORBIDDEN_TENANT_IDENTIFIERS`)**:
   Defined as a shared immutable set in `backend/app/core/constants.py` and exported through `backend/app/domain/models.py`:
   ```python
   FORBIDDEN_TENANT_IDENTIFIERS = {"org_default", "ws_default", "default"}
   ```
2. **Case-Insensitive Stripping**:
   Every tenant identifier is stripped and lowercased before comparison against `FORBIDDEN_TENANT_IDENTIFIERS`:
   ```python
   cleaned = v.strip()
   if cleaned.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
       raise ValueError(...)
   ```
3. **Reusable Domain Validation Helpers (`validate_tenant_org_id` and `validate_tenant_workspace_id`)**:
   Centralized in `backend/app/domain/models.py`. Both helpers enforce identical, symmetric rules:
   - Rejects any value in `FORBIDDEN_TENANT_IDENTIFIERS` (case-insensitive).
   - Rejects whitespace-only or empty strings.
   - For `required=True`, rejects `None`.
   - For `required=False`, accepts `None`, but validates non-empty string if provided.
   - Returns the sanitized (stripped) string.

---

## 3. Detailed File Modifications & Exact Code Snippets

### File 1: `backend/app/core/constants.py`

#### Rationale
`backend/app/core/constants.py` has zero internal imports and serves as the single source of truth for global constants without circular dependency risk.

#### Exact Code Snippet (Lines 8-12)
**Before**:
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
```

**After**:
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Shared tenant security invariants: forbidden default and fallback identifiers
FORBIDDEN_TENANT_IDENTIFIERS = {"org_default", "ws_default", "default"}
```

---

### File 2: `backend/app/domain/models.py`

#### Rationale
Define reusable validator helpers `validate_tenant_org_id` and `validate_tenant_workspace_id` near the top of the file, then update the `@field_validator` methods across all 5 domain models: `Integration`, `Finding`, `ExecutiveReport`, `AnalysisRequest`, and `AnalysisRun`.

#### Step 2.1: Import and Helper Functions (Insert around line 48, right after imports)
```python
from app.core.constants import FORBIDDEN_TENANT_IDENTIFIERS

def validate_tenant_org_id(v: Optional[str], required: bool = True) -> Optional[str]:
    """Validates organization tenant identifier against forbidden fallback defaults."""
    if v is None:
        if required:
            raise ValueError("Tenant org_id is required and cannot be empty.")
        return None
    if not isinstance(v, str) or not v.strip():
        if required:
            raise ValueError("Tenant org_id is required and cannot be empty.")
        raise ValueError(f"Insecure fallback tenant '{v}' is forbidden.")
    cleaned = v.strip()
    if cleaned.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
        raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
    return cleaned


def validate_tenant_workspace_id(v: Optional[str], required: bool = False) -> Optional[str]:
    """Validates workspace identifier against whitespace and forbidden fallback defaults."""
    if v is None:
        if required:
            raise ValueError("Tenant workspace_id is required and cannot be empty.")
        return None
    if not isinstance(v, str) or not v.strip():
        raise ValueError("Insecure fallback workspace cannot be empty or whitespace-only.")
    cleaned = v.strip()
    if cleaned.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
        raise ValueError(f"Insecure fallback workspace '{cleaned}' is forbidden.")
    return cleaned
```

#### Step 2.2: Update `Integration` (Lines 140-156)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_org_id(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        cleaned = v.strip()
        if cleaned in ("org_default", "default"):
            raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
        return cleaned

    @field_validator("workspace_id")
    @classmethod
    def check_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_org_id(cls, v: str) -> str:
        return validate_tenant_org_id(v, required=True)

    @field_validator("workspace_id")
    @classmethod
    def check_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_workspace_id(v, required=False)
```

#### Step 2.3: Update `Finding` (Lines 355-369)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_finding_org_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip() or v.strip() in ("org_default", "default"):
                raise ValueError(f"Insecure fallback tenant '{v}' is forbidden.")
            return v.strip()
        return v

    @field_validator("workspace_id")
    @classmethod
    def check_finding_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_finding_org_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_org_id(v, required=False)

    @field_validator("workspace_id")
    @classmethod
    def check_finding_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_workspace_id(v, required=False)
```

#### Step 2.4: Update `ExecutiveReport` (Lines 2650-2665)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_report_org_id(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        cleaned = v.strip()
        if cleaned in ("org_default", "default"):
            raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
        return cleaned

    @field_validator("workspace_id")
    @classmethod
    def check_report_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_report_org_id(cls, v: str) -> str:
        return validate_tenant_org_id(v, required=True)

    @field_validator("workspace_id")
    @classmethod
    def check_report_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_workspace_id(v, required=False)
```

#### Step 2.5: Update `AnalysisRequest` (Lines 2782-2796)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_request_org_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip() or v.strip() in ("org_default", "default"):
                raise ValueError(f"Insecure fallback tenant '{v}' is forbidden.")
            return v.strip()
        return v

    @field_validator("workspace_id")
    @classmethod
    def check_request_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_request_org_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_org_id(v, required=False)

    @field_validator("workspace_id")
    @classmethod
    def check_request_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_workspace_id(v, required=False)
```

#### Step 2.6: Update `AnalysisRun` (Lines 2817-2833)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_run_org_id(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        cleaned = v.strip()
        if cleaned in ("org_default", "default"):
            raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
        return cleaned

    @field_validator("workspace_id")
    @classmethod
    def check_run_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_run_org_id(cls, v: str) -> str:
        return validate_tenant_org_id(v, required=True)

    @field_validator("workspace_id")
    @classmethod
    def check_run_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_tenant_workspace_id(v, required=False)
```

---

### File 3: `backend/app/orchestration/orchestrator.py`

#### Step 3.1: Import `FORBIDDEN_TENANT_IDENTIFIERS` (Line 18)
```python
from app.core.constants import FORBIDDEN_TENANT_IDENTIFIERS
```

#### Step 3.2: `create_run` Method (Lines 104-118)
**Before**:
```python
        if not org_id or not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        clean_org = org_id.strip()
        if clean_org in ("org_default", "default"):
            raise ValueError(f"Disallowed tenant identifier '{clean_org}'.")

        analysis_id = f"run_{uuid.uuid4().hex[:10]}"
        now_str = datetime.now().isoformat()
        norm_pillars = [p.strip().lower() for p in target_pillars if p and p.strip().lower() in PILLAR_TO_SECTION] if target_pillars else None

        run = AnalysisRun(
            analysis_id=analysis_id,
            org_id=clean_org,
            workspace_id=workspace_id or f"ws_default_{clean_org}",
            website_url=website_url,
```

**After**:
```python
        if not org_id or not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        clean_org = org_id.strip()
        if clean_org.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
            raise ValueError(f"Disallowed tenant identifier '{clean_org}'.")

        clean_ws = None
        if workspace_id is not None:
            if not isinstance(workspace_id, str) or not workspace_id.strip():
                raise ValueError("Tenant workspace_id cannot be empty or whitespace-only.")
            clean_ws = workspace_id.strip()
            if clean_ws.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
                raise ValueError(f"Disallowed workspace identifier '{clean_ws}'.")
        else:
            clean_ws = f"ws_default_{clean_org}"

        analysis_id = f"run_{uuid.uuid4().hex[:10]}"
        now_str = datetime.now().isoformat()
        norm_pillars = [p.strip().lower() for p in target_pillars if p and p.strip().lower() in PILLAR_TO_SECTION] if target_pillars else None

        run = AnalysisRun(
            analysis_id=analysis_id,
            org_id=clean_org,
            workspace_id=clean_ws,
            website_url=website_url,
```

#### Step 3.3: `execute_analysis_pipeline` Method (Lines 310-312)
**Before**:
```python
        if not run or not run.org_id or run.org_id in ("org_default", "default"):
            raise ValueError(f"Cannot execute pipeline for analysis {analysis_id}: valid tenant org_id required, 'org_default' rejected.")
```

**After**:
```python
        clean_org = run.org_id.strip() if (run and isinstance(run.org_id, str)) else ""
        if not run or not clean_org or clean_org.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
            raise ValueError(f"Cannot execute pipeline for analysis {analysis_id}: valid tenant org_id required, 'org_default' rejected.")
```

#### Step 3.4: `resume_analysis_pipeline` Method (Lines 2725-2775)
Add guard to verify that persisted and in-memory runs have valid tenant IDs prior to launching execution:
```python
        stored = self.repository.get_run(analysis_id)
        if not stored:
            logger.warning(f"Cannot resume analysis {analysis_id}: not found in repository.")
            return False

        stored_org = stored.get("org_id")
        clean_stored_org = stored_org.strip() if isinstance(stored_org, str) else ""
        if not clean_stored_org or clean_stored_org.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
            logger.warning(f"Cannot resume analysis {analysis_id}: invalid or forbidden tenant '{stored_org}'.")
            return False
```

#### Step 3.5: External Authority Guards in Orchestrator (Lines 1553, 1556, 3059)
**Line 1553-1556 Before**:
```python
                tenant_project_id = getattr(run, "org_id", None)
                if not tenant_project_id or tenant_project_id == "org_default":
                    tenant_project_id = blackboard.blackboard_state.get("org_id") or getattr(blackboard, "org_id", None)

                if tenant_project_id and tenant_project_id != "org_default":
```
**After**:
```python
                tenant_project_id = getattr(run, "org_id", None)
                clean_tenant = tenant_project_id.strip().lower() if isinstance(tenant_project_id, str) else ""
                if not clean_tenant or clean_tenant in FORBIDDEN_TENANT_IDENTIFIERS:
                    tenant_project_id = blackboard.blackboard_state.get("org_id") or getattr(blackboard, "org_id", None)

                clean_tenant = tenant_project_id.strip().lower() if isinstance(tenant_project_id, str) else ""
                if clean_tenant and clean_tenant not in FORBIDDEN_TENANT_IDENTIFIERS:
```

**Line 3059 Before**:
```python
                        if tenant_id and tenant_id != "org_default" and domain_val:
```
**After**:
```python
                        clean_tenant = tenant_id.strip().lower() if isinstance(tenant_id, str) else ""
                        if clean_tenant and clean_tenant not in FORBIDDEN_TENANT_IDENTIFIERS and domain_val:
```

---

### File 4: `backend/app/orchestration/mission/state.py`

#### Rationale
`MissionState` currently accepts `org_id="ws_default"` and accepts `workspace_id="org_default"` and `"   "`.

#### Exact Code Snippet (Lines 108-121)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_mission_org_id(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip() or v.strip() in ("org_default", "default"):
            raise ValueError(f"Insecure fallback tenant '{v}' is forbidden.")
        return v.strip()

    @field_validator("workspace_id")
    @classmethod
    def check_mission_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_mission_org_id(cls, v: str) -> str:
        from app.domain.models import validate_tenant_org_id
        return validate_tenant_org_id(v, required=True)

    @field_validator("workspace_id")
    @classmethod
    def check_mission_workspace_id(cls, v: str) -> str:
        from app.domain.models import validate_tenant_workspace_id
        return validate_tenant_workspace_id(v, required=True)
```

---

### File 5: `backend/app/crawl/audit/ledger.py`

#### Rationale
`AuditEvent` currently accepts `org_id="ws_default"` and accepts `workspace_id="org_default"` and `"   "`.

#### Exact Code Snippet (Lines 26-39)
**Before**:
```python
    @field_validator("org_id")
    @classmethod
    def check_event_org_id(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip() or v.strip() in ("org_default", "default"):
            raise ValueError(f"Insecure fallback tenant '{v}' is forbidden.")
        return v.strip()

    @field_validator("workspace_id")
    @classmethod
    def check_event_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "ws_default":
            raise ValueError("Insecure fallback workspace 'ws_default' is forbidden.")
        return v
```

**After**:
```python
    @field_validator("org_id")
    @classmethod
    def check_event_org_id(cls, v: str) -> str:
        from app.core.constants import FORBIDDEN_TENANT_IDENTIFIERS
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        cleaned = v.strip()
        if cleaned.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
            raise ValueError(f"Insecure fallback tenant '{cleaned}' is forbidden.")
        return cleaned

    @field_validator("workspace_id")
    @classmethod
    def check_event_workspace_id(cls, v: Optional[str]) -> Optional[str]:
        from app.core.constants import FORBIDDEN_TENANT_IDENTIFIERS
        if v is not None:
            if not isinstance(v, str) or not v.strip():
                raise ValueError("Insecure fallback workspace cannot be empty or whitespace-only.")
            cleaned = v.strip()
            if cleaned.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
                raise ValueError(f"Insecure fallback workspace '{cleaned}' is forbidden.")
            return cleaned
        return v
```

---

### Extended Systemic Harmonization (Recommended Secondary Targets)

To ensure 100% uniformity across all system layers:

1. **`backend/app/orchestration/mission/director.py` (Lines 29-32)**:
   ```python
   # Replace:
   # if not org_id or ... in ("org_default", "default"):
   # if not workspace_id or ... == "ws_default":
   # With:
   from app.core.constants import FORBIDDEN_TENANT_IDENTIFIERS
   if not org_id or not isinstance(org_id, str) or not org_id.strip() or org_id.strip().lower() in FORBIDDEN_TENANT_IDENTIFIERS:
       raise ValueError(f"Valid tenant org_id required for mission; '{org_id}' is forbidden.")
   if not workspace_id or not isinstance(workspace_id, str) or not workspace_id.strip() or workspace_id.strip().lower() in FORBIDDEN_TENANT_IDENTIFIERS:
       raise ValueError(f"Valid workspace_id required for mission; '{workspace_id}' is forbidden.")
   ```

2. **`backend/app/connectors/store.py` (Lines 177, 325)**:
   Update `in ("org_default", "default")` to `clean_org_id.lower() in FORBIDDEN_TENANT_IDENTIFIERS`.

3. **`backend/app/db/repository.py` (Lines 195, 215)**:
   Update `in ("org_default", "default")` to `clean_org_id.lower() in FORBIDDEN_TENANT_IDENTIFIERS`.

4. **`backend/app/identity/access.py` (Line 28)**:
   Update `org_id in ("org_default", "default")` to `org_id.strip().lower() in FORBIDDEN_TENANT_IDENTIFIERS`.

---

## 4. Test Suite Additions: `backend/tests/test_tenant_isolation.py`

The implementing worker should append the following test suite to `backend/tests/test_tenant_isolation.py` to continuously guard against asymmetric validation leaks:

```python
# =============================================================================
# Suite 7: T-TI-07 Symmetric Validation and Insecure Default Rejection
# =============================================================================

@pytest.mark.parametrize("forbidden_id", [
    "org_default", "ws_default", "default",
    "ORG_DEFAULT", "WS_DEFAULT", "DEFAULT",
    "  org_default  ", "  ws_default  ",
])
def test_models_reject_symmetric_forbidden_org_id(forbidden_id):
    """Verifies that all models reject all forbidden identifiers on org_id."""
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|tenant"):
        AnalysisRun(analysis_id="r1", org_id=forbidden_id, website_url="https://example.com", created_at="..", updated_at="..")
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|tenant"):
        AnalysisRequest(website_url="https://example.com", org_id=forbidden_id)
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|tenant"):
        Finding(finding_id="f1", category=Category.TECHNICAL_SEO, severity=Severity.LOW, org_id=forbidden_id)
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|tenant"):
        ExecutiveReport(
            report_id="rep1", website_url="https://example.com", domain="example.com",
            scores=OverallScoreResult(overall_score=50, grade="C"),
            story_summary="s", primary_strategic_opportunity="o",
            consultant_advice_what_to_ignore="i", org_id=forbidden_id
        )
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|tenant"):
        Integration(integration_id="i1", name="int", target_url="https://example.com", created_at="..", org_id=forbidden_id)


@pytest.mark.parametrize("forbidden_id", [
    "org_default", "ws_default", "default",
    "ORG_DEFAULT", "WS_DEFAULT", "DEFAULT",
    "  org_default  ", "  ws_default  ",
])
def test_models_reject_symmetric_forbidden_workspace_id(forbidden_id):
    """Verifies that all models reject all forbidden identifiers on workspace_id."""
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|workspace"):
        AnalysisRun(analysis_id="r1", org_id="org_alpha", workspace_id=forbidden_id, website_url="https://example.com", created_at="..", updated_at="..")
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|workspace"):
        AnalysisRequest(website_url="https://example.com", workspace_id=forbidden_id)
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|workspace"):
        Finding(finding_id="f1", category=Category.TECHNICAL_SEO, severity=Severity.LOW, workspace_id=forbidden_id)
    with pytest.raises((ValueError, Exception), match="(?i)forbidden|workspace"):
        ExecutiveReport(
            report_id="rep1", website_url="https://example.com", domain="example.com",
            scores=OverallScoreResult(overall_score=50, grade="C"),
            story_summary="s", primary_strategic_opportunity="o",
            consultant_advice_what_to_ignore="i", org_id="org_alpha", workspace_id=forbidden_id
        )


@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n  "])
def test_models_reject_whitespace_workspace_id(empty_val):
    """Verifies that whitespace-only workspace_id strings are strictly rejected."""
    with pytest.raises((ValueError, Exception), match="(?i)workspace"):
        AnalysisRun(analysis_id="r1", org_id="org_alpha", workspace_id=empty_val, website_url="https://example.com", created_at="..", updated_at="..")
    with pytest.raises((ValueError, Exception), match="(?i)workspace"):
        AnalysisRequest(website_url="https://example.com", workspace_id=empty_val)
    with pytest.raises((ValueError, Exception), match="(?i)workspace"):
        Finding(finding_id="f1", category=Category.TECHNICAL_SEO, severity=Severity.LOW, workspace_id=empty_val)


def test_orchestrator_create_run_rejects_ws_default_and_forbidden_workspaces():
    orch = AnalysisOrchestrator()
    with pytest.raises(ValueError, match="(?i)disallowed|forbidden"):
        orch.create_run(website_url="https://example.com", org_id="ws_default")
    with pytest.raises(ValueError, match="(?i)disallowed|forbidden|workspace"):
        orch.create_run(website_url="https://example.com", org_id="org_alpha", workspace_id="org_default")
    with pytest.raises(ValueError, match="(?i)workspace"):
        orch.create_run(website_url="https://example.com", org_id="org_alpha", workspace_id="   ")


def test_orchestrator_execute_analysis_pipeline_rejects_ws_default():
    orch = AnalysisOrchestrator()
    run = AnalysisRun(
        analysis_id="run_leak_test",
        org_id="org_valid",
        website_url="https://example.com",
        created_at="2026-11-01T00:00:00Z",
        updated_at="2026-11-01T00:00:00Z",
    )
    # Bypass model validator via object dict mutation to simulate dirty DB record
    object.__setattr__(run, "org_id", "ws_default")
    orch.runs[run.analysis_id] = run

    import asyncio
    with pytest.raises(ValueError, match="(?i)valid tenant org_id required"):
        asyncio.run(orch.execute_analysis_pipeline(run.analysis_id, "https://example.com"))
```

---

## 5. Verification Protocol & Invalidation Conditions

### 5.1 Verification Commands
The implementing worker must execute the following commands to verify that Defect 2 is remediated:

```bash
# 1. Run full tenant isolation suite (all 40+ tests including new Suite 7)
pytest backend/tests/test_tenant_isolation.py -v

# 2. Run security-specific suite
pytest backend/tests/security/test_tenant_isolation.py -v

# 3. Verify dependent orchestrator and connector suites
pytest backend/tests/test_pipeline.py \
       backend/tests/test_mission_director.py \
       backend/tests/test_audit_persistence_and_restore.py \
       backend/tests/test_db_session_and_fail_fast.py -v

# 4. Run AST check to ensure no forbidden argument defaults were introduced
pytest backend/tests/test_tenant_isolation.py -k "test_static_codebase_ast_scan_no_org_default_fallbacks" -v

# 5. Check flake8 syntax
flake8 backend/app/domain/models.py backend/app/orchestration/orchestrator.py --ignore=E501
```

### 5.2 Invalidation Conditions
The fix is considered **INVALID** if any of the following occur:
- `AnalysisRun(..., org_id='ws_default')` succeeds without raising `ValidationError`.
- `AnalysisRun(..., workspace_id='org_default')` succeeds without raising `ValidationError`.
- `AnalysisRun(..., workspace_id='   ')` succeeds without raising `ValidationError`.
- `orchestrator.create_run(..., org_id='ws_default')` succeeds without raising `ValueError`.
- `orchestrator.execute_analysis_pipeline` with `run.org_id='ws_default'` executes without raising `ValueError`.
- Any existing test in `test_tenant_isolation.py` or regression suites fails.
