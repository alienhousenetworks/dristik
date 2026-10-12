import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter06PageByPageProps {
  theme: ReportTheme;
  report: NormalizedReport;
  pageNumber?: number | string;
  chapterNumber?: string;
}

export function Chapter06PageByPage({
  theme,
  report,
  pageNumber,
  chapterNumber = '06',
}: Chapter06PageByPageProps) {
  const { pages, meta } = report;
  const detailsPageNumber = typeof pageNumber === 'number' ? pageNumber + 1 : pageNumber;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber={chapterNumber}
        subtitle="SAMPLED ROUTE INVENTORY"
        title="Page-by-Page Audit Review"
        description={`Review of the ${meta.pagesAnalyzed} analyzed URL${meta.pagesAnalyzed === 1 ? '' : 's'}${meta.discoveredUrlsCount != null ? ` out of ${meta.discoveredUrlsCount} discovered` : ''}. This is the sample, not a site-wide inventory.`}
        domain={meta.domain}
        whyThisMatters="Systemic indexation failures frequently originate on specific high-value sub-routes. Granular route audits prevent individual weak links from diluting overall domain discoverability."
        howWeMeasuredIt="Per-URL DOM extraction, HTTP header validation, TTFB network telemetry, and section-by-section copywriting analysis."
        whatWasAnalyzed="Status codes, word counts, TTFB latency, SEO & Copy scores, title/meta length compliance, and AI citation snippet targets."
        pageNumber={typeof pageNumber === 'number' ? pageNumber : undefined}
      />

      {/* 2. Page Inventory Breakdown */}
      <section
        id="ch_page_by_page"
        data-chapter-id="ch_page_by_page"
        className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
      >
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="06 / PAGE AUDIT // ROUTE INVENTORY & SERP PAIRS"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Sampled Origin Routes
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              URL-Level Diagnostics &amp; Rewrites
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
            <p className="text-[8pt] text-ink-600 font-sans mt-2">
              {meta.discoveredUrlsCount != null
                ? `${meta.pagesAnalyzed} of ${meta.discoveredUrlsCount} discovered URLs are in this inventory.`
                : `${meta.pagesAnalyzed} analyzed URL${meta.pagesAnalyzed === 1 ? '' : 's'}. The crawl did not record a discovered-URL total.`}
              {' '}Findings in this chapter apply to these URLs only.
            </p>
          </div>

          <div className="space-y-4">
            {pages.inventory.slice(0, 4).map((p, idx) => (
              <div
                key={p.url}
                className="report-avoid-break p-4 border border-line rounded bg-paper-50 space-y-3 text-[8pt]"
              >
                {/* Header */}
                <div className="flex flex-wrap items-center justify-between pb-2 border-b border-line gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded bg-ink text-white">
                      PAGE #{idx + 1}
                    </span>
                    <span className="font-mono font-bold text-[9pt] text-ink">
                      {p.path}
                    </span>
                    <span className="font-mono text-[7.5pt] text-ink-500 uppercase">
                      ({p.pageType})
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-[7.5pt]">
                    <span>Status: <strong>{p.statusCode != null ? p.statusCode : 'Not recorded'}</strong></span>
                    <span>Words: <strong>{p.wordCount}</strong></span>
                    <span>TTFB: <strong>{p.ttfbMs ? `${Math.round(p.ttfbMs)}ms` : '—'}</strong></span>
                    {p.seoScore != null && (
                      <span className="text-ink font-bold">SEO: {p.seoScore}/100</span>
                    )}
                    {p.copyScore != null && (
                      <span className="text-good font-bold">Copy: {p.copyScore}/100</span>
                    )}
                  </div>
                </div>

                {/* Hook & Snippet */}
                {(p.hook || p.geoSnippet) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-2.5 bg-paper-100 rounded border border-line text-[8pt]">
                    {p.hook && (
                      <div>
                        <span className="font-mono text-[7pt] font-bold uppercase text-ink-500 block mb-0.5">
                          3-Second First Impression Hook:
                        </span>
                        <p className="font-sans italic text-ink leading-snug">
                          "{p.hook}"
                        </p>
                      </div>
                    )}
                    {p.geoSnippet && (
                      <div>
                        <span className="font-mono text-[7pt] font-bold uppercase text-good block mb-0.5">
                          Direct AI Citation Snippet (GEO):
                        </span>
                        <p className="font-mono text-[7.5pt] text-ink-700 bg-paper-50 p-1.5 rounded border border-line">
                          "{p.geoSnippet}"
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Current vs Suggested SERP Metadata */}
                <div className="border border-line rounded divide-y divide-line bg-paper-100">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div>
                      <span className="font-mono text-[7pt] uppercase text-ink-400 block">Current SERP Title:</span>
                      <p className="text-ink-700 italic truncate">{p.currentTitle || 'Default or missing title'}</p>
                    </div>
                    <div>
                      <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended Title:</span>
                      <p className="text-ink font-medium truncate">{p.suggestedTitle || `${meta.brandName} | Official Enterprise Architecture`}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div>
                      <span className="font-mono text-[7pt] uppercase text-ink-400 block">Current Description:</span>
                      <p className="text-ink-600 line-clamp-2 leading-tight">{p.currentDescription || 'No description tag observed.'}</p>
                    </div>
                    <div>
                      <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended Description:</span>
                      <p className="text-ink line-clamp-2 leading-tight font-medium">{p.suggestedDescription || `Official platform specifications, enterprise documentation, and capabilities for ${meta.brandName}.`}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={detailsPageNumber}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
