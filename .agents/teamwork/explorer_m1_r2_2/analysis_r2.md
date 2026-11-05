# Mathematical and Behavioral Analysis: Aligning Step 15 Scoring with `node_honest_scoring`

**Author**: `explorer_m1_r2_2`  
**Date**: 2026-10-31  
**Target Milestone**: Milestone M1 (Phase 0: Pipeline Scoring Timing & UI Consistency)  
**Target Files**:
- `backend/app/orchestration/orchestrator.py` (lines 1622–1658 and 3054–3094)
- `backend/app/domain/scoring/engine.py` (lines 354, 438–443, 453–457, 1015–1097)

---

## Executive Summary

This investigation analyzed the mathematical and behavioral consequences of aligning Step 15 `calculate_honest_scores` with `node_honest_scoring` in Dristik AI.

1. **Root Cause of Divergence**:
   Step 15 in `backend/app/orchestration/orchestrator.py` evaluated `has_schema` using only the homepage (`len(page_ev.schema_types) > 0` at line 1643), while category scoring at line 1625 and the DAG runner `node_honest_scoring` at line 3054 evaluated site-level schema (`any(...)` across all crawled pages).
2. **Empirical Mathematical Impact**:
   - In multi-page audits where Schema structured data is present on interior pages (`/about`, `/products`, etc.) but absent on the root URL (`page_ev = manifest.pages[0]`), Step 15 forced `SCHEMA` to `0.0` in `calculate_honest_scores`.
   - Because `google_score = 0.40 * Technical + 0.30 * OnPage + 0.30 * Schema`, this discrepancy created an exact **30.0 point drop** in `google_score` (`70.0` vs `100.0`), a **10.5 point drop** in `honest_scores.overall_score`, and caused inconsistent score band classification ("Citation Ready" vs "Fragile Presence").
   - Furthermore, Step 15 passed `commercial_evals=blackboard.commercial_evaluations` without falling back to `blackboard.ai_search_evaluations`, causing an additional **5.0 point divergence** on `ai_readiness_score`.
3. **Crash Vulnerability Identified**:
   If `page_ev` is `None` (manifest with 0 pages or checkpoint loaded without pages), lines 1627, 1643, 1645, and 1657 throw an uncaught `AttributeError: 'NoneType' object has no attribute 'schema_types' / 'readability_score'`.
4. **Design Contract Alignment**:
   Site-level schema resolution (`any(len(p.schema_types) > 0 for p in blackboard.pages)`) perfectly matches the Dristik AI multi-page crawl design contract, the deduction message in `engine.py:457` (*"in crawl sample"*), and the architecture of the GEO and external authority bridge subsystems.
5. **Safety of Defaults**:
   When `readability` is `None` or manifest has 0 pages, `engine.py` marks `audience_flesch_reading_ease` as `NOT_MEASURED` and gracefully renormalizes without throwing an exception or corrupting scores.

---

## 1. Mathematical Breakdown: How `has_schema` Influences the Google Perspective

### 1.1 The Scoring Engine Mechanism (`backend/app/domain/scoring/engine.py`)

`calculate_honest_scores` (lines 1015–1097) invokes `calculate_scores` with the provided `has_schema` boolean parameter:

```python
scores_res = self.calculate_scores(
    findings=findings,
    business_profile=business_profile,
    has_schema=has_schema,
    is_https=is_https,
    readability=readability,
    external_authority_connected=external_authority_connected,
    ...
)
```

Inside `calculate_scores`:
1. **When `has_schema is None`** (lines 354–359):
   - For all checks where `cat_enum == Category.SCHEMA`:
     - `is_measured = False`
     - `status = "NOT_MEASURED"`
     - `s = 0.0; passed = 0; failed = 0`
   - The category score is marked `NOT_MEASURED` with `score = None`.
2. **When `has_schema is False`** (lines 453–457):
   - For all checks where `cat_enum == Category.SCHEMA`:
     - `s = 0.0; passed = 0; failed = 1`
     - Evidence record: `{"schema": "missing", "status": "FAIL", "detail": "No Schema.org types recorded in crawl sample."}`
   - Every schema check fails completely. The category score evaluates to:
     $$\text{CategoryScore}(\text{Category.SCHEMA}).\text{score} = 0.0$$
3. **When `has_schema is True`**:
   - Schema checks evaluate based on matched findings. In the absence of schema violation findings, all checks pass ($s = 1.0$), yielding:
     $$\text{CategoryScore}(\text{Category.SCHEMA}).\text{score} = 100.0$$

### 1.2 The Google Perspective Formulation

In `calculate_honest_scores` (lines 1062–1064):
```python
# Google View: Technical (40%) + On-Page (30%) + Schema (30%).
google_score = weighted_mean([(0.40, tech_score), (0.30, onpage_score), (0.30, schema_score)])
```
When all three categories are measured, the denominator is $0.40 + 0.30 + 0.30 = 1.00$.

Therefore:
$$\Delta \text{google\_score} = 0.30 \times (\text{schema\_score}_{\text{site}} - \text{schema\_score}_{\text{homepage}})$$

For a healthy site with valid Schema on interior pages ($\text{tech\_score} = 100$, $\text{onpage\_score} = 100$):
- **Homepage-only evaluation (`has_schema=False`)**:
  $$\text{google\_score} = 0.40(100) + 0.30(100) + 0.30(0) = \mathbf{70.0}$$
- **Site-level evaluation (`has_schema=True`)**:
  $$\text{google\_score} = 0.40(100) + 0.30(100) + 0.30(100) = \mathbf{100.0}$$
- **Divergence**: Exactly $\mathbf{30.0\text{ points}}$!

### 1.3 Downstream Propagation into Composite and UI

In `calculate_honest_scores` (lines 1093–1097):
```python
overall = weighted_mean([
    (0.35, human_score),
    (0.35, google_score),
    (0.30, ai_readiness_score),
])
```
The $30.0$ point suppression of `google_score` propagates into `overall`:
$$\Delta \text{overall\_score} = 0.35 \times 30.0 = \mathbf{10.5\text{ points}}$$

This causes two severe customer-facing defects:
1. **UI Discrepancy**: On the Overview tab, the canonical Category Score for Schema displays `100% (Grade A)`. In the Scoring Rubric modal, the Google Perspective displays a severe Schema penalty with Google score at `70%`.
2. **Band Degradation**: An overall score of $78.0$ (falling into the `"Citation Ready"` or `"Structure Ready"` band, $\ge 75$) drops to $67.5$, shifting into the `"Fragile Presence"` band ($50 \le \text{score} < 75$).

---

## 2. Design Contract Analysis: Site-Level vs. Page-Level Schema

### 2.1 Codebase Precedent

Across the entire Dristik AI platform, Schema detection is defined at the **site level** across all crawled pages:

| Subsystem | File & Line | Implementation | Contract |
|---|---|---|---|
| Category Scoring (Step 15) | `orchestrator.py:1625` | `any(len(p.schema_types) > 0 for p in blackboard.pages)` | **Site-level** |
| DAG Honest Scoring | `orchestrator.py:3054` | `any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages)` | **Site-level** |
| Deduction String | `engine.py:457` | `"No Schema.org types recorded in crawl sample."` | **Sample-level** |
| GEO Readiness Analyzer | `geo/readiness.py:651` | `sorted({t for p in pages for t in (p.schema_types or [])})` | **Site-level** |
| Per-Engine Evaluator | `geo/per_engine_evaluator.py:82` | `schemas_present.update(p.schema_types or [])` | **Site-level** |
| Schema Crosscheck | `geo/schema_crosscheck.py:101` | `detected_types.update(p.schema_types or [])` | **Site-level** |
| Agent Readiness | `geo/agent_readiness.py:108` | `{t.lower() for page in pages for t in (page.schema_types or [])}` | **Site-level** |
| External Authority Bridge | `authority/audit_bridge.py:49` | `for item in getattr(page, "schema_types", None) or []:` | **Site-level** |
| Step 15 Honest Scores | `orchestrator.py:1643` | `len(page_ev.schema_types) > 0` | **Homepage only (ANOMALY)** |

### 2.2 Domain Rationale

In real-world web architecture:
- Many enterprise websites deploy Schema types across specific templates:
  - `Organization` / `LocalBusiness` on `/about` or `/contact`
  - `Product` / `Offer` / `AggregateRating` on `/products/*` or `/services/*`
  - `FAQPage` on `/faq` or `/support`
  - `Article` / `BlogPosting` on `/blog/*`
- Testing Schema solely against `page_ev` (`manifest.pages[0]`) violates Dristik AI's multi-page audit premise.
- Therefore, site-level `has_schema` resolution is the canonical contract.

---

## 3. Crash Risk and Safe Readability Fallback

### 3.1 Uncaught NoneType Vulnerabilities in Step 15

When `manifest.pages` is empty (e.g., failed crawl, domain timeout, checkpoint restored without page evidence), `page_ev` evaluates to `None` at line 366 (`page_ev = manifest.pages[0] if manifest.pages else None`).

In Step 15, the following lines execute unchecked attribute access on `page_ev`:
1. Line 1627: `readability=page_ev.readability_score`
2. Line 1643: `has_schema=len(page_ev.schema_types) > 0`
3. Line 1645: `readability=page_ev.readability_score`
4. Line 1657: `blackboard.blackboard_state["readability_score"] = page_ev.readability_score`

Each of these lines raises:
```
AttributeError: 'NoneType' object has no attribute 'schema_types'
AttributeError: 'NoneType' object has no attribute 'readability_score'
```

### 3.2 Behavior in `ScoringEngine` when `readability=None`

In `backend/app/domain/scoring/engine.py:438–443`:
```python
elif cid == "audience_flesch_reading_ease":
    if readability is None or isinstance(readability, bool) or not isinstance(readability, (int, float)) or not math.isfinite(float(readability)):
        is_measured = False
        status = "NOT_MEASURED"
    else:
        s = audience_readability_score(readability, audience=getattr(business_profile, "target_audience", None) or "b2b")
        evidence_list.append({"readability": readability, "status": "PASS" if s >= 0.7 else "PARTIAL"})
```

Empirical verification confirms:
- When `readability=None`, `audience_flesch_reading_ease` is marked `status="NOT_MEASURED"`, `is_measured=False`.
- The `Category.CONTENT` score renormalizes over the remaining measured content checks (e.g. sentence length, outline depth, author byline).
- `human_score` and `overall_score` calculate smoothly without any exception.
- When `manifest` has 0 pages or `manifest is None`, `calculate_scores` and `calculate_honest_scores` complete successfully (tested overall scores: $87.2$ and $85.0$).

---

## 4. Evaluation Fallback Parity: Commercial Evaluations

In addition to schema, an inconsistency was identified in `commercial_evals`:
- Step 15 (line 1642):
  ```python
  commercial_evals=blackboard.commercial_evaluations
  ```
- `node_honest_scoring` (line 3085):
  ```python
  commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []
  ```

In audits where `blackboard.commercial_evaluations` is unset but `blackboard.ai_search_evaluations` contains scored queries, Step 15 calculates `ai_readiness_score` solely from `geo_score`, whereas `node_honest_scoring` blends `geo_score` with question support:
$$\text{ai\_readiness\_score} = 0.50 \times \text{geo\_score} + 0.50 \times (\text{avg\_comm} \times 10.0)$$
This introduced up to **5.0 points of divergence** on `ai_readiness_score`.

---

## 5. Verification Matrix

| Test Scenario | Prior Pipeline Behavior | Aligned Behavior | Expected Parity |
|---|---|---|---|
| Single-page site with Schema on homepage | Step 15: Google=100<br>Node: Google=100 | Step 15: Google=100<br>Node: Google=100 | **Identical (0.0 divergence)** |
| Multi-page site with Schema on `/about` only | Step 15: Google=70<br>Node: Google=100 | Step 15: Google=100<br>Node: Google=100 | **Identical (0.0 divergence)** |
| Site without Schema anywhere | Step 15: Google=70<br>Node: Google=70 | Step 15: Google=70<br>Node: Google=70 | **Identical (0.0 divergence)** |
| Empty crawl / `page_ev is None` | Step 15: **CRASH** (`AttributeError`) | Step 15: Safe fallback (`NOT_MEASURED`) | **No crash, graceful fallback** |
| `commercial_evals=None`, `ai_search_evals` present | Step 15: AI=100<br>Node: AI=95 | Step 15: AI=95<br>Node: AI=95 | **Identical (0.0 divergence)** |

---

## 6. Recommended Code Modifications for Implementer

In `backend/app/orchestration/orchestrator.py` at Step 15 (lines 1622–1658):

```python
            # Resolve site-level schema and safe readability
            has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in blackboard.pages) if blackboard.pages else False
            readability = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")

            overall_scores = self.scoring_engine.calculate_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                has_schema=has_schema,
                is_https=website_url.startswith("https://"),
                readability=readability,
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
                has_schema=has_schema,
                is_https=website_url.startswith("https://"),
                readability=readability,
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
            blackboard.blackboard_state["has_schema"] = has_schema
            blackboard.blackboard_state["readability_score"] = readability
```
