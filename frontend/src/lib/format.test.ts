import { describe, expect, it } from 'vitest';
import { categoryLabel, display, formatPercent, scoreTone, severityTone } from './format';

describe('format', () => {
  it('hides unknown placeholders', () => {
    expect(display('unknown')).toBe('—');
    expect(display('  Acme  ')).toBe('Acme');
  });

  it('labels known categories and falls back', () => {
    expect(categoryLabel('TECHNICAL_SEO')).toBe('Technical SEO');
    expect(categoryLabel('CUSTOM_CASE')).toBe('custom case');
  });

  it('maps severity and score to tones', () => {
    expect(severityTone('HIGH')).toBe('text-bad');
    expect(severityTone('MEDIUM')).toBe('text-warn');
    expect(scoreTone(90)).toBe('text-good');
    expect(scoreTone(40)).toBe('text-bad');
  });

  it('formats ratios and percents', () => {
    expect(formatPercent(0.42)).toBe('42%');
    expect(formatPercent(81)).toBe('81%');
    expect(formatPercent(null)).toBe('—');
  });
});
