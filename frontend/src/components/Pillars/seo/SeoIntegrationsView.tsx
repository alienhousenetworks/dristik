import React, { useEffect, useState } from 'react';
import { Badge, Button } from '../../ui';
import { seoApi, SeoConnectorStatus } from '../../../services/seoApi';
import { CheckCircle2, Clock, Lock, Plug } from 'lucide-react';

export interface ProviderIntegration {
  id: string;
  name: string;
  category: string;
  description: string;
  capabilities: string[];
  status: 'CONNECTED' | 'NOT_CONFIGURED' | 'ERROR' | 'QUOTA_EXCEEDED';
  quotaLimit: number;
  quotaUsed: number;
  lastSync?: string | null;
  freshnessHours?: number | null;
  scopes: string[];
}

const DEFAULT_CATALOG: ProviderIntegration[] = [
  {
    id: 'google_search_console',
    name: 'Google Search Console',
    category: 'Google Ecosystem',
    description: 'Stream verified organic search queries, impressions, clicks, CTR, and average position.',
    capabilities: ['Search Queries', 'Clicks & Impressions', 'CTR & Avg Position', 'Index Coverage Errors'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 10000,
    quotaUsed: 0,
    scopes: ['https://www.googleapis.com/auth/webmasters.readonly'],
  },
  {
    id: 'google_analytics_4',
    name: 'Google Analytics 4',
    category: 'Google Ecosystem',
    description: 'Track organic sessions, engagement rate, key events, and organic landing-page conversions.',
    capabilities: ['Organic Sessions', 'Engagement Rate', 'Goal Conversions', 'Top Landing Pages'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 25000,
    quotaUsed: 0,
    scopes: ['https://www.googleapis.com/auth/analytics.readonly'],
  },
  {
    id: 'pagespeed_crux',
    name: 'PageSpeed Insights & CrUX',
    category: 'Google Ecosystem',
    description: 'Collect empirical lab and real-user field Core Web Vitals (LCP, CLS, INP, TTFB).',
    capabilities: ['Field Core Web Vitals', 'Lighthouse Lab Diagnostics', 'Mobile & Desktop Breakdowns'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 25000,
    quotaUsed: 0,
    scopes: ['https://www.googleapis.com/auth/pagespeedonline'],
  },
  {
    id: 'backlink_provider',
    name: 'DataForSEO Backlink Intelligence',
    category: 'Authority & Backlinks',
    description: 'External domain authority, referring domains, toxic link footprints, and anchor distribution.',
    capabilities: ['Referring Domains', 'Total Backlinks', 'Anchor Text Equity', 'Toxic Link Alerts'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 50000,
    quotaUsed: 0,
    scopes: ['api.dataforseo.com/v3/backlinks'],
  },
  {
    id: 'keyword_serp_provider',
    name: 'Keyword & SERP Intelligence',
    category: 'Search Performance',
    description: 'Real search volumes, cost-per-click, keyword difficulty, and competitive rankings.',
    capabilities: ['Real Search Volumes', 'Keyword Difficulty', 'CPC Estimates', 'SERP Feature Detection'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 50000,
    quotaUsed: 0,
    scopes: ['api.dataforseo.com/v3/serp'],
  },
  {
    id: 'google_business_profile',
    name: 'Google Business Profile',
    category: 'Local SEO',
    description: 'Sync local entity details, reviews, NAP consistency, and local pack signals.',
    capabilities: ['Local NAP Consistency', 'Customer Reviews', 'Local Pack Signals'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 5000,
    quotaUsed: 0,
    scopes: ['https://www.googleapis.com/auth/business.manage'],
  },
  {
    id: 'bing_webmaster',
    name: 'Bing Webmaster Tools',
    category: 'Multi-Engine Search',
    description: 'Monitor multi-engine indexing, Bing crawl errors, and Copilot grounding signals.',
    capabilities: ['Bing Indexation Status', 'Bing Crawl Directives', 'Copilot Grounding Signals'],
    status: 'NOT_CONFIGURED',
    quotaLimit: 10000,
    quotaUsed: 0,
    scopes: ['webmasterapi.bing.com'],
  },
];

interface SeoIntegrationsViewProps {
  workspaceId?: string;
  onConnectorsUpdated?: (items: SeoConnectorStatus[]) => void;
}

export function SeoIntegrationsView({ workspaceId, onConnectorsUpdated }: SeoIntegrationsViewProps) {
  const [integrations, setIntegrations] = useState<ProviderIntegration[]>(DEFAULT_CATALOG);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<string | null>(null);

  const applyServerStatuses = (rows: SeoConnectorStatus[]) => {
    const byId = new Map(rows.map((r) => [r.provider_id, r]));
    setIntegrations((prev) =>
      prev.map((item) => {
        const srv = byId.get(item.id);
        if (!srv) return item;
        return {
          ...item,
          status: srv.status,
          quotaLimit: srv.daily_quota_limit,
          quotaUsed: srv.daily_quota_used,
          lastSync: srv.last_sync_timestamp,
          freshnessHours: srv.data_freshness_hours,
          scopes: srv.scopes_granted.length > 0 ? srv.scopes_granted : srv.scopes_required,
        };
      })
    );
    onConnectorsUpdated?.(rows);
  };

  useEffect(() => {
    let active = true;
    seoApi
      .listConnectors(workspaceId)
      .then((rows) => {
        if (active && Array.isArray(rows)) applyServerStatuses(rows);
      })
      .catch(() => {
        /* Unauthenticated or offline test mode keeps honest NOT_CONFIGURED defaults */
      });
    return () => {
      active = false;
    };
  }, [workspaceId]);

  const handleToggleConnect = async (item: ProviderIntegration) => {
    setConnectingId(item.id);
    setFeedback(null);
    try {
      if (item.status === 'CONNECTED') {
        await seoApi.disconnectProvider(item.id, workspaceId);
        setIntegrations((prev) =>
          prev.map((c) => (c.id === item.id ? { ...c, status: 'NOT_CONFIGURED', lastSync: null, quotaUsed: 0 } : c))
        );
        setFeedback(`Disconnected ${item.name} and revoked encrypted credentials.`);
      } else {
        const tokenValue = (apiKeys[item.id] || '').trim() || `oauth_pending_${item.id}`;
        const updated = await seoApi.connectProvider(item.id, { api_key: tokenValue }, workspaceId);
        applyServerStatuses([updated]);
        setFeedback(`Connected ${item.name} with encrypted storage.`);
      }
    } catch (err: any) {
      setFeedback(err?.message || `Unable to update ${item.name}. Ensure you are signed in and provide valid credentials.`);
    } finally {
      setConnectingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Plug className="w-5 h-5 text-primary" />
            <h3 className="text-base font-bold text-ink">SEO Integrations &amp; Connectors Hub</h3>
          </div>
          <p className="text-xs text-ink-500">
            Connect first-party search platforms, analytics, and external authority providers. Unconnected connectors fail-closed without inventing fake numbers.
          </p>
        </div>
        <Badge tone="pine">
          {integrations.filter((i) => i.status === 'CONNECTED').length} of {integrations.length} Connected
        </Badge>
      </div>

      <div className="p-4 rounded-xl border border-line bg-paper-subtle flex items-start gap-3 text-xs leading-relaxed text-ink-600">
        <Lock className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div>
          <strong className="text-ink">Zero Synthetic Metrics Discipline:</strong> Missing connectors never manufacture mock traffic or fake keyword rankings. Unconnected dimensions are excluded from the scoring denominator with explicit disclosures. Credentials are encrypted with Fernet AES-HMAC in your tenant vault.
        </div>
      </div>

      {feedback && (
        <div className="px-3 py-2 rounded-lg bg-paper-subtle border border-line text-xs text-ink-700">{feedback}</div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {integrations.map((item) => {
          const isConnected = item.status === 'CONNECTED';
          const isBusy = connectingId === item.id;
          const quotaPct = item.quotaLimit > 0 ? Math.round((item.quotaUsed / item.quotaLimit) * 100) : 0;

          return (
            <div
              key={item.id}
              className={`rounded-xl border p-5 space-y-4 transition-all ${
                isConnected ? 'border-emerald-500/30 bg-emerald-50/10' : 'border-line bg-paper'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-400">{item.category}</span>
                  <h4 className="text-sm font-bold text-ink mt-0.5">{item.name}</h4>
                </div>
                <Badge tone={isConnected ? 'good' : 'neutral'}>{isConnected ? 'Active & Live' : 'Unconnected'}</Badge>
              </div>

              <p className="text-xs text-ink-600 leading-relaxed">{item.description}</p>

              <div className="grid grid-cols-2 gap-1.5 text-[11px] text-ink-600 pt-1">
                {item.capabilities.map((cap, i) => (
                  <span key={i} className="flex items-center gap-1.5 truncate">
                    <CheckCircle2 className={`w-3 h-3 shrink-0 ${isConnected ? 'text-emerald-600' : 'text-ink-400'}`} />
                    <span className="truncate">{cap}</span>
                  </span>
                ))}
              </div>

              {!isConnected && (
                <input
                  type="password"
                  placeholder="API key or OAuth token..."
                  value={apiKeys[item.id] || ''}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-line bg-paper-subtle text-ink"
                />
              )}

              {isConnected && (
                <div className="pt-3 border-t border-line/60 space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-ink-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-ink-400" /> Sync: {item.lastSync || 'Synced'}
                    </span>
                    <span className="font-mono">
                      {item.quotaUsed.toLocaleString()} / {item.quotaLimit.toLocaleString()} calls
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-paper-200 overflow-hidden">
                    <div style={{ width: `${Math.max(quotaPct, 2)}%` }} className={`h-full ${quotaPct > 80 ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                  </div>
                </div>
              )}

              <div className="pt-2 flex items-center justify-between">
                <span className="text-[10px] font-mono text-ink-400">{item.scopes[0]?.split('/').pop()}</span>
                <Button
                  size="sm"
                  variant={isConnected ? 'secondary' : 'primary'}
                  disabled={isBusy}
                  onClick={() => handleToggleConnect(item)}
                  className="text-xs h-7 px-3"
                >
                  {isBusy ? 'Connecting...' : isConnected ? 'Disconnect Provider' : 'Connect Integration'}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
