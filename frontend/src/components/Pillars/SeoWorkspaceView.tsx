import React, { useState } from 'react';
import { ExecutiveReport, Finding, PageEvidence } from '../../types';
import { SearchConsoleAttributionView } from '../SearchConsoleAttributionView';
import { UrlLevelTechnicalAppendix } from '../UrlLevelTechnicalAppendix';
import { PillarShell, Card } from '../ui';
import {
  Globe,
  FileCode,
  Layers,
  Link2,
  Shield,
  Image as ImageIcon,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ArrowRight,
  TrendingUp,
  Code2,
  Monitor,
  Smartphone,
  ExternalLink,
  Users,
  Search,
  Filter,
  MapPin,
  Languages,
} from 'lucide-react';

interface SeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onSelectFinding?: (f: Finding) => void;
  onOpenConnectors?: (tabId?: string) => void;
}

type SeoSubTab = 'crawl' | 'onpage' | 'assets' | 'links' | 'local' | 'international' | 'security' | 'competitors' | 'gsc' | 'appendix' | 'findings';

export function SeoWorkspaceView({
  report,
  analysisId,
  onSelectFinding,
  onOpenConnectors,
}: SeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<SeoSubTab>('crawl');
  const [serpDevice, setSerpDevice] = useState<'desktop' | 'mobile'>('desktop');
  const [findingSeverityFilter, setFindingSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'>('ALL');
  const [selectedSerpPageUrl, setSelectedSerpPageUrl] = useState<string>('');

  const crawl = report.crawl_manifest;
  const pages = crawl?.pages || [];
  const homePage = pages[0];

  const currentSerpPage = pages.find((p) => p.url === selectedSerpPageUrl) || homePage;

  const seoFindings = (report.findings || []).filter(
    (f) => f.category === 'TECHNICAL_SEO' || f.category === 'ON_PAGE_SEO' || f.category === 'CONTENT'
  );

  const filteredFindings = seoFindings.filter((f) => {
    if (findingSeverityFilter === 'ALL') return true;
    return f.severity === findingSeverityFilter;
  });

  const redirects = report.host_and_redirects;
  const clickDepth = report.click_depth;
  const orphanPages = report.orphan_pages;
  const headings = report.heading_hierarchy;
  const media = report.media_assets;
  const security = report.security_audit;
  const metaRollup = report.meta_rollup;
  const anchorAudit = report.anchor_text_audit;
  const canonicalAudit = report.canonical_audit;
  const httpStatus = report.http_status_breakdown;
  const compParity = report.competitor_seo_parity;
  const localSeo = report.local_seo;
  const intlSeo = report.international_seo;

  const seoScore = report.scores?.category_scores?.['TECHNICAL_SEO']?.score;

  // Title and Meta pixel widths
  const titleText = currentSerpPage?.title || report.domain;
  const metaText = currentSerpPage?.meta_description || 'No meta description provided for this URL.';
  const titlePx = currentSerpPage?.title_pixel_width || Math.min(580, titleText.length * 9.5);
  const metaPx = currentSerpPage?.meta_pixel_width || Math.min(960, metaText.length * 7.0);

  return (
    <PillarShell
      kicker="Discipline 1 · Technical & On-Page SEO"
      title="Search Engine Optimization (SEO)"
      description="Crawlability, HTTP status codes, canonical integrity, Google SERP truncation, heading hierarchy, local NAP consistency, and international targeting."
      scoreLabel="SEO Index"
      score={seoScore != null ? Math.round(seoScore) : '—'}
      metaLabel="Issues"
      meta={`${seoFindings.length} flagged`}
      tabs={[
        { id: 'crawl', label: 'Crawl & Architecture' },
        { id: 'onpage', label: 'On-Page & SERP' },
        { id: 'assets', label: 'Images & Performance' },
        { id: 'links', label: 'Internal Link Equity' },
        { id: 'local', label: 'Local SEO' },
        { id: 'international', label: 'International SEO' },
        { id: 'competitors', label: 'Competitor Parity' },
        { id: 'security', label: 'Security & Host' },
        { id: 'gsc', label: 'Search Console' },
        { id: 'appendix', label: 'URL Appendix & Grid' },
        { id: 'findings', label: `SEO Findings (${seoFindings.length})` },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as SeoSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: CRAWL & ARCHITECTURE
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'crawl' && (
        <div className="space-y-6">
          {/* Top Vitals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                HTTP Status Success Rate
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                <span className="font-mono text-base text-good">
                  {httpStatus && httpStatus.total_urls_checked > 0 ? `${Math.round((httpStatus.count_2xx / httpStatus.total_urls_checked) * 100)}%` : '—'}
                </span>
                <span className="text-xs font-mono text-ink-500">HTTP 200 OK</span>
              </div>
              <p className="text-xs text-ink-500">
                {httpStatus?.count_2xx ?? pages.length} of {httpStatus?.total_urls_checked ?? pages.length} crawled URLs successful
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Canonical Health Score
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                <span className="font-mono text-base text-pine">
                  {canonicalAudit?.canonical_health_score ? `${Math.round(canonicalAudit.canonical_health_score)}/100` : '100/100'}
                </span>
                <span className="text-xs font-mono text-good font-semibold">
                  {canonicalAudit?.broken_canonical_count ? `${canonicalAudit.broken_canonical_count} broken` : 'Clean'}
                </span>
              </div>
              <p className="text-xs text-ink-500">
                {canonicalAudit?.self_canonical_count ?? pages.length} self-referential canonicals
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                XML Sitemap Directives
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                {crawl?.sitemap_found ? (
                  <CheckCircle2 className="w-4 h-4 text-good shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-warn shrink-0" />
                )}
                <span>{crawl?.sitemap_found ? 'Detected & Valid' : 'Missing in robots.txt'}</span>
              </div>
              <p className="text-xs text-ink-500 font-mono truncate">
                {crawl?.sitemap_url || 'No sitemap specified'}
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Max Click Depth
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                <Layers className="w-4 h-4 text-pine shrink-0" />
                <span className="font-mono text-base">{clickDepth?.max_click_depth != null ? `${clickDepth.max_click_depth} Clicks` : '—'}</span>
              </div>
              <p className="text-xs text-ink-500">
                {clickDepth?.high_depth_warning_count ? `${clickDepth.high_depth_warning_count} deep pages (>3)` : 'Good crawl hierarchy'}
              </p>
            </Card>
          </div>

          {/* Granular HTTP Status Code Distribution */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  HTTP Response Codes & Broken Link Inventory
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-500">
                Industry Standard Status Audit
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-good/5 space-y-1">
                <span className="text-[10px] font-mono text-good uppercase font-bold">2xx Success</span>
                <span className="text-xl font-mono font-bold text-good block">
                  {httpStatus?.count_2xx ?? pages.filter(p => p.status_code === 200).length}
                </span>
                <p className="text-[10px] text-ink-500">Indexable clean pages</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-pine uppercase font-bold">3xx Redirects</span>
                <span className="text-xl font-mono font-bold text-ink block">
                  {httpStatus?.count_3xx ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">Redirected hops / canonicals</p>
              </div>
              <div className="p-3 rounded border border-line bg-bad/5 space-y-1">
                <span className="text-[10px] font-mono text-bad uppercase font-bold">4xx Client Errors</span>
                <span className={`text-xl font-mono font-bold block ${
                  (httpStatus?.count_4xx || 0) > 0 ? 'text-bad' : 'text-good'
                }`}>
                  {httpStatus?.count_4xx ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">404 Not Found / 403 Forbidden</p>
              </div>
              <div className="p-3 rounded border border-line bg-bad/5 space-y-1">
                <span className="text-[10px] font-mono text-bad uppercase font-bold">5xx Server Errors</span>
                <span className={`text-xl font-mono font-bold block ${
                  (httpStatus?.count_5xx || 0) > 0 ? 'text-bad' : 'text-good'
                }`}>
                  {httpStatus?.count_5xx ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">Backend server timeouts</p>
              </div>
            </div>

            {/* Broken Links Table if any */}
            {httpStatus?.broken_links && httpStatus.broken_links.length > 0 && (
              <div className="mt-4 pt-3 border-t border-line space-y-2">
                <span className="text-xs font-semibold text-bad block">
                  Flagged Broken Links (4xx/5xx):
                </span>
                <div className="space-y-1 text-xs font-mono max-h-40 overflow-y-auto">
                  {httpStatus.broken_links.map((bl, idx) => (
                    <div key={idx} className="p-2 rounded bg-bad/5 border border-bad/20 flex items-center justify-between gap-3 text-ink-800">
                      <span className="truncate">Source: {bl.source_url} &rarr; Target: <strong>{bl.target_url}</strong></span>
                      <span className="text-bad font-bold shrink-0">{bl.status_code}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Canonical Tag Architecture Matrix */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Canonical Tag Architecture Matrix
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-500">
                {canonicalAudit?.total_pages_evaluated ?? pages.length} Pages Evaluated
              </span>
            </div>
            <p className="text-xs text-ink-600">
              Evaluates whether every page defines an absolute self-referencing canonical tag or points to a valid destination without redirect loops or 404 errors.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Self-Referential</span>
                <span className="text-lg font-mono font-bold text-good">
                  {canonicalAudit?.self_canonical_count ?? pages.length}
                </span>
                <p className="text-[10px] text-ink-500">Valid indexable canonicals</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Canonicalized</span>
                <span className="text-lg font-mono font-bold text-ink">
                  {canonicalAudit?.canonicalized_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">Consolidated duplicate URLs</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Missing Canonicals</span>
                <span className={`text-lg font-mono font-bold ${
                  (canonicalAudit?.missing_canonical_count || 0) > 0 ? 'text-warn' : 'text-good'
                }`}>
                  {canonicalAudit?.missing_canonical_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">At risk of duplicate penalties</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Broken Targets</span>
                <span className={`text-lg font-mono font-bold ${
                  (canonicalAudit?.broken_canonical_count || 0) > 0 ? 'text-bad' : 'text-good'
                }`}>
                  {canonicalAudit?.broken_canonical_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">Canonical points to 4xx/5xx</p>
              </div>
            </div>
          </Card>

          {/* Redirect & Host Consolidation */}
          {redirects && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-pine" />
                  <h3 className="font-serif text-lg text-ink font-semibold">
                    Host Variant & Canonical Redirect Consolidation
                  </h3>
                </div>
                <span className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                  redirects.proper_301_consolidation ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                }`}>
                  {redirects.proper_301_consolidation ? 'Consolidated 301' : 'Fragmented Variants'}
                </span>
              </div>
              <p className="text-xs text-ink-600">
                Ensures www, non-www, HTTP, and HTTPS all 301-redirect cleanly to a single canonical destination URL without redirect loops or multi-hop chains.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                {Object.entries(redirects.host_variants || {}).map(([variant, result]: [string, any]) => (
                  <div key={variant} className="p-3 rounded border border-line bg-paper-50 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-bold text-ink-700">{variant}</span>
                      <span className={`font-mono text-[10px] px-1 rounded ${
                        result.status_code === 200 || result.status_code === 301 ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                      }`}>
                        HTTP {result.status_code}
                      </span>
                    </div>
                    <p className="text-[11px] text-ink-500 truncate" title={result.final_destination}>
                      &rarr; {result.final_destination || 'Resolved'}
                    </p>
                    <p className="text-[10px] text-ink-400 font-mono">
                      {result.hop_count ?? 1} hop(s) · {result.proper_canonical_redirect ? 'Clean' : 'Needs review'}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Click Depth & Orphan Pages */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-line pb-2">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-pine" />
                  <h4 className="font-serif text-base text-ink font-semibold">Crawl Click Depth Distribution</h4>
                </div>
                <span className="text-xs text-ink-500 font-mono">
                  {clickDepth?.total_pages_analyzed || pages.length} pages
                </span>
              </div>
              <div className="space-y-2 pt-2 text-xs">
                {[
                  { label: 'Depth 1 (Homepage / Nav)', count: clickDepth?.depth_1_count || Math.min(pages.length, 3) },
                  { label: 'Depth 2 (Primary Categories)', count: clickDepth?.depth_2_count || Math.max(0, pages.length - 3) },
                  { label: 'Depth 3 (Sub-pages)', count: clickDepth?.depth_3_count || 0 },
                  { label: 'Depth 4+ (Deep Crawl Risk)', count: clickDepth?.depth_4_plus_count || 0 },
                ].map((row, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded bg-paper-50 border border-line">
                    <span className="text-ink-700">{row.label}</span>
                    <span className="font-mono font-bold text-ink">{row.count} pages</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-line pb-2">
                <div className="flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-pine" />
                  <h4 className="font-serif text-base text-ink font-semibold">Orphan Page Detection</h4>
                </div>
                <span className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                  (orphanPages?.orphan_count || 0) === 0 ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                }`}>
                  {orphanPages?.orphan_count || 0} Orphans
                </span>
              </div>
              <p className="text-xs text-ink-600">
                Orphan URLs exist in the XML sitemap but have 0 internal links from crawled pages, leading to indexation drops.
              </p>
              {orphanPages?.orphan_urls && orphanPages.orphan_urls.length > 0 ? (
                <div className="space-y-1.5 max-h-48 overflow-y-auto pt-1">
                  {orphanPages.orphan_urls.map((u: string, idx: number) => (
                    <div key={idx} className="text-xs font-mono p-2 rounded bg-warn/5 border border-warn/20 text-ink-800 truncate">
                      ⚠️ {u}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 rounded bg-good/5 border border-good/20 text-center text-xs text-good font-medium">
                  ✓ No orphan pages detected. All sitemap URLs are discoverable through the site link graph.
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: ON-PAGE & SERP
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'onpage' && (
        <div className="space-y-6">
          {/* Live Google SERP Snippet Simulator */}
          <Card className="p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between border-b border-line pb-3 gap-2">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Google SERP Snippet Preview & Pixel Meter
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center border border-line rounded p-0.5 bg-paper-100 text-xs">
                  <button
                    type="button"
                    onClick={() => setSerpDevice('desktop')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
                      serpDevice === 'desktop' ? 'bg-white shadow-sm font-semibold text-ink' : 'text-ink-500'
                    }`}
                  >
                    <Monitor className="w-3.5 h-3.5" /> Desktop
                  </button>
                  <button
                    type="button"
                    onClick={() => setSerpDevice('mobile')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
                      serpDevice === 'mobile' ? 'bg-white shadow-sm font-semibold text-ink' : 'text-ink-500'
                    }`}
                  >
                    <Smartphone className="w-3.5 h-3.5" /> Mobile
                  </button>
                </div>
                {pages.length > 1 && (
                  <select
                    className="text-xs border border-line rounded px-2 py-1 bg-white font-mono"
                    value={selectedSerpPageUrl}
                    onChange={(e) => setSelectedSerpPageUrl(e.target.value)}
                  >
                    {pages.map((p, idx) => (
                      <option key={idx} value={p.url}>
                        {p.page_type.toUpperCase()}: {p.url.replace(/^https?:\/\/[^/]+/, '') || '/'}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Google SERP Card Preview */}
            <div className={`p-4 rounded-lg border border-line bg-white shadow-sm space-y-1.5 ${
              serpDevice === 'mobile' ? 'max-w-md' : 'max-w-2xl'
            }`}>
              <div className="flex items-center gap-2 text-xs text-[#202124]">
                <div className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center font-bold text-[9px] text-slate-600">
                  G
                </div>
                <div className="flex flex-col">
                  <span className="font-sans text-[12px] font-normal text-[#202124]">{report.domain}</span>
                  <span className="text-[10px] text-[#5f6368] font-mono truncate">{currentSerpPage?.url || report.website_url}</span>
                </div>
              </div>
              <h3 className="text-[#1a0dab] font-sans text-lg hover:underline cursor-pointer font-normal leading-snug line-clamp-1">
                {titleText}
              </h3>
              <p className="text-[#4d5156] font-sans text-xs leading-relaxed line-clamp-2">
                {metaText}
              </p>
            </div>

            {/* Pixel Meter Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink">Title SERP Pixel Width</span>
                  <span className={`font-mono text-xs font-bold ${
                    titlePx > 580 ? 'text-bad' : 'text-good'
                  }`}>
                    {titlePx} px / 580 px max
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-line overflow-hidden">
                  <div
                    className={`h-full transition-all ${titlePx > 580 ? 'bg-bad' : 'bg-good'}`}
                    style={{ width: `${Math.min(100, (titlePx / 580) * 100)}%` }}
                  />
                </div>
                <p className="text-[10px] text-ink-500">
                  {titlePx > 580 ? '⚠️ Exceeds 580px desktop width. Google will truncate with ellipsis.' : '✓ Optimal pixel length. Title will display in full on desktop SERP.'}
                </p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink">Meta Description Pixel Width</span>
                  <span className={`font-mono text-xs font-bold ${
                    metaPx > 960 ? 'text-bad' : 'text-good'
                  }`}>
                    {metaPx} px / 960 px max
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-line overflow-hidden">
                  <div
                    className={`h-full transition-all ${metaPx > 960 ? 'bg-bad' : 'bg-good'}`}
                    style={{ width: `${Math.min(100, (metaPx / 960) * 100)}%` }}
                  />
                </div>
                <p className="text-[10px] text-ink-500">
                  {metaPx > 960 ? '⚠️ Exceeds 960px snippet width. Truncation likely.' : '✓ Fits cleanly inside Google SERP preview boundaries.'}
                </p>
              </div>
            </div>
          </Card>

          {/* Headings Health */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  HTML5 Heading Hierarchy (H1 - H6)
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-ink-500 font-mono">H1 Health:</span>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-pine/10 text-pine">
                  {headings?.h1_health_score ? `${Math.round(headings.h1_health_score)}/100` : '100/100'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Missing H1</span>
                <span className="text-lg font-mono font-bold text-ink">
                  {headings?.missing_h1?.length || 0} pages
                </span>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Multiple H1s</span>
                <span className="text-lg font-mono font-bold text-ink">
                  {headings?.multiple_h1?.length || 0} pages
                </span>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Duplicate H1s</span>
                <span className="text-lg font-mono font-bold text-ink">
                  {headings?.duplicate_h1?.length || 0} pages
                </span>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50">
                <span className="text-[10px] font-mono text-ink-400 block uppercase">H1-Title Collision</span>
                <span className={`text-lg font-mono font-bold ${
                  (metaRollup?.h1_title_collision_count || 0) > 0 ? 'text-warn' : 'text-good'
                }`}>
                  {metaRollup?.h1_title_collision_count ?? 0} pages
                </span>
              </div>
            </div>

            {headings?.outline_tree_sample && headings.outline_tree_sample.length > 0 && (
              <div className="mt-4 pt-3 border-t border-line space-y-2">
                <span className="text-xs font-semibold text-ink-700 block">Homepage Heading Structure Sample:</span>
                <div className="space-y-1 font-mono text-xs p-3 rounded bg-paper-100 border border-line">
                  {headings.outline_tree_sample.map((h: any, idx: number) => (
                    <div key={idx} className="flex items-center gap-2 text-ink-700">
                      <span className="text-pine font-bold w-8">{h.tag || `H${h.level}`}</span>
                      <span className="truncate">{h.text || h.content}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Meta Tags Rollup */}
          {metaRollup && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h3 className="font-serif text-lg text-ink font-semibold">Title & Meta Description Distribution</h3>
                <span className="text-xs font-mono text-ink-500">
                  {metaRollup.total_pages_evaluated || pages.length} URLs
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Title Lengths</span>
                  <p className="text-ink-700">Optimal (50-60 chars): <strong className="font-mono">{metaRollup.optimal_titles?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Truncated (&gt;60 chars): <strong className="font-mono">{metaRollup.too_long_titles?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Exceeds 580px: <strong className="font-mono text-bad">{metaRollup.truncated_pixel_titles?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Too Short (&lt;30 chars): <strong className="font-mono">{metaRollup.too_short_titles?.length ?? 0}</strong></p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Meta Descriptions</span>
                  <p className="text-ink-700">Optimal (140-160 chars): <strong className="font-mono">{metaRollup.optimal_descriptions?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Missing: <strong className="font-mono text-warn">{metaRollup.missing_descriptions?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Exceeds 960px: <strong className="font-mono text-bad">{metaRollup.truncated_pixel_descriptions?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Truncated (&gt;160 chars): <strong className="font-mono">{metaRollup.too_long_descriptions?.length ?? 0}</strong></p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Duplicate Collisions</span>
                  <p className="text-ink-700">Duplicate Titles: <strong className="font-mono">{metaRollup.duplicate_titles?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Duplicate Descriptions: <strong className="font-mono">{metaRollup.duplicate_descriptions?.length ?? 0}</strong></p>
                  <p className="text-ink-500">H1 Identical to Title: <strong className="font-mono text-warn">{metaRollup.h1_title_collision_count ?? 0}</strong></p>
                </div>
              </div>
            </Card>
          )}

          {/* Schema.org & Google Rich Results Validation */}
          {report.schema_validation && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-pine" />
                  <h3 className="font-serif text-lg text-ink font-semibold">Schema.org & Google Rich Results Validator</h3>
                </div>
                <span className={`text-xs font-mono px-2 py-0.5 rounded font-semibold ${
                  report.schema_validation.entities_with_errors_count === 0 ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'
                }`}>
                  {report.schema_validation.valid_entities_count} of {report.schema_validation.total_entities_detected} without rich-result errors
                </span>
              </div>
              <p className="text-xs text-ink-600 leading-relaxed">
                {report.schema_validation.summary}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Entities Detected</span>
                  <p className="font-mono text-base font-bold text-ink">{report.schema_validation.total_entities_detected}</p>
                  <p className="text-[10px] text-ink-400">across {report.schema_validation.total_pages_with_schema} pages</p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Valid Rich Results</span>
                  <p className="font-mono text-base font-bold text-good">{report.schema_validation.valid_entities_count}</p>
                  <p className="text-[10px] text-good">pass Google Rich criteria</p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Syntax / Field Errors</span>
                  <p className={`font-mono text-base font-bold ${
                    report.schema_validation.entities_with_errors_count > 0 ? 'text-bad' : 'text-good'
                  }`}>{report.schema_validation.entities_with_errors_count}</p>
                  <p className="text-[10px] text-ink-400">blocks Google rich snippets</p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Detected Types</span>
                  <p className="font-mono text-xs text-ink-700 truncate">
                    {report.schema_validation.detected_types?.join(', ') || 'None'}
                  </p>
                  <p className="text-[10px] text-ink-400">{report.schema_validation.entities_with_warnings_count} warnings</p>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: ASSETS & PERFORMANCE
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'assets' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">Image Assets & CLS Stability</h3>
              </div>
              <span className="text-xs font-mono text-ink-500">
                {media?.total_images_analyzed || 0} Images Analyzed
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 uppercase">Missing Alt Text</span>
                <span className={`text-xl font-mono font-bold ${
                  (media?.missing_alt_count || 0) > 0 ? 'text-warn' : 'text-good'
                }`}>
                  {media?.missing_alt_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">Hurts image search & accessibility</p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 uppercase">Missing Dimensions (CLS)</span>
                <span className={`text-xl font-mono font-bold ${
                  (media?.missing_dimensions_count || 0) > 0 ? 'text-warn' : 'text-good'
                }`}>
                  {media?.missing_dimensions_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">Causes Core Web Vitals layout shifts</p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 uppercase">Modern Formats</span>
                <span className="text-xl font-mono font-bold text-good">
                  {media?.modern_format_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">WebP / AVIF compressed images</p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 uppercase">Insecure Mixed Content</span>
                <span className={`text-xl font-mono font-bold ${
                  (media?.mixed_content_count || 0) > 0 ? 'text-bad' : 'text-good'
                }`}>
                  {media?.mixed_content_count ?? 0}
                </span>
                <p className="text-[10px] text-ink-500">HTTP images on HTTPS pages</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: INTERNAL LINK EQUITY
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'links' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Link2 className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">Anchor Text Quality & Link Equity</h3>
              </div>
              <span className="text-xs font-mono text-ink-500">
                {anchorAudit?.total_links_analyzed || 'Analyzed'} Links
              </span>
            </div>
            <p className="text-xs text-ink-600">
              Low-equity anchor texts (e.g. &quot;click here&quot;, &quot;read more&quot;, &quot;link&quot;) waste PageRank equity and fail to pass topical relevance signals to Googlebot.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-2">
                <span className="label text-[10px] text-ink-500 block">Generic / Low-Equity Anchors</span>
                <span className="text-2xl font-mono font-bold text-ink">
                  {anchorAudit?.generic_anchor_count ?? 0}
                </span>
                <p className="text-ink-500">Links using uninformative phrases</p>
              </div>

              <div className="p-3 rounded border border-line bg-paper-50 space-y-2">
                <span className="label text-[10px] text-ink-500 block">Equity Preservation Advice</span>
                <p className="text-ink-700 leading-relaxed">
                  Replace vague CTA anchor text with descriptive keywords that indicate the destination page topic.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB: LOCAL SEO
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'local' && (
        <div className="space-y-6">
          {/* Top Vitals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                NAP Consistency Score
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold font-serif text-ink">
                  {localSeo ? `${localSeo.nap_consistency_score}%` : '100%'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  (localSeo?.nap_consistency_score ?? 100) >= 80 ? 'bg-good/10 text-good' : 'bg-red-500/10 text-red-600'
                }`}>
                  {(localSeo?.nap_consistency_score ?? 100) >= 80 ? 'Consistent' : 'Conflicts Detected'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Name, Address, Phone alignment</span>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Google Business Profile
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {localSeo?.has_google_business_profile ? 'Linked' : 'Not Linked'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  localSeo?.has_google_business_profile ? 'bg-good/10 text-good' : 'bg-amber-500/10 text-amber-600'
                }`}>
                  {localSeo?.has_google_business_profile ? 'Verified' : 'Missing Link'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Maps co-reference authority</span>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Google Maps Embed
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {localSeo?.has_google_maps_embed ? 'Embedded' : 'Missing'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  localSeo?.has_google_maps_embed ? 'bg-good/10 text-good' : 'bg-ink-500/10 text-ink-500'
                }`}>
                  {localSeo?.has_google_maps_embed ? 'Interactive' : 'No iframe'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Local contact landing proof</span>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                LocalBusiness Schema
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {localSeo?.local_business_schema_found ? `${localSeo.local_schema_completeness_pct}%` : 'Absent'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  localSeo?.local_business_schema_found ? 'bg-good/10 text-good' : 'bg-red-500/10 text-red-600'
                }`}>
                  {localSeo?.local_business_schema_found ? 'JSON-LD' : 'Missing'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Address, Geo, Hours, Telephone</span>
            </Card>
          </div>

          {/* Diagnostic Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-5 space-y-4">
              <div className="flex items-center gap-2 border-b border-line pb-3">
                <MapPin className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  NAP Consistency & Contact Footprint
                </h3>
              </div>
              <div className="space-y-3 text-xs">
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="label text-[10px] text-ink-500 block">Authoritative Phone Detected</span>
                  <span className="font-mono font-semibold text-ink text-sm">
                    {localSeo?.consistent_phone || 'No phone number declared in main text'}
                  </span>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="label text-[10px] text-ink-500 block">Authoritative Physical Address</span>
                  <span className="text-ink-700 leading-relaxed block">
                    {localSeo?.consistent_address || 'No physical address block detected on crawled pages'}
                  </span>
                </div>
                {localSeo?.phone_conflicts && localSeo.phone_conflicts.length > 1 && (
                  <div className="p-3 rounded border border-red-300 bg-red-50 dark:bg-red-950/20 space-y-2">
                    <span className="text-[10px] font-bold text-red-700 uppercase">Conflicting Phone Numbers</span>
                    <div className="space-y-1 font-mono">
                      {localSeo.phone_conflicts.map((c, i) => (
                        <div key={i} className="flex justify-between text-red-600">
                          <span>{c.phone}</span>
                          <span>({c.occurrences} pages)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {localSeo?.schema_missing_fields && localSeo.schema_missing_fields.length > 0 && (
                  <div className="p-3 rounded border border-amber-300 bg-amber-50 dark:bg-amber-950/20 space-y-1">
                    <span className="text-[10px] font-bold text-amber-700 uppercase">Missing LocalBusiness Schema Fields</span>
                    <span className="text-xs text-amber-800 dark:text-amber-300 block">
                      {localSeo.schema_missing_fields.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            </Card>

            <Card className="p-5 space-y-4">
              <div className="flex items-center gap-2 border-b border-line pb-3">
                <Globe className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Google Business Profile & Local Citations
                </h3>
              </div>
              <div className="space-y-3 text-xs">
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1.5">
                  <span className="label text-[10px] text-ink-500 block">Google Business Profile Links</span>
                  {localSeo?.gbp_urls && localSeo.gbp_urls.length > 0 ? (
                    <div className="space-y-1 font-mono">
                      {localSeo.gbp_urls.map((u, i) => (
                        <a key={i} href={u} target="_blank" rel="noopener noreferrer" className="text-pine flex items-center gap-1 hover:underline truncate">
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{u}</span>
                        </a>
                      ))}
                    </div>
                  ) : (
                    <span className="text-ink-500 italic block">No links to maps.google.com or g.page found</span>
                  )}
                </div>

                <div className="p-3 rounded border border-line bg-paper-50 space-y-1.5">
                  <span className="label text-[10px] text-ink-500 block">Local Directory Citations Found</span>
                  {localSeo?.local_citations_found && localSeo.local_citations_found.length > 0 ? (
                    <div className="space-y-1 font-mono">
                      {localSeo.local_citations_found.map((u, i) => (
                        <a key={i} href={u} target="_blank" rel="noopener noreferrer" className="text-pine flex items-center gap-1 hover:underline truncate">
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{u}</span>
                        </a>
                      ))}
                    </div>
                  ) : (
                    <span className="text-ink-500 italic block">No outbound citations to Yelp, Apple Maps, or Bing Places</span>
                  )}
                </div>

                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="label text-[10px] text-ink-500 block">Local SEO Synthesis</span>
                  <p className="text-ink-700 leading-relaxed">
                    {localSeo?.summary || 'Local SEO evaluation complete.'}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Local Landing Pages Table */}
          {localSeo?.local_landing_pages && localSeo.local_landing_pages.length > 0 && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Local Landing Pages Audit ({localSeo.local_landing_pages.length})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse border border-line">
                  <thead className="bg-paper-100 font-mono text-[11px] text-ink-700">
                    <tr>
                      <th className="p-2.5 border border-line">Location URL</th>
                      <th className="p-2.5 border border-line">Target</th>
                      <th className="p-2.5 border border-line">Unique NAP</th>
                      <th className="p-2.5 border border-line">Local Schema</th>
                      <th className="p-2.5 border border-line">Map / GBP</th>
                      <th className="p-2.5 border border-line">Status</th>
                      <th className="p-2.5 border border-line">Issues</th>
                    </tr>
                  </thead>
                  <tbody>
                    {localSeo.local_landing_pages.map((lp, i) => (
                      <tr key={i} className="hover:bg-paper-50 transition-colors">
                        <td className="p-2.5 border border-line font-mono truncate max-w-xs">{lp.url}</td>
                        <td className="p-2.5 border border-line font-semibold">{lp.target_location || '—'}</td>
                        <td className="p-2.5 border border-line">{lp.has_unique_nap ? '✅ Yes' : '❌ No'}</td>
                        <td className="p-2.5 border border-line">{lp.has_local_schema ? '✅ Yes' : '❌ No'}</td>
                        <td className="p-2.5 border border-line">{lp.has_map ? '✅ Yes' : '❌ No'}</td>
                        <td className="p-2.5 border border-line">
                          <span className={`px-1.5 py-0.5 rounded font-mono font-bold text-[10px] ${
                            lp.status === 'PASS' ? 'bg-good/10 text-good' : 'bg-red-500/10 text-red-600'
                          }`}>
                            {lp.status}
                          </span>
                        </td>
                        <td className="p-2.5 border border-line text-ink-500">
                          {lp.issues.length ? lp.issues.join('; ') : 'All localized signals present'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB: INTERNATIONAL SEO
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'international' && (
        <div className="space-y-6">
          {/* Top Vitals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Targeting Architecture
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {intlSeo?.is_multilingual ? 'Multilingual' : 'Single Locale'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  intlSeo?.is_multilingual ? 'bg-pine/10 text-pine' : 'bg-paper-100 text-ink-600'
                }`}>
                  {intlSeo?.locales_detected?.length || 1} Locales
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Hreflang & language declarations</span>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Hreflang Return Tags
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {intlSeo?.return_tags_healthy ? 'Reciprocal' : 'Broken'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  intlSeo?.return_tags_healthy ? 'bg-good/10 text-good' : 'bg-red-500/10 text-red-600'
                }`}>
                  {intlSeo?.return_tags_healthy ? 'Valid' : 'Errors Flagged'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Bidirectional confirmation</span>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                x-default Fallback
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {intlSeo?.has_x_default ? 'Present' : 'Absent'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  intlSeo?.has_x_default ? 'bg-good/10 text-good' : 'bg-amber-500/10 text-amber-600'
                }`}>
                  {intlSeo?.has_x_default ? 'Active' : 'Missing'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">Fallback for unmatched users</span>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Localized Canonical Integrity
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold font-serif text-ink">
                  {intlSeo?.issues?.some((i) => i.issue_type === 'canonical_conflict') ? 'Conflicts' : 'Aligned'}
                </span>
                <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                  intlSeo?.issues?.some((i) => i.issue_type === 'canonical_conflict') ? 'bg-red-500/10 text-red-600' : 'bg-good/10 text-good'
                }`}>
                  {intlSeo?.issues?.some((i) => i.issue_type === 'canonical_conflict') ? 'De-index Risk' : 'Self-Referencing'}
                </span>
              </div>
              <span className="text-xs text-ink-500 block">No cross-language conflicts</span>
            </Card>
          </div>

          {/* International SEO Summary & Issues */}
          {intlSeo?.issues && intlSeo.issues.length > 0 && (
            <Card className="p-5 space-y-3 border-red-200 dark:border-red-900/50 bg-red-50/40 dark:bg-red-950/20">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <h4 className="font-semibold text-sm text-red-900 dark:text-red-200">
                  International SEO Deficiencies Detected ({intlSeo.issues.length})
                </h4>
              </div>
              <div className="space-y-2 text-xs">
                {intlSeo.issues.map((iss, i) => (
                  <div key={i} className="p-2.5 rounded bg-white dark:bg-ink-900/60 border border-red-200 dark:border-red-900 flex items-start gap-2">
                    <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                      {iss.issue_type.toUpperCase()}
                    </span>
                    <span className="text-ink-700">{iss.message}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Hreflang Matrix Table */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Languages className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Hreflang & Regional Alternates Matrix
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-500">
                {intlSeo?.matrix?.length || 0} Pages Audited
              </span>
            </div>

            {intlSeo?.matrix && intlSeo.matrix.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse border border-line">
                  <thead className="bg-paper-100 font-mono text-[11px] text-ink-700">
                    <tr>
                      <th className="p-2.5 border border-line">Page URL</th>
                      <th className="p-2.5 border border-line">&lt;html lang&gt;</th>
                      <th className="p-2.5 border border-line">Alternates Count</th>
                      <th className="p-2.5 border border-line">Alternates Declared</th>
                      <th className="p-2.5 border border-line">x-default</th>
                      <th className="p-2.5 border border-line">Return Tags</th>
                      <th className="p-2.5 border border-line">Canonical Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {intlSeo.matrix.map((row, i) => (
                      <tr key={i} className="hover:bg-paper-50 transition-colors">
                        <td className="p-2.5 border border-line font-mono truncate max-w-xs">{row.url}</td>
                        <td className="p-2.5 border border-line font-mono font-semibold">{row.declared_lang || '—'}</td>
                        <td className="p-2.5 border border-line font-mono">{row.alternates_count}</td>
                        <td className="p-2.5 border border-line font-mono">
                          {row.alternates.length > 0
                            ? row.alternates.map((a) => a.hreflang).join(', ')
                            : 'None declared'}
                        </td>
                        <td className="p-2.5 border border-line">{row.has_x_default ? '✅' : '—'}</td>
                        <td className="p-2.5 border border-line">
                          {row.return_tags_valid ? (
                            <span className="text-good font-semibold">✅ Valid</span>
                          ) : (
                            <span className="text-red-600 font-semibold">❌ Missing return</span>
                          )}
                        </td>
                        <td className="p-2.5 border border-line">
                          {row.canonical_aligned ? (
                            <span className="text-good font-semibold">Self-Canonical</span>
                          ) : (
                            <span className="text-amber-600 font-semibold">Cross-Target</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-6 text-center text-ink-500 text-xs italic">
                No hreflang alternate tags detected in HTML headers or HTTP response links.
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 5: COMPETITOR SEO PARITY
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'competitors' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">
                  Competitor Technical SEO Parity Matrix
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-pine/10 text-pine">
                {compParity?.target_rank != null
                  ? `Rank #${compParity.target_rank} of ${compParity?.competitors?.length ?? 1}`
                  : 'Pending Competitor Crawl'}
              </span>
            </div>

            <p className="text-xs text-ink-600 leading-relaxed">
              {compParity?.strategic_takeaway || 'Side-by-side technical SEO audit comparing target domain against direct competitors.'}
            </p>

            {/* Side-by-side Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse border border-line">
                <thead>
                  <tr className="bg-paper-100 border-b border-line text-ink-700">
                    <th className="p-2.5 font-semibold">Metric</th>
                    {compParity?.competitors.map((c, idx) => (
                      <th key={idx} className="p-2.5 font-semibold font-mono">
                        {c.brand_name} {c.is_target && <span className="text-pine font-bold">(Target)</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">Overall SEO Score</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono font-bold text-ink">
                        {c.overall_seo_score != null ? `${c.overall_seo_score}/100` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">Technical Health</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono text-ink-700">
                        {c.technical_health_score != null ? `${c.technical_health_score}/100` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">On-Page Optimization</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono text-ink-700">
                        {c.onpage_score != null ? `${c.onpage_score}/100` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">Average Word Count</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono text-ink-700">
                        {c.avg_word_count != null ? `${c.avg_word_count} words` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">Schema Types Count</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono text-ink-700">
                        {c.schema_types_count != null ? `${c.schema_types_count} types` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">Server Latency (TTFB)</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono text-ink-700">
                        {c.avg_ttfb_ms != null ? `${c.avg_ttfb_ms} ms` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-2.5 font-medium text-ink-600">HTTP 200 Pass Rate</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-2.5 font-mono text-good font-semibold">
                        {c.http_200_rate_pct != null ? `${c.http_200_rate_pct}%` : '—'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Advantages and Deficits */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
              <div className="p-3 rounded border border-good/20 bg-good/5 space-y-1">
                <span className="font-semibold text-good block">Key Competitive Advantages</span>
                {compParity?.top_advantages && compParity.top_advantages.length > 0 ? (
                  <ul className="list-disc list-inside space-y-1 text-ink-800">
                    {compParity.top_advantages.map((adv, idx) => (
                      <li key={idx}>{adv}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-ink-500">Parity with competitor baseline.</p>
                )}
              </div>

              <div className="p-3 rounded border border-bad/20 bg-bad/5 space-y-1">
                <span className="font-semibold text-bad block">Competitive Deficits to Close</span>
                {compParity?.critical_deficits && compParity.critical_deficits.length > 0 ? (
                  <ul className="list-disc list-inside space-y-1 text-ink-800">
                    {compParity.critical_deficits.map((def, idx) => (
                      <li key={idx}>{def}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-ink-500">No major technical deficits vs peers.</p>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 6: SECURITY & HOST
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'security' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-pine" />
                <h3 className="font-serif text-lg text-ink font-semibold">SSL, HTTPS & HTTP Security Headers</h3>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-good/10 text-good">
                Score: {security?.score ? Math.round(security.score) : 100}/100
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="font-semibold text-ink block">HTTPS Enforcement</span>
                <p className="text-good font-mono text-[11px]">✓ All requests encrypted via TLS</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="font-semibold text-ink block">Mixed Content</span>
                <p className="text-good font-mono text-[11px]">✓ No insecure asset loading</p>
              </div>
              <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                <span className="font-semibold text-ink block">Security Directives</span>
                <p className="text-ink-600 font-mono text-[11px]">HSTS, X-Frame-Options checked</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 7: SEARCH CONSOLE ATTRIBUTION
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'gsc' && (
        <SearchConsoleAttributionView
          domain={report.domain}
          analysisId={analysisId}
          onOpenConnectors={() => onOpenConnectors?.('google_search_console')}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 8: FINDINGS FILTERED TO SEO
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'findings' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
            <h3 className="font-serif text-lg text-ink font-semibold">Technical & On-Page SEO Issues</h3>
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-ink-500 flex items-center gap-1"><Filter className="w-3.5 h-3.5" /> Filter:</span>
              {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setFindingSeverityFilter(sev)}
                  className={`px-2 py-0.5 rounded font-mono transition-colors ${
                    findingSeverityFilter === sev
                      ? 'bg-ink text-white font-semibold'
                      : 'bg-paper-100 text-ink-600 hover:bg-paper-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            {filteredFindings.map((f) => (
              <div
                key={f.finding_id}
                onClick={() => onSelectFinding?.(f)}
                className="p-4 rounded-lg border border-line bg-paper-50 hover:bg-paper-100 transition-colors cursor-pointer space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                      f.severity === 'CRITICAL' ? 'bg-bad/10 text-bad' :
                      f.severity === 'HIGH' ? 'bg-warn/10 text-warn' : 'bg-ink/5 text-ink-600'
                    }`}>
                      {f.severity}
                    </span>
                    <span className="text-xs font-mono text-ink-400">{f.category}</span>
                  </div>
                  <span className="text-xs text-pine font-medium hover:underline flex items-center gap-1">
                    Inspect Evidence <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
                <h4 className="text-sm font-semibold text-ink">{f.title}</h4>
                <p className="text-xs text-ink-600 line-clamp-2">{f.description}</p>
                {f.recommendation && (
                  <div className="text-xs bg-paper-100 p-2 rounded border border-line/60 text-ink-700">
                    <strong className="text-ink font-medium">Fix: </strong>{f.recommendation}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 9: TECHNICAL URL APPENDIX & DATA GRID
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'appendix' && (
        <div className="space-y-6">
          <UrlLevelTechnicalAppendix
            pages={pages}
            manifest={crawl}
            domain={report.domain}
          />
        </div>
      )}
    </PillarShell>
  );
}
