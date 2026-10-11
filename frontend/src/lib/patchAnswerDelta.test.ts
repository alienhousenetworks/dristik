import { describe, expect, it } from 'vitest';
import { answersUnchanged, effectiveAfterScore, effectiveCitationGain } from './patchAnswerDelta';

describe('patch answer delta', () => {
  it('does not raise a score when the after answer still cannot determine', () => {
    const item = {
      before_score: 1,
      after_score: 5,
      before_answer: 'Cannot determine from crawled site evidence.',
      after_answer: 'Cannot determine from crawled site evidence, as pricing information is not available.',
      patch_citation_gain: 0.4,
    };
    expect(answersUnchanged(item.before_answer, item.after_answer)).toBe(true);
    expect(effectiveAfterScore(item)).toBe(1);
    expect(effectiveCitationGain(item)).toBeNull();
  });

  it('does not treat the current meta description as a new patch fact', () => {
    const before = 'AlienHouse Networks is a professionally managed technology solutions company delivering secure, scalable, and high-performance digital systems for enterprises.';
    const after = `${before}, as stated in their meta description [EV_004].`;
    expect(answersUnchanged(before, after)).toBe(true);
    expect(answersUnchanged(
      'Cannot determine from crawled site evidence.',
      "AlienHouse Networks' product is built for enterprises, as stated in their meta description [EV_004].",
    )).toBe(true);
  });

  it('keeps a score increase when the after answer states a new fact', () => {
    const item = {
      before_score: 3,
      after_score: 8,
      before_answer: 'Pricing is not mentioned on the site.',
      after_answer: 'Pricing starts at $49/mo for standard teams.',
      patch_citation_gain: 0.5,
    };
    expect(answersUnchanged(item.before_answer, item.after_answer)).toBe(false);
    expect(effectiveAfterScore(item)).toBe(8);
    expect(effectiveCitationGain(item)).toBe(0.5);
  });
});
