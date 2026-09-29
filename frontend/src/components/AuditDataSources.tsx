import React, { useEffect, useState } from 'react';
import { fetchExternalCoverage } from '../services/externalAuthority';

const LABELS: Record<string, string> = {
  google_search_console: 'Google Search Console',
  google_analytics_4: 'Google Analytics',
  bing_webmaster: 'Bing Webmaster',
  ahrefs: 'Ahrefs',
  semrush: 'Semrush',
  majestic: 'Majestic',
  dataforseo: 'DataForSEO',
  serpapi: 'SERP provider',
  google_business_profile: 'Google Business',
  citations: 'Citations',
  brand_mentions: 'Brand mentions',
};

export function AuditDataSources({ domain }: { domain: string }) {
  const [rows, setRows] = useState<Array<{ provider: string; connection_status: string; data_state: string }>>([]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      fetchExternalCoverage(domain || '')
        .then((payload) => setRows((payload.matrix || []) as Array<{ provider: string; connection_status: string; data_state: string }>))
        .catch(() => setRows([]));
    }, 400);
    return () => window.clearTimeout(handle);
  }, [domain]);

  const visible = ['google_search_console', 'google_analytics_4', 'bing_webmaster', 'ahrefs', 'google_business_profile', 'brand_mentions'];

  return (
    <div className="mt-4 pt-3 border-t border-line/60">
      <p className="label mb-2">Audit data sources</p>
      <ul className="flex flex-wrap gap-2 text-xs">
        <li className="px-2 py-1 rounded-full border border-line">Website Crawl ✓</li>
        {visible.map((id) => {
          const row = rows.find((item) => item.provider === id);
          const on = row && (row.connection_status === 'CONNECTED' || row.data_state === 'MEASURED' || row.data_state === 'PARTIALLY_MEASURED');
          const mark = row?.data_state === 'NOT_APPLICABLE' ? 'n/a' : on ? '✓' : '—';
          return (
            <li key={id} className="px-2 py-1 rounded-full border border-line">
              {LABELS[id] || id} {mark}
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-ink-500 mt-2">A dash means that source is not connected. It is not an SEO failure. Crawl depth does not limit external authority.</p>
    </div>
  );
}
