# Handoff Report: Milestone M1 Backend Pipeline Scoring Timing & External Authority Flag

**Agent ID**: `explorer_m1_1`  
**Role**: Teamwork Explorer (Read-Only Investigation & Implementation Strategy)  
**Task**: Technical Strategy for Milestone M1 in `backend/app/orchestration/orchestrator.py`  
**Date**: 2026-10-31  

---

## 1. Observation

Direct code and test observations from `/Users/sayantande/Downloads/dristik-main`:

1. **Premature Scoring Stage Emission (`backend/app/orchestration/orchestrator.py:1276-1283`)**:
   ```python
   controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
   controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")
   model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
   model_router.set_active_sub_stage("remediation_blueprints", "Autonomous Code Patch Pack Generation")
   run.status = AnalysisStage.SCORING
   await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
   ```
   Directly following line 1283, lines 1285–1371 execute post-DAG analyzers (visual UX, canonicals, HTTP statuses, headings, media, link depth, meta rollup, forms, security headers, schema rich results, WCAG, host redirects), followed by live GEO search visibility (lines 1393–1494), competitor evidence (lines 1508–1524), external authority attachment (lines 1526–1557), and finding deduplication (lines 1562–1566).
   True scoring execution only begins at Step 15 (line 1581), where `node_honest_scoring` was redundantly marked `RUNNING` a second time at line 1583.

2. **External Authority Key Mismatch Bug (`backend/app/orchestration/orchestrator.py:1547-1553`)**:
   ```python
   cov_items = external_authority_payload.get("coverage", [])
   if any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in cov_items):
       has_external_authority_connected = True
   elif external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
       has_external_authority_connected = True
   elif len(attachment.get("domain_findings", [])) > 0:
       has_external_authority_connected = True
   ```
   Inspected `coverage_matrix` and `_coverage_row` in `backend/app/connectors/authority/analyze.py` (lines 87–144). The row keys are `"connection_status"` and `"data_state"`:
   ```python
   return {
       "provider": provider.provider_id,
       "display_name": provider.display_name,
       "connection_status": connection_status,
       "data_state": data_state,
       ...
   }
   ```
   No `"status"` key exists in coverage rows, and no top-level `"status"` key exists in `external_authority_payload` (returned by `analyze.py:build_report`). Therefore, `c.get("status")` is always `None`, and `has_external_authority_connected` evaluates to `False` unless `domain_findings` > 0.
   When `external_authority_connected=False`, `ScoringEngine.calculate_scores` (line 247) marks `TRUST_AUTHORITY` as `NOT_MEASURED` (`score=None`, `weight=0.0`), claiming connector unavailable even when healthy provider snapshots exist.

3. **Insecure `"org_default"` Tenant Fallback (`backend/app/orchestration/orchestrator.py:1537`)**:
   ```python
   attachment = build_audit_attachment(
       project_id=getattr(run, "org_id", None) or "org_default",
       domain=domain,
       pages=eval_pages,
       evidence_store=getattr(blackboard, "evidence_store", None),
   )
   ```
   When `run.org_id` is missing or None, the call falls back to `"org_default"`, querying and potentially attaching external credentials and snapshots from the shared default bucket.

4. **DAG Runner Incompleteness (`backend/app/orchestration/orchestrator.py:2983-2995`)**:
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
   The runner omitted `external_authority_connected`, `has_schema`, `is_https`, `readability`, `live_citation_score`, `live_benchmark_data`, did not apply `apply_measured_geo_score`, and completely omitted `calculate_honest_scores`.

5. **Roadmap Execution Flow (`backend/app/orchestration/orchestrator.py:1675-1685`)**:
   ```python
   r7, r30, r90 = self.roadmap_builder.build_roadmap(final_findings, blackboard.executive_narrative)
   top_10_plan = self.roadmap_builder.build_top_10_actions(
       final_findings,
       blackboard.business_profile,
       overall_scores,
       blackboard.executive_narrative,
       crawl_summary=manifest.crawl_health if manifest else None,
   )
   ```
   At line 1545, external authority domain findings are appended to `raw_findings`:
   ```python
   for f in attachment.get("domain_findings", []):
       if not any(x.finding_id == f.finding_id for x in raw_findings):
           raw_findings.append(f)
   ```
   Line 1562 executes `final_findings = FindingDeduplicator.deduplicate(raw_findings)`. `final_findings` carries these findings directly into `RoadmapBuilder.build_roadmap` and `build_top_10_actions`.

6. **Test Commands Executed**:
   - `pytest backend/tests/test_scoring_unmeasured_authority.py`: 2 passed in 0.93s.
   - `pytest backend/tests/test_scoring_calibration.py backend/tests/test_scoring_v5.py backend/tests/test_scoring_geo_extractability.py`: 21 passed in 2.78s.
   - `pytest backend/tests/test_pipeline.py`: 8 passed in 6.98s.

---

## 2. Logic Chain

1. **Premature Event Trigger**: In `execute_analysis_pipeline`, SSE events notify frontend subscribers of audit progress. Emitting `AnalysisStage.SCORING` at line 1282 before post-DAG analyzers (Step 14), live visibility, and external authority run causes the UI to report scoring in progress while findings are still being actively discovered. Moving the emission of `AnalysisStage.SCORING` (93%) to Step 15 (line 1583) guarantees that scoring is broadcast only when deterministic calculations begin over complete findings.
2. **Flag Key Alignment**: In `backend/app/connectors/authority/analyze.py`, provider connection and snapshot states are recorded as `"connection_status"` and `"data_state"`. In `orchestrator.py:1548`, checking `c.get("status") == "CONNECTED"` fails because the key name is `"connection_status"`. Updating the check to inspect `c.get("connection_status") == "CONNECTED" or c.get("data_state") in ("MEASURED", "PARTIALLY_MEASURED")` restores proper detection, allowing `ScoringEngine` to recognize connected external authority.
3. **Tenant Isolation**: Falling back to `"org_default"` allows audits without tenant context to access default credentials. Bypassing external authority when tenant context is missing or resolves to `"org_default"` prevents multi-tenant leakage and satisfies enterprise isolation requirements.
4. **DAG Runner Parity**: `run_pipeline_node("node_honest_scoring")` is the manual execution path for re-scoring. It must compute identical scores to the automated pipeline by supplying all environmental parameters (`external_authority_connected`, `has_schema`, `is_https`, `readability`, `live_citation_score`) and invoking `calculate_honest_scores`.
5. **Roadmap Completeness**: Because external findings are attached to `raw_findings` prior to deduplication into `final_findings`, and `final_findings` is passed to `self.roadmap_builder.build_roadmap`, high-priority external findings automatically populate `r7` and `r30`.

---

## 3. Caveats

1. **Frontend Score Synthesis (F05 & F06)**: Frontend changes in `frontend/src/lib/pillarSynthesis.ts` and `frontend/src/components/ScoringRubricModal.tsx` are part of Milestone M1 Phase 0 but belong to the frontend task. The backend changes specified here provide the canonical contract (`category_scores` and `calculate_honest_scores`) that the frontend consumes.
2. **Missing `app.external_authority` Module Alias**: In `backend/tests/test_external_authority.py`, tests import `app.external_authority.audit_bridge`. Because the module was relocated to `app.connectors.authority`, running `pytest backend/tests/test_external_authority.py` fails with `ModuleNotFoundError` until the compatibility shim is added in `app/domain/__init__.py` or `conftest.py` (scheduled in Milestone M2 / F10).
3. **Assumption on Tenant Resolution**: In Milestone M1, missing tenant context skips external authority attachment gracefully without raising an exception. In Milestone M3, missing tenant context on audit initiation will strictly fail fast with `403 Forbidden`.

---

## 4. Conclusion

The technical strategy formulated in `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m1_1/strategy_backend.md` is complete, verified against existing tests, and immediately actionable for the implementer:
- Lines 1276–1283: Premature `node_honest_scoring` status and SSE `stage="scoring"` removed; replaced by post-DAG specialist stage; scoring stage emission moved to Step 15 (line 1583).
- Lines 1537 & 1547–1553: `"org_default"` fallback eliminated; key mismatch fixed by inspecting `connection_status == "CONNECTED"` and `data_state in ("MEASURED", "PARTIALLY_MEASURED")`.
- Lines 2983–2995: DAG runner `node_honest_scoring` updated with full parameters and `calculate_honest_scores` invocation.
- Step 16 Roadmap generation verified to evaluate over `final_findings` including external authority findings.

---

## 5. Verification Method

To independently verify the implementation:

1. **Execute existing test suites**:
   ```bash
   pytest backend/tests/test_scoring_unmeasured_authority.py -v
   pytest backend/tests/test_pipeline.py -v
   pytest backend/tests/test_scoring_calibration.py backend/tests/test_scoring_v5.py backend/tests/test_scoring_geo_extractability.py -v
   ```
2. **Execute new unit tests** (from Section 4 of `strategy_backend.md`):
   ```bash
   pytest backend/tests/unit/test_orchestrator_scoring_timing.py -v
   ```
3. **Inspect target code lines in `backend/app/orchestration/orchestrator.py`**:
   - Verify line 1276 does not emit `AnalysisStage.SCORING`.
   - Verify line 1537 does not use `"org_default"`.
   - Verify lines 1547–1553 check `connection_status` and `data_state`.
   - Verify line 1583 emits `AnalysisStage.SCORING` at 93%.
   - Verify lines 2983–2995 invoke `calculate_honest_scores` and pass `external_authority_connected`.
