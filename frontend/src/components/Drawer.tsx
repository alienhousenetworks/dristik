import React, { useState } from 'react';
import { CodePatch, Finding } from '../types';
import { categoryLabel, display, formatPercent, severityTone } from '../lib/format';
import { classifyFindingNature } from '../lib/findingClassifier';
import { RemediationVerificationLoop } from './RemediationVerificationLoop';
import { CroEvidenceDissectionCard } from './CroEvidenceDissectionCard';
import { CalibrationAxes } from './CalibrationAxes';

interface DrawerProps {
  finding: Finding | null;
  patches: CodePatch[];
  websiteUrl?: string;
  analysisId?: string;
  onClose: () => void;
  onOpenConnectors?: (tabId?: any) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function impactLabel(n: number | undefined): string {
  if (n == null) return '—';
  if (n >= 8) return 'High';
  if (n >= 5) return 'Medium';
  return 'Low';
}

function effortLabel(n: number | undefined): string {
  if (n == null) return '—';
  if (n >= 8) return 'High';
  if (n >= 5) return 'Medium';
  return 'Low';
}

function confidencePercent(c: number | undefined): string {
  if (c == null) return '—';
  return `${Math.round(c * 100)}%`;
}

function evidenceTypeLabel(nature: string, sourceType?: string): string {
  if (sourceType === 'external_ground_truth') return 'EXTERNAL_GROUND_TRUTH';
  if (nature === 'VERIFIED_DOM_FACT') return 'DOM_VERIFIED';
  if (nature === 'SINGLE_SOURCE_UNVERIFIED') return 'SINGLE_SOURCE_UNVERIFIED';
  return 'LLM_INFERENCE';
}

function evidenceTypeBadgeClass(type: string): string {
  if (type === 'DOM_VERIFIED') return 'bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800';
  if (type === 'EXTERNAL_GROUND_TRUTH') return 'bg-blue-100 text-blue-900 border-blue-300 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800';
  if (type === 'SINGLE_SOURCE_UNVERIFIED') return 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800';
  return 'bg-purple-100 text-purple-900 border-purple-300 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800';
}

function statusBadgeClass(status: string): string {
  const s = status?.toLowerCase() || '';
  if (s.includes('verified') || s.includes('confirmed')) return 'bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800';
  if (s.includes('unverified') || s.includes('provisional')) return 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800';
  return 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-ink-900 dark:text-ink-300 dark:border-ink-700';
}

// ─── Section label ─────────────────────────────────────────────────────────────
function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line/60 pt-4 space-y-1.5">
      <span className="block text-[9px] font-mono font-black uppercase tracking-[0.2em] text-ink-400">
        {label}
      </span>
      {children}
    </div>
  );
}

// ─── Main Drawer ───────────────────────────────────────────────────────────────
export function Drawer({ finding, patches, websiteUrl, analysisId, onClose, onOpenConnectors }: DrawerProps) {
  const [copied, setCopied] = useState(false);
  const [patchCopied, setPatchCopied] = useState(false);

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
    setPatchCopied(true);
    setTimeout(() => setPatchCopied(false), 1600);
  };

  // Primary evidence token (first with a selector)
  const primaryEvidence = finding.evidence?.find((e) => e.selector || e.element) || finding.evidence?.[0];
  const sourceUrl = primaryEvidence?.url || finding.evidence?.[0]?.url || null;
  const domSelector = primaryEvidence?.selector || primaryEvidence?.element || null;
  const observedValue = primaryEvidence?.value || primaryEvidence?.snippet || primaryEvidence?.excerpt || null;

  const evType = evidenceTypeLabel(cl.nature, primaryEvidence?.type);
  const findingStatus = finding.verification_status || 'UNVERIFIED';

  const impactWord = impactLabel(finding.impact);
  const effortWord = effortLabel(finding.effort);

  return (
    <div className="fixed inset-0 z-50 flex justify-end scrim" onClick={onClose}>
      <aside
        className="sheet w-full max-w-2xl h-full overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        style={{ background: 'var(--color-paper-50, #fafaf8)' }}
      >
        {/* ── Top bar ─────────────────────────────────────────── */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-3 border-b border-line bg-paper-50/90 backdrop-blur-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${cl.badgeClass}`}>
              {cl.badgeLabel}
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wide border ${severityTone(finding.severity)}`}>
              {finding.severity}
            </span>
            <span className="text-[10px] font-mono text-ink-500 uppercase">
              {categoryLabel(finding.category)}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 hover:bg-paper-100 rounded text-ink-500 hover:text-ink cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* ── Forensic Dossier Body ────────────────────────────── */}
        <div className="px-6 py-6 space-y-6">

          {/* Finding Title & Top Identity */}
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <code className="font-mono text-sm font-bold text-ink tracking-tight bg-paper-200 dark:bg-ink-900 px-2 py-0.5 rounded border border-line">
                  {finding.finding_id}
                </code>
                <button
                  type="button"
                  onClick={async () => {
                    await navigator.clipboard.writeText(finding.finding_id);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1600);
                  }}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-paper-200 hover:bg-paper-300 text-ink-500 hover:text-ink transition-colors cursor-pointer"
                >
                  {copied ? '✓' : 'copy'}
                </button>
              </div>

              {finding.resolution_status === 'RESOLVED' ? (
                <span className="px-2.5 py-0.5 rounded border text-[11px] font-mono bg-emerald-100 text-emerald-800 border-emerald-300 font-bold">
                  ✓ RESOLVED
                </span>
              ) : (
                <span className={`px-2.5 py-0.5 rounded border text-[11px] font-mono font-bold uppercase tracking-wider ${statusBadgeClass(findingStatus)}`}>
                  {display(findingStatus)}
                </span>
              )}
            </div>

            <h3 className="font-serif text-lg font-bold text-ink leading-snug">
              {finding.title || finding.finding}
            </h3>
          </div>

          {/* ═══════════════════════════════════════════════════════ */}
          {/* ROOT CAUSE HIERARCHY (IF CLUSTERED)                     */}
          {/* ═══════════════════════════════════════════════════════ */}
          {finding.sub_observations && finding.sub_observations.length > 1 && (
            <div className="p-4 rounded-xl border border-purple-200 dark:border-purple-900/50 bg-purple-50/50 dark:bg-purple-950/20 space-y-3 shadow-xs">
              <div className="flex items-center justify-between border-b border-purple-200/60 dark:border-purple-900/40 pb-2">
                <span className="text-[11px] font-mono font-black uppercase tracking-wider text-purple-950 dark:text-purple-200 flex items-center gap-1.5">
                  <span>⚡ Root Cause &amp; Contributing Observations Hierarchy</span>
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-200/80 text-purple-900 dark:bg-purple-900 dark:text-purple-200">
                  {finding.sub_observations.length} Observations Clustered
                </span>
              </div>
              <p className="text-xs text-purple-950 dark:text-purple-200/90 leading-relaxed font-sans">
                Rather than treating each symptom as an isolated failure, this canonical finding synthesizes {finding.sub_observations.length} direct observations that stem from the same root-cause architecture.
              </p>
              <div className="space-y-2 pt-1">
                {finding.detailed_observations && finding.detailed_observations.length > 0 ? (
                  finding.detailed_observations.map((obs, idx) => (
                    <div key={obs.observation_id || idx} className="p-3 rounded-lg border border-purple-200/60 dark:border-purple-800/40 bg-white/80 dark:bg-ink-900/80 space-y-1.5 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-ink-900 dark:text-ink-100 flex items-center gap-1.5">
                          <span className="text-purple-600 font-mono text-[10px]">{idx + 1}.</span>
                          <span>{obs.title}</span>
                        </span>
                        {obs.selector && (
                          <code className="text-[10px] px-1.5 py-0.5 rounded bg-paper-100 dark:bg-ink-950 text-emerald-800 dark:text-emerald-400 font-mono font-semibold">
                            {obs.selector}
                          </code>
                        )}
                      </div>
                      {obs.description && obs.description !== obs.title && (
                        <p className="text-[11px] text-ink-700 dark:text-ink-300 font-sans">
                          {obs.description}
                        </p>
                      )}
                      {obs.snippet && (
                        <div className="p-2 rounded bg-paper-100 dark:bg-ink-950 text-[10px] font-mono text-ink-700 dark:text-ink-300 border border-line/40">
                          <span className="text-ink-400 font-bold uppercase text-[9px] block">Observed Snippet:</span>
                          <span className="line-clamp-2">"{obs.snippet}"</span>
                        </div>
                      )}
                      {obs.url && (
                        <div className="text-[9px] font-mono text-ink-400 truncate">
                          URL: <span className="text-blue-700 dark:text-blue-400">{obs.url}</span>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  finding.sub_observations.map((sub, idx) => (
                    <div key={idx} className="flex items-start gap-2 p-2 rounded bg-white/60 dark:bg-ink-900/60 text-xs text-ink-800 dark:text-ink-200 border border-line/40">
                      <span className="text-purple-600 font-bold">•</span>
                      <span>{sub}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════ */}
          {/* PILLAR 1: WHAT WAS FOUND                               */}
          {/* ═══════════════════════════════════════════════════════ */}
          <div className="p-4 rounded-xl border border-slate-300 dark:border-ink-800 bg-white dark:bg-ink-950 space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-line/60 pb-2">
              <span className="text-[11px] font-mono font-black uppercase tracking-wider text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <span>🔍 1. What Was Found (Observation &amp; Evidence)</span>
              </span>
              <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${cl.badgeClass}`}>
                {cl.badgeLabel}
              </span>
            </div>

            <p className="text-xs text-ink-900 dark:text-ink-100 leading-relaxed font-sans">
              {display(finding.description || finding.finding)}
            </p>

            {/* Measured Evidence Tokens */}
            {finding.evidence && finding.evidence.length > 0 ? (
              <div className="space-y-2 pt-1">
                {finding.evidence.map((ev, i) => (
                  <div
                    key={ev.evidence_id || i}
                    className="p-3 rounded border border-line bg-paper-100 dark:bg-ink-900 font-mono text-[11px] space-y-1.5"
                  >
                    {(ev.selector || ev.element) && (
                      <div>
                        <span className="text-ink-400 text-[9px] uppercase font-bold tracking-wider block">DOM Selector</span>
                        <code className="text-emerald-800 dark:text-emerald-400 font-bold">{ev.selector || ev.element}</code>
                      </div>
                    )}
                    {(ev.value || ev.snippet || ev.excerpt) && (
                      <div>
                        <span className="text-ink-400 text-[9px] uppercase font-bold tracking-wider block">Observed Value</span>
                        <span className="text-ink-700 dark:text-ink-300">"{display(ev.value || ev.snippet || ev.excerpt)}"</span>
                      </div>
                    )}
                    {ev.url && (
                      <div>
                        <span className="text-ink-400 text-[9px] uppercase font-bold tracking-wider block">Target URL</span>
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-700 dark:text-blue-400 hover:underline truncate block max-w-full"
                        >
                          {ev.url}
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : domSelector || observedValue ? (
              <div className="p-3 rounded border border-line bg-paper-100 dark:bg-ink-900 font-mono text-[11px] space-y-1.5">
                {domSelector && (
                  <div>
                    <span className="text-ink-400 text-[9px] uppercase font-bold tracking-wider block">DOM Selector</span>
                    <code className="text-emerald-800 dark:text-emerald-400 font-bold">{domSelector}</code>
                  </div>
                )}
                {observedValue && (
                  <div>
                    <span className="text-ink-400 text-[9px] uppercase font-bold tracking-wider block">Observed</span>
                    <span className="text-ink-700 dark:text-ink-300">"{display(observedValue)}"</span>
                  </div>
                )}
                {sourceUrl && (
                  <div>
                    <span className="text-ink-400 text-[9px] uppercase font-bold tracking-wider block">Target URL</span>
                    <a
                      href={sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-700 dark:text-blue-400 hover:underline truncate block max-w-full"
                    >
                      {sourceUrl}
                    </a>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-ink-500 italic">
                Verified crawl finding recorded across audited pages.
              </p>
            )}

            {finding.cro_dissection && (
              <div className="pt-2">
                <CroEvidenceDissectionCard
                  dissection={finding.cro_dissection}
                  finding={finding}
                  onOpenConnectors={() => onOpenConnectors?.('crm')}
                />
              </div>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════ */}
          {/* PILLAR 2: WHAT IS THE PROBLEM                          */}
          {/* ═══════════════════════════════════════════════════════ */}
          <div className="p-4 rounded-xl border border-amber-300 dark:border-amber-900/50 bg-amber-50/30 dark:bg-amber-950/20 space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-amber-200 dark:border-amber-900/40 pb-2">
              <span className="text-[11px] font-mono font-black uppercase tracking-wider text-amber-950 dark:text-amber-200 flex items-center gap-1.5">
                <span>⚠️ 2. What Is The Problem (Risk &amp; Impact)</span>
              </span>
              <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${severityTone(finding.severity)}`}>
                Severity: {finding.severity}
              </span>
            </div>

            {/* Why It Matters / Business Impact */}
            <div className="p-3 rounded-lg border border-amber-200 dark:border-amber-900/40 bg-white/80 dark:bg-ink-950/60 space-y-1">
              <span className="text-[9px] font-mono uppercase tracking-wider font-bold text-amber-800 dark:text-amber-300 block">
                Why It Matters &amp; Business Risk
              </span>
              <p className="text-xs text-ink leading-relaxed">
                {finding.why_it_matters || finding.business_impact || (
                  `This defect degrades website trust, machine extractability, and search performance for ${categoryLabel(finding.category)}.`
                )}
              </p>
              <CalibrationAxes finding={finding} />
            </div>

            {/* Impact / Effort / Priority Metrics */}
            <div className="grid grid-cols-3 gap-3 p-3 bg-white/60 dark:bg-ink-900/40 rounded-lg border border-amber-200/60 dark:border-amber-900/30 font-mono text-center">
              <div>
                <span className="text-[9px] uppercase tracking-wider text-ink-400 block">Impact</span>
                <span className={`text-sm font-black ${
                  finding.impact != null && finding.impact >= 8
                    ? 'text-red-600'
                    : finding.impact != null && finding.impact >= 5
                    ? 'text-amber-600'
                    : 'text-emerald-700'
                }`}>
                  {impactWord} ({finding.impact ?? '—'}/10)
                </span>
              </div>
              <div>
                <span className="text-[9px] uppercase tracking-wider text-ink-400 block">Effort</span>
                <span className="text-sm font-black text-ink">
                  {effortWord} ({finding.effort ?? '—'}/10)
                </span>
              </div>
              <div>
                <span className="text-[9px] uppercase tracking-wider text-ink-400 block">Confidence</span>
                <span className={`text-sm font-black ${cl.confidenceClass}`}>
                  {confidencePercent(finding.confidence)}
                </span>
              </div>
            </div>

            {finding.confidence_basis && (
              <p className="text-[10px] font-mono text-ink-500 italic">
                Confidence Basis: {finding.confidence_basis}
              </p>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════ */}
          {/* PILLAR 3: HOW TO FIX IT                                */}
          {/* ═══════════════════════════════════════════════════════ */}
          <div className="p-4 rounded-xl border border-blue-300 dark:border-blue-900/50 bg-blue-50/30 dark:bg-blue-950/20 space-y-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-blue-200 dark:border-blue-900/40 pb-2">
              <span className="text-[11px] font-mono font-black uppercase tracking-wider text-blue-950 dark:text-blue-200 flex items-center gap-1.5">
                <span>🛠️ 3. How To Fix It (Remediation &amp; Live Verification)</span>
              </span>
              {patch && (
                <span className="text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-blue-200 text-blue-900">
                  Ready-to-Deploy Patch
                </span>
              )}
            </div>

            {/* Recommendation */}
            {finding.recommendation && (
              <div className="p-3.5 rounded-lg border border-blue-200 dark:border-blue-900/40 bg-white/80 dark:bg-ink-950/60 space-y-1">
                <span className="text-[9px] font-mono uppercase tracking-wider font-bold text-blue-800 dark:text-blue-300 block">
                  Actionable Remediation Guidance
                </span>
                <p className="text-xs text-ink leading-relaxed">
                  {display(finding.recommendation)}
                </p>
              </div>
            )}

            {/* Acceptance Criteria */}
            <div className="p-3 rounded-lg border border-line bg-white/60 dark:bg-ink-900/40 space-y-1 text-xs">
              <span className="text-[9px] font-mono font-black uppercase tracking-wider text-ink-500 block">
                Validation Acceptance Criteria:
              </span>
              <p className="text-ink leading-relaxed">
                {finding.validation_criteria || (
                  isFact
                    ? `${domSelector || 'The affected element'} must be updated so that the observed defect condition no longer exists on the live page.`
                    : 'Verify improvement via live recheck or user engagement measurement after applying recommendations.'
                )}
              </p>
            </div>

            {/* CODE PATCH (if available) */}
            {patch && (
              <div className="p-3.5 rounded-lg border border-line bg-white dark:bg-ink-950 space-y-2.5">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-xs text-pine font-bold">{display(patch.target_file, 'patch.diff')}</span>
                  <button
                    type="button"
                    onClick={copyPatch}
                    className="px-2.5 py-1 bg-pine text-white text-xs font-semibold rounded hover:bg-pine/90 transition-colors shadow-2xs cursor-pointer"
                  >
                    {patchCopied ? '✓ Copied' : 'Copy Patch'}
                  </button>
                </div>
                <p className="text-xs text-ink-700 dark:text-ink-300">{display(patch.explanation)}</p>
                <pre className="text-xs leading-relaxed text-ink bg-paper-100 dark:bg-ink-900 p-3 rounded border border-line overflow-x-auto whitespace-pre-wrap font-mono">
                  {patch.after_snippet}
                </pre>
              </div>
            )}

            {/* LIVE CONTINUOUS VERIFICATION LOOP */}
            <div className="pt-2">
              <RemediationVerificationLoop
                finding={finding}
                websiteUrl={sourceUrl || websiteUrl || 'https://dristik-demo.ai'}
                analysisId={analysisId}
                inline
              />
            </div>
          </div>

          {/* bottom spacer */}
          <div className="h-6" />
        </div>
      </aside>
    </div>
  );
}
