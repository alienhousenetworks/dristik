import React from 'react';
import type { AuditTierId, AuditTierSpec } from '../types';

export const DEFAULT_AUDIT_TIERS: AuditTierSpec[] = [
  {
    id: 'basic',
    rank: 1,
    name: 'Basic Scan',
    tagline: 'Fast deterministic technical SEO & crawl hygiene — zero LLM overhead.',
    badge: 'Essential Crawl',
    popular: false,
    base_credits: 5,
    credits_per_page: 1,
    sample_10_pages_credits: 15,
    sample_10_pages_inr: 150,
    sample_10_pages_usd: 1.8,
    features: {
      max_pages: 25,
      enable_ai_verifier: false,
      specialist_limit: 0,
      aeo_question_count: 0,
      enable_live_geo_probes: false,
      enable_ga4_gsc: false,
      enable_psi_crux: false,
      copywriting_page_cap: 0,
      remediation_mode: 'none',
      critic_mode: 'none',
      enable_competitor_bakeoff: false,
      report_documents_mode: 'none',
      report_sizing_mode: 'none',
      white_label_enabled: false,
      ai_depth_mode: 'deterministic_only',
      enable_patch_pack_download: false,
      enable_pptx_download: false,
    },
    included_highlights: ['18 Python technical SEO & crawl analyzers', 'Dashboard & JSON export'],
    locked_highlights: ['No AI specialists, AEO/GEO, connectors, or PDF/PPT suite'],
  },
  {
    id: 'starter',
    rank: 2,
    name: 'Starter AI',
    tagline: 'Core fast-tier AI diagnostics for SEO & CRO plus 1 Executive PDF.',
    badge: 'Small Sites',
    popular: false,
    base_credits: 15,
    credits_per_page: 2,
    sample_10_pages_credits: 35,
    sample_10_pages_inr: 350,
    sample_10_pages_usd: 4.2,
    features: {
      max_pages: 50,
      enable_ai_verifier: false,
      specialist_limit: 10,
      aeo_question_count: 0,
      enable_live_geo_probes: false,
      enable_ga4_gsc: false,
      enable_psi_crux: false,
      copywriting_page_cap: 0,
      remediation_mode: 'deterministic',
      critic_mode: 'none',
      enable_competitor_bakeoff: false,
      report_documents_mode: 'exec_pdf_template',
      report_sizing_mode: 'standard',
      white_label_enabled: false,
      ai_depth_mode: 'fast_tier',
      enable_patch_pack_download: false,
      enable_pptx_download: false,
    },
    included_highlights: ['10 core SEO/CRO AI specialists', '1 Executive PDF & roadmap'],
    locked_highlights: ['No AEO RAG, GA4/GSC, AI copywriting, or PPT decks'],
  },
  {
    id: 'growth',
    rank: 3,
    name: 'Growth Intelligence',
    tagline: 'GA4 & GSC grounded audit with 20 AI specialists, 25-Q AEO & Exec deck.',
    badge: 'Growing Teams',
    popular: false,
    base_credits: 30,
    credits_per_page: 4,
    sample_10_pages_credits: 70,
    sample_10_pages_inr: 700,
    sample_10_pages_usd: 8.4,
    features: {
      max_pages: 100,
      enable_ai_verifier: true,
      specialist_limit: 20,
      aeo_question_count: 25,
      enable_live_geo_probes: false,
      enable_ga4_gsc: true,
      enable_psi_crux: false,
      copywriting_page_cap: 5,
      remediation_mode: 'deterministic',
      critic_mode: 'sampled',
      enable_competitor_bakeoff: false,
      report_documents_mode: 'exec_pair_ai',
      report_sizing_mode: 'standard',
      white_label_enabled: false,
      ai_depth_mode: 'tiered_frontier',
      enable_patch_pack_download: false,
      enable_pptx_download: true,
    },
    included_highlights: ['GA4 + GSC connectors', '20 AI specialists + 25-Q AEO RAG', 'AI Exec PDF + PPTX'],
    locked_highlights: ['No 100-Q AEO, Patch Pack ZIP, or full 5+5 suite'],
  },
  {
    id: 'premium',
    rank: 4,
    name: 'Premium Full-Stack',
    tagline: 'All 35 Frontier AI specialists, 100-Q AEO, all connectors & 5 PDF + 5 PPT.',
    badge: 'Flagship',
    popular: true,
    base_credits: 50,
    credits_per_page: 6,
    sample_10_pages_credits: 110,
    sample_10_pages_inr: 1100,
    sample_10_pages_usd: 13.2,
    features: {
      max_pages: 200,
      enable_ai_verifier: true,
      specialist_limit: 35,
      aeo_question_count: 100,
      enable_live_geo_probes: false,
      enable_ga4_gsc: true,
      enable_psi_crux: true,
      copywriting_page_cap: 40,
      remediation_mode: 'ai_patch_pack',
      critic_mode: 'full',
      enable_competitor_bakeoff: false,
      report_documents_mode: 'full_5_5_standard',
      report_sizing_mode: 'standard',
      white_label_enabled: false,
      ai_depth_mode: 'tiered_frontier',
      enable_patch_pack_download: true,
      enable_pptx_download: true,
    },
    included_highlights: ['All 35 AI specialists + 100% Critic', '100-Q AEO + GA4/GSC/CrUX', '5 AI PDFs + 5 PPTXs + Patch Pack'],
    locked_highlights: ['No Live GEO web probes or 3-Competitor Bake-Off'],
  },
  {
    id: 'enterprise',
    rank: 5,
    name: 'Enterprise Command',
    tagline: 'frontier_all reasoning, Live GEO citations, 3-Competitor Bake-Off & White-Label.',
    badge: 'Enterprise',
    popular: false,
    base_credits: 90,
    credits_per_page: 10,
    sample_10_pages_credits: 190,
    sample_10_pages_inr: 1900,
    sample_10_pages_usd: 22.8,
    features: {
      max_pages: 500,
      enable_ai_verifier: true,
      specialist_limit: 35,
      aeo_question_count: 100,
      enable_live_geo_probes: true,
      enable_ga4_gsc: true,
      enable_psi_crux: true,
      copywriting_page_cap: -1,
      remediation_mode: 'ai_pr_sync',
      critic_mode: 'cross_provider',
      enable_competitor_bakeoff: true,
      report_documents_mode: 'full_5_5_deep',
      report_sizing_mode: 'deep',
      white_label_enabled: true,
      ai_depth_mode: 'frontier_all',
      enable_patch_pack_download: true,
      enable_pptx_download: true,
    },
    included_highlights: ['frontier_all + Cross-Provider Critic', 'Live GEO Probes + 3-Competitor Bake-Off', 'Deep 5+5 White-Label + PR Sync'],
    locked_highlights: [],
  },
];

export const SITE_TYPES = [
  { value: '', label: 'Detect automatically' },
  { value: 'business_corporate', label: 'Business / Corporate' },
  { value: 'saas', label: 'SaaS' },
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'marketplace', label: 'Marketplace' },
  { value: 'agency_services', label: 'Agency / Services' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'publisher_media', label: 'Publisher / Media' },
  { value: 'blog', label: 'Blog' },
  { value: 'community', label: 'Community' },
  { value: 'non_profit', label: 'Non-profit' },
  { value: 'educational', label: 'Educational' },
  { value: 'government', label: 'Government' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'financial', label: 'Financial' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'travel_hospitality', label: 'Travel / Hospitality' },
  { value: 'local_business', label: 'Local Business' },
  { value: 'other', label: 'Other' },
];

export interface PillarOption {
  key: string;
  name: string;
  description: string;
  tag: string;
  colorClass: string;
}

export const PILLARS_LIST: PillarOption[] = [
  {
    key: 'seo',
    name: 'SEO',
    description: 'Crawling, page content, metadata, links and technical issues',
    tag: 'Search Engine Optimization',
    colorClass: 'text-teal-800 bg-teal-50 border-teal-200 dark:text-teal-200 dark:bg-teal-950/40 dark:border-teal-800',
  },
  {
    key: 'geo',
    name: 'GEO',
    description: 'How clearly content explains entities and supports AI discovery',
    tag: 'Generative Engine Optimization',
    colorClass: 'text-teal-800 bg-teal-50 border-teal-200 dark:text-teal-200 dark:bg-teal-950/40 dark:border-teal-800',
  },
  {
    key: 'aeo',
    name: 'AEO',
    description: 'Answer quality, question coverage and structured data',
    tag: 'Answer Engine Optimization',
    colorClass: 'text-teal-800 bg-teal-50 border-teal-200 dark:text-teal-200 dark:bg-teal-950/40 dark:border-teal-800',
  },
  {
    key: 'cro',
    name: 'CRO',
    description: 'Calls to action, forms, trust signals and conversion friction',
    tag: 'Conversion Rate Optimization',
    colorClass: 'text-teal-800 bg-teal-50 border-teal-200 dark:text-teal-200 dark:bg-teal-950/40 dark:border-teal-800',
  },
];

interface AuditFormProps {
  url: string;
  maxPages: number;
  auditTier?: AuditTierId;
  tiers?: AuditTierSpec[];
  creditBalance?: number | null;
  enforceCredits?: boolean;
  adminBypass?: boolean;
  onAuditTierChange?: (tier: AuditTierId) => void;
  onBuyCredits?: () => void;
  siteType: string;
  declaredNotes?: string;
  targetPillars?: string[];
  onTargetPillarsChange?: (pillars: string[]) => void;
  isLoading: boolean;
  error: string | null;
  onUrlChange: (value: string) => void;
  onMaxPagesChange: (value: number) => void;
  onSiteTypeChange: (value: string) => void;
  onDeclaredNotesChange?: (value: string) => void;
  onSubmit: () => void;
}

export function AuditForm({
  url,
  maxPages,
  auditTier = 'basic',
  tiers = DEFAULT_AUDIT_TIERS,
  creditBalance = null,
  enforceCredits = true,
  adminBypass = false,
  onAuditTierChange,
  onBuyCredits,
  siteType,
  declaredNotes = '',
  targetPillars = ['seo', 'geo', 'aeo', 'cro'],
  onTargetPillarsChange,
  isLoading,
  error,
  onUrlChange,
  onMaxPagesChange,
  onSiteTypeChange,
  onDeclaredNotesChange,
  onSubmit,
}: AuditFormProps) {
  const allPillarsKeys = ['seo', 'geo', 'aeo', 'cro'];
  const isAllSelected = targetPillars.length === allPillarsKeys.length;
  const activeTier = tiers.find((t) => t.id === auditTier) || tiers[0] || DEFAULT_AUDIT_TIERS[0];
  const requiredCredits = activeTier.base_credits + maxPages * activeTier.credits_per_page;
  const estimatedInr = requiredCredits * 10;
  const insufficientCredits =
    enforceCredits && !adminBypass && creditBalance !== null && creditBalance < requiredCredits;
  const pageOptions = [3, 5, 10, 25, 50, 100].filter((n) => n <= activeTier.features.max_pages);

  const handleTogglePillar = (key: string) => {
    if (!onTargetPillarsChange) return;
    if (targetPillars.includes(key)) {
      if (targetPillars.length === 1) return; // Keep at least one pillar active
      onTargetPillarsChange(targetPillars.filter((p) => p !== key));
    } else {
      onTargetPillarsChange([...targetPillars, key]);
    }
  };

  const handleSelectAll = () => {
    if (!onTargetPillarsChange) return;
    onTargetPillarsChange(allPillarsKeys);
  };
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex flex-col lg:flex-row lg:items-end gap-3">
        <label className="flex-1 min-w-0">
          <span className="label block mb-1.5">Website URL</span>
          <input
            type="text"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="https://example.com"
            disabled={isLoading}
            autoComplete="url"
            spellCheck={false}
            className="field"
          />
        </label>

        <label className="lg:w-52">
          <span className="label block mb-1.5">Site type</span>
          <select
            value={siteType}
            onChange={(e) => onSiteTypeChange(e.target.value)}
            disabled={isLoading}
            className="field"
          >
            {SITE_TYPES.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>
        </label>

        <label className="lg:w-28">
          <span className="label block mb-1.5">Pages to inspect</span>
          <select
            value={maxPages}
            onChange={(e) => onMaxPagesChange(Number(e.target.value))}
            disabled={isLoading}
            className="field"
          >
            {pageOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <button
          type="submit"
          disabled={isLoading || insufficientCredits}
          className="btn-primary px-5 py-2.5 disabled:opacity-50 lg:mb-px"
        >
          {isLoading ? 'Running…' : `Run (${requiredCredits} cr)`}
        </button>
      </div>

      {/* 5-Tier Audit Depth & Credit Cost Selector */}
      <div className="pt-2 border-t border-line/50 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="label text-xs font-semibold uppercase tracking-wider text-ink-700">
              Audit Tier &amp; Depth
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
              {maxPages} pages · {requiredCredits} credits (~₹{estimatedInr.toLocaleString('en-IN')})
            </span>
          </div>
          <div className="flex items-center gap-2">
            {creditBalance !== null && (
              <span
                className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border font-semibold ${
                  insufficientCredits
                    ? 'bg-bad/10 text-bad border-bad/30'
                    : 'bg-good/10 text-good border-good/30'
                }`}
              >
                Wallet: {creditBalance.toLocaleString('en-IN')} cr{adminBypass ? ' (Admin)' : ''}
              </span>
            )}
            {onBuyCredits && (
              <button
                type="button"
                onClick={onBuyCredits}
                className="text-xs font-semibold text-pine hover:underline cursor-pointer"
              >
                + Buy Credits
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
          {tiers.map((t) => {
            const selected = t.id === activeTier.id;
            const tierCredits = t.base_credits + maxPages * t.credits_per_page;
            const tierInr = tierCredits * 10;
            return (
              <button
                key={t.id}
                type="button"
                disabled={isLoading}
                onClick={() => {
                  onAuditTierChange?.(t.id);
                  if (maxPages > t.features.max_pages) {
                    onMaxPagesChange(t.features.max_pages);
                  }
                }}
                className={`p-3 rounded-2xl border text-left transition-all duration-150 cursor-pointer flex flex-col justify-between ${
                  selected
                    ? 'bg-paper-50 border-pine shadow-sm ring-2 ring-pine/20'
                    : 'bg-paper-100/60 border-line/70 hover:bg-paper-100'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-sans font-semibold text-xs text-ink">{t.name}</span>
                    {t.popular && (
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-pine text-white">
                        PRO
                      </span>
                    )}
                  </div>
                  <div className="flex items-baseline gap-1.5 mb-1.5">
                    <span className="text-sm font-mono font-bold text-ink">{tierCredits} cr</span>
                    <span className="text-[10px] font-mono text-ink-500">₹{tierInr.toLocaleString('en-IN')}</span>
                  </div>
                  <p className="text-[10px] text-ink-500 leading-snug mb-2">
                    {t.included_highlights[0]}
                  </p>
                </div>
                <div className="text-[9px] font-mono text-ink-400 border-t border-line/40 pt-1.5">
                  {t.base_credits} base + {t.credits_per_page}/pg · max {t.features.max_pages}p
                </div>
              </button>
            );
          })}
        </div>

        {insufficientCredits && creditBalance !== null && (
          <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-xl bg-bad/10 border border-bad/30 text-xs text-bad">
            <span>
              <strong>Insufficient credits:</strong> {activeTier.name} ({maxPages} pages) requires{' '}
              <strong>{requiredCredits} cr</strong>, but your wallet has <strong>{creditBalance} cr</strong>{' '}
              (need {requiredCredits - creditBalance} more).
            </span>
            {onBuyCredits && (
              <button
                type="button"
                onClick={onBuyCredits}
                className="px-2.5 py-1 rounded-lg bg-bad text-white font-semibold text-[11px] cursor-pointer"
              >
                Top Up Credits
              </button>
            )}
          </div>
        )}
      </div>

      {siteType === 'other' && onDeclaredNotesChange && (
        <label className="block">
          <span className="label block mb-1.5">Describe the business</span>
          <input
            type="text"
            value={declaredNotes}
            onChange={(e) => onDeclaredNotesChange(e.target.value)}
            placeholder="e.g. B2B wholesale marketplace"
            disabled={isLoading}
            className="field"
          />
        </label>
      )}

      {/* 4 Core Intelligence Pillars Selection */}
      <div className="pt-2 border-t border-line/50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="label text-xs font-semibold uppercase tracking-wider text-ink-700">Choose what to review</span>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
              isAllSelected
                ? 'bg-good/10 text-good border border-good/30'
                : 'bg-paper-200 text-ink-700 border border-line'
            }`}>
              {isAllSelected ? 'Full 4-Pillar Audit' : `Selective Run: ${targetPillars.length} / 4 Active`}
            </span>
          </div>
          {!isAllSelected && onTargetPillarsChange && (
            <button
              type="button"
              onClick={handleSelectAll}
              disabled={isLoading}
              className="text-xs text-ink-500 hover:text-ink underline cursor-pointer disabled:opacity-50"
            >
              Select All Pillars
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {PILLARS_LIST.map((pillar) => {
            const isSelected = targetPillars.includes(pillar.key);
            return (
              <button
                key={pillar.key}
                type="button"
                onClick={() => handleTogglePillar(pillar.key)}
                disabled={isLoading}
                className={`p-3 rounded-2xl border text-left transition-all duration-200 cursor-pointer select-none flex flex-col justify-between ${
                  isSelected
                    ? 'bg-paper-50 border-pine/80 shadow-sm ring-2 ring-pine/20'
                    : 'bg-paper-100/60 border-line/70 opacity-60 hover:opacity-90 hover:bg-paper-100'
                }`}
              >
                <div className="flex items-center justify-between gap-1 mb-1.5">
                  <span className="font-sans font-semibold text-xs text-ink flex items-center gap-1.5">
                    <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] transition-colors ${
                      isSelected ? 'bg-pine text-white font-bold' : 'border border-line bg-paper-200 text-transparent'
                    }`}>
                      ✓
                    </span>
                    {pillar.name}
                  </span>
                  <span className={`text-[9px] font-mono font-semibold px-2 py-0.5 rounded-full border ${pillar.colorClass}`}>
                    {pillar.key.toUpperCase()}
                  </span>
                </div>
                <p className="text-[10px] text-ink-500 line-clamp-1 leading-tight">{pillar.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      <p className="text-xs text-ink-400">
        Site type is treated as context, not truth. Dristik verifies the live pages independently.
      </p>

      {error && (
        <p className="text-sm text-bad" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
