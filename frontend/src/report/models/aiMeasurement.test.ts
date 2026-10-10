import { describe, expect, it } from 'vitest';
import { answerabilityConfidence, buildLiveObservation } from './aiMeasurement';

describe('live AI versus on-page answerability', () => {
  it('does not invent Claude query counts when no engine ran', () => {
    const live = buildLiveObservation(null);
    expect(live.isMeasured).toBe(false);
    expect(live.queriesExecuted).toBe(0);
    expect(live.brandMentionedCount).toBe(0);
    expect(live.brandCitedCount).toBe(0);
    expect(live.liveCitationRatePct).toBeNull();
    expect(live.engineDetails.every((row) => row.status === 'NOT_EXECUTED')).toBe(true);
  });

  it('counts only the observatory records that actually ran', () => {
    const live = buildLiveObservation({
      status: 'MEASURED',
      queries: 100,
      observatory_records: Array.from({ length: 20 }, (_, index) => ({
        engine_id: 'claude',
        brand_mentioned: index < 4,
        brand_cited: false,
      })),
    });
    expect(live.queriesExecuted).toBe(20);
    expect(live.queriesAttempted).toBe(100);
    expect(live.brandMentionedCount).toBe(4);
    expect(live.brandCitedCount).toBe(0);
    expect(live.liveCitationRatePct).toBe(0);
    const claude = live.engineDetails.find((row) => row.engine.startsWith('Claude'));
    const others = live.engineDetails.filter((row) => !row.engine.startsWith('Claude'));
    expect(claude?.queriesExecuted).toBe(20);
    expect(others.every((row) => row.status === 'NOT_EXECUTED')).toBe(true);
  });

  it('does not treat an attempted budget as completed queries', () => {
    const live = buildLiveObservation({
      status: 'NOT_MEASURED',
      queries: 18,
      failed_runs: 18,
      successful_runs: 0,
      engines_measured: 0,
      observatory_records: [],
    });
    expect(live.isMeasured).toBe(false);
    expect(live.queriesExecuted).toBe(0);
    expect(live.queriesAttempted).toBe(18);
    expect(live.queriesFailed).toBe(18);
    expect(live.liveCitationRatePct).toBeNull();
    expect(live.engineDetails.every((row) => row.status === 'NOT_EXECUTED')).toBe(true);
  });

  it('keeps an engine response that does not match the five named labels', () => {
    const live = buildLiveObservation({
      status: 'MEASURED',
      queries: 2,
      observatory_records: [{ engine_id: 'copilot', engine_name: 'Bing Copilot', brand_mentioned: true, brand_cited: false }],
    });
    const copilot = live.engineDetails.find((row) => row.engine === 'Bing Copilot');
    expect(copilot?.queriesExecuted).toBe(1);
    expect(copilot?.status).toBe('MEASURED');
    expect(live.queriesExecuted).toBe(1);
  });

  it('omits confidence when a question has no supporting passage', () => {
    const judged = answerabilityConfidence({
      answerabilityStatus: 'ANSWERABLE',
      citabilityScore: 0,
    });
    expect(judged.confidencePct).toBeNull();
    expect(judged.confidenceBasis).toMatch(/No supporting passage/);
  });
});
