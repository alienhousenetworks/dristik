import React, { useState, useEffect } from 'react';

interface KeywordRankingItem {
  query: string;
  search_volume: number;
  current_position: number;
  monthly_impressions: number;
  monthly_clicks: number;
  ctr_percentage: number;
  intent: string;
  target_page: string;
  associated_technical_bottleneck?: string;
  estimated_revenue_impact_inr: number;
}

interface KeywordGapItem {
  keyword: string;
  search_volume: number;
  competitor_domain: string;
  competitor_position: number;
  your_position?: number;
  opportunity_type: string;
  recommended_action: string;
}

interface CausalChainItem {
  technical_problem: string;
  search_visibility_impact: string;
  traffic_consequence: string;
  conversion_opportunity: string;
}

interface SearchConsoleAttributionReport {
  domain: string;
  is_connected: boolean;
  total_monthly_clicks: number;
  total_monthly_impressions: number;
  average_ctr: number;
  average_position: number;
  top_ranking_keywords: KeywordRankingItem[];
  competitor_keyword_gaps: KeywordGapItem[];
  causal_chains: CausalChainItem[];
  estimated_traffic_leakage_inr: number;
  connection_status_message?: string;
}

import { ConnectorType } from '../types';

interface SearchConsoleAttributionViewProps {
  domain: string;
  analysisId?: string;
  onOpenConnectors?: (initialTab?: ConnectorType) => void;
}

const GoogleIcon = () => (
  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
    <path
      fill="#4285F4"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
    />
    <path
      fill="#34A853"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
    />
    <path
      fill="#EA4335"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
    />
  </svg>
);

export function SearchConsoleAttributionView({ domain, analysisId, onOpenConnectors }: SearchConsoleAttributionViewProps) {
  const [data, setData] = useState<SearchConsoleAttributionReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDirectModal, setShowDirectModal] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [gscPropertyUrl, setGscPropertyUrl] = useState(domain ? `https://${domain}` : '');
  const [gscCredentials, setGscCredentials] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connectSuccess, setConnectSuccess] = useState<string | null>(null);

  const fetchGsc = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ domain });
      if (analysisId) params.append('analysis_id', analysisId);

      const res = await fetch(`/api/v1/intelligence/search-console?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error('Failed to load GSC attribution:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGsc();
  }, [domain, analysisId]);

  // Listen for Google OAuth callback from popup window
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && e.data.type === 'GSC_OAUTH_SUCCESS') {
        fetchGsc();
        setShowDirectModal(false);
        setConnectSuccess(`Google Search Console authorized via Google OAuth (${e.data.email || 'Verified'})!`);
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleGoogleOAuth = () => {
    setConnecting(true);
    setConnectError(null);
    const cleanDomain = (gscPropertyUrl || domain).replace('https://', '').replace('http://', '').split('/')[0];
    const width = 520;
    const height = 660;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const authUrl = `/api/v1/connectors/google/oauth/authorize?domain=${encodeURIComponent(cleanDomain)}`;
    const popup = window.open(
      authUrl,
      'google_oauth_popup',
      `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes`
    );

    const timer = setInterval(() => {
      if (!popup || popup.closed) {
        clearInterval(timer);
        setConnecting(false);
        fetchGsc();
      }
    }, 1000);
  };

  const handleQuickConnect = async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      const cleanDomain = (gscPropertyUrl || domain).replace('https://', '').replace('http://', '').split('/')[0];
      const res = await fetch('/api/v1/connectors/google/oauth/quick-connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: cleanDomain,
          property_url: `https://${cleanDomain}`,
          account_email: `owner@${cleanDomain}`
        })
      });
      const resData = await res.json();
      if (res.ok && resData.success) {
        setConnectSuccess('✓ Google Search Console connected via 1-Click Google OAuth!');
        setTimeout(() => {
          setShowDirectModal(false);
          fetchGsc();
        }, 800);
      } else {
        setConnectError(resData.message || 'Quick connect failed');
      }
    } catch (e: any) {
      setConnectError(e.message || 'Quick connect failed');
    } finally {
      setConnecting(false);
    }
  };

  const handleDirectConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    setConnectError(null);
    setConnectSuccess(null);
    try {
      const res = await fetch('/api/v1/connectors/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'google_search_console',
          name: `Google Search Console (${gscPropertyUrl || domain})`,
          target_url: gscPropertyUrl || domain,
          api_key: gscCredentials,
        }),
      });
      const resData = await res.json();
      if (res.ok && resData.success) {
        setConnectSuccess(resData.message || 'Google Search Console property connected successfully!');
        setTimeout(() => {
          setShowDirectModal(false);
          fetchGsc();
        }, 1000);
      } else {
        setConnectError(resData.detail || resData.message || 'Failed to authenticate Search Console property');
      }
    } catch (err: any) {
      setConnectError(err.message || 'Failed to connect');
    } finally {
      setConnecting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 sheet border border-line rounded-lg flex items-center justify-center gap-3 text-ink-500">
        <div className="w-5 h-5 border-2 border-pine border-t-transparent rounded-full animate-spin"></div>
        <span>Querying Google Search Console telemetry and causal chains...</span>
      </div>
    );
  }

  if (!data) return null;

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="space-y-6">
      {/* Connection Notice when Not Connected */}
      {!data.is_connected && (
        <div className="p-5 rounded-xl border border-amber-300/60 bg-amber-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-warn font-semibold text-xs uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-warn animate-pulse" />
              <span>Google Search Console Not Connected</span>
            </div>
            <p className="text-xs text-ink-700 max-w-xl leading-relaxed">
              Google protects organic search impressions and clicks. To inspect actual keyword rankings and CTR for <strong className="text-ink">{domain}</strong>, connect your property with 1-click Google OAuth.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              id="connect-search-console-btn"
              onClick={() => setShowDirectModal(true)}
              className="px-4 py-2.5 rounded-lg bg-pine text-paper-50 hover:bg-pine-700 text-xs font-semibold shrink-0 transition-all duration-150 shadow-2xs flex items-center gap-2 cursor-pointer"
            >
              <GoogleIcon />
              <span>Sign in with Google</span>
            </button>
          </div>
        </div>
      )}

      {/* Header Banner */}
      <div className="sheet border border-line rounded-lg p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2.5 h-2.5 rounded-full ${data.is_connected ? 'bg-good' : 'bg-warn'}`}></span>
              <span className="label text-pine">
                {data.is_connected ? 'Google Search Console · Live Property' : 'Organic Traffic Attribution'}
              </span>
            </div>
            <h3 className="font-serif text-2xl md:text-3xl text-ink font-normal">
              Search Traffic & Revenue Attribution
            </h3>
            <p className="text-xs text-ink-500 mt-1 max-w-xl leading-relaxed">
              Connecting: <span className="text-bad font-semibold">Technical Problem</span> →{' '}
              <span className="text-warn font-semibold">Search Visibility</span> →{' '}
              <span className="text-pine font-semibold">Traffic</span> →{' '}
              <span className="text-good font-semibold">Conversion Opportunity</span>.
            </p>
          </div>

          <div className="bg-paper-50 border border-line rounded-md p-3 text-right shrink-0">
            <span className="label block text-[10px]">Estimated Traffic Leakage</span>
            <span className="text-2xl font-serif font-bold text-bad">
              {data.is_connected ? formatINR(data.estimated_traffic_leakage_inr) : '—'}
            </span>
          </div>
        </div>

        {/* GSC Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-4 border-t border-line text-xs">
          <div className="bg-paper-50 p-2.5 rounded-md border border-line">
            <span className="label block text-[10px]">Monthly Clicks</span>
            <span className="text-base font-bold font-mono text-ink mt-0.5 block">
              {data.is_connected ? data.total_monthly_clicks.toLocaleString('en-IN') : 'Not Connected'}
            </span>
          </div>
          <div className="bg-paper-50 p-2.5 rounded-md border border-line">
            <span className="label block text-[10px]">Monthly Impressions</span>
            <span className="text-base font-bold font-mono text-ink mt-0.5 block">
              {data.is_connected ? data.total_monthly_impressions.toLocaleString('en-IN') : 'Not Connected'}
            </span>
          </div>
          <div className="bg-paper-50 p-2.5 rounded-md border border-line">
            <span className="label block text-[10px]">Average CTR</span>
            <span className="text-base font-bold font-mono text-warn mt-0.5 block">
              {data.is_connected ? `${data.average_ctr}%` : '—'}
            </span>
          </div>
          <div className="bg-paper-50 p-2.5 rounded-md border border-line">
            <span className="label block text-[10px]">Average Position</span>
            <span className="text-base font-bold font-mono text-pine mt-0.5 block">
              {data.is_connected ? `#${data.average_position}` : '—'}
            </span>
          </div>
        </div>

        {/* Status Message Strip */}
        {data.connection_status_message && (
          <div className="mt-3 text-[11px] font-mono text-ink-500 bg-paper-100 p-2 rounded border border-line/60 flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${data.is_connected ? 'bg-good' : 'bg-ink-500'}`} />
            <span>{data.connection_status_message}</span>
          </div>
        )}
      </div>

      {/* Causal Chains: Tech Problem to Revenue Loss */}
      <div className="sheet border border-line rounded-lg p-6">
        <h4 className="label mb-4 text-pine">Causal Attribution Chains (Audited Deficiencies → Revenue Impact)</h4>
        {data.causal_chains.length === 0 ? (
          <div className="p-8 text-center text-xs text-ink-500 bg-paper-50 rounded-lg border border-line">
            No causal attribution chains available yet. Run a website audit to identify technical bottlenecks, or connect Google Search Console to attribute real organic traffic consequences.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.causal_chains.map((chain, i) => (
              <div key={i} className="bg-paper-50 border border-line rounded-lg p-4 space-y-3">
                <div className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-bad/10 text-bad flex items-center justify-center text-xs shrink-0 font-bold">1</span>
                  <div>
                    <span className="label block text-[10px] text-bad">Technical Bottleneck</span>
                    <p className="text-xs font-semibold text-ink">{chain.technical_problem}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-warn/10 text-warn flex items-center justify-center text-xs shrink-0 font-bold">2</span>
                  <div>
                    <span className="label block text-[10px] text-warn">Search Visibility Impact</span>
                    <p className="text-xs text-ink-700">{chain.search_visibility_impact}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-pine/10 text-pine flex items-center justify-center text-xs shrink-0 font-bold">3</span>
                  <div>
                    <span className="label block text-[10px] text-pine">Traffic Consequence</span>
                    <p className="text-xs text-ink-700">{chain.traffic_consequence}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2 pt-1 border-t border-line/50">
                  <span className="w-5 h-5 rounded-full bg-good/10 text-good flex items-center justify-center text-xs shrink-0 font-bold">4</span>
                  <div>
                    <span className="label block text-[10px] text-good">Remediation Opportunity</span>
                    <p className="text-xs font-semibold text-good">{chain.conversion_opportunity}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Ranking Keywords Table */}
      <div className="sheet border border-line rounded-lg overflow-hidden">
        <div className="p-4 border-b border-line bg-paper-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h4 className="label text-pine">Top Tracked Search Queries</h4>
            <span className="text-[10px] bg-paper-200 text-ink-700 font-mono px-2 py-0.5 rounded border border-line">
              {data.top_ranking_keywords.length} queries
            </span>
          </div>
          <span className="text-xs text-ink-500 font-mono">28-Day Google Search Analytics</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-50 text-ink-500 font-medium">
                <th className="p-3">Query</th>
                <th className="p-3">Position</th>
                <th className="p-3">Impressions</th>
                <th className="p-3">Clicks</th>
                <th className="p-3">CTR</th>
                <th className="p-3">Intent</th>
                <th className="p-3">Revenue Loss (Est)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line font-mono">
              {data.top_ranking_keywords.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-ink-500 font-sans">
                    {data.is_connected
                      ? 'No search query clicks recorded by Google in this 28-day window.'
                      : 'Authorize Google Search Console to inspect actual keyword rankings and CTR.'}
                  </td>
                </tr>
              ) : (
                data.top_ranking_keywords.map((kw, i) => (
                  <tr key={i} className="hover:bg-paper-200/50 transition-colors">
                    <td className="p-3 font-sans font-bold text-ink">{kw.query}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-bold">
                        #{kw.current_position.toFixed(1)}
                      </span>
                    </td>
                    <td className="p-3 text-ink-700">{kw.monthly_impressions.toLocaleString('en-IN')}</td>
                    <td className="p-3 font-bold text-ink">{kw.monthly_clicks.toLocaleString('en-IN')}</td>
                    <td className="p-3 font-bold text-warn">{kw.ctr_percentage}%</td>
                    <td className="p-3 font-sans">
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
                        {kw.intent}
                      </span>
                    </td>
                    <td className="p-3 text-bad font-semibold">
                      {kw.estimated_revenue_impact_inr > 0 ? formatINR(kw.estimated_revenue_impact_inr) : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Competitor Keyword Gaps */}
      <div className="sheet border border-line rounded-lg overflow-hidden">
        <div className="p-4 border-b border-line bg-paper-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h4 className="label text-pine">Competitor Search Gaps</h4>
            <span className="text-[10px] bg-paper-200 text-ink-700 font-mono px-2 py-0.5 rounded border border-line">
              {data.competitor_keyword_gaps.length} gaps
            </span>
          </div>
          <span className="text-xs text-ink-500 font-mono">Organic Visibility Voids</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-50 text-ink-500 font-medium">
                <th className="p-3">Keyword Void</th>
                <th className="p-3">Monthly Vol</th>
                <th className="p-3">Competitor</th>
                <th className="p-3">Rival Pos</th>
                <th className="p-3">Your Pos</th>
                <th className="p-3">Opportunity</th>
                <th className="p-3">Recommended Fix</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line font-mono">
              {data.competitor_keyword_gaps.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-ink-500 font-sans">
                    {data.is_connected
                      ? 'No competitor keyword gaps identified.'
                      : 'Authorize Google Search Console to inspect competitor keyword gaps.'}
                  </td>
                </tr>
              ) : (
                data.competitor_keyword_gaps.map((gap, i) => (
                  <tr key={i} className="hover:bg-paper-200/50 transition-colors">
                    <td className="p-3 font-sans font-bold text-ink">{gap.keyword}</td>
                    <td className="p-3 text-ink-700">{gap.search_volume.toLocaleString('en-IN')}</td>
                    <td className="p-3 font-sans font-semibold text-ink">{gap.competitor_domain}</td>
                    <td className="p-3 text-ink-700">#{gap.competitor_position}</td>
                    <td className="p-3 text-bad font-semibold">{gap.your_position ? `#${gap.your_position}` : 'Not Ranked'}</td>
                    <td className="p-3 font-sans">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
                        {gap.opportunity_type}
                      </span>
                    </td>
                    <td className="p-3 font-sans text-ink-700 text-[11px]">{gap.recommended_action}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Direct Google Search Console Connection Modal */}
      {showDirectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-xs">
          <div className="bg-paper border border-line rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="p-5 border-b border-line flex items-center justify-between bg-paper-100">
              <div className="flex items-center gap-2.5">
                <GoogleIcon />
                <div>
                  <h3 className="font-serif text-lg text-ink font-semibold leading-none">
                    Authorize Google Search Console
                  </h3>
                  <span className="text-[11px] text-ink-500 font-sans mt-0.5 block">
                    1-Click Google OAuth · 100% Non-Tech Friendly
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowDirectModal(false)}
                className="text-ink-500 hover:text-ink p-1.5 rounded-lg border border-line bg-paper-50 transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Domain Input */}
              <div>
                <label className="text-xs font-semibold text-ink-700 block mb-1.5">
                  Target Website Domain / Property
                </label>
                <input
                  type="text"
                  value={gscPropertyUrl}
                  onChange={(e) => setGscPropertyUrl(e.target.value)}
                  placeholder={`https://${domain}`}
                  className="w-full bg-paper-50 border border-line rounded-lg px-3.5 py-2.5 text-xs text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                  required
                />
              </div>

              {/* PRIMARY METHOD: 1-Click Google OAuth */}
              <div className="bg-paper-50 border border-line rounded-xl p-5 space-y-3.5 shadow-2xs">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-white border border-line flex items-center justify-center shrink-0 shadow-2xs">
                    <GoogleIcon />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-ink">Google 1-Click OAuth (Recommended)</h4>
                    <p className="text-xs text-ink-500 leading-relaxed mt-0.5">
                      Sign in with the Google Account that owns or manages this website. Zero code, zero JSON keys, and zero cloud setup required.
                    </p>
                  </div>
                </div>

                <div className="space-y-2 pt-1">
                  <button
                    type="button"
                    onClick={handleGoogleOAuth}
                    disabled={connecting}
                    className="w-full py-3 px-4 rounded-xl bg-paper-50 hover:bg-paper-100 border border-line text-ink font-semibold text-xs shadow-xs transition-all flex items-center justify-center gap-2.5 hover:border-ink-500 cursor-pointer disabled:opacity-60"
                  >
                    <GoogleIcon />
                    <span>{connecting ? 'Waiting for Google Authorization...' : 'Sign in with Google Search Console'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleQuickConnect}
                    disabled={connecting}
                    className="w-full py-2.5 px-4 rounded-xl bg-pine text-paper-50 hover:bg-pine-700 font-semibold text-xs transition-all flex items-center justify-center gap-2 cursor-pointer shadow-2xs disabled:opacity-60"
                  >
                    <span>⚡</span>
                    <span>1-Click Instant Connect (Local / Demo)</span>
                  </button>
                </div>
              </div>

              {/* Success / Error Messages */}
              {connectError && (
                <div className="p-3 rounded-lg text-xs font-mono bg-bad/10 border border-bad/30 text-bad">
                  {connectError}
                </div>
              )}

              {connectSuccess && (
                <div className="p-3 rounded-lg text-xs font-mono bg-good/10 border border-good/30 text-good">
                  {connectSuccess}
                </div>
              )}

              {/* Collapsible Advanced Section for DevOps / Service Account */}
              <div className="pt-2 border-t border-line">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-xs text-ink-500 hover:text-ink font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span className="text-[10px]">{showAdvanced ? '▼' : '▶'}</span>
                  <span>Advanced: Service Account JSON (DevOps / Enterprise)</span>
                </button>

                {showAdvanced && (
                  <form onSubmit={handleDirectConnect} className="mt-3.5 space-y-3 bg-paper-100 p-4 rounded-xl border border-line">
                    <p className="text-[11px] text-ink-500 leading-relaxed">
                      If you manage headless infrastructure, you can link a Google Cloud Service Account with <code>webmasters.readonly</code> access:
                    </p>
                    <textarea
                      rows={4}
                      value={gscCredentials}
                      onChange={(e) => setGscCredentials(e.target.value)}
                      placeholder={`{\n  "type": "service_account",\n  "client_email": "sa@project.iam.gserviceaccount.com",\n  "private_key": "-----BEGIN PRIVATE KEY-----..."\n}`}
                      className="w-full bg-paper-50 border border-line rounded-lg px-3 py-2 text-xs text-ink placeholder:text-ink-500 focus:outline-none focus:border-pine font-mono"
                    />
                    <div className="flex justify-end">
                      <button
                        type="submit"
                        disabled={connecting || !gscCredentials.trim()}
                        className="px-4 py-2 rounded-lg bg-pine text-paper-50 text-xs font-semibold hover:bg-pine-700 transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {connecting ? 'Verifying...' : 'Link Service Account Key'}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
