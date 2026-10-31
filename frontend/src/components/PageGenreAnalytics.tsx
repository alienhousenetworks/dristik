import React, { useState } from 'react';
import { PageEvidence, PageReport } from '../types';

export type PageGenre =
  | 'ecommerce'
  | 'saas'
  | 'editorial'
  | 'homepage'
  | 'service'
  | 'documentation'
  | 'company';

export interface GenreConfig {
  id: PageGenre;
  name: string;
  badge: string;
}

export const GENRE_CONFIGS: Record<PageGenre, GenreConfig> = {
  ecommerce: { id: 'ecommerce', name: 'Commerce', badge: 'COMMERCE' },
  saas: { id: 'saas', name: 'Product', badge: 'PRODUCT' },
  editorial: { id: 'editorial', name: 'Editorial', badge: 'EDITORIAL' },
  homepage: { id: 'homepage', name: 'Homepage', badge: 'HOMEPAGE' },
  service: { id: 'service', name: 'Services', badge: 'SERVICES' },
  documentation: { id: 'documentation', name: 'Documentation', badge: 'DOCS' },
  company: { id: 'company', name: 'Company', badge: 'COMPANY' },
};

export function detectPageGenre(pageType?: string, url = '', title = ''): PageGenre {
  const p = (pageType || '').toLowerCase();
  const u = url.toLowerCase();
  const t = title.toLowerCase();

  if (
    p.includes('product') ||
    p.includes('cart') ||
    p.includes('shop') ||
    p.includes('checkout') ||
    p.includes('collection') ||
    u.includes('/product') ||
    u.includes('/shop') ||
    u.includes('/cart')
  ) {
    return 'ecommerce';
  }
  if (
    p.includes('pricing') ||
    p.includes('saas') ||
    p.includes('landing') ||
    p.includes('feature') ||
    u.includes('/pricing') ||
    u.includes('/features') ||
    t.includes('pricing')
  ) {
    return 'saas';
  }
  if (
    p.includes('blog') ||
    p.includes('article') ||
    p.includes('post') ||
    p.includes('news') ||
    p.includes('guide') ||
    u.includes('/blog') ||
    u.includes('/article') ||
    u.includes('/posts') ||
    u.includes('/news')
  ) {
    return 'editorial';
  }
  if (
    p.includes('doc') ||
    p.includes('api') ||
    p.includes('support') ||
    p.includes('faq') ||
    u.includes('/docs') ||
    u.includes('/api') ||
    u.includes('/help')
  ) {
    return 'documentation';
  }
  if (
    p.includes('service') ||
    p.includes('solution') ||
    u.includes('/service') ||
    u.includes('/solutions') ||
    u.includes('/consulting')
  ) {
    return 'service';
  }
  if (
    p.includes('about') ||
    p.includes('contact') ||
    p.includes('team') ||
    p.includes('career') ||
    u.includes('/about') ||
    u.includes('/contact') ||
    u.includes('/team')
  ) {
    return 'company';
  }
  const path = u.replace(/https?:\/\/[^/]+/, '').replace(/\/$/, '');
  if (!path || path === '' || p.includes('home') || p.includes('root')) {
    return 'homepage';
  }
  return 'saas';
}

export interface Ga4LandingPageMetrics {
  path: string;
  sessions: number;
  bounce_rate: number;
  engagement_rate?: number;
  avg_duration_sec?: number;
  conversions: number;
  conversion_rate?: number;
}

interface PageGenreAnalyticsProps {
  page: PageEvidence;
  report?: PageReport;
  ga4LandingPages?: Ga4LandingPageMetrics[];
}

export function PageGenreAnalytics({ page, report, ga4LandingPages }: PageGenreAnalyticsProps) {
  const [activeTab, setActiveTab] = useState<'measured' | 'specialist'>('measured');
  const genreId = detectPageGenre(page.page_type, page.url, page.title);
  const genre = GENRE_CONFIGS[genreId];
  const copy = report?.copywriting;
  const suggested = copy?.suggested;

  const pagePath = (() => {
    try {
      return new URL(page.url).pathname || '/';
    } catch {
      return page.url.replace(/^https?:\/\/[^/]+/, '') || '/';
    }
  })();
  const matchingGa4 = ga4LandingPages?.find(
    (lp) => lp.path === pagePath || lp.path === pagePath.replace(/\/$/, '') || (pagePath !== '/' && lp.path.includes(pagePath))
  );

  const words = page.word_count || 0;
  const titleLen = (page.title || '').length;
  const h1Count = page.h1?.length ?? 0;
  const ctaCount = page.ctas?.length || report?.ux?.cta_count || 0;
  const ttfb = page.ttfb_ms && page.ttfb_ms > 0 ? Math.round(page.ttfb_ms) : null;
  const images = page.total_images || 0;
  const missingAlt = page.images_without_alt || 0;
  const schema = page.schema_types?.length ? page.schema_types.join(', ') : 'none stored';

  const facts: Array<[string, string]> = [
    ['Role label', genre.name],
    ['Words', String(words)],
    ['Title', titleLen ? `${titleLen} characters` : 'absent'],
    ['H1 headings', String(h1Count)],
    ['Calls to action', String(ctaCount)],
    ['Server response', ttfb == null ? 'not stored' : `${ttfb} ms`],
    ['Images without alt', images ? `${missingAlt} of ${images}` : 'no image count stored'],
    ['Schema types', schema],
    ['Readability', page.readability_score ? String(Math.round(page.readability_score)) : 'not stored'],
  ];

  return (
    <div className="rounded-xl border border-line bg-paper-50/70 p-5 space-y-6 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase bg-pine/15 text-pine dark:text-pine-light border border-pine/30">
              {genre.badge}
            </span>
            <span className="text-xs font-semibold text-ink-700">{genre.name}</span>
          </div>
          <p className="text-xs text-ink-500 leading-relaxed max-w-2xl">
            Role label from the URL and page type. It does not set a word count, a score, or a fix.
          </p>
        </div>
        <div className="flex items-center gap-1.5 p-1 bg-paper-100 rounded-lg border border-line text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('measured')}
            className={`px-3 py-1 rounded font-medium transition cursor-pointer ${activeTab === 'measured' ? 'bg-paper-50 text-ink shadow-xs border border-line font-bold' : 'text-ink-500 hover:text-ink'}`}
          >
            Measured
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('specialist')}
            className={`px-3 py-1 rounded font-medium transition cursor-pointer ${activeTab === 'specialist' ? 'bg-paper-50 text-ink shadow-xs border border-line font-bold' : 'text-ink-500 hover:text-ink'}`}
          >
            Specialist
          </button>
        </div>
      </div>

      {matchingGa4 ? (
        <div className="p-3.5 rounded-lg border border-pine/30 bg-pine/5 space-y-2">
          <span className="text-xs font-bold text-pine dark:text-pine-light">GA4 for {matchingGa4.path}</span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Sessions</span>
              <span className="font-mono font-bold text-ink">{matchingGa4.sessions.toLocaleString()}</span>
            </div>
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Bounce rate</span>
              <span className="font-mono font-bold text-ink">{matchingGa4.bounce_rate}%</span>
            </div>
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Engagement</span>
              <span className="font-mono font-bold text-ink">{matchingGa4.engagement_rate != null ? `${matchingGa4.engagement_rate}%` : '—'}</span>
            </div>
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Key events</span>
              <span className="font-mono font-bold text-ink">{matchingGa4.conversions}</span>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-[11px] text-ink-500">GA4 is not connected for this path. Sessions and conversion rate are not filled in.</p>
      )}

      {activeTab === 'measured' && (
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {facts.map(([label, value]) => (
            <div key={label} className="p-3 rounded-lg border border-line bg-paper-50">
              <dt className="text-ink-500">{label}</dt>
              <dd className="mt-1 font-mono text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      )}

      {activeTab === 'specialist' && (
        <div className="space-y-3 text-xs">
          {copy?.analysis ? (
            <p className="text-ink-700 leading-relaxed">{copy.analysis}</p>
          ) : (
            <p className="text-ink-500 leading-relaxed">
              The page specialist has not written a judgment for this URL. The measured tab is the crawl record.
            </p>
          )}
          {copy?.issues?.length ? (
            <ul className="space-y-2">
              {copy.issues.map((item) => (
                <li key={`${item.area}-${item.issue}`} className="p-3 rounded border border-line bg-paper-50 text-ink-700">
                  <span className="font-semibold text-ink">{item.area}. </span>
                  {item.issue}
                  {item.why_it_matters ? ` ${item.why_it_matters}` : ''}
                </li>
              ))}
            </ul>
          ) : null}
          {suggested?.title ? <p className="text-ink-700"><span className="text-ink-500">Title. </span>{suggested.title}</p> : null}
          {suggested?.meta_description ? <p className="text-ink-700"><span className="text-ink-500">Description. </span>{suggested.meta_description}</p> : null}
          {suggested?.h1 ? <p className="text-ink-700"><span className="text-ink-500">H1. </span>{suggested.h1}</p> : null}
          {suggested?.hero ? <p className="text-ink-700"><span className="text-ink-500">Hero. </span>{suggested.hero}</p> : null}
          {suggested?.primary_cta ? <p className="text-ink-700"><span className="text-ink-500">Call to action. </span>{suggested.primary_cta}</p> : null}
        </div>
      )}
    </div>
  );
}
