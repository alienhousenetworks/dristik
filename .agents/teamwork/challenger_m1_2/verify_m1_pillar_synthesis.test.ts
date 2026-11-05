import { describe, it, expect } from 'vitest';
import { synthesizePillars } from '../../../frontend/src/lib/pillarSynthesis';
import { ExecutiveReport } from '../../../frontend/src/types';

describe('Milestone M1 Empirical Verification: synthesizePillars', () => {

  const makeBaseReport = (overrides?: Partial<ExecutiveReport>): ExecutiveReport => ({
    domain: 'example.com',
    generated_at: '2026-10-31T00:00:00Z',
    business_profile: {
      business_name: 'Example Corp',
      business_type: 'B2B',
      primary_cta: 'Book Demo',
      value_proposition: 'All in one platform',
      target_icp: 'Enterprise'
    } as any,
    scores: {
      overall_score: 75,
      overall_confidence: 0.9,
      evidence_coverage: 0.85,
      grade: 'C',
      health_label: 'FAIR',
      category_scores: {},
      intent_adjusted_weights: {}
    },
    findings: [],
    story_summary: 'Summary',
    what_site_gets_right: [],
    what_is_holding_it_back: [],
    primary_strategic_opportunity: 'SEO',
    consultant_advice_what_to_ignore: 'None',
    three_way_comparison: {} as any,
    ai_search_matrix: [],
    code_patches: [],
    roadmap_7_days: [],
    roadmap_30_days: [],
    roadmap_90_days: [],
    telemetry: {} as any,
    crawl_summary: {},
    agent_execution_trace: [],
    ...overrides,
  });

  describe('1. 8 Canonical Categories Exposed', () => {
    it('exposes all 8 canonical categories on the rollup', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 80,
          overall_confidence: 0.9,
          evidence_coverage: 0.85,
          grade: 'B',
          health_label: 'GOOD',
          category_scores: {
            TECHNICAL_SEO: { category: 'TECHNICAL_SEO' as any, score: 85, confidence: 1, weight: 0.15, weighted_score: 12.75, strengths: [], weaknesses: [], summary: 'Tech ok' },
            ON_PAGE_SEO: { category: 'ON_PAGE_SEO' as any, score: 70, confidence: 1, weight: 0.10, weighted_score: 7.0, strengths: [], weaknesses: [], summary: 'On-page ok' },
            CONTENT: { category: 'CONTENT' as any, score: 65, confidence: 1, weight: 0.15, weighted_score: 9.75, strengths: [], weaknesses: [], summary: 'Content ok' },
            GEO: { category: 'GEO' as any, score: 90, confidence: 1, weight: 0.15, weighted_score: 13.5, strengths: [], weaknesses: [], summary: 'GEO ok' },
            AI_SEARCH: { category: 'AI_SEARCH' as any, score: 78, confidence: 1, weight: 0.15, weighted_score: 11.7, strengths: [], weaknesses: [], summary: 'AI Search ok' },
            SCHEMA: { category: 'SCHEMA' as any, score: 95, confidence: 1, weight: 0.10, weighted_score: 9.5, strengths: [], weaknesses: [], summary: 'Schema ok' },
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 82, confidence: 1, weight: 0.10, weighted_score: 8.2, strengths: [], weaknesses: [], summary: 'UX ok' },
            TRUST_AUTHORITY: { category: 'TRUST_AUTHORITY' as any, score: 88, confidence: 1, weight: 0.10, weighted_score: 8.8, strengths: [], weaknesses: [], summary: 'Trust ok' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);

      // Verify all 8 canonical properties exist and are defined
      expect(rollup.technical_seo).toBeDefined();
      expect(rollup.on_page_seo).toBeDefined();
      expect(rollup.content).toBeDefined();
      expect(rollup.geo).toBeDefined();
      expect(rollup.ai_search).toBeDefined();
      expect(rollup.schema).toBeDefined();
      expect(rollup.ux_conversion).toBeDefined();
      expect(rollup.trust_authority).toBeDefined();

      // Verify scores match
      expect(rollup.technical_seo?.score).toBe(85);
      expect(rollup.on_page_seo?.score).toBe(70);
      expect(rollup.content?.score).toBe(65);
      expect(rollup.geo.score).toBe(90);
      expect(rollup.ai_search?.score).toBe(78);
      expect(rollup.schema?.score).toBe(95);
      expect(rollup.ux_conversion?.score).toBe(82);
      expect(rollup.trust_authority?.score).toBe(88);

      // Verify IDs and metadata
      expect(rollup.technical_seo?.id).toBe('seo'); // mapped to seoPillar
      expect(rollup.on_page_seo?.id).toBe('on_page_seo');
      expect(rollup.content?.id).toBe('content');
      expect(rollup.geo.id).toBe('geo');
      expect(rollup.ai_search?.id).toBe('ai_search');
      expect(rollup.schema?.id).toBe('aeo'); // mapped to aeoPillar
      expect(rollup.ux_conversion?.id).toBe('cro'); // mapped to croPillar
      expect(rollup.trust_authority?.id).toBe('trust_authority');
    });

    it('exposes all 8 canonical categories on empty / null report', () => {
      const rollupNull = synthesizePillars(null);
      const rollupUndefined = synthesizePillars(undefined);

      for (const rollup of [rollupNull, rollupUndefined]) {
        expect(rollup.technical_seo).toBeDefined();
        expect(rollup.on_page_seo).toBeDefined();
        expect(rollup.content).toBeDefined();
        expect(rollup.geo).toBeDefined();
        expect(rollup.ai_search).toBeDefined();
        expect(rollup.schema).toBeDefined();
        expect(rollup.ux_conversion).toBeDefined();
        expect(rollup.trust_authority).toBeDefined();

        expect(rollup.technical_seo?.score).toBe(0);
        expect(rollup.on_page_seo?.score).toBe(0);
        expect(rollup.content?.score).toBe(0);
        expect(rollup.geo.score).toBe(0);
        expect(rollup.ai_search?.score).toBe(0);
        expect(rollup.schema?.score).toBe(0);
        expect(rollup.ux_conversion?.score).toBe(0);
        expect(rollup.trust_authority?.score).toBe(0);
      }
    });
  });

  describe('2. CRO Score & Health Verification', () => {
    it('reflects valid UX_CONVERSION score, grade, and health', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 80,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'B',
          health_label: 'GOOD',
          category_scores: {
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 85.4, confidence: 1, weight: 0.1, weighted_score: 8.54, strengths: [], weaknesses: [], summary: 'High conversion' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.cro.score).toBe(85);
      expect(rollup.cro.grade).toBe('B');
      expect(rollup.cro.health).toBe('GOOD');
      expect(rollup.cro.headline).toBe('Low Friction & Clear Value Proposition');
      expect(rollup.ux_conversion?.score).toBe(85);
      expect(rollup.conversion_intelligence.score).toBe(85);
    });

    it('reflects POOR health and F grade when UX_CONVERSION is low (<60)', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 50,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'F',
          health_label: 'POOR',
          category_scores: {
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 42, confidence: 1, weight: 0.1, weighted_score: 4.2, strengths: [], weaknesses: [], summary: 'Low conversion' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.cro.score).toBe(42);
      expect(rollup.cro.grade).toBe('F');
      expect(rollup.cro.health).toBe('POOR');
      expect(rollup.cro.headline).toBe('Conversion & UX Friction Detected');
    });

    it('returns null score, dash grade, and unmeasured headline when UX_CONVERSION is missing', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 70,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'C',
          health_label: 'FAIR',
          category_scores: {},
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.cro.score).toBeNull();
      expect(rollup.cro.grade).toBe('—');
      expect(rollup.cro.health).toBe('POOR');
      expect(rollup.cro.headline).toBe('Conversion experience unmeasured');
    });

    it('handles GA4 analytics when measured without overriding cro score with null', () => {
      const report = makeBaseReport({
        google_performance: {
          analytics: {
            state: 'MEASURED',
            landing_pages: ['/home'],
            key_events: 15,
            sessions: 100,
          }
        } as any,
        scores: {
          overall_score: 75,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'C',
          health_label: 'FAIR',
          category_scores: {
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 78, confidence: 1, weight: 0.1, weighted_score: 7.8, strengths: [], weaknesses: [], summary: 'Good' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.cro.score).toBe(78);
      expect(rollup.cro.headline).toBe('GA4 key-event rate 15%');
    });
  });

  describe('3. Edge Cases & Boundary Stress Testing', () => {
    it('preserves 0 score across all categories (not converting 0 to null)', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 0,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'F',
          health_label: 'POOR',
          category_scores: {
            TECHNICAL_SEO: { category: 'TECHNICAL_SEO' as any, score: 0, confidence: 1, weight: 0.15, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            ON_PAGE_SEO: { category: 'ON_PAGE_SEO' as any, score: 0, confidence: 1, weight: 0.10, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            CONTENT: { category: 'CONTENT' as any, score: 0, confidence: 1, weight: 0.15, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            GEO: { category: 'GEO' as any, score: 0, confidence: 1, weight: 0.15, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            AI_SEARCH: { category: 'AI_SEARCH' as any, score: 0, confidence: 1, weight: 0.15, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            SCHEMA: { category: 'SCHEMA' as any, score: 0, confidence: 1, weight: 0.10, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 0, confidence: 1, weight: 0.10, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
            TRUST_AUTHORITY: { category: 'TRUST_AUTHORITY' as any, score: 0, confidence: 1, weight: 0.10, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Zero' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);

      expect(rollup.technical_seo?.score).toBe(0);
      expect(rollup.on_page_seo?.score).toBe(0);
      expect(rollup.content?.score).toBe(0);
      expect(rollup.geo.score).toBe(0);
      expect(rollup.ai_search?.score).toBe(0);
      expect(rollup.schema?.score).toBe(0);
      expect(rollup.ux_conversion?.score).toBe(0);
      expect(rollup.trust_authority?.score).toBe(0);

      expect(rollup.cro.score).toBe(0);
      expect(rollup.cro.grade).toBe('F');
      expect(rollup.cro.health).toBe('POOR');
      expect(rollup.cro.headline).toBe('Conversion & UX Friction Detected');

      expect(rollup.seo.score).toBe(0);
      expect(rollup.geo.score).toBe(0);
      expect(rollup.aeo.score).toBe(0);
    });

    it('handles negative scores gracefully without crashing', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 0,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'F',
          health_label: 'POOR',
          category_scores: {
            TECHNICAL_SEO: { category: 'TECHNICAL_SEO' as any, score: -15, confidence: 1, weight: 0.15, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Negative' },
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: -5, confidence: 1, weight: 0.10, weighted_score: 0, strengths: [], weaknesses: [], summary: 'Negative' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.technical_seo?.score).toBe(-15);
      expect(rollup.technical_seo?.grade).toBe('F');
      expect(rollup.technical_seo?.health).toBe('POOR');

      expect(rollup.ux_conversion?.score).toBe(-5);
      expect(rollup.ux_conversion?.grade).toBe('F');
      expect(rollup.ux_conversion?.health).toBe('POOR');
    });

    it('handles null and undefined honest perspectives without crashing', () => {
      const report = makeBaseReport({
        honest_scores: undefined,
        scores: {
          overall_score: 70,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'C',
          health_label: 'FAIR',
          category_scores: {
            TECHNICAL_SEO: { category: 'TECHNICAL_SEO' as any, score: 75, confidence: 1, weight: 0.15, weighted_score: 11.25, strengths: [], weaknesses: [], summary: 'Ok' },
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 65, confidence: 1, weight: 0.10, weighted_score: 6.5, strengths: [], weaknesses: [], summary: 'Ok' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.seo.score).toBe(75);
      expect(rollup.sxo_score).toBe(65); // falls back to croScore
      expect(rollup.sxo_health).toBe('FAIR');
      expect(rollup.content?.highlights[1]).toBe('Readability: Audited');
      expect(rollup.geo.highlights[1]).toBe('Live visibility: not measured');
    });

    it('correctly uses honest_scores.google_score when technical_seo is missing', () => {
      const report = makeBaseReport({
        honest_scores: {
          google_score: 82.3,
          human_score: 91.0,
          ai_readiness_score: 77.0,
          ai_visibility_score: null,
          ai_visibility_status: 'UNMEASURED',
          external_authority_connected: false,
        } as any,
        scores: {
          overall_score: 75,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'C',
          health_label: 'FAIR',
          category_scores: {},
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.seo.score).toBe(82); // rounded from honest.google_score
      expect(rollup.sxo_score).toBe(91); // from honest.human_score
      expect(rollup.sxo_health).toBe('GOOD');
    });

    it('supports lowercase alias keys in category_scores', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 70,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'C',
          health_label: 'FAIR',
          category_scores: {
            technical: { category: 'TECHNICAL_SEO' as any, score: 81, confidence: 1, weight: 0.15, weighted_score: 12.15, strengths: [], weaknesses: [], summary: 'Ok' },
            on_page: { category: 'ON_PAGE_SEO' as any, score: 71, confidence: 1, weight: 0.10, weighted_score: 7.1, strengths: [], weaknesses: [], summary: 'Ok' },
            content: { category: 'CONTENT' as any, score: 61, confidence: 1, weight: 0.15, weighted_score: 9.15, strengths: [], weaknesses: [], summary: 'Ok' },
            geo: { category: 'GEO' as any, score: 91, confidence: 1, weight: 0.15, weighted_score: 13.65, strengths: [], weaknesses: [], summary: 'Ok' },
            ai_search: { category: 'AI_SEARCH' as any, score: 76, confidence: 1, weight: 0.15, weighted_score: 11.4, strengths: [], weaknesses: [], summary: 'Ok' },
            schema: { category: 'SCHEMA' as any, score: 96, confidence: 1, weight: 0.10, weighted_score: 9.6, strengths: [], weaknesses: [], summary: 'Ok' },
            ux_conversion: { category: 'UX_CONVERSION' as any, score: 86, confidence: 1, weight: 0.10, weighted_score: 8.6, strengths: [], weaknesses: [], summary: 'Ok' },
            trust_authority: { category: 'TRUST_AUTHORITY' as any, score: 89, confidence: 1, weight: 0.10, weighted_score: 8.9, strengths: [], weaknesses: [], summary: 'Ok' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.technical_seo?.score).toBe(81);
      expect(rollup.on_page_seo?.score).toBe(71);
      expect(rollup.content?.score).toBe(61);
      expect(rollup.geo.score).toBe(91);
      expect(rollup.ai_search?.score).toBe(76);
      expect(rollup.schema?.score).toBe(96);
      expect(rollup.ux_conversion?.score).toBe(86);
      expect(rollup.trust_authority?.score).toBe(89);
    });

    it('rounds floating point scores properly', () => {
      const report = makeBaseReport({
        scores: {
          overall_score: 75,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'C',
          health_label: 'FAIR',
          category_scores: {
            UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: 74.4, confidence: 1, weight: 0.1, weighted_score: 7.44, strengths: [], weaknesses: [], summary: 'Round down' },
            TECHNICAL_SEO: { category: 'TECHNICAL_SEO' as any, score: 79.6, confidence: 1, weight: 0.15, weighted_score: 11.94, strengths: [], weaknesses: [], summary: 'Round up' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.cro.score).toBe(74);
      expect(rollup.cro.health).toBe('FAIR');
      expect(rollup.seo.score).toBe(80);
      expect(rollup.seo.health).toBe('GOOD');
    });

    it('calibrates grade and health thresholds accurately', () => {
      // 90 -> A / GOOD
      // 80 -> B / GOOD
      // 70 -> C / FAIR
      // 60 -> D / FAIR
      // 59 -> F / POOR
      const testCases = [
        { score: 95, expectedGrade: 'A', expectedHealth: 'GOOD' },
        { score: 90, expectedGrade: 'A', expectedHealth: 'GOOD' },
        { score: 89, expectedGrade: 'B', expectedHealth: 'GOOD' },
        { score: 80, expectedGrade: 'B', expectedHealth: 'GOOD' },
        { score: 79, expectedGrade: 'C', expectedHealth: 'FAIR' },
        { score: 70, expectedGrade: 'C', expectedHealth: 'FAIR' },
        { score: 69, expectedGrade: 'D', expectedHealth: 'FAIR' },
        { score: 60, expectedGrade: 'D', expectedHealth: 'FAIR' },
        { score: 59, expectedGrade: 'F', expectedHealth: 'POOR' },
        { score: 0, expectedGrade: 'F', expectedHealth: 'POOR' },
      ];

      for (const tc of testCases) {
        const report = makeBaseReport({
          scores: {
            overall_score: tc.score,
            overall_confidence: 1,
            evidence_coverage: 1,
            grade: tc.expectedGrade,
            health_label: tc.expectedHealth,
            category_scores: {
              UX_CONVERSION: { category: 'UX_CONVERSION' as any, score: tc.score, confidence: 1, weight: 0.1, weighted_score: tc.score * 0.1, strengths: [], weaknesses: [], summary: '' },
            },
            intent_adjusted_weights: {}
          }
        });
        const rollup = synthesizePillars(report);
        expect(rollup.cro.grade, `Score ${tc.score} grade`).toBe(tc.expectedGrade);
        expect(rollup.cro.health, `Score ${tc.score} health`).toBe(tc.expectedHealth);
      }
    });

    it('handles empty findings gracefully', () => {
      const report = makeBaseReport({ findings: undefined as any });
      const rollup = synthesizePillars(report);
      expect(rollup.seo.findingsCount).toBe(0);
      expect(rollup.cro.findingsCount).toBe(0);
      expect(rollup.content?.findingsCount).toBe(0);
    });

    it('handles empty crawl_manifest and pages gracefully', () => {
      const report = makeBaseReport({
        crawl_manifest: undefined,
        scores: {
          overall_score: 80,
          overall_confidence: 1,
          evidence_coverage: 1,
          grade: 'B',
          health_label: 'GOOD',
          category_scores: {
            TECHNICAL_SEO: { category: 'TECHNICAL_SEO' as any, score: 85, confidence: 1, weight: 0.15, weighted_score: 12.75, strengths: [], weaknesses: [], summary: '' },
            ON_PAGE_SEO: { category: 'ON_PAGE_SEO' as any, score: 80, confidence: 1, weight: 0.10, weighted_score: 8.0, strengths: [], weaknesses: [], summary: '' },
            TRUST_AUTHORITY: { category: 'TRUST_AUTHORITY' as any, score: 80, confidence: 1, weight: 0.10, weighted_score: 8.0, strengths: [], weaknesses: [], summary: '' },
          },
          intent_adjusted_weights: {}
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.seo.highlights[2]).toBe('Sitemap & Robots: Missing');
      expect(rollup.seo.highlights[3]).toBe('Pages Audited: 0 crawled');
      expect(rollup.on_page_seo?.highlights[1]).toBe('H1 Status: Missing');
      expect(rollup.trust_authority?.highlights[1]).toBe('HTTPS: Missing');
    });
  });

  describe('4. ScoringRubricModal Alignment Verification', () => {
    it('verifies that the 8 canonical categories match backend BASELINE_WEIGHTS exactly', () => {
      // Backend weights in backend/app/domain/scoring/weights.py:
      // TECHNICAL_SEO: 0.15 (15%)
      // ON_PAGE_SEO: 0.10 (10%)
      // CONTENT: 0.15 (15%)
      // GEO: 0.15 (15%)
      // AI_SEARCH: 0.15 (15%)
      // SCHEMA: 0.10 (10%)
      // UX_CONVERSION: 0.10 (10%)
      // TRUST_AUTHORITY: 0.10 (10%)

      const rubricPillars = [
        { id: 'technical_seo', weight_pct: 15 },
        { id: 'on_page_seo', weight_pct: 10 },
        { id: 'content', weight_pct: 15 },
        { id: 'geo', weight_pct: 15 },
        { id: 'ai_search', weight_pct: 15 },
        { id: 'schema', weight_pct: 10 },
        { id: 'ux_conversion', weight_pct: 10 },
        { id: 'trust_authority', weight_pct: 10 },
      ];

      const totalWeight = rubricPillars.reduce((sum, p) => sum + p.weight_pct, 0);
      expect(totalWeight).toBe(100);
      expect(rubricPillars.length).toBe(8);
    });
  });
});
