import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter02GeoProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function Chapter02Geo({ theme, report }: Chapter02GeoProps) {
  const { geo, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="02"
        subtitle="LAYER 1 DOM EXTRACTABILITY &amp; LLM GROUNDING"
        title="Generative Engine Optimization (GEO)"
        description="First-party DOM content analysis evaluating how effectively generative answer engines can parse, quote, and ground factual commercial statements about the business without hallucination."
        domain={meta.domain}
        whyThisMatters="Answer engines like ChatGPT, Claude, and Perplexity rely on dense, unambiguous factual prose. Marketing hyperbole causes retrieval truncation and competitor substitution."
        howWeMeasuredIt="Deterministic 8-dimension AST extractability breakdown, crawler manifesto inspection, and passage attribution cross-referencing."
        whatWasAnalyzed="First-party DOM clarity, llms.txt availability, AI bot permissions (GPTBot, ClaudeBot, PerplexityBot), and sentence-level entity rewrites."
        pageNumber={7}
      />

      {/* 2. Analytical Data Page */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="02 / GENERATIVE VISIBILITY // LAYER 1 DOM EXTRACTABILITY"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Diagnostic Measurements
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              DOM Extractability &amp; Entity Attribution
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          {/* 2.1 8-Dimension Extractability Breakdown */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              2.1 The 8-Dimension Extractability Framework
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[8.5pt]">
              {geo.dimensions.map((dim) => (
                <div key={dim.key} className="p-3 border border-slate-200 rounded bg-slate-50 space-y-1">
                  <div className="flex items-center justify-between pb-1 border-b border-slate-200">
                    <span className="font-serif font-bold text-slate-900 text-[9pt]">
                      {dim.label}
                    </span>
                    <span
                      className={`font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded ${
                        dim.band === 'HIGH' || dim.band === 'PASS'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : dim.band === 'PARTIAL' || dim.band === 'MODERATE'
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}
                    >
                      {dim.band}
                    </span>
                  </div>
                  <p className="text-slate-700 leading-relaxed font-sans pt-1">
                    {dim.summary}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 2.2 AI Bot Crawler Permissions & llms.txt */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              2.2 AI Crawler Permissions &amp; /llms.txt Directive Health
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-slate-200">
              <tbody>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50 w-1/3">
                    /llms.txt Direct Answer Manifesto
                  </th>
                  <td className="py-2 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[8pt] font-bold ${
                        geo.llmsTxtFound
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {geo.llmsTxtFound
                        ? 'DETECTED & ACCESSIBLE'
                        : 'MISSING (Recommendation: Publish /llms.txt for curated model grounding)'}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    GPTBot Permission (OpenAI)
                  </th>
                  <td className="py-2 px-3 text-slate-800 font-mono text-[8pt]">
                    {geo.botDirectives.gptBot}
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    ClaudeBot Permission (Anthropic)
                  </th>
                  <td className="py-2 px-3 text-slate-800 font-mono text-[8pt]">
                    {geo.botDirectives.claudeBot}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    PerplexityBot Permission
                  </th>
                  <td className="py-2 px-3 text-slate-800 font-mono text-[8pt]">
                    {geo.botDirectives.perplexityBot}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 2.3 Factual Entity Attribution Recommendations */}
          {geo.attributionRewrites.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
                2.3 Factual Entity Attribution Recommendations
              </h3>
              <p className="text-[7.5pt] text-slate-500 font-sans">
                Transforms ambiguous marketing prose into attributed factual statements that RAG engines can directly extract into answer cards.
              </p>

              <div className="space-y-3">
                {geo.attributionRewrites.slice(0, 2).map((rw, idx) => (
                  <div key={idx} className="p-3 border border-slate-200 rounded bg-slate-50 text-[8.5pt] space-y-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-2.5 bg-rose-50/60 border border-rose-200 rounded">
                        <span className="font-mono text-[7.5pt] font-bold text-rose-800 uppercase block mb-1">
                          Current Observed Passage:
                        </span>
                        <p className="text-slate-800 italic font-sans leading-relaxed">
                          "{rw.currentPassage}"
                        </p>
                      </div>
                      <div className="p-2.5 bg-emerald-50/60 border border-emerald-200 rounded">
                        <span className="font-mono text-[7.5pt] font-bold text-emerald-800 uppercase block mb-1">
                          Recommended Attributed Rewrite:
                        </span>
                        <p className="text-slate-950 font-medium font-sans leading-relaxed">
                          "{rw.recommendedRewrite}"
                        </p>
                      </div>
                    </div>
                    {rw.why && (
                      <p className="text-[7.5pt] text-slate-600 font-sans">
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
          pageNumber={8}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
