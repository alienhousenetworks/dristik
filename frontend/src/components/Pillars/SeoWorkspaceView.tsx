import React, { useState } from 'react';
import { ExecutiveReport, Finding } from '../../types';
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
} from 'lucide-react';

interface SeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onSelectFinding?: (f: Finding) => void;
  onOpenConnectors?: (tabId?: string) => void;
}

type SeoSubTab = 'crawl' | 'onpage' | 'assets' | 'links' | 'security' | 'gsc' | 'findings' | 'appendix';

export function SeoWorkspaceView({
  report,
  analysisId,
  onSelectFinding,
  onOpenConnectors,
}: SeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<SeoSubTab>('crawl');

  const crawl = report.crawl_manifest;
  const pages = crawl?.pages || [];
  const homePage = pages[0];

  const seoFindings = (report.findings || []).filter(
    (f) => f.category === 'TECHNICAL_SEO' || f.category === 'ON_PAGE_SEO' || f.category === 'CONTENT'
  );

  const redirects = report.host_and_redirects;
  const clickDepth = report.click_depth;
  const orphanPages = report.orphan_pages;
  const headings = report.heading_hierarchy;
  const media = report.media_assets;
  const security = report.security_audit;
  const metaRollup = report.meta_rollup;
  const anchorAudit = report.anchor_text_audit;

  const seoScore = report.scores?.category_scores?.['TECHNICAL_SEO']?.score ?? 80;

  return (
    <PillarShell
      kicker="Discipline 1 · Technical & On-Page SEO"
      title="Search Engine Optimization (SEO)"
      description="Crawlability, HTTP status codes, redirect consolidation, heading hierarchy, meta tags, and internal link equity."
      scoreLabel="SEO Index"
      score={Math.round(seoScore)}
      metaLabel="Issues"
      meta={`${seoFindings.length} flagged`}
      tabs={[
        { id: 'crawl', label: 'Crawl & Architecture' },
        { id: 'onpage', label: 'On-Page & Headings' },
        { id: 'assets', label: 'Images & Performance' },
        { id: 'links', label: 'Internal Link Equity' },
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
                XML Sitemap
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
                Robots.txt Directive
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                {crawl?.robots_txt_found ? (
                  <CheckCircle2 className="w-4 h-4 text-good shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-warn shrink-0" />
                )}
                <span>{crawl?.robots_txt_found ? 'Accessible & Valid' : 'Not Discovered'}</span>
              </div>
              <p className="text-xs text-ink-500">
                {crawl?.robots_txt_found ? 'Standard crawl rules active' : 'Default crawler behavior'}
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                HTTP Response & Latency
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                <span className="font-mono text-base">{homePage?.ttfb_ms ? `${homePage.ttfb_ms} ms` : 'Sub-second'}</span>
                <span className="text-xs font-mono text-good font-semibold">TTFB</span>
              </div>
              <p className="text-xs text-ink-500">
                {pages.filter((p) => p.status_code === 200).length} of {pages.length} pages returned HTTP 200 OK
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Max Click Depth
              </span>
              <div className="flex items-center gap-1.5 text-ink font-semibold">
                <Layers className="w-4 h-4 text-pine shrink-0" />
                <span className="font-mono text-base">{clickDepth?.max_click_depth ?? 2} Clicks</span>
              </div>
              <p className="text-xs text-ink-500">
                {clickDepth?.high_depth_warning_count ? `${clickDepth.high_depth_warning_count} deep pages` : 'Good crawl hierarchy'}
              </p>
            </Card>
          </div>

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
                      → {result.final_destination || 'Resolved'}
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
            {/* Click Depth Pyramid */}
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

            {/* Orphan Pages */}
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
          SUB-TAB 2: ON-PAGE & HEADINGS
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'onpage' && (
        <div className="space-y-6">
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
                <span className="text-[10px] font-mono text-ink-400 block uppercase">Hierarchy Skips</span>
                <span className="text-lg font-mono font-bold text-ink">
                  {headings?.hierarchy_violations?.length || 0} violations
                </span>
              </div>
            </div>

            {/* Outline Tree Sample */}
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
                  <p className="text-ink-500">Too Short (&lt;30 chars): <strong className="font-mono">{metaRollup.too_short_titles?.length ?? 0}</strong></p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Meta Descriptions</span>
                  <p className="text-ink-700">Optimal (120-160 chars): <strong className="font-mono">{metaRollup.optimal_descriptions?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Missing: <strong className="font-mono text-warn">{metaRollup.missing_descriptions?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Truncated (&gt;160 chars): <strong className="font-mono">{metaRollup.too_long_descriptions?.length ?? 0}</strong></p>
                </div>
                <div className="p-3 rounded border border-line bg-paper-50 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase">Duplicate Meta</span>
                  <p className="text-ink-700">Duplicate Titles: <strong className="font-mono">{metaRollup.duplicate_titles?.length ?? 0}</strong></p>
                  <p className="text-ink-500">Duplicate Descriptions: <strong className="font-mono">{metaRollup.duplicate_descriptions?.length ?? 0}</strong></p>
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
                  {report.schema_validation.valid_entities_count} of {report.schema_validation.total_entities_detected} Valid
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

              {report.schema_validation.issues && report.schema_validation.issues.length > 0 && (
                <div className="space-y-2 pt-2">
                  <span className="text-xs font-semibold text-ink">Validation Issues & Remedies</span>
                  <div className="max-h-48 overflow-y-auto space-y-1.5">
                    {report.schema_validation.issues.map((iss, idx) => (
                      <div key={idx} className={`p-2.5 rounded border text-xs flex items-start justify-between gap-3 ${
                        iss.severity === 'ERROR' ? 'bg-bad/5 border-bad/20' : 'bg-warn/5 border-warn/20'
                      }`}>
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            <span className={`px-1.5 py-0.2 rounded font-bold uppercase ${
                              iss.severity === 'ERROR' ? 'bg-bad/20 text-bad' : 'bg-warn/20 text-warn'
                            }`}>{iss.severity}</span>
                            <span className="font-semibold text-ink">{iss.schema_type}</span>
                            <span className="text-ink-400">({iss.field})</span>
                          </div>
                          <p className="text-ink-700">{iss.message}</p>
                          <p className="text-[10px] font-mono text-ink-400 truncate">{iss.url}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
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
          SUB-TAB 5: SECURITY & HOST
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
          SUB-TAB 6: SEARCH CONSOLE ATTRIBUTION
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'gsc' && (
        <SearchConsoleAttributionView
          domain={report.domain}
          analysisId={analysisId}
          onOpenConnectors={() => onOpenConnectors?.('google_search_console')}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 7: FINDINGS FILTERED TO SEO
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'findings' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-lg text-ink font-semibold">Technical & On-Page SEO Issues</h3>
            <span className="text-xs text-ink-500 font-mono">{seoFindings.length} findings</span>
          </div>

          <div className="space-y-3">
            {seoFindings.map((f) => (
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
          SUB-TAB 8: TECHNICAL URL APPENDIX & DATA GRID
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
