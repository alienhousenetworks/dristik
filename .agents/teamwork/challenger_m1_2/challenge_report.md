# Empirical Challenge Report — Milestone M1

## Challenge Summary

**Overall risk assessment**: LOW

The Milestone M1 implementation in `frontend/src/lib/pillarSynthesis.ts` and `frontend/src/components/ScoringRubricModal.tsx` successfully reconciles the frontend scoring architecture with the deterministic 8-category scoring engine in the backend. All 8 canonical categories are accurately exposed, CRO cleanly reflects `UX_CONVERSION` scores and health statuses (eliminating the legacy hardcoded null), and edge cases (including score 0, negative values, missing categories, null honest perspectives, and GA4 telemetry) are handled safely and deterministically.

---

## Verdict

**VERDICT: APPROVE**

Empirical verification confirms that all acceptance criteria for Milestone M1 (Pipeline Scoring Timing & UI Consistency) are satisfied with zero regressions and clean builds.

---

## Challenges & Empirical Findings

### 1. Challenge: Zero Score Erasure & Falsy Fallback
- **Assumption challenged**: In JavaScript/TypeScript, expressions like `cat.score || null` or `score ? getGrade(score) : '—'` erroneously convert valid `0` scores to falsy values, causing audits with 0 points to appear as "unmeasured" or `null`.
- **Attack scenario**: Pass an executive report where every canonical category in `report.scores.category_scores` has `{ score: 0 }`.
- **Empirical result**: **PASS**.
  - `techScore`, `onPageScore`, `contentScore`, `geoScore`, `aiSearchScore`, `schemaScore`, `uxScore`, and `trustScore` all use `score != null ? Math.round(score) : null`.
  - In JavaScript, `0 != null` evaluates to `true`.
  - All categories report `score: 0`, `grade: 'F'`, `health: 'POOR'`.
  - `cro.headline` correctly displays `'Conversion & UX Friction Detected'` rather than `'Conversion experience unmeasured'`.

### 2. Challenge: CRO Score & Health State Parity
- **Assumption challenged**: CRO was previously hardcoded to `score: null, grade: '—', health: 'POOR'`. The new implementation must reliably map `UX_CONVERSION` to `croPillar` while preserving GA4 first-party telemetry when present.
- **Attack scenarios**:
  1. `UX_CONVERSION` score = 85 (High): returns `score: 85`, `grade: 'B'`, `health: 'GOOD'`, headline `'Low Friction & Clear Value Proposition'`.
  2. `UX_CONVERSION` score = 42 (Low): returns `score: 42`, `grade: 'F'`, `health: 'POOR'`, headline `'Conversion & UX Friction Detected'`.
  3. `UX_CONVERSION` omitted: returns `score: null`, `grade: '—'`, `health: 'POOR'`, headline `'Conversion experience unmeasured'`.
  4. GA4 active with `state: 'MEASURED'`: headline reflects `GA4 key-event rate X%` while retaining the audited score.
  5. Backward compatibility: `rollup.conversion_intelligence` accurately mirrors `rollup.cro`.
- **Empirical result**: **PASS**. All 5 scenarios executed and passed with exact expected outputs.

### 3. Challenge: 8 Canonical Categories Exposure & Schema Integrity
- **Assumption challenged**: The rollup object must expose all 8 canonical categories required by R1 / F05, with metadata matching backend categories.
- **Attack scenario**: Inspect properties on `rollup` when report is populated vs when report is `null` or `undefined`.
- **Empirical result**: **PASS**.
  - All 8 categories are exposed:
    1. `technical_seo` (id: `'seo'`, shortName: `'SEO'`, weight: 15%)
    2. `on_page_seo` (id: `'on_page_seo'`, shortName: `'On-Page'`, weight: 10%)
    3. `content` (id: `'content'`, shortName: `'Content'`, weight: 15%)
    4. `geo` (id: `'geo'`, shortName: `'GEO'`, weight: 15%)
    5. `ai_search` (id: `'ai_search'`, shortName: `'AI Search'`, weight: 15%)
    6. `schema` (id: `'aeo'`, shortName: `'AEO'`, weight: 10%)
    7. `ux_conversion` (id: `'cro'`, shortName: `'CRO'`, weight: 10%)
    8. `trust_authority` (id: `'trust_authority'`, shortName: `'Trust'`, weight: 10%)
  - When `report` is `null` or `undefined`, `synthesizePillars` produces a complete, safe fallback object where all 8 categories exist with `score: 0`, `grade: '—'`, and `health: 'POOR'`.

### 4. Challenge: Honest Perspectives & SXO Fallback Logic
- **Assumption challenged**: When `honest_scores` is null or partially null, the SXO bridge and fallback calculations must not throw null-pointer errors.
- **Attack scenario**:
  1. `honest_scores: undefined` -> `sxoScore` safely falls back to `croScore ?? null`.
  2. `honest_scores: { human_score: null }` -> safely falls back to `croScore`.
  3. `honest_scores: { human_score: 0 }` -> properly respects `0` (does not fall back to `croScore`).
  4. `catScores['TECHNICAL_SEO']: { score: null }` -> falls back to `honest.google_score`.
- **Empirical result**: **PASS**. All 4 fallback permutations tested and verified.

### 5. Challenge: ScoringRubricModal Alignment with Backend Weights & Rubric
- **Assumption challenged**: `ScoringRubricModal.tsx` must align with backend `BASELINE_WEIGHTS` (`backend/app/domain/scoring/weights.py`) and `SCORING_RUBRIC_V4` (`backend/app/domain/scoring/scoring_rubric.py`).
- **Attack scenario**: Render the modal component, verify 8 categories, verify weights sum to 100%, verify perspective composite formulas, and test tab navigation.
- **Empirical result**: **PASS**.
  - Category weights in modal: 15% (Tech) + 10% (On-Page) + 15% (Content) + 15% (GEO) + 15% (AI Search) + 10% (Schema) + 10% (UX) + 10% (Trust) = 100%. Matches backend `BASELINE_WEIGHTS`.
  - Composite formulas in modal:
    - Google Discoverability: 40% Technical + 30% On-Page + 30% Schema.
    - Human Experience: 50% UX/Conversion + 50% Content Readability.
    - AI Search Readiness: 60% GEO Extractability + 40% Question Support Points.
    - Matches `calculate_honest_scores` in `backend/app/domain/scoring/engine.py:1059-1070`.
  - Interactive tabs (Diminishing Returns, Confidence Gating, Calibrated Bands) render and navigate cleanly.

---

## Stress Test Results

| # | Test Scenario | Expected Behavior | Actual Behavior | Result |
|---|---------------|-------------------|-----------------|--------|
| 1 | 8 Canonical Categories Exposed | All 8 categories populated on rollup | All 8 categories present with correct scores | PASS |
| 2 | Empty / Null Report Handling | Safe fallback rollup with all 8 categories | Safe fallback, 0 scores, no crashes | PASS |
| 3 | Valid UX_CONVERSION Score (85.4) | Round to 85, grade 'B', health 'GOOD' | Score 85, grade 'B', health 'GOOD' | PASS |
| 4 | Low UX_CONVERSION Score (42) | Score 42, grade 'F', health 'POOR' | Score 42, grade 'F', health 'POOR' | PASS |
| 5 | Missing UX_CONVERSION | Score null, grade '—', unmeasured headline | Score null, grade '—', unmeasured headline | PASS |
| 6 | GA4 Measured Integration | GA4 key-event rate headline, score retained | Headline reflects GA4, score intact | PASS |
| 7 | Zero Score Preservation (All 0s) | Retain 0, grade 'F', health 'POOR' | Retained 0 across all categories | PASS |
| 8 | Negative Score Handling (-15, -5) | Retain negative score, grade 'F', 'POOR' | Handled safely, grade 'F', 'POOR' | PASS |
| 9 | Null Honest Perspectives | Fall back to croScore without crashing | sxoScore = croScore, no exceptions | PASS |
| 10 | Technical SEO Null with Honest Google | Fall back to honest.google_score | seo.score = 88 (from google_score) | PASS |
| 11 | Lowercase Category Keys (e.g. `technical`) | Fallback keys resolved | Scores correctly mapped | PASS |
| 12 | Floating Point Rounding (74.4, 79.6) | 74 and 80 | 74 and 80 | PASS |
| 13 | Grade/Health Threshold Boundaries | 90(A/GOOD), 80(B/GOOD), 70(C/FAIR), 60(D/FAIR), 59(F/POOR) | Exact match on all boundaries | PASS |
| 14 | Empty Findings & Missing Pages | 0 findings, 'Missing' sitemap/H1/HTTPS | Handled gracefully without errors | PASS |
| 15 | Extreme Scores (>100) | Grade 'A', health 'GOOD', no NaN | Handled safely | PASS |
| 16 | Rubric Modal Tab & Close Navigation | Tab switching & Escape/button closure | Clean tab rendering & closure | PASS |

---

## Unchallenged Areas

- Backend persistence consolidation (Phase 1 / Milestone M2) — explicitly scoped to M2.
- Tenant scoping and 403 authorization enforcement (Phase 1 / Milestone M3) — explicitly scoped to M3.
