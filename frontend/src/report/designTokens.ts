/**
 * Dristik Report Design Token System (Single Source of Truth)
 * 
 * Defines all geometric, typographic, spatial, and semantic parameters
 * for the A4 editorial intelligence publication.
 */

import { ReportTheme } from './brandTheme';

export const DESIGN_TOKENS = {
  page: {
    format: 'A4',
    widthMm: 210,
    heightMm: 297,
    marginMm: {
      top: 12,
      right: 14,
      bottom: 14,
      left: 14,
    },
    columns: 12,
    gutterMm: 4,
  },

  typography: {
    // Large editorial display titles (Chapter openers, cover, major thesis)
    display: 'font-serif text-[28pt] md:text-[32pt] font-normal leading-[1.12] tracking-tight text-ink',
    displaySmall: 'font-serif text-[22pt] md:text-[24pt] font-normal leading-[1.16] tracking-tight text-ink',
    
    chapterNumber: 'font-mono text-[14pt] font-semibold leading-none tracking-normal text-ink',
    
    sectionTitle: 'font-serif text-[18pt] md:text-[20pt] font-normal leading-snug tracking-tight text-ink',
    pageTitle: 'font-sans text-[14pt] md:text-[15pt] font-semibold leading-snug tracking-tight text-ink',
    
    subheading: 'font-sans text-[10.5pt] font-semibold text-ink',
    kicker: 'font-mono text-[8pt] font-medium tracking-[0.04em] text-ink-500',
    
    body: 'font-sans text-[9.5pt] font-normal leading-[1.52] text-ink-700',
    bodyLead: 'font-sans text-[12pt] font-normal leading-[1.58] text-ink',
    bodySmall: 'font-sans text-[8.5pt] font-normal leading-[1.46] text-ink-500',
    
    caption: 'font-sans text-[7.5pt] font-medium text-ink-500',
    
    metricHero: 'font-mono text-[32pt] md:text-[36pt] font-semibold leading-none tracking-tight text-ink',
    metricMedium: 'font-mono text-[18pt] md:text-[20pt] font-semibold tracking-tight text-ink',
    metricSmall: 'font-mono text-[13pt] font-semibold tracking-tight text-ink',
    
    tableHeader: 'font-sans text-[8pt] font-semibold text-ink-600',
    tableCell: 'font-sans text-[8.5pt] leading-normal text-ink-700',
    
    mono: 'font-mono text-[8pt] leading-tight text-ink-700',
    monoSmall: 'font-mono text-[7pt] leading-tight text-ink-500',
  },

  evidenceStatus: {
    directly_observed: {
      code: 'DIRECTLY_OBSERVED',
      label: 'Directly Observed in DOM',
      badgeClass: 'bg-paper-100 text-ink-700 border-line',
      dotColor: '#171a20',
      symbol: '●',
    },
    calculated: {
      code: 'CALCULATED',
      label: 'Calculated from Sample',
      badgeClass: 'bg-paper-100 text-ink-700 border-line',
      dotColor: '#5c6570',
      symbol: '▲',
    },
    model_derived: {
      code: 'MODEL_DERIVED',
      label: 'Model-Derived Grounding',
      badgeClass: 'bg-paper-100 text-ink-700 border-line',
      dotColor: '#5c6570',
      symbol: '◆',
    },
    insufficient_evidence: {
      code: 'INSUFFICIENT_EVIDENCE',
      label: 'Insufficient Evidence',
      badgeClass: 'bg-warn/10 text-warn border-warn/30',
      dotColor: '#925a08',
      symbol: '○',
    },
  },

  rules: {
    hairline: 'border-b border-line',
    editorial: 'border-b border-ink',
    double: 'border-b-2 border-ink',
    subtle: 'border border-line',
    card: 'border border-line bg-paper-50',
  },
} as const;

/**
 * Creates dynamic CSS styles from a resolved ReportTheme.
 */
export function createDynamicThemeStyles(theme: ReportTheme) {
  return {
    accentText: { color: theme.accent },
    accentDarkText: { color: theme.accentDark },
    accentBg: { backgroundColor: theme.accent },
    accentTintBg: { backgroundColor: theme.accentTint },
    accentBorder: { borderColor: theme.accent },
    accentRule: { borderBottomColor: theme.accent },
  };
}
