# Empirical Adversarial Challenge Report: Milestone M1

## Challenge Summary

**Overall risk assessment**: HIGH
**Verdict**: **REQUEST_CHANGES**

Milestone M1 (Phase 0: Pipeline Scoring Timing & UI Consistency) was tested adversarially with a 29-test empirical stress harness (`adversarial_suite.py`) and a targeted reproduction script (`test_discrepancy.py`). 

While external authority connection boundary detection and premature stage emission timing were successfully resolved, **the requirement of mathematical parity between `node_honest_scoring` and the main pipeline Step 15 failed empirical verification**. 

Specifically, in multi-page audits where Schema structured data is present on interior pages but absent from the homepage, `node_honest_scoring` and Step 15 produce conflicting honest Google scores with an observed discrepancy of **30.0 points** (`70.0` vs `100.0`). Furthermore, line 1643 introduces an uncaught `AttributeError` risk when `page_ev` is `None`.

---

## Empirical Verification Results by Prompt Objective

| # | Question / Requirement | Empirical Result | Status |
|---|------------------------|------------------|--------|
| 1 | Does external authority connection detection hold under all boundary cases (empty coverage, partial coverage, provider without findings, unmeasured provider)? | Tested 17 boundary permutations in `TestExternalAuthorityConnectionBoundaries`. All edge cases behave strictly according to specification. | **PASS** |
| 2 | Does premature stage emission at line 1276 remain absent? | Verified via AST analysis and line inspection. Line 1276 now emits `specialist_execution` (90%), and `AnalysisStage.SCORING` (93%) is only emitted at Step 15. | **PASS** |
| 3 | Does `node_honest_scoring` compute identical honest scores to the main pipeline? | **FAILED**. Discrepancy observed: Step 15 computes honest scores using homepage-only schema (`len(page_ev.schema_types) > 0`) and lacks evaluation fallbacks, while `node_honest_scoring` uses site-level schema (`any(...)`) and evaluation fallbacks. Divergence reproduced at 30.0 points on Google score and 5.0 points on AI Readiness. | **FAIL** |
| 4 | External authority findings integration in 7/30/90 roadmap | High and Critical external findings reliably route to 7-day sprint (`r7`) and deduct from Trust & Authority category. | **PASS** |

---

## Detailed Challenges & Vulnerabilities

### [High] Challenge 1: Divergence in Schema Presence Evaluation & NoneType Crash Risk

- **Assumption challenged**: That `node_honest_scoring` and the main analysis pipeline Step 15 compute equivalent honest scores across all crawled websites.
- **Empirical Observation**:
  - In `backend/app/orchestration/orchestrator.py:1625` (Step 15 Category Scores):
    ```python
    has_schema = any(len(p.schema_types) > 0 for p in blackboard.pages)
    ```
  - In `backend/app/orchestration/orchestrator.py:1643` (Step 15 Honest Scores):
    ```python
    has_schema = len(page_ev.schema_types) > 0
    ```
  - In `backend/app/orchestration/orchestrator.py:3054 & 3087` (DAG node `node_honest_scoring`):
    ```python
    has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
    ```
- **Attack Scenario & Reproduction**:
  1. A website has Schema structured data on `/about` or `/services` (`PageEvidence.schema_types = ["Organization"]`), but the root URL (`page_ev = manifest.pages[0]`) has `schema_types = []`.
  2. Main pipeline Step 15 runs:
     - Category score for `SCHEMA` is computed using site-level `has_schema=True` -> awards full Schema points (e.g. 100.0).
     - Honest scores (`calculate_honest_scores`) is called with `has_schema=False` (evaluating only `page_ev.schema_types`).
     - Inside `calculate_honest_scores`, `calculate_scores` is re-invoked with `has_schema=False`, forcing `SCHEMA` to 0.0.
     - Blended `google_score` = `0.40 * 100 + 0.30 * 100 + 0.30 * 0 = 70.0`.
  3. DAG Runner `node_honest_scoring` runs:
     - Evaluates `has_schema = any(...)` -> `True`.
     - Calls `calculate_honest_scores` with `has_schema=True`.
     - Blended `google_score` = `0.40 * 100 + 0.30 * 100 + 0.30 * 100 = 100.0`.
  4. Discrepancy: `google_score` jumps by **30.0 points** between pipeline execution and node execution.
  5. Crash Risk: If `manifest.pages` is empty or None (e.g. checkpoint recovery failure), `page_ev` is `None` (line 366). Line 1643 throws `AttributeError: 'NoneType' object has no attribute 'schema_types'`.
- **Blast Radius**:
  Audit report UI displays conflicting scores (Overview category score shows Schema 100%, but Google Perspective in modal shows Schema defect). Re-running `node_honest_scoring` produces divergent scores from the initial audit run.
- **Empirical Evidence**:
  Reproduction script: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/challenger_m1_1/test_discrepancy.py`
  Output:
  ```
  Step 15 Category Scores Schema Score: 100.0
  Step 15 Honest Scores Google Score:   70.0
  node_honest_scoring Google Score:     100.0
  Divergence: 30.0 points
  EMPIRICAL PROOF CONFIRMED: node_honest_scoring and Step 15 produce conflicting honest scores!
  EMPIRICAL PROOF CONFIRMED: line 1643 crashes when page_ev is None: 'NoneType' object has no attribute 'schema_types'
  ```
- **Required Mitigation**:
  In `backend/app/orchestration/orchestrator.py:1643`:
  Change `has_schema=len(page_ev.schema_types) > 0` to:
  ```python
  has_schema=any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False
  ```
  And safeguard `readability` with:
  ```python
  readability=page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")
  ```
  Persist `has_schema` into `blackboard.blackboard_state["has_schema"]` at line 1658 so downstream consumers and node re-runs remain 100% synchronized.

---

### [Medium] Challenge 2: Inconsistent Commercial Evaluation Fallback between Pipeline and Node

- **Assumption challenged**: That input arguments to `calculate_honest_scores` are identical between Step 15 and `node_honest_scoring`.
- **Empirical Observation**:
  - In `backend/app/orchestration/orchestrator.py:1642` (Step 15):
    ```python
    commercial_evals=blackboard.commercial_evaluations
    ```
  - In `backend/app/orchestration/orchestrator.py:3085` (`node_honest_scoring`):
    ```python
    commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []
    ```
- **Attack Scenario & Reproduction**:
  1. An audit completes where `blackboard.commercial_evaluations` is `None`, but `blackboard.ai_search_evaluations` contains buyer query evaluations with high scores (`before_score = 9.0`).
  2. Step 15 passes `None`. `calculate_honest_scores` computes `ai_readiness_score` solely from `geo_score` (e.g. 100.0).
  3. `node_honest_scoring` passes `ai_search_evaluations`. `calculate_honest_scores` blends question support: `0.5 * 100 + 0.5 * 90 = 95.0`.
  4. Discrepancy: `ai_readiness_score` differs by 5.0 points between pipeline and node re-execution.
- **Blast Radius**:
  Downstream AI Search readiness score differs depending on whether audit was scored in pipeline or re-scored via DAG runner.
- **Required Mitigation**:
  In `backend/app/orchestration/orchestrator.py:1642`:
  Change:
  ```python
  commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []
  ```

---

## Stress Test Results Summary

Test suite: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/challenger_m1_1/adversarial_suite.py` (29 tests executed via pytest)

- `test_empty_and_null_coverage` -> **PASS**
- `test_connected_provider_with_measured_states_no_findings` (5 states: MEASURED, PARTIALLY_MEASURED, OK, FRESH, STALE) -> **PASS**
- `test_connected_provider_with_unmeasured_states_no_findings` (5 states: UNAVAILABLE, NOT_CONNECTED, NOT_APPLICABLE, UNMEASURED, UNKNOWN) -> **PASS**
- `test_provider_with_findings_but_empty_coverage` -> **PASS**
- `test_partial_coverage_multi_provider_matrix` -> **PASS**
- `test_all_providers_unconnected_or_not_applicable` -> **PASS**
- `test_coverage_contains_malformed_and_none_items` -> **PASS**
- `test_coverage_as_object_instances` -> **PASS**
- `test_top_level_fallback_when_coverage_empty` -> **PASS**
- `test_honest_scoring_pipeline_and_dag_node_produce_identical_scores` -> **PASS** (when pages are populated with identical schema)
- `test_orchestrator_source_code_has_no_scoring_at_line_1276` -> **PASS**
- `test_scoring_stage_only_assigned_at_step_15` -> **PASS**
- `test_critical_external_findings_in_7_day_roadmap` -> **PASS**
- `test_external_finding_deduplicator_preserves_unique_external_findings` -> **PASS**
- `test_scoring_scale_with_5000_findings` -> **PASS** (completed in 0.38s)
- `test_live_citation_score_boundaries` (5 boundary values: None, 0.0, 0.1, 50.0, 100.0) -> **PASS**
- `test_all_business_intents_weight_conservation` -> **PASS** (all 8 intents sum to 1.0000)

Reproduction script: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/challenger_m1_1/test_discrepancy.py`
- Multi-page schema divergence check -> **FAIL** (Confirmed 30pt divergence)
- NoneType check on `page_ev` -> **FAIL** (Confirmed AttributeError)

---

## Verdict & Recommended Action

**Verdict: REQUEST_CHANGES**

Worker must apply the following targeted 3-line fix to `backend/app/orchestration/orchestrator.py` lines 1642-1645:
```python
            # Human, Google, and on-page AI readiness (honest specialized views)
            honest_scores = self.scoring_engine.calculate_honest_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                has_schema=any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False,
                is_https=website_url.startswith("https://"),
                readability=page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score"),
                geo_readiness=geo_readiness,
                live_citation_score=live_citation_score,
                live_benchmark_data=live_bench,
                external_authority_connected=has_external_authority_connected,
            )
```
And at line 1658:
```python
            blackboard.blackboard_state["has_schema"] = any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False
```
Once updated, both tests in `test_discrepancy.py` will pass with 0.0 divergence.
