import React, { useState } from 'react';
import { ExecutiveReport } from '../../../types';
import { Card } from '../../ui';
import {
  Search,
  Monitor,
  Smartphone,
  FileCode,
  Image as ImageIcon,
  Link2,
  AlertTriangle,
  CheckCircle2,
  Edit3,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

interface SeoOnPageExperienceProps {
  report: ExecutiveReport;
}

export function SeoOnPageExperience({ report }: SeoOnPageExperienceProps) {
  const crawl = report.crawl_manifest;
  const pages = crawl?.pages || [];
  const homePage = pages[0];

  const [serpDevice, setSerpDevice] = useState<'desktop' | 'mobile'>('desktop');
  const [selectedSerpPageUrl, setSelectedSerpPageUrl] = useState<string>(homePage?.url || '');
  const [sandboxMode, setSandboxMode] = useState(false);

  const currentSerpPage = pages.find((p) => p.url === selectedSerpPageUrl) || homePage;

  // Custom sandbox values
  const defaultTitle = currentSerpPage?.title || report.domain;
  const defaultMeta = currentSerpPage?.meta_description || 'No meta description provided for this URL.';
  const [customTitle, setCustomTitle] = useState(defaultTitle);
  const [customMeta, setCustomMeta] = useState(defaultMeta);

  // Sync when page changes
  const handlePageSelect = (url: string) => {
    setSelectedSerpPageUrl(url);
    const targetPage = pages.find((p) => p.url === url) || homePage;
    setCustomTitle(targetPage?.title || report.domain);
    setCustomMeta(targetPage?.meta_description || 'No meta description provided for this URL.');
  };

  const activeTitle = sandboxMode ? customTitle : (currentSerpPage?.title || report.domain);
  const activeMeta = sandboxMode ? customMeta : (currentSerpPage?.meta_description || 'No meta description provided for this URL.');

  // Accurate Google pixel width estimations
  // Desktop Arial ~9.5px per average character for 20px font
  const titlePx = Math.min(800, Math.round(activeTitle.length * 9.5));
  // Meta description ~7.0px per character for 14px font
  const metaPx = Math.min(1200, Math.round(activeMeta.length * 7.0));

  const headings = report.heading_hierarchy;
  const metaRollup = report.meta_rollup;
  const media = report.media_assets;
  const anchorAudit = report.anchor_text_audit;

  return (
    <div className="space-y-6">
      {/* ─────────────────────────────────────────────────────────────
          1. GOOGLE SERP SIMULATOR & LIVE TEST SANDBOX
          ───────────────────────────────────────────────────────────── */}
      <Card className="p-6 space-y-5 border-line bg-paper-50">
        <div className="flex flex-wrap items-center justify-between border-b border-line pb-3 gap-3">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-ink-700" />
            <h3 className="font-sans text-base font-semibold text-ink">
              Google SERP Snippet Simulator & Pixel Meter
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Desktop / Mobile Switcher */}
            <div className="flex items-center border border-line rounded p-0.5 bg-paper-100 text-xs">
              <button
                type="button"
                onClick={() => setSerpDevice('desktop')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
                  serpDevice === 'desktop' ? 'bg-paper-50 shadow-sm font-semibold text-ink' : 'text-ink-500'
                }`}
              >
                <Monitor className="w-3.5 h-3.5" /> Desktop
              </button>
              <button
                type="button"
                onClick={() => setSerpDevice('mobile')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
                  serpDevice === 'mobile' ? 'bg-paper-50 shadow-sm font-semibold text-ink' : 'text-ink-500'
                }`}
              >
                <Smartphone className="w-3.5 h-3.5" /> Mobile
              </button>
            </div>

            {/* Live Sandbox Toggle */}
            <button
              type="button"
              onClick={() => setSandboxMode(!sandboxMode)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono transition-colors ${
                sandboxMode
                  ? 'bg-pine-600 text-white border-pine-600 font-semibold shadow-sm'
                  : 'bg-paper-100 border-line text-ink-600 hover:bg-paper-200'
              }`}
            >
              <Edit3 className="w-3.5 h-3.5" />
              {sandboxMode ? 'Editing Sandbox Active' : 'Test Custom Copy'}
            </button>

            {/* URL Selector Dropdown */}
            {pages.length > 1 && (
              <select
                className="text-xs border border-line rounded px-2.5 py-1 bg-paper-50 font-mono text-ink max-w-[220px] truncate"
                value={selectedSerpPageUrl}
                onChange={(e) => handlePageSelect(e.target.value)}
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

        {/* Live Edit Sandbox Inputs (Visible when test mode is ON) */}
        {sandboxMode && (
          <div className="p-4 rounded-lg bg-pine-500/5 border border-pine-500/20 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-pine-700 dark:text-pine-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-pine-600" />
                Live Snippet Copy Sandbox: Test changes before deployment
              </span>
              <button
                type="button"
                onClick={() => {
                  setCustomTitle(defaultTitle);
                  setCustomMeta(defaultMeta);
                }}
                className="text-ink-500 hover:text-ink flex items-center gap-1 text-[11px]"
              >
                <RotateCcw className="w-3 h-3" /> Reset to original
              </button>
            </div>

            <div className="space-y-2">
              <div>
                <label className="text-[11px] font-medium text-ink-600 block mb-1">Proposed Title Tag:</label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full text-xs font-mono px-3 py-1.5 rounded border border-line bg-paper-50 text-ink focus:outline-none focus:ring-1 focus:ring-pine-500"
                  placeholder="Enter custom title..."
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-ink-600 block mb-1">Proposed Meta Description:</label>
                <textarea
                  value={customMeta}
                  onChange={(e) => setCustomMeta(e.target.value)}
                  rows={2}
                  className="w-full text-xs font-mono px-3 py-1.5 rounded border border-line bg-paper-50 text-ink focus:outline-none focus:ring-1 focus:ring-pine-500"
                  placeholder="Enter custom meta description..."
                />
              </div>
            </div>
          </div>
        )}

        {/* Google SERP Card Preview */}
        <div className={`p-4 rounded-lg border border-line bg-paper-50 shadow-sm space-y-1.5 transition-all ${
          serpDevice === 'mobile' ? 'max-w-md' : 'max-w-2xl'
        }`}>
          {/* Favicon & Breadcrumb Header */}
          <div className="flex items-center gap-2 text-xs text-[#202124]">
            <div className="w-5 h-5 rounded-full bg-paper-200 border border-line flex items-center justify-center font-bold text-[10px] text-ink-600">
              G
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-sans text-[12px] font-semibold text-[#202124] truncate">
                {report.business_profile?.business_name || report.domain}
              </span>
              <span className="text-[11px] text-[#5f6368] font-mono truncate">
                {currentSerpPage?.url || report.website_url}
              </span>
            </div>
          </div>

          {/* Title Snippet */}
          <h3 className="text-[#1a0dab] dark:text-[#8ab4f8] font-sans text-lg hover:underline cursor-pointer font-normal leading-snug line-clamp-1">
            {activeTitle}
          </h3>

          {/* Meta Description */}
          <p className="text-[#4d5156] dark:text-[#bdc1c6] font-sans text-xs leading-relaxed line-clamp-2">
            {activeMeta}
          </p>
        </div>

        {/* Pixel Meter Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-1">
          {/* Title Pixel Meter */}
          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-ink">Title Pixel Gauge</span>
              <span className={`font-mono text-xs font-bold ${
                titlePx > 580 ? 'text-bad' : 'text-good'
              }`}>
                {titlePx} px / 580 px max ({activeTitle.length} chars)
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-paper-200 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${titlePx > 580 ? 'bg-bad' : 'bg-good'}`}
                style={{ width: `${Math.min(100, (titlePx / 580) * 100)}%` }}
              />
            </div>
            <p className="text-[11px] text-ink-500">
              {titlePx > 580
                ? '⚠ Exceeds 580px desktop width. Google desktop SERP will truncate with ellipsis.'
                : '✓ Optimal pixel length. Full title is guaranteed to display on desktop and mobile SERPs.'}
            </p>
          </div>

          {/* Meta Description Pixel Meter */}
          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-ink">Meta Description Gauge</span>
              <span className={`font-mono text-xs font-bold ${
                metaPx > 960 ? 'text-bad' : 'text-good'
              }`}>
                {metaPx} px / 960 px max ({activeMeta.length} chars)
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-paper-200 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${metaPx > 960 ? 'bg-bad' : 'bg-good'}`}
                style={{ width: `${Math.min(100, (metaPx / 960) * 100)}%` }}
              />
            </div>
            <p className="text-[11px] text-ink-500">
              {metaPx > 960
                ? '⚠ Exceeds 960px snippet boundary. Google may truncate or replace with on-page text.'
                : '✓ Well within snippet display threshold. Clear and concise search teaser.'}
            </p>
          </div>
        </div>
      </Card>

      {/* ─────────────────────────────────────────────────────────────
          2. HTML5 HEADING HIERARCHY (H1 - H6)
          ───────────────────────────────────────────────────────────── */}
      <Card className="p-6 space-y-4 border-line bg-paper-50">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2">
            <FileCode className="w-4 h-4 text-ink-700" />
            <h3 className="font-sans text-base font-semibold text-ink">
              HTML5 Heading Hierarchy & Semantic Structure
            </h3>
          </div>
          <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-paper-200 text-ink-700">
            H1 Score: {headings?.h1_health_score ? Math.round(headings.h1_health_score) : 100}/100
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">Missing H1</span>
            <span className={`text-xl font-mono font-bold ${
              (headings?.missing_h1?.length || 0) > 0 ? 'text-bad' : 'text-good'
            }`}>
              {headings?.missing_h1?.length || 0} pages
            </span>
            <p className="text-[10px] text-ink-500">Lacks primary topic heading</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">Multiple H1s</span>
            <span className={`text-xl font-mono font-bold ${
              (headings?.multiple_h1?.length || 0) > 0 ? 'text-warn' : 'text-good'
            }`}>
              {headings?.multiple_h1?.length || 0} pages
            </span>
            <p className="text-[10px] text-ink-500">Dilutes primary keyword weight</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">Duplicate H1s</span>
            <span className={`text-xl font-mono font-bold ${
              (headings?.duplicate_h1?.length || 0) > 0 ? 'text-warn' : 'text-good'
            }`}>
              {headings?.duplicate_h1?.length || 0} pages
            </span>
            <p className="text-[10px] text-ink-500">Exact duplicate across pages</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">H1-Title Collision</span>
            <span className={`text-xl font-mono font-bold ${
              (metaRollup?.h1_title_collision_count || 0) > 0 ? 'text-warn' : 'text-good'
            }`}>
              {metaRollup?.h1_title_collision_count ?? 0} pages
            </span>
            <p className="text-[10px] text-ink-500">Exact match limits secondary rank</p>
          </div>
        </div>

        {/* Outline Sample */}
        {headings?.outline_tree_sample && headings.outline_tree_sample.length > 0 && (
          <div className="mt-3 pt-3 border-t border-line space-y-2">
            <span className="text-xs font-semibold text-ink-700 block">
              Sample Heading Hierarchy Outline Tree:
            </span>
            <div className="space-y-1 font-mono text-xs p-3 rounded bg-paper-100 border border-line max-h-40 overflow-y-auto">
              {headings.outline_tree_sample.map((h: any, idx: number) => (
                <div key={idx} className="flex items-center gap-2 text-ink-700">
                  <span className="text-pine-600 font-bold w-7 shrink-0">{h.tag || `H${h.level}`}</span>
                  <span className="truncate">{h.text || h.content}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* ─────────────────────────────────────────────────────────────
          3. MEDIA ASSETS & CORE WEB VITALS (CLS)
          ───────────────────────────────────────────────────────────── */}
      <Card className="p-6 space-y-4 border-line bg-paper-50">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-4 h-4 text-ink-700" />
            <h3 className="font-sans text-base font-semibold text-ink">
              Image Assets, Accessibility & CLS Layout Shifts
            </h3>
          </div>
          <span className="text-xs font-mono text-ink-500">
            {media?.total_images_analyzed || 0} Images Analyzed
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 uppercase font-bold">Missing Alt Text</span>
            <span className={`text-xl font-mono font-bold ${
              (media?.missing_alt_count || 0) > 0 ? 'text-warn' : 'text-good'
            }`}>
              {media?.missing_alt_count ?? 0}
            </span>
            <p className="text-[10px] text-ink-500">Hurts Google Image search & screen readers</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 uppercase font-bold">Missing Dimensions (CLS)</span>
            <span className={`text-xl font-mono font-bold ${
              (media?.missing_dimensions_count || 0) > 0 ? 'text-warn' : 'text-good'
            }`}>
              {media?.missing_dimensions_count ?? 0}
            </span>
            <p className="text-[10px] text-ink-500">Triggers Core Web Vitals layout shifts</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 uppercase font-bold">Next-Gen Formats</span>
            <span className="text-xl font-mono font-bold text-good">
              {media?.modern_format_count ?? 0}
            </span>
            <p className="text-[10px] text-ink-500">Optimized WebP / AVIF compression</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
            <span className="text-[10px] font-mono text-ink-400 uppercase font-bold">Insecure Content</span>
            <span className={`text-xl font-mono font-bold ${
              (media?.mixed_content_count || 0) > 0 ? 'text-bad' : 'text-good'
            }`}>
              {media?.mixed_content_count ?? 0}
            </span>
            <p className="text-[10px] text-ink-500">HTTP image assets served on HTTPS</p>
          </div>
        </div>
      </Card>

      {/* ─────────────────────────────────────────────────────────────
          4. INTERNAL LINK EQUITY & ANCHOR DIVERSITY
          ───────────────────────────────────────────────────────────── */}
      <Card className="p-6 space-y-4 border-line bg-paper-50">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2">
            <Link2 className="w-4 h-4 text-ink-700" />
            <h3 className="font-sans text-base font-semibold text-ink">
              Internal Link Equity & Anchor Text Quality
            </h3>
          </div>
          <span className="text-xs font-mono text-ink-500">
            {anchorAudit?.total_links_analyzed || 'Analyzed'} Links
          </span>
        </div>

        <p className="text-xs text-ink-600 leading-relaxed">
          Low-equity anchor texts (e.g. &quot;click here&quot;, &quot;learn more&quot;, &quot;read this&quot;) waste PageRank equity and fail to pass topical semantic signals to Googlebot.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-2">
            <span className="text-[10px] font-mono uppercase font-bold text-ink-500 block">Generic / Low-Equity Anchors</span>
            <span className="text-2xl font-mono font-bold text-ink">
              {anchorAudit?.generic_anchor_count ?? 0}
            </span>
            <p className="text-ink-500">Links using uninformative CTA phrases instead of topical keywords</p>
          </div>

          <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-2">
            <span className="text-[10px] font-mono uppercase font-bold text-ink-500 block">Equity Preservation Strategy</span>
            <p className="text-ink-700 leading-relaxed">
              Replace ambiguous call-to-action anchors with descriptive keyword targets that clearly define the receiving page topic.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
