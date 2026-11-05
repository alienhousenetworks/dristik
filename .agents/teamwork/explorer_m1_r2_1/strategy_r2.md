# Remediation Blueprint & Strategy: Milestone M1 Iteration 2 (M1_R2)

## Executive Summary

During Milestone M1 Iteration 1 adversarial validation, `challenger_m1_1` identified a mathematical divergence and crash risks between the main analysis pipeline (`Step 15`) and the DAG node runner (`node_honest_scoring`) in `backend/app/orchestration/orchestrator.py`:
1. **Schema Evaluation Discrepancy**: In multi-page audits where Schema structured data is present on interior pages (e.g. `/about`, `/services`) but absent from the homepage, Step 15 evaluates `has_schema` using homepage evidence only (`len(page_ev.schema_types) > 0`), whereas `calculate_scores` and DAG runner `node_honest_scoring` evaluate `has_schema` across all pages (`any(...)`). This creates a **30.0 point divergence** in the honest Google Perspective score (`70.0` vs `100.0`) and internal contradictions on the audit report UI.
2. **Unhandled NoneType Crashes**: When `page_ev` is `None` (empty crawl manifest, zero discovered pages, or headless checkpoint restore), Step 15 raises `AttributeError: 'NoneType' object has no attribute 'schema_types'` and `'readability_score'`.
3. **Evaluation Fallback Divergence**: When `blackboard.commercial_evaluations` is unset, `node_honest_scoring` falls back to `blackboard.ai_search_evaluations or []`, while Step 15 passes `None`, producing a **5.0 point divergence** in the AI Readiness score.
4. **State Persistence Gap**: Step 15 does not persist `has_schema` into `blackboard.blackboard_state`, preventing headless node re-runs from maintaining state parity.

This blueprint provides the exact, unified, non-breaking remediation to align Step 15 and `node_honest_scoring`.

---

## Root Cause Analysis

### 1. Schema Presence Discrepancy (30.0 pt Google Score Divergence)
- **Step 15 Category Scores (`orchestrator.py:1625`)**:
  ```python
  has_schema=any(len(p.schema_types) > 0 for p in blackboard.pages)
  ```
- **Step 15 Honest Scores (`orchestrator.py:1643`)**:
  ```python
  has_schema=len(page_ev.schema_types) > 0
  ```
- **DAG Runner `node_honest_scoring` (`orchestrator.py:3054 & 3086`)**:
  ```python
  has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
  ...
  honest_scores = self.scoring_engine.calculate_honest_scores(..., has_schema=has_schema, ...)
  ```
- **Mathematical Impact**:
  When page 0 lacks schema but page 1 has schema:
  - `calculate_scores` awards full schema points (100.0) -> Schema Category = 100%.
  - `calculate_honest_scores` in Step 15 re-invokes `calculate_scores(has_schema=False)`, collapsing Schema Category to 0.0%.
  - Google Score formula = `0.40 * Technical + 0.30 * OnPage + 0.30 * Schema`.
  - Step 15 yields `0.40(100) + 0.30(100) + 0.30(0) = 70.0`.
  - `node_honest_scoring` yields `0.40(100) + 0.30(100) + 0.30(100) = 100.0`.
  - Discrepancy: **30.0 points**.

### 2. NoneType Crash Vulnerability
- In `orchestrator.py:366`, `page_ev` is assigned:
  ```python
  page_ev = manifest.pages[0] if manifest.pages else None
  ```
- When `manifest.pages` is empty, `page_ev` is `None`.
- At line 1627: `readability=page_ev.readability_score` throws `AttributeError`.
- At line 1643: `has_schema=len(page_ev.schema_types) > 0` throws `AttributeError`.
- At line 1645: `readability=page_ev.readability_score` throws `AttributeError`.
- At line 1657: `blackboard.blackboard_state["readability_score"] = page_ev.readability_score` throws `AttributeError`.
- At line 2076-2077: `manifest.crawl_health.get("avg_ttfb_ms", page_ev.ttfb_ms)` throws `AttributeError` because default expressions in `.get()` are eagerly evaluated.

### 3. Commercial Evaluation Fallback Divergence (5.0 pt AI Readiness Divergence)
- In Step 15 line 1642:
  ```python
  commercial_evals=blackboard.commercial_evaluations
  ```
- In `node_honest_scoring` line 3085:
  ```python
  commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []
  ```
- When `commercial_evaluations` is empty/None but `ai_search_evaluations` exists with buyer queries:
  - Step 15 ignores evaluations, resulting in `ai_readiness_score = geo_score` (e.g. 100.0).
  - `node_honest_scoring` blends question evaluations (`avg_comm * 10.0`), resulting in `95.0`.
  - Discrepancy: **5.0 points**.

---

## Remediation Blueprint

### Target File: `backend/app/orchestration/orchestrator.py`

#### Changes in Step 15 (Lines 1622–1658)
Extract normalized scoring variables prior to calling `calculate_scores` and `calculate_honest_scores`:
1. `has_schema`: Compute site-wide schema presence safely using `any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False`.
2. `readability_val`: Safely extract readability with `page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")`.
3. `is_https_val`: Validate with `website_url.startswith("https://") if website_url else False`.
4. `commercial_evals_val`: Standardize fallback to `blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []`.
5. Pass `has_schema`, `readability_val`, `is_https_val`, and `commercial_evals_val` into both `calculate_scores` and `calculate_honest_scores`.
6. Persist `blackboard.blackboard_state["has_schema"] = has_schema` alongside `readability_score`.

#### Changes in DAG Node Runner `node_honest_scoring` (Lines 3054–3060)
Check `blackboard.blackboard_state.get("has_schema")` first for headless re-runs before computing from `eval_pages`.

#### Defensive Hardening in Crawl Summary (Lines 2076–2077)
Prevent eager evaluation crash when `page_ev` is `None`:
`page_ev.ttfb_ms if page_ev else 0` and `page_ev.word_count if page_ev else 0`.

---

## Exact Unified Diff Patch

```diff
--- a/backend/app/orchestration/orchestrator.py
+++ b/backend/app/orchestration/orchestrator.py
@@ -1621,38 +1621,44 @@ class AnalysisOrchestrator:
                     live_bench["share_of_model"] = geo_bench_report["share_of_model"]
 
+            has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False
+            readability_val = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")
+            is_https_val = website_url.startswith("https://") if website_url else False
+            commercial_evals_val = blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []
+
             overall_scores = self.scoring_engine.calculate_scores(
                 findings=final_findings,
                 business_profile=blackboard.business_profile,
-                has_schema=any(len(p.schema_types) > 0 for p in blackboard.pages),
-                is_https=website_url.startswith("https://"),
-                readability=page_ev.readability_score,
+                has_schema=has_schema,
+                is_https=is_https_val,
+                readability=readability_val,
                 external_authority_connected=has_external_authority_connected,
                 live_citation_score=live_citation_score,
                 live_benchmark_data=live_bench,
                 manifest=manifest,
             )
             extractability = getattr(geo_readiness, "extractability_score", None)
             if overall_scores is not None and extractability is not None:
                 self.scoring_engine.apply_measured_geo_score(overall_scores, extractability)
             blackboard.scores = overall_scores
 
             # Human, Google, and on-page AI readiness (honest specialized views)
             honest_scores = self.scoring_engine.calculate_honest_scores(
                 findings=final_findings,
                 business_profile=blackboard.business_profile,
-                commercial_evals=blackboard.commercial_evaluations,
-                has_schema=len(page_ev.schema_types) > 0,
-                is_https=website_url.startswith("https://"),
-                readability=page_ev.readability_score,
+                commercial_evals=commercial_evals_val,
+                has_schema=has_schema,
+                is_https=is_https_val,
+                readability=readability_val,
                 geo_readiness=geo_readiness,
                 live_citation_score=live_citation_score,
                 live_benchmark_data=live_bench,
                 external_authority_connected=has_external_authority_connected,
             )
             blackboard.honest_scores = honest_scores
 
             # Persist environmental scoring context for downstream nodes / re-runs
             blackboard.blackboard_state["external_authority_connected"] = has_external_authority_connected
             blackboard.blackboard_state["live_citation_score"] = live_citation_score
             blackboard.blackboard_state["live_bench"] = live_bench
-            blackboard.blackboard_state["readability_score"] = page_ev.readability_score
+            blackboard.blackboard_state["readability_score"] = readability_val
+            blackboard.blackboard_state["has_schema"] = has_schema
@@ -2076,2 +2082,2 @@ class AnalysisOrchestrator:
-                    "avg_ttfb_ms": manifest.crawl_health.get("avg_ttfb_ms", page_ev.ttfb_ms),
-                    "total_words": manifest.crawl_health.get("total_words_across_site", page_ev.word_count),
+                    "avg_ttfb_ms": manifest.crawl_health.get("avg_ttfb_ms", page_ev.ttfb_ms if page_ev else 0),
+                    "total_words": manifest.crawl_health.get("total_words_across_site", page_ev.word_count if page_ev else 0),
@@ -3054,1 +3060,3 @@ class AnalysisOrchestrator:
-                has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
+                has_schema = blackboard.blackboard_state.get("has_schema")
+                if has_schema is None:
+                    has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
```

---

## Verification & Non-Regression Blueprint

### Regression Test Implementation
A dedicated regression test must be added to `backend/tests/test_scoring_timing_and_honest_flag.py`:

```python
@pytest.mark.asyncio
async def test_honest_scoring_multipage_schema_and_eval_parity():
    """
    Verify mathematical parity between Step 15 scoring and DAG runner node_honest_scoring
    on non-uniform multi-page sites (Schema on interior page, None on homepage)
    and ensure evaluations fallback parity.
    """
    test_orch = AnalysisOrchestrator()
    run = test_orch.create_run("https://multipage-schema-test.com")
    analysis_id = run.analysis_id

    from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
    controller = get_pipeline_controller(analysis_id)
    controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

    # Page 0 has no schema, Page 1 has schema
    p0 = PageEvidence(url="https://multipage-schema-test.com", schema_types=[], readability_score=78.0)
    p1 = PageEvidence(url="https://multipage-schema-test.com/services", schema_types=["Service"], readability_score=78.0)

    from app.orchestration.cognition.blackboard import CognitiveBlackboard
    from types import SimpleNamespace
    bb = CognitiveBlackboard(run_id=analysis_id, website_url="https://multipage-schema-test.com")
    bb.business_profile = BusinessProfile(
        business_name="Multi-page Test",
        domain="multipage-schema-test.com",
        industry="SaaS",
        primary_intent=BusinessIntent.SAAS,
    )
    bb.findings = []
    bb.pages = [p0, p1]
    bb.crawl_manifest = CrawlManifest(
        audit_id=analysis_id,
        domain="multipage-schema-test.com",
        start_url="https://multipage-schema-test.com",
        pages=[p0, p1],
    )
    bb.commercial_evaluations = None
    bb.ai_search_evaluations = [SimpleNamespace(before_score=8.5)]
    test_orch.blackboards[analysis_id] = bb

    # Execute DAG node runner
    res = await test_orch.run_pipeline_node(analysis_id, "node_honest_scoring")
    assert res["success"] is True

    # Validate that has_schema was recognized site-wide
    assert bb.scores.category_scores["SCHEMA"].score == 100.0
    assert bb.honest_scores.google_score == 100.0
    assert bb.honest_scores.ai_readiness_score == 92.5
```

### Verification Commands
1. Run empirical parity verification:
   ```bash
   python3.12 /Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m1_r2_1/test_blueprint_verification.py
   ```
   *Expected*: `Divergence: 0.0000 points`, `VERIFICATION SUCCESS`.
2. Run adversarial test suite:
   ```bash
   pytest /Users/sayantande/Downloads/dristik-main/.agents/teamwork/challenger_m1_1/adversarial_suite.py -v
   ```
   *Expected*: `29 passed`.
3. Run M1 scoring timing test suite:
   ```bash
   pytest /Users/sayantande/Downloads/dristik-main/backend/tests/test_scoring_timing_and_honest_flag.py -v
   ```
   *Expected*: `9 passed` (or `10 passed` with new regression test).
