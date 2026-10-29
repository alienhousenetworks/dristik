import { describe, expect, it } from 'vitest';
import { ExecutiveReport } from '../../types';
import { chapterVisuals } from './chapterSeries';

describe('chapterVisuals', () => {
  it('does not invent Core Web Vitals, citations, or a forecast series', () => {
    const visual = chapterVisuals({} as ExecutiveReport, '16');
    expect(visual.charts).toHaveLength(0);
    expect(visual.gap).toMatch(/not a Core Web Vital/i);
    const forecast = chapterVisuals({} as ExecutiveReport, '52');
    expect(forecast.charts).toHaveLength(0);
    expect(forecast.gap).toMatch(/No forecast chart is drawn/);
    const ai = chapterVisuals({ ai_visibility_scorecard: { successful_runs: 4, mention_rate_pct: 25, citation_rate_pct: null } } as ExecutiveReport, '47');
    expect(ai.charts[0]?.bars.map((bar) => bar.label)).toEqual(['Mention rate %']);
    expect(JSON.stringify(ai.charts)).not.toContain('83.3');
  });

  it('plots stored HTTP status and crawl response time', () => {
    const report = {
      crawl_manifest: {
        pages: [{ url: 'https://example.com', status_code: 200, ttfb_ms: 291.6, title: 'Example' }],
      },
    } as ExecutiveReport;
    const http = chapterVisuals(report, '07');
    expect(http.charts[0]?.bars).toEqual([{ label: 'HTTP 200', value: 1 }]);
    const timing = chapterVisuals(report, '14');
    expect(timing.charts.some((chart) => chart.title === 'Crawl response time (ms)' && chart.bars[0]?.value === 291.6)).toBe(true);
    expect(timing.charts.some((chart) => /Core Web Vital/i.test(chart.title))).toBe(false);
  });
});
