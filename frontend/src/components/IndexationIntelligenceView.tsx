import React, { useState, useMemo } from 'react';
import { CrawlManifest, PageEvidence } from '../types';

interface IndexationIntelligenceViewProps {
  manifest?: CrawlManifest;
  pages?: PageEvidence[];
  domain: string;
}

type FilterTab = 'all' | 'indexable' | 'noindex' | 'robots_blocked' | 'soft_404' | 'canonical_mismatch' | 'js_dependent';

export function IndexationIntelligenceView({
  manifest,
  pages: propPages,
  domain,
}: IndexationIntelligenceViewProps) {
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all');
  const [selectedPageForDiff, setSelectedPageForDiff] = useState<any | null>(null);

  const rawRollup = manifest?.indexation_rollup;
  const pagesList = propPages || manifest?.pages || [];

  // Fallback to synthesize page status items if indexation_rollup is not yet loaded
  const statuses = useMemo(() => {
    if (rawRollup?.pages && rawRollup.pages.length > 0) {
      return rawRollup.pages;
    }
    // Client-side synthesis fallback from PageEvidence
    return pagesList.map((p) => {
      const robots = (p.robots_meta || '').toLowerCase();
      const xRobots = (p.x_robots_tag || '').toLowerCase();
      const hasNoindex = robots.includes('noindex') || xRobots.includes('noindex');
      const isCanonSelf = !p.canonical_url || p.canonical_url.replace(/\/$/, '') === p.url.replace(/\/$/, '');
      const isSoft404 = p.status_code === 200 && (
        (p.title || '').toLowerCase().includes('404') ||
        (p.title || '').toLowerCase().includes('not found') ||
        (p.h1 || []).some((h) => h.toLowerCase().includes('404') || h.toLowerCase().includes('not found'))
      );

      const rawWords = p.raw_html ? p.raw_html.split(/\s+/).length : p.word_count;
      const renderedWords = p.word_count || 0;
      const isJsOnly = p.render_mode === 'js_rendered' || (p.raw_html && renderedWords > rawWords * 2 && renderedWords > 40);

      const isIndexable = p.status_code === 200 && !hasNoindex && !isSoft404 && isCanonSelf;

      return {
        url: p.url,
        status_code: p.status_code,
        crawlable: p.status_code < 400,
        indexable: isIndexable,
        indexed_state: 'UNVERIFIED_NO_GSC',
        canonical_declared: p.canonical_url,
        canonical_selected: p.canonical_url || p.url,
        canonical_match: isCanonSelf,
        has_noindex: hasNoindex,
        x_robots_tag: p.x_robots_tag || null,
        robots_blocked: false,
        is_soft_404: isSoft404,
        is_duplicate: false,
        duplicate_of_url: null,
        gsc_coverage_state: null,
        alternate_canonical: isCanonSelf ? null : p.canonical_url,
        is_redirect: p.status_code >= 300 && p.status_code < 400,
        redirect_target: p.final_url,
        is_js_only_content: isJsOnly,
        blocked_resources: [],
        render_delta: {
          raw_word_count: rawWords,
          rendered_word_count: renderedWords,
          word_count_delta: Math.max(0, renderedWords - rawWords),
          raw_headings: p.h1 || [],
          rendered_headings: p.h1 || [],
          js_only_headings: [],
          raw_internal_links: (p.internal_links || []).length,
          rendered_internal_links: (p.internal_links || []).length,
          js_only_links_count: 0,
          js_dependency_risk: isJsOnly ? 'CRITICAL' : 'LOW',
        },
      };
    });
  }, [rawRollup, pagesList]);

  const filteredPages = useMemo(() => {
    switch (activeFilter) {
      case 'indexable':
        return statuses.filter((s: any) => s.indexable);
      case 'noindex':
        return statuses.filter((s: any) => s.has_noindex);
      case 'robots_blocked':
        return statuses.filter((s: any) => s.robots_blocked);
      case 'soft_404':
        return statuses.filter((s: any) => s.is_soft_404);
      case 'canonical_mismatch':
        return statuses.filter((s: any) => !s.canonical_match && s.canonical_declared);
      case 'js_dependent':
        return statuses.filter((s: any) => s.is_js_only_content);
      default:
        return statuses;
    }
  }, [statuses, activeFilter]);

  const stats = useMemo(() => {
    const total = statuses.length;
    const indexable = statuses.filter((s: any) => s.indexable).length;
    const noindex = statuses.filter((s: any) => s.has_noindex).length;
    const blocked = statuses.filter((s: any) => s.robots_blocked).length;
    const soft404 = statuses.filter((s: any) => s.is_soft_404).length;
    const canonMismatch = statuses.filter((s: any) => !s.canonical_match && s.canonical_declared).length;
    const jsDep = statuses.filter((s: any) => s.is_js_only_content).length;

    return { total, indexable, noindex, blocked, soft404, canonMismatch, jsDep };
  }, [statuses]);

  return (
    <div className="space-y-6">
      {/* Overview Stat Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 text-xs">
        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-ink-500 block">Evaluated Pages</span>
          <span className="text-xl font-bold font-mono text-ink block">{stats.total}</span>
          <span className="text-[10px] text-ink-500 block">Crawled corpus</span>
        </div>

        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-good block">Indexable Pages</span>
          <span className="text-xl font-bold font-mono text-good block">{stats.indexable}</span>
          <span className="text-[10px] text-ink-500 block">
            {stats.total ? `${Math.round((stats.indexable / stats.total) * 100)}% of total` : '—'}
          </span>
        </div>

        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-bad block">Noindex Tags</span>
          <span className="text-xl font-bold font-mono text-bad block">{stats.noindex}</span>
          <span className="text-[10px] text-ink-500 block">Meta / X-Robots</span>
        </div>

        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-warn block">Robots Blocked</span>
          <span className="text-xl font-bold font-mono text-warn block">{stats.blocked}</span>
          <span className="text-[10px] text-ink-500 block">Disallow rules</span>
        </div>

        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-warn block">Soft 404 Pages</span>
          <span className="text-xl font-bold font-mono text-warn block">{stats.soft404}</span>
          <span className="text-[10px] text-ink-500 block">HTTP 200 with error copy</span>
        </div>

        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-ink-700 block">Canonical Mismatch</span>
          <span className="text-xl font-bold font-mono text-ink-700 block">{stats.canonMismatch}</span>
          <span className="text-[10px] text-ink-500 block">Alternate declared</span>
        </div>

        <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-3 rounded-lg space-y-1">
          <span className="label text-[10px] text-ink-700 block">JS-Dependent</span>
          <span className="text-xl font-bold font-mono text-ink-700 block">{stats.jsDep}</span>
          <span className="text-[10px] text-ink-500 block">Requires JS rendering</span>
        </div>
      </div>

      {/* Filter Tabs Strip */}
      <div className="flex items-center gap-2 overflow-x-auto border-b border-line pb-2">
        <button
          type="button"
          onClick={() => setActiveFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'all'
              ? 'bg-ink text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-ink'
          }`}
        >
          All ({stats.total})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('indexable')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'indexable'
              ? 'bg-good text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-good'
          }`}
        >
          Indexable ({stats.indexable})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('noindex')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'noindex'
              ? 'bg-bad text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-bad'
          }`}
        >
          Noindex ({stats.noindex})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('robots_blocked')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'robots_blocked'
              ? 'bg-warn text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-warn'
          }`}
        >
          Robots Blocked ({stats.blocked})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('soft_404')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'soft_404'
              ? 'bg-warn text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-warn'
          }`}
        >
          Soft 404 ({stats.soft404})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('canonical_mismatch')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'canonical_mismatch'
              ? 'bg-pine text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-ink'
          }`}
        >
          Canonical Mismatch ({stats.canonMismatch})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('js_dependent')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
            activeFilter === 'js_dependent'
              ? 'bg-pine text-paper-50'
              : 'bg-paper-100 text-ink-600 hover:text-ink'
          }`}
        >
          JS Dependency ({stats.jsDep})
        </button>
      </div>

      {/* Main Indexation Table */}
      <div className="sheet border border-line rounded-lg overflow-hidden">
        <div className="p-4 border-b border-line bg-paper-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h4 className="font-sans font-bold text-ink text-base">Indexation State Machine</h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200 border border-line text-ink-700">
              {filteredPages.length} URLs shown
            </span>
          </div>
          <span className="text-xs text-ink-500 font-mono">16-Point Search Engine Evaluation</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-50 text-ink-500 font-medium">
                <th className="p-3">Page URL</th>
                <th className="p-3">Status</th>
                <th className="p-3">Indexability</th>
                <th className="p-3">Canonical Declared</th>
                <th className="p-3">Robots Directives</th>
                <th className="p-3">Render Delta (Raw vs JS)</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line font-mono">
              {filteredPages.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-ink-500 font-sans">
                    No pages matching the selected filter ({activeFilter}).
                  </td>
                </tr>
              ) : (
                filteredPages.map((page: any, idx: number) => {
                  const delta = page.render_delta;
                  return (
                    <tr key={idx} className="hover:bg-paper-100/50 transition-colors">
                      <td className="p-3 font-sans max-w-xs truncate">
                        <span className="font-semibold text-ink block truncate" title={page.url}>
                          {page.url}
                        </span>
                        {page.is_soft_404 && (
                          <span className="inline-block mt-0.5 text-[9px] px-1.5 py-0.2 rounded bg-warn/15 text-warn font-semibold">
                             Soft 404 Copy Detected
                          </span>
                        )}
                        {page.is_duplicate && (
                          <span className="inline-block mt-0.5 text-[9px] px-1.5 py-0.2 rounded bg-bad/15 text-bad font-semibold">
                             Duplicate of {page.duplicate_of_url}
                          </span>
                        )}
                      </td>

                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                          page.status_code === 200
                            ? 'bg-good/15 text-good'
                            : page.status_code >= 300 && page.status_code < 400
                            ? 'bg-paper-200 text-ink-700'
                            : 'bg-bad/15 text-bad'
                        }`}>
                          {page.status_code}
                        </span>
                      </td>

                      <td className="p-3">
                        {page.indexable ? (
                          <span className="inline-flex items-center gap-1 text-good font-semibold font-sans">
                            <span></span> Indexable
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-bad font-semibold font-sans">
                            <span></span> Non-Indexable
                          </span>
                        )}
                      </td>

                      <td className="p-3 max-w-xs truncate font-sans text-[11px]">
                        {page.canonical_declared ? (
                          <div>
                            <span className="text-ink font-mono block truncate" title={page.canonical_declared}>
                              {page.canonical_declared}
                            </span>
                            {!page.canonical_match && (
                              <span className="text-warn text-[9px] block">
                                ↗ Alternate canonical (mismatch with page URL)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-ink-400 italic">None declared</span>
                        )}
                      </td>

                      <td className="p-3 font-sans text-[11px]">
                        {page.has_noindex && (
                          <span className="px-1.5 py-0.5 rounded bg-bad/15 text-bad font-semibold mr-1">
                            noindex
                          </span>
                        )}
                        {page.robots_blocked && (
                          <span className="px-1.5 py-0.5 rounded bg-warn/15 text-warn font-semibold mr-1">
                            robots.txt blocked
                          </span>
                        )}
                        {page.x_robots_tag && (
                          <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 font-mono text-[10px]">
                            {page.x_robots_tag}
                          </span>
                        )}
                        {!page.has_noindex && !page.robots_blocked && !page.x_robots_tag && (
                          <span className="text-ink-500">Standard Allow</span>
                        )}
                      </td>

                      <td className="p-3 font-sans">
                        {delta ? (
                          <div className="space-y-0.5">
                            <span className="text-[11px] text-ink block">
                              Raw: <strong className="font-mono">{delta.raw_word_count}</strong> w · Rendered:{' '}
                              <strong className="font-mono">{delta.rendered_word_count}</strong> w
                            </span>
                            {delta.js_dependency_risk === 'CRITICAL' && (
                              <span className="text-[9px] font-bold text-bad bg-bad/10 px-1.5 py-0.2 rounded inline-block">
                                 High JS Dependency (+{delta.word_count_delta} words)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-ink-400">—</span>
                        )}
                      </td>

                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedPageForDiff(page)}
                          className="px-2.5 py-1 rounded border border-line bg-paper-50 hover:bg-paper-200 text-ink text-[11px] font-semibold transition-colors cursor-pointer"
                        >
                          Compare DOM
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Side-by-Side Raw HTML vs Rendered DOM Drawer / Modal */}
      {selectedPageForDiff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-xs">
          <div className="bg-paper border border-line rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-line flex items-center justify-between bg-paper-100">
              <div>
                <h3 className="font-sans text-lg font-bold text-ink">
                  Render Delta: Raw HTTP Stream vs Headless Browser DOM
                </h3>
                <span className="text-xs text-ink-500 font-mono truncate block max-w-xl">
                  {selectedPageForDiff.url}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedPageForDiff(null)}
                className="text-ink-500 hover:text-ink p-1.5 rounded-lg border border-line bg-paper-50 transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Summary Metrics Comparison */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="border border-line rounded-lg p-3 bg-paper-50 space-y-1">
                  <span className="label text-[10px] text-ink-500 block">Raw Stream Word Count</span>
                  <span className="text-2xl font-bold font-mono text-ink block">
                    {selectedPageForDiff.render_delta?.raw_word_count ?? '—'}
                  </span>
                  <span className="text-[10px] text-ink-500 block">Seen by simple bots</span>
                </div>

                <div className="border border-line rounded-lg p-3 bg-paper-50 space-y-1">
                  <span className="label text-[10px] text-ink-700 block">Rendered DOM Word Count</span>
                  <span className="text-2xl font-bold font-mono text-ink-700 block">
                    {selectedPageForDiff.render_delta?.rendered_word_count ?? '—'}
                  </span>
                  <span className="text-[10px] text-ink-500 block">Seen after JS execution</span>
                </div>

                <div className="border border-line rounded-lg p-3 bg-paper-50 space-y-1">
                  <span className="label text-[10px] text-bad block">Client JS Dependency Delta</span>
                  <span className="text-2xl font-bold font-mono text-bad block">
                    +{selectedPageForDiff.render_delta?.word_count_delta ?? 0}
                  </span>
                  <span className="text-[10px] text-ink-500 block">
                    Risk: {selectedPageForDiff.render_delta?.js_dependency_risk || 'LOW'}
                  </span>
                </div>
              </div>

              {/* Headings & Content comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                <div className="border border-line rounded-lg p-4 bg-paper-50 space-y-3">
                  <div className="flex items-center justify-between border-b border-line pb-2">
                    <span className="font-semibold text-ink">Raw HTML Headings</span>
                    <span className="text-ink-500 font-mono">
                      {(selectedPageForDiff.render_delta?.raw_headings || []).length} tags
                    </span>
                  </div>
                  <div className="space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto">
                    {(selectedPageForDiff.render_delta?.raw_headings || []).length === 0 ? (
                      <p className="text-ink-400 italic">No headings found in initial raw HTML stream.</p>
                    ) : (
                      selectedPageForDiff.render_delta?.raw_headings.map((h: string, i: number) => (
                        <div key={i} className="p-1.5 bg-paper-100 rounded border border-line">
                          {h}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="border border-line rounded-lg p-4 bg-paper-50 space-y-3">
                  <div className="flex items-center justify-between border-b border-line pb-2">
                    <span className="font-semibold text-ink-700">Rendered DOM Headings (Final)</span>
                    <span className="text-ink-500 font-mono">
                      {(selectedPageForDiff.render_delta?.rendered_headings || []).length} tags
                    </span>
                  </div>
                  <div className="space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto">
                    {(selectedPageForDiff.render_delta?.rendered_headings || []).length === 0 ? (
                      <p className="text-ink-400 italic">No headings found in rendered DOM.</p>
                    ) : (
                      selectedPageForDiff.render_delta?.rendered_headings.map((h: string, i: number) => (
                        <div key={i} className="p-1.5 bg-paper-100 rounded border border-line">
                          {h}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="p-4 bg-paper-100 rounded-lg border border-line text-xs space-y-1">
                <span className="font-semibold text-ink block">Search Engine Crawling Implication:</span>
                <p className="text-ink-700 leading-relaxed">
                  Search engines (Googlebot, Bingbot, and AI crawlers like GPTBot and PerplexityBot) prioritize fast initial HTML streaming. If your main value proposition, headings, and internal navigation depend exclusively on client-side JavaScript execution, pages face indexation delays, missing passage extraction, or total omission from answer engines.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
