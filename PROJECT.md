# Project: Dristik AI — Phase 0 & Phase 1 Architecture and Execution Plan

## Architecture
Dristik AI is an enterprise AI-search, GEO, and technical audit platform.
- **Analysis Pipeline**: Multi-stage pipeline executing crawling, DOM AST extraction, security headers, schema validation, and specialized workforce analysis waves, followed by post-DAG analyzers, live search visibility, external authority attachment, deterministic scoring, and tactical roadmap synthesis.
- **Deterministic Scoring Engine**: 8 canonical engine categories (`TECHNICAL_SEO`, `ON_PAGE_SEO`, `CONTENT`, `GEO`, `AI_SEARCH`, `SCHEMA`, `UX_CONVERSION`, `TRUST_AUTHORITY`) weighted at 15/10/15/15/15/10/10/10 with dynamic intent multipliers summing to 1.0. Honest scoring computes transparent 3-perspective scores (Google, AI Search, Human).
- **Enterprise Persistence**: Unified PostgreSQL-compatible relational model (supporting SQLite for local test environments) configured via `DATABASE_URL` in `Settings` and managed via SQLAlchemy and Alembic migrations, consolidating legacy fragmented databases (`dristik.db`, `dristik_audits.db`, `external_authority.db`, `geo_aeo_pipeline.db`). Fail-fast engine connectivity replacing silent `MockSession`.
- **Strict Multi-Tenancy**: Mandatory `org_id` and `workspace_id` tenant scoping across all domain models, repositories, and connectors. Rejection of unauthenticated or tenant-less requests with `403 Forbidden` / `401 Unauthorized`, eliminating insecure fallback to `"org_default"`.

## Feature Inventory
Every feature identified during the Survey phase mapped to its implementation milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Scoring Pipeline Re-ordering & SSE Event Timing | Move scoring stage emission (`AnalysisStage.SCORING`) from premature line 1276 to Step 15 where deterministic scoring begins after external authority and live search visibility checks. | M1 | ORIGINAL_REQUEST §R1 |
| F02 | External Authority Flag Detection | Fix dictionary key mismatch in `orchestrator.py` (`connection_status == "CONNECTED"` / `data_state`) so `has_external_authority_connected` accurately reflects provider snapshots. | M1 | ORIGINAL_REQUEST §R1 |
| F03 | Honest Scoring & DAG Node Parity | Ensure `calculate_honest_scores` receives `external_authority_connected=True` when snapshots exist, and update DAG runner `node_honest_scoring` at line 2985 to invoke honest scoring with full parameters. | M1 | ORIGINAL_REQUEST §R1 |
| F04 | Roadmap Inclusion of External Authority Findings | Ensure 7/30/90 roadmap generation evaluates over `final_findings` including external authority findings, and add regression tests. | M1 | ORIGINAL_REQUEST §R1 |
| F05 | Frontend Pillar Synthesis Alignment | Re-align `frontend/src/lib/pillarSynthesis.ts` and `Overview.tsx` to directly consume canonical 8 category scores from `report.scores.category_scores`, removing ad-hoc 45/35/20 blend and hardcoded nulls. | M1 | ORIGINAL_REQUEST §R1 |
| F06 | Scoring Rubric Modal Reconcilement | Align `frontend/src/components/ScoringRubricModal.tsx` perspective formulas with backend `calculate_honest_scores`; retain `five_pillars` alias in `scoring_rubric.py` for backward-compatibility. | M1 | ORIGINAL_REQUEST §R1 |
| F07 | MockSession Elimination & Fail-Fast Connectivity | Delete silent `MockSession` fallback in `backend/app/db/session.py:28-74`; implement fail-fast engine connection diagnostics. | M2 | ORIGINAL_REQUEST §R2 |
| F08 | Database Configuration & DATABASE_URL | Add `DATABASE_URL` to `Settings` in `backend/app/core/config.py` defaulting to PostgreSQL compatible URI (retaining SQLite for local test harnesses). | M2 | ORIGINAL_REQUEST §R2 |
| F09 | Unified Enterprise Relational Schema & Alembic Migrations | Consolidate 4 SQLite schemas into unified SQLAlchemy models based on `enterprise_schema.py`; configure Alembic migration version. | M2 | ORIGINAL_REQUEST §R2 |
| F10 | Circular Import Resolution in Scoring Explanations | Fix circular import in `backend/app/domain/scoring/score_explanations.py:6` and register compatibility shims in `backend/conftest.py`. | M2 | ORIGINAL_REQUEST §R3 |
| F11 | Elimination of org_default and ws_default | Remove hardcoded `"org_default"` and `"ws_default"` defaults in `models.py`, `orchestrator.py`, and repository methods. | M3 | ORIGINAL_REQUEST §R2 |
| F12 | Strict Tenant Isolation & 403 Forbidden Enforcement | Require tenant context on all audit runs, reports, and credential stores; return `403 Forbidden` on missing or cross-tenant access. | M3 | ORIGINAL_REQUEST §R2 |
| F13 | External Authority Bridge Tenant Scoping | Eliminate `"org_default"` fallback in `orchestrator.py:1537` external authority attachment. | M3 | ORIGINAL_REQUEST §R2 |
| F14 | Regression & E2E Test Suite Pass | Verify all 2,248 existing tests pass; add unit tests for score timing, honest score flag, and tenant isolation. | M4 | ORIGINAL_REQUEST §R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Phase 0: Pipeline Scoring Timing & UI Consistency | F01, F02, F03, F04, F05, F06 | None | DONE |
| M2 | Phase 1: Unified Enterprise Persistence & MockSession Elimination | F07, F08, F09, F10 | None | DONE |
| M3 | Phase 1: Strict Multi-Tenancy Isolation & Tenant Scoping | F11, F12, F13 | M2 | IN_PROGRESS |
| M4 | Final Verification, Regression & E2E Testing | F14 | M1, M2, M3 | PLANNED |

## Interface Contracts
### Pipeline Orchestrator ↔ Deterministic Scoring Engine
- `calculate_scores(findings, business_profile, external_authority_connected, live_citation_score, ...)` -> `CategoryScores`
  - Invariant: `findings` must include deduplicated specialist findings AND external authority domain findings.
  - Invariant: `external_authority_connected` is `True` iff connected provider snapshots exist in authority store.
- `calculate_honest_scores(..., external_authority_connected, ...)` -> `HonestScores`
  - Returns honest 3-perspective scores (`google_score`, `ai_search_score`, `human_score`).

### Database Session & Repository ↔ Domain Services
- `get_db() -> Generator[Session, None, None]`
  - Invariant: Raises `DatabaseConnectionError` immediately if engine connectivity fails. Never returns `MockSession`.
- `AuditRepository.list_runs(org_id: str, workspace_id: Optional[str])`
  - Invariant: `org_id` is mandatory non-empty string. Rejects empty/None `org_id` with `ValueError` or `Forbidden`.

### Tenant Context ↔ HTTP Endpoints
- `require_org_context(user, org_id)`
  - Invariant: If request lacks authenticated user or user lacks access to `org_id`, returns `403 Forbidden` (or `401 Unauthorized` if unauthenticated).

## Code Layout
- `backend/app/orchestration/orchestrator.py`: Pipeline execution flow, node status events, scoring sequence.
- `backend/app/domain/scoring/`:
  - `engine.py`: Canonical 8-category scoring and honest scoring logic.
  - `weights.py`: Canonical weights (15/10/15/15/15/10/10/10) and intent multipliers.
  - `scoring_rubric.py`: Scoring rubric definitions.
  - `score_explanations.py`: Score explanation models and dimensions.
- `backend/app/db/`:
  - `session.py`: Database engine and session lifecycle.
  - `enterprise_schema.py`: Target unified enterprise schema.
  - `models/`: SQLAlchemy relational models.
- `backend/app/core/config.py`: Application settings (`DATABASE_URL`).
- `backend/app/domain/models.py`: Domain entity models (tenant scoping).
- `backend/app/connectors/authority/`: External authority provider services, store, and audit bridge.
- `backend/tests/`: Pytest suites and conftest setup.
- `frontend/src/`:
  - `lib/pillarSynthesis.ts`: Frontend score aggregation.
  - `components/ScoringRubricModal.tsx`: Scoring rubric modal UI.
  - `components/Overview.tsx`: Audit overview tab.
