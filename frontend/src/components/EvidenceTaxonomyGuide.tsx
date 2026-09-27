import React, { useState } from 'react';
import { EvidenceClass, EvidenceTaxonomyReport, Finding } from '../types';

interface EvidenceTaxonomyGuideProps {
  taxonomyReport?: EvidenceTaxonomyReport;
  findings?: Finding[];
  selectedClass?: EvidenceClass | 'ALL';
  onSelectClass?: (evClass: EvidenceClass | 'ALL') => void;
  compact?: boolean;
}

const DEFAULT_TAXONOMY_SPECS: Record<
  EvidenceClass,
  {
    label: string;
    title: string;
    level: string;
    description: string;
    badgeStyle: string;
    activeBorder: string;
    subtypes: string[];
    sampleEvidence: string;
  }
> = {
  OBSERVED: {
    label: 'OBSERVED',
    title: 'Directly Measured',
    level: 'Level 1 · Deterministic Ground Truth',
    description:
      'Directly measured from browser runtime, response headers, or DOM/AST syntax trees. 100% checkable via browser DevTools or curl.',
    badgeStyle: 'bg-emerald-100 text-emerald-950 border-emerald-400 dark:bg-emerald-950/80 dark:text-emerald-200 dark:border-emerald-600',
    activeBorder: 'border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/30',
    subtypes: ['DOM', 'HTTP', 'AST', 'Headers', 'Screenshot', 'Accessibility tree', 'Schema'],
    sampleEvidence: '[ev_001] DOM selector: h1:nth-of-type(1) -> "BEYOND IMAGINATION"',
  },
  EXTERNALLY_VERIFIED: {
    label: 'EXTERNALLY VERIFIED',
    title: 'Confirmed External Source',
    level: 'Level 2 · Corroborated External Signal',
    description:
      'Confirmed through an external authoritative source: live search engines, corporate registries, certificate authorities, or GSC.',
    badgeStyle: 'bg-sky-100 text-sky-950 border-sky-400 dark:bg-sky-950/80 dark:text-sky-200 dark:border-sky-600',
    activeBorder: 'border-sky-500 bg-sky-50/40 dark:bg-sky-950/30',
    subtypes: ['Search', 'Business directory', 'Company profile', 'Certificate registry', 'GSC', 'Analytics'],
    sampleEvidence: '[ext_gsc_01] Google Search Console API -> 4 URLs not indexed',
  },
  MODEL_INFERRED: {
    label: 'MODEL-INFERRED',
    title: 'LLM Interpretation',
    level: 'Level 3 · Cognitive Model Deduction',
    description:
      'LLM interpretation of observed evidence. Synthesized by neural language models based on semantic patterns, market psychology, and clarity.',
    badgeStyle: 'bg-purple-100 text-purple-950 border-purple-400 dark:bg-purple-950/80 dark:text-purple-200 dark:border-purple-600',
    activeBorder: 'border-purple-500 bg-purple-50/40 dark:bg-purple-950/30',
    subtypes: ['Semantic synthesis', 'Cognitive reasoning', 'Entity extraction'],
    sampleEvidence: '[inf_009] Value proposition communicates technical agency rather than SaaS product',
  },
  HYPOTHESIS: {
    label: 'HYPOTHESIS',
    title: 'Potential Issue (Needs Verification)',
    level: 'Level 4 · Working Hypothesis / Single-Source',
    description:
      'Potential issue requiring verification. Observed from a single crawl or heuristic signal without external corroboration.',
    badgeStyle: 'bg-amber-100 text-amber-950 border-amber-400 dark:bg-amber-950/80 dark:text-amber-200 dark:border-amber-600',
    activeBorder: 'border-amber-500 bg-amber-50/40 dark:bg-amber-950/30',
    subtypes: ['Single-source unverified', 'Working hypothesis', 'Unverified anomaly'],
    sampleEvidence: '[hyp_003] SINGLE-SOURCE UNVERIFIED: Tokyo edge node latency spike',
  },
  RECOMMENDATION: {
    label: 'RECOMMENDATION',
    title: 'Proposed Remediation',
    level: 'Level 5 · Actionable Engineering Intervention',
    description:
      'Proposed remediation. Concrete code diff, configuration adjustment, or strategic copywriting directive to eliminate the defect.',
    badgeStyle: 'bg-indigo-100 text-indigo-950 border-indigo-400 dark:bg-indigo-950/80 dark:text-indigo-200 dark:border-indigo-600',
    activeBorder: 'border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/30',
    subtypes: ['Code patch', 'Config change', 'Content rewrite', 'Strategic directive'],
    sampleEvidence: '[rec_005] Code Patch: Inject Service JSON-LD script into <head>',
  },
};

const ORDERED_CLASSES: EvidenceClass[] = [
  'OBSERVED',
  'EXTERNALLY_VERIFIED',
  'MODEL_INFERRED',
  'HYPOTHESIS',
  'RECOMMENDATION',
];

export function EvidenceTaxonomyGuide({
  taxonomyReport,
  findings = [],
  selectedClass = 'ALL',
  onSelectClass,
  compact = false,
}: EvidenceTaxonomyGuideProps) {
  const [activeInfoClass, setActiveInfoClass] = useState<EvidenceClass | null>(null);

  // Compute live counts if taxonomy report is omitted
  const counts = React.useMemo(() => {
    if (taxonomyReport?.class_counts) {
      return taxonomyReport.class_counts;
    }
    const c: Record<string, number> = {
      OBSERVED: 0,
      EXTERNALLY_VERIFIED: 0,
      MODEL_INFERRED: 0,
      HYPOTHESIS: 0,
      RECOMMENDATION: 0,
    };
    findings.forEach((f) => {
      const cls = f.evidence_class || 'OBSERVED';
      c[cls] = (c[cls] || 0) + 1;
    });
    return c;
  }, [taxonomyReport, findings]);

  const total = Object.values(counts).reduce((a, b) => a + b, 0) || findings.length || 1;
  const observedAndVerified = (counts.OBSERVED || 0) + (counts.EXTERNALLY_VERIFIED || 0);
  const integrityScore = taxonomyReport?.epistemic_integrity_score ?? Math.round((observedAndVerified / total) * 100);

  return (
    <div className="bg-paper-50 dark:bg-ink-950 border border-line rounded-xl p-5 shadow-xs space-y-5">
      {/* Header & Epistemic Score */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line/60 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-ink text-paper-50">
              Taxonomy Architecture
            </span>
            <h3 className="font-serif text-lg font-bold text-ink">
              Explicit Evidence Taxonomy &amp; Epistemic Hierarchy
            </h3>
          </div>
          <p className="text-xs text-ink-600 dark:text-ink-400 mt-1 max-w-2xl leading-relaxed">
            Dristik strictly separates empirical physical measurements from model deductions and working hypotheses.
            Findings never blur raw DOM reality with cognitive inferences.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-white dark:bg-ink-900 border border-line rounded-lg px-4 py-2 shrink-0 shadow-2xs">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500">
              Deterministic Integrity
            </div>
            <div className="text-xl font-bold font-mono text-emerald-700 dark:text-emerald-400">
              {integrityScore}%
            </div>
          </div>
          <div className="text-[10px] text-ink-500 font-mono border-l border-line pl-3">
            <div>{observedAndVerified} Empirical Facts</div>
            <div>{total} Total Findings</div>
          </div>
        </div>
      </div>

      {/* 5 Evidence Classes Visual Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {ORDERED_CLASSES.map((cls) => {
          const spec = DEFAULT_TAXONOMY_SPECS[cls];
          const count = counts[cls] || 0;
          const isSelected = selectedClass === cls;

          return (
            <div
              key={cls}
              onClick={() => onSelectClass?.(isSelected ? 'ALL' : cls)}
              className={`p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? `${spec.activeBorder} shadow-sm ring-1 ring-ink/20`
                  : 'bg-white dark:bg-ink-900/60 border-line hover:border-ink-400 dark:hover:border-ink-600'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-1">
                  <span
                    className={`text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${spec.badgeStyle}`}
                  >
                    {spec.label}
                  </span>
                  <span className="font-mono text-xs font-bold text-ink">
                    {count}
                  </span>
                </div>

                <div>
                  <h4 className="font-bold text-xs text-ink leading-tight">
                    {spec.title}
                  </h4>
                  <div className="text-[10px] font-mono text-ink-500 mt-0.5">
                    {spec.level}
                  </div>
                </div>

                {!compact && (
                  <p className="text-[11px] text-ink-600 dark:text-ink-400 leading-snug line-clamp-3">
                    {spec.description}
                  </p>
                )}
              </div>

              <div className="mt-3 pt-2.5 border-t border-line/60">
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-ink-400 mb-1">
                  Subtypes:
                </div>
                <div className="flex flex-wrap gap-1">
                  {spec.subtypes.slice(0, 3).map((sub) => (
                    <span
                      key={sub}
                      className="text-[9px] font-mono px-1 py-0.2 rounded bg-paper-200/80 dark:bg-ink-950 text-ink-600 dark:text-ink-400 border border-line/50"
                    >
                      {sub}
                    </span>
                  ))}
                  {spec.subtypes.length > 3 && (
                    <span className="text-[9px] font-mono text-ink-400 self-center">
                      +{spec.subtypes.length - 3}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Epistemic Ledger Rule Callout */}
      <div className="bg-amber-500/10 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-800/60 rounded-lg p-3.5 flex items-start gap-3 text-xs">
        <span className="text-base text-amber-700 dark:text-amber-400 leading-none">⚖️</span>
        <div className="space-y-1">
          <div className="font-bold text-amber-950 dark:text-amber-200">
            Epistemic Separation Guarantee
          </div>
          <p className="text-[11px] text-amber-900/90 dark:text-amber-300/90 leading-relaxed font-sans">
            Findings flagged as <strong className="font-mono">OBSERVED</strong> are guaranteed to originate from verified DOM selectors, HTTP responses, or AST parses.
            Heuristic deductions are strictly badged as <strong className="font-mono">MODEL-INFERRED</strong>, and provisional findings remain flagged as <strong className="font-mono">HYPOTHESIS</strong> with capped confidence.
          </p>
        </div>
      </div>
    </div>
  );
}
