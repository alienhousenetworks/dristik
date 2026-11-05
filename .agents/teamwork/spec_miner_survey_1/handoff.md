# Handoff Report — Phase 0 & Phase 1 Ground Truth Specification Mining

**Agent:** `spec_miner_survey_1`  
**Recipient:** Parent / Orchestrator (`530d48e9-ac3f-4fe2-8d83-6df3cf3f882f`)  
**Type:** Hard Handoff (Task Complete)  
**Deliverable Path:** `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_survey_1/survey_spec_report.md`

---

## 1. Observation

1. **Scoring Formulas and Weights:**
   - `backend/app/domain/scoring/weights.py:8-17`: Defines baseline weights for 8 categories:
     ```python
     BASELINE_WEIGHTS: Dict[Category, float] = {
         Category.TECHNICAL_SEO: 0.15,
         Category.ON_PAGE_SEO: 0.10,
         Category.CONTENT: 0.15,
         Category.GEO: 0.15,
         Category.AI_SEARCH: 0.15,
         Category.SCHEMA: 0.10,
         Category.UX_CONVERSION: 0.10,
         Category.TRUST_AUTHORITY: 0.10,
     }
     ```
   - `backend/app/domain/scoring/weights.py:19-48`: Defines `INTENT_MULTIPLIERS` for `SAAS`, `ECOMMERCE`, `LEAD_GENERATION`, `CONTENT_PUBLISHING`, and `AGENCY`.
   - `backend/app/domain/scoring/scoring_rubric.py:95-158`: Defines deprecated `five_pillars` (Search 25%, AI Search 25%, Experience 20%, Conversion 20%, Trust 10%). `backend/tests/test_confidence_gating.py:12` asserts:
     ```python
     assert len(rubric["five_pillars"]) == 5
     ```
   - `frontend/src/lib/pillarSynthesis.ts:61-69`: Synthesizes `seoScore` using:
     ```typescript
     const searchParts = [
       [techScore, 0.45],
       [onPageScore, 0.35],
       [contentScore, 0.20],
     ];
     ```
     and sets `croScore = null`, conflicting with backend category scores.

2. **Pipeline Scoring & Roadmap Timing:**
   - `backend/app/orchestration/orchestrator.py:1393-1685`:
     - Line 1409: Live AI visibility checks run at Step 13.
     - Line 1535: External authority attachment runs via `build_audit_attachment`. Domain findings are appended to `raw_findings`.
     - Line 1547-1553: `has_external_authority_connected` is dynamically determined from `attachment["report"]["coverage"]`.
     - Line 1562: `final_findings = FindingDeduplicator.deduplicate(raw_findings)`.
     - Line 1597 & 1614: `calculate_scores` and `calculate_honest_scores` run at Step 15 with `findings=final_findings`, `external_authority_connected=has_external_authority_connected`, `live_citation_score=live_citation_score`.
     - Line 1675: `r7, r30, r90 = self.roadmap_builder.build_roadmap(final_findings, blackboard.executive_narrative)` runs at Step 16.
     - **Discrepancy in DAG Runner (`orchestrator.py:2985`):**
       In `node_honest_scoring`:
       ```python
       scores = self.scoring_engine.calculate_scores(
           manifest=blackboard.crawl_manifest,
           findings=blackboard.findings or [],
           claims=blackboard.claim_registry.get_all(),
           evidence_store=blackboard.evidence_store,
           pages=eval_pages,
           evaluations=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
           business_profile=blackboard.business_profile,
       )
       ```
       Here `external_authority_connected` is not passed (defaults to `False`), and `calculate_honest_scores` is omitted entirely.

3. **Database Fragmentation & MockSession Fallback:**
   - `backend/app/db/session.py:28-74`:
     ```python
     except ImportError:
         class MockSession:
             ...
             def query(self, *args, **kwargs): return self
             def first(self): return None
             def all(self): return []
     ```
     This masks missing dependencies or configuration errors silently.
   - Fragmented SQLite files:
     - `data/dristik.db`: used by `session.py` and `identity/store.py`.
     - `data/dristik_audits.db`: used by `backend/app/db/repository.py:40`.
     - `data/external_authority.db`: used by `connectors/authority/store.py:21`.
     - `data/geo_aeo_pipeline.db`: used by `geo/pipeline_store.py:30`.
   - `backend/app/db/enterprise_schema.py`: Contains DDL for 8 foundational enterprise tables (`organizations`, `workspaces`, `domains`, `audit_runs`, `evidence_nodes`, `findings`, `ai_citations`, `enterprise_audit_logs`).
   - `backend/alembic.ini`: Exists, but `backend/migrations/versions/` is empty with zero migration files.

4. **Tenant Scoping & `org_default` / `ws_default` Fallbacks:**
   - `backend/app/domain/models.py`:
     - Line 125–126 (`Integration`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
     - Line 2609–2610 (`ExecutiveReport`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
     - Line 2716–2717 (`AnalysisRequest`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
     - Line 2733–2734 (`AnalysisRun`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`.
   - `backend/app/orchestration/orchestrator.py:99`: `create_run(..., org_id: str = "org_default")`.
   - `backend/app/orchestration/orchestrator.py:1537`: `project_id=getattr(run, "org_id", None) or "org_default"`.
   - `backend/app/identity/tenancy/manager.py:20-38`: Pre-seeds in-memory registry with `org_default` and `ws_default`.
   - `backend/app/identity/access.py:28`: Blocks cross-tenant access with 404:
     ```python
     if not run or not Authorizer.can_access_org(user, getattr(run, "org_id", "") or ""):
         raise HTTPException(status_code=404, detail="Analysis run not found.")
     ```

5. **Test Suite Verification:**
   - `pytest backend/tests/test_scoring_unmeasured_authority.py backend/tests/security/test_tenant_isolation.py` executed: 6 passed in 2.69s.
   - `pytest backend/tests/test_confidence_gating.py backend/tests/test_scoring_v5.py` executed: 13 passed in 2.02s.

---

## 2. Logic Chain

1. **Category Weight Alignment:**
   - Observation 1 proves that `weights.py` and `scoring_rubric_v5.json` treat the 8 categories as canonical, while `pillarSynthesis.ts` and `scoreLedger.ts` synthesize non-standard 4-pillar and 5-pillar formulas.
   - Therefore, aligning UI consistency requires removing client-side re-weighting in `pillarSynthesis.ts` and displaying the 8 canonical categories (or the 3 honest perspective views) directly.
   - Because `test_confidence_gating.py:12` explicitly tests `len(rubric["five_pillars"]) == 5`, `five_pillars` must be retained in `scoring_rubric.py` as a backward-compatibility stub.

2. **Pipeline Scoring Order & Honest Scores:**
   - Observation 2 demonstrates that the main pipeline (`execute_analysis_pipeline`) in `orchestrator.py` was partially updated to run external authority (Step 13) before deduplication (Step 14) and scoring (Step 15).
   - However, in DAG node execution (`node_honest_scoring` at line 2985), `calculate_honest_scores` is never called, and `external_authority_connected` is not passed.
   - In Step 13 (line 1537), `project_id` still falls back to `"org_default"`.
   - Therefore, both the main orchestrator and DAG node handlers must be aligned so that external authority attachment runs without `org_default`, and passes `external_authority_connected` into both `calculate_scores` and `calculate_honest_scores`.

3. **Unified Persistence & MockSession Elimination:**
   - Observation 3 shows 4 distinct SQLite files across different modules and a silent `MockSession` fallback.
   - `MockSession` masks database connectivity failures by returning empty lists and None.
   - Therefore, removing `MockSession` and enforcing a unified `DATABASE_URL` managed via SQLAlchemy and Alembic migrations satisfies R2 and eliminates data fragmentation.

4. **Multi-Tenant Isolation:**
   - Observation 4 documents pervasive defaults to `"org_default"` and `"ws_default"` across Pydantic models, route handlers, and connectors.
   - When requests lack an org context, falling back to `"org_default"` causes data leakage across tenants.
   - Removing `"org_default"` and `"ws_default"`, enforcing `403 Forbidden` on unauthenticated or missing tenant context, and enforcing `require_analysis` across all data queries ensures strict enterprise tenant isolation.

---

## 3. Caveats

1. **Read-Only Scope:** In accordance with the dispatch assignment, zero source code or schema modifications were applied. All findings reflect the live codebase and authoritative specifications as inspected.
2. **PostgreSQL vs SQLite Local Environment:** While production specifies PostgreSQL compatibility, local test harnesses currently run on SQLite (`check_same_thread=False`). The unified SQLAlchemy schema must maintain compatibility with both database backends.
3. **Legacy Test Assertions:** `test_confidence_gating.py:12` expects `len(rubric["five_pillars"]) == 5`. Any refactoring of `scoring_rubric.py` must preserve this key as an alias to avoid breaking tests.

---

## 4. Conclusion

The authoritative ground truth for Phase 0 and Phase 1 is fully established:
1. **Scoring & UI:** Canonical 8 engine categories (`TECHNICAL_SEO`, `ON_PAGE_SEO`, `CONTENT`, `GEO`, `AI_SEARCH`, `SCHEMA`, `UX_CONVERSION`, `TRUST_AUTHORITY`) are the sole truth. Frontend synthesis must consume these categories directly.
2. **Pipeline Sequencing:** Scoring (`calculate_scores` and `calculate_honest_scores`) and the 7/30/90 roadmap must execute after external authority findings are attached and live visibility checks complete.
3. **Enterprise Persistence:** The 8 tables from `backend/app/db/enterprise_schema.py` form the target relational model. `MockSession` must be deleted from `session.py`.
4. **Tenant Isolation:** Fallbacks to `org_default` and `ws_default` must be eliminated, and missing tenant contexts must return `403 Forbidden`.

The full specification is documented in `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_survey_1/survey_spec_report.md`.

---

## 5. Verification Method

To independently verify the observations and conclusions:
1. **Inspect Survey Report:**
   ```bash
   view_file /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_survey_1/survey_spec_report.md
   ```
2. **Verify Scoring Weights & Intent Multipliers:**
   ```bash
   python3 -c "from app.domain.scoring.weights import BASELINE_WEIGHTS, INTENT_MULTIPLIERS; print(sum(BASELINE_WEIGHTS.values()))"
   ```
   *Expected:* Output is `1.0`.
3. **Verify Existing Unit Test Suite:**
   ```bash
   pytest backend/tests/test_scoring_unmeasured_authority.py backend/tests/security/test_tenant_isolation.py backend/tests/test_confidence_gating.py backend/tests/test_scoring_v5.py
   ```
   *Expected:* All 19 tests pass without errors.
4. **Inspect MockSession and Fallbacks:**
   - Inspect `backend/app/db/session.py` lines 28–74 to confirm `MockSession`.
   - Inspect `backend/app/domain/models.py` lines 2733–2734 to confirm `org_default` and `ws_default`.
