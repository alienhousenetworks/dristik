import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter06PageByPageProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function Chapter06PageByPage({
  theme,
  report,
}: Chapter06PageByPageProps) {
  const { pages, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="06"
        subtitle="EXHAUSTIVE CRAWL INVENTORY &amp; ROUTE BLUEPRINTS"
        title="Page-by-Page Audit Review"
        description="Comprehensive technical analysis of every sampled URL within the audit scope. Compares current SERP metadata against optimized, character-compliant production blueprints."
        domain={meta.domain}
        whyThisMatters="Systemic indexation failures frequently originate on specific high-value sub-routes. Granular route audits prevent individual weak links from diluting overall domain discoverability."
        howWeMeasuredIt="Per-URL DOM extraction, HTTP header validation, TTFB network telemetry, and section-by-section copywriting analysis."
        whatWasAnalyzed="Status codes, word counts, TTFB latency, SEO & Copy scores, title/meta length compliance, and AI citation snippet targets."
        pageNumber={16}
      />

      {/* 2. Page Inventory Breakdown */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="06 / PAGE AUDIT // ROUTE INVENTORY & SERP PAIRS"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Sampled Origin Routes
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              URL-Level Diagnostics &amp; Rewrites
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          <div className="space-y-4">
            {pages.inventory.slice(0, 4).map((p, idx) => (
              <div
                key={p.url}
                className="report-avoid-break p-4 border border-slate-200 rounded bg-white space-y-3 text-[8pt]"
              >
                {/* Header */}
                <div className="flex flex-wrap items-center justify-between pb-2 border-b border-slate-200 gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded bg-slate-900 text-white">
                      PAGE #{idx + 1}
                    </span>
                    <span className="font-mono font-bold text-[9pt] text-slate-900">
                      {p.path}
                    </span>
                    <span className="font-mono text-[7.5pt] text-slate-500 uppercase">
                      ({p.pageType})
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-[7.5pt]">
                    <span>Status: <strong>{p.statusCode != null ? p.statusCode : '200'}</strong></span>
                    <span>Words: <strong>{p.wordCount}</strong></span>
                    <span>TTFB: <strong>{p.ttfbMs ? `${Math.round(p.ttfbMs)}ms` : '—'}</strong></span>
                    {p.seoScore != null && (
                      <span className="text-slate-900 font-bold">SEO: {p.seoScore}/100</span>
                    )}
                    {p.copyScore != null && (
                      <span className="text-emerald-700 font-bold">Copy: {p.copyScore}/100</span>
                    )}
                  </div>
                </div>

                {/* Hook & Snippet */}
                {(p.hook || p.geoSnippet) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-2.5 bg-slate-50 rounded border border-slate-200 text-[8pt]">
                    {p.hook && (
                      <div>
                        <span className="font-mono text-[7pt] font-bold uppercase text-slate-500 block mb-0.5">
                          3-Second First Impression Hook:
                        </span>
                        <p className="font-serif italic text-slate-900 leading-snug">
                          "{p.hook}"
                        </p>
                      </div>
                    )}
                    {p.geoSnippet && (
                      <div>
                        <span className="font-mono text-[7pt] font-bold uppercase text-emerald-800 block mb-0.5">
                          Direct AI Citation Snippet (GEO):
                        </span>
                        <p className="font-mono text-[7.5pt] text-slate-800 bg-white p-1.5 rounded border border-slate-200">
                          "{p.geoSnippet}"
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Current vs Suggested SERP Metadata */}
                <div className="border border-slate-200 rounded divide-y divide-slate-200 bg-slate-50/50">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div>
                      <span className="font-mono text-[7pt] uppercase text-slate-400 block">Current SERP Title:</span>
                      <p className="text-slate-700 italic truncate">{p.currentTitle || 'Default or missing title'}</p>
                    </div>
                    <div>
                      <span className="font-mono text-[7pt] uppercase font-bold text-emerald-800 block">Recommended Title:</span>
                      <p className="text-slate-900 font-medium truncate">{p.suggestedTitle || `${meta.brandName} | Official Enterprise Architecture`}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
                    <div>
                      <span className="font-mono text-[7pt] uppercase text-slate-400 block">Current Description:</span>
                      <p className="text-slate-600 line-clamp-2 leading-tight">{p.currentDescription || 'No description tag observed.'}</p>
                    </div>
                    <div>
                      <span className="font-mono text-[7pt] uppercase font-bold text-emerald-800 block">Recommended Description:</span>
                      <p className="text-slate-900 line-clamp-2 leading-tight font-medium">{p.suggestedDescription || `Official platform specifications, enterprise documentation, and capabilities for ${meta.brandName}.`}</p>
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
          pageNumber={17}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
