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

    expect(score.composite).toBe(52.4);
    expect(score.grade).toBe('D');
    expect(score.rows.find((row) => row.categoryKey === 'GEO')?.rawScore).toBe(52.7);
    expect(score.rows.find((row) => row.categoryKey === 'AEO')?.rawScore).toBe(0);
  });
});
