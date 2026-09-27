import React, { useState, useMemo } from 'react';
import { PageEvidence, CrawlManifest } from '../types';

interface UrlLevelTechnicalAppendixProps {
  pages?: PageEvidence[];
  manifest?: CrawlManifest;
  domain?: string;
}

export function UrlLevelTechnicalAppendix({
  pages = [],
  manifest,
  domain = 'target.com',
}: UrlLevelTechnicalAppendixProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<
    'ALL' | '200' | 'REDIRECT' | 'ERROR' | 'CANONICAL_ISSUE' | 'MISSING_H1' | 'THIN_CONTENT' | 'PIXEL_TRUNCATED'
  >('ALL');

  // Summary Metrics
  const totalUrls = pages.length;
  const okCount = pages.filter((p) => p.status_code >= 200 && p.status_code < 300).length;
  const redirectCount = pages.filter((p) => p.status_code >= 300 && p.status_code < 400).length;
  const errorCount = pages.filter((p) => p.status_code >= 400).length;
  const canonicalIssueCount = pages.filter((p) => {
    if (!p.canonical_url) return true;
    const cleanUrl = p.url.replace(/\/$/, '');
    const cleanCanon = p.canonical_url.replace(/\/$/, '');
    return cleanUrl !== cleanCanon;
  }).length;
  const missingH1Count = pages.filter((p) => !p.h1 || p.h1.length === 0).length;
  const thinContentCount = pages.filter((p) => (p.word_count || 0) < 250).length;
  const pixelTruncatedCount = pages.filter(
    (p) => (p.title_pixel_width && p.title_pixel_width > 580) || p.title_pixel_status === 'TRUNCATED'
  ).length;

  const avgTtfb = useMemo(() => {
    if (!pages.length) return 0;
    const sum = pages.reduce((acc, p) => acc + (p.ttfb_ms || 0), 0);
    return Math.round(sum / pages.length);
  }, [pages]);

  // Filtered pages
  const filteredPages = useMemo(() => {
    return pages.filter((p) => {
      // 1. Text Search
      if (searchTerm) {
        const lower = searchTerm.toLowerCase();
        const urlMatch = (p.url || '').toLowerCase().includes(lower);
        const titleMatch = (p.title || '').toLowerCase().includes(lower);
        const h1Match = (p.h1 || []).some((h) => h.toLowerCase().includes(lower));
        if (!urlMatch && !titleMatch && !h1Match) return false;
      }

      // 2. Status Filter
      if (statusFilter === '200') return p.status_code >= 200 && p.status_code < 300;
      if (statusFilter === 'REDIRECT') return p.status_code >= 300 && p.status_code < 400;
      if (statusFilter === 'ERROR') return p.status_code >= 400;
      if (statusFilter === 'CANONICAL_ISSUE') {
        if (!p.canonical_url) return true;
        return p.url.replace(/\/$/, '') !== p.canonical_url.replace(/\/$/, '');
      }
      if (statusFilter === 'MISSING_H1') {
        return !p.h1 || p.h1.length === 0;
      }
      if (statusFilter === 'THIN_CONTENT') {
        return (p.word_count || 0) < 250;
      }
      if (statusFilter === 'PIXEL_TRUNCATED') {
        return (p.title_pixel_width && p.title_pixel_width > 580) || p.title_pixel_status === 'TRUNCATED';
      }
      return true;
    });
  }, [pages, searchTerm, statusFilter]);

  const handleExportCsv = () => {
    const headers = [
      'URL',
      'Status Code',
      'Indexable',
      'Inlinks',
      'TTFB (ms)',
      'Canonical URL',
      'Canonical Status',
      'Title',
      'Title Length',
      'Title Pixel Width (px)',
      'Title Pixel Status',
      'Primary H1',
      'H1 Count',
      'Word Count',
      'Thin Content',
      'Schema Types',
      'Images Without Alt',
      'Total Images',
    ];

    const rows = pages.map((p) => {
      const cleanUrl = p.url.replace(/\/$/, '');
      const cleanCanon = (p.canonical_url || '').replace(/\/$/, '');
      const canonStatus = !p.canonical_url
        ? 'Missing'
        : cleanUrl === cleanCanon
        ? 'Self-Referencing'
        : 'Points to Different URL';

      return [
        `"${p.url}"`,
        p.status_code,
        p.is_indexable !== false ? 'YES' : 'NO',
        p.inlinks_count ?? 0,
        p.ttfb_ms ? Math.round(p.ttfb_ms) : '',
        `"${p.canonical_url || ''}"`,
        `"${canonStatus}"`,
        `"${(p.title || '').replace(/"/g, '""')}"`,
        (p.title || '').length,
        p.title_pixel_width ?? '',
        p.title_pixel_status ?? 'OPTIMAL',
        `"${((p.h1 && p.h1[0]) || '').replace(/"/g, '""')}"`,
        (p.h1 || []).length,
        p.word_count || 0,
        (p.word_count || 0) < 250 ? 'YES' : 'NO',
        `"${(p.schema_types || []).join('; ')}"`,
        p.images_without_alt ?? 0,
        p.total_images ?? 0,
      ].join(',');
    });

    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `technical-url-appendix-${domain}.csv`);
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
              Diagnostic Appendix
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Enterprise Crawl &amp; Indexability Ledger
            </span>
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-1">
            URL-Level Technical Appendix
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">
            Full tabular audit inventory of all {totalUrls} crawled URLs with HTTP codes, internal inlinks, SERP pixel widths, canonical status, schema, and heading structures.
          </p>
        </div>

        <button
          type="button"
          onClick={handleExportCsv}
          className="px-3 py-1.5 text-xs font-mono font-bold bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded shadow-xs transition-colors flex items-center gap-1.5"
        >
          <span>📥 Export Full Inventory (CSV)</span>
        </button>
      </div>

      {/* Metric Scorecards Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 mt-4 font-mono text-xs">
        <div className="p-2 bg-slate-50 border border-slate-200 rounded">
          <span className="text-[9px] text-slate-500 uppercase">Total Crawled</span>
          <p className="text-sm font-bold text-slate-900 mt-0.5">{totalUrls}</p>
        </div>
        <div className="p-2 bg-emerald-50 border border-emerald-200 rounded">
          <span className="text-[9px] text-emerald-800 uppercase">200 OK</span>
          <p className="text-sm font-bold text-emerald-950 mt-0.5">{okCount}</p>
        </div>
        <div className="p-2 bg-blue-50 border border-blue-200 rounded">
          <span className="text-[9px] text-blue-800 uppercase">Redirects (3xx)</span>
          <p className="text-sm font-bold text-blue-950 mt-0.5">{redirectCount}</p>
        </div>
        <div className="p-2 bg-red-50 border border-red-200 rounded">
          <span className="text-[9px] text-red-800 uppercase">Errors (4xx/5xx)</span>
          <p className="text-sm font-bold text-red-950 mt-0.5">{errorCount}</p>
        </div>
        <div className="p-2 bg-amber-50 border border-amber-200 rounded">
          <span className="text-[9px] text-amber-800 uppercase">Canonical Issues</span>
          <p className="text-sm font-bold text-amber-950 mt-0.5">{canonicalIssueCount}</p>
        </div>
        <div className="p-2 bg-purple-50 border border-purple-200 rounded">
          <span className="text-[9px] text-purple-800 uppercase">Thin Content</span>
          <p className="text-sm font-bold text-purple-950 mt-0.5">{thinContentCount}</p>
        </div>
        <div className="p-2 bg-orange-50 border border-orange-200 rounded">
          <span className="text-[9px] text-orange-800 uppercase">SERP Truncated</span>
          <p className="text-sm font-bold text-orange-950 mt-0.5">{pixelTruncatedCount}</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 mt-4 pt-2 border-t border-slate-200 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-400 text-[11px] mr-1">Filter:</span>
          {[
            { key: 'ALL', label: `All (${totalUrls})` },
            { key: '200', label: `200 OK (${okCount})` },
            { key: 'REDIRECT', label: `3xx (${redirectCount})` },
            { key: 'ERROR', label: `4xx/5xx (${errorCount})` },
            { key: 'CANONICAL_ISSUE', label: `Non-Canonical (${canonicalIssueCount})` },
            { key: 'MISSING_H1', label: `Missing H1 (${missingH1Count})` },
            { key: 'THIN_CONTENT', label: `Thin Content (${thinContentCount})` },
            { key: 'PIXEL_TRUNCATED', label: `Pixel &gt; 580px (${pixelTruncatedCount})` },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setStatusFilter(item.key as any)}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition-colors ${
                statusFilter === item.key
                  ? 'bg-blue-950 text-white shadow-xs'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              <span dangerouslySetInnerHTML={{ __html: item.label }} />
            </button>
          ))}
        </div>

        <div className="w-full sm:w-64">
          <input
            type="text"
            placeholder="Search URL, title, or H1..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-2.5 py-1 text-xs border border-slate-300 rounded font-sans focus:outline-hidden focus:border-blue-900"
          />
        </div>
      </div>

      {/* Appendix Table */}
      <div className="overflow-x-auto mt-3">
        <table className="w-full text-left text-xs border-collapse font-sans">
          <thead>
            <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 font-mono text-[11px]">
              <th className="py-2 px-2.5 font-bold w-1/4">URL &amp; Path</th>
              <th className="py-2 px-2.5 font-bold text-center">Status</th>
              <th className="py-2 px-2.5 font-bold text-center">Indexable</th>
              <th className="py-2 px-2.5 font-bold text-center">Inlinks</th>
              <th className="py-2 px-2.5 font-bold text-center">TTFB</th>
              <th className="py-2 px-2.5 font-bold">Canonical Status</th>
              <th className="py-2 px-2.5 font-bold w-1/4">Title &amp; Pixel Width</th>
              <th className="py-2 px-2.5 font-bold">Primary H1</th>
              <th className="py-2 px-2.5 font-bold">Schema</th>
              <th className="py-2 px-2.5 font-bold text-right">Words</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 font-mono text-[11px]">
            {filteredPages.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-6 text-center text-slate-400 font-sans italic">
                  No URLs match the selected filter criteria.
                </td>
              </tr>
            ) : (
              filteredPages.map((p, idx) => {
                const cleanUrl = p.url.replace(/\/$/, '');
                const cleanCanon = (p.canonical_url || '').replace(/\/$/, '');
                const canonStatus = !p.canonical_url
                  ? 'MISSING'
                  : cleanUrl === cleanCanon
                  ? 'SELF'
                  : 'MISMATCH';

                const statusColor =
                  p.status_code >= 200 && p.status_code < 300
                    ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                    : p.status_code >= 300 && p.status_code < 400
                    ? 'bg-blue-100 text-blue-900 border-blue-300'
                    : 'bg-red-100 text-red-900 border-red-300';

                const ttfbColor =
                  (p.ttfb_ms || 0) < 500
                    ? 'text-emerald-800'
                    : (p.ttfb_ms || 0) < 1000
                    ? 'text-amber-800 font-bold'
                    : 'text-red-800 font-bold';

                const pathDisplay = p.url.replace(/^https?:\/\/[^/]+/, '') || '/';
                const pixelWidth = p.title_pixel_width || (p.title ? Math.round(p.title.length * 9.5) : 0);
                const isPixelTruncated = pixelWidth > 580;
                const isThin = (p.word_count || 0) < 250;

                return (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    {/* URL Path */}
                    <td className="py-2 px-2.5 max-w-[220px]">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-bold text-blue-900 hover:underline truncate block"
                        title={p.url}
                      >
                        {pathDisplay}
                      </a>
                      <span className="text-[9px] text-slate-400 truncate block">
                        {p.url}
                      </span>
                    </td>

                    {/* Status Code */}
                    <td className="py-2 px-2.5 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${statusColor}`}>
                        {p.status_code}
                      </span>
                    </td>

                    {/* Indexable */}
                    <td className="py-2 px-2.5 text-center">
                      <span
                        className={`text-[9px] px-1 py-0.5 rounded font-bold ${
                          p.is_indexable !== false
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : 'bg-red-50 text-red-800 border border-red-200'
                        }`}
                      >
                        {p.is_indexable !== false ? 'Indexable' : 'Blocked'}
                      </span>
                    </td>

                    {/* Inlinks */}
                    <td className="py-2 px-2.5 text-center font-bold text-slate-700">
                      {p.inlinks_count ?? 0}
                    </td>

                    {/* TTFB */}
                    <td className={`py-2 px-2.5 text-center ${ttfbColor}`}>
                      {p.ttfb_ms ? `${Math.round(p.ttfb_ms)}ms` : '—'}
                    </td>

                    {/* Canonical Status */}
                    <td className="py-2 px-2.5">
                      {canonStatus === 'SELF' ? (
                        <span className="text-[10px] text-emerald-800 font-semibold">
                          ✓ Self
                        </span>
                      ) : canonStatus === 'MISSING' ? (
                        <span className="text-[10px] text-amber-800 font-semibold bg-amber-50 px-1 py-0.5 rounded border border-amber-200">
                          Missing
                        </span>
                      ) : (
                        <div className="max-w-[140px]">
                          <span className="text-[9px] font-bold text-amber-900 bg-amber-50 px-1 py-0.5 rounded border border-amber-300 block mb-0.5">
                            Points to:
                          </span>
                          <span
                            className="text-[9px] text-slate-500 font-mono truncate block"
                            title={p.canonical_url}
                          >
                            {p.canonical_url?.replace(/^https?:\/\/[^/]+/, '') || p.canonical_url}
                          </span>
                        </div>
                      )}
                    </td>

                    {/* Title & SERP Pixel Width */}
                    <td className="py-2 px-2.5 font-sans max-w-[220px]">
                      <p className="font-bold text-slate-900 text-[11px] truncate" title={p.title || 'No Title'}>
                        {p.title || <span className="text-red-600 italic">Missing Title</span>}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span
                          className={`font-mono text-[9px] px-1 py-0.2 rounded font-semibold ${
                            isPixelTruncated
                              ? 'bg-red-50 text-red-700 border border-red-200'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {pixelWidth}px {isPixelTruncated ? '⚠️ Truncated' : '✓'}
                        </span>
                        <span className="text-[9px] text-slate-400 font-mono">
                          ({(p.title || '').length}ch)
                        </span>
                      </div>
                    </td>

                    {/* Primary H1 */}
                    <td className="py-2 px-2.5 font-sans max-w-[160px]">
                      <p className="text-slate-700 text-[10px] truncate" title={(p.h1 && p.h1[0]) || 'No H1'}>
                        {(p.h1 && p.h1[0]) || <span className="text-amber-700 italic font-mono text-[9px]">✕ Missing H1</span>}
                      </p>
                    </td>

                    {/* Schema Types */}
                    <td className="py-2 px-2.5">
                      {(p.schema_types || []).length > 0 ? (
                        <div className="flex flex-wrap gap-0.5 max-w-[120px]">
                          {p.schema_types.slice(0, 2).map((s, sIdx) => (
                            <span
                              key={sIdx}
                              className="px-1 py-0.2 rounded bg-blue-50 border border-blue-200 text-blue-900 text-[8px] font-mono"
                            >
                              {s}
                            </span>
                          ))}
                          {p.schema_types.length > 2 && (
                            <span className="text-[8px] text-slate-400 font-mono">
                              +{p.schema_types.length - 2}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-400 italic">None</span>
                      )}
                    </td>

                    {/* Words */}
                    <td className="py-2 px-2.5 text-right font-mono text-[10px]">
                      <span className={isThin ? 'text-amber-700 font-bold bg-amber-50 px-1 py-0.5 rounded border border-amber-200' : 'text-slate-700'}>
                        {p.word_count || 0}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Details */}
      <div className="mt-4 pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500">
        <span>
          Showing {filteredPages.length} of {totalUrls} URLs
        </span>
        <span>
          Audited against Screaming Frog &amp; Ahrefs parity · <strong className="text-slate-800">Dristik Methodology v2.2</strong>
        </span>
      </div>
    </div>
  );
}


