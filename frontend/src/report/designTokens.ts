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
    display: 'font-serif text-[38pt] md:text-[44pt] font-normal leading-[1.08] tracking-tight',
    displaySmall: 'font-serif text-[26pt] md:text-[30pt] font-normal leading-[1.12] tracking-tight',
    
    // Massive chapter numbering for section transitions
    chapterNumber: 'font-mono text-[64pt] md:text-[76pt] font-extralight leading-none tracking-tighter',
    
    // Editorial section headers
    sectionTitle: 'font-serif text-[20pt] md:text-[22pt] font-normal leading-snug tracking-tight',
    pageTitle: 'font-serif text-[15pt] md:text-[17pt] font-medium leading-snug tracking-tight',
    
    // Subheadings and architectural kickers
    subheading: 'font-sans text-[10.5pt] font-semibold uppercase tracking-wider',
    kicker: 'font-mono text-[8pt] font-bold uppercase tracking-[0.18em]',
    
    // Body text (optimized for sustained readability in print)
    body: 'font-sans text-[9.5pt] font-normal leading-[1.52] text-slate-800',
    bodyLead: 'font-serif text-[12pt] font-normal leading-[1.58] text-slate-900',
    bodySmall: 'font-sans text-[8.5pt] font-normal leading-[1.46] text-slate-600',
    
    // Metadata, footnotes, and captions
    caption: 'font-sans text-[7.5pt] font-medium text-slate-500 tracking-wide',
    
    // High-impact numerical metrics
    metricHero: 'font-serif text-[44pt] md:text-[52pt] font-light leading-none tracking-tight',
    metricMedium: 'font-mono text-[22pt] md:text-[26pt] font-bold tracking-tight',
    metricSmall: 'font-mono text-[14pt] font-bold tracking-tight',
    
    // Data tables & technical appendix
    tableHeader: 'font-sans text-[8pt] font-bold uppercase tracking-wider text-slate-700',
    tableCell: 'font-sans text-[8.5pt] leading-normal text-slate-800',
    
    // Cryptographic hashes, DOM selectors, code patches
    mono: 'font-mono text-[8pt] leading-tight text-slate-700',
    monoSmall: 'font-mono text-[7pt] leading-tight text-slate-600',
  },

  evidenceStatus: {
    directly_observed: {
      code: 'DIRECTLY_OBSERVED',
      label: 'Directly Observed in DOM',
      badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-300',
      dotColor: '#059669',
      symbol: '●',
    },
    calculated: {
      code: 'CALCULATED',
      label: 'Calculated from Sample',
      badgeClass: 'bg-sky-50 text-sky-800 border-sky-300',
      dotColor: '#0284c7',
      symbol: '▲',
    },
    model_derived: {
      code: 'MODEL_DERIVED',
      label: 'Model-Derived Grounding',
      badgeClass: 'bg-purple-50 text-purple-800 border-purple-300',
      dotColor: '#7c3aed',
      symbol: '◆',
    },
    insufficient_evidence: {
      code: 'INSUFFICIENT_EVIDENCE',
      label: 'Insufficient Evidence',
      badgeClass: 'bg-slate-50 text-slate-600 border-slate-300',
      dotColor: '#64748b',
      symbol: '○',
    },
  },

  rules: {
    hairline: 'border-b border-slate-200',
    editorial: 'border-b border-slate-900',
    double: 'border-b-2 border-slate-900',
    subtle: 'border border-slate-200',
    card: 'border border-slate-200/90 bg-white',
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
