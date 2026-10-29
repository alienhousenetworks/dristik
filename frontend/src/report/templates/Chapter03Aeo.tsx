import React from 'react';
import { formatPercentPoints } from '../../lib/format';
import { effectiveAfterScore } from '../../lib/patchAnswerDelta';
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
  pageNumber?: number | string;
  chapterNumber?: string;
}

export function Chapter03Aeo({
  theme,
  report,
  engineChart,
  exhaustiveMode = false,
  pageNumber,
  chapterNumber = '03',
}: Chapter03AeoProps) {
  const { aeo, meta, remediation } = report;
  const { liveObservation, readiness, auditedQuestions } = aeo;
  const displayQuestions = auditedQuestions.slice(0, 8);
  const questionCount = aeo.totalSandboxQuestions;
  const page2 = typeof pageNumber === 'number' ? pageNumber + 1 : pageNumber;
  const page3 = typeof pageNumber === 'number' ? pageNumber + 2 : pageNumber;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber={chapterNumber}
        subtitle="LAYER 2 LIVE CITATION TELEMETRY &amp; DOM EXTRACTABILITY"
        title="Answer Engine Visibility (AEO) &amp; AI Citations"
        description="Comprehensive audit measuring direct answers, question extractability, and live citation visibility across ChatGPT, Perplexity, Gemini, Claude, and Google AIO."
        domain={meta.domain}
        whyThisMatters="When prospects search for solutions in conversational answer engines, visibility depends on concise entity answers and verifiable primary sources."
        howWeMeasuredIt="Evaluated dynamic query intents against target URLs and measured real engine responses where configured."
        whatWasAnalyzed="Direct answer quality, question clustering, citation attribution, and multi-model competitive presence."
        pageNumber={typeof pageNumber === 'number' ? pageNumber : undefined}
      />
      {/* 2. Analytical Data Page - Live Telemetry vs Extractability Matrix */}
      <section
        id="ch_aeo"
        data-chapter-id="ch_aeo"
        className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
      >
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="03 / ANSWER ENGINE VISIBILITY // LIVE CITATIONS VS EXTRACTABILITY"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Multi-Model Analysis
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              Live Citation Observation vs. DOM Extractability
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          {/* Section A: Live Citation Observation */}
          <div className="p-4 border border-line rounded bg-paper-100 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-line">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink">
                3.1 Empirical Live Citation Observation (Direct API Query Telemetry)
              </span>
              <span className="font-mono text-[7.5pt] px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-bold">
                {liveObservation.isMeasured
                  ? 'LIVE MEASURED'
                  : liveObservation.queriesAttempted > 0
                    ? 'ATTEMPTED — NOT COMPLETED'
                    : 'NOT EXECUTED'}
              </span>
            </div>

            <p className="text-[8.5pt] text-ink-700 font-sans leading-relaxed">
              Empirical execution of live conversational prompts asking AI engines to recommend and cite solutions in this domain. Measures actual real-world citation frequency, brand mentions, and link-backs.
            </p>

            {/* Telemetry Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[8.5pt]">
              <div className="p-2.5 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] text-ink-500 block uppercase">Live Citation Rate</span>
                <span className="text-xl font-sans font-bold text-ink block mt-0.5">
                  {formatPercentPoints(liveObservation.liveCitationRatePct)}
                </span>
                <span className="text-[7pt] text-ink-500 block">Direct URL link attribution</span>
              </div>
              <div className="p-2.5 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] text-ink-500 block uppercase">Mention Rate</span>
                <span className="text-xl font-sans font-bold text-ink block mt-0.5">
                  {formatPercentPoints(liveObservation.brandMentionRatePct)}
                </span>
                <span className="text-[7pt] text-ink-500 block">Named in answer text</span>
              </div>
              <div className="p-2.5 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] text-ink-500 block uppercase">Queries completed</span>
                <span className="text-xl font-sans font-bold text-ink block mt-0.5">
                  {liveObservation.queriesExecuted}
                </span>
                <span className="text-[7pt] text-ink-500 block">
                  {liveObservation.queriesAttempted > 0
                    ? `${liveObservation.queriesAttempted} attempted${liveObservation.queriesFailed > 0 ? `, ${liveObservation.queriesFailed} failed` : ''}`
                    : 'No live prompts were sent'}
                </span>
              </div>
              <div className="p-2.5 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] text-ink-500 block uppercase">Engines Measured</span>
                <span className="text-xl font-sans font-bold text-ink block mt-0.5">
                  {liveObservation.engineCount} / {liveObservation.engineDetails.length}
                </span>
                <span className="text-[7pt] text-ink-500 block">Fail-closed unmeasured</span>
              </div>
            </div>

            {/* Per-Engine Live Telemetry Breakdown */}
            <div className="pt-1">
              <table className="w-full text-[8pt] border-collapse border border-line">
                <thead>
                  <tr className="bg-paper-50 border-b border-line text-left font-mono text-[7.5pt] text-ink-600 uppercase">
                    <th className="py-1.5 px-3">Live Engine</th>
                    <th className="py-1.5 px-3">Queries</th>
                    <th className="py-1.5 px-3">Brand Mentioned</th>
                    <th className="py-1.5 px-3">Brand Cited</th>
                    <th className="py-1.5 px-3">Live Citation Rate</th>
                    <th className="py-1.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line bg-paper-50">
                  {liveObservation.engineDetails.map((eng) => (
                    <tr key={eng.engine}>
                      <td className="py-1.5 px-3 font-semibold text-ink">{eng.engine}</td>
                      <td className="py-1.5 px-3 font-mono">{eng.queriesExecuted}</td>
                      <td className="py-1.5 px-3 font-mono">{eng.queriesExecuted > 0 ? `${eng.brandMentioned} (${formatPercentPoints((eng.brandMentioned / eng.queriesExecuted) * 100, 0)})` : '—'}</td>
                      <td className="py-1.5 px-3 font-mono">{eng.queriesExecuted > 0 ? `${eng.brandCited} (${formatPercentPoints((eng.brandCited / eng.queriesExecuted) * 100, 0)})` : '—'}</td>
                      <td className="py-1.5 px-3 font-mono font-bold">{formatPercentPoints(eng.citationRatePct)}</td>
                      <td className="py-1.5 px-3 font-mono text-[7.5pt]">
                        <span className={`inline-block px-1.5 py-0.2 rounded ${eng.status.includes('NOT_EXECUTED') ? 'bg-paper-200 text-ink-600' : 'bg-warn/10 text-warn'}`}>
                          {eng.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section B: Generative Extractability & Readiness */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                3.2 Generative Extractability &amp; Citation Readiness (On-Page Structural Analysis)
              </h3>
              <span className="font-mono text-[7.5pt] text-ink-500 italic">
                On-page extractability. Not a live citation rate.
              </span>
            </div>
            {!aeo.liveObservation.isMeasured && (
              <p className="text-[8pt] text-ink-700 font-sans border border-line bg-paper-100 rounded px-3 py-2">
                No live engine completed a measurement on this run
                {aeo.liveObservation.queriesAttempted > 0 ? ` (${aeo.liveObservation.queriesAttempted} attempted, ${aeo.liveObservation.queriesFailed} failed, ${aeo.liveObservation.queriesExecuted} completed)` : ''}.
                The scores below are on-page readiness for each engine profile. They are not mentions, citations, or a rank.
              </p>
            )}

            <table className="w-full text-[8.5pt] border-collapse border border-line">
              <thead>
                <tr className="bg-paper-100 border-b border-line text-left font-mono text-[7.5pt] text-ink-600 uppercase">
                  <th className="py-2 px-3">Answer Engine Profile</th>
                  <th className="py-2 px-3">Extractability Index</th>
                  <th className="py-2 px-3">Citation Readiness</th>
                  <th className="py-2 px-3">Primary Retrieval Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {aeo.engines.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-3 px-3 text-ink-600 font-sans">
                      No per-engine extractability score was recorded. The GEO pillar is the on-page measurement. It is not a live citation rank.
                    </td>
                  </tr>
                )}
                {aeo.engines.map((eng) => (
                  <tr key={eng.name} className="hover:bg-paper-100">
                    <td className="py-2 px-3 font-semibold text-ink">
                      {eng.name}
                    </td>
                    <td className="py-2 px-3 font-mono font-bold">
                      {eng.score != null ? `${eng.score}/100` : '—'}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded font-mono text-[7.5pt] font-bold ${
                          eng.status === 'Pass' || eng.status === 'High'
                            ? 'bg-good/10 text-good border border-good/30'
                            : 'bg-warn/10 text-warn border border-warn/30'
                        }`}
                      >
                        {eng.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-ink-600 font-mono text-[8pt]">
                      {eng.retrievalSource}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Section C: Closed-Loop Remediation Re-Query Uplift */}
          <div className="p-4 rounded bg-paper-100 border border-line space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-line">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink">
                3.3 Re-Query After Patch: Grounded Citation Uplift Delta
              </span>
              {aeo.requeryGainPct != null && remediation.state === 'VERIFIED' && (
                <span className="font-mono text-[9pt] font-bold px-2.5 py-0.5 rounded bg-good/10 text-good border border-good/30">
                  +{formatPercentPoints(aeo.requeryGainPct, 0)} verified citability change
                </span>
              )}
              {aeo.requeryGainPct != null && remediation.state !== 'VERIFIED' && (
                <span className="font-mono text-[9pt] font-bold px-2.5 py-0.5 rounded bg-warn/10 text-warn border border-warn/30">
                  Projected {formatPercentPoints(aeo.requeryGainPct, 0)} — not verified
                </span>
              )}
            </div>

            <p className="text-[8.5pt] text-ink-700 font-sans leading-relaxed">
              {remediation.state === 'VERIFIED'
                ? 'A recrawl after the applied change confirmed the score movement below.'
                : `${remediation.label}. An after-score on a generated patch is a projection. It is not a live re-query and it is not a verified fix.`}
            </p>

            {aeo.commercialInquiries.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                {aeo.commercialInquiries.slice(0, 2).map((item) => (
                  <div key={item.question_key} className="p-3 bg-paper-50 border border-line rounded text-[8pt] space-y-1.5">
                    <div className="flex items-center justify-between font-mono text-[7.5pt]">
                      <span className="font-bold text-ink">{item.question_title}</span>
                      <span className="text-ink-500">Score: {item.before_score}/10 → {effectiveAfterScore(item) ?? item.before_score}/10</span>
                    </div>
                    <p className="text-ink-600 italic font-sans">"{item.buyer_query}"</p>
                    <div className="pt-1 border-t border-line flex items-center justify-between text-[7.5pt] font-mono">
                      <span>Evidence: <strong>{item.before_evidence_status}</strong></span>
                      <span className={remediation.state === 'VERIFIED' ? 'text-good font-bold' : 'text-warn font-bold'}>
                        {remediation.state === 'VERIFIED' ? 'Verified after recrawl' : remediation.label}
                      </span>
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
          pageNumber={page2}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>

      {/* 3. Analytical Data Page - Dynamic 100-Question Sandbox & Question-Level Audit Table */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="03 / ANSWER ENGINE VISIBILITY // ON-PAGE ANSWERABILITY"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Bespoke Commercial Inquiries
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              On-page answerability ({questionCount} question{questionCount === 1 ? '' : 's'})
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          <p className="text-[8.5pt] text-ink-700 font-sans leading-relaxed">
            {questionCount > 0
              ? `${questionCount} on-page question${questionCount === 1 ? '' : 's'} checked against crawled pages for ${meta.brandName}. This is answerability, not a live citation test. A question with no supporting passage does not receive an answer-confidence score.`
              : `No on-page answerability questions were evaluated for ${meta.brandName}. This is not a 100-question audit.`}
          </p>
          <p className="text-[8pt] text-ink-600 font-mono">
            Question coverage {report.coverageConfidence.questionCoverage.numerator}/{report.coverageConfidence.questionCoverage.denominator}
            {' · '}
            Answerability {report.coverageConfidence.answerability.numerator}/{report.coverageConfidence.answerability.denominator}
            {' · '}
            Claim grounding {report.coverageConfidence.claimGrounding
              ? `${report.coverageConfidence.claimGrounding.numerator}/${report.coverageConfidence.claimGrounding.denominator}`
              : 'not recorded'}
            . These are three different ratios.
          </p>

          {/* Facets Grid */}
          <div className="space-y-3">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
              Citability Readiness Across 10 Strategic Facets
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[8.5pt]">
              {aeo.sandboxFacets.map((facet) => (
                <div key={facet.facetId} className="p-3 border border-line rounded bg-paper-100 space-y-1.5">
                  <div className="flex items-center justify-between pb-1 border-b border-line">
                    <span className="font-sans font-bold text-ink text-[9pt]">
                      {facet.facetTitle}
                    </span>
                    <span
                      className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded"
                    >
                      {facet.averageCitability}/10 Citability
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-[7.5pt] text-ink-600">
                    <span className="text-good font-bold">Answerable: {facet.answerableCount}</span>
                    <span className="text-warn font-bold">Partial: {facet.partialCount}</span>
                    <span className="text-bad font-bold">Gaps: {facet.gapCount}</span>
                  </div>

                  {facet.sampleQuestions.length > 0 && (
                    <div className="pt-1 text-[7.5pt] text-ink-500 font-sans italic border-t border-line">
                      Sample: "{facet.sampleQuestions[0].generated_question}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Question-Level Audit Table (Resolving Issue 2: Transparent, Verifiable Records) */}
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                Audited Inquiry-Level Evidence &amp; Answerability Sample
              </h3>
              <span className="font-mono text-[7.5pt] text-ink-500">
                Showing {displayQuestions.length} of {questionCount} on-page questions
              </span>
            </div>

            <table className="w-full text-[8pt] border-collapse border border-line">
              <thead>
                <tr className="bg-paper-100 border-b border-line text-left font-mono text-[7.5pt] text-ink-600 uppercase">
                  <th className="py-2 px-3 w-1/2">Inquiry / Buyer Prompt</th>
                  <th className="py-2 px-3">Evidence Ref</th>
                  <th className="py-2 px-3">Answerability</th>
                  <th className="py-2 px-3">Citation Ready</th>
                  <th className="py-2 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line bg-paper-50">
                {displayQuestions.map((q) => (
                  <tr key={q.questionId} className="hover:bg-paper-100">
                    <td className="py-2 px-3 text-ink font-sans">
                      <span className="font-mono text-[7pt] text-ink-400 block">{q.questionId} · {q.facet}</span>
                      <span className="font-medium">{q.question}</span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[7.5pt]">
                      <span className={`px-1.5 py-0.5 rounded ${q.evidenceRef === 'No evidence' ? 'bg-bad/10 text-bad border border-bad/30 font-bold' : 'bg-paper-200 text-ink-700'}`}>
                        {q.evidenceRef}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono">
                      <span className={`font-bold ${q.answerabilityPct === 100 ? 'text-good' : (q.answerabilityPct === 50 ? 'text-warn' : 'text-bad')}`}>
                        {formatPercentPoints(q.answerabilityPct, 0)}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`inline-flex px-1.5 py-0.2 rounded font-mono text-[7pt] font-bold ${
                        q.citationReadiness === 'High' ? 'bg-good/10 text-good border border-good/30' : (
                          q.citationReadiness === 'Medium' ? 'bg-warn/10 text-warn border border-warn/30' : 'bg-bad/10 text-bad border border-bad/30'
                        )
                      }`}>
                        {q.citationReadiness}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-ink-600 text-[7.5pt]">
                      {q.confidencePct == null ? '—' : formatPercentPoints(q.confidencePct, 0)}
                      <span className="block text-ink-400">{q.confidenceBasis}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mode Footer */}
          <div className="p-3 rounded bg-paper-100 border border-line text-[8pt] font-mono text-ink-600 flex items-center justify-between">
            <span>
              MODE: {exhaustiveMode ? 'FULL QUESTION LIST' : 'EXECUTIVE SAMPLE OF EVALUATED QUESTIONS'}
            </span>
            <span>On-page questions evaluated: {questionCount}. Live queries attempted: {liveObservation.queriesAttempted}. Completed: {liveObservation.queriesExecuted}.</span>
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={page3}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
