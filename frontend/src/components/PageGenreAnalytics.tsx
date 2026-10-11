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
  archetype: string;
  description: string;
  targetWordRange: [number, number];
  targetReadability: number;
  targetCtaRatio: number; // 1 CTA per N words
  targetAltRatio: number; // percentage
  targetTtfbMs: number;
  directives: string[];
  geoFocus: string;
}

export const GENRE_CONFIGS: Record<PageGenre, GenreConfig> = {
  ecommerce: {
    id: 'ecommerce',
    name: 'E-Commerce / Product & Catalog',
    badge: 'ECOMMERCE',
    archetype: 'Transactional Catalog & Conversion Page',
    description: 'Engineered for high purchase intent, frictionless checkout, and rich merchant schema visibility.',
    targetWordRange: [600, 1400],
    targetReadability: 65,
    targetCtaRatio: 250,
    targetAltRatio: 100,
    targetTtfbMs: 350,
    directives: [
      'Implement Product, AggregateRating, and Offer JSON-LD schema for Google Shopping rich snippets.',
      'Place primary Add to Cart / Checkout CTA within first 20% of scroll depth with sticky buy button.',
      'Provide comprehensive image alt coverage for all product variants and colorways.',
    ],
    geoFocus: 'Optimized for product specifications, pricing parity, and stock availability queries in AI shopping assistants.',
  },
  saas: {
    id: 'saas',
    name: 'B2B SaaS / Product Tour & Conversion',
    badge: 'B2B SAAS',
    archetype: 'Value Proposition & Free Trial Horizon',
    description: 'Designed to capture high-intent problem solvers through rigorous proof and immediate 3-second hook.',
    targetWordRange: [800, 2000],
    targetReadability: 60,
    targetCtaRatio: 300,
    targetAltRatio: 90,
    targetTtfbMs: 400,
    directives: [
      'Anchor an undeniable 3-second hook immediately communicating target user and core workflow velocity.',
      'Position verified customer social proof metrics and logos before the first conversion hurdle.',
      'Offer both high-commitment (Book Demo) and zero-friction (Start Free / Interactive Sandbox) CTAs.',
    ],
    geoFocus: 'Structured for direct feature comparison, ROI justification, and tech-stack integration citations by LLMs.',
  },
  editorial: {
    id: 'editorial',
    name: 'Editorial / Thought Leadership & Blog',
    badge: 'EDITORIAL',
    archetype: 'Informational Authority & Semantic Hub',
    description: 'Crafted for deep dwell time, topical authority, and direct citation in AI Search and Answer Engines.',
    targetWordRange: [1400, 3200],
    targetReadability: 55,
    targetCtaRatio: 600,
    targetAltRatio: 85,
    targetTtfbMs: 450,
    directives: [
      'Embed a dedicated 40–60 word extractable definition snippet in the second paragraph for ChatGPT/Perplexity citation.',
      'Maintain an unbroken semantic heading hierarchy (H1 -> H2 -> H3) without skipping heading levels.',
      'Add FAQPage schema and standalone Q&A blocks addressing adjacent long-tail search intent.',
    ],
    geoFocus: 'Tailored for zero-click AI summaries, Perplexity sourcing, and Google AI Overview quote extraction.',
  },
  homepage: {
    id: 'homepage',
    name: 'Homepage / Brand Gateway',
    badge: 'HOMEPAGE',
    archetype: 'Universal Brand Gateway & Routing Hub',
    description: 'Primary entry point orchestrating audience segmentation, brand authority, and global sitewide signals.',
    targetWordRange: [700, 1800],
    targetReadability: 65,
    targetCtaRatio: 250,
    targetAltRatio: 95,
    targetTtfbMs: 300,
    directives: [
      'Clear hero positioning stating exact category leadership within 50 characters.',
      'Provide intuitive routing paths for both prospects, existing customers, and developers.',
      'Ensure Organization and WebSite schema are present with SearchAction potential.',
    ],
    geoFocus: 'Primary source for brand entity definition, company overview, and executive vision in AI knowledge bases.',
  },
  service: {
    id: 'service',
    name: 'Professional Services & Solutions',
    badge: 'SERVICES',
    archetype: 'Expertise Delivery & Consultation Path',
    description: 'Focuses on outcome articulation, methodology credibility, and inquiry qualification.',
    targetWordRange: [900, 2200],
    targetReadability: 58,
    targetCtaRatio: 350,
    targetAltRatio: 90,
    targetTtfbMs: 400,
    directives: [
      'Detail concrete client deliverables and business outcomes over vague capability lists.',
      'Incorporate case study vignettes with measurable percentage improvements.',
      'Include a direct consultation booking form with calendar integration to minimize booking drop-off.',
    ],
    geoFocus: 'Formatted to answer "Best service providers for [need]" and methodology differentiation inquiries.',
  },
  documentation: {
    id: 'documentation',
    name: 'Technical Documentation & Guides',
    badge: 'DOCS',
    archetype: 'Technical Reference & Implementation Architecture',
    description: 'Engineered for skimmability, code accuracy, and precise problem resolution.',
    targetWordRange: [500, 2500],
    targetReadability: 50,
    targetCtaRatio: 800,
    targetAltRatio: 80,
    targetTtfbMs: 350,
    directives: [
      'Use copyable code snippets with language syntax identifiers and version compatibility tags.',
      'Provide clear prerequisite checklists and troubleshooting tables for common error states.',
      'Ensure deep internal link connectivity to related SDK modules and API parameters.',
    ],
    geoFocus: 'Highest priority citation target for developer agents, Claude Code, and Copilot programming queries.',
  },
  company: {
    id: 'company',
    name: 'Company / About & Credibility',
    badge: 'COMPANY',
    archetype: 'Corporate Governance & Entity Verification',
    description: 'Establishes Google E-E-A-T credentials, executive transparency, and geographic presence.',
    targetWordRange: [500, 1500],
    targetReadability: 65,
    targetCtaRatio: 500,
    targetAltRatio: 90,
    targetTtfbMs: 400,
    directives: [
      'Link executive biographies to verified LinkedIn/Wikidata entities for Google Knowledge Graph ingestion.',
      'Publish verifiable physical address, NAP consistency, and corporate registration identifiers.',
      'Articulate mission statements and founder heritage to build institutional trust.',
    ],
    geoFocus: 'Authoritative ground truth for entity identity, executive leadership, and company origin.',
  },
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
  const [activeTab, setActiveTab] = useState<'visuals' | 'benchmark' | 'directives'>('visuals');
  const genreId = detectPageGenre(page.page_type, page.url, page.title);
  const genre = GENRE_CONFIGS[genreId];

  // Match GA4 per-page empirical telemetry
  const pagePath = (() => {
    try {
      const u = new URL(page.url);
      return u.pathname || '/';
    } catch {
      return page.url.replace(/^https?:\/\/[^/]+/, '') || '/';
    }
  })();

  const matchingGa4 = ga4LandingPages?.find(
    (lp) => lp.path === pagePath || lp.path === pagePath.replace(/\/$/, '') || (pagePath !== '/' && lp.path.includes(pagePath))
  );

  // 1. Calculate the 5 Vector Dimensions (0 - 100)
  const seoBase = report?.seo?.score != null ? Math.round(report.seo.score) : 72;
  const copyScore =
    report?.copywriting?.llm_status === 'ok' && report.copywriting.score != null
      ? Math.round(report.copywriting.score)
      : 70;

  // Semantic SEO dimension
  let semanticSeoScore = seoBase;
  const titleLen = (page.title || '').length;
  if (titleLen >= 50 && titleLen <= 65) semanticSeoScore = Math.min(100, semanticSeoScore + 6);
  if (page.h1 && page.h1.length === 1) semanticSeoScore = Math.min(100, semanticSeoScore + 4);

  // GEO & AI Quotability dimension
  const suggested = report?.copywriting?.suggested;
  let geoQuotability = 60;
  if (suggested?.geo_snippet) geoQuotability += 18;
  if (suggested?.faq_items && suggested.faq_items.length > 0) geoQuotability += 12;
  if (page.schema_types && page.schema_types.length > 0) geoQuotability += 10;
  geoQuotability = Math.min(100, geoQuotability);

  // Conversion & Action UX dimension
  const ctaCount = (page.ctas && page.ctas.length) || report?.ux?.cta_count || 0;
  let conversionVelocity = 55;
  if (suggested?.hook_3sec) conversionVelocity += 16;
  if (ctaCount >= 1) conversionVelocity += 14;
  if (ctaCount >= 3) conversionVelocity += 5;
  if (page.readability_score && page.readability_score >= 50) conversionVelocity += 10;
  conversionVelocity = Math.min(100, conversionVelocity);

  // Genre Intent Alignment
  let genreIntentScore = 65;
  const words = page.word_count || 0;
  if (words >= genre.targetWordRange[0] && words <= genre.targetWordRange[1]) {
    genreIntentScore += 18;
  } else if (words >= genre.targetWordRange[0] * 0.7) {
    genreIntentScore += 8;
  }
  if (genreId === 'ecommerce') {
    const hasProductSchema = (page.schema_types || []).some((s) => s.toLowerCase().includes('product'));
    if (hasProductSchema) genreIntentScore += 15;
  } else if (genreId === 'editorial') {
    if ((page.h2 || []).length >= 3) genreIntentScore += 15;
  } else if (genreId === 'saas' || genreId === 'homepage') {
    if (suggested?.hook_3sec) genreIntentScore += 15;
  }
  genreIntentScore = Math.min(100, Math.max(30, genreIntentScore));

  // Technical & Core Web Vitals Speed
  let techRobustness = 75;
  const ttfb = page.ttfb_ms || 280;
  if (ttfb < 300) techRobustness += 15;
  else if (ttfb < 600) techRobustness += 8;
  else if (ttfb > 1200) techRobustness -= 15;

  const totalImages = page.total_images || 0;
  const missingAlt = page.images_without_alt || 0;
  const altRatio = totalImages > 0 ? Math.round(((totalImages - missingAlt) / totalImages) * 100) : 100;
  if (altRatio >= 90) techRobustness += 10;
  techRobustness = Math.min(100, Math.max(35, techRobustness));

  // 2. Performance Radar Chart Geometry
  const radarDimensions = [
    { label: 'Semantic SEO', value: semanticSeoScore, benchmark: 88 },
    { label: 'GEO Quotability', value: geoQuotability, benchmark: 85 },
    { label: 'Conversion Velocity', value: conversionVelocity, benchmark: 82 },
    { label: 'Genre Intent Match', value: genreIntentScore, benchmark: 90 },
    { label: 'Speed & UX Rigor', value: techRobustness, benchmark: 85 },
  ];

  const radarCx = 135;
  const radarCy = 135;
  const radarRadius = 88;

  const getCoordinates = (value: number, index: number) => {
    const angle = (index * 2 * Math.PI) / 5 - Math.PI / 2;
    const r = (value / 100) * radarRadius;
    return {
      x: radarCx + r * Math.cos(angle),
      y: radarCy + r * Math.sin(angle),
    };
  };

  const pagePolygonPoints = radarDimensions
    .map((d, i) => {
      const { x, y } = getCoordinates(d.value, i);
      return `${x},${y}`;
    })
    .join(' ');

  const benchmarkPolygonPoints = radarDimensions
    .map((d, i) => {
      const { x, y } = getCoordinates(d.benchmark, i);
      return `${x},${y}`;
    })
    .join(' ');

  // Concentric radar web levels
  const radarWebRings = [0.25, 0.5, 0.75, 1.0].map((level) => {
    return Array.from({ length: 5 })
      .map((_, i) => {
        const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
        const r = level * radarRadius;
        return `${radarCx + r * Math.cos(angle)},${radarCy + r * Math.sin(angle)}`;
      })
      .join(' ');
  });

  // 3. User Attention & Scroll Retention Curve Points (4 Scroll Stages)
  // Milestone 0: 0% scroll (Hero Entrance) - 100%
  // Milestone 1: 30% scroll (Value Hook)
  const hookRetention = suggested?.hook_3sec ? 88 : 68;
  // Milestone 2: 65% scroll (Proof & Exploration)
  const proofRetention = page.readability_score >= 55 ? Math.round(hookRetention * 0.88) : Math.round(hookRetention * 0.72);
  // Milestone 3: 100% scroll (Action Threshold)
  const actionRetention = ctaCount > 0 ? Math.round(proofRetention * 0.85) : Math.round(proofRetention * 0.65);

  const attentionCurveData = [
    { stage: 'Hero Entrance', pct: '0%', retention: 100, note: 'Immediate visual payload' },
    { stage: 'Value Hook', pct: '30%', retention: hookRetention, note: suggested?.hook_3sec ? '3s Hook Activated' : 'Friction: Weak hook' },
    { stage: 'Deep Proof & Copy', pct: '65%', retention: proofRetention, note: `${words} words dwell window` },
    { stage: 'Conversion Horizon', pct: '100%', retention: actionRetention, note: ctaCount > 0 ? `${ctaCount} CTA anchors ready` : 'Zero action catalyst' },
  ];

  // SVG Curve generation (360x130 coordinate space)
  const cX = [35, 135, 235, 335];
  const cY = attentionCurveData.map((d) => 115 - (d.retention / 100) * 85);

  const bezierPath = `M ${cX[0]} ${cY[0]} C ${cX[0] + 45} ${cY[0]}, ${cX[1] - 45} ${cY[1]}, ${cX[1]} ${cY[1]} C ${cX[1] + 45} ${cY[1]}, ${cX[2] - 45} ${cY[2]}, ${cX[2]} ${cY[2]} C ${cX[2] + 45} ${cY[2]}, ${cX[3] - 45} ${cY[3]}, ${cX[3]} ${cY[3]}`;
  const areaPath = `${bezierPath} L ${cX[3]} 122 L ${cX[0]} 122 Z`;

  // 4. Benchmark Variance Metrics
  const ctaWords = ctaCount > 0 ? Math.round(words / ctaCount) : 0;
  const benchmarkDeltas = [
    {
      metric: 'Word Count Density',
      current: `${words.toLocaleString()} words`,
      target: `${genre.targetWordRange[0]}–${genre.targetWordRange[1]} words`,
      status: words >= genre.targetWordRange[0] && words <= genre.targetWordRange[1] ? 'optimal' : words < genre.targetWordRange[0] ? 'thin' : 'verbose',
      fillPct: Math.min(100, Math.round((words / genre.targetWordRange[1]) * 100)),
    },
    {
      metric: 'Readability Score',
      current: `${page.readability_score ? Math.round(page.readability_score) : 60}/100`,
      target: `Target ~${genre.targetReadability}`,
      status: (page.readability_score || 60) >= genre.targetReadability - 10 ? 'optimal' : 'warning',
      fillPct: Math.min(100, Math.round(page.readability_score || 60)),
    },
    {
      metric: 'CTA Spacing Frequency',
      current: ctaCount > 0 ? `1 per ${ctaWords} words` : '0 CTAs found',
      target: `1 per ~${genre.targetCtaRatio} words`,
      status: ctaCount > 0 && ctaWords <= genre.targetCtaRatio * 1.5 ? 'optimal' : 'critical',
      fillPct: ctaCount > 0 ? Math.min(100, Math.round((genre.targetCtaRatio / Math.max(ctaWords, 1)) * 100)) : 10,
    },
    {
      metric: 'Image Accessibility (Alt)',
      current: `${altRatio}% coverage`,
      target: `${genre.targetAltRatio}% benchmark`,
      status: altRatio >= genre.targetAltRatio ? 'optimal' : altRatio >= 70 ? 'warning' : 'critical',
      fillPct: altRatio,
    },
    {
      metric: 'Server Response (TTFB)',
      current: `${Math.round(ttfb)}ms`,
      target: `< ${genre.targetTtfbMs}ms budget`,
      status: ttfb <= genre.targetTtfbMs ? 'optimal' : ttfb <= genre.targetTtfbMs * 1.6 ? 'warning' : 'critical',
      fillPct: Math.max(10, Math.min(100, Math.round((genre.targetTtfbMs / Math.max(ttfb, 1)) * 100))),
    },
  ];

  return (
    <div className="rounded-xl border border-line bg-paper-50/70 p-5 space-y-6 shadow-xs">
      {/* Genre Archetype Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase bg-pine/15 text-pine dark:text-pine-light border border-pine/30">
              {genre.badge} ARCHETYPE
            </span>
            <span className="text-xs font-semibold text-ink-700">{genre.name}</span>
          </div>
          <p className="text-xs text-ink-500 leading-relaxed max-w-2xl">{genre.description}</p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-paper-100 rounded-lg border border-line text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('visuals')}
            className={`px-3 py-1 rounded font-medium transition cursor-pointer ${
              activeTab === 'visuals'
                ? 'bg-paper-50 text-ink shadow-xs border border-line font-bold'
                : 'text-ink-500 hover:text-ink'
            }`}
          >
            Graph Charts
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('benchmark')}
            className={`px-3 py-1 rounded font-medium transition cursor-pointer ${
              activeTab === 'benchmark'
                ? 'bg-paper-50 text-ink shadow-xs border border-line font-bold'
                : 'text-ink-500 hover:text-ink'
            }`}
          >
            Variance Bars
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('directives')}
            className={`px-3 py-1 rounded font-medium transition cursor-pointer ${
              activeTab === 'directives'
                ? 'bg-paper-50 text-ink shadow-xs border border-line font-bold'
                : 'text-ink-500 hover:text-ink'
            }`}
          >
            Strategic Blueprint
          </button>
        </div>
      </div>

      {/* Empirical GA4 Visitor Telemetry Overlay */}
      {matchingGa4 ? (
        <div className="p-3.5 rounded-lg border border-pine/30 bg-pine/5 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-pine animate-pulse" />
              <span className="text-xs font-bold text-pine dark:text-pine-light">
                Verified First-Party GA4 Telemetry
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-paper-100 text-ink-600 border border-line">
                Path: {matchingGa4.path}
              </span>
            </div>
            <span className="text-[10px] font-mono text-ink-500">Google Analytics 4 Data API</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">30d Sessions</span>
              <span className="font-mono font-bold text-ink text-sm">
                {matchingGa4.sessions.toLocaleString()}
              </span>
            </div>
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Bounce Rate</span>
              <span className="font-mono font-bold text-ink text-sm">{matchingGa4.bounce_rate}%</span>
            </div>
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Engagement Rate</span>
              <span className="font-mono font-bold text-good text-sm">
                {matchingGa4.engagement_rate != null ? `${matchingGa4.engagement_rate}%` : '—'}
              </span>
            </div>
            <div className="p-2 rounded bg-paper-50 border border-line">
              <span className="text-[10px] text-ink-500 block">Conversions</span>
              <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400 text-sm">
                {matchingGa4.conversions} ({matchingGa4.conversion_rate || 0}%)
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-2.5 rounded-lg border border-line bg-paper-100/50 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-500">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-ink-400" />
            <span>GA4 visitor telemetry unmeasured for this path. Displaying crawl-derived behavioral heuristics.</span>
          </div>
          <span className="font-mono text-[10px] text-ink-400">Zero-Fake Telemetry Protocol</span>
        </div>
      )}

      {/* 4 Genre KPI Score Rings */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg border border-line bg-paper-50 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-ink-500">
            <span>Genre Intent Match</span>
            <span className="font-mono font-bold text-ink">{genreIntentScore}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-paper-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-pine transition-all duration-500"
              style={{ width: `${genreIntentScore}%` }}
            />
          </div>
          <p className="text-[10px] text-ink-500 truncate">Aligned to {genre.badge}</p>
        </div>

        <div className="p-3 rounded-lg border border-line bg-paper-50 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-ink-500">
            <span>Dwell & Retention</span>
            <span className="font-mono font-bold text-ink">{hookRetention}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-paper-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-good transition-all duration-500"
              style={{ width: `${hookRetention}%` }}
            />
          </div>
          <p className="text-[10px] text-ink-500 truncate">Est. Above-Fold Grip</p>
        </div>

        <div className="p-3 rounded-lg border border-line bg-paper-50 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-ink-500">
            <span>Conversion Velocity</span>
            <span className="font-mono font-bold text-ink">{conversionVelocity}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-paper-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${conversionVelocity}%` }}
            />
          </div>
          <p className="text-[10px] text-ink-500 truncate">{ctaCount} Active CTAs</p>
        </div>

        <div className="p-3 rounded-lg border border-line bg-paper-50 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-ink-500">
            <span>GEO AI Quotability</span>
            <span className="font-mono font-bold text-ink">{geoQuotability}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-paper-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-purple-500 transition-all duration-500"
              style={{ width: `${geoQuotability}%` }}
            />
          </div>
          <p className="text-[10px] text-ink-500 truncate">Answer Engine Extracts</p>
        </div>
      </div>

      {/* Main Tab Content */}
      {activeTab === 'visuals' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Chart 1: Radar / Spider Graph Chart */}
          <div className="p-4 rounded-xl border border-line bg-paper-50 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-ink">5-Axis Performance Radar Chart</p>
                <p className="text-[11px] text-ink-500">Page Vector Polygon vs. {genre.name} Target</p>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono">
                <span className="inline-flex items-center gap-1 text-pine font-semibold">
                  <span className="w-2.5 h-2.5 rounded-full bg-pine/70 inline-block" /> Page
                </span>
                <span className="inline-flex items-center gap-1 text-ink-400">
                  <span className="w-2.5 h-0.5 border-t border-dashed border-ink-400 inline-block" /> Target
                </span>
              </div>
            </div>

            <div className="flex justify-center items-center py-2">
              <svg width="270" height="270" viewBox="0 0 270 270" className="overflow-visible select-none">
                <defs>
                  <linearGradient id={`radarGrad-${genreId}`} x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#0d9488" stopOpacity="0.45" />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity="0.25" />
                  </linearGradient>
                </defs>

                {/* Concentric Web Rings */}
                {radarWebRings.map((pts, idx) => (
                  <polygon
                    key={idx}
                    points={pts}
                    fill="none"
                    stroke="currentColor"
                    strokeDasharray="2,3"
                    className="text-line opacity-60"
                    strokeWidth="1"
                  />
                ))}

                {/* Axis Radial Lines */}
                {radarDimensions.map((_, i) => {
                  const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
                  const x = radarCx + radarRadius * Math.cos(angle);
                  const y = radarCy + radarRadius * Math.sin(angle);
                  return (
                    <line
                      key={i}
                      x1={radarCx}
                      y1={radarCy}
                      x2={x}
                      y2={y}
                      stroke="currentColor"
                      className="text-line opacity-50"
                      strokeWidth="1"
                    />
                  );
                })}

                {/* Benchmark Polygon (Dashed target) */}
                <polygon
                  points={benchmarkPolygonPoints}
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth="1.5"
                  strokeDasharray="3,3"
                />

                {/* Page Polygon (Vibrant fill) */}
                <polygon
                  points={pagePolygonPoints}
                  fill={`url(#radarGrad-${genreId})`}
                  stroke="#0d9488"
                  strokeWidth="2.5"
                />

                {/* Vertex Markers & Data Chips */}
                {radarDimensions.map((d, i) => {
                  const { x, y } = getCoordinates(d.value, i);
                  const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
                  const labelRadius = radarRadius + 22;
                  const lx = radarCx + labelRadius * Math.cos(angle);
                  const ly = radarCy + labelRadius * Math.sin(angle);

                  return (
                    <g key={i}>
                      <circle cx={x} cy={y} r="4" fill="#0d9488" stroke="#ffffff" strokeWidth="1.5" />
                      <text
                        x={lx}
                        y={ly}
                        textAnchor="middle"
                        dominantBaseline="central"
                        className="text-[9px] font-mono fill-current text-ink-700 font-semibold"
                      >
                        {d.value}%
                      </text>
                      <text
                        x={lx}
                        y={ly + (ly > radarCy ? 11 : -11)}
                        textAnchor="middle"
                        dominantBaseline="central"
                        className="text-[8px] fill-current text-ink-500"
                      >
                        {d.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          {/* Chart 2: Attention & Scroll Retention Curve Area Graph */}
          <div className="p-4 rounded-xl border border-line bg-paper-50 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-ink">Visitor Attention & Scroll Retention Curve</p>
                <p className="text-[11px] text-ink-500">Estimated Visitor Dwell Drop-off Along Scroll Journey</p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good border border-good/30 font-semibold">
                {actionRetention}% End Horizon
              </span>
            </div>

            <div className="py-2">
              <svg width="100%" height="150" viewBox="0 0 370 145" className="overflow-visible select-none">
                <defs>
                  <linearGradient id={`attentionGrad-${genreId}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
                  </linearGradient>
                </defs>

                {/* Horizontal Baseline Grids */}
                <line x1="20" y1="30" x2="350" y2="30" stroke="currentColor" className="text-line opacity-40" strokeDasharray="3,3" />
                <line x1="20" y1="72" x2="350" y2="72" stroke="currentColor" className="text-line opacity-40" strokeDasharray="3,3" />
                <line x1="20" y1="115" x2="350" y2="115" stroke="currentColor" className="text-line opacity-60" strokeWidth="1" />

                {/* Y-Axis Labeling */}
                <text x="12" y="32" className="text-[8px] font-mono fill-current text-ink-400" textAnchor="end">100%</text>
                <text x="12" y="74" className="text-[8px] font-mono fill-current text-ink-400" textAnchor="end">50%</text>
                <text x="12" y="117" className="text-[8px] font-mono fill-current text-ink-400" textAnchor="end">0%</text>

                {/* Smooth Area Gradient Fill */}
                <path d={areaPath} fill={`url(#attentionGrad-${genreId})`} />

                {/* Smooth Line Curve */}
                <path d={bezierPath} fill="none" stroke="#10b981" strokeWidth="2.5" />

                {/* Data Milestone Nodes */}
                {attentionCurveData.map((d, i) => (
                  <g key={i}>
                    <line x1={cX[i]} y1={cY[i]} x2={cX[i]} y2="115" stroke="currentColor" className="text-line opacity-30" strokeDasharray="2,2" />
                    <circle cx={cX[i]} cy={cY[i]} r="5" fill="#10b981" stroke="#ffffff" strokeWidth="2" />
                    <text x={cX[i]} y={cY[i] - 10} textAnchor="middle" className="text-[9px] font-mono font-bold fill-current text-ink">
                      {d.retention}%
                    </text>
                    <text x={cX[i]} y="130" textAnchor="middle" className="text-[9px] font-semibold fill-current text-ink-700">
                      {d.pct}
                    </text>
                    <text x={cX[i]} y="141" textAnchor="middle" className="text-[8px] fill-current text-ink-400">
                      {d.stage}
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            <div className="pt-2 border-t border-line text-[11px] text-ink-500 flex items-center justify-between">
              <span>Friction Bottleneck: {suggested?.hook_3sec ? 'Low Above-Fold Friction' : 'Missing 3-Sec Hook Drop-off'}</span>
              <span>Reading Pace: {Math.round(words / 220)} min dwell window</span>
            </div>
          </div>
        </div>
      )}

      {/* Variance Bar Charts */}
      {activeTab === 'benchmark' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-ink-500">
            <p>Empirical Crawl Value vs. Recommended {genre.name} Targets</p>
            <span className="font-mono text-[11px]">Category: {genre.archetype}</span>
          </div>

          <div className="space-y-3.5">
            {benchmarkDeltas.map((item) => (
              <div key={item.metric} className="p-3 bg-paper-50 rounded-lg border border-line space-y-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-ink">{item.metric}</span>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-ink-500 text-[11px]">{item.target}</span>
                    <span className="font-mono font-bold text-ink">{item.current}</span>
                    <span
                      className={`px-2 py-0.2 rounded text-[10px] font-mono font-semibold uppercase ${
                        item.status === 'optimal'
                          ? 'bg-good/10 text-good border border-good/30'
                          : item.status === 'warning'
                          ? 'bg-warn/10 text-warn border border-warn/30'
                          : 'bg-bad/10 text-bad border border-bad/30'
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>
                </div>

                <div className="w-full h-2 rounded-full bg-paper-200 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      item.status === 'optimal' ? 'bg-good' : item.status === 'warning' ? 'bg-warn' : 'bg-bad'
                    }`}
                    style={{ width: `${item.fillPct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategic Blueprint Directives */}
      {activeTab === 'directives' && (
        <div className="space-y-4 text-xs">
          <div className="p-4 rounded-lg bg-paper-100/70 border border-line space-y-2">
            <span className="label text-pine block font-bold">Answer Engine (GEO) Extraction Vector</span>
            <p className="text-ink-700 leading-relaxed text-xs">{genre.geoFocus}</p>
          </div>

          <div className="space-y-2.5">
            <span className="label block text-ink-700">Recommended Engineering & Copywriting Directives</span>
            <ul className="space-y-2">
              {genre.directives.map((dir, idx) => (
                <li key={idx} className="flex items-start gap-2.5 p-3 rounded bg-paper-50 border border-line">
                  <span className="w-5 h-5 rounded-full bg-pine/15 text-pine font-mono text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span className="text-ink-700 leading-relaxed">{dir}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
