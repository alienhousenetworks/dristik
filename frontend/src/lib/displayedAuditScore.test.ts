import { describe, it, expect } from 'vitest';
import { buildDisplayedScore } from './displayedAuditScore';
import { ExecutiveReport } from '../types';

describe('buildDisplayedScore', () => {
  it('shows the dossier composite when GEO was stored as 100 and overall as 83', () => {
    const score = buildDisplayedScore({
      scores: {
        overall_score: 83,
        category_scores: {
          GEO: { score: 100, status: 'MEASURED', weight: 20, weighted_score: 20, summary: '' },
        },
      },
      honest_scores: {
        google_score: 79.6,
        ai_readiness_score: 80,
        human_score: 76.6,
        live_ai_citation_score: 0,
        ai_visibility_status: 'MEASURED',
        ai_visibility_score: 0,
      },
      geo_readiness: { extractability_score: 52.7 },
    } as unknown as ExecutiveReport);

    expect(score.composite).toBe(69.8);
    expect(score.grade).toBe('C');
    expect(score.rows.find((row) => row.categoryKey === 'GEO')?.rawScore).toBe(52.7);
    expect(score.rows.find((row) => row.categoryKey === 'AEO')?.included).toBe(false);
  });

  it('keeps a live citation of zero when an engine on this run responded', () => {
    const score = buildDisplayedScore({
      scores: { overall_score: 83 },
      honest_scores: {
        google_score: 79.6,
        human_score: 76.6,
        live_ai_citation_score: 0,
        ai_visibility_status: 'MEASURED',
      },
      geo_readiness: { extractability_score: 52.7 },
      ai_visibility_scorecard: {
        status: 'MEASURED',
        queries: 18,
        successful_runs: 4,
        failed_runs: 14,
        engines_measured: 1,
        engines_requested: 5,
        repeats: 1,
        citation_rate_pct: 0,
        observatory_records: [{ engine_id: 'claude', brand_mentioned: false, brand_cited: false }],
      },
    } as unknown as ExecutiveReport);

    expect(score.composite).toBe(52.4);
    expect(score.grade).toBe('D');
    expect(score.rows.find((row) => row.categoryKey === 'AEO')?.rawScore).toBe(0);
  });

  it('uses canonical_scorecard verbatim when present so UI matches API and PDFs', () => {
    const score = buildDisplayedScore({
      scores: { overall_score: 91.5 },
      honest_scores: { google_score: 95, ai_readiness_score: 90, human_score: 88 },
      canonical_scorecard: {
        methodology_version: 'dristik_enterprise_v4.0',
        audit_run_id: 'run_parity_001',
        domain: 'example.com',
        composite_health_score: 68.0,
        composite_grade: 'C',
        capability_completeness_score: 52.0,
        evidence_coverage_score: 20.0,
        optimization_effectiveness_score: null,
        crawl_coverage: {
          discovered_urls: 120,
          crawled_urls: 5,
          rendered_urls: 5,
          inspected_urls: 5,
          tested_urls: 0,
        },
        pillars: {
          SEO: { pillar: 'SEO', pillar_weight: 25, capability_completeness_score: 70, evidence_coverage_score: 20, measured_health_score: 74.0, status: 'MEASURED' },
          GEO: { pillar: 'GEO', pillar_weight: 25, capability_completeness_score: 60, evidence_coverage_score: 20, measured_health_score: 62.0, status: 'MEASURED' },
          AEO: { pillar: 'AEO', pillar_weight: 25, capability_completeness_score: 0, evidence_coverage_score: 0, measured_health_score: null, status: 'UNMEASURED' },
          CRO: { pillar: 'CRO', pillar_weight: 25, capability_completeness_score: 50, evidence_coverage_score: 20, measured_health_score: 68.0, status: 'MEASURED' },
        },
      },
    } as unknown as ExecutiveReport);

    expect(score.composite).toBe(68.0);
    expect(score.grade).toBe('C');
    expect(score.formula).toBe('dristik_enterprise_v4.0');
    expect(score.rows.find((row) => row.categoryKey === 'TECHNICAL_SEO')?.rawScore).toBe(74.0);
    expect(score.rows.find((row) => row.categoryKey === 'GEO')?.rawScore).toBe(62.0);
    expect(score.rows.find((row) => row.categoryKey === 'AEO')?.included).toBe(false);
    expect(score.rows.find((row) => row.categoryKey === 'UX_CONVERSION')?.rawScore).toBe(68.0);
  });
});
