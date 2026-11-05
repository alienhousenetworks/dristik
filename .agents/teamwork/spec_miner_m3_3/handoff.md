# Handoff Report — Milestone M3 Strict Multi-Tenancy Isolation Test Specification

**Agent**: `spec_miner_m3_3` (Specification Miner)  
**Parent**: `530d48e9-ac3f-4fe2-8d83-6df3cf3f882f`  
**Milestone**: M3 — Phase 1: Strict Multi-Tenancy Isolation & Tenant Scoping  
**Date**: 2026-10-31  

---

## 1. Observation

Direct code and environment observations:

1. **Domain Model Defaults**:
   - In `backend/app/domain/models.py`:
     - Line 125–126: `class Integration(BaseModel): org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
     - Line 333–334: `class Finding(BaseModel): org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
     - Line 2609–2610: `class ExecutiveReport(BaseModel): org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
     - Line 2716–2717: `class AnalysisRequest(BaseModel): org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
     - Line 2733–2734: `class AnalysisRun(BaseModel): org_id: str = "org_default"`, `workspace_id: str = "ws_default"`

2. **Orchestrator Defaults & Tenant Scoping**:
   - In `backend/app/orchestration/orchestrator.py`:
     - Line 99: `def create_run(self, website_url: str, org_id: str = "org_default", created_by: Optional[str] = None, target_pillars: Optional[List[str]] = None) -> AnalysisRun:`
     - Line 1533–1572: External authority attachment resolves `tenant_project_id`:
       ```python
       tenant_project_id = getattr(run, "org_id", None)
       if not tenant_project_id or tenant_project_id == "org_default":
           tenant_project_id = blackboard.blackboard_state.get("org_id") or getattr(blackboard, "org_id", None)
       if tenant_project_id and tenant_project_id != "org_default":
           attachment = build_audit_attachment(...)
       else:
           logger.info("External authority attachment skipped: missing tenant org context (refusing 'org_default' fallback)")
       ```

3. **Persistence Repository Tenant Scoping**:
   - In `backend/app/db/repository.py`:
     - Line 183–197: `def list_runs(self, org_id: Optional[str] = None, limit: int = 50)` defaults to `org_id=None` and executes `SELECT * FROM audits ORDER BY created_at DESC LIMIT ?`, which leaks cross-tenant audits when unscoped.
     - Line 199–224: `def delete_run(self, analysis_id: str, org_id: Optional[str] = None) -> bool`: verifies `org_id` only if provided.

4. **External Authority Credential Store**:
   - In `backend/app/connectors/authority/store.py`:
     - Line 146–159: `def load_secret(self, project_id: str, provider: str) -> Optional[Dict[str, Any]]`: fetches `SELECT token_ciphertext, status FROM external_connections WHERE project_id=? AND provider=?` and decrypts via Fernet.
     - Line 279–318: `def save_snapshot(...)`: partitions snapshot storage by `project_id`.

5. **API Layer Tenant Access Control**:
   - In `backend/app/identity/access.py`:
     - Line 10–30: `require_analysis(analysis_id: str, user: UserIdentity, permission: str = "mission:read")`: validates `Authorizer.can_perform(user, permission)` and `Authorizer.can_access_org(user, getattr(run, "org_id", "") or "")`, raising `HTTPException(status_code=404, detail="Analysis run not found.")` if tenant mismatch occurs.
   - In `backend/app/api/routes/audits/analyses.py`:
     - Line 152–212: `GET /analyses` filters both in-memory `orchestrator.runs` (`Authorizer.can_access_org(user, r.org_id)`) and database records (`repo.list_runs(org_id=org_id, limit=limit)`).
     - Line 214–228: `DELETE /analyses/{analysis_id}` delegates to `require_analysis` and `repo.delete_run(run.analysis_id, org_id=run.org_id)`.
     - Lines 347–1177: Sub-resource routes (`/report`, `/findings`, `/manifest`, `/twin`, `/timeline`, `/patch-pack/*`, `/checkpoints`) all guard through `require_analysis`.
   - In `backend/app/reports/pdf_generator.py`:
     - Lines 1050–1172: Executive presentation deck and adaptive audit book routes (`/{analysis_id}/audit-book`, `/{analysis_id}/section-deck`) guard through `require_analysis(analysis_id, user)`.

6. **Existing Test Suite Baseline**:
   - Running `pytest backend/tests/security/test_tenant_isolation.py` executed 4 tests in 0.72s with 100% pass rate.
   - The primary file `backend/tests/test_tenant_isolation.py` does not yet exist and is designated for the comprehensive M3 test suite.

---

## 2. Logic Chain

1. **Vulnerability of Legacy Fallbacks**:
   - The presence of `"org_default"` and `"ws_default"` in Pydantic domain models (`AnalysisRequest`, `AnalysisRun`, `Finding`, `ExecutiveReport`, `Integration`) and function signatures (`create_run`, `add_integration`) allows un-scoped caller invocations to silently fall back into a shared bucket, creating an insecure multi-tenant environment (Observation 1, Observation 2).
2. **Repository Leak Prevention**:
   - `AuditRepository.list_runs` allowing `org_id=None` poses a critical data isolation risk by returning all audits across organizations (Observation 3). To comply with `PROJECT.md:49-50`, `org_id` must be mandatory; passing `None`, `""`, or `"org_default"` must raise a `ValueError`.
3. **Cross-Tenant Run & Artifact Privacy**:
   - `require_analysis` implements security-by-obscurity by masking cross-tenant runs with HTTP 404 rather than HTTP 403, preventing attackers from probing for the existence of valid run IDs across other organizations (Observation 5). All sub-resource endpoints (reports, findings, books, decks, patch packs) adhere to this contract.
4. **Credential Isolation**:
   - `ExternalStore` and `ConnectorStore` strictly enforce key derivation and query scoping by `project_id` / `org_id` (Observation 4). Cross-tenant queries return `None` or empty lists, preventing any provider credential leakage.
5. **Orchestrator Same-Domain Collision Safety**:
   - When two tenants audit the same domain (e.g. `example.com`), orchestrator attachments must rely strictly on the caller's verified `run.org_id`. A tenant with no connected authority credentials must never inherit snapshot coverage or domain findings from another tenant auditing the same domain (Observation 2).

---

## 3. Caveats

1. **System Admin Role**:
   - `Authorizer.can_access_org` permits users with `UserRole.SYSTEM_ADMIN` or `is_system=True` to access any organization. This is intended behavior for internal operations and debugging, but must not be accessible to standard enterprise users.
2. **PostgreSQL vs. SQLite in Tests**:
   - Test suites execute against in-memory or temporary SQLite databases (`tmp_path`). All SQL queries in `AuditRepository` and `ExternalStore` use portable SQL schemas compatible with both SQLite and PostgreSQL.
3. **Read-Only Scope**:
   - In accordance with the dispatch prompt and role constraints, no source code was modified. The test blueprint has been authored and saved to `.agents/teamwork/spec_miner_m3_3/test_blueprint_m3.md`.

---

## 4. Conclusion

Milestone M3 requires an exhaustive, 6-suite test module at `backend/tests/test_tenant_isolation.py` addressing:
- **T-TI-01**: Mandatory tenant context enforcement on API routes, domain models, and repository operations.
- **T-TI-02**: Static AST/signature checks and runtime error checks guaranteeing zero occurrence of `"org_default"` and `"ws_default"`.
- **T-TI-03**: Cross-tenant isolation across in-memory registries, database persistence, and lifecycle operations.
- **T-TI-04**: Strict blocking of cross-tenant reads on reports, findings, audit books, presentation decks, and patch packs.
- **T-TI-05**: Hermetic tenant partitioning in `ExternalStore` and `ConnectorStore`.
- **T-TI-06**: Orchestrator external authority attachment scoping and collision resistance.

The full actionable blueprint is documented in `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_3/test_blueprint_m3.md`.

---

## 5. Verification Method

To independently verify the findings and the blueprint:

1. **Inspect Artifacts**:
   - View test blueprint: `view_file /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_3/test_blueprint_m3.md`
   - Inspect existing security isolation tests: `view_file /Users/sayantande/Downloads/dristik-main/backend/tests/security/test_tenant_isolation.py`
2. **Execute Baseline Test Suite**:
   ```bash
   pytest backend/tests/security/test_tenant_isolation.py -v
   pytest backend/tests/test_db_session_and_fail_fast.py backend/tests/test_scoring_timing_and_honest_flag.py -v
   ```
3. **Verification Condition for Implementer**:
   When `backend/tests/test_tenant_isolation.py` is implemented according to the blueprint and F11/F12/F13 code changes are applied:
   ```bash
   pytest backend/tests/test_tenant_isolation.py -v
   ```
   All test cases (T-TI-01 through T-TI-06) must pass with 0 failures and 0 warnings.
