import React, { useState, useEffect } from 'react';

interface AnalyticsIntegrationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  domain?: string;
}

interface IntegrationItem {
  connected: boolean;
  provider: string;
  capabilities: string[];
  property_id?: string;
}

interface IntegrationStatus {
  google_search_console: IntegrationItem;
  google_analytics_4: IntegrationItem;
  dataforseo_keyword_index: IntegrationItem;
  ahrefs?: IntegrationItem;
  semrush?: IntegrationItem;
  majestic?: IntegrationItem;
  google_business_profile?: IntegrationItem;
  brand_mentions?: IntegrationItem;
  citations_directories?: IntegrationItem;
  [key: string]: any;
}

export function AnalyticsIntegrationsModal({
  isOpen,
  onClose,
  domain = '',
}: AnalyticsIntegrationsModalProps) {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [ga4PropertyId, setGa4PropertyId] = useState('');
  const [isSavingGa4, setIsSavingGa4] = useState(false);
  const [ga4SavedNotice, setGa4SavedNotice] = useState(false);
  const [ga4Error, setGa4Error] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'gsc' | 'ga4' | 'backlinks' | 'entity'>('overview');

  const refreshStatus = () => {
    fetch('/api/v1/integrations/status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setStatus(data);
      })
      .catch(() => {});
  };

  useEffect(() => {
    if (isOpen) {
      refreshStatus();
    }
  }, [isOpen]);

  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && (e.data.type === 'GSC_OAUTH_SUCCESS' || e.data.type === 'OAUTH_SUCCESS')) {
        refreshStatus();
      }
    };
    let bcConn: BroadcastChannel | null = null;
    let bcGsc: BroadcastChannel | null = null;
    try {
      bcConn = new BroadcastChannel('dristik_connector_oauth');
      bcConn.onmessage = () => refreshStatus();
      bcGsc = new BroadcastChannel('dristik_gsc_auth');
      bcGsc.onmessage = () => refreshStatus();
    } catch (_) {}

    const handleStorage = (e: StorageEvent) => {
      if ((e.key === 'dristik_gsc_auth_sync' || e.key === 'dristik_connector_oauth_sync') && e.newValue) {
        refreshStatus();
      }
    };

    window.addEventListener('message', handleMessage);
    window.addEventListener('storage', handleStorage);
    return () => {
      window.removeEventListener('message', handleMessage);
      window.removeEventListener('storage', handleStorage);
      if (bcConn) try { bcConn.close(); } catch (_) {}
      if (bcGsc) try { bcGsc.close(); } catch (_) {}
    };
  }, []);

  const startGa4Oauth = () => {
    const query = new URLSearchParams();
    if (domain) query.set('domain', domain);
    if (ga4PropertyId) query.set('property_id', ga4PropertyId);
    window.location.assign(`/api/v1/connectors/oauth/google_analytics_4/authorize?${query.toString()}`);
  };

  if (!isOpen) return null;

  const handleSaveGa4 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ga4PropertyId.trim()) return;
    setIsSavingGa4(true);
    setGa4Error(null);
    try {
      const res = await fetch('/api/v1/integrations/ga4/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ property_id: ga4PropertyId.trim() }),
      });
      if (res.ok) {
        setGa4SavedNotice(true);
        if (status) {
          setStatus({
            ...status,
            google_analytics_4: {
              ...status.google_analytics_4,
              connected: true,
              property_id: ga4PropertyId.trim(),
            },
          });
        }
        setTimeout(() => setGa4SavedNotice(false), 4000);
      } else {
        const body = await res.json().catch(() => ({}));
        setGa4Error(typeof body.detail === 'string' ? body.detail : 'GA4 did not connect. A property ID alone is not a measurement.');
      }
    } catch {
      setGa4Error('GA4 connection request failed.');
    } finally {
      setIsSavingGa4(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm animate-fade-in">
      <div
        className="sheet border border-line rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden bg-paper-50 dark:bg-ink-950"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-line flex items-center justify-between bg-paper-100/50 dark:bg-ink-900/50">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-bold border border-line">
                FIRST-PARTY GROUND TRUTH
              </span>
              <span className="font-mono text-xs text-ink-500">Domain: {domain}</span>
            </div>
            <h2 className="font-sans text-2xl text-ink font-bold mt-1">
              Analytics &amp; Authority Connectors
            </h2>
            <p className="text-xs text-ink-500 mt-0.5">
              Connect Google Search Console, GA4, Ahrefs, Semrush, Majestic, and Local Entity graphs for empirical telemetry.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-paper-200 dark:hover:bg-ink-800 text-ink-500 hover:text-ink transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tab Bar */}
        <div className="flex border-b border-line px-6 gap-3 bg-paper-50 dark:bg-ink-900/30 overflow-x-auto">
          {[
            { id: 'overview', label: 'Connector Overview' },
            { id: 'gsc', label: 'Google Search Console' },
            { id: 'ga4', label: 'Google Analytics 4' },
            { id: 'backlinks', label: 'Backlink & Authority (Ahrefs/Semrush/Majestic)' },
            { id: 'entity', label: 'Local Entity & Citations (GBP/Reviews)' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-2 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-line text-ink-700'
                  : 'border-transparent text-ink-500 hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-ink-700 dark:text-ink-300">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Category 1: Search Console & Traffic */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold tracking-[0.04em] text-ink-500 uppercase">
                  Search Telemetry &amp; Traffic (First-Party)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* GSC Card */}
                  <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex flex-col justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-bold text-ink text-sm">Google Search Console</span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            status?.google_search_console.connected
                              ? 'bg-good/10 text-good border-good/30'
                              : 'bg-warn/10 text-warn border-warn/30'
                          }`}
                        >
                          {status?.google_search_console.connected ? '● CONNECTED' : '○ UNCONNECTED'}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500">
                        Streams real search impressions, search queries, average positions, and Googlebot crawl indexing errors.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('gsc')}
                      className="mt-3 text-xs font-semibold text-ink-700 underline hover:text-ink self-start"
                    >
                      Configure →
                    </button>
                  </div>

                  {/* GA4 Card */}
                  <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex flex-col justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-bold text-ink text-sm">Google Analytics 4 (GA4)</span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            status?.google_analytics_4.connected
                              ? 'bg-good/10 text-good border-good/30'
                              : 'bg-warn/10 text-warn border-warn/30'
                          }`}
                        >
                          {status?.google_analytics_4.connected ? '● CONNECTED' : '○ UNCONNECTED'}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500">
                        Replaces bounce/conversion hypotheses with verified 30-day session dwell times and conversion funnels.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('ga4')}
                      className="mt-3 text-xs font-semibold text-ink-700 underline hover:text-ink self-start"
                    >
                      Configure →
                    </button>
                  </div>
                </div>
              </div>

              {/* Category 2: Authority & Backlink Graph */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold tracking-[0.04em] text-ink-500 uppercase">
                  Backlink Graph &amp; Off-Page Authority
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* DataForSEO Card */}
                  <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex flex-col justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-bold text-ink text-sm">DataForSEO Backlinks API</span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            status?.dataforseo_keyword_index.connected
                              ? 'bg-good/10 text-good border-good/30'
                              : 'bg-paper-200 text-ink-500 border-line'
                          }`}
                        >
                          {status?.dataforseo_keyword_index.connected ? '● LICENSED' : '○ UNCONNECTED'}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500">
                        Live referring domain graphs, anchor distribution, and search volumes.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('backlinks')}
                      className="mt-3 text-xs font-semibold text-ink-700 underline hover:text-ink self-start"
                    >
                      Details →
                    </button>
                  </div>

                  {/* Ahrefs / Semrush / Majestic Card */}
                  <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex flex-col justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-bold text-ink text-sm">Ahrefs / Semrush / Majestic</span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            status?.ahrefs?.connected || status?.semrush?.connected || status?.majestic?.connected
                              ? 'bg-good/10 text-good border-good/30'
                              : 'bg-paper-200 text-ink-500 border-line'
                          }`}
                        >
                          {status?.ahrefs?.connected || status?.semrush?.connected || status?.majestic?.connected
                            ? '● CONNECTED'
                            : '○ UNCONNECTED'}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500">
                        Authoritative Domain Rating, Citation Flow, Trust Flow, and referring IP topology.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('backlinks')}
                      className="mt-3 text-xs font-semibold text-ink-700 underline hover:text-ink self-start"
                    >
                      Configure →
                    </button>
                  </div>
                </div>
              </div>

              {/* Category 3: Local Entity & Brand Reputation */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold tracking-[0.04em] text-ink-500 uppercase">
                  Entity Graph &amp; Brand Reputation
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Google Business Profile */}
                  <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex flex-col justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-bold text-ink text-sm">Google Business Profile (GBP)</span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            status?.google_business_profile?.connected
                              ? 'bg-good/10 text-good border-good/30'
                              : 'bg-paper-200 text-ink-500 border-line'
                          }`}
                        >
                          {status?.google_business_profile?.connected ? '● CONNECTED' : '○ UNCONNECTED'}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500">
                        Local map pack rankings, verified business attributes, opening hours, and direct review telemetry.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('entity')}
                      className="mt-3 text-xs font-semibold text-ink-700 underline hover:text-ink self-start"
                    >
                      Details →
                    </button>
                  </div>

                  {/* Reviews & Citations */}
                  <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex flex-col justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-sans font-bold text-ink text-sm">Review Platforms &amp; Citations</span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            status?.citations_directories?.connected || status?.brand_mentions?.connected
                              ? 'bg-good/10 text-good border-good/30'
                              : 'bg-paper-200 text-ink-500 border-line'
                          }`}
                        >
                          {status?.citations_directories?.connected || status?.brand_mentions?.connected
                            ? '● CONNECTED'
                            : '○ UNCONNECTED'}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500">
                        Aggregates Yelp, Trustpilot, G2, directory NAP consistency, and co-citation web mentions.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('entity')}
                      className="mt-3 text-xs font-semibold text-ink-700 underline hover:text-ink self-start"
                    >
                      Details →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'gsc' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-2">
                <h3 className="font-sans font-bold text-ink text-base">Google Search Console Integration</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  Connect via Google Service Account JSON credentials or OAuth. Dristik will query the Search Console Search Analytics API to extract your actual 90-day search queries, clicks, impressions, and Googlebot indexing exclusions.
                </p>
                <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line font-mono text-xs text-ink-600">
                  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ga4' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-3">
                <h3 className="font-sans font-bold text-ink text-base">Google Analytics 4 Property Connector</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  Sign in with Google to automatically link your GA4 properties, or manually configure a service account property ID.
                </p>
                <button
                  type="button"
                  onClick={startGa4Oauth}
                  className="w-full py-2.5 px-4 rounded-lg border border-line bg-paper-50 dark:bg-ink-900 text-xs font-semibold text-ink hover:bg-paper-200 dark:hover:bg-ink-800 transition"
                >
                  1-Click Google Sign-In (OAuth SSO)
                </button>
              </div>

              <form onSubmit={handleSaveGa4} className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-2">
                <h4 className="font-sans font-semibold text-ink text-sm">Manual Property ID Probe</h4>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  Probes the GA4 Data API with the server service account. Requires GOOGLE_APPLICATION_CREDENTIALS.
                </p>
                <div className="pt-2 flex gap-3">
                  <input
                    type="text"
                    placeholder="Enter GA4 Property ID..."
                    value={ga4PropertyId}
                    onChange={(e) => setGa4PropertyId(e.target.value)}
                    className="flex-1 px-3 py-2 rounded-lg border border-line bg-paper-50 dark:bg-ink-900 font-mono text-xs text-ink focus:outline-none focus:border-pine"
                  />
                  <button
                    type="submit"
                    disabled={isSavingGa4}
                    className="px-4 py-2 rounded-lg bg-pine text-white text-xs font-semibold hover:opacity-90 transition-opacity"
                  >
                    {isSavingGa4 ? 'Saving...' : 'Connect GA4'}
                  </button>
                </div>
                {ga4SavedNotice && (
                  <p className="text-xs text-good font-semibold">GA4 Data API probe succeeded.</p>
                )}
                {ga4Error && (
                  <p className="text-xs text-bad font-semibold">{ga4Error}</p>
                )}
              </form>
            </div>
          )}

          {activeTab === 'backlinks' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-3">
                <h3 className="font-sans font-bold text-ink text-base">Backlink Graph &amp; Off-Page Authority Providers</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  Unlike legacy SEO tools that fabricate synthetic domain scores, Dristik never reports backlink authority without a live verified link graph provider. When unconnected, Dristik labels trust authority as <span className="font-semibold text-warn">Not measured — connector unavailable</span> and renormalizes the audit score strictly across measured categories.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                  <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line space-y-1">
                    <div className="font-bold text-xs text-ink">Ahrefs API v3</div>
                    <div className="text-[11px] text-ink-500">Connect via OAuth or API Key in <span className="font-mono">.env</span>:</div>
                    <div className="font-mono text-[10px] text-ink-600">AHREFS_API_KEY=your_key</div>
                    <div className="font-mono text-[10px] text-ink-600">AHREFS_CLIENT_ID=your_id</div>
                  </div>
                  <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line space-y-1">
                    <div className="font-bold text-xs text-ink">Semrush Authority API</div>
                    <div className="text-[11px] text-ink-500">Configure OAuth or API token:</div>
                    <div className="font-mono text-[10px] text-ink-600">SEMRUSH_API_KEY=your_key</div>
                    <div className="font-mono text-[10px] text-ink-600">SEMRUSH_CLIENT_ID=your_id</div>
                  </div>
                  <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line space-y-1">
                    <div className="font-bold text-xs text-ink">Majestic SEO</div>
                    <div className="text-[11px] text-ink-500">Flow metrics &amp; Topical Trust:</div>
                    <div className="font-mono text-[10px] text-ink-600">MAJESTIC_API_KEY=your_key</div>
                  </div>
                  <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line space-y-1">
                    <div className="font-bold text-xs text-ink">DataForSEO Link Index</div>
                    <div className="text-[11px] text-ink-500">Live referring domains &amp; backlink counts:</div>
                    <div className="font-mono text-[10px] text-ink-600">DATAFORSEO_LOGIN=login</div>
                    <div className="font-mono text-[10px] text-ink-600">DATAFORSEO_PASSWORD=pass</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'entity' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-3">
                <h3 className="font-sans font-bold text-ink text-base">Local Business, Reviews &amp; Directory Citations</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  Real reputation signals feed into local pack visibility and Knowledge Graph entity verification.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                  <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line space-y-1">
                    <div className="font-bold text-xs text-ink">Google Business Profile (GBP)</div>
                    <div className="text-[11px] text-ink-500">Configure GBP credentials:</div>
                    <div className="font-mono text-[10px] text-ink-600">GBP_ACCOUNT_ID=account_id</div>
                    <div className="font-mono text-[10px] text-ink-600">GOOGLE_APPLICATION_CREDENTIALS=...</div>
                  </div>
                  <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line space-y-1">
                    <div className="font-bold text-xs text-ink">Review Platforms &amp; Brand Mentions</div>
                    <div className="text-[11px] text-ink-500">Yelp, Trustpilot, G2 &amp; co-citation trackers:</div>
                    <div className="font-mono text-[10px] text-ink-600">BRAND_MENTIONS_ENABLED=true</div>
                    <div className="font-mono text-[10px] text-ink-600">BRAND_MENTIONS_API_KEY=...</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-line flex items-center justify-between bg-paper-100/50 dark:bg-ink-900/50">
          <span className="text-xs font-mono text-ink-500">
            Dristik Zero-Fake Standard: Grounded in First-Party APIs
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-ink text-paper-50 dark:bg-paper-100 dark:text-ink font-semibold text-xs hover:opacity-90 transition-opacity"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
