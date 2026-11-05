import { describe, it, expect, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});
import { synthesizePillars } from '../../../frontend/src/lib/pillarSynthesis';
import { ScoringRubricModal } from '../../../frontend/src/components/ScoringRubricModal';
import { ExecutiveReport } from '../../../frontend/src/types';

describe('Adversarial & Component Stress Testing for Milestone M1', () => {

  const makeBaseReport = (overrides?: any): ExecutiveReport => ({
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

  describe('Adversarial Score Value Permutations', () => {
    it('handles explicit null in category score without throwing', () => {
      const report = makeBaseReport({
        scores: {
          category_scores: {
            TECHNICAL_SEO: { score: null } as any,
            UX_CONVERSION: { score: null } as any,
            GEO: { score: null } as any,
            SCHEMA: { score: null } as any,
            CONTENT: { score: null } as any,
            ON_PAGE_SEO: { score: null } as any,
            AI_SEARCH: { score: null } as any,
            TRUST_AUTHORITY: { score: null } as any,
          }
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.technical_seo?.score).toBeNull();
      expect(rollup.ux_conversion?.score).toBeNull();
      expect(rollup.cro.score).toBeNull();
      expect(rollup.cro.grade).toBe('—');
      expect(rollup.cro.health).toBe('POOR');
      expect(rollup.content?.score).toBeNull();
      expect(rollup.trust_authority?.score).toBeNull();
    });

    it('falls back to honest_scores.google_score when techCat.score is null', () => {
      const report = makeBaseReport({
        honest_scores: { google_score: 88.4 } as any,
        scores: {
          category_scores: {
            TECHNICAL_SEO: { score: null } as any,
          }
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.seo.score).toBe(88);
      expect(rollup.technical_seo?.score).toBe(88);
    });

    it('falls back to croScore for sxoScore when honest.human_score is null', () => {
      const report = makeBaseReport({
        honest_scores: { human_score: null } as any,
        scores: {
          category_scores: {
            UX_CONVERSION: { score: 72 } as any,
          }
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.sxo_score).toBe(72);
      expect(rollup.sxo_health).toBe('FAIR');
      expect(rollup.website_experience.score).toBe(72);
    });

    it('prefers honest.human_score = 0 over croScore when human_score is zero', () => {
      const report = makeBaseReport({
        honest_scores: { human_score: 0 } as any,
        scores: {
          category_scores: {
            UX_CONVERSION: { score: 85 } as any,
          }
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.sxo_score).toBe(0); // 0 != null is true, so 0 is used, not 85!
      expect(rollup.sxo_health).toBe('POOR');
    });

    it('handles report with scores object completely null', () => {
      const report = makeBaseReport({ scores: null });
      const rollup = synthesizePillars(report);
      expect(rollup.seo.score).toBeNull();
      expect(rollup.cro.score).toBeNull();
      expect(rollup.technical_seo?.score).toBeNull();
      expect(rollup.ux_conversion?.score).toBeNull();
    });

    it('handles report with completely empty object {}', () => {
      const rollup = synthesizePillars({} as any);
      expect(rollup.seo.score).toBeNull();
      expect(rollup.cro.score).toBeNull();
    });

    it('handles extreme scores: >100 and negative', () => {
      const report = makeBaseReport({
        scores: {
          category_scores: {
            TECHNICAL_SEO: { score: 150 } as any,
            UX_CONVERSION: { score: -20 } as any,
          }
        }
      });

      const rollup = synthesizePillars(report);
      expect(rollup.technical_seo?.score).toBe(150);
      expect(rollup.technical_seo?.grade).toBe('A');
      expect(rollup.technical_seo?.health).toBe('GOOD');

      expect(rollup.ux_conversion?.score).toBe(-20);
      expect(rollup.ux_conversion?.grade).toBe('F');
      expect(rollup.ux_conversion?.health).toBe('POOR');
    });
  });

  describe('ScoringRubricModal Component Verification', () => {
    it('does not render when isOpen is false', () => {
      const { container } = render(<ScoringRubricModal isOpen={false} onClose={() => {}} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders all 8 canonical categories in weights tab when isOpen is true', () => {
      render(<ScoringRubricModal isOpen={true} onClose={() => {}} />);

      // Verify Title
      expect(screen.getByText('Dristik Enterprise Web Intelligence & Scoring Rubric')).toBeTruthy();

      // Verify All 8 Categories
      expect(screen.getByText('1. Technical SEO')).toBeTruthy();
      expect(screen.getByText('2. On-Page SEO')).toBeTruthy();
      expect(screen.getByText('3. Content & Semantics')).toBeTruthy();
      expect(screen.getByText('4. GEO & AI Readiness')).toBeTruthy();
      expect(screen.getByText('5. AI Search Visibility')).toBeTruthy();
      expect(screen.getByText('6. Schema Architecture')).toBeTruthy();
      expect(screen.getByText('7. UX & Conversion (CRO)')).toBeTruthy();
      expect(screen.getByText('8. Trust & Authority (E-E-A-T)')).toBeTruthy();

      // Verify Weights
      expect(screen.getAllByText('Weight: 15%').length).toBe(4); // Tech, Content, GEO, AI Search = 4
      expect(screen.getAllByText('Weight: 10%').length).toBe(4); // On-Page, Schema, UX, Trust = 4

      // Verify Honest Perspectives
      expect(screen.getByText('Google Discoverability')).toBeTruthy();
      expect(screen.getByText('Human Experience')).toBeTruthy();
      expect(screen.getByText('AI Search Readiness')).toBeTruthy();
    });

    it('navigates through tabs: formula, gating, bands', () => {
      render(<ScoringRubricModal isOpen={true} onClose={() => {}} />);

      // Click Formula Tab
      fireEvent.click(screen.getByText('2. Diminishing Returns Math'));
      expect(screen.getByText('Diminishing Returns Deduction Formula')).toBeTruthy();
      expect(screen.getByText('CRITICAL')).toBeTruthy();
      expect(screen.getByText('-25.0 pts')).toBeTruthy();
      expect(screen.getByText('-15.0 pts')).toBeTruthy();

      // Click Gating Tab
      fireEvent.click(screen.getByText('3. Confidence Gating Rules'));
      expect(screen.getByText('Strict Confidence Gating Architecture')).toBeTruthy();
      expect(screen.getByText('Verified Empirical DOM Facts')).toBeTruthy();
      expect(screen.getByText('Cognitive Model Inferences')).toBeTruthy();

      // Click Bands Tab
      fireEvent.click(screen.getByText('4. Calibrated Score Bands'));
      expect(screen.getByText('Category Benchmark')).toBeTruthy();
      expect(screen.getByText('Score: 90 – 100')).toBeTruthy();
      expect(screen.getByText('Score: 0 – 49')).toBeTruthy();
    });

    it('calls onClose when close button or Escape is triggered', () => {
      let closed = false;
      const handleClose = () => { closed = true; };
      const { unmount } = render(<ScoringRubricModal isOpen={true} onClose={handleClose} />);

      // Click close button
      fireEvent.click(screen.getByText('Close Specification'));
      expect(closed).toBe(true);

      // Reset and test Escape
      closed = false;
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(closed).toBe(true);
      unmount();
    });
  });
});
