import React, { useState, useEffect } from 'react';

interface AnalyticsIntegrationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  domain?: string;
}

interface IntegrationStatus {
  google_search_console: {
    connected: boolean;
    provider: string;
    capabilities: string[];
  };
  google_analytics_4: {
    connected: boolean;
    property_id?: string;
    provider: string;
    capabilities: string[];
  };
  dataforseo_keyword_index: {
    connected: boolean;
    provider: string;
    capabilities: string[];
  };
}

export function AnalyticsIntegrationsModal({
  isOpen,
  onClose,
  domain = 'example.com',
}: AnalyticsIntegrationsModalProps) {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [ga4PropertyId, setGa4PropertyId] = useState('');
  const [isSavingGa4, setIsSavingGa4] = useState(false);
  const [ga4SavedNotice, setGa4SavedNotice] = useState(false);
  const [ga4Error, setGa4Error] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'gsc' | 'ga4' | 'backlinks'>('overview');

  useEffect(() => {
    if (isOpen) {
      fetch('/api/v1/integrations/status')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) setStatus(data);
        })
        .catch(() => {});
    }
  }, [isOpen]);

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
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-pine/10 text-pine font-bold border border-pine/30">
                FIRST-PARTY GROUND TRUTH
              </span>
              <span className="font-mono text-xs text-ink-500">Domain: {domain}</span>
            </div>
            <h2 className="font-serif text-2xl text-ink font-bold mt-1">
              Analytics &amp; Search Index Connectors
            </h2>
            <p className="text-xs text-ink-500 mt-0.5">
              Connect your verified Google Search Console, GA4 property, and DataForSEO link graph for empirical telemetry.
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
        <div className="flex border-b border-line px-6 gap-3 bg-paper-50 dark:bg-ink-900/30">
          {[
            { id: 'overview', label: 'Connector Overview' },
            { id: 'gsc', label: 'Google Search Console' },
            { id: 'ga4', label: 'Google Analytics 4' },
            { id: 'backlinks', label: 'Backlink Graph' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-2 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-pine text-pine'
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
            <div className="space-y-4">
              {/* GSC Card */}
              <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-serif font-bold text-ink text-base">Google Search Console</span>
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                        status?.google_search_console.connected
                          ? 'bg-good/10 text-good border-good/30'
                          : 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                      }`}
                    >
                      {status?.google_search_console.connected ? '● CONNECTED' : '○ SANDBOX CALIBRATED'}
                    </span>
                  </div>
                  <p className="text-xs text-ink-500">
                    Streams real search impressions, search queries, average positions, and Googlebot crawl indexing errors.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('gsc')}
                  className="text-xs font-semibold text-pine underline hover:text-ink"
                >
                  Configure →
                </button>
              </div>

              {/* GA4 Card */}
              <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-serif font-bold text-ink text-base">Google Analytics 4 (GA4)</span>
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                        status?.google_analytics_4.connected
                          ? 'bg-good/10 text-good border-good/30'
                          : 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                      }`}
                    >
                      {status?.google_analytics_4.connected ? '● CONNECTED' : '○ SANDBOX CALIBRATED'}
                    </span>
                  </div>
                  <p className="text-xs text-ink-500">
                    Replaces bounce/conversion hypotheses with verified 30-day session dwell times and conversion funnels.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('ga4')}
                  className="text-xs font-semibold text-pine underline hover:text-ink"
                >
                  Configure →
                </button>
              </div>

              {/* Backlink Graph Card */}
              <div className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-serif font-bold text-ink text-base">DataForSEO / Majestic Backlink Index</span>
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
                    Live referring domain graphs and keyword search volume. (Zero-Fake standard: On-Page Trust is strictly reported without fabricated link counts when unconnected).
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('backlinks')}
                  className="text-xs font-semibold text-pine underline hover:text-ink"
                >
                  Details →
                </button>
              </div>
            </div>
          )}

          {activeTab === 'gsc' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-2">
                <h3 className="font-serif font-bold text-ink text-base">Google Search Console Integration</h3>
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
            <form onSubmit={handleSaveGa4} className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-2">
                <h3 className="font-serif font-bold text-ink text-base">Google Analytics 4 Property Connector</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  A numeric property ID is not a connection. Dristik probes the GA4 Data API with the server service account and only then marks the property measured. Set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON first.
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
              </div>
            </form>
          )}

          {activeTab === 'backlinks' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-paper-100/60 dark:bg-ink-900/60 border border-line space-y-2">
                <h3 className="font-serif font-bold text-ink text-base">Backlink Graph &amp; Keyword Index License</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  Unlike legacy SEO tools that fabricate synthetic domain scores, Dristik never claims backlink authority without a live verified link graph provider.
                </p>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  To enable live competitor backlink comparisons (referring domains, citation flow), configure DataForSEO credentials in your <span className="font-mono">.env</span> file:
                </p>
                <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded border border-line font-mono text-xs text-ink-600 space-y-1">
                  <div>DATAFORSEO_LOGIN=your_api_login</div>
                  <div>DATAFORSEO_PASSWORD=your_api_password</div>
                  <div>CRUX_API_KEY=your_chrome_ux_report_key</div>
                  <div>CLEARBIT_API_KEY=your_clearbit_key</div>
                  <div>BUILTWITH_API_KEY=your_builtwith_key</div>
                  <div>CRUNCHBASE_API_KEY=your_crunchbase_user_key</div>
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
