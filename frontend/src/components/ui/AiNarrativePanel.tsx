import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';

interface AiNarrativePanelProps {
  report?: ExecutiveReport | null;
  bundleKey: 'executive_pdf' | 'seo_pdf' | 'geo_pdf' | 'aeo_pdf' | 'cro_pdf';
  title?: string;
}

export const AiNarrativePanel: React.FC<AiNarrativePanelProps> = ({
  report,
  bundleKey,
  title = 'Enterprise AI Narrative & Verification',
}) => {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);

  if (!report) return null;

  const docNarratives = (report as any).document_narratives || {};
  const bundle = docNarratives[bundleKey];
  const chapterNarratives = (report as any).chapter_narratives || {};
  const coverageLedger = (report as any).coverage_ledger;
  const criticGate = (report as any).quality_gate_results?.critic_gate;

  const chapters: Array<Record<string, any>> = Array.isArray(bundle?.chapters)
    ? bundle.chapters
    : bundleKey === 'seo_pdf'
      ? Object.entries(chapterNarratives)
          .filter(([k, v]) => !/^\d+$/.test(k) && v && typeof v === 'object')
          .map(([k, v]: [string, any]) => ({
            chapter_id: k,
            title: v.title || k.replace(/_/g, ' '),
            executive_takeaway: v.executive_summary || v.summary || '',
            body_md: v.narrative || v.body_md || v.analysis || '',
            why_it_matters: v.business_impact || v.why_it_matters || '',
            cited_finding_ids: v.cited_finding_ids || [],
            epistemic_labels: v.epistemic_labels || [],
          }))
      : [];

  const execSummary = bundle?.executive_summary || (bundleKey === 'executive_pdf' ? report.story_summary : '');

  if (!execSummary && chapters.length === 0 && !coverageLedger && !criticGate) {
    return null;
  }

  return (
    <section
      className="rounded-xl border border-indigo-200/70 bg-gradient-to-br from-indigo-50/60 via-white to-slate-50 p-5 shadow-sm mb-6"
      data-testid={`ai-narrative-panel-${bundleKey}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-indigo-700">
            AI Synthesis &amp; Adversarial Verification
          </div>
          <h3 className="text-base font-semibold text-slate-900">{title}</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {bundle?.narrative_mode && (
            <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 font-medium text-indigo-800">
              Mode: {bundle.narrative_mode}
            </span>
          )}
          {coverageLedger && (
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-medium text-emerald-800">
              AI Verified: {coverageLedger.deterministic_findings_ai_reviewed ?? 0}/
              {coverageLedger.deterministic_findings_total ?? 0} findings
              {coverageLedger.confirmed_count != null ? ` (${coverageLedger.confirmed_count} confirmed)` : ''}
            </span>
          )}
          {criticGate && (
            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 font-medium text-amber-900">
              Critic Gate: {criticGate.verified_count ?? 0} verified
              {criticGate.rejected_count ? `, ${criticGate.rejected_count} rejected` : ''}
            </span>
          )}
        </div>
      </div>

      {execSummary && (
        <p className="text-sm leading-relaxed text-slate-700 mb-4 whitespace-pre-line">
          {execSummary}
        </p>
      )}

      {bundle?.critic_summary && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50/70 px-3.5 py-2 text-xs text-amber-950">
          <span className="font-semibold">Critic Review: </span>
          {typeof bundle.critic_summary === 'string'
            ? bundle.critic_summary
            : JSON.stringify(bundle.critic_summary)}
        </div>
      )}

      {chapters.length > 0 && (
        <div className="space-y-2">
          {chapters.map((ch, idx) => {
            const isOpen = expandedIdx === idx;
            return (
              <div
                key={ch.chapter_id || idx}
                className="rounded-lg border border-slate-200 bg-white overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setExpandedIdx(isOpen ? null : idx)}
                  className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-slate-50 transition-colors"
                >
                  <div className="min-w-0 pr-3">
                    <div className="text-sm font-semibold text-slate-900 truncate">
                      {ch.title || ch.chapter_id || `Chapter ${idx + 1}`}
                    </div>
                    {ch.executive_takeaway && (
                      <div className="text-xs text-slate-600 line-clamp-1 mt-0.5">
                        {ch.executive_takeaway}
                      </div>
                    )}
                  </div>
                  <span className="text-xs font-medium text-indigo-600 shrink-0">
                    {isOpen ? 'Hide' : 'Read AI Analysis'}
                  </span>
                </button>
                {isOpen && (
                  <div className="border-t border-slate-100 px-4 py-3 space-y-2.5 text-sm text-slate-700">
                    {ch.executive_takeaway && (
                      <div className="rounded-md bg-indigo-50/70 px-3 py-2 text-xs font-medium text-indigo-950">
                        <span className="uppercase tracking-wide text-indigo-700 font-semibold">Takeaway: </span>
                        {ch.executive_takeaway}
                      </div>
                    )}
                    {ch.body_md && (
                      <div className="whitespace-pre-line leading-relaxed text-slate-700">
                        {ch.body_md}
                      </div>
                    )}
                    {ch.why_it_matters && (
                      <div className="text-xs text-slate-600">
                        <span className="font-semibold text-slate-800">Why it matters: </span>
                        {ch.why_it_matters}
                      </div>
                    )}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      {Array.isArray(ch.epistemic_labels) &&
                        ch.epistemic_labels.map((lbl: string, i: number) => (
                          <span
                            key={i}
                            className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700"
                          >
                            {lbl}
                          </span>
                        ))}
                      {Array.isArray(ch.cited_finding_ids) && ch.cited_finding_ids.length > 0 && (
                        <span className="text-[11px] text-slate-500">
                          Cited findings: {ch.cited_finding_ids.join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default AiNarrativePanel;
