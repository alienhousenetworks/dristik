import React, { useState, useEffect } from 'react';

interface CompetitorPillarScores {
  search_seo: number;
  ai_search_geo: number;
  experience_sxo: number;
  conversion_cro: number;
  brand_trust: number;
  overall_score: number;
}

interface CompetitorTechSpecs {
  status_code: number;
  ttfb_ms: number;
  word_count: number;
  h1_count: number;
  h1_text?: string | null;
  has_meta_description: boolean;
  meta_description_len: number;
  schema_types: string[];
  schema_count: number;
  cta_count: number;
  primary_cta?: string | null;
  has_viewport: boolean;
  dom_elements_count: number;
  is_https: boolean;
}

interface PeerBenchmarkProfile {
  domain: string;
  brand_name: string;
  is_target: boolean;
  rank: number;
  scores: CompetitorPillarScores;
  specs: CompetitorTechSpecs;
  crawl_status: string;
  error_message?: string | null;
}

interface CompetitiveMoatItem {
  title: string;
  pillar: string;
  description: string;
  advantage_delta: string;
}

interface CompetitiveGapItem {
  title: string;
  pillar: string;
  description: string;
  winning_competitor: string;
  recommendation: string;
}

interface CompetitiveBenchmarkResult {
  target_domain: string;
  competitor_1_domain: string;
  competitor_2_domain: string;
  peers: PeerBenchmarkProfile[];
  target_overall_rank: number;
  peer_average_score: number;
  target_vs_peer_avg_delta: number;
  competitive_moats: CompetitiveMoatItem[];
  vulnerability_gaps: CompetitiveGapItem[];
  strategic_summary: string;
}

interface CompetitorSideBySideBenchmarkProps {
  targetDomain: string;
  analysisId?: string;
  niche?: string;
}

export function CompetitorSideBySideBenchmark({
  targetDomain,
  analysisId,
  niche,
}: CompetitorSideBySideBenchmarkProps) {
  const cleanTarget = targetDomain.replace('https://', '').replace('http://', '').split('/')[0];

  const [comp1, setComp1] = useState<string>('');
  const [comp2, setComp2] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [benchmarkResult, setBenchmarkResult] = useState<CompetitiveBenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<Array<{ domain: string; brand: string; category: string }>>([]);

  // Fetch smart suggestions on mount
  useEffect(() => {
    fetch(`/api/v1/intelligence/competitors/suggestions?domain=${encodeURIComponent(cleanTarget)}&niche=${encodeURIComponent(niche || '')}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.suggestions && data.suggestions.length >= 2) {
          setSuggestions(data.suggestions);
          if (!comp1) setComp1(data.suggestions[0].domain);
          if (!comp2) setComp2(data.suggestions[1].domain);
        }
      })
      .catch((err) => console.error('Suggestion fetch error:', err));
  }, [cleanTarget, niche]);

  const handleRunBenchmark = async (c1Override?: string, c2Override?: string) => {
    const c1 = c1Override || comp1;
    const c2 = c2Override || comp2;

    if (!c1 || !c2) {
      setError('Please provide two competitor URLs or domains.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/v1/intelligence/competitors/benchmark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_domain: cleanTarget,
          competitor_1_url: c1,
          competitor_2_url: c2,
          analysis_id: analysisId,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Benchmark failed with status HTTP ${res.status}`);
      }

      const data: CompetitiveBenchmarkResult = await res.json();
      setBenchmarkResult(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to execute 3-way competitor crawl.');
    } finally {
      setLoading(false);
    }
  };

  const applySuggestions = (s1: string, s2: string) => {
    setComp1(s1);
    setComp2(s2);
    handleRunBenchmark(s1, s2);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="sheet border border-line rounded-xl p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">⚔️</span>
              <span className="label text-pine text-xs">Real Competitive Benchmarking Layer</span>
            </div>
            <h3 className="font-serif text-2xl sm:text-3xl text-ink mt-1 font-normal">
              3-Way Side-by-Side Homepage Benchmark
            </h3>
            <p className="text-xs text-ink-500 mt-1 max-w-2xl">
              Scrapes 2 competitor homepages with the identical crawler pipeline. Evaluates relative scores across the 5 pillars, extracts technical specs, and isolates empirical competitive moats.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleRunBenchmark()}
              disabled={loading || !comp1 || !comp2}
              className="px-4 py-2 bg-pine text-white rounded-md text-xs font-semibold hover:bg-pine/90 transition-colors shadow-2xs cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
            >
              {loading ? (
                <>
                  <span className="animate-spin">⏳</span>
                  <span>Crawling Competitors...</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>Run 3-Way Benchmark Now</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Competitor Input Form */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="space-y-1">
            <label className="text-[10px] font-mono uppercase font-bold text-ink-500 block">
              Your Target Domain
            </label>
            <div className="p-2 bg-paper-100 dark:bg-ink-950 rounded border border-line font-mono text-xs text-ink font-semibold flex items-center justify-between">
              <span>{cleanTarget}</span>
              <span className="text-[9px] bg-pine/15 text-pine px-1.5 py-0.5 rounded font-bold">TARGET</span>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-mono uppercase font-bold text-ink-500 block">
              Competitor 1 Domain / URL
            </label>
            <input
              type="text"
              value={comp1}
              onChange={(e) => setComp1(e.target.value)}
              placeholder="e.g. competitor1.com"
              className="w-full p-2 bg-white dark:bg-ink-900 rounded border border-line font-mono text-xs text-ink focus:border-pine focus:outline-hidden"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-mono uppercase font-bold text-ink-500 block">
              Competitor 2 Domain / URL
            </label>
            <input
              type="text"
              value={comp2}
              onChange={(e) => setComp2(e.target.value)}
              placeholder="e.g. competitor2.com"
              className="w-full p-2 bg-white dark:bg-ink-900 rounded border border-line font-mono text-xs text-ink focus:border-pine focus:outline-hidden"
            />
          </div>
        </div>

        {/* Quick Suggestion Chips */}
        {suggestions.length >= 2 && (
          <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
            <span className="text-ink-400 font-mono text-[10px] uppercase">Suggested Peers:</span>
            <button
              type="button"
              onClick={() => applySuggestions(suggestions[0].domain, suggestions[1].domain)}
              className="px-2.5 py-1 bg-paper-100 hover:bg-paper-200 dark:bg-ink-800 rounded border border-line text-[11px] font-mono text-ink-700 transition-colors cursor-pointer"
            >
              ⚡ Benchmark against {suggestions[0].brand} ({suggestions[0].domain}) &amp; {suggestions[1].brand} ({suggestions[1].domain})
            </button>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 text-xs text-bad rounded">
            <strong>Benchmark Error:</strong> {error}
          </div>
        )}
      </div>

      {/* Empty State before running */}
      {!benchmarkResult && !loading && (
        <div className="sheet border border-dashed border-line rounded-xl p-10 text-center space-y-4">
          <div className="text-4xl">📊</div>
          <div className="max-w-md mx-auto space-y-1">
            <h4 className="font-serif text-xl text-ink font-semibold">No Peer Benchmark Loaded Yet</h4>
            <p className="text-xs text-ink-500">
              Enterprise buyers never evaluate scores in isolation. Run the 3-way crawl to compare your TTFB speed, Schema richness, and conversion CTAs against your top 2 rivals.
            </p>
          </div>
          <button
            type="button"
            onClick={() => handleRunBenchmark()}
            disabled={!comp1 || !comp2}
            className="px-4 py-2 bg-ink text-paper rounded text-xs font-semibold hover:bg-ink/90 transition-colors cursor-pointer shadow-2xs"
          >
            Start Empirical Benchmark
          </button>
        </div>
      )}

      {/* BENCHMARK RESULTS VIEW */}
      {benchmarkResult && (
        <div className="space-y-6">
          {/* 1. TOP 3-WAY LEADERBOARD CARDS */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {benchmarkResult.peers.map((peer) => {
              const isLead = peer.rank === 1;
              const isTarget = peer.is_target;

              return (
                <div
                  key={peer.domain}
                  className={`sheet rounded-xl p-5 border transition-all space-y-3 relative ${
                    isTarget
                      ? 'border-2 border-pine shadow-md bg-paper-50/70 dark:bg-ink-900/60'
                      : 'border-line bg-white dark:bg-ink-950'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                        isLead
                          ? 'bg-good/15 text-good'
                          : peer.rank === 2
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                          : 'bg-bad/15 text-bad'
                      }`}
                    >
                      RANK #{peer.rank} · {isLead ? 'LEADER' : peer.rank === 2 ? 'CONTENDER' : 'LAGGING'}
                    </span>

                    {isTarget && (
                      <span className="text-[10px] font-mono bg-pine text-white font-bold px-2 py-0.5 rounded shadow-2xs">
                        YOUR SITE
                      </span>
                    )}
                  </div>

                  <div>
                    <h4 className="font-serif text-xl font-bold text-ink">{peer.brand_name}</h4>
                    <p className="font-mono text-xs text-ink-500 truncate">{peer.domain}</p>
                  </div>

                  <div className="flex items-baseline justify-between pt-1 border-t border-line">
                    <div>
                      <span className="label text-[10px] block">Overall Score</span>
                      <div className="flex items-baseline gap-1">
                        <span className="font-serif text-4xl font-bold text-ink">
                          {peer.scores.overall_score}
                        </span>
                        <span className="text-xs font-mono text-ink-500">/ 100</span>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="label text-[10px] block">Peer Delta</span>
                      <span
                        className={`text-xs font-mono font-bold ${
                          peer.scores.overall_score >= benchmarkResult.peer_average_score
                            ? 'text-good'
                            : 'text-bad'
                        }`}
                      >
                        {peer.scores.overall_score >= benchmarkResult.peer_average_score ? '+' : ''}
                        {peer.scores.overall_score - benchmarkResult.peer_average_score} pts vs avg
                      </span>
                    </div>
                  </div>

                  {peer.crawl_status === 'FAILED' && (
                    <div className="text-[10px] text-bad font-mono bg-red-50 dark:bg-red-950/30 p-1.5 rounded border border-red-200">
                      Crawl note: {peer.error_message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Strategic Narrative Takeaway */}
          <div className="sheet border-l-4 border-l-pine border border-line rounded-lg p-4 text-xs space-y-1">
            <span className="font-mono text-[10px] uppercase font-bold text-pine block">
              Strategic Competitive TakeawayBLUF
            </span>
            <p className="text-ink leading-relaxed font-normal">{benchmarkResult.strategic_summary}</p>
          </div>

          {/* 2. 5-PILLAR SIDE-BY-SIDE COMPARISON */}
          <div className="sheet border border-line rounded-xl p-6 space-y-5">
            <div className="border-b border-line pb-3">
              <h4 className="font-serif text-lg text-ink font-semibold">5-Pillar Scorecard Comparison</h4>
              <p className="text-xs text-ink-500">
                Peer comparison across the 5 canonical Website Intelligence pillars under the same deterministic rules.
              </p>
            </div>

            <div className="space-y-4">
              {[
                { key: 'search_seo', label: '1. Search (SEO)', desc: 'Crawlability, Titles, Meta, Heading Hierarchy' },
                { key: 'ai_search_geo', label: '2. AI Search (GEO)', desc: 'Schema.org JSON-LD, FAQ Entities, Answer Readiness' },
                { key: 'experience_sxo', label: '3. Website Experience (SXO)', desc: 'TTFB Server Speed, Viewport, DOM Bloat' },
                { key: 'conversion_cro', label: '4. Conversion Intelligence (CRO)', desc: 'CTA Action Verbs, Value Proposition, Forms' },
                { key: 'brand_trust', label: '5. Brand & Trust', desc: 'Verified Entity Metadata, HTTPS, Social Proof' },
              ].map((pillar) => {
                const readScore = (peer?: { scores?: Record<string, number> | null }) => {
                  const value = peer?.scores?.[pillar.key];
                  return typeof value === 'number' ? value : null;
                };
                const targetScore = readScore(benchmarkResult.peers.find((p) => p.is_target) as any);
                const p1Score = readScore(benchmarkResult.peers.find((p) => !p.is_target && p.domain === benchmarkResult.competitor_1_domain) as any);
                const p2Score = readScore(benchmarkResult.peers.find((p) => !p.is_target && p.domain === benchmarkResult.competitor_2_domain) as any);
                const measuredScores = [targetScore, p1Score, p2Score].filter((n): n is number => n != null);
                const maxScore = measuredScores.length ? Math.max(...measuredScores) : null;
                const showScore = (n: number | null) => (n == null ? '—' : `${n}%`);

                return (
                  <div key={pillar.key} className="p-3.5 bg-paper-50 dark:bg-ink-900/30 rounded-lg border border-line space-y-2">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                      <div>
                        <span className="font-bold text-xs text-ink">{pillar.label}</span>
                        <span className="text-[11px] text-ink-500 ml-2">({pillar.desc})</span>
                      </div>
                      <span className="text-[10px] font-mono text-ink-500">Max score: {maxScore == null ? '—' : `${maxScore}%`}</span>
                    </div>

                    <div className="grid grid-cols-3 gap-3 font-mono text-xs">
                      <div className={`p-2 rounded border ${targetScore != null && targetScore === maxScore ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 text-emerald-900 dark:text-emerald-200 font-bold' : 'bg-white dark:bg-ink-950 border-line text-ink'}`}>
                        <span className="text-[10px] block text-ink-400">Target ({cleanTarget})</span>
                        <span className="text-sm">{showScore(targetScore)}</span>
                      </div>
                      <div className={`p-2 rounded border ${p1Score != null && p1Score === maxScore ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 text-emerald-900 dark:text-emerald-200 font-bold' : 'bg-white dark:bg-ink-950 border-line text-ink'}`}>
                        <span className="text-[10px] block text-ink-400">{benchmarkResult.competitor_1_domain}</span>
                        <span className="text-sm">{showScore(p1Score)}</span>
                      </div>
                      <div className={`p-2 rounded border ${p2Score != null && p2Score === maxScore ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 text-emerald-900 dark:text-emerald-200 font-bold' : 'bg-white dark:bg-ink-950 border-line text-ink'}`}>
                        <span className="text-[10px] block text-ink-400">{benchmarkResult.competitor_2_domain}</span>
                        <span className="text-sm">{showScore(p2Score)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 3. HEAD-TO-HEAD TECHNICAL SPECIFICATION TABLE */}
          <div className="sheet border border-line rounded-xl p-6 space-y-4">
            <div className="border-b border-line pb-3">
              <h4 className="font-serif text-lg text-ink font-semibold">Head-to-Head Technical Architecture Specs</h4>
              <p className="text-xs text-ink-500">
                Direct empirical measurements extracted from the HTML DOM and network layer across all 3 sites.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono border-collapse">
                <thead>
                  <tr className="border-b border-line text-[10px] uppercase text-ink-500">
                    <th className="py-2.5 px-3">Specification / Metric</th>
                    <th className="py-2.5 px-3 text-pine font-bold bg-paper-100 dark:bg-ink-800">
                      Target ({cleanTarget})
                    </th>
                    <th className="py-2.5 px-3">{benchmarkResult.competitor_1_domain}</th>
                    <th className="py-2.5 px-3">{benchmarkResult.competitor_2_domain}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line text-ink">
                  <tr>
                    <td className="py-2.5 px-3 font-semibold font-sans">Server Latency (TTFB)</td>
                    <td className="py-2.5 px-3 font-bold text-pine bg-paper-50 dark:bg-ink-900/40">
                      {benchmarkResult.peers[0]?.specs.ttfb_ms} ms
                    </td>
                    <td className="py-2.5 px-3">{benchmarkResult.peers[1]?.specs.ttfb_ms} ms</td>
                    <td className="py-2.5 px-3">{benchmarkResult.peers[2]?.specs.ttfb_ms} ms</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold font-sans">Content Depth (Word Count)</td>
                    <td className="py-2.5 px-3 font-bold text-pine bg-paper-50 dark:bg-ink-900/40">
                      {benchmarkResult.peers[0]?.specs.word_count} words
                    </td>
                    <td className="py-2.5 px-3">{benchmarkResult.peers[1]?.specs.word_count} words</td>
                    <td className="py-2.5 px-3">{benchmarkResult.peers[2]?.specs.word_count} words</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold font-sans">Schema.org Entity Types</td>
                    <td className="py-2.5 px-3 font-bold text-pine bg-paper-50 dark:bg-ink-900/40">
                      {benchmarkResult.peers[0]?.specs.schema_count} types ({benchmarkResult.peers[0]?.specs.schema_types.slice(0, 2).join(', ') || 'None'})
                    </td>
                    <td className="py-2.5 px-3">
                      {benchmarkResult.peers[1]?.specs.schema_count} types ({benchmarkResult.peers[1]?.specs.schema_types.slice(0, 2).join(', ') || 'None'})
                    </td>
                    <td className="py-2.5 px-3">
                      {benchmarkResult.peers[2]?.specs.schema_count} types ({benchmarkResult.peers[2]?.specs.schema_types.slice(0, 2).join(', ') || 'None'})
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold font-sans">Primary CTA Action Verb</td>
                    <td className="py-2.5 px-3 font-bold text-pine bg-paper-50 dark:bg-ink-900/40 truncate max-w-[150px]">
                      "{benchmarkResult.peers[0]?.specs.primary_cta || 'None detected'}"
                    </td>
                    <td className="py-2.5 px-3 truncate max-w-[150px]">
                      "{benchmarkResult.peers[1]?.specs.primary_cta || 'None detected'}"
                    </td>
                    <td className="py-2.5 px-3 truncate max-w-[150px]">
                      "{benchmarkResult.peers[2]?.specs.primary_cta || 'None detected'}"
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold font-sans">Mobile Viewport Meta</td>
                    <td className="py-2.5 px-3 font-bold text-pine bg-paper-50 dark:bg-ink-900/40">
                      {benchmarkResult.peers[0]?.specs.has_viewport ? '✓ Configured' : '✗ Missing'}
                    </td>
                    <td className="py-2.5 px-3">
                      {benchmarkResult.peers[1]?.specs.has_viewport ? '✓ Configured' : '✗ Missing'}
                    </td>
                    <td className="py-2.5 px-3">
                      {benchmarkResult.peers[2]?.specs.has_viewport ? '✓ Configured' : '✗ Missing'}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold font-sans">DOM Elements Weight</td>
                    <td className="py-2.5 px-3 font-bold text-pine bg-paper-50 dark:bg-ink-900/40">
                      {benchmarkResult.peers[0]?.specs.dom_elements_count} nodes
                    </td>
                    <td className="py-2.5 px-3">{benchmarkResult.peers[1]?.specs.dom_elements_count} nodes</td>
                    <td className="py-2.5 px-3">{benchmarkResult.peers[2]?.specs.dom_elements_count} nodes</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* 4. MOATS VS GAPS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Competitive Moats */}
            <div className="sheet border border-emerald-300 dark:border-emerald-800 bg-emerald-50/20 dark:bg-emerald-950/10 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2 border-b border-emerald-200 dark:border-emerald-900 pb-2">
                <span className="text-base">🛡️</span>
                <h5 className="font-serif text-base font-bold text-emerald-950 dark:text-emerald-200">
                  Competitive Moats (Where You Lead Peers)
                </h5>
              </div>

              {benchmarkResult.competitive_moats.length > 0 ? (
                <div className="space-y-3">
                  {benchmarkResult.competitive_moats.map((moat, i) => (
                    <div key={i} className="p-3 bg-white dark:bg-ink-900 rounded border border-emerald-200 dark:border-emerald-900 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-ink">{moat.title}</span>
                        <span className="text-[10px] font-mono font-bold bg-good/15 text-good px-1.5 py-0.5 rounded">
                          {moat.advantage_delta}
                        </span>
                      </div>
                      <p className="text-ink-600 dark:text-ink-300 leading-relaxed">{moat.description}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ink-500 italic">
                  No distinct technical moats identified over competitors. Immediate remediation advised to establish leadership.
                </p>
              )}
            </div>

            {/* Vulnerability Gaps */}
            <div className="sheet border border-amber-300 dark:border-amber-800 bg-amber-50/20 dark:bg-amber-950/10 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2 border-b border-amber-200 dark:border-amber-900 pb-2">
                <span className="text-base">⚠️</span>
                <h5 className="font-serif text-base font-bold text-amber-950 dark:text-amber-200">
                  Priority Vulnerability Gaps (Where Rivals Beat You)
                </h5>
              </div>

              {benchmarkResult.vulnerability_gaps.length > 0 ? (
                <div className="space-y-3">
                  {benchmarkResult.vulnerability_gaps.map((gap, i) => (
                    <div key={i} className="p-3 bg-white dark:bg-ink-900 rounded border border-amber-200 dark:border-amber-900 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-ink">{gap.title}</span>
                        <span className="text-[10px] font-mono text-amber-800 dark:text-amber-300 font-semibold">
                          Captured by {gap.winning_competitor}
                        </span>
                      </div>
                      <p className="text-ink-600 dark:text-ink-300 leading-relaxed">{gap.description}</p>
                      <div className="pt-1 text-[11px] text-pine font-medium">
                        Fix: {gap.recommendation}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ink-500 italic">
                  No critical specification gaps identified against these competitors.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
