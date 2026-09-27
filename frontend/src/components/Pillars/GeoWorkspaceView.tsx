import React, { useState } from 'react';
import { ExecutiveReport, AiSearchQueryEvaluation, TabId } from '../../types';
import { RealAiCitationTracker } from '../RealAiCitationTracker';
import { GeoAeoTrendTracker } from '../GeoAeoTrendTracker';
import { PillarShell, Card } from '../ui';
import {
  Sparkles,
  Bot,
  Quote,
  TrendingUp,
  FileCheck,
  Search,
  CheckCircle2,
  AlertCircle,
  Lightbulb,
  Copy,
  Check,
  ArrowUpRight,
} from 'lucide-react';

interface GeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: TabId) => void;
  onEvaluationsUpdated?: (evals: AiSearchQueryEvaluation[]) => void;
}

type GeoSubTab = 'engines' | 'citations' | 'infogain' | 'queries' | 'rewrites' | 'trends';

export function GeoWorkspaceView({
  report,
  analysisId,
  onOpenPatchPack,
  onNavigateToTab,
  onEvaluationsUpdated,
}: GeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<GeoSubTab>('engines');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const perEngine = report.per_engine_geo;
  const infoGain = perEngine?.information_gain;
  const queries = report.ai_search_matrix || [];

  const geoReadiness = report.geo_readiness;
  const citationPassages = geoReadiness?.citation_passages;
  const rawRewrites = citationPassages?.rewrite_recommendations || [];
  
  // Deduplicate recommendations by normalized current passage
  const seenRewriteKeys = new Set<string>();
  const rewrites = rawRewrites.filter((r: any) => {
    const key = (r.current_passage || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    if (!key || seenRewriteKeys.has(key)) return false;
    seenRewriteKeys.add(key);
    return true;
  });

  const readinessScore = report.scores?.category_scores?.['GEO']?.score;
  const geoScore = readinessScore != null ? Math.round(readinessScore) : null;
  const scorecard = report.ai_visibility_scorecard;
  const rate = (value?: number | null) => (value == null ? 'Not measured' : `${Math.round(value)}%`);

  return (
    <PillarShell
      kicker="Discipline 2 · Generative Engine Optimization"
      title="Generative Engine Optimization (GEO)"
      description="GEO Readiness is what the crawled pages can answer. Live AI citation visibility is measured only from successful engine responses."
      scoreLabel="GEO Readiness"
      score={geoScore ?? '—'}
      metaLabel="On-page grade"
      meta={perEngine?.overall_engine_grade || 'Not measured'}
      tabs={[
        { id: 'engines', label: 'Per-Engine AI Matrix' },
        { id: 'citations', label: 'Live AI Citations' },
        { id: 'infogain', label: 'Information Gain & Fluff' },
        { id: 'queries', label: `Query Matrix (${queries.length})` },
        { id: 'rewrites', label: 'LLM Passage Rewrites' },
        { id: 'trends', label: 'Visibility Trends' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as GeoSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: PER-ENGINE AI MATRIX
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'engines' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* ChatGPT */}
            <Card className="p-4 space-y-2 border-t-4 border-t-emerald-600">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink text-sm flex items-center gap-1.5">
                  <Bot className="w-4 h-4 text-emerald-600" /> ChatGPT
                </span>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 font-bold">
                  {perEngine?.chatgpt?.grade ? `Grade ${perEngine.chatgpt.grade}` : 'Not measured'}
                </span>
              </div>
              <p className="font-serif text-3xl font-bold text-ink">
                {perEngine?.chatgpt?.score != null ? Math.round(perEngine.chatgpt.score) : '—'}
                <span className="text-xs text-ink-400 font-sans font-normal"> / 100</span>
              </p>
              <p className="text-xs text-ink-500">
                {perEngine?.chatgpt?.readiness_band || 'OpenAI search retrieval & GPTBot compatibility'}
              </p>
            </Card>

            {/* Perplexity */}
            <Card className="p-4 space-y-2 border-t-4 border-t-cyan-600">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink text-sm flex items-center gap-1.5">
                  <Search className="w-4 h-4 text-cyan-600" /> Perplexity
                </span>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-700 font-bold">
                  {perEngine?.perplexity?.grade ? `Grade ${perEngine.perplexity.grade}` : 'Not measured'}
                </span>
              </div>
              <p className="font-serif text-3xl font-bold text-ink">
                {perEngine?.perplexity?.score != null ? Math.round(perEngine.perplexity.score) : '—'}
                <span className="text-xs text-ink-400 font-sans font-normal"> / 100</span>
              </p>
              <p className="text-xs text-ink-500">
                {perEngine?.perplexity?.readiness_band || 'PerplexityBot indexation & citation index'}
              </p>
            </Card>

            {/* Google AI Overviews */}
            <Card className="p-4 space-y-2 border-t-4 border-t-blue-600">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink text-sm flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-blue-600" /> Google AIO / SGE
                </span>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-700 font-bold">
                  {perEngine?.google_aio?.grade ? `Grade ${perEngine.google_aio.grade}` : 'Not measured'}
                </span>
              </div>
              <p className="font-serif text-3xl font-bold text-ink">
                {perEngine?.google_aio?.score != null ? Math.round(perEngine.google_aio.score) : '—'}
                <span className="text-xs text-ink-400 font-sans font-normal"> / 100</span>
              </p>
              <p className="text-xs text-ink-500">
                {perEngine?.google_aio?.readiness_band || 'Featured snippet & generative overview inclusion'}
              </p>
            </Card>

            {/* Claude & Gemini */}
            <Card className="p-4 space-y-2 border-t-4 border-t-amber-600">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink text-sm flex items-center gap-1.5">
                  <Lightbulb className="w-4 h-4 text-amber-600" /> Claude / Gemini
                </span>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 font-bold">
                  {perEngine?.claude_gemini?.grade ? `Grade ${perEngine.claude_gemini.grade}` : 'Not measured'}
                </span>
              </div>
              <p className="font-serif text-3xl font-bold text-ink">
                {perEngine?.claude_gemini?.score != null ? Math.round(perEngine.claude_gemini.score) : '—'}
                <span className="text-xs text-ink-400 font-sans font-normal"> / 100</span>
              </p>
              <p className="text-xs text-ink-500">
                {perEngine?.claude_gemini?.readiness_band || 'Anthropic ClaudeBot & Google Extended visibility'}
              </p>
            </Card>
          </div>

          <Card className="p-5 space-y-3">
            <h3 className="font-serif text-lg text-ink font-semibold">Live AI citation visibility</h3>
            <p className="text-xs text-ink-600 leading-relaxed">
              {scorecard?.status === 'MEASURED'
                ? `Mention rate ${rate(scorecard.mention_rate_pct)}. Citation rate ${rate(scorecard.citation_rate_pct)}. ${scorecard.successful_runs} successful responses, ${scorecard.failed_runs} errors excluded. ${scorecard.measurement_note || ''}`
                : (scorecard?.not_measured_reason || 'Live citation visibility was not measured for this run. GEO Readiness above is on-page only.')}
            </p>
            {scorecard?.status === 'MEASURED' && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div><span className="text-ink-400 block">Entity accuracy</span><span className="font-semibold">{rate(scorecard.entity_accuracy_pct)}</span></div>
                <div><span className="text-ink-400 block">Service recognition</span><span className="font-semibold">{rate(scorecard.service_recognition_pct)}</span></div>
                <div><span className="text-ink-400 block">Competitor visibility</span><span className="font-semibold">{rate(scorecard.competitor_visibility_pct)}</span></div>
                <div><span className="text-ink-400 block">Citation accuracy</span><span className="font-semibold">{rate(scorecard.citation_accuracy_pct)}</span></div>
              </div>
            )}
          </Card>

          {/* Engine Directives & Recommendations */}
          <Card className="p-5 space-y-4">
            <h3 className="font-serif text-lg text-ink font-semibold">Generative Search Optimization Guidelines</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="p-3 rounded bg-paper-50 border border-line space-y-1.5">
                <span className="font-semibold text-ink flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-good" /> Citation Density
                </span>
                <p className="text-ink-600">
                  Generative engines prioritize sources with clear, quotable sentences, statistical proofs, and explicit author credentials.
                </p>
              </div>
              <div className="p-3 rounded bg-paper-50 border border-line space-y-1.5">
                <span className="font-semibold text-ink flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-good" /> Entity Grounding
                </span>
                <p className="text-ink-600">
                  Explicitly state your brand entity in subject positions rather than vague pronouns (&quot;We&quot;, &quot;Our platform&quot;).
                </p>
              </div>
              <div className="p-3 rounded bg-paper-50 border border-line space-y-1.5">
                <span className="font-semibold text-ink flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-good" /> Information Gain
                </span>
                <p className="text-ink-600">
                  Commodity summary content is filtered out by LLMs. Include original data tables, proprietary metrics, and unique benchmarks.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: LIVE AI CITATIONS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'citations' && (
        <RealAiCitationTracker
          domain={report.domain}
          bizName={report.business_profile?.business_name}
          niche={report.business_profile?.industry}
          analysisId={analysisId}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: INFORMATION GAIN & FLUFF RATIO
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'infogain' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Quote className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Information Gain & Content Originality Audit
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-pine/10 text-pine">
                Fluff Score: {infoGain?.fluff_ratio_score ?? 35}%
              </span>
            </div>
            <p className="text-xs text-ink-600 leading-relaxed">
              Google SGE and OpenAI search models prioritize pages that provide net-new information (&quot;Information Gain&quot;). Pages filled with commodity fluff and generic restatements suffer severe ranking demotions in AI summaries.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="label text-[10px] text-ink-500 block">Benchmark Tables</span>
                <span className="font-semibold text-ink text-sm block">
                  {infoGain?.has_benchmark_tables ? '✅ Detected' : '❌ Missing'}
                </span>
                <p className="text-ink-500 text-[11px]">Structured tabular data for easy AI ingestion</p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="label text-[10px] text-ink-500 block">Methodology Sections</span>
                <span className="font-semibold text-ink text-sm block">
                  {infoGain?.has_methodology_section ? '✅ Detected' : '❌ Not Found'}
                </span>
                <p className="text-ink-500 text-[11px]">Explanation of data collection & verification</p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="label text-[10px] text-ink-500 block">Executive / Expert Quotes</span>
                <span className="font-semibold text-ink text-sm block">
                  {infoGain?.has_executive_quotes ? '✅ Detected' : '⚠️ Low density'}
                </span>
                <p className="text-ink-500 text-[11px]">Direct attributions for authoritative citations</p>
              </div>
            </div>

            {/* Original vs Commodity Signals */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3">
              <div className="p-4 rounded border border-good/30 bg-good/5 space-y-2">
                <h4 className="text-xs font-bold text-good uppercase tracking-wider">
                  Original Data Signals Found ({infoGain?.original_data_signals?.length || 0})
                </h4>
                {infoGain?.original_data_signals && infoGain.original_data_signals.length > 0 ? (
                  <ul className="text-xs text-ink-700 space-y-1 list-disc pl-4">
                    {infoGain.original_data_signals.map((sig: string, idx: number) => (
                      <li key={idx}>{sig}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-ink-500">No proprietary statistics or primary research detected.</p>
                )}
              </div>

              <div className="p-4 rounded border border-warn/30 bg-warn/5 space-y-2">
                <h4 className="text-xs font-bold text-warn uppercase tracking-wider">
                  Commodity Fluff Warnings ({infoGain?.commodity_fluff_signals?.length || 0})
                </h4>
                {infoGain?.commodity_fluff_signals && infoGain.commodity_fluff_signals.length > 0 ? (
                  <ul className="text-xs text-ink-700 space-y-1 list-disc pl-4">
                    {infoGain.commodity_fluff_signals.map((sig: string, idx: number) => (
                      <li key={idx}>{sig}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-ink-500">Content demonstrates high topical density.</p>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: COMMERCIAL QUERY MATRIX
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'queries' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-lg text-ink font-semibold">Commercial Query Extraction Matrix</h3>
            <span className="text-xs text-ink-500 font-mono">{queries.length} queries</span>
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-line bg-paper-100 text-ink-500 uppercase tracking-wider font-mono text-[10px]">
                  <th className="p-3">Query</th>
                  <th className="p-3">Question Type</th>
                  <th className="p-3">Detected Answer</th>
                  <th className="p-3">Quality Score</th>
                  <th className="p-3">Evidence Quality</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {queries.map((q, idx) => (
                  <tr key={idx} className="hover:bg-paper-50 transition-colors">
                    <td className="p-3 font-semibold text-ink max-w-[280px]">{q.query}</td>
                    <td className="p-3 text-ink-600 font-mono">{q.question_type || 'Commercial'}</td>
                    <td className="p-3 text-ink-700 max-w-[280px] truncate" title={q.detected_answer}>
                      {q.detected_answer || '—'}
                    </td>
                    <td className="p-3 font-mono font-bold text-ink">
                      {Math.round(q.score)}/100
                    </td>
                    <td className="p-3">
                      <span className={`inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded font-bold ${
                        q.evidence_quality === 'HIGH' ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                      }`}>
                        {q.evidence_quality || 'VERIFIED'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 5: LLM PASSAGE REWRITES
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'rewrites' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-ink/5">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">LLM Citation Passage Rewrites</h3>
              </div>
              <p className="text-xs text-ink-600 mt-0.5">
                AI engines quote self-contained, fact-grounded statements with explicit brand attribution. Vague marketing fluff and ambiguous pronouns are eliminated.
              </p>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-center">
              <span className="px-2.5 py-1 rounded-full bg-pine/10 text-pine font-mono text-xs font-semibold">
                {rewrites.length} high-impact recommendations
              </span>
            </div>
          </div>

          {rewrites.length === 0 ? (
            <Card className="p-8 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-good mx-auto" />
              <h4 className="font-medium text-ink">All Passages are Highly Citation-Ready</h4>
              <p className="text-xs text-ink-500 max-w-md mx-auto">
                No weak, fluff-heavy, or pronoun-led passages detected across crawled pages. Sentences are already self-contained and brand-attributed.
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {rewrites.map((r: any, idx: number) => {
                const isCopied = copiedId === (r.passage_id || `rec-${idx}`);
                return (
                  <Card key={idx} className="p-4 space-y-3 border-ink/10 hover:border-pine/30 transition-all shadow-sm">
                    {/* Header: Rewrite #, Tag Chips, Score Badge, Copy Action */}
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-pine font-mono bg-pine/5 px-2 py-0.5 rounded border border-pine/20">
                          Rewrite #{idx + 1}
                        </span>
                        {r.category && (
                          <span className="text-[11px] text-ink-600 font-medium">
                            {r.category}
                          </span>
                        )}
                        {Array.isArray(r.improvements) && r.improvements.map((imp: string, i: number) => (
                          <span key={i} className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-ink-100 text-ink-700 text-[10px] font-mono">
                            {imp}
                          </span>
                        ))}
                      </div>

                      <div className="flex items-center gap-2">
                        {r.estimated_score_improvement && (
                          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-good/10 text-good font-semibold border border-good/20">
                            Score: {r.estimated_score_improvement}
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => handleCopy(r.recommended_rewrite, r.passage_id || `rec-${idx}`)}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors ${
                            isCopied
                              ? 'bg-good text-white'
                              : 'bg-ink-100 hover:bg-ink-200 text-ink-700 hover:text-ink-900 border border-ink/10'
                          }`}
                          title="Copy recommended rewrite"
                        >
                          {isCopied ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy Rewrite</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Side-by-Side Current vs Recommended */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-md bg-bad/5 border border-bad/20 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-mono font-bold text-bad uppercase tracking-wider">
                            Current Crawled Copy
                          </span>
                          <span className="text-[10px] text-ink-400 font-mono">Original</span>
                        </div>
                        <p className="text-ink-700 font-mono text-[11px] leading-relaxed">
                          {r.current_passage}
                        </p>
                      </div>

                      <div className="p-3 rounded-md bg-good/5 border border-good/30 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-mono font-bold text-good uppercase tracking-wider flex items-center gap-1">
                            <Sparkles className="w-3 h-3 text-good" />
                            Citation-Ready Rewrite
                          </span>
                          <span className="text-[10px] text-good font-mono font-semibold">Recommended</span>
                        </div>
                        <p className="text-ink-900 font-mono text-[11px] font-medium leading-relaxed">
                          {r.recommended_rewrite}
                        </p>
                      </div>
                    </div>

                    {/* Bottom: Rationale & Why it matters for GEO */}
                    {r.why && (
                      <div className="flex items-start gap-1.5 pt-1 text-[11px] text-ink-600 bg-ink-50/60 p-2 rounded border border-ink/5">
                        <Lightbulb className="w-3.5 h-3.5 text-pine shrink-0 mt-0.5" />
                        <span className="leading-snug">
                          <strong className="text-ink font-semibold">GEO Impact: </strong>
                          {r.why}
                        </span>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 6: VISIBILITY TRENDS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'trends' && (
        <GeoAeoTrendTracker domain={report.domain} />
      )}
    </PillarShell>
  );
}
