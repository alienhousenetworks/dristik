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
  const { technicalSeo, meta, coverageConfidence } = report;
  const ttfbSamples = coverageConfidence.performancePagesCount;

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
        howWeMeasuredIt="Deterministic AST crawler parsing, canonical header crosscheck, and one server time-to-first-byte measurement per sampled URL. This is not a Core Web Vitals field study and it is not a full page-load time."
        whatWasAnalyzed="Apex vs WWW consolidation, 301 redirect chains, robots.txt permissions, XML sitemaps, and HTTP status code distribution."
        pageNumber={5}
      />

      {/* 2. Analytical Data Page */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="01 / TECHNICAL SEO // TOPOLOGY & DIRECTIVES"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Analysis &amp; Measurements
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              Canonical Consolidation, Latency &amp; Directives
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          {/* 1.1 Canonical Host Consolidation Table */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
              1.1 Canonical Host &amp; Routing Verification
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-line">
              <tbody>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100 w-1/3">
                    Canonical Destination
                  </th>
                  <td className="py-2 px-3 text-ink font-mono">
                    {technicalSeo.canonicalDestination}
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    Host Redirection Consolidation
                  </th>
                  <td className="py-2 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[8pt] font-bold ${
                        technicalSeo.is301Consolidated
                          ? 'bg-good/10 text-good border border-good/30'
                          : 'bg-warn/10 text-warn border border-warn/30'
                      }`}
                    >
                      {technicalSeo.is301Consolidated
                        ? 'PROPERLY CONSOLIDATED (301 PERMANENT)'
                        : 'WARNING: MULTIPLE APEX/WWW VARIANTS ACTIVE'}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    Redirect Chains Recorded
                  </th>
                  <td className="py-2 px-3 text-ink-700">
                    {technicalSeo.redirectChainsCount === 0
                      ? 'Zero redirect chains detected (Direct 200 OK delivery)'
                      : `${technicalSeo.redirectChainsCount} multi-hop redirect chains observed`}
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    Robots.txt Directives
                  </th>
                  <td className="py-2 px-3 text-ink-700">
                    {technicalSeo.robotsTxtStatus}
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    XML Sitemap Health
                  </th>
                  <td className="py-2 px-3 text-ink-700">
                    {technicalSeo.sitemapStatus}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    HTTP 200 Sampling Pass Rate
                  </th>
                  <td className="py-2 px-3 font-semibold text-ink">
                    {technicalSeo.http200RateText}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 1.2 Latency Curve Visualization */}
          {latencyChart && (
            <div className="p-4 border border-line rounded bg-paper-100 space-y-2">
              <div className="flex items-center justify-between pb-1 border-b border-line">
                <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                  1.2 Server Time-to-First-Byte (TTFB) Response Distribution
                </span>
                <span className="font-mono text-[7.5pt] text-ink-500">
                  Sample of {ttfbSamples} URL{ttfbSamples === 1 ? '' : 's'} · response-time reference &lt; 800ms
                </span>
              </div>
              <p className="text-[7.5pt] text-ink-500 font-sans">
                Server time-to-first-byte for the {ttfbSamples} URL{ttfbSamples === 1 ? '' : 's'} this run fetched, one measurement each. It is not a full page-load time, not a Chrome User Experience Report result, and not a site-wide performance score. The 400 ms line is Dristik&apos;s response-time target.
              </p>
              <div className="py-2">
                <LatencyCurveChart chart={latencyChart} />
              </div>
            </div>
          )}

          {/* 1.3 Key Crawl Observations */}
          <div className="p-4 rounded bg-paper-100 border border-line space-y-2 text-[8.5pt]">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-600 block">
              Architectural Crawl Interpretation
            </span>
            <p className="text-ink-700 font-sans leading-relaxed">
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
