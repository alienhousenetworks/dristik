import React, { useState } from 'react';
import { CodePatch, Finding } from '../types';
import { categoryLabel, display, formatPercent, severityTone } from '../lib/format';
import { classifyFindingNature } from '../lib/findingClassifier';

interface DrawerProps {
  finding: Finding | null;
  patches: CodePatch[];
  onClose: () => void;
}

export function Drawer({ finding, patches, onClose }: DrawerProps) {
  const [copied, setCopied] = useState(false);
  if (!finding) return null;

  const cl = classifyFindingNature(finding);
  const isFact = cl.nature === 'VERIFIED_DOM_FACT';

  const patch =
    finding.code_patch ||
    patches.find((item) => item.category === finding.category) ||
    null;

  const copyPatch = async () => {
    if (!patch) return;
    await navigator.clipboard.writeText(patch.after_snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end scrim" onClick={onClose}>
      <aside
        className="sheet w-full max-w-xl h-full overflow-y-auto px-7 py-8 space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header with Dual Badges */}
        <div className="flex items-start justify-between gap-4 border-b border-line pb-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded text-[10px] uppercase tracking-wider border ${cl.badgeClass}`}>
                {cl.badgeLabel}
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wide border ${severityTone(finding.severity)}`}>
                {finding.severity}
              </span>
              <span className="text-xs font-mono text-ink-500 uppercase">
                {categoryLabel(finding.category)}
              </span>
            </div>
            <h3 className="font-serif text-2xl text-ink leading-snug">{finding.finding || finding.title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 hover:bg-paper-100 rounded text-ink-500 hover:text-ink cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Verification Spec Matrix */}
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 card text-xs">
          <div>
            <dt className="text-ink-400 text-[10px] uppercase font-mono">Verification Status</dt>
            <dd className="font-semibold text-ink mt-0.5">{display(finding.verification_status)}</dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] uppercase font-mono">Confidence Rubric</dt>
            <dd className={`font-semibold mt-0.5 ${cl.confidenceClass}`}>
              {cl.canonicalConfidence}
              {finding.confidence != null ? ` (${formatPercent(finding.confidence)})` : ''}
            </dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] uppercase font-mono">Checkability</dt>
            <dd className="font-semibold text-ink mt-0.5">{isFact ? '100% DevTools Replicable' : 'Advisory Inference'}</dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] uppercase font-mono">Impact / Effort</dt>
            <dd className="font-semibold text-ink mt-0.5">{finding.impact} / {finding.effort}</dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] uppercase font-mono">Materiality</dt>
            <dd className="font-semibold text-ink mt-0.5">{finding.materiality || 'Standard'}</dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] uppercase font-mono">Audit Finding ID</dt>
            <dd className="font-mono text-[10px] text-ink-500 mt-0.5 truncate">{finding.finding_id.slice(0, 14)}</dd>
          </div>
        </dl>

        {finding.confidence_basis && (
          <p className="text-xs font-mono text-ink-500 bg-paper-100 dark:bg-ink-900 p-2.5 rounded border border-line">
            Grounding Basis: {finding.confidence_basis}
          </p>
        )}

        {/* TIER 1: EMPIRICAL VERIFIED OBSERVATION (The Ground Truth) */}
        <section className={`p-4 rounded-lg border space-y-3 ${
          isFact
            ? 'bg-emerald-50/20 dark:bg-emerald-950/10 border-emerald-300 dark:border-emerald-800'
            : 'bg-paper-50 dark:bg-ink-950 border-line'
        }`}>
          <div className="flex items-center justify-between border-b pb-2 border-line/60">
            <div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-400 block">
                Tier 1 · {cl.observationHeading}
              </span>
              <span className="text-[11px] text-ink-500">{cl.checkMethod}</span>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900 text-emerald-900 dark:text-emerald-200 rounded">
              {isFact ? 'EMPIRICAL PROOF' : 'HEURISTIC SCAN'}
            </span>
          </div>

          <p className="text-xs text-ink leading-relaxed">
            {display(finding.description)}
          </p>
          <p className="text-[10px] text-ink-500 italic">
            {cl.observationHelp}
          </p>

          {/* Granular DOM Evidence Items */}
          {finding.evidence && finding.evidence.length > 0 ? (
            <div className="space-y-2 pt-2">
              <span className="text-[10px] font-mono font-bold uppercase text-ink-500 block">
                Extracted DOM / Network Tokens ({finding.evidence.length})
              </span>
              <ul className="space-y-2">
                {finding.evidence.map((item, index) => (
                  <li key={item.evidence_id || index} className="p-2.5 bg-white dark:bg-ink-900 rounded border border-line text-xs font-mono space-y-1">
                    {item.element && (
                      <div className="text-emerald-800 dark:text-emerald-400 font-bold">
                        Element: <code>{item.element}</code>
                      </div>
                    )}
                    {item.selector && (
                      <div className="text-blue-900 dark:text-blue-400">
                        Selector: <code>{item.selector}</code>
                      </div>
                    )}
                    {(item.value || item.snippet) && (
                      <div className="text-ink-700 dark:text-ink-300 bg-paper-100 dark:bg-ink-950 p-1.5 rounded break-all">
                        "{display(item.value || item.snippet)}"
                      </div>
                    )}
                    {item.url && (
                      <div className="text-ink-400 text-[10px] truncate">
                        URL: {item.url}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="p-2.5 bg-paper-100 dark:bg-ink-900 rounded border border-line text-[11px] text-ink-500 italic">
              No individual DOM selector tokens logged for this high-level heuristic finding.
            </div>
          )}
        </section>

        {/* TIER 2: COGNITIVE MODEL RECOMMENDATION (The AI Advisory) */}
        <section className="p-4 rounded-lg border border-purple-300 dark:border-purple-800 bg-purple-50/20 dark:bg-purple-950/10 space-y-3">
          <div className="flex items-center justify-between border-b pb-2 border-purple-200 dark:border-purple-800/60">
            <div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-purple-800 dark:text-purple-400 block">
                Tier 2 · {cl.recommendationHeading}
              </span>
              <span className="text-[11px] text-ink-500">Cognitive Multi-Agent Synthesis</span>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-900 dark:text-purple-200 rounded">
              AI ADVISORY
            </span>
          </div>

          <p className="text-xs text-ink leading-relaxed">
            {display(finding.recommendation)}
          </p>
          <p className="text-[10px] text-ink-500 italic">
            {cl.recommendationHelp}
          </p>

          {/* Business Impact if present */}
          {finding.business_impact && (
            <div className="p-2.5 bg-white dark:bg-ink-900 rounded border border-purple-200 dark:border-purple-900 text-xs space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase text-purple-700 dark:text-purple-400 block">
                Projected Business &amp; Search Impact
              </span>
              <p className="text-ink-700 dark:text-ink-300">{finding.business_impact}</p>
            </div>
          )}
        </section>

        {/* Code Patch Section */}
        {patch && (
          <section className="p-4 rounded-lg border border-line bg-paper-50 dark:bg-ink-950 space-y-3">
            <div className="flex items-baseline justify-between gap-3 border-b border-line pb-2">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-pine block">
                  Engineering Code Patch
                </span>
                <span className="font-mono text-xs text-ink">{display(patch.target_file, 'patch.diff')}</span>
              </div>
              <button
                type="button"
                onClick={copyPatch}
                className="px-2.5 py-1 bg-pine text-white text-xs font-semibold rounded hover:bg-pine/90 transition-colors shadow-2xs cursor-pointer"
              >
                {copied ? '✓ Copied' : 'Copy Patch'}
              </button>
            </div>
            <p className="text-xs text-ink-700 dark:text-ink-300">{display(patch.explanation)}</p>
            <pre className="text-xs leading-relaxed text-ink bg-white dark:bg-ink-900 p-3 rounded border border-line overflow-x-auto whitespace-pre-wrap font-mono">
              {patch.after_snippet}
            </pre>
          </section>
        )}
      </aside>
    </div>
  );
}
