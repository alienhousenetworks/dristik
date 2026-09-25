import React, { useState, useEffect } from 'react';

interface CompetitorProfile {
  competitor_id: string;
  domain: string;
  brand_name: string;
  market_overlap: string;
  discovered_reason: string;
  overall_score?: number | null;
  winning_queries: string[];
  vulnerabilities: string[];
  discovery_confidence?: number;
  score_basis?: string;
  product_overlap_reason?: string;
  market_size?: string | null;
}

interface BenchmarkTableRow {
  dimension: string;
  dimension_key: string;
  target_score?: number | null;
  competitor_1?: number | null;
  competitor_2?: number | null;
  competitor_3?: number | null;
  gap_verdict: string;
}

interface CompetitorBenchmarkMatrix {
  target_domain: string;
  target_brand: string;
  market_niche: string;
  status?: string;
  message?: string;
  competitors: CompetitorProfile[];
  comparative_table: BenchmarkTableRow[];
  primary_competitive_gap: string;
  recommended_offensive_plays: string[];
  discovery_method?: string;
  market_size_status?: string;
  market_size_note?: string;
  score_basis?: string;
}

interface CompetitorDiscoveryViewProps {
  websiteUrl: string;
  analysisId?: string;
}

export function CompetitorDiscoveryView({ websiteUrl, analysisId }: CompetitorDiscoveryViewProps) {
  const [matrix, setMatrix] = useState<CompetitorBenchmarkMatrix | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customCompetitorUrl, setCustomCompetitorUrl] = useState('');
  const [activeCompetitorUrls, setActiveCompetitorUrls] = useState<string[]>([]);

  const loadCompetitors = async (overrideUrls?: string[]) => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (websiteUrl) queryParams.set('website_url', websiteUrl);
      if (analysisId) queryParams.set('analysis_id', analysisId);

      const urlsToUse = overrideUrls !== undefined ? overrideUrls : activeCompetitorUrls;
      urlsToUse.forEach((u) => {
        queryParams.append('competitor_urls', u);
      });

      const res = await fetch(`/api/v1/intelligence/competitors?${queryParams.toString()}`);
      const raw = await res.text();
      if (!res.ok) {
        setMatrix(null);
        setError(`Competitor API returned HTTP ${res.status}. ${raw.slice(0, 240) || 'Empty body.'} Add rival URLs manually if auto-discovery is wrong.`);
        return;
      }
      const data = raw ? JSON.parse(raw) : null;
      if (!data) {
        setMatrix(null);
        setError('Competitor API returned an empty body. Restart the backend and retry.');
        return;
      }
      setMatrix(data);
    } catch (err) {
      setMatrix(null);
      setError(`Could not load competitors: ${err instanceof Error ? err.message : String(err)}. Confirm the API is running, then retry or enter rival domains.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompetitors();
  }, [websiteUrl, analysisId]);

  const handleAddCustomCompetitor = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customCompetitorUrl.trim();
    if (!trimmed) return;
    const cleanDomain = trimmed.replace(/^https?:\/\//i, '').split('/')[0];
    if (activeCompetitorUrls.includes(cleanDomain)) return;
    const updated = [...activeCompetitorUrls, cleanDomain].slice(0, 3);
    setActiveCompetitorUrls(updated);
    setCustomCompetitorUrl('');
    loadCompetitors(updated);
  };

  const handleResetToAutomated = () => {
    setActiveCompetitorUrls([]);
    loadCompetitors([]);
  };

  if (loading) {
    return (
      <div className="p-8 sheet border border-line rounded-lg flex items-center justify-center gap-3 text-ink-500">
        <div className="w-5 h-5 border-2 border-pine border-t-transparent rounded-full animate-spin"></div>
        <span>Discovering organic & AI search competitors automatically...</span>
      </div>
    );
  }

  if (error && !matrix) {
    return (
      <div className="p-6 sheet border border-bad/40 rounded-lg space-y-3">
        <span className="label text-bad">Competitor discovery failed</span>
        <p className="text-sm text-ink-800">{error}</p>
        <p className="text-xs text-ink-600">
          What to do: retry, or type a real rival domain below after reload. Dristik will not invent TAM or pick Cloudflare/HubSpot unless they actually compete with this business.
        </p>
        <button
          type="button"
          onClick={() => loadCompetitors()}
          className="px-3 py-1.5 text-xs bg-pine text-white rounded-md"
        >
          Retry discovery
        </button>
      </div>
    );
  }

  if (!matrix) return null;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="sheet border border-line rounded-lg p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="label text-pine">
                Automated Competitor Discovery (Zero Manual Input Required)
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-good/10 text-good border border-good/20 font-semibold">
                {activeCompetitorUrls.length > 0 ? 'CUSTOM BENCHMARK' : (matrix.discovery_method || 'IDENTITY MATCH').replace(/_/g, ' ').toUpperCase()}
              </span>
            </div>
            <h3 className="font-serif text-2xl md:text-3xl text-ink font-normal">
              You vs Discovered Market Competitors
            </h3>
            <p className="text-xs text-ink-500 mt-1 max-w-xl">
              {matrix.message || 'No invented rival scores. Add a rival domain to name a competitor; scores stay null until that site is crawled.'}
            </p>
            <p className="text-[11px] text-ink-500 mt-1 max-w-xl">
              {matrix.market_size_note || 'Market size (TAM/SAM/SOM) was not measured.'}
            </p>
          </div>

          <div className="bg-paper-50 border border-line rounded-md p-3 text-xs text-ink-700 max-w-md">
            <span className="label text-[10px] block mb-0.5 text-warn font-semibold">Primary Competitive Gap:</span>
            <p className="text-xs text-ink leading-relaxed font-medium">{matrix.primary_competitive_gap}</p>
          </div>
        </div>

        {/* Inline Custom Competitor Input */}
        <div className="mt-5 pt-4 border-t border-line flex flex-col sm:flex-row items-center justify-between gap-3">
          <form onSubmit={handleAddCustomCompetitor} className="flex items-center gap-2 w-full sm:w-auto flex-1 max-w-md">
            <input
              type="text"
              placeholder="Add rival domain (e.g. competitor.com)..."
              value={customCompetitorUrl}
              onChange={(e) => setCustomCompetitorUrl(e.target.value)}
              className="px-3 py-1.5 text-xs bg-paper-50 border border-line rounded-md text-ink w-full focus:outline-none focus:border-pine font-mono"
            />
            <button
              type="submit"
              disabled={!customCompetitorUrl.trim()}
              className="px-3 py-1.5 text-xs bg-pine text-white rounded-md hover:bg-pine/90 disabled:opacity-50 transition-colors whitespace-nowrap font-medium"
            >
              + Benchmark Domain
            </button>
          </form>

          {activeCompetitorUrls.length > 0 && (
            <button
              onClick={handleResetToAutomated}
              className="text-xs text-ink-500 hover:text-ink underline self-end sm:self-auto"
            >
              Reset to Automated Discovery
            </button>
          )}
        </div>
      </div>

      {matrix.competitors.length === 0 && (
        <div className="sheet border border-line rounded-lg p-5 text-sm text-ink-700">
          No rivals identified. Competitor scores are null — they are not copies of your audit. Add a real rival domain above.
        </div>
      )}

      {/* Discovered Competitor Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {matrix.competitors.map((comp, idx) => (
          <div
            key={comp.competitor_id || idx}
            className="sheet border border-line rounded-lg p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-mono font-bold text-ink-500">#{idx + 1}</span>
                  <span className="text-sm font-bold text-ink block">{comp.brand_name}</span>
                </div>
                <span className="text-[11px] font-mono text-pine hover:underline">{comp.domain}</span>
              </div>
              <div className="text-right">
                <span className="label text-[10px] block">Score</span>
                <span className="text-lg font-mono font-bold text-pine">
                  {comp.overall_score != null ? `${comp.overall_score}/100` : 'null'}
                </span>
                <span className="label text-[10px] block text-ink-500">not crawled</span>
              </div>
            </div>

            <div className="text-xs text-ink-700">
              <span className="label text-[10px] block text-ink-500">Overlap & Discovery Reason</span>
              <p className="mt-0.5 text-xs leading-relaxed">{comp.discovered_reason}</p>
            </div>

            {(comp.winning_queries?.length > 0 || comp.vulnerabilities?.length > 0) && (
            <div className="text-xs pt-2 border-t border-line space-y-2">
              {comp.winning_queries?.length > 0 && (
              <div>
                <span className="label text-[10px] text-good block font-semibold">Winning Commercial Queries:</span>
                <ul className="mt-1 space-y-0.5">
                  {comp.winning_queries.map((q, qIdx) => (
                    <li key={qIdx} className="text-[11px] text-ink-700 truncate font-mono">
                      • "{q}"
                    </li>
                  ))}
                </ul>
              </div>
              )}
              {comp.vulnerabilities?.length > 0 && (
              <div className="pt-1">
                <span className="label text-[10px] text-bad block font-semibold">Exploitable Vulnerabilities:</span>
                <ul className="mt-1 space-y-0.5">
                  {comp.vulnerabilities.map((v, vIdx) => (
                    <li key={vIdx} className="text-[11px] text-ink-600 truncate">
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
              )}
            </div>
            )}
          </div>
        ))}
      </div>

      {/* 7-Vector Comparative Benchmark Table */}
      <div className="sheet border border-line rounded-lg overflow-hidden">
        <div className="p-4 border-b border-line flex items-center justify-between bg-paper-50/50">
          <div>
            <span className="label text-ink font-semibold block">
              7-Vector Commercial Benchmark Matrix
            </span>
            <span className="text-xs text-ink-500">Your column is from this audit when measured. Rival columns are null unless that site was crawled. No copied fallback numbers.</span>
          </div>
          <span className="text-xs font-mono bg-paper-100 dark:bg-ink-900 px-2.5 py-1 rounded border border-line text-ink-700">
            Unmeasured = null
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-paper-50 text-ink-500 border-b border-line label text-[10px]">
                <th className="p-3.5">Dimension</th>
                <th className="p-3.5 text-pine font-bold bg-pine/5">
                  You ({matrix.target_brand})
                </th>
                {matrix.competitors.map((c, i) => (
                  <th key={c.competitor_id || i} className="p-3.5 font-semibold text-ink-700">
                    Comp {i + 1}: {c.brand_name}
                  </th>
                ))}
                <th className="p-3.5">Gap Analysis & Strategic Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line font-mono">
              {matrix.comparative_table.map((row, idx) => {
                const peerScores = [row.competitor_1, row.competitor_2, row.competitor_3];
                return (
                <tr key={idx} className="hover:bg-paper-200/40 transition-colors">
                  <td className="p-3.5 font-sans font-medium text-ink">{row.dimension}</td>
                  <td className="p-3.5 font-bold text-pine text-sm bg-pine/5">
                    <span className="inline-block min-w-[28px]">{row.target_score != null ? row.target_score : 'null'}</span>
                  </td>
                  {matrix.competitors.map((c, i) => (
                    <td key={c.competitor_id || i} className="p-3.5 text-ink-500 font-semibold">
                      {peerScores[i] != null ? peerScores[i] : 'null'}
                    </td>
                  ))}
                  <td className="p-3.5 font-sans text-ink-600 text-[11px] leading-relaxed max-w-sm">
                    {row.gap_verdict}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recommended Offensive Plays */}
      {matrix.recommended_offensive_plays?.length > 0 && (
        <div className="sheet border border-line rounded-lg p-5 space-y-3 bg-paper-50/30">
          <div className="flex items-center gap-2 label text-pine font-semibold">
            <span>⚔️</span>
            <span>Recommended Offensive Plays to Displace Competitors</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {matrix.recommended_offensive_plays.map((play, i) => (
              <div key={i} className="bg-paper-50 border border-line p-3.5 rounded-md text-xs text-ink-700 space-y-1 shadow-2xs">
                <span className="label text-pine block font-mono text-[10px]">Strategic Play #{i + 1}</span>
                <p className="leading-relaxed">{play}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
