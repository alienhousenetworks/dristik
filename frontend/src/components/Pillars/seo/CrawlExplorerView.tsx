import React, { useMemo, useState } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport, Finding } from '../../../types';
import { UrlInspectionDrawer } from './UrlInspectionDrawer';
import { Download, Eye, Search, X } from 'lucide-react';

interface CrawlExplorerViewProps {
  report: ExecutiveReport;
  onSelectFinding?: (f: Finding) => void;
}

function getIndexabilityState(page: Record<string, any>): 'Indexable' | 'Non-indexable' | 'Unknown' {
  const code = Number(page.status_code ?? 0);
  const robotsMeta = String(page.robots_meta || '').toLowerCase();
  const xRobots = String((page.response_headers || {})['x-robots-tag'] || '').toLowerCase();
  if (robotsMeta.includes('noindex') || xRobots.includes('noindex') || (code >= 300 && code > 0)) {
    return 'Non-indexable';
  }
  if (code >= 200 && code < 300) return 'Indexable';
  return 'Unknown';
}

function getDirectory(url: string): string {
  try {
    const segs = new URL(url).pathname.split('/').filter(Boolean);
    return segs.length > 0 ? `/${segs[0]}` : '/';
  } catch {
    return '/';
  }
}

export function CrawlExplorerView({ report, onSelectFinding }: CrawlExplorerViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | '200' | '3xx' | '4xx' | '5xx'>('ALL');
  const [indexFilter, setIndexFilter] = useState<'ALL' | 'Indexable' | 'Non-indexable' | 'Unknown'>('ALL');
  const [pageTypeFilter, setPageTypeFilter] = useState<string>('ALL');
  const [directoryFilter, setDirectoryFilter] = useState<string>('ALL');
  const [canonicalFilter, setCanonicalFilter] = useState<'ALL' | 'SELF' | 'MISMATCH' | 'MISSING'>('ALL');
  const [titleFilter, setTitleFilter] = useState<'ALL' | 'PRESENT' | 'MISSING'>('ALL');
  const [h1Filter, setH1Filter] = useState<'ALL' | 'PRESENT' | 'MISSING'>('ALL');
  const [schemaFilter, setSchemaFilter] = useState<'ALL' | 'PRESENT' | 'MISSING'>('ALL');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [issueFilter, setIssueFilter] = useState<'ALL' | 'HAS_ISSUES' | 'CLEAN'>('ALL');
  const [depthFilter, setDepthFilter] = useState<'ALL' | '0-1' | '2-3' | '4+'>('ALL');
  const [sitemapFilter, setSitemapFilter] = useState<'ALL' | 'IN_SITEMAP' | 'NOT_IN_SITEMAP'>('ALL');
  const [languageFilter, setLanguageFilter] = useState<string>('ALL');
  const [selectedPage, setSelectedPage] = useState<Record<string, any> | null>(null);

  // Strictly use real crawled pages — NEVER fabricate /about or /contact fallback URLs
  const rawPages = useMemo(() => {
    const list = (report.crawl_manifest?.pages || report.page_reports || []) as Array<Record<string, any>>;
    return list;
  }, [report]);

  const sitemapSet = useMemo(() => {
    const sm = (report.crawl_manifest as any)?.sitemap_urls || [];
    return new Set<string>(Array.isArray(sm) ? sm.map((u: string) => String(u).replace(/\/$/, '')) : []);
  }, [report]);

  const findingsByUrl = useMemo(() => {
    const map = new Map<string, Finding[]>();
    for (const f of report.findings || []) {
      const urls = Array.isArray((f as any).affected_urls)
        ? (f as any).affected_urls
        : (f as any).url
          ? [(f as any).url]
          : [];
      for (const u of urls) {
        const key = String(u).replace(/\/$/, '');
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(f);
      }
    }
    return map;
  }, [report.findings]);

  const directories = useMemo(() => Array.from(new Set(rawPages.map((p) => getDirectory(String(p.url || ''))))).sort(), [rawPages]);
  const pageTypes = useMemo(() => Array.from(new Set(rawPages.map((p) => String(p.page_type || 'page')))).sort(), [rawPages]);
  const languages = useMemo(
    () => Array.from(new Set(rawPages.map((p) => String(p.language || p.html_lang || 'unknown')))).sort(),
    [rawPages]
  );

  const filteredPages = useMemo(() => {
    return rawPages.filter((p) => {
      const url = String(p.url || '');
      const urlKey = url.replace(/\/$/, '');
      const title = String(p.title || '');
      const code = Number(p.status_code ?? 0);
      const indexState = getIndexabilityState(p);
      const h1Count = Array.isArray(p.h1) ? p.h1.length : p.h1 ? 1 : 0;
      const schemaCount = Array.isArray(p.schema_types) ? p.schema_types.length : 0;
      const canonical = String(p.canonical_url || '').trim();
      const urlFindings = findingsByUrl.get(urlKey) || [];
      const depth = typeof p.click_depth === 'number' ? p.click_depth : null;
      const inSitemap = sitemapSet.has(urlKey);

      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!url.toLowerCase().includes(q) && !title.toLowerCase().includes(q)) return false;
      }
      if (statusFilter === '200' && code !== 200) return false;
      if (statusFilter === '3xx' && (code < 300 || code >= 400)) return false;
      if (statusFilter === '4xx' && (code < 400 || code >= 500)) return false;
      if (statusFilter === '5xx' && code < 500) return false;
      if (indexFilter !== 'ALL' && indexState !== indexFilter) return false;
      if (pageTypeFilter !== 'ALL' && String(p.page_type || 'page') !== pageTypeFilter) return false;
      if (directoryFilter !== 'ALL' && getDirectory(url) !== directoryFilter) return false;
      if (languageFilter !== 'ALL' && String(p.language || p.html_lang || 'unknown') !== languageFilter) return false;

      if (canonicalFilter === 'MISSING' && canonical) return false;
      if (canonicalFilter === 'SELF' && (!canonical || canonical.replace(/\/$/, '') !== urlKey)) return false;
      if (canonicalFilter === 'MISMATCH' && (!canonical || canonical.replace(/\/$/, '') === urlKey)) return false;

      if (titleFilter === 'PRESENT' && (!title || title === '—')) return false;
      if (titleFilter === 'MISSING' && title && title !== '—') return false;
      if (h1Filter === 'PRESENT' && h1Count === 0) return false;
      if (h1Filter === 'MISSING' && h1Count > 0) return false;
      if (schemaFilter === 'PRESENT' && schemaCount === 0) return false;
      if (schemaFilter === 'MISSING' && schemaCount > 0) return false;

      if (issueFilter === 'HAS_ISSUES' && urlFindings.length === 0) return false;
      if (issueFilter === 'CLEAN' && urlFindings.length > 0) return false;
      if (severityFilter !== 'ALL' && !urlFindings.some((f) => f.severity === severityFilter)) return false;

      if (depthFilter === '0-1' && (depth == null || depth > 1)) return false;
      if (depthFilter === '2-3' && (depth == null || depth < 2 || depth > 3)) return false;
      if (depthFilter === '4+' && (depth == null || depth < 4)) return false;

      if (sitemapFilter === 'IN_SITEMAP' && !inSitemap) return false;
      if (sitemapFilter === 'NOT_IN_SITEMAP' && inSitemap) return false;

      return true;
    });
  }, [
    rawPages, searchQuery, statusFilter, indexFilter, pageTypeFilter, directoryFilter,
    canonicalFilter, titleFilter, h1Filter, schemaFilter, severityFilter, issueFilter,
    depthFilter, sitemapFilter, languageFilter, findingsByUrl, sitemapSet,
  ]);

  const hasActiveFilters =
    searchQuery !== '' ||
    statusFilter !== 'ALL' ||
    indexFilter !== 'ALL' ||
    pageTypeFilter !== 'ALL' ||
    directoryFilter !== 'ALL' ||
    canonicalFilter !== 'ALL' ||
    titleFilter !== 'ALL' ||
    h1Filter !== 'ALL' ||
    schemaFilter !== 'ALL' ||
    severityFilter !== 'ALL' ||
    issueFilter !== 'ALL' ||
    depthFilter !== 'ALL' ||
    sitemapFilter !== 'ALL' ||
    languageFilter !== 'ALL';

  const clearFilters = () => {
    setSearchQuery('');
    setStatusFilter('ALL');
    setIndexFilter('ALL');
    setPageTypeFilter('ALL');
    setDirectoryFilter('ALL');
    setCanonicalFilter('ALL');
    setTitleFilter('ALL');
    setH1Filter('ALL');
    setSchemaFilter('ALL');
    setSeverityFilter('ALL');
    setIssueFilter('ALL');
    setDepthFilter('ALL');
    setSitemapFilter('ALL');
    setLanguageFilter('ALL');
  };

  const handleExportCsv = () => {
    const headers = ['URL', 'HTTP Status', 'Indexability', 'Canonical', 'Title', 'H1', 'Word Count', 'Crawl Depth', 'Internal Links', 'TTFB ms', 'Findings', 'Last Crawled'];
    const rows = filteredPages.map((p) => {
      const urlKey = String(p.url || '').replace(/\/$/, '');
      const fCount = (findingsByUrl.get(urlKey) || []).length;
      return [
        `"${p.url || ''}"`,
        p.status_code ?? '',
        getIndexabilityState(p),
        `"${p.canonical_url || ''}"`,
        `"${String(p.title || '').replace(/"/g, '""')}"`,
        `"${(Array.isArray(p.h1) ? p.h1.join('; ') : p.h1 || '').replace(/"/g, '""')}"`,
        p.word_count ?? 0,
        p.click_depth ?? '',
        p.internal_links_count ?? (Array.isArray(p.internal_links) ? p.internal_links.length : 0),
        p.ttfb_ms ?? '',
        fCount,
        `"${p.crawled_at || report.generated_at || ''}"`,
      ];
    });
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `dristik-crawl-export-${report.domain}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">Crawl Explorer</h3>
          <p className="text-xs text-ink-500">
            Empirical inventory of {rawPages.length} URL(s) actually crawled and inspected during this audit run.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleExportCsv} className="text-xs">
          <Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV
        </Button>
      </div>

      {/* 13 Filter Controls Toolbar */}
      <div className="p-4 rounded-xl border border-line bg-paper-subtle space-y-3">
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2 text-ink-400" />
            <input
              type="text"
              placeholder="Search URL or title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-line bg-paper text-ink"
            />
          </div>
          <select aria-label="HTTP Status Filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">HTTP: All Status</option>
            <option value="200">200 OK</option>
            <option value="3xx">3xx Redirect</option>
            <option value="4xx">4xx Client Error</option>
            <option value="5xx">5xx Server Error</option>
          </select>
          <select aria-label="Indexability Filter" value={indexFilter} onChange={(e) => setIndexFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Indexability: All</option>
            <option value="Indexable">Indexable</option>
            <option value="Non-indexable">Non-indexable</option>
            <option value="Unknown">Unknown</option>
          </select>
          <select aria-label="Canonical State Filter" value={canonicalFilter} onChange={(e) => setCanonicalFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Canonical: All</option>
            <option value="SELF">Self-referencing</option>
            <option value="MISMATCH">Cross / Mismatch</option>
            <option value="MISSING">Missing Canonical</option>
          </select>
          <select aria-label="Page Type Filter" value={pageTypeFilter} onChange={(e) => setPageTypeFilter(e.target.value)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Page Type: All</option>
            {pageTypes.map((pt) => <option key={pt} value={pt}>{pt}</option>)}
          </select>
          <select aria-label="Directory Filter" value={directoryFilter} onChange={(e) => setDirectoryFilter(e.target.value)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Directory: All</option>
            {directories.map((dir) => <option key={dir} value={dir}>{dir}</option>)}
          </select>
          <select aria-label="Findings Filter" value={issueFilter} onChange={(e) => setIssueFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Findings: All</option>
            <option value="HAS_ISSUES">Has Findings</option>
            <option value="CLEAN">Zero Findings</option>
          </select>
          <select aria-label="Severity Filter" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Severity: All</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select aria-label="Crawl Depth Filter" value={depthFilter} onChange={(e) => setDepthFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Crawl Depth: All</option>
            <option value="0-1">Depth 0–1</option>
            <option value="2-3">Depth 2–3</option>
            <option value="4+">Depth 4+</option>
          </select>
          <select aria-label="Title Filter" value={titleFilter} onChange={(e) => setTitleFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Title: All</option>
            <option value="PRESENT">Title Present</option>
            <option value="MISSING">Title Missing</option>
          </select>
          <select aria-label="H1 Filter" value={h1Filter} onChange={(e) => setH1Filter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">H1: All</option>
            <option value="PRESENT">H1 Present</option>
            <option value="MISSING">H1 Missing</option>
          </select>
          <select aria-label="Schema Filter" value={schemaFilter} onChange={(e) => setSchemaFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Schema: All</option>
            <option value="PRESENT">Has Schema</option>
            <option value="MISSING">No Schema</option>
          </select>
          <select aria-label="Sitemap Filter" value={sitemapFilter} onChange={(e) => setSitemapFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Sitemap: All</option>
            <option value="IN_SITEMAP">In Sitemap</option>
            <option value="NOT_IN_SITEMAP">Not in Sitemap</option>
          </select>
          <select aria-label="Language Filter" value={languageFilter} onChange={(e) => setLanguageFilter(e.target.value)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">Language: All</option>
            {languages.map((lang) => <option key={lang} value={lang}>{lang}</option>)}
          </select>
        </div>

        <div className="flex flex-wrap items-center justify-between text-xs text-ink-500 pt-1 border-t border-line/60">
          <span>
            Showing <strong className="text-ink">{filteredPages.length}</strong> of <strong className="text-ink">{rawPages.length}</strong> crawled pages
          </span>
          {hasActiveFilters && (
            <button onClick={clearFilters} className="text-xs text-primary font-semibold hover:underline flex items-center gap-1">
              <X className="w-3.5 h-3.5" /> Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Full 12-Column Inventory Table */}
      <div className="rounded-xl border border-line bg-paper overflow-x-auto shadow-xs">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-line bg-paper-subtle text-[11px] font-semibold uppercase text-ink-400">
              <th className="py-3 px-3">URL</th>
              <th className="py-3 px-2">HTTP</th>
              <th className="py-3 px-2">Indexability</th>
              <th className="py-3 px-2">Canonical</th>
              <th className="py-3 px-2">Title</th>
              <th className="py-3 px-2">H1</th>
              <th className="py-3 px-2">Words</th>
              <th className="py-3 px-2">Depth</th>
              <th className="py-3 px-2">Inlinks</th>
              <th className="py-3 px-2">Performance</th>
              <th className="py-3 px-2">Findings</th>
              <th className="py-3 px-2">Last Crawled</th>
              <th className="py-3 px-2 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {filteredPages.length === 0 ? (
              <tr>
                <td colSpan={13} className="py-8 text-center text-xs text-ink-500">
                  {rawPages.length === 0 ? 'No crawled URLs recorded in this audit snapshot.' : 'No URLs match the current filter criteria.'}
                </td>
              </tr>
            ) : (
              filteredPages.map((page, idx) => {
                const url = String(page.url || '');
                const urlKey = url.replace(/\/$/, '');
                const statusCode = page.status_code != null ? Number(page.status_code) : null;
                const indexState = getIndexabilityState(page);
                const canonical = String(page.canonical_url || '');
                const title = String(page.title || '—');
                const h1s: string[] = Array.isArray(page.h1) ? page.h1 : page.h1 ? [String(page.h1)] : [];
                const wordCount = Number(page.word_count ?? 0);
                const depth = typeof page.click_depth === 'number' ? page.click_depth : null;
                const inLinks = Number(page.internal_links_count ?? (Array.isArray(page.internal_links) ? page.internal_links.length : 0));
                const ttfb = typeof page.ttfb_ms === 'number' ? `${Math.round(page.ttfb_ms)}ms` : '—';
                const fCount = (findingsByUrl.get(urlKey) || []).length;
                const lastCrawled = page.crawled_at || report.generated_at ? new Date(page.crawled_at || report.generated_at).toLocaleDateString() : '—';

                return (
                  <tr
                    key={url || idx}
                    onClick={() => setSelectedPage(page)}
                    className="hover:bg-paper-subtle/80 cursor-pointer transition-colors group"
                  >
                    <td className="py-3 px-3 font-mono font-medium text-ink max-w-[200px] truncate" title={url}>
                      {url}
                    </td>
                    <td className="py-3 px-2">
                      <Badge tone={statusCode === 200 ? 'good' : statusCode && statusCode >= 400 ? 'bad' : 'warn'}>
                        {statusCode ?? '—'}
                      </Badge>
                    </td>
                    <td className="py-3 px-2">
                      <span className={indexState === 'Indexable' ? 'text-emerald-600 font-medium' : indexState === 'Non-indexable' ? 'text-rose-600 font-medium' : 'text-ink-400'}>
                        {indexState}
                      </span>
                    </td>
                    <td className="py-3 px-2 max-w-[140px] truncate font-mono text-[11px] text-ink-500" title={canonical || 'Missing'}>
                      {canonical ? (canonical.replace(/\/$/, '') === urlKey ? 'Self' : canonical) : <span className="text-amber-600">Missing</span>}
                    </td>
                    <td className="py-3 px-2 max-w-[170px] truncate text-ink-700" title={title}>{title}</td>
                    <td className="py-3 px-2 max-w-[140px] truncate text-ink-600">
                      {h1s.length > 0 ? h1s[0] : <span className="text-rose-500 font-semibold">Missing</span>}
                    </td>
                    <td className="py-3 px-2 font-mono text-ink-600">{wordCount}</td>
                    <td className="py-3 px-2 font-mono text-ink-500">{depth ?? '—'}</td>
                    <td className="py-3 px-2 font-mono text-ink-500">{inLinks}</td>
                    <td className="py-3 px-2 font-mono text-ink-500">{ttfb}</td>
                    <td className="py-3 px-2">
                      <Badge tone={fCount > 0 ? 'warn' : 'good'}>{fCount}</Badge>
                    </td>
                    <td className="py-3 px-2 font-mono text-[11px] text-ink-400">{lastCrawled}</td>
                    <td className="py-3 px-2 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPage(page);
                        }}
                        className="text-xs h-7 px-2"
                      >
                        Inspect <Eye className="w-3 h-3 ml-1" />
                      </Button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {selectedPage && (
        <UrlInspectionDrawer
          page={selectedPage}
          report={report}
          allPages={rawPages}
          onClose={() => setSelectedPage(null)}
          onSelectFinding={onSelectFinding}
        />
      )}
    </div>
  );
}
