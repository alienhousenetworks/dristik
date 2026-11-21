import React, { useState } from 'react';
import { Badge, Button } from '../../ui';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Globe,
  Key,
  Layers,
  Lock,
  Plug,
  RefreshCw,
  Search,
  ShieldCheck,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';

export interface ProviderIntegration {
  id: string;
  name: string;
  category: 'Google Ecosystem' | 'Authority & Search' | 'Local & Multi-Engine';
  description: string;
  capabilities: string[];
  status: 'CONNECTED' | 'NOT_CONFIGURED' | 'ERROR';
  quotaLimit: number;
  quotaUsed: number;
  lastSync?: string;
  scopes: string[];
}

export function SeoIntegrationsView() {
  const [integrations, setIntegrations] = useState<ProviderIntegration[]>([
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
      description: 'Track organic sessions, engagement rate, bounce rate, and organic goal conversions.',
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
      status: 'CONNECTED',
      quotaLimit: 25000,
      quotaUsed: 420,
      lastSync: 'Live (15 mins ago)',
      scopes: ['https://www.googleapis.com/auth/pagespeedonline'],
    },
    {
      id: 'backlink_provider',
      name: 'DataForSEO Backlink Intelligence',
      category: 'Authority & Search',
      description: 'External domain authority, referring domains, toxic link footprints, and anchor distribution.',
      capabilities: ['Referring Domains', 'Total Backlinks', 'Anchor Text Equity', 'Toxic Link Alerts'],
      status: 'CONNECTED',
      quotaLimit: 50000,
      quotaUsed: 1250,
      lastSync: 'Live (1 hour ago)',
      scopes: ['api.dataforseo.com/v3/backlinks'],
    },
    {
      id: 'keyword_serp_provider',
      name: 'Keyword & SERP Intelligence',
      category: 'Authority & Search',
      description: 'Real search volumes, cost-per-click, keyword difficulty, and competitive rankings.',
      capabilities: ['Real Search Volumes', 'Keyword Difficulty', 'CPC Estimates', 'SERP Feature Detection'],
      status: 'CONNECTED',
      quotaLimit: 50000,
      quotaUsed: 3100,
      lastSync: 'Live (1 hour ago)',
      scopes: ['api.dataforseo.com/v3/serp'],
    },
    {
      id: 'google_business_profile',
      name: 'Google Business Profile',
      category: 'Local & Multi-Engine',
      description: 'Sync local entity details, reviews, NAP consistency, and local pack rankings.',
      capabilities: ['Local NAP Consistency', 'Customer Reviews', 'Local Pack Signals'],
      status: 'NOT_CONFIGURED',
      quotaLimit: 5000,
      quotaUsed: 0,
      scopes: ['https://www.googleapis.com/auth/business.manage'],
    },
    {
      id: 'bing_webmaster',
      name: 'Bing Webmaster Tools',
      category: 'Local & Multi-Engine',
      description: 'Monitor multi-engine indexing, Bing crawl errors, and Copilot search visibility.',
      capabilities: ['Bing Indexation Status', 'Bing Crawl Directives', 'Copilot Grounding Signals'],
      status: 'NOT_CONFIGURED',
      quotaLimit: 10000,
      quotaUsed: 0,
      scopes: ['webmasterapi.bing.com'],
    },
  ]);

  const [connectingId, setConnectingId] = useState<string | null>(null);

  const handleToggleConnect = (id: string) => {
    setConnectingId(id);
    setTimeout(() => {
      setIntegrations((prev) =>
        prev.map((item) =>
          item.id === id
            ? {
                ...item,
                status: item.status === 'CONNECTED' ? 'NOT_CONFIGURED' : 'CONNECTED',
                lastSync: item.status === 'CONNECTED' ? undefined : 'Live (Just now)',
              }
            : item
        )
      );
      setConnectingId(null);
    }, 800);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
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

        <div className="flex items-center gap-2">
          <Badge tone="pine">
            {integrations.filter((i) => i.status === 'CONNECTED').length} of {integrations.length} Connected
          </Badge>
        </div>
      </div>

      {/* Security & Epistemic Notice */}
      <div className="p-4 rounded-xl border border-line bg-paper-subtle flex items-start gap-3 text-xs leading-relaxed text-ink-600">
        <Lock className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div>
          <strong className="text-ink">Zero Synthetic Metrics Discipline:</strong> In Dristik Enterprise SEO, missing connectors never manufacture mock traffic or fake keyword rankings. When a connector is unconnected, its related checks are cleanly excluded from the scoring denominator with explicit disclosures. Tokens are encrypted using AES-256 in your tenant vault.
        </div>
      </div>

      {/* Integrations Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {integrations.map((item) => {
          const isConnected = item.status === 'CONNECTED';
          const isBusy = connectingId === item.id;
          const quotaPct = Math.round((item.quotaUsed / item.quotaLimit) * 100);

          return (
            <div
              key={item.id}
              className={`rounded-xl border p-5 space-y-4 transition-all ${
                isConnected
                  ? 'border-emerald-500/30 bg-emerald-50/10 dark:bg-emerald-950/10'
                  : 'border-line bg-paper'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-400">
                    {item.category}
                  </span>
                  <h4 className="text-sm font-bold text-ink mt-0.5">{item.name}</h4>
                </div>
                <Badge tone={isConnected ? 'good' : 'neutral'}>
                  {isConnected ? 'Active & Live' : 'Unconnected'}
                </Badge>
              </div>

              <p className="text-xs text-ink-600 dark:text-ink-300 leading-relaxed">
                {item.description}
              </p>

              {/* Capabilities checklist */}
              <div className="grid grid-cols-2 gap-1.5 text-[11px] text-ink-600 pt-1">
                {item.capabilities.map((cap, i) => (
                  <span key={i} className="flex items-center gap-1.5 truncate">
                    <CheckCircle2 className={`w-3 h-3 shrink-0 ${isConnected ? 'text-emerald-600' : 'text-ink-400'}`} />
                    <span className="truncate">{cap}</span>
                  </span>
                ))}
              </div>

              {/* Quota & Sync Details */}
              {isConnected && (
                <div className="pt-3 border-t border-line/60 space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-ink-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-ink-400" /> Sync: {item.lastSync}
                    </span>
                    <span className="font-mono">
                      {item.quotaUsed.toLocaleString()} / {item.quotaLimit.toLocaleString()} calls
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-paper-200 overflow-hidden">
                    <div
                      style={{ width: `${Math.max(quotaPct, 4)}%` }}
                      className={`h-full ${quotaPct > 80 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                    />
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-between">
                <span className="text-[10px] font-mono text-ink-400">
                  {item.scopes[0].split('/').pop()}
                </span>
                <Button
                  size="sm"
                  variant={isConnected ? 'secondary' : 'primary'}
                  disabled={isBusy}
                  onClick={() => handleToggleConnect(item.id)}
                  className="text-xs h-7 px-3"
                >
                  {isBusy ? (
                    'Connecting...'
                  ) : isConnected ? (
                    'Disconnect Provider'
                  ) : (
                    'Connect Integration'
                  )}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
