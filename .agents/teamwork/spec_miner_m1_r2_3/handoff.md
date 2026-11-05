# Handoff Report: Milestone M1 (Iteration 2) Regression Test Specification
**Agent**: `spec_miner_m1_r2_3` (Specification Miner)  
**Parent**: `530d48e9-ac3f-4fe2-8d83-6df3cf3f882f`  
**Working Directory**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_r2_3`  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

1. **Step 15 vs DAG Node Inconsistency in `orchestrator.py`**:
   - In `backend/app/orchestration/orchestrator.py:1625`:
     ```python
     has_schema = any(len(p.schema_types) > 0 for p in blackboard.pages)
     ```
   - In `backend/app/orchestration/orchestrator.py:1643`:
     ```python
     has_schema = len(page_ev.schema_types) > 0
     ```
   - In `backend/app/orchestration/orchestrator.py:3054 & 3086`:
     ```python
     has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
     ```
   - Observed empirical outcome from `test_discrepancy.py`:
     When a site has structured data on `/about` (`p1.schema_types = ["Organization"]`) but not on the homepage (`p0.schema_types = []`):
     - Step 15 Category Scores `SCHEMA` evaluates to `100.0`.
     - Step 15 Honest Scores `google_score` evaluates to `70.0` (with Schema as `0.0`).
     - DAG runner `node_honest_scoring` `google_score` evaluates to `100.0` (with Schema as `100.0`).
     - Mathematical divergence: **30.0 points** (`100.0` vs `70.0`).

2. **NoneType Crash Risk on `page_ev`**:
   - In `backend/app/orchestration/orchestrator.py:366`:
     ```python
     page_ev = manifest.pages[0] if manifest.pages else None
     ```
   - In `backend/app/orchestration/orchestrator.py:1627, 1643, 1645, 1657`:
     - Line 1627: `readability=page_ev.readability_score`
     - Line 1643: `has_schema=len(page_ev.schema_types) > 0`
     - Line 1645: `readability=page_ev.readability_score`
     - Line 1657: `blackboard.blackboard_state["readability_score"] = page_ev.readability_score`
   - Observed exception when `page_ev is None`:
     `AttributeError: 'NoneType' object has no attribute 'schema_types'`
     `AttributeError: 'NoneType' object has no attribute 'readability_score'`

3. **Commercial Evaluations Fallback Inconsistency**:
   - Step 15 (line 1642): `commercial_evals=blackboard.commercial_evaluations`
   - DAG runner (line 3085): `commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []`

4. **Blackboard State Missing Key**:
   - At line 1658, `blackboard.blackboard_state` records `external_authority_connected`, `live_citation_score`, `live_bench`, and `readability_score`, but omits `has_schema`.

---

## 2. Logic Chain

1. **Step 15 and `node_honest_scoring` evaluate different schema scopes**:
   - Step 15 `calculate_scores` evaluates site-level schema (`any(...)`), but Step 15 `calculate_honest_scores` evaluates only `page_ev.schema_types` (homepage).
   - `node_honest_scoring` evaluates site-level schema for both calls.
   - Therefore, whenever schema exists on interior pages but not the homepage, Step 15 honest score drops Schema to 0, producing a 30-point drop in `google_score` (formula `0.40 * Tech + 0.30 * OnPage + 0.30 * Schema`) and conflicting with its own `CategoryScores.SCHEMA` score of 100.0.
   - When the DAG runner subsequently executes `node_honest_scoring`, the score jumps to 100.0, creating score inconsistency for the user.

2. **Direct attribute access on `page_ev` assumes `page_ev` is never `None`**:
   - In line 366, `page_ev` is explicitly guarded: `manifest.pages[0] if manifest.pages else None`.
   - When an audit has 0 crawled pages (such as an empty crawl manifest or checkpoint resume), `page_ev` is `None`.
   - Lines 1627, 1643, 1645, and 1657 attempt direct attribute accesses (`page_ev.readability_score`, `page_ev.schema_types`), causing an unhandled `AttributeError`.
   - In contrast, `node_honest_scoring` (lines 3054-3058) cleanly guards against empty page lists using `eval_pages = blackboard.pages or []` and `if eval_pages else False`.

3. **Required Regression Tests**:
   - `test_honest_scores_site_level_schema_consistency`: Verifies that a multi-page audit with interior schema awards full Schema points in Step 15 honest scoring and produces 0.0 divergence with `node_honest_scoring`.
   - `test_honest_scores_empty_manifest_resilience`: Verifies that an empty crawl manifest (`pages=[]`, `page_ev=None`) executes without `AttributeError`, safely defaulting `has_schema=False` and `readability=None`.
   - `test_honest_scores_orchestrator_source_guards`: AST test verifying that Step 15 has no unguarded `page_ev.schema_types` or `page_ev.readability_score` accesses.

---

## 3. Caveats

- The crawler itself raises `RuntimeError("No pages could be crawled from...")` at line 388 when crawling from scratch returns 0 pages. The `page_ev is None` scenario arises when an audit is reloaded from checkpoint, during manual node execution, or when downstream testing passes an empty manifest.
- This agent is read-only on the codebase per instructions. The test code has been fully drafted and specified in `test_blueprint_r2.md`, but the codebase files (`backend/app/orchestration/orchestrator.py` and `backend/tests/test_scoring_timing_and_honest_flag.py`) have not been modified.

---

## 4. Conclusion

The specification and test blueprint for Milestone M1 Iteration 2 is complete:
1. The root causes of the 30.0 point score discrepancy and NoneType crash hazard have been isolated to lines 1625-1658 of `backend/app/orchestration/orchestrator.py`.
2. A comprehensive test blueprint has been published to `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_r2_3/test_blueprint_r2.md` containing:
   - Features Discovered and Edge Cases tables per specification miner protocol.
   - Exact line-by-line fix for `orchestrator.py`.
   - Concrete test cases: `test_honest_scores_site_level_schema_consistency`, `test_honest_scores_empty_manifest_resilience`, and `test_honest_scores_orchestrator_source_guards`.
3. Worker agent can directly apply the 10-line patch to `orchestrator.py` and append the test cases to `backend/tests/test_scoring_timing_and_honest_flag.py`.

---

## 5. Verification Method

Once worker applies the patch and appends the tests:
1. Run target test suite:
   ```bash
   pytest backend/tests/test_scoring_timing_and_honest_flag.py -v
   ```
   *Expected outcome*: 12 passed in < 2 seconds.
2. Run adversarial suite:
   ```bash
   pytest .agents/teamwork/challenger_m1_1/adversarial_suite.py -v
   ```
   *Expected outcome*: 29 passed.
3. Verify discrepancy reproduction:
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 .agents/teamwork/challenger_m1_1/test_discrepancy.py
   ```
   *Expected outcome*: 0.0 points divergence; no AttributeError.
