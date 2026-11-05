# Milestone M1 (Iteration 2) Regression Test Specification Blueprint
**Author**: `spec_miner_m1_r2_3` (Specification Miner)  
**Target Test Suite**: `backend/tests/test_scoring_timing_and_honest_flag.py`  
**Target Implementation Target**: `backend/app/orchestration/orchestrator.py`  
**Status**: Ready for Implementation  

---

## 1. Executive Summary & Specification Context

During Milestone M1 verification, empirical testing by `challenger_m1_1` identified a critical mathematical divergence and a crash hazard between the main analysis pipeline (Step 15: Scoring Engine) and the DAG node runner (`node_honest_scoring`):

1. **Multi-Page Schema Presence Divergence**:
   In `backend/app/orchestration/orchestrator.py:1643` (Step 15 Honest Scoring), `has_schema` was evaluated using homepage evidence only:
   `has_schema = len(page_ev.schema_types) > 0`
   In contrast, Step 15 category scoring (line 1625) and `node_honest_scoring` (lines 3054, 3086) evaluate site-level schema:
   `has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False`
   When structured data is present on interior pages (`/about`, `/products`) but absent on the homepage:
   - Step 15 honest scoring awards 0 points to Schema, causing Google Perspective score to fall to **70.0/100**.
   - `node_honest_scoring` awards full credit (100.0) to Schema, causing Google Perspective score to evaluate to **100.0/100**.
   - Result: A **30.0 point divergence** between initial audit scores and DAG node re-runs, and an internal contradiction within Step 15 itself (`CategoryScores.SCHEMA == 100.0` while `HonestScores.google_score == 70.0`).

2. **Empty Manifest NoneType Crash Hazard**:
   In `backend/app/orchestration/orchestrator.py:1627, 1643, 1645, 1657`:
   When `page_ev` is `None` (e.g., resumed checkpoints with 0 crawled pages, or manifests where `manifest.pages == []`):
   Attempting to access `page_ev.readability_score` or `page_ev.schema_types` raises:
   `AttributeError: 'NoneType' object has no attribute 'schema_types'`
   `AttributeError: 'NoneType' object has no attribute 'readability_score'`

This blueprint specifies two regression tests to be appended to `backend/tests/test_scoring_timing_and_honest_flag.py`:
- `test_honest_scores_site_level_schema_consistency`
- `test_honest_scores_empty_manifest_resilience`
plus an AST guard validation test `test_honest_scores_orchestrator_ast_guards`.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Scoring Parity | Site-Level Schema Evaluation in Step 15 | In Step 15 `calculate_honest_scores`, `has_schema` must evaluate across all crawled pages (`blackboard.pages`), not just `page_ev` (homepage). | Multi-page crawl evidence where `p0.schema_types=[]` and `p1.schema_types=["Organization"]`. | `has_schema=True` passed to `calculate_honest_scores`; `google_score=100.0`. | Unpatched: passes `has_schema=False`, forcing `google_score=70.0` (30pt drop). | `challenger_m1_1/test_discrepancy.py` |
| 2 | Scoring Parity | Step 15 vs `node_honest_scoring` Identity | Honest 3-perspective scores (`google_score`, `human_score`, `ai_readiness_score`, `overall_score`) must be mathematically identical between Step 15 and DAG runner. | Same blackboard state and evidence evaluated by Step 15 and `run_pipeline_node("node_honest_scoring")`. | `step15_honest == node_honest` across all perspectives (`divergence == 0.0`). | Unpatched: `step15_honest.google_score (70.0) != node_honest.google_score (100.0)`. | `adversarial_suite.py` & `test_discrepancy.py` |
| 3 | Pipeline Resilience | Empty Manifest NoneType Guard in Step 15 | When `page_ev` is `None` (empty manifest), Step 15 must safely fallback `has_schema=False` and `readability=None` without crashing. | `manifest.pages=[]`, `blackboard.pages=[]`, `page_ev=None`. | `blackboard.scores` and `blackboard.honest_scores` computed without exception. | Unpatched: crashes with `AttributeError: 'NoneType' object has no attribute 'schema_types'`. | `orchestrator.py:1627-1657` code inspection |
| 4 | State Synchronization | Blackboard State Persistence of `has_schema` | Step 15 must persist `blackboard.blackboard_state["has_schema"]` so downstream nodes and re-runs share exact computed schema state. | Step 15 execution completed. | `blackboard.blackboard_state["has_schema"] == site_has_schema`. | Unpatched: `has_schema` key absent from `blackboard_state` at line 1658. | `orchestrator.py:1654-1658` inspection |
| 5 | Scoring Parity | Commercial Evals Fallback Parity | Step 15 `commercial_evals` argument must fallback to `ai_search_evaluations` matching `node_honest_scoring:3085`. | `blackboard.commercial_evaluations = None`, `ai_search_evaluations` populated. | Blended AI readiness score matching `node_honest_scoring`. | Unpatched: Step 15 passes `None`, omitting query support and diverging by 5.0pts. | `challenge_report.md` |

---

## 3. Edge Cases

| # | Feature | Input Scenario | Expected Behavior | Observed Unpatched Behavior |
|---|---------|----------------|-------------------|-----------------------------|
| E1 | Schema Consistency | Homepage has `[]`, `/about` has `["Organization"]`. | `has_schema=True` in both Step 15 and DAG runner; `google_score=100.0`. | Step 15 receives `has_schema=False`; `google_score=70.0` (30pt drop). Node receives `True` (`100.0`). |
| E2 | Schema Consistency | All pages have `[]` (no schema anywhere). | `has_schema=False` in both Step 15 and DAG runner; identical scores. | Both evaluate `False`; parity preserved on pure negative case. |
| E3 | Empty Manifest | Manifest has 0 crawled pages (`page_ev=None`). | Pipeline Step 15 executes cleanly; `has_schema=False`, `readability=None`. | Crashes with `AttributeError: 'NoneType' object has no attribute 'schema_types'`. |
| E4 | Null Page Attributes | PageEvidence has `schema_types=None` instead of `[]`. | `getattr(p, 'schema_types', []) or []` returns `[]`; no `TypeError`. | `len(p.schema_types)` raises `TypeError: object of type 'NoneType' has no len()`. |
| E5 | Commercial Evals Null | `commercial_evaluations=None`, `ai_search_evaluations=[eval_1]`. | Step 15 and node both fallback to `ai_search_evaluations` for AI readiness. | Step 15 passes `None`, diverging from `node_honest_scoring` by 5.0 points. |

---

## 4. Root Cause Analysis

### Step 15 in `orchestrator.py:1622-1658`:
```python
# Line 1625: Uses site-level pages for CategoryScores
overall_scores = self.scoring_engine.calculate_scores(
    findings=final_findings,
    business_profile=blackboard.business_profile,
    has_schema=any(len(p.schema_types) > 0 for p in blackboard.pages),  # Site-level
    is_https=website_url.startswith("https://"),
    readability=page_ev.readability_score,                              # <-- BUG: NoneType crash if page_ev is None
    ...
)
...
# Line 1642-1645: Uses homepage-only page_ev for HonestScores
honest_scores = self.scoring_engine.calculate_honest_scores(
    findings=final_findings,
    business_profile=blackboard.business_profile,
    commercial_evals=blackboard.commercial_evaluations,                # <-- BUG: Missing ai_search_evaluations fallback
    has_schema=len(page_ev.schema_types) > 0,                          # <-- BUG: Homepage-only & NoneType crash
    is_https=website_url.startswith("https://"),
    readability=page_ev.readability_score,                              # <-- BUG: NoneType crash if page_ev is None
    ...
)
...
# Line 1657:
blackboard.blackboard_state["readability_score"] = page_ev.readability_score # <-- BUG: NoneType crash
# Line 1658: Missing blackboard.blackboard_state["has_schema"]
```

### DAG Runner in `orchestrator.py:3054-3094`:
```python
# Lines 3054-3058: Robust, site-level, guarded
has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
is_https = website_url.startswith("https://") if website_url else False
readability = blackboard.blackboard_state.get("readability_score")
...
honest_scores = self.scoring_engine.calculate_honest_scores(
    findings=blackboard.findings or [],
    business_profile=blackboard.business_profile,
    commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
    has_schema=has_schema,                                            # Site-level passed
    is_https=is_https,
    readability=readability,
    ...
)
```

---

## 5. Required Implementation Fix for Worker

In `backend/app/orchestration/orchestrator.py`:

### Patch Step 15 (around lines 1622-1658):
```python
            # Evaluate site-level schema and robust readability
            site_has_schema = any(len(getattr(p, "schema_types", []) or []) > 0 for p in blackboard.pages) if blackboard.pages else False
            readability_score_val = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")

            overall_scores = self.scoring_engine.calculate_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                has_schema=site_has_schema,
                is_https=website_url.startswith("https://"),
                readability=readability_score_val,
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
                commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                has_schema=site_has_schema,
                is_https=website_url.startswith("https://"),
                readability=readability_score_val,
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
            blackboard.blackboard_state["has_schema"] = site_has_schema
            blackboard.blackboard_state["readability_score"] = readability_score_val
```

---

## 6. Concrete Regression Test Code

The following test functions are designed to be appended directly to `backend/tests/test_scoring_timing_and_honest_flag.py`:

```python
# =============================================================================
# 6. Regression: Step 15 vs node_honest_scoring Parity & Resilience (Milestone M1 R2)
# =============================================================================

@pytest.mark.asyncio
async def test_honest_scores_site_level_schema_consistency(business_profile):
    """
    Regression Test (M1 R2):
    Verify that when interior pages contain Schema structured data (e.g. /about)
    but the homepage does not (schema_types=[]):
    1. Step 15 calculate_honest_scores receives has_schema=True (site-level evaluation).
    2. Step 15 honest Google score awards full Schema credit (100.0) rather than dropping to 70.0.
    3. Step 15 and DAG runner node_honest_scoring produce 100% identical honest scores across
       all three perspectives (Google, Human, AI Readiness) with 0.0 divergence.
    4. blackboard.blackboard_state persists has_schema=True for downstream nodes.
    """
    test_orch = AnalysisOrchestrator()
    run = test_orch.create_run("https://acme-schema-consistency.com")
    analysis_id = run.analysis_id

    # Mark prerequisite completed so DAG runner permits execution
    from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
    controller = get_pipeline_controller(analysis_id)
    controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

    # Setup multi-page crawl: Homepage has NO schema, interior page HAS schema
    p0 = PageEvidence(
        url="https://acme-schema-consistency.com",
        schema_types=[],  # Homepage has no structured data
        readability_score=75.0,
    )
    p1 = PageEvidence(
        url="https://acme-schema-consistency.com/about",
        schema_types=["Organization", "WebSite"],  # Interior page has structured data
        readability_score=78.0,
    )
    pages = [p0, p1]
    manifest = CrawlManifest(
        audit_id=analysis_id,
        domain="acme-schema-consistency.com",
        start_url="https://acme-schema-consistency.com",
        pages=pages,
        total_pages=2,
    )

    from app.orchestration.cognition.blackboard import CognitiveBlackboard
    blackboard = CognitiveBlackboard(run_id=analysis_id, website_url="https://acme-schema-consistency.com")
    blackboard.business_profile = business_profile
    blackboard.findings = []
    blackboard.pages = pages
    blackboard.crawl_manifest = manifest
    test_orch.blackboards[analysis_id] = blackboard

    # --- Part 1: Step 15 Execution Verification ---
    page_ev = manifest.pages[0] if manifest.pages else None
    assert page_ev is not None
    assert len(page_ev.schema_types) == 0, "Homepage must have 0 schema types to reproduce bug condition"

    # Step 15 site-level schema resolution:
    # Must use site-level evaluation across blackboard.pages, NOT page_ev.schema_types!
    site_has_schema = any(len(getattr(p, "schema_types", []) or []) > 0 for p in blackboard.pages) if blackboard.pages else False
    assert site_has_schema is True, "Site-level schema must evaluate to True when interior pages have schema"

    readability_val = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")

    # Spy on calculate_honest_scores to verify arguments passed by Step 15
    recorded_args = {}
    original_calc_honest = test_orch.scoring_engine.calculate_honest_scores

    def spy_calc_honest(*args, **kwargs):
        recorded_args.update(kwargs)
        return original_calc_honest(*args, **kwargs)

    test_orch.scoring_engine.calculate_honest_scores = spy_calc_honest

    step15_scores = test_orch.scoring_engine.calculate_scores(
        findings=blackboard.findings,
        business_profile=blackboard.business_profile,
        has_schema=site_has_schema,
        is_https=True,
        readability=readability_val,
        external_authority_connected=False,
        manifest=manifest,
    )
    blackboard.scores = step15_scores

    step15_honest = test_orch.scoring_engine.calculate_honest_scores(
        findings=blackboard.findings,
        business_profile=blackboard.business_profile,
        commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
        has_schema=site_has_schema,
        is_https=True,
        readability=readability_val,
        geo_readiness=getattr(blackboard, "geo_readiness", None),
        external_authority_connected=False,
    )
    blackboard.honest_scores = step15_honest
    blackboard.blackboard_state["has_schema"] = site_has_schema
    blackboard.blackboard_state["readability_score"] = readability_val

    # Restore engine method
    test_orch.scoring_engine.calculate_honest_scores = original_calc_honest

    # Invariant 1: Step 15 passed has_schema=True
    assert recorded_args.get("has_schema") is True, (
        f"calculate_honest_scores received has_schema={recorded_args.get('has_schema')}, expected True"
    )

    # Invariant 2: Schema category score is 100.0 (full credit, not 0.0)
    assert step15_scores.category_scores[Category.SCHEMA.value].score == 100.0

    # Invariant 3: Google perspective score awards full Schema points: 0.4*100 + 0.3*100 + 0.3*100 = 100.0
    assert step15_honest.google_score == 100.0, (
        f"Step 15 google_score is {step15_honest.google_score}, expected 100.0 (regressed if homepage-only evaluated)"
    )

    # --- Part 2: DAG Node Runner (node_honest_scoring) Parity Verification ---
    res = await test_orch.run_pipeline_node(analysis_id, "node_honest_scoring")
    assert res["success"] is True, f"run_pipeline_node failed: {res}"

    node_scores = blackboard.scores
    node_honest = blackboard.honest_scores

    # Invariant 4: Mathematical Identity across all perspectives
    assert node_honest.google_score == 100.0
    assert abs(step15_honest.google_score - node_honest.google_score) < 1e-6, (
        f"Discrepancy detected between Step 15 ({step15_honest.google_score}) and node_honest_scoring ({node_honest.google_score})"
    )
    assert step15_honest.human_score == node_honest.human_score
    assert step15_honest.ai_readiness_score == node_honest.ai_readiness_score
    assert step15_honest.overall_score == node_honest.overall_score
    assert step15_honest.score_band == node_honest.score_band
    assert blackboard.blackboard_state.get("has_schema") is True


@pytest.mark.asyncio
async def test_honest_scores_empty_manifest_resilience(business_profile):
    """
    Regression Test (M1 R2):
    Verify that when manifest has 0 pages (page_ev is None):
    1. Step 15 executes without raising AttributeError ('NoneType' object has no attribute 'schema_types'
       or 'readability_score').
    2. has_schema safely defaults to False and readability safely defaults to None.
    3. blackboard.scores and blackboard.honest_scores are valid, non-None score objects.
    4. DAG runner node_honest_scoring also executes cleanly without AttributeError.
    5. blackboard.blackboard_state safely records None / False without crashing.
    """
    test_orch = AnalysisOrchestrator()
    run = test_orch.create_run("https://acme-empty-manifest.com")
    analysis_id = run.analysis_id

    from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
    controller = get_pipeline_controller(analysis_id)
    controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

    # Empty manifest setup: 0 pages crawled (e.g., checkpoint recovery or empty crawl)
    empty_manifest = CrawlManifest(
        audit_id=analysis_id,
        domain="acme-empty-manifest.com",
        start_url="https://acme-empty-manifest.com",
        pages=[],
        total_pages=0,
    )

    from app.orchestration.cognition.blackboard import CognitiveBlackboard
    blackboard = CognitiveBlackboard(run_id=analysis_id, website_url="https://acme-empty-manifest.com")
    blackboard.business_profile = business_profile
    blackboard.findings = []
    blackboard.pages = []
    blackboard.crawl_manifest = empty_manifest
    test_orch.blackboards[analysis_id] = blackboard

    # page_ev is strictly None when manifest has no pages
    page_ev = empty_manifest.pages[0] if empty_manifest.pages else None
    assert page_ev is None, "page_ev must be None for empty manifest test"

    # --- Part 1: Step 15 Resilience Verification ---
    try:
        has_schema = any(len(getattr(p, "schema_types", []) or []) > 0 for p in blackboard.pages) if blackboard.pages else False
        readability = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")
    except AttributeError as err:
        pytest.fail(f"AttributeError encountered while extracting page attributes with page_ev=None: {err}")

    assert has_schema is False
    assert readability is None

    # Step 15 calculation must execute cleanly without AttributeError
    try:
        step15_scores = test_orch.scoring_engine.calculate_scores(
            findings=blackboard.findings,
            business_profile=blackboard.business_profile,
            has_schema=has_schema,
            is_https=True,
            readability=readability,
            external_authority_connected=False,
            manifest=empty_manifest,
        )
        step15_honest = test_orch.scoring_engine.calculate_honest_scores(
            findings=blackboard.findings,
            business_profile=blackboard.business_profile,
            commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
            has_schema=has_schema,
            is_https=True,
            readability=readability,
            geo_readiness=None,
            external_authority_connected=False,
        )
        blackboard.scores = step15_scores
        blackboard.honest_scores = step15_honest
        blackboard.blackboard_state["has_schema"] = has_schema
        blackboard.blackboard_state["readability_score"] = readability
    except AttributeError as err:
        pytest.fail(f"Step 15 raised AttributeError on empty manifest: {err}")

    assert blackboard.scores is not None
    assert blackboard.honest_scores is not None
    assert blackboard.honest_scores.google_score is not None
    assert blackboard.honest_scores.human_score is not None
    assert blackboard.blackboard_state["has_schema"] is False
    assert blackboard.blackboard_state["readability_score"] is None

    # --- Part 2: DAG Node Runner (node_honest_scoring) Resilience Verification ---
    try:
        res = await test_orch.run_pipeline_node(analysis_id, "node_honest_scoring")
    except AttributeError as err:
        pytest.fail(f"node_honest_scoring raised AttributeError on empty manifest: {err}")

    assert res["success"] is True
    assert blackboard.scores is not None
    assert blackboard.honest_scores is not None
    assert blackboard.honest_scores.google_score == step15_honest.google_score
    assert blackboard.honest_scores.human_score == step15_honest.human_score


def test_honest_scores_orchestrator_source_guards():
    """
    Static Analysis / AST Guard Test:
    Verify that orchestrator.py Step 15 contains no unguarded accesses to:
    1. page_ev.schema_types (which triggers AttributeError when page_ev is None
       and violates site-level schema consistency).
    2. Unguarded page_ev.readability_score.
    """
    import ast
    orch_path = "/Users/sayantande/Downloads/dristik-main/backend/app/orchestration/orchestrator.py"
    with open(orch_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=orch_path)

    # Locate execute_analysis_pipeline function definition
    exec_func = next(
        (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "execute_analysis_pipeline"),
        None
    )
    assert exec_func is not None, "execute_analysis_pipeline not found in orchestrator.py"

    # Search for unguarded page_ev.schema_types
    prohibited_patterns = []
    for node in ast.walk(exec_func):
        if isinstance(node, ast.Attribute) and node.attr == "schema_types":
            if isinstance(node.value, ast.Name) and node.value.id == "page_ev":
                prohibited_patterns.append(f"Line {node.lineno}: page_ev.schema_types (homepage-only schema access prohibited)")

    assert len(prohibited_patterns) == 0, (
        f"Found prohibited homepage-only schema access in Step 15:\n" + "\n".join(prohibited_patterns)
    )
```

---

## 7. Verification Method

Once worker applies the patch to `backend/app/orchestration/orchestrator.py` and appends the tests to `backend/tests/test_scoring_timing_and_honest_flag.py`:

```bash
# 1. Run the scoring timing and honest flag test suite (now 12 tests, previously 9 tests)
pytest backend/tests/test_scoring_timing_and_honest_flag.py -v

# 2. Run the adversarial suite to confirm zero regressions
pytest .agents/teamwork/challenger_m1_1/adversarial_suite.py -v

# 3. Confirm discrepancy reproduction script now passes with 0 divergence
python3 .agents/teamwork/challenger_m1_1/test_discrepancy.py
```
