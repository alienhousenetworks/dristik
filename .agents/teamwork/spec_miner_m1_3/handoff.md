# Handoff Report — Milestone M1 (Phase 0) Test Specification

**Agent**: `spec_miner_m1_3` (teamwork_preview_spec_miner)  
**Parent Agent**: `530d48e9-ac3f-4fe2-8d83-6df3cf3f882f` (parent)  
**Task**: Test specification and verification assertions for Milestone M1 (Phase 0)  
**Artifact**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_3/test_spec_m1.md`  
**Date**: 2026-10-31T17:22:00Z  

---

## 1. Observation

Direct code observations from inspecting the codebase:

1. **Premature Scoring Emission**:
   In `backend/app/orchestration/orchestrator.py` at line 1276:
   ```python
   # 12. Causal Prioritization & Scoring Engine
   controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
   controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")

   model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
   model_router.set_active_sub_stage("remediation_blueprints", "Autonomous Code Patch Pack Generation")
   run.status = AnalysisStage.SCORING
   await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
   ```
   At lines 1284–1580, post-DAG analyzers (canonicals, HTTP status, headings, media, links, meta, forms, schema, WCAG, local SEO, indexation), live AI visibility, GEO readiness, and external authority attachment execute.
   Deterministic scoring only actually executes at line 1597 (`overall_scores = self.scoring_engine.calculate_scores(...)`), creating a premature emission of `AnalysisStage.SCORING` at line 1281 before analyzers and external authority finish.

2. **External Authority Flag Key Mismatch**:
   In `backend/app/orchestration/orchestrator.py` at lines 1547–1553:
   ```python
   cov_items = external_authority_payload.get("coverage", [])
   if any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in cov_items):
       has_external_authority_connected = True
   elif external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
       has_external_authority_connected = True
   elif len(attachment.get("domain_findings", [])) > 0:
       has_external_authority_connected = True
   ```
   In `backend/app/connectors/authority/analyze.py` at line 130 (`_coverage_row`):
   ```python
   return {
       "provider": provider.provider_id,
       "display_name": provider.display_name,
       "connection_status": connection_status,
       "data_state": data_state,
       ...
   }
   ```
   Coverage items contain `"connection_status": "CONNECTED"` and `"data_state": "OK"` (or `"PARTIALLY_MEASURED"`), NEVER `"status"`. Consequently, `c.get("status")` evaluates to `None`, so `has_external_authority_connected` remained `False` unless `domain_findings` were non-empty.

3. **DAG Runner Missing Honest Scoring**:
   In `backend/app/orchestration/orchestrator.py` at lines 2983–2995 (`node_honest_scoring`):
   ```python
   elif node_id == "node_honest_scoring":
       eval_pages = blackboard.pages or []
       scores = self.scoring_engine.calculate_scores(
           manifest=blackboard.crawl_manifest,
           findings=blackboard.findings or [],
           claims=blackboard.claim_registry.get_all(),
           evidence_store=blackboard.evidence_store,
           pages=eval_pages,
           evaluations=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
           business_profile=blackboard.business_profile,
       )
       blackboard.scores = scores
   ```
   `node_honest_scoring` only invoked `calculate_scores` and never called `calculate_honest_scores`, leaving `blackboard.honest_scores` unpopulated and omitting `external_authority_connected`.

4. **Frontend Pillar Formula Inconsistency**:
   In `frontend/src/lib/pillarSynthesis.ts` at lines 58–69:
   ```typescript
   const techScore = catScores['TECHNICAL_SEO']?.score ?? catScores['technical']?.score ?? honest?.google_score;
   const onPageScore = catScores['ON_PAGE_SEO']?.score;
   const contentScore = catScores['CONTENT']?.score;
   const searchParts = [
     [techScore, 0.45],
     [onPageScore, 0.35],
     [contentScore, 0.20],
   ].filter((pair): pair is [number, number] => typeof pair[0] === 'number');
   ```
   And CRO score at line 207:
   ```typescript
   const croPillar: PillarScoreData = {
     id: 'cro',
     ...
     score: null,
     grade: '—',
   ```
   In `frontend/src/components/ScoringRubricModal.tsx` at lines 210–218:
   Google Discoverability is described as `45% Technical + 35% On-Page + 20% Schema` and Human Experience as `40% UX/CRO + 35% Content Readability + 25% Trust`.
   In `backend/app/domain/scoring/engine.py` at lines 1060–1063:
   Google View is `0.40 * tech_score + 0.30 * onpage_score + 0.30 * schema_score`.
   Human View is `0.50 * ux_score + 0.50 * content_score`.

5. **Existing Test Suite Execution Results**:
   - `pytest backend/tests/test_scoring_unmeasured_authority.py backend/tests/test_confidence_gating.py backend/tests/test_scoring_v5.py`: 15 passed in 1.65s.
   - `pytest backend/tests/test_ai_scoring_calibration.py backend/tests/test_ai_search_scoring_integrity.py backend/tests/test_scoring_calibration.py backend/tests/test_scoring_geo_extractability.py backend/tests/test_scoring_missing_measurements.py backend/tests/test_scoring_transparency.py backend/tests/unit/test_scoring.py backend/tests/test_aeo_scoring_zero_fabrication.py`: 29 passed in 1.79s.
   - `pytest backend/tests/test_pipeline.py`: 8 passed in 11.32s.
   - `npm test` in `frontend/`: 105 passed across 29 test files in 7.97s.

---

## 2. Logic Chain

1. **Step 1 (Scoring Timing & Sequence)**:
   Observation 1 demonstrates that line 1276 set `run.status = AnalysisStage.SCORING` and emitted a 93% progress event before running 15 post-DAG analyzers, live visibility probes, and external authority attachment. When external findings were attached later at line 1545, any scoring or roadmap run before that point lacked those findings. Therefore, re-ordering scoring emission to Step 15 guarantees that all findings exist before category scoring and 7/30/90 roadmap generation occur.

2. **Step 2 (Flag Detection Correction)**:
   Observation 2 demonstrates that `build_audit_attachment()` returns coverage rows populated with `connection_status` and `data_state`. Because `orchestrator.py:1548` checked `c.get("status") == "CONNECTED"`, connected providers with valid snapshots were ignored unless domain findings were emitted. Fixing this key check to check `c.get("connection_status") == "CONNECTED"` and `c.get("data_state") in ("OK", "PARTIALLY_MEASURED", "FRESH", "STALE")` ensures `has_external_authority_connected` evaluates to `True`.

3. **Step 3 (Honest Scores & DAG Runner Parity)**:
   Observation 3 shows that DAG runner `node_honest_scoring` at line 2985 omitted `calculate_honest_scores` entirely. Calling `self.scoring_engine.calculate_honest_scores(..., external_authority_connected=has_external_authority_connected)` and persisting the result to `blackboard.honest_scores` brings the DAG node runner into exact parity with the main pipeline flow at line 1614.

4. **Step 4 (Roadmap Evaluation over Complete Evidence)**:
   At line 1545 of `orchestrator.py`, external domain findings from `build_audit_attachment` are merged into `raw_findings`. At line 1562, `FindingDeduplicator.deduplicate` produces `final_findings`. At line 1675, `self.roadmap_builder.build_roadmap(final_findings, ...)` creates `r7`, `r30`, and `r90`. Critical and High severity external findings (e.g. GSC crawl anomalies, toxic backlinks) are routed into `r7` (7 days) with owner roles and verification steps.

5. **Step 5 (Frontend Alignment & Canonical Harmony)**:
   Observation 4 shows that `pillarSynthesis.ts` and `ScoringRubricModal.tsx` used divergent client formulas (45/35/20) and hardcoded nulls, while `weights.py` establishes the 8 canonical engine categories (15/10/15/15/15/10/10/10) and `engine.py` implements honest perspectives (40/30/30 for Google, 50/50 for Human). Aligning the frontend directly to consume `report.scores.category_scores` eliminates triple scoring divergence across views.

---

## 3. Caveats

1. **Database Session & MockSession**:
   Investigation focused strictly on Milestone M1 (Scoring Timing, Honest Flag, Roadmap, UI Consistency). Database engine consolidation and `MockSession` removal belong to Milestone M2 (Phase 1 Persistence).
2. **Backward-Compatibility Alias in `scoring_rubric.py`**:
   `test_confidence_gating.py:12` asserts `len(rubric["five_pillars"]) == 5`. When updating `scoring_rubric.py`, the `five_pillars` alias key must be preserved to prevent breaking existing tests.
3. **Legacy `app.external_authority` Import in `test_external_authority.py`**:
   `backend/tests/test_external_authority.py` fails during test collection due to `from app.external_authority.audit_bridge ...`. This is scoped to Milestone M2 (Feature F10: conftest import shims).

---

## 4. Conclusion

The specification and test blueprint for Milestone M1 is complete, verified against live code, and documented in `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_3/test_spec_m1.md`.
The new test module `backend/tests/test_scoring_timing_and_honest_flag.py` defines 6 exact, independent test cases with mock harnesses, fixtures, and assertions:
1. `test_external_authority_flag_detection_from_coverage`
2. `test_external_authority_flag_false_when_unconnected`
3. `test_pipeline_scoring_timing_sequence`
4. `test_external_authority_findings_in_scores_and_roadmap`
5. `test_honest_scores_dynamic_flag_and_dag_node_runner`
6. `test_canonical_weights_and_honest_perspective_formulas`

All 52 existing backend unit/integration tests and 105 frontend Vitest tests pass without regressions.

---

## 5. Verification Method

To independently verify this specification and its assertions:

1. **Inspect Blueprint File**:
   View `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_3/test_spec_m1.md`.

2. **Run Existing Scoring and Pipeline Regression Suites**:
   ```bash
   pytest backend/tests/test_scoring_unmeasured_authority.py \
          backend/tests/test_confidence_gating.py \
          backend/tests/test_scoring_v5.py \
          backend/tests/test_pipeline.py -v
   ```
   Expected: 28 passed, 0 failed.

3. **Run Full Related Scoring Integrity Suite**:
   ```bash
   pytest backend/tests/test_ai_scoring_calibration.py \
          backend/tests/test_ai_search_scoring_integrity.py \
          backend/tests/test_scoring_calibration.py \
          backend/tests/test_scoring_geo_extractability.py \
          backend/tests/test_scoring_missing_measurements.py \
          backend/tests/test_scoring_transparency.py \
          backend/tests/unit/test_scoring.py \
          backend/tests/test_aeo_scoring_zero_fabrication.py -v
   ```
   Expected: 29 passed, 0 failed.

4. **Run Frontend Vitest Suite**:
   ```bash
   cd /Users/sayantande/Downloads/dristik-main/frontend && npm test
   ```
   Expected: 105 passed across 29 test files.

5. **Invalidation Conditions**:
   - `has_external_authority_connected` evaluates to `False` when a provider snapshot exists in the external authority store.
   - `calculate_scores` or `calculate_honest_scores` runs before external authority findings are merged into `final_findings`.
   - `roadmap_7_days` does not contain High or Critical external authority findings.
   - `five_pillars` key is missing from `scoring_rubric.py` causing `test_confidence_gating.py` to fail.
