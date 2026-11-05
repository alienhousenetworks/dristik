# Original User Request

## Initial Request — 2026-10-31T16:27:46Z

Execute Phase 0 (Pipeline Scoring Timing & UI Consistency) and Phase 1 (Unified Enterprise Persistence & Strict Multi-Tenancy Isolation) for the Dristik AI platform.

Working directory: /Users/sayantande/Downloads/dristik-main
Integrity mode: development

## Requirements

### R1. Pipeline Scoring Timing & UI Consistency (Phase 0)
Ensure audit scores, roadmaps, and UI scorecards reflect complete evidence:
- Re-order scoring execution in the analysis pipeline so category scores, honest scores, and the 7/30/90 roadmap evaluate after external authority attachments and live search visibility checks complete.
- Ensure the `external_authority_connected` flag accurately reflects live integration status rather than hardcoding `False`.
- Align frontend score synthesis (`frontend/src/lib/pillarSynthesis.ts` and `ScoringRubricModal.tsx`) directly with the 8 canonical engine categories, eliminating conflicting legacy 5-pillar formulas.

### R2. Unified Enterprise Persistence & Tenant Scoping (Phase 1)
Consolidate fragmented data storage into a production-grade relational model:
- Replace fragmented SQLite stores (`dristik.db`, `dristik_audits.db`, `external_authority.db`) with a unified PostgreSQL-compatible schema managed via SQLAlchemy and Alembic migrations.
- Remove the silent `MockSession` fallback in `backend/app/db/session.py`.
- Enforce strict `org_id` and `workspace_id` tenant scoping across all audit runs, reports, and credential stores, completely removing the fallback to `org_default`.

### R3. Verification & Non-Regression
- Maintain backward compatibility and verify that existing test suites pass.
- Add regression tests verifying that score calculations run after external authority attachment and that cross-tenant access is blocked.

## Verification Resources
- Test suite: `pytest` in `backend/` (2,248 existing tests).
- Ground truth documentation: `DRISTIK_WORKING_FLOW_AGENTS_GAPS.md` and `docs/ENTERPRISE_AUDIT_INTEGRITY_REMEDIATION.md`.

## Acceptance Criteria

### Scoring & Integrity
- [ ] On a completed audit with external authority data connected, category scores and the 7/30/90 roadmap reflect external findings.
- [ ] The honest score pass (`calculate_honest_scores`) dynamically receives `external_authority_connected=True` when provider snapshots exist.
- [ ] The Overview tab, Rubric modal, and report header display consistent category scores derived from the same canonical weights.

### Persistence & Tenant Isolation
- [ ] Database configuration defaults to a unified `DATABASE_URL` (PostgreSQL compatible, retaining SQLite for local test harnesses).
- [ ] Silent `MockSession` in `session.py` is removed; connection failures fail fast with meaningful error diagnostics.
- [ ] Queries and background jobs without a valid tenant context fail with `403 Forbidden` / error rather than falling back to `org_default`.

### Test Suite Execution
- [ ] All 2,248 existing tests pass with `pytest backend/`.
- [ ] New unit tests pass for:
  1. Score timing sequence and honest score flag verification.
  2. Multi-tenant isolation ensuring unauthorized tenant access is rejected.
