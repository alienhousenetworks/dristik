# Handoff Report: Phase 0 Codebase Investigation

**Agent**: `explorer_survey_2`  
**Working Directory**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_survey_2`  
**Recipient**: `parent` (`530d48e9-ac3f-4fe2-8d83-6df3cf3f882f`)  
**Handoff Type**: Hard (Task Complete)  
**Reference Document**: `survey_phase0_report.md`

---

## 1. Observation

1. **Pipeline Execution Flow in `backend/app/orchestration/orchestrator.py`**:
   - Lines 1275–1283:
     ```python
     # 12. Causal Prioritization & Scoring Engine
     controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
     controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")
     model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
     run.status = AnalysisStage.SCORING
     await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
     ```
     Observed: `node_honest_scoring` is marked RUNNING and SSE emits stage="scoring" (93%) before post-DAG analyzers (lines 1285–1371), decision engine finding synthesis (line 1372), live AI visibility (lines 1393–1468), and external authority attachment (lines 1526–1557) have executed.
   - Lines 1581–1626:
     ```python
     # Step 15: Scoring Engine (Single Source of Truth over complete findings)
     controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
     ...
     overall_scores = self.scoring_engine.calculate_scores(
         findings=final_findings,
         business_profile=blackboard.business_profile,
         has_schema=any(len(p.schema_types) > 0 for p in blackboard.pages),
         is_https=website_url.startswith("https://"),
         readability=page_ev.readability_score,
         external_authority_connected=has_external_authority_connected,
         live_citation_score=live_citation_score,
         live_benchmark_data=live_bench,
         manifest=manifest,
     )
     ...
     honest_scores = self.scoring_engine.calculate_honest_scores(
         findings=final_findings,
         business_profile=blackboard.business_profile,
         commercial_evals=blackboard.commercial_evaluations,
         has_schema=len(page_ev.schema_types) > 0,
         is_https=website_url.startswith("https://"),
         readability=page_ev.readability_score,
         geo_readiness=geo_readiness,
         live_citation_score=live_citation_score,
         live_benchmark_data=live_bench,
         external_authority_connected=has_external_authority_connected,
     )
     ```
     Observed: The true calculation of `calculate_scores` and `calculate_honest_scores` runs at Step 15 over `final_findings`, receiving `external_authority_connected=has_external_authority_connected` and `live_citation_score=live_citation_score`.
   - Lines 1675–1682:
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
     Observed: Roadmaps (7/30/90) and top 10 actions run at Step 16 over `final_findings`.
   - Lines 2983–2995 (`run_pipeline_node("node_honest_scoring")`):
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
     Observed: In manual node execution, `external_authority_connected` and `live_citation_score` are completely missing.

2. **External Authority Flag & Key Mismatch**:
   - In `backend/app/orchestration/orchestrator.py` lines 1547–1553:
     ```python
     cov_items = external_authority_payload.get("coverage", [])
     if any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in cov_items):
         has_external_authority_connected = True
     elif external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
         has_external_authority_connected = True
     elif len(attachment.get("domain_findings", [])) > 0:
         has_external_authority_connected = True
     ```
   - In `backend/app/connectors/authority/analyze.py` lines 130–144 (`_coverage_row`):
     ```python
     return {
         "provider": provider.provider_id,
         "display_name": provider.display_name,
         "connection_status": connection_status,
         "data_state": data_state,
         ...
     }
     ```
     Observed: The key in `coverage` rows is `"connection_status"` and `"data_state"`. There is NO `"status"` key. Furthermore, the report dictionary from `build_report` contains no top-level `"status"` key. Unless `domain_findings` has items, `has_external_authority_connected` is falsely evaluated as `False`.

3. **Frontend Score Calculations in `frontend/src/lib/pillarSynthesis.ts`**:
   - Lines 58–70:
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
   - Lines 152–155:
     ```typescript
     const aeoParts = [schemaScore, extractabilityScore, botScore].filter((n): n is number => typeof n === 'number');
     const aeoScore = aeoParts.length
       ? Math.round(aeoParts.reduce((sum, n) => sum + n, 0) / aeoParts.length)
       : null;
     ```
   - Lines 207–209:
     ```typescript
     score: null,
     grade: '—',
     health: getHealth(null),
     ```
   - Lines 258 & 282:
     ```typescript
     const sxoScore = seoScore ?? null;
     ...
     score: aeoScore, // for brand_entity_intelligence
     ```
     Observed: The frontend synthesizes non-canonical scores that conflict with the 8 categories from `report.scores.category_scores`, hardcoding CRO to null and copying SEO/AEO into SXO/Brand.

4. **Scoring Rubric Inconsistencies**:
   - `frontend/src/components/ScoringRubricModal.tsx` defines 8 categories (15/10/15/15/15/10/10/10) in Tab 1, but states 3 perspective formulas:
     - Google: 45% Tech + 35% On-Page + 20% Schema
     - Human: 40% UX/CRO + 35% Content + 25% Trust
   - `backend/app/domain/scoring/engine.py:calculate_honest_scores` (lines 1060–1070) uses:
     - Google: 40% Tech + 30% On-Page + 30% Schema
     - Human: 50% UX/CRO + 50% Content
   - `backend/app/domain/scoring/scoring_rubric.py` (lines 95–160) still publishes `five_pillars`: Search SEO (25%), AI Search GEO (25%), Experience SXO (20%), Conversion CRO (20%), Brand Trust (10%).

---

## 2. Logic Chain

1. **Step 1: Pipeline Execution Flow**:
   - Observation: In `orchestrator.py:1276`, `controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)` is invoked prematurely before analyzers and authority attachment run.
   - Inference: The UI receives a `scoring` stage event at 93% while post-DAG analysis and live visibility checks are still executing.
   - Observation: In `orchestrator.py:1581–1682`, `calculate_scores`, `calculate_honest_scores`, `remediation_plan`, and `build_roadmap` execute sequentially after live AI visibility (line 1410) and external authority attachment (line 1536).
   - Inference: The actual calculation sequence in `execute_analysis_pipeline` already executes in the correct logical order (findings -> attachment -> deduplication -> scoring -> roadmaps). However, the premature progress event at line 1276 creates an illusion of early scoring, and the manual DAG node route at line 2985 omits vital parameters.

2. **Step 2: External Authority Connected Flag**:
   - Observation: `orchestrator.py` checks `c.get("status") == "CONNECTED"`, but `_coverage_row()` in `analyze.py` returns `connection_status` and `data_state`.
   - Inference: `c.get("status")` is undefined (`None`).
   - Observation: In `ScoringEngine.calculate_scores` line 247, if `external_authority_connected` is False and there are no trust findings with evidence, `gate_trust_requires_evidence` triggers and marks `Category.TRUST_AUTHORITY` as `NOT_MEASURED` (`weight=0.0`, `score=None`).
   - Inference: Even when provider credentials and snapshots exist, if no deficit findings are produced, the engine treats authority as unmeasured due to the dictionary key bug.

3. **Step 3: Frontend Score Synthesis & UI Alignment**:
   - Observation: `pillarSynthesis.ts` constructs an artificial 45/35/20 blend for SEO, averages arbitrary components for AEO, and hardcodes CRO score to `null`.
   - Observation: `Overview.tsx` and `WebsiteIntelligenceTriadHero.tsx` consume `pillarSynthesis.ts` rather than the 8 canonical categories in `report.scores.category_scores`.
   - Observation: `ScoringRubricModal.tsx` explains 8 categories, but `scoring_rubric.py` publishes 5 legacy pillars (25/25/20/20/10).
   - Inference: A buyer viewing the audit sees up to three conflicting scores for the same category across the header, overview discipline cards, rubric modal, and report body.

---

## 3. Caveats

1. **External Authority Relocation**: `app/external_authority/` was relocated to `app/connectors/authority/`. `backend/tests/test_external_authority.py` still imports from `app.external_authority` and requires an alias in `app/domain/__init__.py` to run.
2. **Playwright Integration Tests**: The full test suite run (`pytest backend/`) includes browser tests in `tests/test_docs_access_control.py` that rely on Playwright and can block in local environments without a running display or if pipe buffers fill. Focused testing (`pytest backend/tests/test_scoring*.py`) should be used for scoring validation.
3. **Intent Multipliers**: Baseline weights are 15/10/15/15/15/10/10/10, but `weights.py:compute_intent_adjusted_weights` alters them based on `BusinessIntent` (SaaS, Ecommerce, etc.). The frontend Rubric modal displays baseline weights and does not currently show the dynamically adjusted intent weights for the specific audited company.

---

## 4. Conclusion

The Phase 0 codebase investigation is complete. The required fixes are specific and scoped:
1. **Pipeline Ordering & SSE Events**: Remove the premature `node_honest_scoring` RUNNING event at `orchestrator.py:1276`. Emit scoring stage at Step 15 (line 1583). Fix manual DAG node execution at line 2985.
2. **External Authority Detection**: Update `orchestrator.py` lines 1547–1553 to inspect `connection_status == "CONNECTED"` or `data_state in ("MEASURED", "PARTIALLY_MEASURED")`.
3. **Frontend Score Alignment**: Re-anchor `frontend/src/lib/pillarSynthesis.ts` and `Overview.tsx` directly to the 8 canonical categories from `report.scores.category_scores`, eliminating the ad-hoc 45/35/20 blends and hardcoded nulls.
4. **Specification Cleanup**: Remove the obsolete 5-pillar table (25/25/20/20/10) from `backend/app/domain/scoring/scoring_rubric.py`, and reconcile perspective formulas with `calculate_honest_scores`.

---

## 5. Verification Method

1. **Verify Scoring Unit Tests**:
   ```bash
   pytest backend/tests/test_scoring_calibration.py \
          backend/tests/test_scoring_geo_extractability.py \
          backend/tests/test_scoring_missing_measurements.py \
          backend/tests/test_scoring_transparency.py \
          backend/tests/test_scoring_unmeasured_authority.py \
          backend/tests/test_scoring_v5.py -v
   ```
2. **Verify Authority Connection Behavior**:
   Run `test_scoring_unmeasured_authority.py` to confirm that:
   - When `external_authority_connected=False`, `TRUST_AUTHORITY` status is `NOT_MEASURED` and weight is 0.0.
   - When `external_authority_connected=True`, `TRUST_AUTHORITY` status is `MEASURED` and weight > 0.0.
3. **Inspect Frontend Build**:
   ```bash
   cd frontend && npm run build
   ```
4. **Invalidation Conditions**:
   - If `TRUST_AUTHORITY` evaluates to `NOT_MEASURED` when valid provider snapshots are attached.
   - If Overview tab discipline cards show different numbers than `report.scores.category_scores`.
   - If SSE streams `scoring` before post-DAG analyzers complete.
