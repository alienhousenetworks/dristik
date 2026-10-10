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
    expect(live.brandMentionedCount).toBe(4);
    expect(live.brandCitedCount).toBe(0);
    expect(live.liveCitationRatePct).toBe(0);
    const claude = live.engineDetails.find((row) => row.engine.startsWith('Claude'));
    const others = live.engineDetails.filter((row) => !row.engine.startsWith('Claude'));
    expect(claude?.queriesExecuted).toBe(20);
    expect(others.every((row) => row.status === 'NOT_EXECUTED')).toBe(true);
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
