import React, { useMemo, useState } from 'react';
import { Finding, Severity, EvidenceClass } from '../types';
import { CATEGORY_FILTERS, categoryLabel, severityTone } from '../lib/format';
import { classifyFindingNature } from '../lib/findingClassifier';
import { EvidenceTaxonomyGuide } from './EvidenceTaxonomyGuide';
import { CroEvidenceDissectionCard } from './CroEvidenceDissectionCard';
import { CalibrationAxes } from './CalibrationAxes';

interface FindingsProps {
  findings: Finding[];
  onSelect: (finding: Finding) => void;
}

const SEVERITIES: Array<Severity | 'ALL'> = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
type EvidenceClassFilter = 'ALL' | EvidenceClass;

function impactWord(n: number | undefined): string {
  if (n == null) return '—';
  if (n >= 8) return 'High';
  if (n >= 5) return 'Medium';
  return 'Low';
}

function effortWord(n: number | undefined): string {
  if (n == null) return '—';
  if (n >= 8) return 'High';
  if (n >= 5) return 'Medium';
  return 'Low';
}

function confidencePercent(c: number | undefined): string {
  if (c == null) return '—';
  return `${Math.round(c * 100)}%`;
}

// ─── Horizontal labeled field pair ───────────────────────────────────────────
function MetaRow({ label, value, valueClass = '' }: { label: string; value: React.ReactNode; valueClass?: string }) {
  return (
    <div className="flex items-baseline gap-2 py-0.5">
      <span className="w-28 shrink-0 text-[9px] font-mono font-bold uppercase tracking-[0.04em] text-ink-400">{label}</span>
      <div className="flex-1 border-b border-dashed border-line/40" />
      <span className={`text-[11px] font-mono font-semibold text-right ${valueClass || 'text-ink'}`}>{value}</span>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────
export function Findings({ findings, onSelect }: FindingsProps) {
  const [category, setCategory] = useState<(typeof CATEGORY_FILTERS)[number]>('ALL');
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>('ALL');
  const [evidenceClass, setEvidenceClass] = useState<EvidenceClassFilter>('ALL');

  const classCounts = useMemo(() => {
    const c: Record<EvidenceClass, number> = {
      OBSERVED: 0,
      EXTERNALLY_VERIFIED: 0,
      MODEL_INFERRED: 0,
      HYPOTHESIS: 0,
      RECOMMENDATION: 0,
    };
    findings.forEach((f) => {
      const cl = classifyFindingNature(f);
      c[cl.evidenceClass] = (c[cl.evidenceClass] || 0) + 1;
    });
    return c;
  }, [findings]);

  const filtered = useMemo(
    () =>
      findings.filter((item) => {
        const catOk = category === 'ALL' || item.category === category;
        const sevOk = severity === 'ALL' || item.severity === severity;
        const cl = classifyFindingNature(item);
        const classOk = evidenceClass === 'ALL' || cl.evidenceClass === evidenceClass;
        return catOk && sevOk && classOk;
      }),
    [findings, category, severity, evidenceClass]
  );

  return (
    <div className="space-y-6">
      {/* ── First-Class Evidence Taxonomy Guide ──────────────── */}
      <EvidenceTaxonomyGuide
        findings={findings}
        selectedClass={evidenceClass}
        onSelectClass={(cls) => setEvidenceClass(cls)}
      />

      {/* ── Header & Evidence Class segmented controls ───────── */}
      <div className="flex flex-col md:flex-row gap-3 justify-between items-start md:items-center">
        <div>
          <h3 className="font-sans text-xl font-bold text-ink">Forensic Findings Ledger</h3>
          <p className="text-xs text-ink-500">
            {findings.length} findings · {classCounts.OBSERVED} directly observed · {classCounts.EXTERNALLY_VERIFIED} externally verified · {classCounts.HYPOTHESIS} working hypotheses
          </p>
        </div>

        {/* Evidence Class segmented control */}
        <div className="flex flex-wrap p-1 bg-paper-100 dark:bg-ink-900 rounded-lg text-xs font-mono gap-1">
          <button
            type="button"
            onClick={() => setEvidenceClass('ALL')}
            className={`px-2.5 py-1.5 rounded-md font-semibold ${
              evidenceClass === 'ALL' ? 'bg-ink text-paper-50 shadow-xs' : 'text-ink-600 dark:text-ink-300 hover:text-ink'
            }`}
          >
            All ({findings.length})
          </button>
          <button
            type="button"
            onClick={() => setEvidenceClass('OBSERVED')}
            className={`px-2.5 py-1.5 rounded-md font-semibold ${
              evidenceClass === 'OBSERVED'
                ? 'bg-good/10 text-white shadow-xs'
                : 'text-good dark:text-good hover:bg-good/10 dark:hover:bg-good/10'
            }`}
          >
            Observed ({classCounts.OBSERVED})
          </button>
          <button
            type="button"
            onClick={() => setEvidenceClass('EXTERNALLY_VERIFIED')}
            className={`px-2.5 py-1.5 rounded-md font-semibold ${
              evidenceClass === 'EXTERNALLY_VERIFIED'
                ? 'bg-paper-100 text-white shadow-xs'
                : 'text-ink-700 dark:text-ink-700 hover:bg-paper-100 dark:hover:bg-paper-100'
            }`}
          >
            Externally Verified ({classCounts.EXTERNALLY_VERIFIED})
          </button>
          <button
            type="button"
            onClick={() => setEvidenceClass('MODEL_INFERRED')}
            className={`px-2.5 py-1.5 rounded-md font-semibold ${
              evidenceClass === 'MODEL_INFERRED'
                ? 'bg-paper-100 text-white shadow-xs'
                : 'text-ink-700 dark:text-ink-700 hover:bg-paper-100 dark:hover:bg-paper-100'
            }`}
          >
            Model-Inferred ({classCounts.MODEL_INFERRED})
          </button>
          <button
            type="button"
            onClick={() => setEvidenceClass('HYPOTHESIS')}
            className={`px-2.5 py-1.5 rounded-md font-semibold ${
              evidenceClass === 'HYPOTHESIS'
                ? 'bg-warn/10 text-white shadow-xs'
                : 'text-warn dark:text-warn hover:bg-warn/10 dark:hover:bg-warn/10'
            }`}
          >
            Hypothesis ({classCounts.HYPOTHESIS})
          </button>
          <button
            type="button"
            onClick={() => setEvidenceClass('RECOMMENDATION')}
            className={`px-2.5 py-1.5 rounded-md font-semibold ${
              evidenceClass === 'RECOMMENDATION'
                ? 'bg-paper-100 text-white shadow-xs'
                : 'text-ink-700 dark:text-ink-700 hover:bg-paper-100 dark:hover:bg-paper-100'
            }`}
          >
            Remediation ({classCounts.RECOMMENDATION})
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-ink-400 mr-1 font-mono uppercase text-[10px]">Severity</span>
          {SEVERITIES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setSeverity(item)}
              className={`px-2 py-1 rounded-md font-mono ${
                severity === item ? 'bg-ink text-paper-50 font-semibold' : 'text-ink-500 hover:text-ink hover:bg-paper-100'
              }`}
            >
              {item === 'ALL' ? 'All' : item.toLowerCase()}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-ink-400 mr-1 font-mono uppercase text-[10px]">Category</span>
          {CATEGORY_FILTERS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={`px-2 py-1 rounded-md font-mono ${
                category === item ? 'bg-ink text-paper-50 font-semibold' : 'text-ink-500 hover:text-ink hover:bg-paper-100'
              }`}
            >
              {item === 'ALL' ? 'All' : categoryLabel(item)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Findings list ───────────────────────────────────────── */}
      {filtered.length === 0 ? (
        <div className="card p-8 text-center text-ink-400 text-sm">
          No findings match the active filters.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((finding) => {
            const cl = classifyFindingNature(finding);
            const isObserved = cl.evidenceClass === 'OBSERVED';
            const isVerified = cl.evidenceClass === 'EXTERNALLY_VERIFIED';
            const isHypothesis = cl.evidenceClass === 'HYPOTHESIS';

            // Primary evidence token
            const primaryEv = finding.evidence?.find((e) => e.selector || e.element) || finding.evidence?.[0];
            const hasSelector = primaryEv?.selector || primaryEv?.element;
            const hasObserved = primaryEv?.value || primaryEv?.snippet;

            return (
              <div
                key={finding.finding_id}
                onClick={() => onSelect(finding)}
                className={`rounded-xl border shadow-xs transition-all cursor-pointer hover:shadow-md hover:-translate-y-0.5 ${cl.containerClass}`}
                style={{ transition: 'box-shadow 0.15s, transform 0.15s' }}
              >
                {/* ── Card top stripe ───────────────────────── */}
                <div className="px-5 pt-4 pb-3 flex flex-wrap items-center justify-between gap-2 border-b border-line/60">
                  {/* Left: evidence class badge + severity + category */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] uppercase tracking-[0.04em] border font-mono font-semibold ${cl.badgeClass}`}>
                      {cl.badgeLabel}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wide border ${severityTone(finding.severity)}`}>
                      {finding.severity}
                    </span>
                    <span className="text-[10px] font-mono text-ink-500 uppercase">{categoryLabel(finding.category)}</span>
                    {finding.evidence_scope && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-line text-ink-600">
                        {finding.evidence_scope.replace(/_/g, ' ')}
                        {finding.scope_hit_count && finding.scope_sample_size
                          ? ` ${finding.scope_hit_count}/${finding.scope_sample_size}`
                          : ''}
                      </span>
                    )}
                  </div>
                  {/* Right: finding ID & resolution status */}
                  <div className="flex items-center gap-2">
                    {finding.resolution_status === 'RESOLVED' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good border border-good/30 font-bold">
                        <span>✓</span>
                        <span>CERTIFIED RESOLVED</span>
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-warn/10 text-warn border border-warn/30 font-bold">
                        OPEN
                      </span>
                    )}
                    <code className="text-[10px] font-mono text-ink-500 bg-paper-100 dark:bg-ink-900 px-2 py-0.5 rounded border border-line">
                      {finding.finding_id}
                    </code>
                  </div>
                </div>

                {/* ── Card body: 3-Pillar Architecture (Found / Problem / Fix) ───── */}
                <div className="px-5 py-4 space-y-3.5">
                  {/* Root Cause Banner if multiple observations clustered */}
                  {finding.sub_observations && finding.sub_observations.length > 1 && (
                    <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg bg-paper-100 dark:bg-paper-100 border border-line dark:border-line text-ink-700 dark:text-ink-700 text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <span className="font-bold tracking-[0.04em] uppercase text-[10px] bg-paper-100 dark:bg-paper-100 text-ink-700 dark:text-ink-700 px-1.5 py-0.5 rounded">
                           ROOT CAUSE
                        </span>
                        <span className="font-semibold">Synthesizes {finding.sub_observations.length} underlying observations</span>
                      </div>
                      <span className="text-[10px] font-mono text-ink-700 dark:text-ink-700">
                        Unified Remediation
                      </span>
                    </div>
                  )}

                  {/* Headline Title */}
                  <h4 className="font-sans text-base font-bold text-ink leading-snug">
                    {finding.title || finding.finding}
                  </h4>
                  <CalibrationAxes finding={finding} compact />

                  {/* ── 3-PILLAR GRID ── */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    
                    {/* PILLAR 1: WHAT WAS FOUND */}
                    <div className="p-3 rounded-lg border border-line dark:border-ink-800 bg-paper-50 dark:bg-ink-950/60 flex flex-col justify-between space-y-2">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-[0.04em] text-ink-700 dark:text-ink-300 border-b border-line/40 pb-1">
                          <span>🔍 1. What Was Found</span>
                        </div>
                        <p className="text-xs text-ink-700 dark:text-ink-200 leading-relaxed font-sans">
                          {finding.description || finding.finding}
                        </p>

                        {/* If clustered root cause, render underlying observations */}
                        {finding.sub_observations && finding.sub_observations.length > 1 ? (
                          <div className="space-y-1.5 mt-2 pt-2 border-t border-line/40">
                            <span className="text-[9px] font-mono font-bold uppercase tracking-[0.04em] text-ink-400 block">
                              Contributing Observations ({finding.sub_observations.length}):
                            </span>
                            <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                              {finding.detailed_observations && finding.detailed_observations.length > 0 ? (
                                finding.detailed_observations.map((obs, idx) => (
                                  <div key={obs.observation_id || idx} className="p-1.5 rounded bg-paper-200/50 dark:bg-ink-900 border border-line/30 text-[10px] space-y-0.5">
                                    <div className="flex items-center justify-between gap-1">
                                      <span className="font-semibold text-ink-700 dark:text-ink-200 truncate">• {obs.title}</span>
                                      {obs.selector && (
                                        <code className="text-[8px] px-1 py-0.2 rounded bg-paper-100 dark:bg-ink-950 text-good dark:text-good font-mono shrink-0">
                                          {obs.selector}
                                        </code>
                                      )}
                                    </div>
                                    {obs.snippet && (
                                      <div className="text-[9px] text-ink-600 dark:text-ink-400 italic truncate pl-1 border-l border-line/60">
                                        "{obs.snippet}"
                                      </div>
                                    )}
                                  </div>
                                ))
                              ) : (
                                finding.sub_observations.map((sub, idx) => (
                                  <div key={idx} className="text-[10px] text-ink-700 dark:text-ink-300 flex items-start gap-1">
                                    <span className="text-ink-700 font-bold">•</span>
                                    <span>{sub}</span>
                                  </div>
                                ))
                              )}
                            </div>
                          </div>
                        ) : (
                          (hasSelector || hasObserved) && (
                            <div className="p-2 bg-paper-200/50 dark:bg-ink-900 rounded font-mono text-[10px] space-y-1 border border-line/40">
                              {hasSelector && (
                                <div className="truncate">
                                  <span className="text-ink-400 uppercase font-bold text-[9px]">Selector: </span>
                                  <code className="text-good dark:text-good font-semibold">{hasSelector}</code>
                                </div>
                              )}
                              {hasObserved && (
                                <div className="line-clamp-2 text-ink-700 dark:text-ink-300">
                                  <span className="text-ink-400 uppercase font-bold text-[9px]">Observed: </span>
                                  <span>"{hasObserved}"</span>
                                </div>
                              )}
                            </div>
                          )
                        )}
                      </div>
                      {primaryEv?.url && (
                        <div className="pt-1 text-[10px] font-mono text-ink-400 truncate">
                          URL: <span className="text-ink-700 dark:text-ink-700">{primaryEv.url}</span>
                        </div>
                      )}
                    </div>

                    {/* PILLAR 2: WHAT IS THE PROBLEM */}
                    <div className="p-3 rounded-lg border border-warn/30 dark:border-warn/30 bg-warn/10 dark:bg-warn/10 flex flex-col justify-between space-y-2">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-[0.04em] text-warn dark:text-warn border-b border-warn/30 dark:border-warn/30 pb-1">
                          <span> 2. What Is The Problem</span>
                        </div>
                        <p className="text-xs text-warn dark:text-warn leading-relaxed font-sans">
                          {finding.why_it_matters || finding.business_impact || (
                            `Defect impairs compliance and discoverability for ${finding.severity.toLowerCase()} severity standard.`
                          )}
                        </p>
                      </div>
                      <div className="pt-1 flex flex-wrap items-center gap-2 border-t border-warn/30 dark:border-warn/30 text-[10px] font-mono">
                        <span className="text-warn dark:text-warn font-semibold">
                          Impact: {impactWord(finding.impact)} ({finding.impact ?? '—'}/10)
                        </span>
                        <span className="text-warn dark:text-warn">·</span>
                        <span className="text-warn dark:text-warn">
                          Effort: {effortWord(finding.effort)}
                        </span>
                      </div>
                    </div>

                    {/* PILLAR 3: HOW TO FIX IT */}
                    <div className="p-3 rounded-lg border border-line dark:border-line bg-paper-100 dark:bg-paper-100 flex flex-col justify-between space-y-2">
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-[10px] font-mono font-bold uppercase tracking-[0.04em] text-ink-700 dark:text-ink-700 border-b border-line dark:border-line pb-1">
                          <span> 3. How To Fix It</span>
                          {finding.code_patch && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-paper-100 text-ink-700 font-bold">
                              Code Patch
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-ink-700 dark:text-ink-700 leading-relaxed font-sans line-clamp-3">
                          {finding.recommendation || 'Apply suggested architectural or tag fixes to align with verified standards.'}
                        </p>
                      </div>
                      <div className="pt-1 text-[10px] font-mono text-ink-700 dark:text-ink-700 border-t border-line dark:border-line">
                        {finding.validation_criteria ? (
                          <span className="truncate block">Target: {finding.validation_criteria}</span>
                        ) : (
                          <span>Verify live via continuous assurance loop</span>
                        )}
                      </div>
                    </div>

                  </div>

                  {/* Grounded CRO Evidence Dissection Card (if present) */}
                  {finding.cro_dissection && (
                    <div className="mt-2">
                      <CroEvidenceDissectionCard dissection={finding.cro_dissection} finding={finding} />
                    </div>
                  )}
                </div>

                {/* ── Card footer ────────────────────────────── */}
                <div className="px-5 py-2.5 border-t border-line/40 flex items-center justify-between text-[11px] text-ink-500 bg-paper-50/50 dark:bg-ink-950/30 rounded-b-xl">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px]">
                      {cl.checkMethod}
                    </span>
                    <span className="text-ink-300 dark:text-ink-700">·</span>
                    <span className="font-mono text-[10px] text-ink-500">
                      Confidence: {confidencePercent(finding.confidence)}
                    </span>
                  </div>
                  <span className="text-ink-700 font-semibold flex items-center gap-1 hover:underline">
                    <span>Inspect Full Dossier, Code Patch &amp; Verify</span>
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
