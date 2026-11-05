# Phase 0 Investigation Report: Pipeline Scoring Timing & UI Consistency

**Date**: 2026-10-31  
**Investigator**: `explorer_survey_2`  
**Target Subsystem**: Backend Pipeline Execution Flow & Frontend Score Synthesis  
**Scope**: Requirements R1 & Acceptance Criteria for Phase 0 (`ORIGINAL_REQUEST.md`, `DRISTIK_WORKING_FLOW_AGENTS_GAPS.md`, `docs/ENTERPRISE_AUDIT_INTEGRITY_REMEDIATION.md`)

---

## 1. Executive Summary

Phase 0 addresses audit scoring integrity and UI consistency. Our codebase investigation examined:
1. **Backend Pipeline Timing & Ordering**: How audit stages execute, where specialist claims and post-DAG analyzers produce findings, when external authority and live search visibility run, and where scoring (`calculate_scores`, `calculate_honest_scores`) and roadmaps (7/30/90) evaluate.
2. **External Authority Connection State**: How `external_authority_connected` is passed and a critical field mismatch bug in `backend/app/orchestration/orchestrator.py` that causes the flag to evaluate to `False` even when external authority providers are connected and snapshots exist.
3. **Frontend Score Synthesis Discrepancies**: The presence of multiple conflicting score calculations across `frontend/src/lib/pillarSynthesis.ts`, `frontend/src/report/models/scoreLedger.ts`, `frontend/src/components/ScoringRubricModal.tsx`, `frontend/src/components/Overview.tsx`, and `backend/app/domain/scoring/scoring_rubric.py`.

### Core Findings Table

| Area | Current Implementation Location | Observation / Problem | Remediation Target |
|---|---|---|---|
| **Pipeline Stage Emission** | `backend/app/orchestration/orchestrator.py:1276` | `node_honest_scoring` is prematurely set to `RUNNING` and SSE emits `AnalysisStage.SCORING` at 93% *before* post-DAG analyzers, live visibility, and external authority run. | Move scoring status emission to Step 15 (line 1583) where scoring actually begins. |
| **Scoring Execution Timing** | `backend/app/orchestration/orchestrator.py:1597-1626` | `calculate_scores` and `calculate_honest_scores` run at lines 1597-1626 after live visibility and external authority attachment. However, manual DAG node execution (`run_pipeline_node("node_honest_scoring")` at line 2985) runs scoring without live visibility or external authority parameters. | Keep Step 15 after external authority; fix manual DAG node execution at line 2985. |
| **External Authority Flag** | `backend/app/orchestration/orchestrator.py:1547-1553` | Checks `c.get("status") == "CONNECTED"`, but `coverage_matrix` produces rows with `"connection_status"` and `"data_state"`. Checks `external_authority_payload.get("status")` which does not exist. Flag stays `False` unless domain findings > 0. | Update detection to inspect `connection_status` and `data_state in ("MEASURED", "PARTIALLY_MEASURED")` or provider snapshots presence. |
| **Roadmap Generation** | `backend/app/orchestration/orchestrator.py:1675-1685` | `RoadmapBuilder.build_roadmap` and `build_top_10_actions` are invoked at Step 16 over `final_findings`. This properly receives external findings appended at line 1545. | Verify regression coverage ensuring external authority findings appear in 7/30/90 roadmap. |
| **Frontend Pillar Synthesis** | `frontend/src/lib/pillarSynthesis.ts:58-70, 152-155, 207, 258` | Synthesizes arbitrary blends: SEO (45% tech, 35% on-page, 20% content); AEO (averaging schema, extractability, bot score); CRO hardcoded to `score: null`; SXO alias equals SEO score; Brand alias equals AEO score. | Re-align `synthesizePillars` directly with canonical 8 category scores from `report.scores.category_scores`. |
| **Rubric Modal vs Engine** | `frontend/src/components/ScoringRubricModal.tsx:35-132, 207-220` vs `backend/app/domain/scoring/scoring_rubric.py:95-150` | `ScoringRubricModal.tsx` Tab 1 lists the 8 categories (15/10/15/15/15/10/10/10), but displays 3 perspective formulas that diverge from backend `calculate_honest_scores`. Backend `scoring_rubric.py` still contains legacy `five_pillars` (25/25/20/20/10). | Eliminate legacy 5-pillar definitions from `scoring_rubric.py`. Reconcile perspective formulas between backend and modal. |
| **Displayed Overall Composite** | `frontend/src/report/models/scoreLedger.ts:44-49` & `frontend/src/lib/displayedAuditScore.ts:76-97` | Overview tab and header calculate overall composite using a 4-pillar model (Technical 30%, GEO 25%, AEO 25%, CRO 20%), which can diverge from backend `scores.overall_score`. | Clarify relationship between canonical 8-category overall score and displayed composite; ensure consistent weights. |

---

## 2. Backend Pipeline Execution Flow Investigation

### 2.1 File Locations and Subsystem Architecture

The backend pipeline orchestrator and associated subsystems reside in:
- **Pipeline Orchestrator**: `backend/app/orchestration/orchestrator.py` (`AnalysisOrchestrator`)
- **Execution Manager**: `backend/app/orchestration/execution_manager.py`
- **Agent Workforce Pool**: `backend/app/orchestration/agent_pool.py` (`AgentPool.execute_all`)
- **Specialist DAG Waves**: `backend/app/orchestration/dependency_resolver.py` (`topological_waves`)
- **Page Intelligence Agent**: `backend/app/crawl/page_intelligence.py` (`PageIntelligenceAgent`)
- **Integrity Validation Gate**: `backend/app/reports/validation_gate.py` (`IntegrityGate`)
- **Live Search Visibility Checks**:
  - Multi-engine audit monitor: `backend/app/geo/audit_monitor.py` (`run_audit_visibility`)
  - AI citation tracker: `backend/app/geo/citations/tracker.py` (`ai_citation_tracker.track_buyer_queries`)
  - GEO on-page extractability readiness: `backend/app/geo/readiness.py` (`evaluate_geo_readiness`)
  - Agent bot readiness: `backend/app/geo/agent_readiness.py` (`evaluate_agent_readiness`)
- **External Authority Connectors**:
  - Attachment bridge: `backend/app/connectors/authority/audit_bridge.py` (`build_audit_attachment`)
  - Authority service: `backend/app/connectors/authority/service.py` (`ExternalAuthorityService`)
  - Report & finding analyzer: `backend/app/connectors/authority/analyze.py` (`build_report`, `coverage_matrix`)
  - Note on module relocation: The authority module was moved from `app.external_authority` to `app.connectors.authority`. Legacy imports in `backend/tests/test_external_authority.py` fail because `sys.modules["app.external_authority"]` alias was not registered in `app/domain/__init__.py`.
- **Deterministic Scoring Engine**:
  - Canonical Scoring Kernel: `backend/app/domain/scoring/engine.py` (`ScoringEngine.calculate_scores` and `ScoringEngine.calculate_honest_scores`)
  - Dynamic Intent Multipliers & Weights: `backend/app/domain/scoring/weights.py` (`BASELINE_WEIGHTS`, `compute_intent_adjusted_weights`)
  - Scoring Rubric Specification: `backend/app/domain/scoring/scoring_rubric.py` (`SCORING_RUBRIC_V4`)
  - Displayed Composite Helper: `backend/app/domain/scoring/displayed_score.py` (`displayed_composite`)
- **Tactical Roadmaps & Top Actions**:
  - Roadmap generator: `backend/app/reports/roadmap.py` (`RoadmapBuilder.build_roadmap`, `RoadmapBuilder.build_top_10_actions`)

---

### 2.2 Execution Sequence Analysis

Tracing `AnalysisOrchestrator.execute_analysis_pipeline` in `backend/app/orchestration/orchestrator.py`:

```
Lines 370-438   : Steps 1-2  - Crawl & DOM AST extraction (node_crawl, node_dom_extraction)
Lines 506-538   : Step 3     - DNS, SSL & Security Headers (node_dns_ssl_headers)
Lines 621-650   : Steps 4-5  - Schema & Entity Resolution (node_schema_ld_json, node_entity_resolution)
Lines 654-670   : Step 6     - ICP & Business Profile (node_icp_offer_profile)
Lines 737-964   : Step 7     - Specialist Workforce DAG execution in topological Kahn waves
Lines 971-1045  : Step 8     - Page Intelligence & copywriting cards (node_seo_page_intelligence)
Lines 1058-1135 : Step 9     - Adversarial Verification (node_adversarial_critic)
Lines 1141-1190 : Step 10    - Evidence Integrity Gate (pruning dangling refs)
Lines 1196-1215 : Step 11    - Causal Bottlenecks initial pass (node_causal_bottlenecks)
Lines 1228-1256 : Step 12    - Commercial Simulation across 6 buyer queries (node_aeo_search_simulation)
Lines 1260-1271 : Step 13    - Executive Strategy Narrative compilation (node_executive_narrative)
────────────────────────────────────────────────────────────────────────────────────────────
Line 1276       : [ANOMALY]  - node_honest_scoring is marked RUNNING and SSE emits stage="scoring" (93%)
                               PREMATURE: deterministic scoring has NOT started yet!
────────────────────────────────────────────────────────────────────────────────────────────
Lines 1285-1371 : Step 14    - Post-DAG Analyzers:
                               Canonicals, HTTP statuses, Heading hierarchy, Media assets,
                               Link depth/orphans, Meta rollup, Form UX, CRO heuristics,
                               Schema rich results, WCAG audit, Local/Intl/Ecommerce SEO,
                               Indexation classifier, Competitor parity, Security headers, Host probe.
Line 1372       : Synthesis  - raw_findings = self.decision_engine.synthesize_findings(...)
Lines 1381-1390 : Entity     - evaluate_entity_graph(...)
Lines 1393-1494 : Live GEO   - run_audit_visibility -> live_citation_score, ai_visibility_scorecard
                               evaluate_geo_readiness, enrich_geo_readiness_citations
Lines 1496-1505 : Agent AEO  - evaluate_agent_readiness
Lines 1508-1524 : Competitor - build competitive evidence graph & competitive report
Lines 1526-1557 : Ext Auth   - build_audit_attachment(project_id, domain, pages, evidence_store)
                               appends attachment["domain_findings"] to raw_findings
                               computes has_external_authority_connected
Lines 1562-1566 : Dedup      - final_findings = FindingDeduplicator.deduplicate(raw_findings)
                               assign_evidence_scope(f, sample_size=len(eval_pages))
Lines 1569-1578 : Causal     - Second Causal Pass with competitive & observatory evidence
────────────────────────────────────────────────────────────────────────────────────────────
Lines 1581-1640 : Step 15    - TRUE Deterministic Scoring Engine execution:
                               calculate_scores(findings=final_findings, external_authority_connected=...,
                                                live_citation_score=..., live_benchmark_data=...)
                               calculate_honest_scores(...)
                               calculate_confidence(...)
                               node_honest_scoring marked COMPLETED
────────────────────────────────────────────────────────────────────────────────────────────
Lines 1645-1686 : Step 16    - Remediation Plan & Roadmaps:
                               remediation_planner.build_remediation_plan(final_findings)
                               roadmap_builder.build_roadmap(final_findings) -> r7, r30, r90
                               roadmap_builder.build_top_10_actions(final_findings, ...)
Lines 1687-2615 : Step 17+   - Digital twin, timeline, narrative assembly, validation gate,
                               cryptographic manifest sealing, progressive report consolidation.
```

---

### 2.3 Critical Finding: `external_authority_connected` Key Mismatch Bug

In `backend/app/orchestration/orchestrator.py` lines 1547–1553:
```python
cov_items = external_authority_payload.get("coverage", [])
if any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in cov_items):
    has_external_authority_connected = True
elif external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
    has_external_authority_connected = True
elif len(attachment.get("domain_findings", [])) > 0:
    has_external_authority_connected = True
```

However, examining `coverage_matrix` and `_coverage_row` in `backend/app/connectors/authority/analyze.py` (lines 87–144):
```python
def _coverage_row(provider, connection_status, data_state, connection, note, app_ready=False):
    return {
        "provider": provider.provider_id,
        "display_name": provider.display_name,
        "connection_status": connection_status,  # <-- Notice: key is "connection_status", NOT "status"
        "data_state": data_state,                # <-- Notice: data state is "MEASURED", "PARTIALLY_MEASURED", etc.
        ...
    }
```
And examining `build_report()` in `backend/app/connectors/authority/analyze.py` (lines 64–84):
The return dictionary has keys:
`["title", "project_id", "domain", "period_days", "period_label", "universal_authority_score", "score_note", "coverage", "pillars", "sections", "findings", "entity_signals", "citation_summary", "competitor_gap", "trends", "data_sources", "notes"]`.
There is **NO top-level `"status"` key** in `external_authority_payload`.

**Failure Consequence**:
1. `c.get("status")` is ALWAYS `None`.
2. `external_authority_payload.get("status")` is ALWAYS `None`.
3. If an external authority connector (GSC, Ahrefs, Semrush, etc.) is connected and returns measured snapshots, but no negative finding is generated (i.e. `domain_findings` is empty), `has_external_authority_connected` evaluates to `False`.
4. As a result, in `ScoringEngine.calculate_scores` (line 247):
   ```python
   elif gate.gate_id == "gate_trust_requires_evidence" and not external_authority_connected:
       ...
       is_unmeasured_by_gate = True
       unmeasured_reason = "connector unavailable"
   ```
   The `trust_authority` category is locked to `NOT_MEASURED` (`score=None`, `weight=0.0`), falsely claiming the connector was unavailable even though live snapshots were attached!

---

### 2.4 Manual Node Execution Anomaly in `orchestrator.py`

In `backend/app/orchestration/orchestrator.py` lines 2983–2995 (`run_pipeline_node("node_honest_scoring")`):
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
In this path:
- `external_authority_connected` is omitted, defaulting to `False`.
- `live_citation_score` is omitted, defaulting to `None`.
- `calculate_honest_scores` is never called.
If a user runs the scoring DAG node directly, scores regress to unmeasured state.

---

## 3. Frontend Score Synthesis & UI Consistency Investigation

### 3.1 Dissection of `frontend/src/lib/pillarSynthesis.ts`

`synthesizePillars` is used by:
1. `frontend/src/components/Overview.tsx` (lines 101, 112, 123, 134, 145, 156)
2. `frontend/src/components/WebsiteIntelligenceTriadHero.tsx` (lines 17, 28, 34, 40, 46, 52)
3. `frontend/src/components/Navigation/PillarNavBar.tsx` (lines 50, 82, 89, 96, 103, 110)

Inspection of calculations in `pillarSynthesis.ts`:
1. **SEO Pillar** (`lines 58-70`):
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
   *Issue*: It blends 3 separate engine categories (`TECHNICAL_SEO`, `ON_PAGE_SEO`, `CONTENT`) using arbitrary weights (45%, 35%, 20%). A user viewing Technical SEO sees one score, but the SEO tab shows this weighted blend.
2. **GEO Pillar** (`lines 108-110`):
   ```typescript
   const geoScore = measuredExtractability != null
     ? Math.round(measuredExtractability)
     : (typeof geoCatScore === 'number' ? Math.round(geoCatScore) : null);
   ```
   *Issue*: Ignores `catScores['GEO']` if `extractability_score` exists, decoupling the category score from the rubric check deductions.
3. **AEO Pillar** (`lines 152-155`):
   ```typescript
   const aeoParts = [schemaScore, extractabilityScore, botScore].filter((n): n is number => typeof n === 'number');
   const aeoScore = aeoParts.length
     ? Math.round(aeoParts.reduce((sum, n) => sum + n, 0) / aeoParts.length)
     : null;
   ```
   *Issue*: Averages `schemaScore`, `extractabilityScore`, and `botScore` unweighted, creating a composite that does not exist in the backend engine.
4. **CRO Pillar** (`lines 207-209`):
   ```typescript
   score: null,
   grade: '—',
   health: getHealth(null),
   ```
   *Issue*: Hardcodes `score: null`! Even though `catScores['UX_CONVERSION']` was computed by the engine, `pillarSynthesis.ts` refuses to display it, showing `—`.
5. **Competitors Pillar** (`lines 234-236`):
   ```typescript
   const totalBakeoff = (bakeoff?.target_wins || 0) + (bakeoff?.competitor_wins || 0) + (bakeoff?.ties || 0);
   const competitorScore = totalBakeoff > 0 ? Math.round(((bakeoff?.target_wins || 0) / totalBakeoff) * 100) : null;
   ```
   *Issue*: Bake-off win rate is displayed as a 0-100 score in place of an audit category.
6. **Legacy Aliases** (`lines 258, 282, 301-305`):
   - `search_intelligence`: points to `seoPillar`
   - `ai_search_intelligence`: points to `geoPillar`
   - `website_experience` (`sxoScore`): `const sxoScore = seoScore ?? null;` (Circularly assigned to the SEO score!)
   - `conversion_intelligence`: points to `croPillar` (null)
   - `brand_entity_intelligence`: `score: aeoScore` (Assigned to the AEO score!)

---

### 3.2 Inspection of `ScoringRubricModal.tsx` & Backend `scoring_rubric.py`

#### `frontend/src/components/ScoringRubricModal.tsx`
- Tab 1 ("Eight Engine Categories", lines 35–132) correctly lists the canonical 8 categories with baseline weights:
  1. Technical SEO (15%)
  2. On-Page SEO (10%)
  3. Content & Semantics (15%)
  4. GEO & AI Readiness (15%)
  5. AI Search Visibility (15%)
  6. Schema Architecture (10%)
  7. UX & Conversion (CRO) (10%)
  8. Trust & Authority (E-E-A-T) (10%)
  Sum = 100%.
- However, Tab 1 lines 202–221 introduces "3 Honest Perspective Views":
  - Google Discoverability: `45% Technical + 35% On-Page + 20% Schema`
  - Human Experience: `40% UX/CRO + 35% Content + 25% Trust`
  - AI Search Readiness: `50% GEO + 50% AI Search Visibility`
  *Discrepancy with backend*: In `backend/app/domain/scoring/engine.py:calculate_honest_scores` (lines 1060–1070):
  - Google View is calculated as: `0.40 * tech_score + 0.30 * onpage_score + 0.30 * schema_score`
  - Human View is calculated as: `0.50 * ux_score + 0.50 * content_score`
  The modal's text teaches different ratios than the engine evaluates!

#### `backend/app/domain/scoring/scoring_rubric.py`
- Lines 95–160 still contains:
  ```python
  "five_pillars": [
      {"id": "search_seo", "name": "Pillar 1: Search Intelligence", "weight_pct": 25},
      {"id": "ai_search_geo", "name": "Pillar 2: AI Search Intelligence", "weight_pct": 25},
      {"id": "experience_sxo", "name": "Pillar 3: Experience Intelligence", "weight_pct": 20},
      {"id": "conversion_cro", "name": "Pillar 4: Conversion Intelligence", "weight_pct": 20},
      {"id": "brand_trust", "name": "Pillar 5: Trust Intelligence", "weight_pct": 10},
  ]
  ```
  This is returned by `GET /api/v1/platform/scoring-rubric`. Any consumer expecting the engine weights gets this obsolete 5-pillar structure.

---

### 3.3 Score Rendering in Overview Tab and Headers

1. **`frontend/src/components/Overview.tsx`**:
   - Overall Score: Computed via `buildDisplayedScore(report)` from `frontend/src/lib/displayedAuditScore.ts`, which uses `REPORT_PILLARS` from `frontend/src/report/models/scoreLedger.ts`:
     - Technical Discoverability: 30%
     - Generative Extractability: 25%
     - Live Citations: 25%
     - Conversion & UX Friction: 20%
   - 5 Discipline Cards: Display `rollup.seo`, `rollup.geo`, `rollup.aeo`, `rollup.cro`, `rollup.competitors` from `pillarSynthesis.ts`.
   *Problem*: The 8 canonical categories are nowhere to be seen on the Overview tab! The cards show synthesized blends that do not match the engine's 8 categories.
2. **`frontend/src/components/WebsiteIntelligenceTriadHero.tsx`**:
   - Renders 5 legacy buttons: Search, AI Search, Experience, Conversion, Brand.
   - Uses `buildDisplayedScore(report).composite` for overall score.
3. **`frontend/src/components/Report.tsx`**:
   - Lines 40–45 and 227–278: Renders "Honest 3-Scores":
     - Human Score (`honest?.human_score ?? UX_CONVERSION * 0.95`)
     - Google Score (`honest?.google_score ?? TECHNICAL_SEO * 0.95`)
     - AI Citation Score (`honest?.ai_citation_score ?? honest?.ai_visibility_score`)
   - Executive story score claim is aligned by `alignDisplayedStory()` to match `buildDisplayedScore()`.

---

## 4. Alignment Strategy: 8 Canonical Categories as the Single Source of Truth

To resolve the inconsistencies identified in R1:

### 4.1 Backend Engine Alignment
1. **Remove Premature SSE Event**:
   In `backend/app/orchestration/orchestrator.py:1276-1283`, remove the premature call to `mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)` and emission of `AnalysisStage.SCORING`. Replace it with `specialist_execution` or `post_analysis` stage.
2. **Fix `has_external_authority_connected`**:
   Update `backend/app/orchestration/orchestrator.py:1547-1553`:
   ```python
   has_external_authority_connected = False
   cov_items = external_authority_payload.get("coverage", [])
   for c in cov_items:
       c_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
       c_data = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
       if c_status == "CONNECTED" or c_data in ("MEASURED", "PARTIALLY_MEASURED"):
           has_external_authority_connected = True
           break
   if len(attachment.get("domain_findings", [])) > 0:
       has_external_authority_connected = True
   ```
3. **Clean Up `scoring_rubric.py`**:
   Remove `five_pillars` from `SCORING_RUBRIC_V4` in `backend/app/domain/scoring/scoring_rubric.py`. Align `honest_perspectives` formulas with `calculate_honest_scores`.
4. **Register Missing `app.external_authority` Alias**:
   In `backend/app/domain/__init__.py`, alias `app.connectors.authority` to `sys.modules["app.external_authority"]` so tests importing `app.external_authority` pass.

### 4.2 Frontend Synthesis Alignment
1. **Refactor `frontend/src/lib/pillarSynthesis.ts`**:
   - Expose the 8 canonical categories directly:
     ```typescript
     technical_seo: catScores['TECHNICAL_SEO']?.score ?? null,
     on_page_seo: catScores['ON_PAGE_SEO']?.score ?? null,
     content: catScores['CONTENT']?.score ?? null,
     geo: catScores['GEO']?.score ?? null,
     ai_search: catScores['AI_SEARCH']?.score ?? null,
     schema: catScores['SCHEMA']?.score ?? null,
     ux_conversion: catScores['UX_CONVERSION']?.score ?? null,
     trust_authority: catScores['TRUST_AUTHORITY']?.score ?? null,
     ```
   - For backward compatibility with tabs expecting `seo`, `geo`, `aeo`, `cro`, map them deterministically to canonical categories:
     - `seo`: `catScores['TECHNICAL_SEO']?.score` or canonical SEO category
     - `geo`: `catScores['GEO']?.score`
     - `aeo` / `ai_search`: `catScores['AI_SEARCH']?.score`
     - `cro`: `catScores['UX_CONVERSION']?.score` (never hardcode null!)
     - `trust`: `catScores['TRUST_AUTHORITY']?.score`
2. **Harmonize Overview Tab**:
   In `frontend/src/components/Overview.tsx`, update the scorecard cards to display the canonical category scores directly from `report.scores.category_scores`, matching the weights taught in `ScoringRubricModal.tsx`.
3. **Harmonize Rubric Modal**:
   Update `ScoringRubricModal.tsx` Tab 1 perspective view descriptions to match the exact mathematical weights computed by `calculate_honest_scores` (Google: 40/30/30, Human: 50/50).

---

## 5. Verification Commands for Implementers

1. **Scoring Unit & Calibration Tests**:
   ```bash
   pytest backend/tests/test_scoring_calibration.py \
          backend/tests/test_scoring_unmeasured_authority.py \
          backend/tests/test_scoring_v5.py \
          backend/tests/test_scoring_geo_extractability.py -v
   ```
2. **Authority & Bridge Tests**:
   ```bash
   pytest backend/tests/test_external_authority.py -v
   ```
3. **Frontend Build & Typecheck**:
   ```bash
   cd frontend && npm run build
   ```
