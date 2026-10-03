import React from 'react';
import { LifecycleRevenueIntelligence, ConnectorType } from '../types';

interface LifecycleRevenueIntelligenceViewProps {
  lifecycleData?: LifecycleRevenueIntelligence;
  onOpenConnectors?: (initialTab?: ConnectorType) => void;
}

const CANNED = new Set([17700, 14200, 1020, 14200000, 6050000]);

function metric(value: unknown): string {
  if (value == null || value === 'UNKNOWN' || value === '') return 'UNKNOWN';
  if (typeof value === 'number' && CANNED.has(value)) return 'UNKNOWN';
  return String(value);
}

export function LifecycleRevenueIntelligenceView({
  lifecycleData,
  onOpenConnectors,
}: LifecycleRevenueIntelligenceViewProps) {
  const gsc = lifecycleData?.gsc;
  const ga4 = lifecycleData?.ga4;
  const crm = lifecycleData?.crm;
  const gscLive = Boolean(gsc?.is_connected) && !CANNED.has(gsc?.impressions || 0);
  const ga4Live = Boolean(ga4?.is_connected) && !(ga4?.landing_pages || []).some((row) => row.sessions === 14200);
  const crmLive = Boolean(crm?.is_connected) && !CANNED.has(crm?.pipeline_value_inr || 0);
  const stages = lifecycleData?.stages || {};

  const cards = [
    {
      title: 'Website',
      status: 'See the crawl',
      rows: [
        ['DOM / TTFB / schema', 'On the audit, not repeated here'],
      ],
    },
    {
      title: 'Search (GSC)',
      status: gscLive ? 'Measured' : 'Not measured',
      rows: [
        ['Impressions', gscLive ? metric(gsc?.impressions) : 'UNKNOWN'],
        ['Clicks', gscLive ? metric(gsc?.clicks) : 'UNKNOWN'],
        ['CTR', gscLive ? metric(stages.search?.metrics?.ctr ?? gsc?.ctr) : 'UNKNOWN'],
      ],
    },
    {
      title: 'Visitors (GA4)',
      status: ga4Live ? 'Measured' : 'Not measured',
      rows: [
        ['Engagement', ga4Live ? metric(stages.visitor?.metrics?.engagement_rate) : 'UNKNOWN'],
        ['Conversion', ga4Live ? metric(stages.visitor?.metrics?.conversion_rate) : 'UNKNOWN'],
        ['Abandonment', 'UNKNOWN'],
      ],
    },
    {
      title: 'Leads (CRM)',
      status: crmLive ? 'Measured' : 'Not measured',
      rows: [
        ['Lead quality', crmLive ? metric(crm?.lead_quality_score) : 'UNKNOWN'],
        ['Lead → customer', crmLive ? metric(crm?.conversion_rate_lead_to_customer) : 'UNKNOWN'],
      ],
    },
    {
      title: 'Revenue',
      status: crmLive ? 'Measured' : 'Not measured',
      rows: [
        ['Pipeline', crmLive ? metric(crm?.pipeline_value_inr) : 'UNKNOWN'],
        ['Closed', crmLive ? metric(crm?.closed_revenue_inr) : 'UNKNOWN'],
      ],
    },
  ];

  return (
    <div className="bg-paper-50 border border-line rounded-xl p-5 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-sans text-lg font-bold text-ink">Search, visitors, leads, revenue</h3>
          <p className="text-xs text-ink-600 mt-1 max-w-2xl">
            {lifecycleData?.summary || 'These numbers stay blank until Google Search Console, GA4, or a CRM returns them.'}
          </p>
        </div>
        {onOpenConnectors && (
          <button
            type="button"
            onClick={() => onOpenConnectors('google_search_console')}
            className="text-xs font-mono text-ink-700 underline"
          >
            Open connectors
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {cards.map((card) => (
          <div key={card.title} className="p-3 rounded-lg border border-line bg-paper-50 space-y-2">
            <div className="flex items-center justify-between text-[10px] font-mono uppercase text-ink-500">
              <span>{card.title}</span>
              <span>{card.status}</span>
            </div>
            {card.rows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-2 font-mono text-[10px]">
                <span className="text-ink-500">{label}</span>
                <span className="font-bold text-ink text-right">{value}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
