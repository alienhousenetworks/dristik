import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter02GeoProps {
  theme: ReportTheme;
  report: NormalizedReport;
  pageNumber?: number | string;
  chapterNumber?: string;
}

export function Chapter02Geo({
  theme,
  report,
  pageNumber,
  chapterNumber = '02',
}: Chapter02GeoProps) {
  const { geo, meta } = report;
  const detailsPageNumber = typeof pageNumber === 'number' ? pageNumber + 1 : pageNumber;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber={chapterNumber}
        subtitle="LAYER 1 DOM EXTRACTABILITY &amp; LLM GROUNDING"
        title="Generative Engine Optimization (GEO)"
        description="First-party DOM content analysis evaluating how effectively generative answer engines can parse, quote, and ground factual commercial statements about the business without hallucination."
        domain={meta.domain}
        whyThisMatters="Answer engines like ChatGPT, Claude, and Perplexity rely on dense, unambiguous factual prose. Marketing hyperbole causes retrieval truncation and competitor substitution."
        howWeMeasuredIt="Deterministic 8-dimension AST extractability breakdown, crawler manifesto inspection, and passage attribution cross-referencing."
        whatWasAnalyzed="First-party DOM clarity, llms.txt availability, AI bot permissions (GPTBot, ClaudeBot, PerplexityBot), and sentence-level entity rewrites."
        pageNumber={typeof pageNumber === 'number' ? pageNumber : undefined}
      />

      {/* 2. Analytical Data Page */}
      <section
        id="ch_geo"
        data-chapter-id="ch_geo"
        className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
      >
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="02 / GENERATIVE VISIBILITY // LAYER 1 DOM EXTRACTABILITY"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Diagnostic Measurements
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              DOM Extractability &amp; Entity Attribution
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          {/* 2.1 8-Dimension Extractability Breakdown */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
              2.1 The 8-Dimension Extractability Framework
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[8.5pt]">
              {geo.dimensions.length === 0 && (
                <p className="text-ink-600 font-sans md:col-span-2">
                  Extractability dimensions were not scored on this run.
                </p>
              )}
              {geo.dimensions.map((dim) => (
                <div key={dim.key} className="p-3 border border-line rounded bg-paper-100 space-y-1">
                  <div className="flex items-center justify-between pb-1 border-b border-line">
                    <span className="font-sans font-bold text-ink text-[9pt]">
                      {dim.label}
                    </span>
                    <span
                      className={`font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded ${
                        dim.band === 'HIGH' || dim.band === 'PASS'
                          ? 'bg-good/10 text-good border border-good/30'
                          : dim.band === 'PARTIAL' || dim.band === 'MODERATE'
                          ? 'bg-warn/10 text-warn border border-warn/30'
                          : 'bg-bad/10 text-bad border border-bad/30'
                      }`}
                    >
                      {dim.band}
                    </span>
                  </div>
                  <p className="text-ink-700 leading-relaxed font-sans pt-1">
                    {dim.summary}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 2.2 AI Bot Crawler Permissions & llms.txt */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
              2.2 AI Crawler Permissions &amp; /llms.txt Directive Health
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-line">
              <tbody>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100 w-1/3">
                    /llms.txt Direct Answer Manifesto
                  </th>
                  <td className="py-2 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[8pt] font-bold ${
                        geo.llmsTxtFound
                          ? 'bg-good/10 text-good border border-good/30'
                          : 'bg-warn/10 text-warn border border-warn/30'
                      }`}
                    >
                      {geo.llmsTxtFound
                        ? 'DETECTED & ACCESSIBLE'
                        : 'MISSING (Recommendation: Publish /llms.txt for curated model grounding)'}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    GPTBot Permission (OpenAI)
                  </th>
                  <td className="py-2 px-3 text-ink-700 font-mono text-[8pt]">
                    {geo.botDirectives.gptBot}
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    ClaudeBot Permission (Anthropic)
                  </th>
                  <td className="py-2 px-3 text-ink-700 font-mono text-[8pt]">
                    {geo.botDirectives.claudeBot}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    PerplexityBot Permission
                  </th>
                  <td className="py-2 px-3 text-ink-700 font-mono text-[8pt]">
                    {geo.botDirectives.perplexityBot}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 2.3 Factual Entity Attribution Recommendations */}
          {geo.attributionRewrites.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                2.3 Factual Entity Attribution Recommendations
              </h3>
              <p className="text-[7.5pt] text-ink-500 font-sans">
                Transforms ambiguous marketing prose into attributed factual statements that RAG engines can directly extract into answer cards.
              </p>

              <div className="space-y-3">
                {geo.attributionRewrites.slice(0, 2).map((rw, idx) => (
                  <div key={idx} className="p-3 border border-line rounded bg-paper-100 text-[8.5pt] space-y-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-2.5 bg-bad/10 border border-bad/30 rounded">
                        <span className="font-mono text-[7.5pt] font-bold text-bad uppercase block mb-1">
                          Current Observed Passage:
                        </span>
                        <p className="text-ink-700 italic font-sans leading-relaxed">
                          "{rw.currentPassage}"
                        </p>
                      </div>
                      <div className="p-2.5 bg-good/10 border border-good/30 rounded">
                        <span className="font-mono text-[7.5pt] font-bold text-good uppercase block mb-1">
                          Recommended Attributed Rewrite:
                        </span>
                        <p className="text-ink font-medium font-sans leading-relaxed">
                          "{rw.recommendedRewrite}"
                        </p>
                      </div>
                    </div>
                    {rw.why && (
                      <p className="text-[7.5pt] text-ink-600 font-sans">
                        <strong>Rationale:</strong> {rw.why}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
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
