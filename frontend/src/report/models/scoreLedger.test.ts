import { describe, expect, it } from 'vitest';
import { buildAuthoritativeScore, gradeForScore, REPORT_PILLARS } from './scoreLedger';

describe('authoritative report score', () => {
  it('uses the ledger total when a measured citation rate is zero', () => {
    const score = buildAuthoritativeScore([
      { ...REPORT_PILLARS.technical, rawScore: 79.6, status: 'MEASURED' },
      { ...REPORT_PILLARS.geo, rawScore: 80, status: 'MEASURED' },
      { ...REPORT_PILLARS.aeo, rawScore: 0, status: 'LIVE_MEASURED' },
      { ...REPORT_PILLARS.cro, rawScore: 76.6, status: 'MEASURED' },
    ]);

    expect(score.composite).toBe(59.2);
    expect(score.grade).toBe('D');
    expect(gradeForScore(83)).not.toBe(score.grade);
    expect(score.rows.every((row) => row.included)).toBe(true);
    expect(score.rows.reduce((sum, row) => sum + row.weightPct, 0)).toBe(100);
  });

  it('drops an unmeasured pillar and rescales the remaining weights', () => {
    const score = buildAuthoritativeScore([
      { ...REPORT_PILLARS.technical, rawScore: 79.6, status: 'MEASURED' },
      { ...REPORT_PILLARS.geo, rawScore: 80, status: 'MEASURED' },
      { ...REPORT_PILLARS.aeo, rawScore: null, status: 'NOT_MEASURED' },
      { ...REPORT_PILLARS.cro, rawScore: 76.6, status: 'MEASURED' },
    ]);

    expect(score.composite).toBe(78.9);
    expect(score.grade).toBe('B');
    const aeo = score.rows.find((row) => row.categoryKey === 'AEO');
    expect(aeo?.included).toBe(false);
    expect(aeo?.nominalWeightPct).toBe(25);
    expect(score.rows.find((row) => row.categoryKey === 'TECHNICAL_SEO')?.weightPct).toBe(40);
    expect(score.rows.find((row) => row.categoryKey === 'TECHNICAL_SEO')?.nominalWeightPct).toBe(30);
    expect(score.partialCoverage).toBe(true);
    expect(score.coverageLabel).toBe('Partial-coverage composite');
    expect(score.excludedPillars).toContain('Live Answer-Engine Citations (AEO)');
    expect(score.rows.filter((row) => row.included).reduce((sum, row) => sum + row.weightPct, 0)).toBe(100);
  });
});
