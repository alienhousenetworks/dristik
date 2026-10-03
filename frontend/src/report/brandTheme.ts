/**
 * Pure, testable Brand Theme Pipeline for Dristik Editorial Reports.
 * 
 * Extracts, validates, contrast-calibrates (WCAG AA 4.5:1), and maps
 * client brand identity into an accessible ReportTheme.
 * 
 * Strict rule: Client brand colors NEVER replace Dristik semantic severity tokens.
 */

export interface ReportTheme {
  // Client-influenced contextual tokens
  accent: string;        // WCAG AA 4.5:1 compliant on white
  accentDark: string;    // Deep tone (7:1+ contrast) for fine text/kicks
  accentTint: string;    // 6-8% light tint on white for chapter openers/callouts
  chartAccent: string;   // High-clarity chart stroke/fill
  highlight: string;     // Subdued accent for metadata badges
  isClientThemed: boolean;
  rawExtractedColor?: string;

  // Dristik analyst & publisher tokens (Fixed)
  dristik: {
    publisherNavy: string;
    publisherSlate: string;
    publisherInk: string;
    publisherPaper: string;
    publisherLine: string;
  };

  // Semantic severity tokens (Fixed Dristik tokens - never overridden)
  semantic: {
    critical: string;
    criticalBg: string;
    warning: string;
    warningBg: string;
    positive: string;
    positiveBg: string;
    neutral: string;
    neutralBg: string;
  };
}

export const DRISTIK_DEFAULT_ACCENT = '#0d9488'; // Dristik signature teal

export const FIXED_DRISTIK_TOKENS = {
  dristik: {
    publisherNavy: '#0f172a',
    publisherSlate: '#334155',
    publisherInk: '#0b0f19',
    publisherPaper: '#f8fafc',
    publisherLine: '#e2e8f0',
  },
  semantic: {
    critical: '#dc2626',
    criticalBg: '#fef2f2',
    warning: '#d97706',
    warningBg: '#fffbeb',
    positive: '#059669',
    positiveBg: '#ecfdf5',
    neutral: '#64748b',
    neutralBg: '#f1f5f9',
  },
};

// ============================================================================
// COLOR UTILITIES: HSL, RGB, Luminance & Contrast
// ============================================================================

export interface HSL {
  h: number; // 0-360
  s: number; // 0-1
  l: number; // 0-1
}

export interface RGB {
  r: number; // 0-255
  g: number; // 0-255
  b: number; // 0-255
}

export function parseHexToRgb(hex: string): RGB | null {
  let clean = hex.trim().replace(/^#/, '');
  if (clean.length === 3) {
    clean = clean.split('').map((c) => c + c).join('');
  }
  if (clean.length !== 6) return null;
  const num = parseInt(clean, 16);
  if (isNaN(num)) return null;
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

export function rgbToHex(rgb: RGB): string {
  const toHex = (n: number) => {
    const clamped = Math.max(0, Math.min(255, Math.round(n)));
    return clamped.toString(16).padStart(2, '0');
  };
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
}

export function rgbToHsl(rgb: RGB): HSL {
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h = h * 60;
  }

  return { h, s, l };
}

export function hslToRgb(hsl: HSL): RGB {
  const { h, s, l } = hsl;
  if (s === 0) {
    const val = Math.round(l * 255);
    return { r: val, g: val, b: val };
  }

  const hue2rgb = (p: number, q: number, t: number) => {
    let normalized = t;
    if (normalized < 0) normalized += 1;
    if (normalized > 1) normalized -= 1;
    if (normalized < 1 / 6) return p + (q - p) * 6 * normalized;
    if (normalized < 1 / 2) return q;
    if (normalized < 2 / 3) return p + (q - p) * (2 / 3 - normalized) * 6;
    return p;
  };

  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const normH = h / 360;

  return {
    r: Math.round(hue2rgb(p, q, normH + 1 / 3) * 255),
    g: Math.round(hue2rgb(p, q, normH) * 255),
    b: Math.round(hue2rgb(p, q, normH - 1 / 3) * 255),
  };
}

/**
 * Calculates WCAG 2.1 relative luminance for an sRGB color.
 */
export function relativeLuminance(rgb: RGB): number {
  const transform = (val: number) => {
    const s = val / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * transform(rgb.r) + 0.7152 * transform(rgb.g) + 0.0722 * transform(rgb.b);
}

/**
 * Calculates WCAG contrast ratio between two colors (range: 1 to 21).
 */
export function contrastRatio(rgb1: RGB, rgb2: RGB): number {
  const lum1 = relativeLuminance(rgb1);
  const lum2 = relativeLuminance(rgb2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

// ============================================================================
// VALIDATION & CONTRAST TUNING PIPELINE
// ============================================================================

/**
 * Validates whether a candidate hex color is suitable for editorial branding.
 * Discards near-white, near-black, and washed-out grays.
 * Caps saturation for neon colors to maintain editorial authority.
 */
export function validateAndCalibrateColor(rawHex?: string | null): HSL | null {
  if (!rawHex) return null;
  const rgb = parseHexToRgb(rawHex);
  if (!rgb) return null;

  const hsl = rgbToHsl(rgb);

  // 1. Discard near-white (lightness > 0.92) or near-black (lightness < 0.08)
  if (hsl.l > 0.92 || hsl.l < 0.08) {
    return null;
  }

  // 2. Discard washed-out grays (saturation < 0.12)
  if (hsl.s < 0.12) {
    return null;
  }

  // 3. Cap neon colors (saturation > 0.82) to avoid blinding editorial contrast
  const cappedSaturation = hsl.s > 0.82 ? 0.76 : hsl.s;

  return {
    h: hsl.h,
    s: cappedSaturation,
    l: hsl.l,
  };
}

/**
 * Adjusts lightness of the brand color until it strictly satisfies WCAG AA (4.5:1)
 * contrast against the given background (defaults to white #ffffff),
 * preserving the brand's exact hue.
 */
export function enforceWcagContrast(
  hsl: HSL,
  targetContrast = 4.5,
  surfaceRgb: RGB = { r: 255, g: 255, b: 255 }
): HSL {
  let currentHsl = { ...hsl };
  let currentRgb = hslToRgb(currentHsl);
  let ratio = contrastRatio(currentRgb, surfaceRgb);

  if (ratio >= targetContrast) {
    return currentHsl;
  }

  // Since paper is white, we reduce lightness (step down) while keeping hue & saturation
  while (ratio < targetContrast && currentHsl.l > 0.12) {
    currentHsl.l = Math.max(0.12, currentHsl.l - 0.02);
    currentRgb = hslToRgb(currentHsl);
    ratio = contrastRatio(currentRgb, surfaceRgb);
  }

  return currentHsl;
}

// ============================================================================
// BRAND THEME BUILDER & EXTRACTION
// ============================================================================

export interface ColorExtractionInput {
  metaThemeColor?: string | null;
  cssPrimaryVar?: string | null;
  logoExtractedColor?: string | null;
  manifestBrandColor?: string | null;
  fallbackColor?: string;
}

/**
 * Creates an accessible, contrast-validated ReportTheme.
 */
export function buildReportTheme(candidateHex?: string | null): ReportTheme {
  const calibratedHsl = validateAndCalibrateColor(candidateHex);

  if (!calibratedHsl) {
    // Graceful fallback: Dristik signature teal
    const fallbackHsl = rgbToHsl(parseHexToRgb(DRISTIK_DEFAULT_ACCENT)!);
    const aaHsl = enforceWcagContrast(fallbackHsl, 4.5);
    const accentHex = rgbToHex(hslToRgb(aaHsl));
    const darkHex = rgbToHex(hslToRgb({ ...aaHsl, l: Math.max(0.15, aaHsl.l - 0.15) }));
    const tintRgb = hslToRgb({ ...aaHsl, s: Math.min(0.4, aaHsl.s), l: 0.96 });

    return {
      accent: accentHex,
      accentDark: darkHex,
      accentTint: rgbToHex(tintRgb),
      chartAccent: accentHex,
      highlight: rgbToHex(hslToRgb({ ...aaHsl, l: 0.88 })),
      isClientThemed: false,
      ...FIXED_DRISTIK_TOKENS,
    };
  }

  // 1. Accent: Tuned to pass WCAG AA (4.5:1)
  const aaHsl = enforceWcagContrast(calibratedHsl, 4.5);
  const accentHex = rgbToHex(hslToRgb(aaHsl));

  // 2. AccentDark: Deep high-contrast tone (7:1+) for small text and kickers
  const darkHsl = enforceWcagContrast(calibratedHsl, 7.0);
  const darkHex = rgbToHex(hslToRgb(darkHsl));

  // 3. AccentTint: 6-8% wash on white (high lightness ~96%, softened saturation)
  const tintHsl: HSL = {
    h: calibratedHsl.h,
    s: Math.min(0.35, calibratedHsl.s),
    l: 0.965,
  };
  const tintHex = rgbToHex(hslToRgb(tintHsl));

  // 4. ChartAccent: Pure hue calibrated for visual clarity
  const chartHsl: HSL = {
    h: calibratedHsl.h,
    s: Math.max(0.65, calibratedHsl.s),
    l: Math.min(0.45, Math.max(0.32, aaHsl.l)),
  };
  const chartHex = rgbToHex(hslToRgb(chartHsl));

  // 5. Highlight: Soft pill/badge background
  const highlightHsl: HSL = {
    h: calibratedHsl.h,
    s: Math.min(0.4, calibratedHsl.s),
    l: 0.91,
  };
  const highlightHex = rgbToHex(hslToRgb(highlightHsl));

  return {
    accent: accentHex,
    accentDark: darkHex,
    accentTint: tintHex,
    chartAccent: chartHex,
    highlight: highlightHex,
    isClientThemed: true,
    rawExtractedColor: candidateHex || undefined,
    ...FIXED_DRISTIK_TOKENS,
  };
}

/**
 * Extracts candidate color from multiple crawled surfaces with priority.
 */
export function extractBrandColorFromManifest(input: ColorExtractionInput): string | null {
  return (
    input.metaThemeColor ||
    input.cssPrimaryVar ||
    input.manifestBrandColor ||
    input.logoExtractedColor ||
    input.fallbackColor ||
    null
  );
}
