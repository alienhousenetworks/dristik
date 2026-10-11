import React, { useState, useEffect } from 'react';

interface EngineQueryResult {
  engine: string;
  was_mentioned: boolean;
  position?: number | null;
  was_cited: boolean;
  cited_url?: string | null;
  source_used?: string;
  is_factually_correct?: boolean | null;
  answer_completeness?: string;
  brand_accuracy?: string;
  competitor_confusion?: boolean;
  has_hallucination?: boolean;
  hallucination_note?: string | null;
  competitor_cited_instead?: string | null;
  source_domains_used: string[];
  synthesized_snippet: string;
  extractability_health: string;
  word_count_impression_pct?: number | null;
  position_adjusted_impression_pct?: number | null;
  dristik_adjusted_impression_pct?: number | null;
  unlinked_brand_mentions?: number;
  failure_reason?: string | null;
  failure_code?: string | null;
}

interface BuyerQueryEvaluation {
  query_id: string;
  buyer_query: string;
  commercial_intent: string;
  monthly_search_volume?: number | null;
  engines: EngineQueryResult[];
  overall_citation_status: string;
  primary_competitor_capturing: string;
  recommended_action: string;
}

interface AiCitationData {
  target_domain: string;
  total_queries_tracked: number;
  overall_ai_citation_score: number | null;
  mention_rate_ci?: [number, number] | null;
  citation_rate_ci?: [number, number] | null;
  word_count_impression_pct?: number | null;
  word_count_impression_ci?: [number, number] | null;
  position_adjusted_impression_pct?: number | null;
  dristik_adjusted_impression_pct?: number | null;
  total_cost_usd?: number | null;
  engines_breakdown: Record<string, number>;
  tracked_queries: BuyerQueryEvaluation[];
  critical_ai_blindspots: string[];
  is_live?: boolean;
  provider_used?: string;
  status_message?: string;
  engines_measured_count?: number;
  engines_total_count?: number;
  failure_reason?: string | null;
  failure_code?: string | null;
  next_steps?: string[];
  engine_errors?: string[];
}

interface RealAiCitationTrackerProps {
  domain: string;
  bizName?: string;
  niche?: string;
  analysisId?: string;
  initialData?: AiCitationData | null;
}

function FailurePanel({
  title,
  reason,
  code,
  nextSteps,
  engineErrors,
  onRetry,
}: {
  title: string;
  reason: string;
  code?: string | null;
  nextSteps?: string[];
  engineErrors?: string[];
  onRetry: () => void;
}) {
  return (
    <div className="p-6 sheet border border-bad/40 rounded-lg space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="label text-bad block mb-1">AI citation tracker failed</span>
          <h3 className="font-sans text-xl text-ink font-normal">{title}</h3>
        </div>
        {code && (
          <span className="text-[10px] font-mono px-2 py-1 rounded border border-line bg-paper-50 text-ink-700 whitespace-nowrap">
            {code}
          </span>
        )}
      </div>
      <p className="text-sm text-ink-700 leading-relaxed">{reason}</p>
      {engineErrors && engineErrors.length > 0 && (
        <div className="bg-paper-50 border border-line rounded-md p-3 space-y-1">
          <span className="label text-[10px] block">Exact engine errors</span>
          <ul className="text-xs font-mono text-ink-700 space-y-1">
            {engineErrors.map((err, i) => (
              <li key={i}>• {err}</li>
            ))}
          </ul>
        </div>
      )}
      {nextSteps && nextSteps.length > 0 && (
        <div className="space-y-1.5">
          <span className="label text-[10px] text-ink-700 block">What to do</span>
          <ol className="list-decimal list-inside text-sm text-ink-700 space-y-1">
            {nextSteps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      )}
      <button
        type="button"
        onClick={onRetry}
        className="px-3 py-1.5 text-xs bg-pine text-white rounded-md hover:bg-pine/90"
      >
        Retry tracker
      </button>
    </div>
  );
}

export function RealAiCitationTracker({
  domain,
  bizName = 'Target Brand',
  niche = 'Software & Technology',
  analysisId,
  initialData,
}: RealAiCitationTrackerProps) {
  const [data, setData] = useState<AiCitationData | null>(initialData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [selectedQuery, setSelectedQuery] = useState<BuyerQueryEvaluation | null>(
    initialData?.tracked_queries?.[0] || null
  );

  const fetchCitations = async () => {
    setLoading(true);
    setError(null);
    setErrorCode(null);
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 55000);
    try {
      const params = new URLSearchParams({
        domain,
        biz_name: bizName,
        niche,
      });
      if (analysisId) params.append('analysis_id', analysisId);

      const resp = await fetch(`/api/v1/intelligence/ai-citations?${params.toString()}`, {
        signal: controller.signal,
      });
      const raw = await resp.text();
      let json: AiCitationData | null = null;
      try {
        json = raw ? JSON.parse(raw) : null;
      } catch {
        json = null;
      }

      if (!resp.ok) {
        const detail = (json as unknown as { detail?: string } | null)?.detail;
        setData(null);
        setErrorCode(`HTTP ${resp.status}`);
        setError(
          detail ||
            `The citation API returned HTTP ${resp.status}. ${raw.slice(0, 280) || 'Empty body.'} Check that the API is running and the intelligence route is mounted.`
        );
        return;
      }

      if (!json) {
        setData(null);
        setErrorCode('empty_body');
        setError('The citation API returned an empty body. Restart the backend and retry.');
        return;
      }

      setData(json);
      if (json.tracked_queries?.length > 0) {
        setSelectedQuery(json.tracked_queries[0]);
      } else {
        setSelectedQuery(null);
      }
    } catch (e) {
      const aborted = e instanceof DOMException && e.name === 'AbortError';
      setData(null);
      setErrorCode(aborted ? 'timeout' : 'network');
      setError(
        aborted
          ? 'The tracker waited 55 seconds with no response. The eight-engine fan-out is hanging or the API is down. Restart the API, confirm OPENROUTER_API_KEY / PERPLEXITY_API_KEY, then retry.'
          : `Could not reach the citation API: ${e instanceof Error ? e.message : String(e)}. Start the backend (uvicorn) and confirm /api/v1/intelligence/ai-citations is reachable.`
      );
    } finally {
      window.clearTimeout(timer);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialData && initialData.tracked_queries && initialData.tracked_queries.length > 0) {
      setData(initialData);
      setSelectedQuery(initialData.tracked_queries[0]);
      return;
    }
    fetchCitations();
  }, [domain, bizName, niche, analysisId, initialData]);

  if (loading) {
    return (
      <div className="p-8 sheet border border-line rounded-lg flex flex-col items-center justify-center gap-2 text-ink-500">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-line border-t-transparent rounded-full animate-spin"></div>
          <span>Querying live answer engines (up to ~45s)…</span>
        </div>
        <p className="text-xs text-ink-500 max-w-xl text-center">
          If this does not finish, the provider key is missing, unauthorized, out of credits, or a model id is unavailable. The result will name the exact reason instead of hanging.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <FailurePanel
        title="Could not load AI citations"
        reason={error}
        code={errorCode}
        nextSteps={[
          'Confirm the API process is running.',
          'Set OPENROUTER_API_KEY or PERPLEXITY_API_KEY in backend/.env and restart.',
          'Retry. If HTTP 401/403, the key is wrong. If 402, add credits. If timeout, the provider is slow or blocked.',
        ]}
        onRetry={fetchCitations}
      />
    );
  }

  if (!data) {
    return (
      <FailurePanel
        title="No citation payload"
        reason="The tracker returned nothing. This is a failed load, not an empty audit."
        code="no_data"
        nextSteps={['Retry.', 'If it repeats, restart the API and check backend logs for ai_citation_tracker.']}
        onRetry={fetchCitations}
      />
    );
  }

  if (!data.is_live) {
    return (
      <FailurePanel
        title="Live citation tracking is unavailable"
        reason={data.failure_reason || data.status_message || 'Engines were not measured. Score kept null.'}
        code={data.failure_code}
        nextSteps={
          data.next_steps && data.next_steps.length > 0
            ? data.next_steps
            : [
                'Add OPENROUTER_API_KEY or PERPLEXITY_API_KEY to backend/.env.',
                'Restart the API and retry this panel.',
              ]
        }
        engineErrors={data.engine_errors}
        onRetry={fetchCitations}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="sheet border border-line rounded-lg p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${data.is_live ? 'bg-good animate-pulse' : 'bg-warn'}`}></span>
              <span className="label text-ink-700">
                {data.is_live ? `Live Citations · ${data.provider_used || 'Active Search'}` : 'Target Domain Evaluation'}
              </span>
              {data.is_live && (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-good/10 text-good border border-good/20 font-semibold">
                  {data.engines_measured_count
                    ? `${data.engines_measured_count} of ${data.engines_total_count || 8} ENGINES MEASURED`
                    : 'LIVE GROUNDED MEASUREMENT'}
                </span>
              )}
            </div>
            <h3 className="font-sans text-2xl md:text-3xl text-ink font-normal">
              AI Answer Engine Citation Graph
            </h3>
            <p className="text-xs text-ink-500 mt-1 max-w-xl leading-relaxed">
              {data.status_message || (
                data.is_live
                  ? "Real-time evaluation across top frontier AI engines. Inspects citations, rankings, and competitor displacement."
                  : "Evaluates high-intent commercial queries across Gemini, ChatGPT, Claude, Qwen, DeepSeek, Perplexity, Grok, and Llama."
              )}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-end sm:items-center gap-3">
            <div className="flex items-center gap-4 bg-paper-50 dark:bg-ink-900 border border-line rounded-md p-4 shrink-0">
              <div className="text-right">
                <span className="label block text-[10px]">Overall AI Citation Score</span>
                <div className="flex items-baseline justify-end gap-1 mt-0.5">
                  <span className="text-3xl font-sans font-bold text-good">
                    {data.overall_ai_citation_score != null ? data.overall_ai_citation_score : '—'}
                  </span>
                  <span className="text-xs text-ink-500 font-mono">/ 100</span>
                </div>
                {data.citation_rate_ci && (
                  <span className="text-[10px] font-mono text-ink-400 block mt-0.5" title="95% Wilson Score Confidence Interval">
                    95% CI: [{data.citation_rate_ci[0]}% – {data.citation_rate_ci[1]}%]
                  </span>
                )}
              </div>
              <div className="w-12 h-12 rounded-full border-2 border-line bg-paper-100 dark:bg-ink-800 flex items-center justify-center font-bold text-sm text-ink font-mono">
                {data.total_queries_tracked}Q
              </div>
            </div>
          </div>
        </div>

        {/* CONTINUOUS IMPRESSION METRICS STRIP (AGGARWAL ET AL., KDD 2024) */}
        {(data.word_count_impression_pct != null || data.position_adjusted_impression_pct != null) && (
          <div className="mt-4 pt-4 border-t border-line grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-paper-100/60 dark:bg-ink-900/60 p-3 rounded-md border border-line space-y-1">
              <div className="flex items-center justify-between">
                <span className="label text-[10px] text-ink-500">Paper Imp_wc (Word-Count)</span>
                <span className="text-[9px] font-mono bg-paper-200 dark:bg-ink-800 text-ink-600 px-1.5 py-0.5 rounded">Continuous</span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold font-mono text-ink">{data.word_count_impression_pct}%</span>
                {data.word_count_impression_ci && (
                  <span className="text-[10px] font-mono text-ink-400">
                    [{data.word_count_impression_ci[0]}%–{data.word_count_impression_ci[1]}%]
                  </span>
                )}
              </div>
              <p className="text-[10px] text-ink-500 leading-tight">Words in sentences citing target domain</p>
            </div>

            <div className="bg-paper-100/60 dark:bg-ink-900/60 p-3 rounded-md border border-line space-y-1">
              <div className="flex items-center justify-between">
                <span className="label text-[10px] text-ink-500">Paper Imp_pwc (Pos-Weighted)</span>
                <span className="text-[9px] font-mono bg-paper-200 dark:bg-ink-800 text-ink-600 px-1.5 py-0.5 rounded">Exp Decay</span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold font-mono text-ink">{data.position_adjusted_impression_pct}%</span>
              </div>
              <p className="text-[10px] text-ink-500 leading-tight">Discounted by position exp(-pos/total)</p>
            </div>

            <div className="bg-paper-100/60 dark:bg-ink-900/60 p-3 rounded-md border border-line space-y-1">
              <div className="flex items-center justify-between">
                <span className="label text-[10px] text-ink-500">Dristik-Adjusted Imp</span>
                <span className="text-[9px] font-mono bg-paper-200 dark:bg-ink-800 text-ink-600 px-1.5 py-0.5 rounded">Credit-Split</span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold font-mono text-ink">{data.dristik_adjusted_impression_pct}%</span>
              </div>
              <p className="text-[10px] text-ink-500 leading-tight">Sentence credit split by cited sources |C_s|</p>
            </div>
          </div>
        )}

        {data.engine_errors && data.engine_errors.length > 0 && (
          <div className="mt-4 bg-warn/10 border border-warn/30 rounded-md p-3 text-xs text-ink-700">
            <span className="label text-warn block mb-1">Partial engine failures</span>
            <ul className="space-y-0.5 font-mono">
              {data.engine_errors.map((err, i) => (
                <li key={i}>• {err}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 mt-6 pt-5 border-t border-line text-xs">
          {Object.entries(data.engines_breakdown || {}).map(([engine, pct]) => (
            <div key={engine} className="bg-paper-50 border border-line p-2.5 rounded-md hover:border-ink transition-colors">
              <span className="text-[11px] font-medium text-ink-700 block truncate" title={engine}>{engine}</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="font-mono font-bold text-ink">{pct}%</span>
                <span className={`text-[10px] font-semibold ${pct >= 50 ? 'text-good' : 'text-warn'}`}>
                  {pct >= 50 ? 'Cited' : 'Gap'}
                </span>
              </div>
              <div className="w-full bg-paper-300 h-1.5 rounded-full mt-1.5 overflow-hidden">
                <div
                  className={`h-full ${pct >= 50 ? 'bg-good' : 'bg-warn'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="label text-ink">
            Tracked High-Intent Commercial Buyer Inquiries
          </span>
          <span className="text-xs text-ink-500">Click a query to inspect live answer graph</span>
        </div>

        {data.tracked_queries.length === 0 ? (
          <div className="p-8 text-center bg-paper-50 rounded-lg border border-line text-ink-500 text-xs">
            No live citation queries tracked for this domain yet. Connect an engine API or trigger an audit to evaluate commercial queries.
          </div>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {data.tracked_queries.map((q) => {
            const isSelected = selectedQuery?.query_id === q.query_id;
            return (
              <button
                key={q.query_id}
                type="button"
                onClick={() => setSelectedQuery(q)}
                className={`text-left p-3.5 rounded-lg border transition-all ${
                  isSelected
                    ? 'sheet border-2 border-line shadow-xs'
                    : 'bg-paper-50 border-line hover:border-ink-400'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
                    {q.commercial_intent}
                  </span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                    q.overall_citation_status === 'Dominant'
                      ? 'bg-good/10 text-good border-good/30'
                      : q.overall_citation_status === 'At Risk'
                      ? 'bg-warn/10 text-warn border-warn/30'
                      : 'bg-bad/10 text-bad border-bad/30'
                  }`}>
                    {q.overall_citation_status}
                  </span>
                </div>
                <p className="text-xs font-semibold line-clamp-2 leading-relaxed text-ink">
                  "{q.buyer_query}"
                </p>
                <p className="text-[11px] text-ink-500 mt-2">
                  Vol: <span className="font-mono text-ink font-semibold">{q.monthly_search_volume != null ? `${q.monthly_search_volume}/mo` : 'not measured'}</span>
                  {' · '}Comp: <span className="text-warn font-medium">{q.primary_competitor_capturing}</span>
                </p>
              </button>
            );
          })}
        </div>
        )}
      </div>

      {/* Mode B Live Retrieval Benchmark Table */}
      {data.tracked_queries.length > 0 && (
        <div className="sheet border border-line rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="label text-ink-700">Mode B · Live Answer Engine Retrieval Benchmark</span>
            <span className="text-xs font-mono text-ink-500">Zero-Fake Empirical Telemetry</span>
          </div>
          <div className="border border-line rounded-md overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-paper-100 border-b border-line text-[10px] font-mono uppercase text-ink-700 tracking-[0.04em]">
                  <th className="py-2.5 px-3 font-semibold">Buyer Query</th>
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
                {data.tracked_queries.flatMap((q) =>
                  q.engines.map((eng, idx) => (
                    <tr key={`${q.query_id}-${eng.engine}-${idx}`} className="hover:bg-paper-50">
                      <td className="py-2 px-3 font-medium text-ink max-w-[200px] truncate" title={q.buyer_query}>
                        "{q.buyer_query}"
                      </td>
                      <td className="py-2 px-2 font-mono font-semibold text-ink-700">
                        {eng.engine}
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                          eng.was_mentioned ? 'bg-good/10 text-good' : 'bg-paper-200 text-ink-500'
                        }`}>
                          {eng.was_mentioned ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                          eng.was_cited ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'
                        }`}>
                          {eng.was_cited ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                          eng.is_factually_correct ? 'bg-good/10 text-good' : (eng.is_factually_correct === false ? 'bg-bad/10 text-bad' : 'bg-paper-200 text-ink-600')
                        }`}>
                          {eng.is_factually_correct ? 'Yes' : (eng.is_factually_correct === false ? 'No' : '—')}
                        </span>
                      </td>
                      <td className="py-2 px-2 font-mono text-[10px] text-ink-700">
                        {eng.source_used || (eng.was_cited ? data.target_domain : (eng.source_domains_used?.[0] || '—'))}
                      </td>
                      <td className="py-2 px-2 text-center font-mono text-[10px] text-ink-700">
                        {eng.position ? `#${eng.position}` : '—'}
                      </td>
                      <td className="py-2 px-2 text-[10px] text-ink-700">
                        {eng.answer_completeness || (eng.was_cited ? 'Complete' : eng.was_mentioned ? 'Partial' : 'Missing')}
                      </td>
                      <td className="py-2 px-2 text-[10px]">
                        <span className={eng.competitor_cited_instead || eng.competitor_confusion ? 'text-warn font-semibold' : 'text-ink-500'}>
                          {eng.competitor_cited_instead ? `Cited: ${eng.competitor_cited_instead}` : (eng.competitor_confusion ? 'Detected' : 'None')}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-[10px]">
                        <span className={eng.has_hallucination ? 'text-bad font-semibold' : 'text-ink-500'}>
                          {eng.has_hallucination ? 'Flagged' : 'None'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedQuery && (
        <div className="sheet border border-line rounded-lg p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
            <div>
              <span className="label text-[10px]">Target Query</span>
              <h4 className="text-base font-sans text-ink mt-0.5">"{selectedQuery.buyer_query}"</h4>
            </div>
            <div className="bg-paper-50 px-3 py-1.5 rounded-md border border-line text-xs">
              <span className="text-ink-500">Remediation Action: </span>
              <span className="text-good font-semibold">{selectedQuery.recommended_action}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {selectedQuery.engines.map((eng, idx) => (
              <div
                key={idx}
                className="bg-paper-50 border border-line rounded-md p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-pine"></span>
                    <span className="font-bold text-sm text-ink">{eng.engine}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {eng.extractability_health === 'UNAVAILABLE' ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded border bg-warn/10 text-warn border-warn/30">
                        Unmeasured
                      </span>
                    ) : (
                      <>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          eng.was_mentioned ? 'bg-good/10 text-good border-good/30' : 'bg-paper-200 text-ink-500 border-line'
                        }`}>
                          {eng.was_mentioned ? (eng.position ? `Mentioned (#${eng.position})` : 'Mentioned') : 'Omitted'}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          eng.was_cited ? 'bg-paper-200 text-ink-700 border-line' : 'bg-bad/10 text-bad border-bad/30'
                        }`}>
                          {eng.was_cited ? 'URL Cited' : 'No Link'}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <div className="bg-paper-200/50 border border-line rounded p-3 text-xs text-ink-700 font-mono leading-relaxed">
                  <span className="label text-[10px] block mb-1">
                    {eng.failure_reason ? 'Failure reason' : 'Generated Output Snippet'}
                  </span>
                  "{eng.failure_reason || eng.synthesized_snippet}"
                </div>

                {eng.failure_code && (
                  <p className="text-[11px] font-mono text-warn">Code: {eng.failure_code}</p>
                )}

                <div className="text-xs space-y-1.5 pt-1">
                  {eng.competitor_cited_instead && (
                    <div className="flex items-start gap-1.5 text-warn">
                      <span className="font-bold"> Competitor Cited Instead:</span>
                      <span className="font-medium text-ink">{eng.competitor_cited_instead}</span>
                    </div>
                  )}
                  {eng.source_domains_used.length > 0 && (
                    <div className="flex items-center gap-1.5 text-ink-500">
                      <span>Source Authorities:</span>
                      <div className="flex flex-wrap gap-1">
                        {eng.source_domains_used.map((src, i) => (
                          <span key={i} className="text-[10px] bg-paper-200 border border-line px-1.5 py-0.5 rounded text-ink-700">
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.critical_ai_blindspots?.length > 0 && (
        <div className="bg-bad/10 border border-bad/30 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2 label text-bad">
            <span>Identified AI Citation Blindspots</span>
          </div>
          <ul className="space-y-1.5 text-xs text-ink-700">
            {data.critical_ai_blindspots.map((blindspot, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-bad font-bold">•</span>
                <span>{blindspot}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
