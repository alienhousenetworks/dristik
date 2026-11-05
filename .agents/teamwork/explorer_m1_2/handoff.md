# Handoff Report: Milestone M1 Frontend Score Synthesis & UI Consistency Strategy

**Agent:** `explorer_m1_2`  
**Role:** teamwork_preview_explorer (Investigation & Synthesis)  
**Date:** 2026-10-31  
**Milestone:** M1 — Phase 0: Pipeline Scoring Timing & UI Consistency  
**Output Artifact:** `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m1_2/strategy_frontend.md`

---

## 1. Observation

Direct code observations with exact line numbers and quotes:

1. **`frontend/src/lib/pillarSynthesis.ts` (Lines 58–70, 108–110, 152–155, 207–209, 258, 282)**:
   - Line 61–69:
     ```typescript
     const searchParts = [
       [techScore, 0.45],
       [onPageScore, 0.35],
       [contentScore, 0.20],
     ].filter((pair): pair is [number, number] => typeof pair[0] === 'number');
     const searchWeight = searchParts.reduce((sum, pair) => sum + pair[1], 0);
     const seoScore = searchWeight > 0
       ? Math.round(searchParts.reduce((sum, [value, weight]) => sum + value * weight, 0) / searchWeight)
       : (typeof techScore === 'number' ? Math.round(techScore) : null);
     ```
   - Line 152–155:
     ```typescript
     const aeoParts = [schemaScore, extractabilityScore, botScore].filter((n): n is number => typeof n === 'number');
     const aeoScore = aeoParts.length
       ? Math.round(aeoParts.reduce((sum, n) => sum + n, 0) / aeoParts.length)
       : null;
     ```
   - Line 207–209:
     ```typescript
     score: null,
     grade: '—',
     health: getHealth(null),
     ```
   - Line 258:
     ```typescript
     const sxoScore = seoScore ?? null;
     ```
   - Line 282:
     ```typescript
     score: aeoScore,
     ```
   The client layer applies ad-hoc formulas: blending SEO (45/35/20), averaging AEO without weights, hardcoding CRO to null, circularly assigning SXO to SEO, and circularly assigning Brand to AEO.

2. **`frontend/src/components/ScoringRubricModal.tsx` (Lines 208–220)**:
   - Line 210:
     ```tsx
     <p className="text-[11px] text-ink-500">45% Technical + 35% On-Page + 20% Schema. Evaluates organic crawling and indexing posture.</p>
     ```
   - Line 214:
     ```tsx
     <p className="text-[11px] text-ink-500">40% UX/CRO + 35% Content Readability + 25% Trust. Evaluates engagement and conversion friction.</p>
     ```
   - Line 218:
     ```tsx
     <p className="text-[11px] text-ink-500">50% GEO Extractability + 50% AI Search Visibility (stays blank if live engine monitor was not run).</p>
     ```
   The modal teaches perspective formulas that diverge from backend kernel formulas.

3. **`backend/app/domain/scoring/engine.py:calculate_honest_scores` (Lines 1059–1080)**:
   - Line 1060:
     ```python
     human_score = weighted_mean([(0.50, ux_score), (0.50, content_score)])
     ```
   - Line 1063:
     ```python
     google_score = weighted_mean([(0.40, tech_score), (0.30, onpage_score), (0.30, schema_score)])
     ```
   - Lines 1067–1079:
     ```python
     if geo_readiness is not None and getattr(geo_readiness, "questions_total", 0) > 0:
         support_ratio = getattr(geo_readiness, "questions_supported", 0) / geo_readiness.questions_total
         support_points = support_ratio * 100.0
         ai_readiness_score = weighted_mean([(0.6, geo_score), (0.4, support_points)])
     ...
     else:
         ai_readiness_score = None if geo_score is None else round(geo_score, 1)
     ```
   The authoritative backend honest scoring applies:
   - Google: 40% Technical + 30% On-Page + 30% Schema.
   - Human: 50% UX/Conversion + 50% Content Readability.
   - AI Readiness: 60% GEO + 40% Question Support Points (or 100% GEO fallback). AI Visibility is an independent live empirical citation score.

4. **`backend/app/domain/scoring/scoring_rubric.py` (Lines 75–94, 95–158)**:
   - Lines 75–94 contain the outdated formulas: `0.45 * Technical + 0.35 * OnPage + 0.20 * Schema`, `0.40 * UX + 0.35 * Content + 0.25 * Trust`, `0.50 * GEO + 0.50 * AIVisibility`.
   - Lines 95–158 contain `"five_pillars": [...]` with 5 entries.

5. **`backend/tests/test_confidence_gating.py` (Line 12)**:
   - Line 12:
     ```python
     def test_scoring_rubric_schema():
         rubric = get_scoring_rubric_v4()
         assert rubric["version"] == "enterprise_web_intel_v4"
         assert len(rubric["five_pillars"]) == 5
         assert "diminishing_returns" in rubric
         assert "confidence_gating_rules" in rubric
     ```
   Running `pytest backend/tests/test_confidence_gating.py -v` passed with 3 passed tests. Deleting `five_pillars` would break line 12.

---

## 2. Logic Chain

1. From **Observation 1**, `pillarSynthesis.ts` overrides backend scoring decisions by performing client-side averaging (45/35/20 SEO, unweighted AEO) and suppressing CRO score by forcing `score: null`. This contradicts Requirement R1 ("Align frontend score synthesis directly with the 8 canonical engine categories, eliminating conflicting legacy 5-pillar formulas").
2. Aligning `pillarSynthesis.ts` to read directly from `report.scores.category_scores` (`TECHNICAL_SEO`, `ON_PAGE_SEO`, `CONTENT`, `GEO`, `AI_SEARCH`, `SCHEMA`, `UX_CONVERSION`, `TRUST_AUTHORITY`):
   - Restores truthfulness to the UI scorecard.
   - Allows `Overview.tsx`, `PillarNavBar.tsx`, and `WebsiteIntelligenceTriadHero.tsx` to display true category scores without altering their component code.
   - Fixes CRO displaying `—` by allowing `catScores['UX_CONVERSION']` to populate `cro.score` with its appropriate grade and health.
3. From **Observations 2 & 3**, `ScoringRubricModal.tsx` advertises formulas that do not match `engine.py:calculate_honest_scores`. Updating lines 208–220 in `ScoringRubricModal.tsx` reconciles the frontend documentation with backend mathematics.
4. From **Observations 4 & 5**, `scoring_rubric.py` must reconcile `honest_perspectives` to match `engine.py`, but must NOT delete `five_pillars` because `test_confidence_gating.py:12` explicitly asserts `len(rubric["five_pillars"]) == 5`. Retaining `five_pillars` as a backward-compatibility alias dictionary preserves full backward compatibility while declaring `eight_categories` as authoritative.

---

## 3. Caveats

1. The display of headline overall score (`buildDisplayedScore` / `displayed_composite`) uses a 4-pillar model (`Technical 30%`, `GEO 25%`, `AEO 25%`, `CRO 20%`), which is already in exact mathematical alignment between `frontend/src/lib/displayedAuditScore.ts` and `backend/app/domain/scoring/displayed_score.py`. This blueprint preserves that headline composite while ensuring individual discipline cards match canonical categories.
2. External authority and live search visibility timing (Backend pipeline Step 13 vs Step 15) are part of Milestone M1 and addressed by sister explorer / implementer tasks; this blueprint focuses specifically on Frontend Score Synthesis & UI Consistency.

---

## 4. Conclusion

The technical strategy for Milestone M1 Frontend Score Synthesis & UI Consistency is complete and documented in:
`/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m1_2/strategy_frontend.md`.

The strategy consists of:
1. **`pillarSynthesis.ts`**: Re-align score calculations directly with `report.scores.category_scores`, eliminating the 45/35/20 SEO blend, unweighted AEO average, and hardcoded CRO null. Map legacy aliases faithfully (`website_experience` to Human score, `brand_entity_intelligence` to Trust). Expose all 8 canonical categories.
2. **`ScoringRubricModal.tsx`**: Reconcile perspective formulas (Google: 40/30/30, Human: 50/50, AI: 60/40) to match backend `calculate_honest_scores`.
3. **`scoring_rubric.py`**: Reconcile `honest_perspectives` formulas to match `calculate_honest_scores`, while retaining `five_pillars` as a 5-element alias list for backward compatibility with `test_confidence_gating.py:12`.
4. **`types.ts`**: Extend `WebsiteIntelligenceRollup` to optionally declare the 8 canonical categories.

---

## 5. Verification Method

To independently verify the technical fix strategy:

1. **Verify Backend Tests Pass**:
   ```bash
   pytest backend/tests/test_confidence_gating.py -v
   pytest backend/tests/test_scoring_calibration.py \
          backend/tests/test_scoring_unmeasured_authority.py \
          backend/tests/test_scoring_v5.py \
          backend/tests/test_scoring_geo_extractability.py -v
   ```
   *Pass Condition:* All tests pass without regression. `assert len(rubric["five_pillars"]) == 5` succeeds.

2. **Verify Frontend Build & Tests**:
   ```bash
   cd frontend
   npm run build
   npm test
   ```
   *Pass Condition:* TypeScript typecheck passes with 0 errors (`tsc && vite build`). All 29 vitest suites (105 tests) pass.

3. **Inspect Output Blueprint**:
   Read `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m1_2/strategy_frontend.md` to confirm file paths, line ranges, and before/after code specifications.
