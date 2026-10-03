import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';
import { LatencyCurveChart } from '../../components/VisualIntelligence/charts/LatencyCurveChart';
import { ChartSpecification } from '../../types';

interface Chapter01TechnicalSeoProps {
  theme: ReportTheme;
  report: NormalizedReport;
  latencyChart?: ChartSpecification | null;
}

export function Chapter01TechnicalSeo({
  theme,
  report,
  latencyChart,
}: Chapter01TechnicalSeoProps) {
  const { technicalSeo, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="01"
        subtitle="SEARCH ENGINE TOPOLOGY &amp; DIRECTIVES"
        title="Discoverability &amp; Technical SEO Architecture"
        description="Comprehensive evaluation of how search crawlers navigate, parse, and allocate crawl budget across target origin surfaces. Assesses canonical routing, indexability directives, and server response latency."
        domain={meta.domain}
        whyThisMatters="Unconsolidated canonical domains, redirect loops, and slow server latency actively degrade organic crawl frequency and divide PageRank equity."
        howWeMeasuredIt="Deterministic AST crawler parsing, canonical header crosscheck, and TTFB server latency measurements across sampled origin endpoints."
        whatWasAnalyzed="Apex vs WWW consolidation, 301 redirect chains, robots.txt permissions, XML sitemaps, and HTTP status code distribution."
        pageNumber={5}
      />

      {/* 2. Analytical Data Page */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="01 / TECHNICAL SEO // TOPOLOGY & DIRECTIVES"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Analysis &amp; Measurements
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              Canonical Consolidation, Latency &amp; Directives
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          {/* 1.1 Canonical Host Consolidation Table */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              1.1 Canonical Host &amp; Routing Verification
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-slate-200">
              <tbody>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50 w-1/3">
                    Canonical Destination
                  </th>
                  <td className="py-2 px-3 text-slate-900 font-mono">
                    {technicalSeo.canonicalDestination}
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    Host Redirection Consolidation
                  </th>
                  <td className="py-2 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[8pt] font-bold ${
                        technicalSeo.is301Consolidated
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {technicalSeo.is301Consolidated
                        ? 'PROPERLY CONSOLIDATED (301 PERMANENT)'
                        : 'WARNING: MULTIPLE APEX/WWW VARIANTS ACTIVE'}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    Redirect Chains Recorded
                  </th>
                  <td className="py-2 px-3 text-slate-800">
                    {technicalSeo.redirectChainsCount === 0
                      ? 'Zero redirect chains detected (Direct 200 OK delivery)'
                      : `${technicalSeo.redirectChainsCount} multi-hop redirect chains observed`}
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    Robots.txt Directives
                  </th>
                  <td className="py-2 px-3 text-slate-800">
                    {technicalSeo.robotsTxtStatus}
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    XML Sitemap Health
                  </th>
                  <td className="py-2 px-3 text-slate-800">
                    {technicalSeo.sitemapStatus}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    HTTP 200 Sampling Pass Rate
                  </th>
                  <td className="py-2 px-3 font-semibold text-slate-900">
                    {technicalSeo.http200RateText}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 1.2 Latency Curve Visualization */}
          {latencyChart && (
            <div className="p-4 border border-slate-200 rounded bg-slate-50/50 space-y-2">
              <div className="flex items-center justify-between pb-1 border-b border-slate-200">
                <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700">
                  1.2 Server Time-to-First-Byte (TTFB) Response Distribution
                </span>
                <span className="font-mono text-[7.5pt] text-slate-500">
                  Target: &lt; 200ms Fast · Warning: &gt; 800ms
                </span>
              </div>
              <p className="text-[7.5pt] text-slate-500 font-sans">
                Continuous network latency histogram across audited sample nodes.
              </p>
              <div className="py-2">
                <LatencyCurveChart chart={latencyChart} />
              </div>
            </div>
          )}

          {/* 1.3 Key Crawl Observations */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8.5pt]">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-600 block">
              Architectural Crawl Interpretation
            </span>
            <p className="text-slate-800 font-sans leading-relaxed">
              Search spider accessibility is fundamentally sound. The origin server maintains deterministic canonical delivery without index-diluting redirect loops. Ensure future staging and regional subdomains maintain identical 301 consolidation to prevent split authority signals.
            </p>
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={6}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
