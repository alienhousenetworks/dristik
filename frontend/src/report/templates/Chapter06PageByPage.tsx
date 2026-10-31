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
  const hasSpecialistCopy = (item: (typeof pages.inventory)[number]) => Boolean(
    item.suggestedTitle || item.suggestedDescription || item.hook || item.geoSnippet || item.suggestedH1 || item.hero || item.primaryCta || item.bodyRewrite || item.analysis || item.sections?.length || item.faqs?.length
  );
  const writtenPages = pages.inventory.filter(hasSpecialistCopy);
  const shownPages = writtenPages.length > 0 ? writtenPages : pages.inventory.slice(0, 4);

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
        whatWasAnalyzed="Status codes, word counts, TTFB, and the title, description, hook, and section rewrites the page specialist wrote for these URLs."
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
            {shownPages.map((p, idx) => (
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

                {p.analysis && (
                  <p className="text-ink-700 leading-snug">{p.analysis}</p>
                )}

                {/* Current vs Suggested SERP Metadata */}
                <div className="border border-line rounded divide-y divide-line bg-paper-100">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div>
                      <span className="font-mono text-[7pt] uppercase text-ink-400 block">Current SERP Title:</span>
                      <p className="text-ink-700 italic break-words">{p.currentTitle || 'No title tag stored.'}</p>
                    </div>
                    <div>
                      <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended Title:</span>
                      <p className="text-ink font-medium break-words">
                        {p.suggestedTitle || 'The copy specialist did not write a title for this URL.'}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div>
                      <span className="font-mono text-[7pt] uppercase text-ink-400 block">Current Description:</span>
                      <p className="text-ink-600 leading-tight break-words">{p.currentDescription || 'No description tag stored.'}</p>
                    </div>
                    <div>
                      <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended Description:</span>
                      <p className="text-ink leading-tight font-medium break-words">
                        {p.suggestedDescription || 'The copy specialist did not write a description for this URL.'}
                      </p>
                    </div>
                  </div>

                  {(p.suggestedH1 || p.hero || p.primaryCta) && (
                    <div className="grid grid-cols-1 gap-2 p-2">
                      {p.suggestedH1 && (
                        <div>
                          <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended H1:</span>
                          <p className="text-ink font-medium break-words">{p.suggestedH1}</p>
                        </div>
                      )}
                      {p.hero && (
                        <div>
                          <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended hero:</span>
                          <p className="text-ink break-words">{p.hero}</p>
                        </div>
                      )}
                      {p.primaryCta && (
                        <div>
                          <span className="font-mono text-[7pt] uppercase font-bold text-good block">Recommended call to action:</span>
                          <p className="text-ink font-medium break-words">{p.primaryCta}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {p.bodyRewrite && (
                  <div>
                    <span className="font-mono text-[7pt] font-bold uppercase text-ink-500 block mb-0.5">Page rewrite:</span>
                    <p className="text-ink-700 whitespace-pre-wrap leading-snug">{p.bodyRewrite}</p>
                  </div>
                )}

                {p.sections && p.sections.length > 0 && (
                  <div className="space-y-2">
                    <span className="font-mono text-[7pt] font-bold uppercase text-ink-500 block">
                      Copy for the sections on this URL:
                    </span>
                    {p.sections.map((section) => (
                      <div key={`${p.url}-${section.name}`} className="border border-line rounded p-2">
                        <p className="font-semibold text-ink">{section.name}</p>
                        <p className="text-ink-700 whitespace-pre-wrap leading-snug">{section.copy}</p>
                      </div>
                    ))}
                  </div>
                )}

                {p.faqs && p.faqs.length > 0 && (
                  <div className="space-y-1">
                    <span className="font-mono text-[7pt] font-bold uppercase text-ink-500 block">Specialist FAQs:</span>
                    {p.faqs.map((faq) => (
                      <p key={`${p.url}-${faq.question}`} className="text-ink-700 leading-snug">
                        <span className="font-semibold text-ink">Q: {faq.question}</span>
                        {faq.answer ? ` A: ${faq.answer}` : ''}
                      </p>
                    ))}
                  </div>
                )}
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
