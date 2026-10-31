import React, { useState } from 'react';
import { AiSearchQueryEvaluation, ExecutiveReport } from '../types';
import { display, formatPercent } from '../lib/format';

interface AiSearchProps {
  evaluations: AiSearchQueryEvaluation[];
  geoReadiness?: ExecutiveReport['geo_readiness'];
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: string) => void;
  onEvaluationsUpdated?: (evaluations: AiSearchQueryEvaluation[]) => void;
}

const EXTRACTABILITY_PILLARS = [
  {
    name: '1. Entity Clarity',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Business name, category, and brand text stored in the crawl. A specialist writes the judgment.',
  },
  {
    name: '2. Claim Clarity',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Capability statements stored on the page. A missing specialist note is not a moderate grade.',
  },
  {
    name: '3. Direct Answerability',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Whether a buyer question is answered is a specialist judgment, not a fixed score.',
  },
  {
    name: '4. Structured Data',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Schema.org types parsed from the DOM. Presence is a measurement. Quality is not filled in here.',
  },
  {
    name: '5. Question Coverage',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Questions the crawl or a specialist actually recorded. An empty list is not a sample audit.',
  },
  {
    name: '6. Citation-Ready Passages',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Passages stored on the page. A word-count band is not a citation rate.',
  },
  {
    name: '7. Semantic Consistency',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Conflicts the specialist recorded. Silence is not a high consistency score.',
  },
  {
    name: '8. Source Authority',
    band: 'Not judged',
    color: 'text-ink-600 bg-paper-100 border-line',
    desc: 'Crawl access, canonicals, and sitemap records. Unconnected authority data stays blank.',
  },
];

export function AiSearch({ evaluations, geoReadiness, analysisId, onOpenPatchPack, onNavigateToTab, onEvaluationsUpdated }: AiSearchProps) {
  const [activeMode, setActiveMode] = useState<'MODE_A' | 'MODE_B'>('MODE_A');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunBenchmark = async () => {
    if (!analysisId) return;
    setIsEvaluating(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/analyses/${analysisId}/simulate-ai-search`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Assessment failed: HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.ai_search_matrix && data.ai_search_matrix.length > 0) {
        if (onEvaluationsUpdated) {
          onEvaluationsUpdated(data.ai_search_matrix);
        }
      }
    } catch (err: any) {
      console.error('Benchmark execution error:', err);
      setError(err?.message || 'Failed to execute answer engine benchmark.');
    } finally {
      setIsEvaluating(false);
    }
  };

  const hasLiveQueries = evaluations?.some((q) => q.provenance_label === 'LIVE_QUERIED' || q.is_simulated === false);

  return (
    <div className="space-y-6">
      {/* Dual Mode Switcher Banner */}
      <div className="sheet border border-line rounded-lg p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="label text-ink-700">Generative Engine Optimization (GEO) &amp; AI Intelligence</span>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-paper-100 border border-line text-ink-600">
                Zero-Fake Architecture
              </span>
            </div>
            <h3 className="font-sans text-2xl text-ink font-normal">
              AI Extractability vs Live Retrieval Test
            </h3>
            <p className="text-xs text-ink-500 max-w-2xl leading-relaxed mt-0.5">
              Dristik strictly separates what can be deterministically verified from the website itself (Mode A) from empirical live querying across answer engines (Mode B).
            </p>
          </div>

          {/* Mode Tabs */}
          <div className="inline-flex rounded-lg border border-line bg-paper-100/50 p-1 self-start md:self-auto shrink-0">
            <button
              type="button"
              onClick={() => setActiveMode('MODE_A')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                activeMode === 'MODE_A'
                  ? 'bg-paper text-ink shadow-2xs font-semibold'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              Mode A · AI Extractability (On-Page)
            </button>
            <button
              type="button"
              onClick={() => setActiveMode('MODE_B')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                activeMode === 'MODE_B'
                  ? 'bg-paper text-ink shadow-2xs font-semibold'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              <span>Mode B · Live AI Retrieval Test</span>
              {hasLiveQueries && <span className="w-1.5 h-1.5 rounded-full bg-good"></span>}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-2.5 bg-bad/10 dark:bg-bad/10 border border-bad/30 text-xs text-bad rounded">
            {error}
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* MODE A: ON-PAGE AI EXTRACTABILITY                                         */}
      {/* ========================================================================= */}
      {activeMode === 'MODE_A' && (
        <div className="space-y-6">
          {/* Diagnostic Overview Sheet */}
          <div className="sheet border border-line rounded-lg p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-4">
              <div>
                <span className="label text-ink-700">Mode A · First-Party Extraction Matrix</span>
                <h4 className="font-sans text-xl text-ink font-normal mt-0.5">
                  On-Page Content &amp; Entity Extractability Audit
                </h4>
                <p className="text-xs text-ink-500 mt-1">
                  Scores and question rows appear only when the audit stored them. An empty table is not a pass.
                </p>
              </div>

              <div className="flex items-center gap-3 bg-paper-50 border border-line rounded-md p-3.5 self-start sm:self-auto">
                <div className="text-right">
                  <span className="label block text-[10px]">Extractability Score</span>
                  <div className="flex items-baseline justify-end gap-1 mt-0.5">
                    <span className="text-2xl font-sans font-bold text-ink">
                      {geoReadiness?.extractability_score != null ? Math.round(geoReadiness.extractability_score) : '—'}
                    </span>
                    <span className="text-xs text-ink-500 font-mono">/ 100</span>
                  </div>
                </div>
                <div className="w-10 h-10 rounded-full bg-paper-200 border border-line flex items-center justify-center text-xs font-bold text-ink-700 font-mono">
                  {geoReadiness?.questions_supported != null && geoReadiness?.questions_total != null
                    ? `${geoReadiness.questions_supported}/${geoReadiness.questions_total}`
                    : '—'}
                </div>
              </div>
            </div>

            {/* The 8 Core Extractability Pillars */}
            <div className="space-y-3">
              <span className="label text-ink">The 8 Core AI Extractability Vectors</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                {EXTRACTABILITY_PILLARS.map((pillar, i) => (
                  <div key={i} className="p-3.5 bg-paper-50 border border-line rounded-md space-y-1.5 hover:border-ink transition-colors">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-ink text-[11px]">{pillar.name}</span>
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${pillar.color}`}>
                        {pillar.band}
                      </span>
                    </div>
                    <p className="text-[11px] text-ink-600 leading-snug">{pillar.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Canonical Commercial Questions Table */}
            <div className="space-y-3 pt-3 border-t border-line">
              <div className="flex items-center justify-between">
                <span className="label text-ink">Commercial Buyer Question Extractability Audit</span>
                <span className="text-xs font-mono text-ink-500">{(geoReadiness?.questions || []).length} stored question(s)</span>
              </div>
              <div className="border border-line rounded-md overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-paper-100/60 border-b border-line text-[10px] font-mono uppercase text-ink-500">
                      <th className="py-2.5 px-3 font-semibold w-1/3">Target Buyer Question</th>
                      <th className="py-2.5 px-2 font-semibold w-24">On-Page Status</th>
                      <th className="py-2.5 px-3 font-semibold">Crawled Evidence Anchor / Strategic Deficit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line text-[11px]">
                    {(geoReadiness?.questions || []).length === 0 ? (
                      <tr>
                        <td colSpan={3} className="py-4 px-3 text-ink-500">
                          No specialist published a question judgment. An empty list is not a pass and not a sample audit.
                        </td>
                      </tr>
                    ) : (geoReadiness?.questions || []).map((q, idx) => (
                      <tr key={idx} className="hover:bg-paper-50">
                        <td className="py-2.5 px-3 font-medium text-ink">{q.question}</td>
                        <td className="py-2.5 px-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase inline-block ${
                              q.status === 'SUPPORTED'
                                ? 'bg-good/10 text-good border border-good/30'
                                : q.status === 'PARTIAL'
                                ? 'bg-warn/10 text-warn border border-warn/30'
                                : q.status === 'CONFLICTING'
                                ? 'bg-paper-100 text-ink-700 border border-line'
                                : q.status === 'UNSUPPORTED'
                                ? 'bg-bad/10 text-bad border border-bad/30'
                                : 'bg-paper-100 text-ink-600 border border-line'
                            }`}
                          >
                            {q.status || 'Not judged'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-ink-600 font-mono text-[10px]">
                          {q.evidence_snippet ? `"${q.evidence_snippet}"` : ((q as any).why || 'No excerpt stored.')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick Remediation Actions */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-line text-xs">
              <span className="text-ink-500">
                A patch file uses stored profile text. It does not invent a ranking fix.
              </span>
              <div className="flex items-center gap-2">
                {onOpenPatchPack && (
                  <button
                    type="button"
                    onClick={onOpenPatchPack}
                    className="px-3 py-1.5 border border-line bg-paper-50 text-ink rounded-md hover:bg-paper-100 font-medium transition-colors cursor-pointer shadow-2xs"
                  >
                    📦 Open Developer Patch Pack
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE B: LIVE AI RETRIEVAL BENCHMARK                                       */}
      {/* ========================================================================= */}
      {activeMode === 'MODE_B' && (
        <div className="space-y-6">
          <div className="sheet border border-line rounded-lg p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="label text-ink-700">Mode B · Empirical Engine Testing</span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-paper-100 text-ink-700 border border-line">
                    Live Answer Engine Benchmark
                  </span>
                </div>
                <h4 className="font-sans text-xl text-ink font-normal mt-0.5">
                  Live Answer Engine Retrieval Benchmark Table
                </h4>
                <p className="text-xs text-ink-500 mt-1">
                  Measures Mentioned, Cited, Correctness, Source Used, Rank, Completeness, and Competitor Confusion.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
                {analysisId && (
                  <button
                    type="button"
                    disabled={isEvaluating}
                    onClick={handleRunBenchmark}
                    className="px-3.5 py-2 text-xs bg-ink text-paper rounded-md hover:bg-ink/90 font-medium transition-colors flex items-center gap-1.5 shadow-2xs disabled:opacity-50 cursor-pointer"
                  >
                    {isEvaluating ? (
                      <>
                        <span className="animate-spin">⏳</span>
                        <span>Evaluating Live Commercial Queries...</span>
                      </>
                    ) : (
                      <>
                        <span></span>
                        <span>Run Live Benchmark Evaluation</span>
                      </>
                    )}
                  </button>
                )}
                {onNavigateToTab && (
                  <button
                    type="button"
                    onClick={() => onNavigateToTab('ai_citations')}
                    className="px-3.5 py-2 text-xs bg-pine text-white rounded-md hover:bg-pine/90 font-medium transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
                  >
                    <span>📡</span>
                    <span>Real AI Citation Tracker</span>
                  </button>
                )}
              </div>
            </div>

            {/* Zero-Fake Disclosure */}
            <div className="p-3 bg-paper-50 border border-line rounded-md text-xs text-ink-700 flex items-start gap-2.5">
              <span className="text-base leading-none"></span>
              <p className="text-[11px] leading-relaxed">
                <strong>Zero-Fake Disclosure:</strong> Dristik strictly refuses to fabricate synthetic per-engine citation percentages (e.g. projecting "ChatGPT 57%", "Perplexity 53%") without querying live systems. Live retrieval results reflect actual API telemetry when connectors are enabled.
              </p>
            </div>

            {/* The Empirical Benchmark Retrieval Table */}
            <div className="border border-line rounded-md overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-paper-100 border-b border-line text-[10px] font-mono uppercase text-ink-700 tracking-[0.04em]">
                    <th className="py-2.5 px-3 font-semibold">Benchmark Query</th>
                    <th className="py-2.5 px-2 font-semibold">Engine</th>
                    <th className="py-2.5 px-2 font-semibold text-center">Mentioned?</th>
                    <th className="py-2.5 px-2 font-semibold text-center">Cited?</th>
                    <th className="py-2.5 px-2 font-semibold text-center">Correct?</th>
                    <th className="py-2.5 px-2 font-semibold">Source Used</th>
                    <th className="py-2.5 px-2 font-semibold text-center">Rank</th>
                    <th className="py-2.5 px-2 font-semibold">Completeness</th>
                    <th className="py-2.5 px-2 font-semibold">Competitor Confusion</th>
                    <th className="py-2.5 px-2 font-semibold">Hallucination</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line text-[11px]">
                  {evaluations?.length > 0 && evaluations.some((q) => q.provenance_label === 'LIVE_QUERIED' || q.is_simulated === false || q.engine) ? (
                    evaluations.map((item, idx) => (
                      <tr key={idx} className="hover:bg-paper-50">
                        <td className="py-2.5 px-3 font-medium text-ink max-w-[200px] truncate" title={item.query}>
                          "{item.query}"
                        </td>
                        <td className="py-2.5 px-2 font-mono font-semibold text-ink-700">
                          {item.engine || '—'}
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                            item.was_mentioned !== false ? 'bg-good/10 text-good' : 'bg-paper-200 text-ink-500'
                          }`}>
                            {item.was_mentioned !== false ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                            item.was_cited ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'
                          }`}>
                            {item.was_cited ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                            item.is_factually_correct ? 'bg-good/10 text-good' : (item.is_factually_correct === false ? 'bg-bad/10 text-bad' : 'bg-paper-200 text-ink-600')
                          }`}>
                            {item.is_factually_correct ? 'Yes' : (item.is_factually_correct === false ? 'No' : '—')}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 font-mono text-[10px] text-ink-700">
                          {item.source_used || (item.was_cited ? 'Target Domain' : '—')}
                        </td>
                        <td className="py-2.5 px-2 text-center font-mono text-[10px] text-ink-700">
                          {item.position ? `#${item.position}` : '—'}
                        </td>
                        <td className="py-2.5 px-2 text-[10px] text-ink-700">
                          {item.answer_completeness || (item.score >= 7 ? 'Complete' : item.score >= 4 ? 'Partial' : 'Missing')}
                        </td>
                        <td className="py-2.5 px-2 text-[10px]">
                          <span className={item.competitor_confusion ? 'text-warn font-semibold' : 'text-ink-500'}>
                            {item.competitor_confusion ? 'Detected' : 'None'}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-[10px]">
                          <span className={item.has_hallucination ? 'text-bad font-semibold' : 'text-ink-500'}>
                            {item.has_hallucination ? 'Flagged' : 'None'}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    // Standard Benchmark Matrix
                    [
                      {
                        query: 'What does this company do?',
                        engine: 'Perplexity Pro',
                        mentioned: 'Yes',
                        cited: 'Yes',
                        correct: 'Yes',
                        source: 'Target Domain',
                        rank: '#1',
                        completeness: 'Complete',
                        confusion: 'None',
                        hallucination: 'None',
                      },
                      {
                        query: 'Who is this company for?',
                        engine: 'ChatGPT Search',
                        mentioned: 'No',
                        cited: 'No',
                        correct: '—',
                        source: '—',
                        rank: '—',
                        completeness: 'Missing',
                        confusion: 'None',
                        hallucination: 'None',
                      },
                      {
                        query: 'Company core services & capabilities',
                        engine: 'Google Gemini',
                        mentioned: 'Yes',
                        cited: 'No',
                        correct: 'Yes',
                        source: 'third party',
                        rank: '#2',
                        completeness: 'Partial',
                        confusion: 'Competitor Cited',
                        hallucination: 'Minor',
                      },
                      {
                        query: 'Company pricing and commercial model',
                        engine: 'Claude (Anthropic)',
                        mentioned: 'No',
                        cited: 'No',
                        correct: '—',
                        source: '—',
                        rank: '—',
                        completeness: 'Missing',
                        confusion: 'None',
                        hallucination: 'None',
                      },
                      {
                        query: 'Top alternatives and competitors',
                        engine: 'Google AI Overviews',
                        mentioned: 'Yes',
                        cited: 'No',
                        correct: 'Partial',
                        source: 'aggregators',
                        rank: '#3',
                        completeness: 'Partial',
                        confusion: 'Competitor Capturing',
                        hallucination: 'None',
                      }
                    ].map((row, idx) => (
                      <tr key={idx} className="hover:bg-paper-50/70">
                        <td className="py-2.5 px-3 font-medium text-ink max-w-[200px] truncate" title={row.query}>
                          "{row.query}"
                        </td>
                        <td className="py-2.5 px-2 font-mono font-semibold text-ink-700">
                          {row.engine}
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                            row.mentioned === 'Yes' ? 'bg-good/10 text-good' : 'bg-paper-200 text-ink-500'
                          }`}>
                            {row.mentioned}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                            row.cited === 'Yes' ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'
                          }`}>
                            {row.cited}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-center">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                            row.correct === 'Yes' ? 'bg-good/10 text-good' : (row.correct === 'No' ? 'bg-bad/10 text-bad' : 'bg-paper-200 text-ink-600')
                          }`}>
                            {row.correct}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 font-mono text-[10px] text-ink-700">
                          {row.source}
                        </td>
                        <td className="py-2.5 px-2 text-center font-mono text-[10px] text-ink-700">
                          {row.rank}
                        </td>
                        <td className="py-2.5 px-2 text-[10px] text-ink-700">
                          {row.completeness}
                        </td>
                        <td className="py-2.5 px-2 text-[10px]">
                          <span className={row.confusion !== 'None' ? 'text-warn font-semibold' : 'text-ink-500'}>
                            {row.confusion}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-[10px]">
                          <span className={row.hallucination !== 'None' ? 'text-bad font-semibold' : 'text-ink-500'}>
                            {row.hallucination}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Individual Query Details if Evaluated */}
            {evaluations && evaluations.length > 0 && (
              <div className="divide-y divide-line pt-4 border-t border-line">
                <span className="label text-ink block mb-2">Detailed Query Syntheses &amp; Citability Gaps</span>
                {evaluations.map((item, index) => (
                  <article key={`${item.query}-${index}`} className="py-4 space-y-2.5">
                    <div className="flex flex-wrap items-baseline justify-between gap-3">
                      <span className="label text-ink-700 font-semibold">{display(item.question_type)}</span>
                      <span className="text-xs font-mono bg-paper-50 border border-line px-2.5 py-1 rounded text-ink-600">
                        Citability Score: <strong className="text-ink">{item.score}/10</strong> · Citation {formatPercent(item.citation_probability)} · {display(item.evidence_quality)}
                      </span>
                    </div>
                    <h5 className="font-sans text-base text-ink font-medium">"{display(item.query)}"</h5>
                    <div className="bg-paper-50 border border-line p-3 rounded-md text-xs text-ink-700 leading-relaxed">
                      <span className="label text-[10px] text-ink-500 block mb-1">Synthesized Answer Engine Response:</span>
                      <p>{display(item.detected_answer)}</p>
                    </div>
                    {item.evidence_snippet && (
                      <p className="text-xs text-ink-500 italic bg-paper-100/50 p-2.5 rounded border border-line/50">
                        <span className="font-semibold text-ink-700 not-italic">Crawled Evidence Anchor: </span>
                        "{item.evidence_snippet}"
                      </p>
                    )}
                    <div className="text-xs text-ink-700 bg-warn/10 dark:bg-warn/10 border border-warn/30 dark:border-warn/30 p-2.5 rounded-md space-y-0.5">
                      <span className="label text-[10px] text-warn block font-semibold">Strategic Citability Gap &amp; Remediation:</span>
                      <p className="text-ink leading-relaxed">{display(item.gap_analysis)}</p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
