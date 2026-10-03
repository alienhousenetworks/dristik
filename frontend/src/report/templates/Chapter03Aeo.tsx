import React, { useState } from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';
import { EngineComparisonBarChart } from '../../components/VisualIntelligence/charts/EngineComparisonBarChart';
import { ChartSpecification } from '../../types';

interface Chapter03AeoProps {
  theme: ReportTheme;
  report: NormalizedReport;
  engineChart?: ChartSpecification | null;
  exhaustiveMode?: boolean;
}

export function Chapter03Aeo({
  theme,
  report,
  engineChart,
  exhaustiveMode = false,
}: Chapter03AeoProps) {
  const { aeo, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="03"
        subtitle="LAYER 2 LIVE MULTI-MODEL CITATION EVIDENCE"
        title="Answer Engine Visibility &amp; AI Citations"
        description="Empirical live-query analysis measuring whether generative answer engines synthesize, cite, or hallucinate the brand across commercial buyer queries and conversational prompts."
        domain={meta.domain}
        whyThisMatters="Conversational answer engines increasingly intercept decision-makers before traditional search. If an engine cannot ground your value proposition, competitors capture the recommendation."
        howWeMeasuredIt="Live multi-engine query synthesis, citation rate telemetry, 100-question bespoke commercial sandbox testing, and closed-loop before/after patch re-queries."
        whatWasAnalyzed="ChatGPT Search, Perplexity AI, Google AI Overviews, Claude, Gemini, 10 strategic commercial inquiry facets, and empirical citation uplift deltas."
        pageNumber={9}
      />

      {/* 2. Analytical Data Page - Multi-Engine Matrix & Re-Query */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="03 / ANSWER ENGINE VISIBILITY // LIVE AI CITATION MATRIX"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Multi-Model Analysis
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              Per-Engine Citations &amp; Re-Query Uplift
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          {/* Engine Comparison Visual Bar */}
          {engineChart && (
            <div className="p-4 border border-slate-200 rounded bg-slate-50/50 space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block pb-1 border-b border-slate-200">
                Cross-Engine Citability Index vs Enterprise Baseline
              </span>
              <div className="py-2">
                <EngineComparisonBarChart chart={engineChart} />
              </div>
            </div>
          )}

          {/* 3.1 Per-Engine Citation Scorecard Table */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              3.1 Per-Engine AI Visibility Scorecard
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-slate-200">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-left font-mono text-[7.5pt] text-slate-600 uppercase">
                  <th className="py-2 px-3">Answer Engine Profile</th>
                  <th className="py-2 px-3">Citation Score</th>
                  <th className="py-2 px-3">Readiness Status</th>
                  <th className="py-2 px-3">Primary Retrieval Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {aeo.engines.map((eng) => (
                  <tr key={eng.name} className="hover:bg-slate-50/50">
                    <td className="py-2 px-3 font-semibold text-slate-900">
                      {eng.name}
                    </td>
                    <td className="py-2 px-3 font-mono font-bold">
                      {eng.score != null ? `${eng.score}/100` : '—'}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded font-mono text-[7.5pt] font-bold ${
                          eng.status === 'Pass' || eng.status === 'High'
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : 'bg-amber-50 text-amber-800 border border-amber-200'
                        }`}
                      >
                        {eng.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-600 font-mono text-[8pt]">
                      {eng.retrievalSource}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 3.2 Closed-Loop Remediation Re-Query Uplift */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-900">
                3.2 Re-Query After Patch: Grounded Citation Uplift Delta
              </span>
              {aeo.requeryGainPct != null && (
                <span className="font-mono text-[9pt] font-bold px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-300">
                  +{aeo.requeryGainPct}% Net Citability Gain
                </span>
              )}
            </div>

            <p className="text-[8.5pt] text-slate-700 font-sans leading-relaxed">
              Demonstrates verified citation readiness before vs. after injecting deterministic entity schema and character-safe copy. Baseline unassisted queries produced ambiguous answers; post-patch re-queries achieved direct attribution.
            </p>

            {aeo.commercialInquiries.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                {aeo.commercialInquiries.slice(0, 2).map((item) => (
                  <div key={item.question_key} className="p-3 bg-white border border-slate-200 rounded text-[8pt] space-y-1.5">
                    <div className="flex items-center justify-between font-mono text-[7.5pt]">
                      <span className="font-bold text-slate-900">{item.question_title}</span>
                      <span className="text-slate-500">Score: {item.before_score}/10 → {item.after_score ?? item.before_score}/10</span>
                    </div>
                    <p className="text-slate-600 italic font-sans">"{item.buyer_query}"</p>
                    <div className="pt-1 border-t border-slate-100 flex items-center justify-between text-[7.5pt] font-mono">
                      <span>Evidence: <strong>{item.before_evidence_status}</strong></span>
                      <span className="text-emerald-700 font-bold">Post-Patch Grounded</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={10}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>

      {/* 3. Analytical Data Page - Dynamic 100-Question Sandbox Digest */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="03 / ANSWER ENGINE VISIBILITY // 100-QUESTION AI SANDBOX"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Bespoke Commercial Inquiries
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              Dynamic 100-Question AI Sandbox Digest
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          <p className="text-[8.5pt] text-slate-700 font-sans leading-relaxed">
            100 commercial &amp; technical inquiries dynamically synthesized specifically for {meta.brandName}. Every question executes an automated answer-check against crawled first-party DOM evidence to identify extractable answers, citability scores, and citation gaps.
          </p>

          {/* Facets Grid */}
          <div className="space-y-3">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              Citability Readiness Across 10 Strategic Facets
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[8.5pt]">
              {aeo.sandboxFacets.map((facet) => (
                <div key={facet.facetId} className="p-3 border border-slate-200 rounded bg-slate-50 space-y-1.5">
                  <div className="flex items-center justify-between pb-1 border-b border-slate-200">
                    <span className="font-serif font-bold text-slate-900 text-[9pt]">
                      {facet.facetTitle}
                    </span>
                    <span
                      className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded"
                      style={{ backgroundColor: theme.accentTint, color: theme.accentDark }}
                    >
                      {facet.averageCitability}/10 Citability
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-[7.5pt] text-slate-600">
                    <span className="text-emerald-700 font-bold">Answerable: {facet.answerableCount}</span>
                    <span className="text-amber-700 font-bold">Partial: {facet.partialCount}</span>
                    <span className="text-rose-700 font-bold">Gaps: {facet.gapCount}</span>
                  </div>

                  {facet.sampleQuestions.length > 0 && (
                    <div className="pt-1 text-[7.5pt] text-slate-500 font-sans italic border-t border-slate-100">
                      Sample: "{facet.sampleQuestions[0].generated_question}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Exhaustive Question Inventory Note */}
          <div className="p-3 rounded bg-slate-50 border border-slate-200 text-[8pt] font-mono text-slate-600 flex items-center justify-between">
            <span>
              MODE: {exhaustiveMode ? 'EXHAUSTIVE 100-QUESTION AUDIT' : 'EXECUTIVE DIGEST (10 FACETS + TOP CITATION GAPS)'}
            </span>
            <span>Total Evaluated: {aeo.totalSandboxQuestions} Inquiries</span>
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={11}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
