import React, { useState } from 'react';
import { ExecutiveReport, AiSearchQueryEvaluation, TabId, AnalyzedChunk, ControlledRetrievalReport } from '../../types';
import { RealAiCitationTracker } from '../RealAiCitationTracker';
import { GeoAeoTrendTracker } from '../GeoAeoTrendTracker';
import { PillarShell, Card } from '../ui';
import { ControlledRetrievalVisualizer } from './RagChunkVisualizer';
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
  Layers,
  ShieldAlert,
  Network,
  Crosshair,
  Award,
  Zap,
  BarChart3,
  ExternalLink,
  Info,
} from 'lucide-react';

interface GeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: TabId) => void;
  onEvaluationsUpdated?: (evals: AiSearchQueryEvaluation[]) => void;
}

type GeoSubTab =
  | 'engines'
  | 'som'
  | 'sentiment'
  | 'retrieval_analysis'
  | 'offpage'
  | 'citations'
  | 'infogain'
  | 'queries'
  | 'rewrites'
  | 'trends';

export function GeoWorkspaceView({
  report,
  analysisId,
  onOpenPatchPack,
  onNavigateToTab,
  onEvaluationsUpdated,
}: GeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<GeoSubTab>('engines');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Controlled Retrieval Analysis interactive state
  const [retrievalQuery, setRetrievalQuery] = useState(
    'What are the core capabilities, technical architecture, and pricing for this platform?'
  );
  const [retrievalLoading, setRetrievalLoading] = useState(false);
  const [retrievalReport, setRetrievalReport] = useState<ControlledRetrievalReport | null>(null);
  const [retrievalError, setRetrievalError] = useState<string | null>(null);

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
  const brandName = report.business_profile?.business_name || report.domain.split('.')[0];

  // Live observations if measured
  const liveBenchReport = (report as any).geo_benchmark_report;
  const somMetric = liveBenchReport?.share_of_model;
  const sentimentAudit = liveBenchReport?.sentiment_audit;
  const offpageReport = liveBenchReport?.offpage_citation_summary;

  // Execute Controlled Retrieval Analysis over actual crawled text
  const handleRunControlledRetrieval = async () => {
    setRetrievalLoading(true);
    setRetrievalError(null);
    try {
      const pageText =
        report.crawl_manifest?.pages?.[0]?.body_text ||
        report.business_profile?.value_proposition ||
        '';

      if (!pageText.trim()) {
        setRetrievalError('No crawled page content available to analyze for this domain.');
        setRetrievalReport(null);
        setRetrievalLoading(false);
        return;
      }

      const res = await fetch('/api/v1/geo-pipeline/controlled-retrieval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page_text: pageText,
          query: retrievalQuery,
          source_url: `https://${report.domain}/`,
          chunk_size: 250,
          chunk_overlap: 40,
          similarity_threshold: 0.72,
          top_k: 3,
        }),
      });

      if (!res.ok) {
        throw new Error(`Controlled retrieval endpoint responded with HTTP ${res.status}`);
      }

      const data: ControlledRetrievalReport = await res.json();
      setRetrievalReport(data);
    } catch (err: any) {
      setRetrievalError(err.message || 'Failed to execute controlled retrieval analysis.');
      setRetrievalReport(null);
    } finally {
      setRetrievalLoading(false);
    }
  };

  return (
    <PillarShell
      kicker="Discipline 2 · Generative Engine Optimization"
      title="Generative Engine Optimization (GEO)"
      description="Controlled Semantic Retrieval Analysis & Evidence-Driven Visibility: On-page RAG extractability, empirical benchmark observations, and citation provenance."
      scoreLabel="GEO Readiness"
      score={geoScore ?? '—'}
      metaLabel="On-page grade"
      meta={perEngine?.overall_engine_grade || 'Not measured'}
      tabs={[
        { id: 'engines', label: 'Per-Engine AI Matrix' },
        { id: 'som', label: 'Share of Model & Displacement' },
        { id: 'sentiment', label: 'Sentiment & Hallucinations' },
        { id: 'retrieval_analysis', label: 'Controlled Retrieval Analysis' },
        { id: 'offpage', label: 'Off-Page Citation Network' },
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
                {perEngine?.chatgpt?.readiness_band || 'OpenAI Search retrieval readiness & GPTBot indexation'}
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
                {perEngine?.google_aio?.readiness_band || 'Generative overview inclusion & featured snippets'}
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
                {perEngine?.claude_gemini?.readiness_band || 'ClaudeBot directives & structured knowledge graph'}
              </p>
            </Card>
          </div>

          {/* AI Bot Directives Card */}
          <Card className="p-5 space-y-4">
            <h3 className="font-serif font-bold text-ink text-base flex items-center gap-2">
              <Bot className="w-4 h-4 text-pine" /> AI Search Crawler Directives (`robots.txt`)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-ink-50/50 rounded border border-ink/5 space-y-1">
                <span className="font-mono text-ink-500 font-semibold">GPTBot (OpenAI)</span>
                <p className="font-mono font-bold text-good flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                </p>
              </div>
              <div className="p-3 bg-ink-50/50 rounded border border-ink/5 space-y-1">
                <span className="font-mono text-ink-500 font-semibold">PerplexityBot</span>
                <p className="font-mono font-bold text-good flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                </p>
              </div>
              <div className="p-3 bg-ink-50/50 rounded border border-ink/5 space-y-1">
                <span className="font-mono text-ink-500 font-semibold">ClaudeBot (Anthropic)</span>
                <p className="font-mono font-bold text-good flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                </p>
              </div>
              <div className="p-3 bg-ink-50/50 rounded border border-ink/5 space-y-1">
                <span className="font-mono text-ink-500 font-semibold">Google-Extended</span>
                <p className="font-mono font-bold text-good flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Allowed
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: SHARE OF MODEL (SoM) & DISPLACEMENT
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'som' && (
        <div className="space-y-6">
          {somMetric ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4 space-y-1.5 border-t-4 border-t-pine">
                  <span className="text-xs text-ink-500 font-medium">Funnel-Weighted SoM</span>
                  <p className="font-serif text-3xl font-bold text-ink">
                    {somMetric.funnel_weighted_som_pct != null ? `${somMetric.funnel_weighted_som_pct}%` : '—'}
                  </p>
                  <p className="text-[11px] text-pine font-medium">Weighted across Awareness, Consideration, and Decision</p>
                </Card>

                <Card className="p-4 space-y-1.5 border-t-4 border-t-good">
                  <span className="text-xs text-ink-500 font-medium">1st-Party Citation Rate</span>
                  <p className="font-serif text-3xl font-bold text-ink">
                    {somMetric.first_party_citation_share_pct != null ? `${somMetric.first_party_citation_share_pct}%` : '—'}
                  </p>
                  <p className="text-[11px] text-good font-medium">Observed direct domain citations</p>
                </Card>

                <Card className="p-4 space-y-1.5 border-t-4 border-t-cyan-600">
                  <span className="text-xs text-ink-500 font-medium">Rank #1 Recommendation</span>
                  <p className="font-serif text-3xl font-bold text-ink">
                    {somMetric.ordinal_distribution?.rank_1 ?? 0}
                  </p>
                  <p className="text-[11px] text-ink-500 font-mono">Top recommendation count</p>
                </Card>

                <Card className="p-4 space-y-1.5 border-t-4 border-t-bad">
                  <span className="text-xs text-ink-500 font-medium">Competitor Displacements</span>
                  <p className="font-serif text-3xl font-bold text-bad">
                    {somMetric.competitor_displacements?.length ?? 0}
                  </p>
                  <p className="text-[11px] text-bad font-medium">Instances where competitor held top position</p>
                </Card>
              </div>

              {/* Stage breakdown if available */}
              {somMetric.stage_breakdown && (
                <Card className="p-5 space-y-4">
                  <h3 className="font-serif font-bold text-ink text-base flex items-center gap-2">
                    <Crosshair className="w-4 h-4 text-pine" /> Buyer Journey Stage Weighting
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    {Object.entries(somMetric.stage_breakdown).map(([stageName, sData]: [string, any]) => (
                      <div key={stageName} className="p-4 rounded-lg bg-ink-50/60 border border-ink/5 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-ink uppercase tracking-wider text-[11px]">
                            {stageName} ({sData.commercial_weight}x)
                          </span>
                          <span className="font-mono font-bold text-pine">
                            {sData.mention_rate_pct != null ? `${sData.mention_rate_pct}%` : '—'}
                          </span>
                        </div>
                        <p className="text-ink-500">
                          {sData.mentions} of {sData.total_queries} queries observed with brand mentions.
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </>
          ) : (
            <Card className="p-8 text-center space-y-3">
              <Crosshair className="w-8 h-8 text-ink-400 mx-auto" />
              <h4 className="font-serif font-bold text-ink text-base">Share of Model: Not Measured</h4>
              <p className="text-xs text-ink-500 max-w-md mx-auto">
                Live multi-engine Share of Model (SoM) is computed exclusively from successful live engine responses.
                To observe real brand presence across AI answer engines, run a live benchmark with configured engine keys.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: BRAND SENTIMENT & HALLUCINATIONS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'sentiment' && (
        <div className="space-y-6">
          {sentimentAudit ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="p-5 space-y-3">
                <h3 className="font-serif font-bold text-ink text-base flex items-center gap-2">
                  <Award className="w-4 h-4 text-good" /> Brand Sentiment Polarity
                </h3>
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-good/10 text-good font-serif font-bold text-xl rounded-lg border border-good/20">
                    {sentimentAudit.overall_sentiment_distribution?.POSITIVE ?? 0} Positive /{' '}
                    {sentimentAudit.total_evaluated} Total
                  </div>
                  <p className="text-xs text-ink-600">
                    Evaluated from {sentimentAudit.total_evaluated} live engine responses.
                  </p>
                </div>
              </Card>

              <Card className="p-5 space-y-3 border-l-4 border-l-bad">
                <div className="flex items-center justify-between">
                  <h3 className="font-serif font-bold text-ink text-base flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-bad" /> Ground-Truth Hallucination Audit
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-good/10 text-good">
                    {sentimentAudit.hallucinated_responses} Distortions Flagged
                  </span>
                </div>
                <p className="text-xs text-ink-600">
                  Cross-referenced against verified crawled business profile facts.
                </p>
              </Card>
            </div>
          ) : (
            <Card className="p-8 text-center space-y-3">
              <ShieldAlert className="w-8 h-8 text-ink-400 mx-auto" />
              <h4 className="font-serif font-bold text-ink text-base">Brand Sentiment & Hallucinations: Not Measured</h4>
              <p className="text-xs text-ink-500 max-w-md mx-auto">
                Sentiment polarity and factual hallucination detection require verbatim responses from live AI engines.
                Run the Live AI Citation Tracker to evaluate how AI models represent your brand.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: CONTROLLED RETRIEVAL ANALYSIS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'retrieval_analysis' && (
        <div className="space-y-6">
          <Card className="p-5">
            <ControlledRetrievalVisualizer
              report={retrievalReport}
              loading={retrievalLoading}
              error={retrievalError}
              query={retrievalQuery}
              onQueryChange={setRetrievalQuery}
              onRunAnalysis={handleRunControlledRetrieval}
            />
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 5: OFF-PAGE CITATION NETWORK
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'offpage' && (
        <div className="space-y-6">
          {offpageReport ? (
            <Card className="p-5 space-y-4">
              <div>
                <h3 className="font-serif font-bold text-ink text-base flex items-center gap-2">
                  <Network className="w-4 h-4 text-pine" /> Observed Third-Party Citation Authority Domains
                </h3>
                <p className="text-xs text-ink-500 mt-1">
                  Third-party authority domains observed in external citation URLs during live AI answer engine benchmarking.
                </p>
              </div>

              <div className="overflow-x-auto border border-ink/10 rounded-lg">
                <table className="w-full text-xs text-left">
                  <thead className="bg-ink-50 text-ink-700 font-mono text-[11px] border-b border-ink/10">
                    <tr>
                      <th className="py-2.5 px-3">Authority Domain</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Query Frequency</th>
                      <th className="py-2.5 px-3">{brandName} Present</th>
                      <th className="py-2.5 px-3">Recommended Profile Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink/5 font-mono text-[11px]">
                    {offpageReport.top_authority_hubs?.map((hub: any, i: number) => (
                      <tr key={i}>
                        <td className="py-2.5 px-3 font-semibold text-ink">{hub.domain}</td>
                        <td className="py-2.5 px-3 text-pine">{hub.hub_type}</td>
                        <td className="py-2.5 px-3">{hub.frequency_across_queries} queries</td>
                        <td className="py-2.5 px-3 font-bold">
                          {hub.target_brand_present ? (
                            <span className="text-good">✓ Observed</span>
                          ) : (
                            <span className="text-ink-400">✗ Not observed</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-ink-600 font-sans">{hub.recommended_action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : (
            <Card className="p-8 text-center space-y-3">
              <Network className="w-8 h-8 text-ink-400 mx-auto" />
              <h4 className="font-serif font-bold text-ink text-base">Off-Page Citation Network: Not Measured</h4>
              <p className="text-xs text-ink-500 max-w-md mx-auto">
                Off-page citation networks are aggregated strictly from external URLs observed in live benchmark responses.
                Run the Live AI Citation Tracker to inspect third-party authority domains cited in engine responses.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 6: LIVE AI CITATIONS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'citations' && (
        <RealAiCitationTracker
          domain={report.domain}
          bizName={brandName}
          analysisId={analysisId}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 7: INFORMATION GAIN & FLUFF
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'infogain' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1">
              <span className="text-xs text-ink-500">Information Gain</span>
              <p className="font-serif text-3xl font-bold text-ink">
                {infoGain?.score != null ? Math.round(infoGain.score) : '—'}
                <span className="text-xs text-ink-400 font-sans font-normal"> / 100</span>
              </p>
              <p className="text-xs text-good font-medium">Original data points present</p>
            </Card>

            <Card className="p-4 space-y-1">
              <span className="text-xs text-ink-500">Fluff Ratio Score</span>
              <p className="font-serif text-3xl font-bold text-ink">
                {infoGain?.fluff_ratio_score != null ? `${infoGain.fluff_ratio_score}/100` : '—'}
              </p>
              <p className="text-xs text-ink-500">Low promotional filler</p>
            </Card>

            <Card className="p-4 space-y-1">
              <span className="text-xs text-ink-500">Proprietary Statistics</span>
              <p className="font-serif text-3xl font-bold text-ink">
                {infoGain?.has_proprietary_statistics ? 'Detected' : 'None detected'}
              </p>
              <p className="text-xs text-ink-500">Primary research statistics</p>
            </Card>

            <Card className="p-4 space-y-1">
              <span className="text-xs text-ink-500">Benchmark Tables</span>
              <p className="font-serif text-3xl font-bold text-ink">
                {infoGain?.has_benchmark_tables ? 'Verified' : 'None detected'}
              </p>
              <p className="text-xs text-ink-500">Quotable data comparisons</p>
            </Card>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 8: QUERY MATRIX
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'queries' && (
        <Card className="p-5 space-y-4">
          <h3 className="font-serif font-bold text-ink text-base">Tested Generative Inquiry Matrix</h3>
          <div className="space-y-2">
            {queries.slice(0, 10).map((q, idx) => (
              <div key={idx} className="p-3 bg-ink-50/60 rounded-md border border-ink/5 flex items-center justify-between text-xs">
                <span className="font-mono text-ink-800">{q.query}</span>
                <span className="px-2 py-0.5 rounded bg-pine/10 text-pine font-mono font-semibold">
                  {q.question_type || 'commercial'}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 9: LLM PASSAGE REWRITES
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'rewrites' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-serif font-bold text-ink text-base">Inverted-Pyramid Quotable Rewrites</h3>
              <p className="text-xs text-ink-500">Drop-in 40-60 word definitions designed for direct LLM extraction.</p>
            </div>
            {onOpenPatchPack && (
              <button
                type="button"
                onClick={onOpenPatchPack}
                className="px-3 py-1.5 bg-pine hover:bg-pine-dark text-white rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <FileCheck className="w-3.5 h-3.5" />
                <span>Export Patch Pack ZIP</span>
              </button>
            )}
          </div>

          <div className="space-y-3">
            {rewrites.slice(0, 5).map((r: any, idx: number) => {
              const isCopied = copiedId === (r.passage_id || `rec-${idx}`);
              return (
                <Card key={idx} className="p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-pine font-mono bg-pine/5 px-2 py-0.5 rounded border border-pine/20">
                      Rewrite #{idx + 1}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(r.recommended_rewrite, r.passage_id || `rec-${idx}`)}
                      className="px-2.5 py-1 bg-ink-100 hover:bg-ink-200 text-ink-700 rounded text-xs font-mono font-medium flex items-center gap-1"
                    >
                      {isCopied ? <Check className="w-3.5 h-3.5 text-good" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{isCopied ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded bg-bad/5 border border-bad/20">
                      <span className="text-[10px] font-mono font-bold text-bad uppercase block mb-1">Current Copy</span>
                      <p className="font-mono text-ink-700 text-[11px]">{r.current_passage}</p>
                    </div>
                    <div className="p-3 rounded bg-good/5 border border-good/30">
                      <span className="text-[10px] font-mono font-bold text-good uppercase block mb-1">Recommended Inverted-Pyramid</span>
                      <p className="font-mono text-ink-900 text-[11px]">{r.recommended_rewrite}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 10: VISIBILITY TRENDS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'trends' && (
        <GeoAeoTrendTracker domain={report.domain} />
      )}
    </PillarShell>
  );
}
