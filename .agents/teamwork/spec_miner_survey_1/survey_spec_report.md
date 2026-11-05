# Dristik AI Phase 0 & Phase 1 Ground Truth Specification Report

**Prepared by:** `spec_miner_survey_1` (teamwork_preview_spec_miner)  
**Date:** 2026-10-31  
**Target Milestone:** Phase 0 (Pipeline Scoring Timing & UI Consistency) and Phase 1 (Unified Enterprise Persistence & Strict Multi-Tenancy Isolation)  
**Authoritative Documentation Probed:**
- `DRISTIK_WORKING_FLOW_AGENTS_GAPS.md` (Live tree map as of October 2026)
- `docs/ENTERPRISE_AUDIT_INTEGRITY_REMEDIATION.md` (Hardening contract and non-negotiable evidence policy)
- `.agents/teamwork/ORIGINAL_REQUEST.md` (Phase 0 and Phase 1 objectives)
- Live Source Tree: `backend/app/domain/scoring/`, `backend/app/orchestration/orchestrator.py`, `backend/app/db/`, `backend/app/identity/`, `backend/app/connectors/authority/`, `frontend/src/lib/pillarSynthesis.ts`, `frontend/src/components/ScoringRubricModal.tsx`

---

## 1. Executive Summary

Dristik AI is an evidence-backed website-intelligence auditor operating on an explicit representative sample crawl (default 10 pages). The core product rule is **strict empirical grounding**:
- Every customer-facing score or claim must be backed by a verified DOM selector, HTTP telemetry, or verified external API snapshot.
- An LLM may interpret evidence, but must **never fabricate** Core Web Vitals, backlinks, Search Console clicks, live ChatGPT citations, or an unearned universal authority score.
- Unmeasured pillars stay unmeasured (`NOT_MEASURED` / null). Trust is omitted and remaining category weights are renormalized when no external authority snapshot is connected.
- AI Search visibility stays blank unless live engines were actually queried.

This specification report details the ground-truth technical contracts required for **Phase 0** (scoring timing, external authority connection, and UI consistency) and **Phase 1** (unified relational persistence, Alembic migrations, MockSession elimination, and strict tenant isolation).

---

## 2. Canonical 8 Engine Categories vs Legacy 5-Pillar Formulas

### 2.1 The Canonical 8 Engine Categories

The authoritative scoring engine (`backend/app/domain/scoring/weights.py`, `backend/app/domain/scoring/engine.py`, `backend/app/domain/scoring/scoring_rubric_v5.json`) computes **eight discrete category scores**:

| Category ID | Canonical Name | Baseline Weight | Measurement Mode / Core Signals |
|---|---|---|---|
| `TECHNICAL_SEO` | Technical SEO | **15% (0.15)** | Deterministic AST & DOM crawl: HTTP status, canonicals, robots.txt (RFC 9309), sitemap 200s, TTFB latency (<500ms), 4xx/5xx errors, click depth <= 3. |
| `ON_PAGE_SEO` | On-Page SEO | **10% (0.10)** | HTML & Semantic DOM: H1 hierarchy, title & meta lengths, Open Graph cards, image alt text coverage, internal anchor distribution. |
| `CONTENT` | Content & Semantics | **15% (0.15)** | Natural language heuristics: topic depth, Flesch-Kincaid / Gunning-Fog readability, keyword cannibalization, proof-point density, entity grounding. |
| `GEO` | Generative Engine Optimization (GEO) | **15% (0.15)** | On-page answer extractability: top 200 words entity definition, pricing transparency, commercial Q&A extractability, direct definition clarity. |
| `AI_SEARCH` | AI Search Visibility | **15% (0.15)** | Live multi-engine querying (ChatGPT, Perplexity, Gemini, Claude): mention rate, share of voice, citation accuracy. **Stays blank/null when unmeasured.** |
| `SCHEMA` | Schema Architecture | **10% (0.10)** | AST structured data parser: JSON-LD validation, Schema.org class alignment, Organization sameAs, Rich Results eligibility. |
| `UX_CONVERSION` | UX & Conversion (CRO) | **10% (0.10)** | Behavioral heuristics + GA4 telemetry: 5-second value proposition clarity, CTA action verbs and contrast, form barrier count (<4 fields), mobile viewport. |
| `TRUST_AUTHORITY` | Trust & Authority Architecture | **10% (0.10)** | Verified on-page governance & connected external providers: HTTPS/TLS, legal entity schema, published privacy/terms, author bylines, NAP transparency, GSC/Ahrefs/Semrush backlink data. |

**Sum of Baseline Weights:** $0.15 + 0.10 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10 = 1.00$ (100%).

#### Intent-Adaptive Dynamic Rebalancing
In `backend/app/domain/scoring/weights.py`, baseline category weights are adjusted based on the audited business intent (`BusinessIntent`):
- `SAAS`: AI_SEARCH $\times 1.25$, GEO $\times 1.20$, UX_CONVERSION $\times 1.15$, TECHNICAL_SEO $\times 0.90$.
- `ECOMMERCE`: SCHEMA $\times 1.35$, UX_CONVERSION $\times 1.30$, TRUST_AUTHORITY $\times 1.20$, GEO $\times 0.85$.
- `LEAD_GENERATION`: UX_CONVERSION $\times 1.30$, TRUST_AUTHORITY $\times 1.25$, AI_SEARCH $\times 1.15$.
- `CONTENT_PUBLISHING`: CONTENT $\times 1.35$, GEO $\times 1.25$, TECHNICAL_SEO $\times 1.15$, UX_CONVERSION $\times 0.75$.
- `AGENCY`: TRUST_AUTHORITY $\times 1.30$, UX_CONVERSION $\times 1.20$, GEO $\times 1.15$.

**Normalization Formula:**
$$\text{AdjustedWeight}(c) = \frac{\text{BaselineWeight}(c) \times \text{Multiplier}(c)}{\sum_{k \in \text{ActiveCategories}} (\text{BaselineWeight}(k) \times \text{Multiplier}(k))}$$

#### Category Score Deduction & Diminishing Returns
- **Deduction Formula:** $\text{Deduction} = \text{BaseStep}[\text{occurrence\_index}]$
  - `CRITICAL`: $[25.0, 12.0, 8.0, 5.0]$ pts
  - `HIGH`: $[15.0, 9.0, 6.0, 4.0]$ pts
  - `MEDIUM`: $[8.0, 5.0, 3.0, 2.0]$ pts
  - `LOW`: $[3.0, 2.0, 1.0, 1.0]$ pts
  - `INFO`: $[0.0, 0.0, 0.0, 0.0]$ pts
- **Score Floor:** Clamped to $\text{clamp}(100 - \sum \text{Deductions}, 20.0, 100.0)$.
- **Confidence Gating:** Only `VERIFIED` and `HIGH_CONFIDENCE` (or legacy `CERTAIN` / `LIKELY`) findings deduct points. `LOW_CONFIDENCE`, `UNVERIFIED`, and `GUESSING` findings are routed exclusively to *Exploratory Hypotheses* and **deduct 0 points**.
- **Missing Connector Policy:**
  - `TRUST_AUTHORITY`: When `external_authority_connected=False`, category score is `None`, status is `NOT_MEASURED`, provenance is `CONNECTOR_UNAVAILABLE`, and its weight is omitted with the remaining active category weights renormalized to 1.0.
  - `AI_SEARCH`: When live engines were not queried, score is `None`, status is `NOT_MEASURED`, and weight is omitted with remaining active weights renormalized.

#### Three Honest Specialized Perspectives
`calculate_honest_scores` in `backend/app/domain/scoring/engine.py` generates three distinct composite perspectives:
1. **Google Discoverability View (`google_score`):**
   $$\text{GoogleScore} = \text{weighted\_mean}([(\text{Technical}, 0.40), (\text{OnPage}, 0.30), (\text{Schema}, 0.30)])$$
2. **Human Experience View (`human_score`):**
   $$\text{HumanScore} = \text{weighted\_mean}([(\text{UX/Conversion}, 0.50), (\text{Content}, 0.50)])$$
3. **AI Search Readiness View (`ai_readiness_score`):**
   $$\text{AIReadinessScore} = \text{weighted\_mean}([(\text{GEO}, 0.60), (\text{QuestionsSupportedPoints}, 0.40)])$$
   *(If question evaluations do not exist, falls back directly to `round(geo_score, 1)`).*

---

### 2.2 The Legacy 5-Pillar Formulas & Conflicting Syntheses

The legacy architecture previously attempted to aggregate results into five pillars (`scoring_rubric.py:95-158`):
1. **Pillar 1: Search Intelligence (Technical & On-Page SEO)** — 25%
2. **Pillar 2: AI Search Intelligence (GEO / AEO / LLMO)** — 25%
3. **Pillar 3: Experience Intelligence (SXO & Readability)** — 20%
4. **Pillar 4: Conversion Intelligence (CRO & Funnels)** — 20%
5. **Pillar 5: Trust Intelligence (On-Page E-E-A-T Architecture)** — 10%

#### Current Conflicting Syntheses Identified:
1. **`frontend/src/lib/pillarSynthesis.ts`:**
   - Synthesizes `seo` using: $0.45 \times \text{Tech} + 0.35 \times \text{OnPage} + 0.20 \times \text{Content}$.
   - Synthesizes `geo` using on-page extractability score, or falls back to category `GEO`.
   - Synthesizes `aeo` using the mean of `[schemaScore, extractabilityScore, botScore]`.
   - Synthesizes `cro` as `score: null` with a string headline ("GA4 key-event rate" or "Heuristic from crawled pages").
   - Synthesizes `competitors` as commercial bakeoff win percentage.
   - Maps legacy keys `search_intelligence`, `ai_search_intelligence`, `website_experience` (sxo), `conversion_intelligence`, `brand_entity_intelligence`.
2. **`frontend/src/report/models/scoreLedger.ts` (`REPORT_PILLARS`):**
   - Defines a 4-pillar composite: Technical (0.30), GEO (0.25), AEO/Live Citations (0.25), CRO (0.20).
3. **`frontend/src/components/Overview.tsx`:**
   - Renders 5 discipline cards (`seo`, `geo`, `aeo`, `cro`, `competitors`) derived from `synthesizePillars`, alongside the authoritative composite score from `buildDisplayedScore(report)`.
4. **`backend/app/domain/scoring/scoring_rubric.py`:**
   - Contains both the canonical 8 categories AND the deprecated `five_pillars` dictionary. `test_confidence_gating.py:12` asserts `len(rubric["five_pillars"]) == 5`.

#### Required Phase 0 Alignment:
- The frontend score cards and synthesis must directly present the **8 canonical engine categories** (or the clearly labeled 3 honest perspective views: Google Discoverability, Human Experience, AI Search Readiness).
- Eliminate divergent client-side weighting in `pillarSynthesis.ts`. The UI must read category scores directly from `report.scores.category_scores` and `report.honest_scores`.
- Retain the `five_pillars` key in `scoring_rubric.py` strictly as a deprecated schema alias so legacy assertions in `test_confidence_gating.py` continue to pass without regression.

---

## 3. Phase 0 Ground Truth Specification: Pipeline Scoring Timing & UI Consistency

### 3.1 Pipeline Execution Sequence in `AnalysisOrchestrator`

The pipeline orchestrator (`backend/app/orchestration/orchestrator.py`) executes `execute_analysis_pipeline`. To ensure complete evidence before score calculation, the execution sequence must be:

```
[1. Crawl & Ingestion]
         ↓
[2. Deterministic AST/DOM Analyzers & Evidence Graph]
         ↓
[3. 105-Agent Specialist Workforce (Kahn Waves 1-9)]
         ↓
[4. Post-DAG Analyzers (Canonical, Redirects, Schema, Headings, WCAG)]
         ↓
[5. Live AI Search Visibility & Citation Benchmark] (Step 13)
         ↓
[6. External Authority Attachment & Credential Synced Snapshots] (Step 13)
         ↓
[7. Multi-Source Causal Diagnostic Chains] (Step 13/14)
         ↓
[8. Finding Deduplication & Taxonomy Scope Assignment] (Step 14)
         ↓
[9. Scoring Engine Calculation (Category Scores & Honest Views)] (Step 15)
         ↓
[10. Remediation Planner, Autonomous Code Patch Pack, & 7/30/90 Roadmaps] (Step 16)
         ↓
[11. Executive Narrative Assembly, Temporal Digital Twin, & Manifest Seal]
```

### 3.2 Detailed Step-by-Step Contract for Phase 0

#### Step 1: External Authority Attachment & Live Search Before Scoring
- In `orchestrator.py` (lines 1393–1557):
  1. Live AI visibility check (`run_audit_visibility` and `ai_citation_tracker.track_buyer_queries`) runs first. If successful, `live_citation_score` is set to the measured citation percentage, and `visibility_measured = True`.
  2. External authority attachment runs next via `build_audit_attachment` (`app.connectors.authority.audit_bridge`).
  3. External domain findings (`attachment.get("domain_findings", [])`) are appended to `raw_findings` **before** deduplication.
  4. The flag `has_external_authority_connected` is set to `True` if:
     - Any coverage item in the report has `status == "CONNECTED"`.
     - Or report status is `"CONNECTED"` or `"PARTIALLY_MEASURED"`.
     - Or `len(attachment.get("domain_findings", [])) > 0`.
     - Otherwise `False`.

#### Step 2: Finding Deduplication & Taxonomy Scoping
- In Step 14 (lines 1559–1566):
  - `final_findings = FindingDeduplicator.deduplicate(raw_findings)`
  - Each finding receives an authoritative scope: `PAGE_VERIFIED`, `SAMPLE_VERIFIED`, or `SITE_INFERRED` via `assign_evidence_scope`.
  - Stored in `blackboard.findings = final_findings`.

#### Step 3: Scoring Engine (`calculate_scores` & `calculate_honest_scores`)
- In Step 15 (lines 1581–1627):
  - `overall_scores = self.scoring_engine.calculate_scores(...)` is invoked with:
    - `findings=final_findings` (includes external findings)
    - `external_authority_connected=has_external_authority_connected`
    - `live_citation_score=live_citation_score`
  - `honest_scores = self.scoring_engine.calculate_honest_scores(...)` is invoked with the exact same parameters:
    - `findings=final_findings`
    - `external_authority_connected=has_external_authority_connected`
    - `live_citation_score=live_citation_score`
    - `geo_readiness=geo_readiness`
  - **Critical Defect Remediation in DAG Runner:**
    - In `orchestrator.py:2985` (`node_honest_scoring`), the manual DAG step must also pass `external_authority_connected` and call both `calculate_scores` and `calculate_honest_scores`.

#### Step 4: 7/30/90 Roadmap Timing
- In Step 16 (lines 1645–1686):
  - `self.roadmap_builder.build_roadmap(final_findings, blackboard.executive_narrative)` produces `r7, r30, r90`.
  - `self.roadmap_builder.build_top_10_actions(final_findings, blackboard.business_profile, overall_scores, ...)` produces the top 10 action plan.
  - Because `final_findings` already contains the deduplicated external authority findings and live AI visibility gaps, the 7/30/90 roadmap and top 10 actions **accurately reflect external findings and citations**.

---

## 4. Phase 1 Ground Truth Specification: Unified Enterprise Persistence & Strict Multi-Tenancy

### 4.1 Fragmentation Audit of Existing Storage Stores

| Store / File | Owning Module | Current Purpose | Proposed Unified State |
|---|---|---|---|
| `data/dristik.db` | `backend/app/identity/store.py` (`AUTH_DATABASE_PATH`) | Users, sessions, organizations, password resets, contacts, invitations. | Consolidated into unified PostgreSQL/SQLite schema. |
| `data/dristik_audits.db` | `backend/app/db/repository.py` (`AUDIT_DATABASE_PATH`) | Audits, checkpoints, crawl pages, evidence, claims, findings, telemetry. | Consolidated into unified PostgreSQL/SQLite schema. |
| `data/external_authority.db` | `backend/app/connectors/authority/store.py` (`EXTERNAL_AUTHORITY_DB_PATH`) | Provider credentials, OAuth tokens (Fernet encrypted), sync jobs, external snapshots. | Consolidated into unified PostgreSQL/SQLite schema. |
| `data/geo_aeo_pipeline.db` | `backend/app/geo/pipeline_store.py` | GEO/AEO prompt trends and historical query matrices. | Consolidated into unified PostgreSQL/SQLite schema. |
| Memory / `MockSession` | `backend/app/db/session.py` | Stubs queries with `query()->self, first()->None, all()->[]`. | **Completely eliminated.** Fails fast on connection error. |

### 4.2 Unified Relational Persistence Schema (PostgreSQL & SQLite Compatible)

`backend/app/db/enterprise_schema.py` defines the canonical 8-table enterprise relational model. The schema must be declared via SQLAlchemy models in `backend/app/db/models/` inheriting from `Base` (`backend/app/db/base.py`):

```
                   organizations
                   (id, name, slug, plan, sso_enabled, ...)
                         │
                         ├────────────────────────────────────────┐
                         ▼                                        ▼
                     workspaces                         enterprise_audit_logs
       (id, org_id, name, slug, created_at)        (id, org_id, user_id, action, ...)
                         │
                         ▼
                      domains
 (id, workspace_id, hostname, site_type, max_pages, ...)
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   audit_runs                        ai_citations
(id, domain_id, status, ...   (id, domain_id, query, engine, is_cited, ...)
 overall_score, started_at)
        │
        ├─────────────────────────────────┐
        ▼                                 ▼
  evidence_nodes                       findings
(id, audit_run_id, url,        (id, audit_run_id, code, category,
 content_hash, storage_uri)     severity, title, suggested_patch, ...)
```

#### Core Schema Definitions:
1. **`organizations`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `name VARCHAR(255) NOT NULL`, `slug VARCHAR(100) NOT NULL UNIQUE`, `plan VARCHAR(50) DEFAULT 'enterprise'`
   - `sso_enabled BOOLEAN DEFAULT FALSE`, `sso_provider VARCHAR(50)`, `sso_metadata_url TEXT`
   - `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`
2. **`workspaces`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `org_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE`
   - `name VARCHAR(255) NOT NULL`, `slug VARCHAR(100) NOT NULL`
   - `UNIQUE (org_id, slug)`
3. **`domains`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
   - `hostname VARCHAR(255) NOT NULL`, `default_scheme VARCHAR(10) DEFAULT 'https'`
   - `site_type VARCHAR(50) DEFAULT 'b2b_saas'`, `crawl_frequency VARCHAR(50) DEFAULT 'weekly'`, `max_pages INT DEFAULT 500`
   - `is_active BOOLEAN DEFAULT TRUE`, `created_at TIMESTAMPTZ`
4. **`audit_runs`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `domain_id VARCHAR(64) NOT NULL REFERENCES domains(id) ON DELETE CASCADE`
   - `triggered_by VARCHAR(64)`, `status VARCHAR(50) DEFAULT 'queued'`, `stage VARCHAR(50) DEFAULT 'discovery'`
   - `pages_crawled INT DEFAULT 0`, `overall_score INT`, `confidence_score INT`, `evidence_coverage INT`
   - `error_message TEXT`, `started_at TIMESTAMPTZ`, `completed_at TIMESTAMPTZ`, `created_at TIMESTAMPTZ`
5. **`evidence_nodes`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `audit_run_id VARCHAR(64) NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE`
   - `url TEXT NOT NULL`, `node_type VARCHAR(50) NOT NULL`, `content_hash VARCHAR(64) NOT NULL`
   - `storage_uri TEXT NOT NULL`, `metadata JSONB / TEXT NOT NULL DEFAULT '{}'`, `created_at TIMESTAMPTZ`
6. **`findings`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `audit_run_id VARCHAR(64) NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE`
   - `code VARCHAR(50) NOT NULL`, `category VARCHAR(50) NOT NULL`, `severity VARCHAR(20) NOT NULL`
   - `title VARCHAR(255) NOT NULL`, `description TEXT NOT NULL`, `impact_explanation TEXT NOT NULL`
   - `remediation_advice TEXT NOT NULL`, `suggested_patch JSONB / TEXT`, `jira_issue_key VARCHAR(50)`, `github_pr_url TEXT`
   - `status VARCHAR(50) DEFAULT 'open'`, `created_at TIMESTAMPTZ`
7. **`ai_citations`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `domain_id VARCHAR(64) NOT NULL REFERENCES domains(id) ON DELETE CASCADE`
   - `query TEXT NOT NULL`, `engine VARCHAR(50) NOT NULL`, `is_cited BOOLEAN DEFAULT FALSE`
   - `citation_rank INT`, `cited_url TEXT`, `extracted_snippet TEXT`, `competitor_citations JSONB / TEXT DEFAULT '[]'`
   - `queried_at TIMESTAMPTZ`
8. **`enterprise_audit_logs`**:
   - `id VARCHAR(64) PRIMARY KEY`
   - `org_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE`
   - `user_id VARCHAR(64)`, `action VARCHAR(100) NOT NULL`, `resource_type VARCHAR(50) NOT NULL`, `resource_id VARCHAR(100)`
   - `ip_address VARCHAR(45)`, `user_agent TEXT`, `payload JSONB / TEXT`, `created_at TIMESTAMPTZ`

### 4.3 Database Configuration & Migration Strategy (SQLAlchemy + Alembic)

1. **Unified `DATABASE_URL`:**
   - In `backend/app/core/config.py`: Add `DATABASE_URL: str = Field(default="postgresql+psycopg2://dristik:dristik@localhost:5432/dristik")` with fallback to `sqlite:///data/dristik.db` for local test harnesses.
   - In `backend/app/db/session.py`: Default `DATABASE_URL` to settings. Create engine with SQLite thread check flags only when `sqlite` is in URL.
2. **Elimination of `MockSession`:**
   - Delete lines 28–74 in `backend/app/db/session.py`.
   - Replace with strict connection handling: If SQLAlchemy is not available or database connection fails, raise a descriptive runtime error immediately (*Fail Fast*).
3. **Alembic Migrations:**
   - Update `backend/alembic.ini` to read `sqlalchemy.url` dynamically or point to `DATABASE_URL`.
   - Update `backend/migrations/env.py` to import `Base` from `app.db.base` and all models from `app.db.models`.
   - Generate initial migration version in `backend/migrations/versions/` representing the unified enterprise schema.

### 4.4 Elimination of `org_default` and `ws_default` & Strict Tenant Isolation Rules

#### Codebase Inventory of `org_default` / `ws_default` Fallbacks:
1. `backend/app/orchestration/orchestrator.py`:
   - Line 99: `create_run(..., org_id: str = "org_default")`
   - Line 1537: `project_id=getattr(run, "org_id", None) or "org_default"`
2. `backend/app/domain/models.py`:
   - Line 125–126 (`Integration`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
   - Line 2609–2610 (`ExecutiveReport`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
   - Line 2716–2717 (`AnalysisRequest`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
   - Line 2733–2734 (`AnalysisRun`): `org_id: str = "org_default"`, `workspace_id: str = "ws_default"`
3. `backend/app/identity/tenancy/manager.py`:
   - Lines 20–38: Hardcoded default organization `org_default` and default workspace `ws_default`.
4. `backend/app/api/routes/integrations/google.py` & `connectors.py`:
   - Lines 43, 175, 241, 278: Fallbacks defaulting to `org_default` or `ws_default`.
5. `backend/app/connectors/authority/audit_bridge.py`:
   - Fallback if project_id missing.

#### Strict Tenant Isolation Rules:
1. **Mandatory Tenant Context:**
   - Every `AnalysisRequest`, `AnalysisRun`, `ExecutiveReport`, and `Integration` must have an explicit, non-empty `org_id` and `workspace_id`.
   - If an incoming API request or background job lacks a valid tenant context, it must **fail immediately with `HTTP 403 Forbidden`** (or `401 Unauthorized` if unauthenticated). It must never fall back to `org_default`.
2. **Cross-Tenant Access Rejection:**
   - In `backend/app/identity/access.py:require_analysis`: If caller `user.org_id != run.org_id`, return `404 Not Found` (to prevent ID enumeration) or `403 Forbidden`.
   - In `backend/app/api/routes/platform/workspaces.py`: Enforce `_owned_workspace` and `_owned_domain` verifying `workspace.org_id == user.org_id`.
3. **Audit Bridge Tenant Enforcement:**
   - In `audit_bridge.py:build_audit_attachment`: If `project_id` (org_id) is empty, do not run authority queries; return an explicit `NOT_CONFIGURED` / empty payload.

---

## 5. Non-Negotiable Acceptance Criteria & Policies

Derived from `docs/ENTERPRISE_AUDIT_INTEGRITY_REMEDIATION.md` and `ORIGINAL_REQUEST.md`:

| # | Policy / Criterion | Ground Truth Rule | Verification Target |
|---|---|---|---|
| AC-1 | **Complete Evidence Scoring** | On a completed audit with external authority data connected, category scores and the 7/30/90 roadmap must reflect external findings. | External findings present in `final_findings`, `report.scores`, and `r7/r30/r90`. |
| AC-2 | **Dynamic Authority Flag** | The honest score pass (`calculate_honest_scores`) dynamically receives `external_authority_connected=True` when provider snapshots exist; otherwise `False`. | `test_scoring_unmeasured_authority.py` passes; Trust score is null/`NOT_MEASURED` when False, active when True. |
| AC-3 | **UI Scorecard Alignment** | Overview tab, Rubric modal, and report header display consistent category scores derived from the same 8 canonical weights. | No divergent calculations in `pillarSynthesis.ts` vs backend `weights.py`. |
| AC-4 | **Unified DB Configuration** | Database configuration defaults to a unified `DATABASE_URL` (PostgreSQL compatible, retaining SQLite for local test harnesses). | `settings.DATABASE_URL` exists and connects cleanly. |
| AC-5 | **MockSession Elimination** | Silent `MockSession` in `session.py` is removed; connection failures fail fast with meaningful error diagnostics. | `session.py` contains no `MockSession`; raises Exception if DB unreachable. |
| AC-6 | **Strict Tenant Isolation** | Queries and background jobs without a valid tenant context fail with `403 Forbidden` / error rather than falling back to `org_default`. | No `org_default` fallback anywhere in core models or routes. |
| AC-7 | **Zero Fabricated Metrics** | Missing, timed-out, unauthorized, or malformed provider data must not be replaced by constants, canned examples, or optimistic defaults. | Metric provenance state is `UNAVAILABLE` or `NOT_CONFIGURED`. |
| AC-8 | **Diminishing Returns Math** | Repeating issues hit at diminishing rates: Critical 25/12/8/5, High 15/9/6/4, Medium 8/5/3/2, Low 3/2/1/1. Score floor 20.0. | Verified via `test_scoring_v5.py`. |
| AC-9 | **Empirical AI Visibility** | Live citation score requires real engine execution. Simulated results must be labeled `SIMULATION_ONLY` and cannot populate live citation fields. | `honest.ai_visibility_score` is null if status is not `MEASURED`. |
| AC-10 | **Test Suite Non-Regression** | All 2,248 existing tests pass with `pytest backend/` + new unit tests for score timing and tenant isolation. | Clean pytest execution with zero regressions. |

---

## 6. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Scoring | Intent-Adaptive Baseline Weights | 8 canonical categories with dynamic multipliers based on business intent (SaaS, Ecommerce, LeadGen, Publishing, Agency). | `BusinessIntent`, active category list | Normalized dictionary of weights summing to 1.0 | Defaults to baseline weights if intent unknown | `backend/app/domain/scoring/weights.py` |
| 2 | Scoring | Diminishing Returns Deductions | Non-linear penalties for repeated errors within the same taxonomy to prevent score collapse. | Finding severity, occurrence count | Point deduction float | Clamps total category score to [20.0, 100.0] | `backend/app/domain/scoring/scoring_rubric.py:159` |
| 3 | Scoring | Confidence Gating Architecture | Barring low-confidence / GUESSING findings from reducing scores or appearing as executive blockers. | `Finding.confidence_rubric`, `EpistemicConfidence` | Point deduction or 0 pts; exploratory routing | Caps deduction at 0 for GUESSING claims | `backend/app/domain/enums.py:101-186`, `test_confidence_gating.py` |
| 4 | Scoring | Honest Specialized Views | Composite views for Google (40/30/30), Human (50/50), and AI Readiness (60/40). | `cat_scores`, `geo_readiness`, `commercial_evals` | `HonestScores` object | Unmeasured inputs left out; weights scaled | `backend/app/domain/scoring/engine.py:1015` |
| 5 | Orchestration | Step 13 External & Visibility Collection | Evaluates live citations and attaches external authority snapshots before deduplication and scoring. | Domain, eval pages, provider credentials | `attachment["report"]`, `live_citation_score` | Fails open with placeholder report; crawl continues | `backend/app/orchestration/orchestrator.py:1393` |
| 6 | Orchestration | Step 14 Scope Classification | Assigns `PAGE_VERIFIED`, `SAMPLE_VERIFIED`, or `SITE_INFERRED` to each finding. | Finding, crawled sample size | Scoped Finding object | Defaults to `PAGE_VERIFIED` or `SAMPLE_VERIFIED` | `backend/app/domain/evidence/taxonomy.py` |
| 7 | Orchestration | Step 16 Roadmap Timing | Generates 7/30/90-day roadmaps and top-10 actions using findings that include external authority. | Final deduplicated findings, executive narrative | `r7`, `r30`, `r90`, `top_10_plan` | Empty lists if findings are empty | `backend/app/orchestration/orchestrator.py:1675` |
| 8 | Persistence | Enterprise Relational Schema | 8 relational tables for orgs, workspaces, domains, audit_runs, evidence, findings, citations, and audit logs. | PostgreSQL DDL / SQLite DDL | Relational database tables | Fails if database unreachable | `backend/app/db/enterprise_schema.py` |
| 9 | Persistence | MockSession Fallback | Silent fallback in session.py that stubs query methods when SQLAlchemy import fails. | None (import error trigger) | MockSession instance with no-op methods | Masks real DB errors | `backend/app/db/session.py:28-74` |
| 10 | Security / Auth | Tenant Isolation & Access Scoping | Verifies user ownership before returning stored audits or modifying workspace resources. | `analysis_id`, `UserIdentity` | `AnalysisRun` object or 404/403 | Returns 404/403 if org_id does not match | `backend/app/identity/access.py:10` |
| 11 | Tenancy | Pervasive `org_default` Fallback | Legacy fallback defaulting org_id to `org_default` when not supplied. | Missing org_id | String `"org_default"` | Mixes snapshots across tenants | `models.py`, `orchestrator.py`, `connectors/` |
| 12 | Frontend | Displayed Audit Score Ledger | Calculates one authoritative composite for header and PDF; handles partial coverage dynamically. | `ExecutiveReport` | `AuthoritativeScore` with rows and composite | Leaves out unmeasured pillars, scales remaining | `frontend/src/report/models/scoreLedger.ts` |
| 13 | Frontend | Client-Side Pillar Synthesis | Synthesizes 5 legacy pillars from category scores, extractability, and bot permissions. | `ExecutiveReport` | `WebsiteIntelligenceRollup` | Yields null scores for CRO / missing signals | `frontend/src/lib/pillarSynthesis.ts` |

---

## 7. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---|---|---|
| 1 | Trust Category Scoring | `external_authority_connected=False` | Trust category score is `None`, status is `NOT_MEASURED`, provenance is `CONNECTOR_UNAVAILABLE`, weight is 0.0, and overall score is calculated by renormalizing remaining 7 categories to 1.0. |
| 2 | Trust Category Scoring | `external_authority_connected=True` with high-severity backlink penalty | Trust score calculates normally (deducts points from 100), status is `MEASURED`, weight is > 0.0. |
| 3 | AI Visibility Scoring | Live multi-engine run yields 0% citations across 10 queries | Score is `0.0` (numeric zero), status is `MEASURED`. Zero is treated as a real empirical measurement, not null/unmeasured! |
| 4 | AI Visibility Scoring | Live multi-engine monitor was not run (no API keys) | Score is `None`, status is `NOT_MEASURED`. Score remains blank; does not penalize overall score. |
| 5 | Confidence Gating | Finding has severity `CRITICAL` but confidence `0.4` and rubric `GUESSING` | Finding deduction is capped at 0 pts; finding is excluded from `what_is_holding_it_back` and routed to `exploratory_hypotheses`. |
| 6 | Score Floor | Severe stack of 10+ critical defects in Technical SEO | Calculated deductions exceed 150 points. Final category score clamps cleanly at floor `20.0` (never negative or zero). |
| 7 | Tenant Access Control | User from `org_1` requests analysis ID belonging to `org_2` | `require_analysis` raises `HTTPException(404, "Analysis run not found")` to prevent ID enumeration. |
| 8 | Tenant Inactive User | Inactive user (`is_active=False`) requests run belonging to their own `org_1` | `Authorizer.can_perform` and `can_access_org` return False; `require_analysis` raises `HTTPException(403)`. |
| 9 | Cross-Tenant Audit Bridge | Analysis run initiated without tenant context | Prior behavior fell back to `org_default` snapshots. Target behavior raises 403 Forbidden or returns empty attachment with error. |
| 10 | DB Disconnection | PostgreSQL server unreachable upon startup | If MockSession is active: silently returns empty queries and fails silently later. Target behavior: fails fast immediately with descriptive database connection diagnostic. |
| 11 | Partial Coverage Blending | Report has Technical SEO (80) and GEO (70), but Live Citations and CRO are unmeasured | `buildAuthoritativeScore` omits unmeasured pillars, scales Technical (0.30/0.55 = 54.5%) and GEO (0.25/0.55 = 45.5%), yielding composite 75.5 with label "Partial-coverage composite". |
| 12 | Intent Multiplier Normalization | Intent is SAAS with only 6 of 8 categories active | `compute_intent_adjusted_weights` loops over active categories, multiplies baseline weights, sums adjusted weights, and divides each by total so sum is exactly 1.0. |

---

## 8. Verification Targets & Architectural Guidance for Implementation

1. **For Phase 0 Implementation:**
   - Modify `orchestrator.py` to ensure `external_authority_connected` is dynamically passed into both `calculate_scores` and `calculate_honest_scores` at Step 15 and in `node_honest_scoring`.
   - Update `frontend/src/lib/pillarSynthesis.ts` and `frontend/src/components/Overview.tsx` to display the 8 canonical categories (or the 3 honest perspective views) without conflicting local synthesis.
   - Retain `five_pillars` in `scoring_rubric.py` as a backward-compatibility stub for `test_confidence_gating.py`.
2. **For Phase 1 Implementation:**
   - Remove `MockSession` completely from `backend/app/db/session.py`.
   - Implement declarative SQLAlchemy models in `backend/app/db/models/` matching the 8 enterprise schema tables with foreign key constraints.
   - Configure Alembic in `backend/migrations/` and generate initial version `001_enterprise_schema.py`.
   - Remove `org_default` and `ws_default` fallbacks from `models.py`, `orchestrator.py`, `connectors/`, and `manager.py`. Require valid `org_id` and `workspace_id`, returning `HTTP 403 Forbidden` if missing or unauthorized.
