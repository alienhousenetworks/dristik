import React, { useState } from 'react';
import { CommercialQueryEvaluation, KieAnswerRisk } from '../types';
import {
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Zap,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Info,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function ScorePill({ score, label }: { score: number; label: string }) {
  const color =
    score >= 7
      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
      : score >= 5
      ? 'bg-amber-100 text-amber-800 border-amber-300'
      : 'bg-rose-100 text-rose-800 border-rose-300';
  return (
    <div className="flex flex-col items-center">
      <span className="text-[10px] font-medium text-ink-500 mb-0.5">{label}</span>
      <span className={`font-mono text-lg font-black px-3 py-1 rounded border ${color}`}>
        {score}/10
      </span>
    </div>
  );
}

function GroundingPill({
  ratio,
  label,
}: {
  ratio?: number | null;
  label: string;
}) {
  if (ratio == null) return null;
  const pct = Math.round(ratio * 100);
  const color =
    pct >= 60
      ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
      : pct >= 30
      ? 'bg-amber-50 border-amber-300 text-amber-800'
      : 'bg-rose-50 border-rose-300 text-rose-800';
  return (
    <div className="flex flex-col items-center">
      <span className="text-[10px] font-medium text-ink-500 mb-0.5">{label}</span>
      <span className={`font-mono text-lg font-black px-3 py-1 rounded border ${color}`}>
        {pct}%
      </span>
      <span className="text-[9px] text-ink-400 mt-0.5">Grounding</span>
    </div>
  );
}

function RiskBadge({ risk }: { risk?: KieAnswerRisk | string | null }) {
  if (!risk) return null;
  const config: Record<string, string> = {
    HIGH: 'bg-rose-100 text-rose-800 border-rose-300',
    MEDIUM: 'bg-amber-100 text-amber-800 border-amber-300',
    LOW: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  };
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${config[risk] ?? 'bg-paper-100 border-line text-ink-600'}`}>
      AI Answer Risk: {risk}
    </span>
  );
}

function EvidenceStatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    VERIFIED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    AMBIGUOUS: 'bg-amber-100 text-amber-800 border-amber-300',
    MISSING: 'bg-rose-100 text-rose-800 border-rose-300',
  };
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded border font-semibold uppercase ${config[status] ?? 'bg-paper-100 border-line text-ink-600'}`}>
      {status}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

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
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const hasEvals = evals.length > 0;
  const hasAfterEvals = hasEvals && evals.some((e) => e.after_score != null);

  // Score averages (Before / After)
  const avgBeforeScore = hasEvals
    ? Math.round(evals.reduce((acc, e) => acc + e.before_score, 0) / evals.length)
    : null;
  const avgAfterScore = hasAfterEvals
    ? Math.round(
        evals.filter((e) => e.after_score != null).reduce((acc, e) => acc + (e.after_score || 0), 0) /
          evals.filter((e) => e.after_score != null).length
      )
    : null;

  // Grounding averages (KIE)
  const evalsWithBeforeGrounding = evals.filter((e) => e.before_grounding_ratio != null);
  const avgBeforeGrounding =
    evalsWithBeforeGrounding.length > 0
      ? Math.round(
          evalsWithBeforeGrounding.reduce((acc, e) => acc + (e.before_grounding_ratio || 0), 0) /
            evalsWithBeforeGrounding.length *
            100
        )
      : null;
  const evalsWithAfterGrounding = evals.filter((e) => e.after_grounding_ratio != null);
  const avgAfterGrounding =
    evalsWithAfterGrounding.length > 0
      ? Math.round(
          evalsWithAfterGrounding.reduce((acc, e) => acc + (e.after_grounding_ratio || 0), 0) /
            evalsWithAfterGrounding.length *
            100
        )
      : null;

  const scoreDelta =
    avgBeforeScore != null && avgAfterScore != null ? avgAfterScore - avgBeforeScore : null;
  const groundingDelta =
    avgBeforeGrounding != null && avgAfterGrounding != null
      ? avgAfterGrounding - avgBeforeGrounding
      : null;

  const highRiskCount = evals.filter((e) => e.answer_risk === 'HIGH').length;

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
        if (data.commercial_evaluations?.length > 0) {
          setEvals(data.commercial_evaluations);
          if (onRequerySuccess) onRequerySuccess(data.commercial_evaluations);
        }
      }
    } catch (err) {
      console.error('Re-query failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="sheet border border-line rounded-lg p-6 space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-pine" />
            <h3 className="font-serif text-xl text-ink">
              Re-Query After Patch — Citation Readiness Diff
            </h3>
          </div>
          <p className="text-xs text-ink-500 mt-1 max-w-2xl">
            Evaluates the same commercial buyer inquiries against the <strong>current raw DOM</strong> (Before)
            vs the <strong>post-patch enriched context</strong> (After: Schema.org + FAQ + llms.txt).
            The <strong>Grounding Ratio</strong> measures what fraction of the synthesized answer is
            backed by first-party crawled evidence — a low ratio flags hallucination risk for
            ChatGPT Search, Perplexity, and Gemini.
          </p>
        </div>

        {/* Delta Summary */}
        {hasEvals && (
          <div className="flex items-center gap-4 bg-paper-50 border border-line px-4 py-3 rounded-md flex-wrap">
            {avgBeforeScore != null && (
              <ScorePill score={avgBeforeScore} label="Before (avg)" />
            )}
            {hasAfterEvals && (
              <>
                <ArrowRight className="w-4 h-4 text-ink-400 mt-4" />
                {avgAfterScore != null && (
                  <ScorePill score={avgAfterScore} label="After Patch (avg)" />
                )}
                {scoreDelta != null && (
                  <div className="border-l border-line pl-3 text-center">
                    <span className="text-[10px] font-medium text-pine block mb-0.5">Score Δ</span>
                    <span className="text-lg font-black text-pine font-mono">+{scoreDelta}</span>
                  </div>
                )}
              </>
            )}
            {avgBeforeGrounding != null && (
              <>
                <div className="border-l border-line pl-3">
                  <GroundingPill ratio={avgBeforeGrounding / 100} label="Before Grounding" />
                </div>
                {avgAfterGrounding != null && (
                  <>
                    <ArrowRight className="w-4 h-4 text-ink-400 mt-4" />
                    <GroundingPill ratio={avgAfterGrounding / 100} label="After Grounding" />
                    {groundingDelta != null && (
                      <div className="border-l border-line pl-3 text-center">
                        <span className="text-[10px] font-medium text-pine block mb-0.5">Grounding Δ</span>
                        <span className="text-lg font-black text-pine font-mono">+{groundingDelta}%</span>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* ── KIE Context Notice ── */}
      {highRiskCount > 0 && (
        <div className="flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-800">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-rose-600" />
          <span>
            <strong>{highRiskCount} inquiry{highRiskCount > 1 ? 'ies' : 'y'} flagged HIGH Answer Risk:</strong>{' '}
            These topics have insufficient first-party evidence, meaning AI answer engines
            are likely to hallucinate or substitute competitor information. Apply the
            recommended patches below before re-querying.
          </span>
        </div>
      )}

      {/* ── Evaluation Cards ── */}
      {!hasEvals ? (
        <div className="p-8 text-center text-ink-500 text-xs border border-dashed border-line rounded-lg bg-paper-50">
          No commercial inquiry evaluations recorded yet.
          Run a commercial inquiry evaluation or verify patch deployment to view genuine citation scores.
        </div>
      ) : (
        <div className="space-y-4">
          {evals.map((item) => {
            const isExpanded = expandedKey === item.question_key;
            return (
              <div
                key={item.question_key}
                className="sheet border border-line rounded-lg overflow-hidden transition-all hover:border-ink-400"
              >
                {/* Card Header */}
                <div
                  className="bg-paper-50 px-4 py-3 border-b border-line flex flex-wrap items-center justify-between gap-2 cursor-pointer select-none"
                  onClick={() => setExpandedKey(isExpanded ? null : item.question_key)}
                >
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="text-xs font-bold text-ink uppercase tracking-wide">
                      {item.question_title}
                    </span>
                    <EvidenceStatusBadge status={item.before_evidence_status} />
                    <RiskBadge risk={item.answer_risk} />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-ink-500 italic">"{item.buyer_query}"</span>
                    <button className="text-ink-400 hover:text-ink">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Before vs After Split */}
                <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-line text-xs">
                  {/* BEFORE */}
                  <div className="p-4 space-y-3 sheet">
                    <div className="flex items-center justify-between">
                      <span className="label text-ink-500 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-ink-400" />
                        Before — Raw DOM Evidence
                      </span>
                      <div className="flex items-center gap-2">
                        {item.before_grounding_ratio != null && (
                          <span className="font-mono text-[10px] text-ink-600 bg-paper-100 border border-line px-1.5 py-0.5 rounded">
                            {Math.round(item.before_grounding_ratio * 100)}% grounded
                          </span>
                        )}
                        <span className="font-bold px-2 py-0.5 rounded bg-paper-50 text-ink-700 border border-line font-mono">
                          {item.before_score}/10
                        </span>
                      </div>
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

                  {/* AFTER */}
                  <div className="p-4 space-y-3 bg-emerald-50/40">
                    <div className="flex items-center justify-between">
                      <span className="label text-good flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-good" />
                        After Patch — Grounded Answer
                      </span>
                      <div className="flex items-center gap-2">
                        {item.after_grounding_ratio != null && (
                          <span className="font-mono text-[10px] text-emerald-700 bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 rounded">
                            {Math.round(item.after_grounding_ratio * 100)}% grounded
                          </span>
                        )}
                        <span className="font-bold px-2 py-0.5 rounded bg-emerald-100 text-good border border-emerald-200 font-mono">
                          {item.after_score != null ? `${item.after_score}/10` : 'Pending'}
                        </span>
                        {item.delta != null && item.delta > 0 && (
                          <span className="font-bold px-1.5 py-0.5 rounded bg-pine-100 text-pine text-[10px] font-mono">
                            +{item.delta}
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-ink-700 leading-relaxed bg-paper-50 p-2.5 rounded border border-emerald-200 font-mono text-[11px] shadow-2xs">
                      {item.after_answer || 'Pending patch application and re-query.'}
                    </p>
                    {item.evidence_snippet && (
                      <blockquote className="text-[11px] text-emerald-800/80 border-l-2 border-emerald-500 pl-2 font-mono">
                        "{item.evidence_snippet}"
                      </blockquote>
                    )}
                    <div className="flex items-center justify-between text-[11px] text-good font-medium pt-1">
                      <span className="flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" />
                        Cites first-party entity graph
                      </span>
                      <span>
                        {item.patch_citation_gain != null
                          ? `+${Math.round(item.patch_citation_gain * 100)}% Citation Readiness`
                          : 'Pending Verification'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Expanded full evidence detail */}
                {isExpanded && (
                  <div className="border-t border-line bg-paper p-4 text-xs space-y-3">
                    <div className="flex items-center gap-1.5 font-semibold text-ink-600 text-[11px]">
                      <Info className="w-3.5 h-3.5" />
                      What this evaluation means
                    </div>
                    <p className="text-ink-600 leading-relaxed">
                      The <strong>Grounding Ratio</strong> measures what fraction of the synthesized answer
                      is directly supported by first-party crawled evidence. A ratio below 35% means an AI
                      answer engine can't reliably ground its response and will hallucinate — substituting
                      competitor evidence or fabricating specifics. Applying the recommended patches
                      (Schema.org markup, FAQ sections, pricing tables) directly increases this ratio.
                    </p>
                    <div className="flex items-center gap-1 text-[11px] text-pine font-semibold">
                      <Zap className="w-3.5 h-3.5" />
                      Fix: Publish a dedicated, citable page section addressing this inquiry with explicit
                      facts, pricing, certifications, or case study data.
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Custom Re-Query Panel ── */}
      <div className="pt-2 border-t border-line">
        <button
          type="button"
          onClick={() => setShowCustomPatch(!showCustomPatch)}
          className="text-xs font-semibold text-pine hover:underline flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          {showCustomPatch
            ? '− Hide Custom Re-Query Simulator'
            : '+ Test Live with Custom Schema or FAQ'}
        </button>

        {showCustomPatch && (
          <div className="mt-3 p-4 bg-paper-50 border border-line rounded-md space-y-3">
            <p className="text-xs text-ink-700">
              Paste your updated Schema.org JSON-LD or FAQ HTML below to simulate how answer engines
              re-index your commercial entities. The live model will re-evaluate every inquiry against
              the patched context and return genuine before → after scores.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="label text-[10px] block mb-1">
                  Custom JSON-LD Schema (optional)
                </label>
                <textarea
                  id="custom-schema-input"
                  value={customSchema}
                  onChange={(e) => setCustomSchema(e.target.value)}
                  placeholder='{"@context": "https://schema.org", "@type": "FAQPage", ...}'
                  rows={4}
                  className="w-full text-xs font-mono p-2 border border-line rounded bg-white text-ink"
                />
              </div>
              <div>
                <label className="label text-[10px] block mb-1">
                  Custom FAQ / Pricing HTML (optional)
                </label>
                <textarea
                  id="custom-faq-input"
                  value={customFaq}
                  onChange={(e) => setCustomFaq(e.target.value)}
                  placeholder="<div class='faq-item'><h3>How much does it cost?</h3><p>Starting at ₹49k...</p></div>"
                  rows={4}
                  className="w-full text-xs font-mono p-2 border border-line rounded bg-white text-ink"
                />
              </div>
            </div>
            <button
              id="run-requery-btn"
              type="button"
              disabled={isLoading}
              onClick={handleRunRequery}
              className="btn-primary font-semibold px-4 py-1.5 rounded text-xs transition-colors shadow-xs disabled:opacity-50"
            >
              {isLoading ? 'Running Live Re-Query...' : 'Run Live Model Re-Query Verification'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
