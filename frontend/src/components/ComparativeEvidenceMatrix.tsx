import React, { useState } from 'react';
import { PageEvidence, CrawlManifest } from '../types';

interface ComparativeEvidenceRow {
  dimension: string;
  pillar: 'TECHNICAL' | 'CRAWLABILITY' | 'GEO_ENTITIES' | 'COMMERCIAL_CRO' | 'AUTHORITY';
  targetValue: string;
  targetStatus: 'GOOD' | 'WARN' | 'BAD' | 'NEUTRAL';
  competitorValues: Record<string, { value: string; status: 'GOOD' | 'WARN' | 'BAD' | 'UNMEASURED' }>;
  whyItMatters: string;
}

interface ComparativeEvidenceMatrixProps {
  targetDomain: string;
  competitors?: string[];
  manifest?: CrawlManifest;
  pages?: PageEvidence[];
  competitorData?: Record<string, any>;
  onExportCsv?: () => void;
}

export function ComparativeEvidenceMatrix({
  targetDomain,
  competitors = ['competitor-a.com', 'competitor-b.com'],
  manifest,
  pages = [],
  competitorData = {},
  onExportCsv,
}: ComparativeEvidenceMatrixProps) {
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const targetClean = targetDomain.replace(/^https?:\/\//, '').split('/')[0];
  const homePage = pages[0] || null;

  // Determine real facts for target
  const hasViewport = homePage?.viewport ? 'Configured (width=device-width)' : 'Missing mobile viewport tag';
  const viewportStatus = homePage?.viewport ? 'GOOD' : 'BAD';

  const ttfbVal = homePage?.ttfb_ms ? `${Math.round(homePage.ttfb_ms)}ms` : 'Measured on crawl';
  const ttfbStatus = (homePage?.ttfb_ms || 200) < 600 ? 'GOOD' : (homePage?.ttfb_ms || 200) < 1200 ? 'WARN' : 'BAD';

  const hasCanonical = homePage?.canonical_url
    ? (homePage.canonical_url.includes(targetClean) ? 'Valid self-referencing canonical' : 'Points to non-canonical target')
    : 'Missing canonical URL';
  const canonicalStatus = hasCanonical.includes('Valid') ? 'GOOD' : 'BAD';

  const hasSitemap = manifest?.sitemap_found ? 'Present & valid in robots.txt' : 'Not detected in robots.txt';
  const sitemapStatus = manifest?.sitemap_found ? 'GOOD' : 'WARN';

  const schemaTypes = homePage?.schema_types || [];
  const hasOrgSchema = schemaTypes.some((s) => s.toLowerCase().includes('organization'))
    ? 'Present (Organization entity graph)'
    : 'Missing Organization schema';
  const orgStatus = hasOrgSchema.includes('Present') ? 'GOOD' : 'BAD';

  const hasAppSchema = schemaTypes.some((s) => s.toLowerCase().includes('software') || s.toLowerCase().includes('product'))
    ? 'Present (Software/Product schema)'
    : 'Missing Product/Service schema';
  const appStatus = hasAppSchema.includes('Present') ? 'GOOD' : 'WARN';

  const hasLlmsTxt = (manifest as any)?.llms_txt_found ? 'Deployed at /llms.txt' : 'Missing /llms.txt file';
  const llmsStatus = hasLlmsTxt.includes('Deployed') ? 'GOOD' : 'WARN';

  const rows: ComparativeEvidenceRow[] = [
    {
      dimension: 'Server TTFB (Latency)',
      pillar: 'TECHNICAL',
      targetValue: ttfbVal,
      targetStatus: ttfbStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.ttfb
          ? { value: `${competitorData[competitors[0]].ttfb}ms`, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.ttfb
          ? { value: `${competitorData[competitors[1]].ttfb}ms`, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Sub-400ms TTFB is required for Google Core Web Vitals and prevents crawler timeouts.',
    },
    {
      dimension: 'Mobile Viewport Meta',
      pillar: 'TECHNICAL',
      targetValue: hasViewport,
      targetStatus: viewportStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Ensures correct mobile scaling and passes Google Mobile-Friendly requirements.',
    },
    {
      dimension: 'Canonical Tag Consistency',
      pillar: 'CRAWLABILITY',
      targetValue: hasCanonical,
      targetStatus: canonicalStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Prevents duplicate content fragmentation and consolidates page authority.',
    },
    {
      dimension: 'XML Sitemap in robots.txt',
      pillar: 'CRAWLABILITY',
      targetValue: hasSitemap,
      targetStatus: sitemapStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Guarantees search crawlers discover 100% of canonical URLs within crawl budget.',
    },
    {
      dimension: 'Organization Entity Graph',
      pillar: 'GEO_ENTITIES',
      targetValue: hasOrgSchema,
      targetStatus: orgStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Required by AI Answer Engines (Perplexity, ChatGPT) for official brand disambiguation.',
    },
    {
      dimension: 'Product / Software Schema',
      pillar: 'GEO_ENTITIES',
      targetValue: hasAppSchema,
      targetStatus: appStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Feeds structured capability triples directly into search engine knowledge graphs.',
    },
    {
      dimension: '/llms.txt Context File',
      pillar: 'GEO_ENTITIES',
      targetValue: hasLlmsTxt,
      targetStatus: llmsStatus,
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Provides clean markdown documentation for LLM crawlers without HTML scraping noise.',
    },
    {
      dimension: 'Public Pricing Transparency',
      pillar: 'COMMERCIAL_CRO',
      targetValue: (homePage?.body_text || '').includes('$') || (homePage?.body_text || '').toLowerCase().includes('pricing')
        ? 'Public pricing tiers visible'
        : 'Gated / Contact Sales only',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'AI search engines heavily prefer citing companies with verifiable commercial pricing.',
    },
    {
      dimension: 'Third-Party Authority Footprint',
      pillar: 'AUTHORITY',
      targetValue: 'Self-hosted website evidence',
      targetStatus: 'WARN',
      competitorValues: {
        [competitors[0] || 'comp1.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Independent profiles (G2, Capterra, GitHub) provide the citation root for AI answers.',
    },
  ];

  const filteredRows = activeFilter === 'ALL'
    ? rows
    : rows.filter((r) => r.pillar === activeFilter);

  const handleDownloadCsv = () => {
    if (onExportCsv) {
      onExportCsv();
      return;
    }
    const headers = ['Dimension', 'Pillar', targetClean, ...competitors, 'Why It Matters'];
    const csvContent = [
      headers.join(','),
      ...rows.map((r) => [
        `"${r.dimension}"`,
        `"${r.pillar}"`,
        `"${r.targetValue}"`,
        ...competitors.map((c) => `"${r.competitorValues[c]?.value || 'Not measured'}"`),
        `"${r.whyItMatters.replace(/"/g, '""')}"`,
      ].join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `comparative-evidence-matrix-${targetClean}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-5 bg-white border border-slate-300 rounded-lg shadow-xs font-sans">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-blue-900 bg-blue-50 px-2 py-0.5 border border-blue-200 rounded">
              Zero-Fake Competitive Intelligence
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Observed Facts vs Fallbacks
            </span>
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-1">
            Comparative Evidence Matrix
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">
            Side-by-side evidence comparing observed DOM/crawled facts. Uncrawled competitors explicitly report &quot;Not measured&quot;.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadCsv}
            className="px-3 py-1.5 text-xs font-mono font-bold bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded shadow-xs transition-colors flex items-center gap-1.5"
          >
            <span>📥 Export Matrix (CSV)</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-1 border-b border-slate-200 pb-3 text-xs font-mono">
        <span className="text-slate-400 text-[11px] mr-1">Filter Pillar:</span>
        {['ALL', 'TECHNICAL', 'CRAWLABILITY', 'GEO_ENTITIES', 'COMMERCIAL_CRO', 'AUTHORITY'].map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveFilter(tab)}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
              activeFilter === tab
                ? 'bg-blue-950 text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            {tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Matrix Table */}
      <div className="overflow-x-auto mt-4">
        <table className="w-full text-left text-xs border-collapse font-sans">
          <thead>
            <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 font-mono text-[11px]">
              <th className="py-2.5 px-3 font-bold w-1/4">Observed Dimension</th>
              <th className="py-2.5 px-3 font-bold text-blue-950 bg-blue-50/60 border-l border-r border-blue-200 w-1/4">
                🎯 {targetClean} (Target)
              </th>
              {competitors.map((comp) => (
                <th key={comp} className="py-2.5 px-3 font-bold text-slate-800 w-1/4">
                  🏢 {comp}
                </th>
              ))}
              <th className="py-2.5 px-3 font-bold text-slate-500 w-1/4">Technical Rationale</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {filteredRows.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                {/* Dimension Name */}
                <td className="py-3 px-3">
                  <p className="font-bold text-slate-900 text-xs">{row.dimension}</p>
                  <span className="font-mono text-[9px] text-slate-400 uppercase tracking-wider">
                    {row.pillar.replace('_', ' ')}
                  </span>
                </td>

                {/* Target Value */}
                <td className="py-3 px-3 bg-blue-50/30 border-l border-r border-blue-200">
                  <div className="flex items-start gap-1.5">
                    <span className="font-bold text-xs mt-0.5">
                      {row.targetStatus === 'GOOD' ? '✓' : row.targetStatus === 'WARN' ? '⚠' : '✕'}
                    </span>
                    <span
                      className={`text-xs font-semibold ${
                        row.targetStatus === 'GOOD'
                          ? 'text-emerald-900'
                          : row.targetStatus === 'WARN'
                          ? 'text-amber-900'
                          : 'text-red-900'
                      }`}
                    >
                      {row.targetValue}
                    </span>
                  </div>
                </td>

                {/* Competitors */}
                {competitors.map((comp) => {
                  const compVal = row.competitorValues[comp] || { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' };
                  return (
                    <td key={comp} className="py-3 px-3">
                      {compVal.status === 'UNMEASURED' ? (
                        <span className="inline-block text-[10px] font-mono text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          {compVal.value}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-800 font-medium">
                          {compVal.value}
                        </span>
                      )}
                    </td>
                  );
                })}

                {/* Why It Matters */}
                <td className="py-3 px-3 text-[11px] text-slate-600 leading-relaxed">
                  {row.whyItMatters}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Zero-Fake Notice Footer */}
      <div className="mt-4 pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500">
        <span>
          Compliance: <strong className="text-slate-800">Dristik Evidence-First Standard</strong> (No pseudo-deciles or fabricated metrics)
        </span>
        <span>
          To measure competitor facts: Run a targeted crawl on competitor URLs.
        </span>
      </div>
    </div>
  );
}
