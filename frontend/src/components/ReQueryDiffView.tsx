import React, { useState } from 'react';
import { CommercialQueryEvaluation } from '../types';

interface ReQueryDiffViewProps {
  analysisId: string;
  evaluations: CommercialQueryEvaluation[];
  onRequerySuccess?: (updated: CommercialQueryEvaluation[]) => void;
}

export function ReQueryDiffView({
  analysisId,
  evaluations: initialEvaluations,
  onRequerySuccess,
}: ReQueryDiffViewProps) {
  const [evals, setEvals] = useState<CommercialQueryEvaluation[]>(initialEvaluations || []);
  const [customSchema, setCustomSchema] = useState('');
  const [customFaq, setCustomFaq] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showCustomPatch, setShowCustomPatch] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('all');

  const hasEvaluations = evals.length > 0;
  const hasAfterEvaluations = hasEvaluations && evals.some((e) => e.after_score != null);

  const avgBefore = hasEvaluations
    ? Math.round((evals.reduce((acc, e) => acc + e.before_score, 0) / evals.length) * 10)
    : null;
  const avgAfter = hasAfterEvaluations
    ? Math.round(
        (evals.filter((e) => e.after_score != null).reduce((acc, e) => acc + (e.after_score || 0), 0) /
          evals.filter((e) => e.after_score != null).length) *
          10
      )
    : null;
  const gainPct = avgBefore != null && avgAfter != null ? avgAfter - avgBefore : null;

  const handleRunRequery = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/v1/analyses/${analysisId}/re-query`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          custom_schema: customSchema || undefined,
          custom_faq: customFaq || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.commercial_evaluations && data.commercial_evaluations.length > 0) {
          setEvals(data.commercial_evaluations);
          if (onRequerySuccess) onRequerySuccess(data.commercial_evaluations);
        }
      }
    } catch (err) {
      console.error('Re-query request failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'AMBIGUOUS':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      default:
        return 'bg-red-100 text-red-800 border-red-300';
    }
  };

  const filteredEvals = activeTab === 'all' ? evals : evals.filter((e) => e.question_key === activeTab);

  return (
    <div className="sheet border border-line rounded-lg p-6 space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-pine"></span>
            <h3 className="font-serif text-xl text-ink">
              Re-Query After Patch: Before → After Citation Readiness
            </h3>
          </div>
          <p className="text-xs text-ink-500 mt-1">
            Evaluates the same 6 commercial buyer inquiries across current raw DOM vs post-patch structured context (Schema.org + FAQ + llms.txt).
          </p>
        </div>

        {/* Citation Delta Metric (Rendered only if evaluations exist) */}
        {hasEvaluations ? (
          <div className="flex items-center gap-4 bg-paper-50 border border-line px-4 py-2 rounded-md">
            <div className="text-center">
              <span className="label text-[10px] block">Before</span>
              <span className="text-lg font-bold text-ink-700 font-mono">{avgBefore}%</span>
            </div>
            <div className="text-ink-400">→</div>
            <div className="text-center">
              <span className="label text-[10px] text-good block">After Patch</span>
              <span className="text-xl font-black text-good font-mono">
                {avgAfter != null ? `${avgAfter}%` : 'Pending'}
              </span>
            </div>
            {gainPct != null && (
              <div className="border-l border-line pl-3 text-center">
                <span className="label text-[10px] text-pine block">Delta</span>
                <span className="text-sm font-bold text-pine font-mono">+{gainPct}% Gain</span>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-paper-50 border border-line px-3 py-2 rounded-md text-xs text-ink-500 italic">
            No before/after evaluation is available yet
          </div>
        )}
      </div>


      {/* Inquiry Navigation Filter */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <button
          type="button"
          onClick={() => setActiveTab('all')}
          className={`px-3 py-1 rounded-full font-medium transition-colors ${
            activeTab === 'all'
              ? 'btn-primary'
              : 'bg-paper-50 text-ink-700 hover:bg-paper-200 border border-line'
          }`}
        >
          All 6 Questions ({evals.length})
        </button>
        {evals.map((e) => (
          <button
            key={e.question_key}
            type="button"
            onClick={() => setActiveTab(e.question_key)}
            className={`px-3 py-1 rounded-full font-medium transition-colors ${
              activeTab === e.question_key
                ? 'btn-primary'
                : 'bg-paper-50 text-ink-700 hover:bg-paper-200 border border-line'
            }`}
          >
            {e.question_title}
          </button>
        ))}
      </div>

      {/* Before vs After Cards Grid */}
      <div className="space-y-4">
        {filteredEvals.length === 0 ? (
          <div className="p-8 text-center text-ink-500 text-xs border border-dashed border-line rounded-lg bg-paper-50">
            No commercial inquiry evaluations recorded yet. Run a commercial inquiry evaluation or verify patch deployment to view genuine citation scores.
          </div>
        ) : (
          filteredEvals.map((item) => (
            <div
              key={item.question_key}
              className="sheet border border-line rounded-lg overflow-hidden transition-all hover:border-ink-400"
            >
            {/* Header */}
            <div className="bg-paper-50 px-4 py-2.5 border-b border-line flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-bold text-ink uppercase tracking-wide">
                  {item.question_title}
                </span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded border font-semibold uppercase ${getStatusBadge(
                    item.before_evidence_status
                  )}`}
                >
                  Raw Evidence: {item.before_evidence_status}
                </span>
              </div>
              <div className="text-xs text-ink-500 italic">
                "{item.buyer_query}"
              </div>
            </div>

            {/* Before vs After Split */}
            <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-line text-xs">
              {/* BEFORE (Raw DOM) */}
              <div className="p-4 space-y-2 sheet">
                <div className="flex items-center justify-between">
                  <span className="label text-ink-500 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-ink-400"></span>
                    Current Answer (ChatGPT / Perplexity)
                  </span>
                  <span className="font-bold px-2 py-0.5 rounded bg-paper-50 text-ink-700 border border-line font-mono">
                    Citability: {item.before_score}/10
                  </span>
                </div>
                <p className="text-ink-700 leading-relaxed bg-paper-50 p-2.5 rounded border border-line font-mono text-[11px]">
                  {item.before_answer}
                </p>
                {item.gap_analysis && (
                  <p className="text-[11px] text-bad font-medium">
                    <span className="font-semibold">Retrieval Bottleneck:</span> {item.gap_analysis}
                  </p>
                )}
              </div>

              {/* AFTER (Post-Patch Schema + FAQ) */}
              <div className="p-4 space-y-2 bg-emerald-50/40">
                <div className="flex items-center justify-between">
                  <span className="label text-good flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-good"></span>
                    Grounded Answer (Post-Patch Re-Query)
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold px-2 py-0.5 rounded bg-emerald-100 text-good border border-emerald-200 font-mono">
                      Citability: {item.after_score != null ? `${item.after_score}/10` : 'Pending re-query'}
                    </span>
                    {item.delta != null && (
                      <span className="font-bold px-1.5 py-0.5 rounded bg-pine-100 text-pine text-[10px] font-mono">
                        +{item.delta}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-ink-700 leading-relaxed bg-paper-50 p-2.5 rounded border border-emerald-200 font-mono text-[11px] shadow-2xs">
                  {item.after_answer || 'Pending patch application and live engine re-query.'}
                </p>
                <div className="flex items-center justify-between text-[11px] text-good font-medium pt-1">
                  <span>✓ Cites official entity graph</span>
                  <span>
                    {item.patch_citation_gain != null
                      ? `+${Math.round(item.patch_citation_gain * 100)}% Citation Readiness`
                      : 'Pending Verification'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )))}
      </div>


      {/* Interactive Custom Re-Query Toggle */}
      <div className="pt-2 border-t border-line">
        <button
          type="button"
          onClick={() => setShowCustomPatch(!showCustomPatch)}
          className="text-xs font-semibold text-pine hover:underline flex items-center gap-1.5"
        >
          <span>{showCustomPatch ? '− Hide Custom Re-Query Simulator' : '+ Test Live with Custom Schema or FAQ Paste'}</span>
        </button>

        {showCustomPatch && (
          <div className="mt-3 p-4 bg-paper-50 border border-line rounded-md space-y-3">
            <p className="text-xs text-ink-700">
              Paste your updated Schema.org JSON-LD or FAQ HTML below to simulate how answer engines re-index your commercial entities in real time:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="label text-[10px] block mb-1">
                  Custom JSON-LD Schema (optional)
                </label>
                <textarea
                  value={customSchema}
                  onChange={(e) => setCustomSchema(e.target.value)}
                  placeholder='{"@context": "https://schema.org", "@type": "FAQPage", ...}'
                  rows={4}
                  className="w-full text-xs font-mono p-2 border border-line rounded bg-white text-ink"
                />
              </div>
              <div>
                <label className="label text-[10px] block mb-1">
                  Custom FAQ HTML / Pricing (optional)
                </label>
                <textarea
                  value={customFaq}
                  onChange={(e) => setCustomFaq(e.target.value)}
                  placeholder="<div class='faq-item'><h3>How much does it cost?</h3><p>Starting at ₹49k...</p></div>"
                  rows={4}
                  className="w-full text-xs font-mono p-2 border border-line rounded bg-white text-ink"
                />
              </div>
            </div>
            <button
              type="button"
              disabled={isLoading}
              onClick={handleRunRequery}
              className="btn-primary font-semibold px-4 py-1.5 rounded text-xs transition-colors shadow-xs disabled:opacity-50"
            >
              {isLoading ? 'Querying Live Answer Engines...' : 'Run Live Model Re-Query Verification'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
