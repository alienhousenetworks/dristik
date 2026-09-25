import React, { useMemo, useState } from 'react';
import { Finding, Severity } from '../types';
import { CATEGORY_FILTERS, categoryLabel, severityTone } from '../lib/format';
import { classifyFindingNature, FindingNature } from '../lib/findingClassifier';

interface FindingsProps {
  findings: Finding[];
  onSelect: (finding: Finding) => void;
}

const SEVERITIES: Array<Severity | 'ALL'> = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
type NatureFilter = 'ALL' | FindingNature;

export function Findings({ findings, onSelect }: FindingsProps) {
  const [category, setCategory] = useState<(typeof CATEGORY_FILTERS)[number]>('ALL');
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>('ALL');
  const [nature, setNature] = useState<NatureFilter>('ALL');

  // Counts for nature tabs
  const verifiedCount = useMemo(
    () => findings.filter((f) => classifyFindingNature(f).nature === 'VERIFIED_DOM_FACT').length,
    [findings]
  );
  const unverifiedCount = useMemo(
    () => findings.filter((f) => classifyFindingNature(f).nature === 'SINGLE_SOURCE_UNVERIFIED').length,
    [findings]
  );
  const inferenceCount = useMemo(
    () => findings.filter((f) => classifyFindingNature(f).nature === 'LLM_INFERENCE').length,
    [findings]
  );

  const filtered = useMemo(
    () =>
      findings.filter((item) => {
        const catOk = category === 'ALL' || item.category === category;
        const sevOk = severity === 'ALL' || item.severity === severity;
        const natureClass = classifyFindingNature(item);
        const natOk = nature === 'ALL' || natureClass.nature === nature;
        return catOk && sevOk && natOk;
      }),
    [findings, category, severity, nature]
  );

  return (
    <div className="space-y-6">
      {/* Top Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">
        <div>
          <h3 className="font-serif text-xl font-bold text-ink">Findings & Evidence</h3>
          <p className="text-xs text-ink-500">
            {findings.length} findings categorized by empirical verification level
          </p>
        </div>

        {/* Nature Mode Segmented Control */}
        <div className="flex p-1 bg-paper-100 rounded-lg text-xs font-mono">
          <button
            type="button"
            onClick={() => setNature('ALL')}
            className={`px-3 py-1.5 rounded-md ${nature === 'ALL' ? 'bg-ink text-paper-50' : 'text-ink-500 hover:text-ink'}`}
          >
            All ({findings.length})
          </button>
          <button
            type="button"
            onClick={() => setNature('VERIFIED_DOM_FACT')}
            className={`px-3 py-1.5 rounded-md ${nature === 'VERIFIED_DOM_FACT' ? 'bg-ink text-paper-50' : 'text-ink-500 hover:text-ink'}`}
          >
            Verified ({verifiedCount})
          </button>
          <button
            type="button"
            onClick={() => setNature('LLM_INFERENCE')}
            className={`px-3 py-1.5 rounded-md ${nature === 'LLM_INFERENCE' ? 'bg-ink text-paper-50' : 'text-ink-500 hover:text-ink'}`}
          >
            Advisory ({inferenceCount})
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-ink-400 mr-1">Severity</span>
          {SEVERITIES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setSeverity(item)}
              className={`px-2 py-1 rounded-md ${
                severity === item ? 'bg-ink text-paper-50 font-semibold' : 'text-ink-500 hover:text-ink hover:bg-paper-100'
              }`}
            >
              {item === 'ALL' ? 'All' : item.toLowerCase()}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-ink-400 mr-1">Category</span>
          {CATEGORY_FILTERS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={`px-2 py-1 rounded-md ${
                category === item ? 'bg-ink text-paper-50 font-semibold' : 'text-ink-500 hover:text-ink hover:bg-paper-100'
              }`}
            >
              {item === 'ALL' ? 'All' : categoryLabel(item)}
            </button>
          ))}
        </div>
      </div>

      {/* Findings List */}
      {filtered.length === 0 ? (
        <div className="card p-8 text-center text-ink-400 text-sm">
          No findings match the active filters.
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((finding) => {
            const cl = classifyFindingNature(finding);
            const isFact = cl.nature === 'VERIFIED_DOM_FACT';
            const hasSelector = finding.evidence?.find((e) => e.selector)?.selector;
            const hasSnippet = finding.evidence?.find((e) => e.value || e.snippet)?.value || finding.evidence?.find((e) => e.snippet)?.snippet;

            return (
              <div
                key={finding.finding_id}
                onClick={() => onSelect(finding)}
                className={`p-5 rounded-lg border shadow-xs transition-all cursor-pointer hover:shadow-sm ${cl.containerClass}`}
              >
                {/* Header Badge Row */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3 mb-3 border-line/60">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Typographical Nature Badge */}
                    <span className={`px-2.5 py-0.5 rounded text-[10px] uppercase tracking-wider border ${cl.badgeClass}`}>
                      {cl.badgeLabel}
                    </span>

                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wide border ${severityTone(finding.severity)}`}>
                      {finding.severity}
                    </span>

                    <span className="text-xs font-mono text-ink-500">
                      {categoryLabel(finding.category)}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono text-ink-500">
                    <span>Impact: <strong className="text-ink">{finding.impact}/10</strong></span>
                    <span>Effort: <strong className="text-ink">{finding.effort}/10</strong></span>
                    <span className={cl.confidenceClass}>
                      {cl.canonicalConfidence}
                    </span>
                  </div>
                </div>

                {/* Main Content & Title */}
                <div className="space-y-2">
                  <h4 className="font-serif text-lg font-semibold text-ink">
                    {finding.finding || finding.title}
                  </h4>

                  {/* Observation Block */}
                  <div className={`p-3 rounded text-xs space-y-1 ${isFact ? 'bg-paper-100/70 dark:bg-ink-950/60 font-sans' : 'bg-purple-50/40 dark:bg-purple-950/20 italic'}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-ink-600 block">
                        {cl.observationHeading}
                      </span>
                      <span className="text-[10px] font-mono text-ink-400">
                        {cl.checkMethod}
                      </span>
                    </div>
                    <p className="text-ink-800 dark:text-ink-200 leading-relaxed font-normal not-italic">
                      {finding.description}
                    </p>
                    <p className="text-[10px] text-ink-500 not-italic">
                      {cl.observationHelp}
                    </p>
                  </div>

                  {/* DOM Technical Evidence Snippet for Verified Facts */}
                  {isFact && (hasSelector || hasSnippet) && (
                    <div className="p-2.5 bg-paper-200/50 dark:bg-ink-950 rounded border border-line text-[11px] font-mono space-y-1">
                      {hasSelector && (
                        <div className="text-emerald-800 dark:text-emerald-400 truncate">
                          <span className="text-ink-400">Selector:</span> <code>{hasSelector}</code>
                        </div>
                      )}
                      {hasSnippet && (
                        <div className="text-ink-600 dark:text-ink-300 truncate">
                          <span className="text-ink-400">Measured:</span> "{hasSnippet}"
                        </div>
                      )}
                    </div>
                  )}

                  {/* Distinct Recommendation Directive */}
                  {finding.recommendation && (
                    <div className={`p-3 rounded text-xs border ${
                      isFact
                        ? 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/40'
                        : 'bg-purple-50/50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-900/40'
                    }`}>
                      <span className="font-mono text-[10px] font-bold uppercase tracking-wider block mb-0.5 text-ink-700">
                        {cl.recommendationHeading}
                      </span>
                      <p className="text-ink-800 dark:text-ink-200 leading-relaxed">
                        {finding.recommendation}
                      </p>
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-2 border-t border-line/40 flex items-center justify-between text-[11px] text-ink-500">
                  <span className="font-mono text-[10px]">ID: {finding.finding_id.slice(0, 12)}</span>
                  <span className="text-pine font-medium flex items-center gap-1 hover:underline">
                    <span>Inspect Evidence &amp; Code Patch</span>
                    <span>→</span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
