# Technical Fix Strategy Blueprint: Milestone M1 Frontend Score Synthesis & UI Consistency

**Author:** `explorer_m1_2` (teamwork_preview_explorer)  
**Date:** 2026-10-31  
**Milestone:** M1 — Phase 0: Pipeline Scoring Timing & UI Consistency  
**Target Subsystems:**
- `frontend/src/lib/pillarSynthesis.ts`
- `frontend/src/types.ts`
- `frontend/src/components/ScoringRubricModal.tsx`
- `backend/app/domain/scoring/scoring_rubric.py`
- `frontend/src/components/Overview.tsx` (consumer inspection)

---

## 1. Executive Summary & Objective

In Dristik AI, deterministic scoring is governed by **8 canonical engine categories** (`TECHNICAL_SEO`, `ON_PAGE_SEO`, `CONTENT`, `GEO`, `AI_SEARCH`, `SCHEMA`, `UX_CONVERSION`, `TRUST_AUTHORITY`) with intent-adaptive baseline weights (15/10/15/15/15/10/10/10) and 3 specialized honest perspectives (Google Discoverability, Human Experience, AI Search Readiness).

However, investigation reveals conflicting legacy syntheses in the frontend client layer and discrepancy in published rubric documentation:
1. `frontend/src/lib/pillarSynthesis.ts` applies client-side ad-hoc formulas:
   - SEO synthesizes a `45/35/20` blend of Technical, On-Page, and Content.
   - AEO calculates an unweighted arithmetic average of `[schemaScore, extractabilityScore, botScore]`.
   - CRO hardcodes `score: null` (rendering `—` on overview cards and navigation badges even when the engine successfully computed `UX_CONVERSION`).
   - SXO (`website_experience`) circularly references `seoScore`.
   - Brand & Entity (`brand_entity_intelligence`) circularly references `aeoScore`.
2. `frontend/src/components/ScoringRubricModal.tsx` displays outdated perspective formulas (Google: `45/35/20`, Human: `40/35/25`, AI: `50/50`) that diverge from the backend calculation kernel in `backend/app/domain/scoring/engine.py:calculate_honest_scores` (Google: `40/30/30`, Human: `50/50`, AI: `60/40`).
3. `backend/app/domain/scoring/scoring_rubric.py` mirrors the outdated perspective formulas and contains the legacy `five_pillars` dictionary. While `eight_categories` must be authoritative, `five_pillars` must be retained as an alias list to prevent breaking regressions in `test_confidence_gating.py:12` (`assert len(rubric["five_pillars"]) == 5`).

This blueprint provides the exact, line-by-line implementation strategy to eliminate these conflicts, reconcile the UI scorecard with backend ground truth, and guarantee non-regression across all test harnesses.

---

## 2. Root Cause Analysis

### 2.1 Conflicting Syntheses in `frontend/src/lib/pillarSynthesis.ts`

| Target Field | Current Implementation (Lines) | Problem Description | Remediation |
|---|---|---|---|
| **SEO Pillar** | Lines 58–70 | Blends `techScore` (45%), `onPageScore` (35%), `contentScore` (20%). Diverges from canonical `TECHNICAL_SEO` category score (15% baseline). | Directly consume `catScores['TECHNICAL_SEO']?.score`. Expose `ON_PAGE_SEO` and `CONTENT` as distinct categories and report highlights without ad-hoc weighting. |
| **GEO Pillar** | Lines 100–110 | Evaluates `measuredExtractability != null ? Math.round(measuredExtractability) : geoCatScore`. Backend `apply_measured_geo_score` already sets `category_scores['GEO'].score` to measured extractability. | Directly consume `catScores['GEO']?.score`. |
| **AEO Pillar** | Lines 152–155 | Computes unweighted mean `(schemaScore + extractabilityScore + botScore) / 3`. Arbitrary composite with no engine backing. | Directly consume `catScores['SCHEMA']?.score` (or `catScores['AI_SEARCH']?.score`). Retain bot directives and llms.txt in highlights. |
| **CRO Pillar** | Lines 207–209 | Hardcodes `score: null`, `grade: '—'`, `health: 'POOR'`. Ignores engine-calculated `catScores['UX_CONVERSION']`. | Read `catScores['UX_CONVERSION']?.score`. Compute standard grade and health. Include GA4 metrics in highlights. |
| **SXO Alias** | Line 258 | `const sxoScore = seoScore ?? null;` Circularly assigns Experience to SEO! | Map to `honest?.human_score ?? catScores['UX_CONVERSION']?.score`. |
| **Brand Alias** | Line 282 | `score: aeoScore;` Circularly assigns Brand & Entity to AEO! | Map to canonical `catScores['TRUST_AUTHORITY']?.score`. |

### 2.2 Formula Divergence in `ScoringRubricModal.tsx` vs `engine.py`

In `frontend/src/components/ScoringRubricModal.tsx` lines 208–220:
- **Google Discoverability**: Claims `45% Technical + 35% On-Page + 20% Schema`.
  - Backend `engine.py:1063`: `weighted_mean([(0.40, tech_score), (0.30, onpage_score), (0.30, schema_score)])` (Ratio: `40/30/30`).
- **Human Experience**: Claims `40% UX/CRO + 35% Content Readability + 25% Trust`.
  - Backend `engine.py:1060`: `weighted_mean([(0.50, ux_score), (0.50, content_score)])` (Ratio: `50/50`; Trust is omitted from Human View because Trust is verified via external authority / governance).
- **AI Search Readiness**: Claims `50% GEO Extractability + 50% AI Search Visibility`.
  - Backend `engine.py:1070`: `weighted_mean([(0.6, geo_score), (0.4, support_points)])` (Ratio: `60% GEO + 40% Question Support Points` or `100% GEO fallback`). AI Visibility is a separate live citation empirical rate (`live_citation_score`).

### 2.3 Backward Compatibility Invariant in `scoring_rubric.py`

In `backend/app/domain/scoring/scoring_rubric.py`:
- `test_confidence_gating.py:12` executes:
  ```python
  def test_scoring_rubric_schema():
      rubric = get_scoring_rubric_v4()
      assert rubric["version"] == "enterprise_web_intel_v4"
      assert len(rubric["five_pillars"]) == 5
      assert "diminishing_returns" in rubric
      assert "confidence_gating_rules" in rubric
  ```
- If `five_pillars` is deleted, `test_confidence_gating.py` immediately fails.
- Therefore, `five_pillars` must be preserved as a legacy backward-compatibility alias, while `eight_categories` is established as the primary, authoritative engine rubric.

---

## 3. Implementation Blueprint

### 3.1 `frontend/src/types.ts`

**Target File:** `/Users/sayantande/Downloads/dristik-main/frontend/src/types.ts`  
**Location:** Lines 2451–2466  

Extend `WebsiteIntelligenceRollup` to optionally expose all 8 canonical categories while preserving existing properties for backward compatibility.

```typescript
export interface WebsiteIntelligenceRollup {
  // Enterprise separated pillars (mapped deterministically to canonical categories)
  seo: PillarScoreData;
  geo: PillarScoreData;
  aeo: PillarScoreData;
  cro: PillarScoreData;
  competitors: PillarScoreData;
  
  // 8 Canonical Engine Categories (Authoritative)
  technical_seo?: PillarScoreData;
  on_page_seo?: PillarScoreData;
  content?: PillarScoreData;
  schema?: PillarScoreData;
  trust_authority?: PillarScoreData;
  ai_search?: PillarScoreData;
  ux_conversion?: PillarScoreData;
  
  // Legacy pillar mappings for backward compatibility
  search_intelligence: PillarScoreData;
  ai_search_intelligence: PillarScoreData;
  website_experience: PillarScoreData;
  conversion_intelligence: PillarScoreData;
  brand_entity_intelligence: PillarScoreData;
  sxo_score: number | null;
  sxo_health: 'GOOD' | 'FAIR' | 'POOR';
}
```

---

### 3.2 `frontend/src/lib/pillarSynthesis.ts`

**Target File:** `/Users/sayantande/Downloads/dristik-main/frontend/src/lib/pillarSynthesis.ts`  
**Locations:** Lines 19–49 (Empty Rollup), Lines 58–93 (SEO), Lines 98–133 (GEO), Lines 138–182 (AEO), Lines 187–226 (CRO), Lines 256–309 (Aliases & Return).

#### Step-by-Step Refactoring Plan:

1. **Category Score Extraction**:
   Extract each canonical category directly from `report.scores?.category_scores`:
   ```typescript
   const catScores = report.scores?.category_scores || {};
   const honest = report.honest_scores;
   const findings = report.findings || [];

   const techCat = catScores['TECHNICAL_SEO'];
   const onPageCat = catScores['ON_PAGE_SEO'];
   const contentCat = catScores['CONTENT'];
   const geoCat = catScores['GEO'];
   const aiSearchCat = catScores['AI_SEARCH'];
   const schemaCat = catScores['SCHEMA'];
   const uxCat = catScores['UX_CONVERSION'];
   const trustCat = catScores['TRUST_AUTHORITY'];
   ```

2. **SEO Pillar (Technical SEO)**:
   - Eliminate `searchParts` 45/35/20 calculation.
   - Use `techCat?.score != null ? Math.round(techCat.score) : (honest?.google_score != null ? Math.round(honest.google_score) : null)`.
   - Score highlights show Technical, On-Page, and Content breakdown directly as reported by the engine.

3. **GEO Pillar (Generative Engine Optimization)**:
   - Use `geoCat?.score != null ? Math.round(geoCat.score) : null`.
   - Note: Backend `calculate_scores` / `apply_measured_geo_score` already sets `catScores['GEO'].score` to `extractability_score` when measured.
   - Highlights retain information gain, prompt coverage, and live citation status.

4. **AEO Pillar (Structured Data & Answer Engine Optimization)**:
   - Eliminate unweighted `(schema + extractability + bot) / 3`.
   - Use canonical `schemaCat?.score != null ? Math.round(schemaCat.score) : null`.
   - If `catScores['AI_SEARCH']?.score` is available, it can also inform live search highlights.
   - Highlights retain entity graph quality, JSON-LD types, and bot directives.

5. **CRO Pillar (Conversion Rate Optimization & UX Friction)**:
   - Eliminate hardcoded `score: null`.
   - Use canonical `uxCat?.score != null ? Math.round(uxCat.score) : null`.
   - `grade`: `getGrade(croScore)`.
   - `health`: `getHealth(croScore)`.
   - `headline`: If GA4 is connected, show key-event rate. Otherwise, display descriptive headline based on `croScore` threshold (e.g. `>= 75 ? 'Low Friction & Clear Value Proposition' : 'Conversion & UX Friction Detected'`).
   - Highlights preserve GA4 telemetry, form audit friction, primary CTA, and value proposition clarity.

6. **Experience Pillar (Legacy SXO)**:
   - Eliminate circular `const sxoScore = seoScore`.
   - Use `honest?.human_score != null ? Math.round(honest.human_score) : (croScore ?? null)`.
   - Highlights preserve TTFB latency and mobile viewport.

7. **Brand & Entity Pillar (Legacy Trust)**:
   - Eliminate circular `score: aeoScore`.
   - Use canonical `trustCat?.score != null ? Math.round(trustCat.score) : null`.
   - Highlights preserve Organization schema, entity conflicts, and brand signals.

8. **Expose Canonical Categories on Return Object**:
   Populate `technical_seo`, `on_page_seo`, `content`, `geo`, `ai_search`, `schema`, `ux_conversion`, `trust_authority` alongside `seo`, `geo`, `aeo`, `cro`, `competitors`.

#### Code Replacement in `pillarSynthesis.ts`:

```typescript
// Replace lines 58-70:
const techScore = techCat?.score != null ? Math.round(techCat.score) : (honest?.google_score != null ? Math.round(honest.google_score) : null);
const onPageScore = onPageCat?.score != null ? Math.round(onPageCat.score) : null;
const contentScore = contentCat?.score != null ? Math.round(contentCat.score) : null;
const seoScore = techScore;

// Replace lines 108-110:
const geoCatScore = geoCat?.score != null ? Math.round(geoCat.score) : null;
const geoScore = geoCatScore;

// Replace lines 152-155:
const schemaScore = schemaCat?.score != null ? Math.round(schemaCat.score) : null;
const aeoScore = schemaScore;

// Replace lines 207-209:
const uxScore = uxCat?.score != null ? Math.round(uxCat.score) : null;
const croScore = uxScore;

const croPillar: PillarScoreData = {
  id: 'cro',
  name: 'Conversion Rate Optimization (CRO)',
  shortName: 'CRO',
  categoryTag: 'CRO',
  score: croScore,
  grade: getGrade(croScore),
  health: getHealth(croScore),
  headline: ga4Measured
    ? `GA4 key-event rate ${ga4Rate}%`
    : (croScore == null ? 'Conversion experience unmeasured' : (croScore >= 75 ? 'Low Friction & Clear Value Proposition' : 'Conversion & UX Friction Detected')),
  summary: ga4Measured
    ? 'Google Analytics 4 landing pages and key events for this property. The rate is key events divided by sessions.'
    : 'Audited behavioral heuristics across CTAs, form barriers, and value proposition clarity.',
  highlights: [
    ga4Measured
      ? `GA4: ${ga4KeyEvents} key events / ${ga4Sessions} sessions (${ga4Rate}%)`
      : 'GA4 key-event rate: not measured',
    `Form Friction: ${formAudit?.cro_friction_grade ? `Grade ${formAudit.cro_friction_grade} (${formAudit.total_forms_detected} forms)` : 'Not measured'}`,
    `Primary CTA: ${report.business_profile?.primary_cta ? `"${report.business_profile.primary_cta}"` : 'Not detected'}`,
    `Value Prop Clarity: ${report.business_profile?.value_proposition ? 'Extracted' : 'Missing clear hero'}`,
    `UX Friction Hazards: ${report.semantic_business?.friction_points?.length || 0} logged`,
  ],
  findingsCount: croFindings.length,
};

// Replace lines 258, 282:
const sxoScore = honest?.human_score != null ? Math.round(honest.human_score) : (croScore ?? null);
const trustScore = trustCat?.score != null ? Math.round(trustCat.score) : null;

// Return object includes both legacy and canonical categories:
return {
  seo: seoPillar,
  geo: geoPillar,
  aeo: aeoPillar,
  cro: croPillar,
  competitors: competitorPillar,
  technical_seo: seoPillar,
  on_page_seo: onPagePillar,
  content: contentPillar,
  schema: aeoPillar,
  trust_authority: trustPillar,
  ai_search: aiSearchPillar,
  ux_conversion: croPillar,
  search_intelligence: seoPillar,
  ai_search_intelligence: geoPillar,
  website_experience: experiencePillar,
  conversion_intelligence: croPillar,
  brand_entity_intelligence: brandPillar,
  sxo_score: sxoScore,
  sxo_health: getHealth(sxoScore),
};
```

---

### 3.3 `frontend/src/components/ScoringRubricModal.tsx`

**Target File:** `/Users/sayantande/Downloads/dristik-main/frontend/src/components/ScoringRubricModal.tsx`  
**Location:** Lines 202–221  

#### Diff Specification:

```diff
               {/* Three Honesty Perspective Views */}
               <div className="p-4 rounded-xl border border-line bg-paper-100/60 dark:bg-ink-900/30 space-y-3">
                 <span className="font-semibold text-ink text-xs uppercase tracking-[0.04em] block">
                   3 Honest Perspective Views (Composite Blends)
                 </span>
                 <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                   <div className="p-3 rounded-lg bg-paper-50 dark:bg-ink-950 border border-line space-y-1">
                     <span className="font-bold text-ink block">Google Discoverability</span>
-                    <p className="text-[11px] text-ink-500">45% Technical + 35% On-Page + 20% Schema. Evaluates organic crawling and indexing posture.</p>
+                    <p className="text-[11px] text-ink-500">40% Technical + 30% On-Page + 30% Schema. Evaluates organic crawling, DOM hierarchy, and structured indexing posture.</p>
                   </div>
                   <div className="p-3 rounded-lg bg-paper-50 dark:bg-ink-950 border border-line space-y-1">
                     <span className="font-bold text-ink block">Human Experience</span>
-                    <p className="text-[11px] text-ink-500">40% UX/CRO + 35% Content Readability + 25% Trust. Evaluates engagement and conversion friction.</p>
+                    <p className="text-[11px] text-ink-500">50% UX/Conversion + 50% Content Readability. Evaluates user friction, CTA clarity, and copy comprehension.</p>
                   </div>
                   <div className="p-3 rounded-lg bg-paper-50 dark:bg-ink-950 border border-line space-y-1">
                     <span className="font-bold text-ink block">AI Search Readiness</span>
-                    <p className="text-[11px] text-ink-500">50% GEO Extractability + 50% AI Search Visibility (stays blank if live engine monitor was not run).</p>
+                    <p className="text-[11px] text-ink-500">60% GEO Extractability + 40% Question Support Points (or 100% GEO baseline). Live AI Visibility tracked separately.</p>
                   </div>
                 </div>
               </div>
```

---

### 3.4 `backend/app/domain/scoring/scoring_rubric.py`

**Target File:** `/Users/sayantande/Downloads/dristik-main/backend/app/domain/scoring/scoring_rubric.py`  
**Location:** Lines 75–94 (`honest_perspectives`) and Lines 95–158 (`five_pillars`)

#### Code Strategy:
1. Reconcile `honest_perspectives` to match `backend/app/domain/scoring/engine.py:calculate_honest_scores`:
   - Google: `0.40 * Technical + 0.30 * OnPage + 0.30 * Schema`
   - Human: `0.50 * UX + 0.50 * Content`
   - AI Search: `0.60 * GEO + 0.40 * QuestionSupport (or 1.0 * GEO fallback)`
2. Retain `five_pillars` as a 5-element list for backward compatibility with `test_confidence_gating.py:12` and public `/api/v1/platform/meta/scoring-rubric` consumers.
3. Add explanatory docstrings and header comments declaring `eight_categories` as the single authoritative scoring engine model.

#### Diff Specification:

```diff
     "honest_perspectives": [
         {
             "id": "google_perspective",
             "name": "Google Discoverability",
-            "description": "Blended view of Technical SEO (45%), On-Page SEO (35%), and Schema Architecture (20%). Evaluates indexation and organic search readiness.",
-            "formula": "0.45 * Technical + 0.35 * OnPage + 0.20 * Schema"
+            "description": "Blended view of Technical SEO (40%), On-Page SEO (30%), and Schema Architecture (30%). Evaluates organic crawlability, semantic markup, and indexation posture.",
+            "formula": "0.40 * Technical + 0.30 * OnPage + 0.30 * Schema"
         },
         {
             "id": "human_perspective",
             "name": "Human Experience",
-            "description": "Blended view of UX & Conversion (40%), Content Readability (35%), and Trust & Security (25%). Evaluates real buyer engagement and trust.",
-            "formula": "0.40 * UX + 0.35 * Content + 0.25 * Trust"
+            "description": "Blended view of UX & Conversion (50%) and Content Readability (50%). Evaluates user journey clarity, value proposition comprehension, and conversion friction.",
+            "formula": "0.50 * UX + 0.50 * Content"
         },
         {
             "id": "ai_perspective",
             "name": "AI Search Readiness",
-            "description": "Blended view of On-Page GEO extractability (50%) and live AI Visibility (50% when measured; otherwise on-page only). Evaluates citation readiness in generative answers.",
-            "formula": "0.50 * GEO + 0.50 * AIVisibility (or 1.0 * GEO if visibility unmeasured)"
+            "description": "Blended view of On-Page GEO extractability (60%) and deterministic commercial question support (40%). Live AI Search Visibility is tracked empirically as a separate citation rate.",
+            "formula": "0.60 * GEO + 0.40 * QuestionSupport (or 1.0 * GEO fallback)"
         }
     ],
+    # Note: 'five_pillars' is retained strictly as a backward-compatibility schema alias
+    # for legacy clients and regression tests (test_confidence_gating.py:12).
+    # The authoritative categories are 'eight_categories' above.
     "five_pillars": [
         {
             "id": "search_seo",
```

---

## 4. UI Consumer Impact & Non-Regression Analysis

### 4.1 Overview Tab (`frontend/src/components/Overview.tsx`)
- Lines 106–162 instantiate 5 discipline cards using:
  `rollup.seo.score`, `rollup.geo.score`, `rollup.aeo.score`, `rollup.cro.score`, `rollup.competitors.score`.
- **Before:**
  - `rollup.seo.score` showed an artificial 45/35/20 blend, disagreeing with `TECHNICAL_SEO` in the report.
  - `rollup.cro.score` showed `null` (`—`), frustrating users whose audit had evaluated forms, CTAs, and UX friction.
  - `rollup.aeo.score` showed an unweighted average of unrelated numbers.
- **After:**
  - `rollup.seo.score` reflects `TECHNICAL_SEO` directly.
  - `rollup.geo.score` reflects `GEO` directly.
  - `rollup.aeo.score` reflects `SCHEMA` directly.
  - `rollup.cro.score` reflects `UX_CONVERSION` directly (displays grade and health!).
  - `overallScore` continues to display `displayed.composite` from `buildDisplayedScore(report)` seamlessly.

### 4.2 Pillar Navigation Bar (`frontend/src/components/Navigation/PillarNavBar.tsx`)
- Reads `rollup.seo.score`, `rollup.geo.score`, `rollup.aeo.score`, `rollup.cro.score`.
- With the fix, the CRO badge in the navigation sidebar will now properly display the CRO score rather than undefined.

### 4.3 Website Intelligence Triad Hero (`frontend/src/components/WebsiteIntelligenceTriadHero.tsx`)
- Reads `rollup.conversion_intelligence.score` (which now correctly receives `rollup.cro.score`).
- Reads `rollup.brand_entity_intelligence.score` (which now receives `TRUST_AUTHORITY` instead of AEO).
- Reads `rollup.sxo_score` (which now receives `human_score` instead of SEO).

---

## 5. Verification & Test Plan

### 5.1 Automated Verification Commands

1. **Frontend Typecheck & Build**:
   ```bash
   cd /Users/sayantande/Downloads/dristik-main/frontend
   npm run build
   ```
   *Expected Result:* Zero TypeScript compilation errors. `tsc` completes cleanly.

2. **Frontend Vitest Suite**:
   ```bash
   cd /Users/sayantande/Downloads/dristik-main/frontend
   npm test
   ```
   *Expected Result:* All 29 test files (105 tests) pass.

3. **Backend Confidence Gating Test**:
   ```bash
   cd /Users/sayantande/Downloads/dristik-main
   pytest backend/tests/test_confidence_gating.py -v
   ```
   *Expected Result:* `test_scoring_rubric_schema` passes because `len(rubric["five_pillars"]) == 5` is preserved.

4. **Backend Scoring Calibration & Engine Suite**:
   ```bash
   cd /Users/sayantande/Downloads/dristik-main
   pytest backend/tests/test_scoring_calibration.py \
          backend/tests/test_scoring_unmeasured_authority.py \
          backend/tests/test_scoring_v5.py \
          backend/tests/test_scoring_geo_extractability.py -v
   ```
   *Expected Result:* All 23 scoring calibration and verification tests pass.

### 5.2 Concrete Implementation Test Cases

When implementing this strategy, create a new frontend test file `frontend/src/lib/pillarSynthesis.test.ts` to lock in these contracts:
1. `synthesizePillars` uses `TECHNICAL_SEO` directly without 45/35/20 blending.
2. `synthesizePillars` populates `cro.score` with `catScores['UX_CONVERSION'].score` and calculates valid health/grade.
3. `synthesizePillars` populates `aeo.score` with `catScores['SCHEMA'].score`.
4. `synthesizePillars` maps `brand_entity_intelligence` to `catScores['TRUST_AUTHORITY'].score`.
5. `synthesizePillars` maps `website_experience` to `honest.human_score` or `catScores['UX_CONVERSION'].score`.
6. `synthesizePillars` exposes all 8 canonical categories on the returned rollup object.
