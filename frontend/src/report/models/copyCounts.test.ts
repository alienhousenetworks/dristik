import { describe, expect, it } from 'vitest';
import { countWords } from './copyCounts';

describe('displayed word counts', () => {
  it('counts the headline that is shown, not the headline plus the subhead', () => {
    const headline = 'The Definitive Digital Solutions & Services for High-Growth Enterprises';
    expect(countWords(headline)).toBe(9);
    expect(countWords(`${headline} ${'extra '.repeat(37)}`)).toBe(46);
  });
});
