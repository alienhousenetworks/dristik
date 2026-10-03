import { describe, it, expect } from 'vitest';
import {
  buildReportTheme,
  parseHexToRgb,
  contrastRatio,
  validateAndCalibrateColor,
  FIXED_DRISTIK_TOKENS,
} from './brandTheme';

describe('BrandTheme Pipeline', () => {
  const whiteRgb = { r: 255, g: 255, b: 255 };

  it('adjusts bright neon yellow to pass WCAG AA (>= 4.5:1)', () => {
    const neonYellow = '#ffff00';
    const theme = buildReportTheme(neonYellow);

    const rgb = parseHexToRgb(theme.accent);
    expect(rgb).not.toBeNull();
    const ratio = contrastRatio(rgb!, whiteRgb);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
    expect(theme.isClientThemed).toBe(true);
  });

  it('adjusts bright neon lime to pass WCAG AA', () => {
    const neonLime = '#00ff44';
    const theme = buildReportTheme(neonLime);

    const rgb = parseHexToRgb(theme.accent);
    expect(rgb).not.toBeNull();
    const ratio = contrastRatio(rgb!, whiteRgb);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it('adjusts dark brand color safely', () => {
    const deepBlue = '#0a192f';
    const theme = buildReportTheme(deepBlue);

    const rgb = parseHexToRgb(theme.accent);
    expect(rgb).not.toBeNull();
    const ratio = contrastRatio(rgb!, whiteRgb);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it('adjusts low-contrast pastel color to meet AA threshold', () => {
    const pastelPink = '#ffb3ba';
    const theme = buildReportTheme(pastelPink);

    const rgb = parseHexToRgb(theme.accent);
    expect(rgb).not.toBeNull();
    const ratio = contrastRatio(rgb!, whiteRgb);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it('falls back to Dristik signature teal for invalid or washed-out input without failing', () => {
    const pureWhite = '#ffffff';
    const washedGray = '#888888';

    const themeWhite = buildReportTheme(pureWhite);
    expect(themeWhite.isClientThemed).toBe(false);
    expect(contrastRatio(parseHexToRgb(themeWhite.accent)!, whiteRgb)).toBeGreaterThanOrEqual(4.5);

    const themeGray = buildReportTheme(washedGray);
    expect(themeGray.isClientThemed).toBe(false);
  });

  it('preserves immutable Dristik semantic severity tokens', () => {
    const brandNeonOrange = '#ff6600';
    const theme = buildReportTheme(brandNeonOrange);

    expect(theme.semantic.critical).toBe(FIXED_DRISTIK_TOKENS.semantic.critical);
    expect(theme.semantic.warning).toBe(FIXED_DRISTIK_TOKENS.semantic.warning);
    expect(theme.semantic.positive).toBe(FIXED_DRISTIK_TOKENS.semantic.positive);
    expect(theme.semantic.neutral).toBe(FIXED_DRISTIK_TOKENS.semantic.neutral);
  });

  it('guarantees accentDark achieves high contrast (>= 7.0:1)', () => {
    const themes = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'].map(buildReportTheme);
    for (const theme of themes) {
      const darkRgb = parseHexToRgb(theme.accentDark);
      expect(darkRgb).not.toBeNull();
      expect(contrastRatio(darkRgb!, whiteRgb)).toBeGreaterThanOrEqual(6.8);
    }
  });
});
