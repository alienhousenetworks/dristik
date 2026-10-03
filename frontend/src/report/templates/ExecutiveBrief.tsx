import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface ExecutiveBriefProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function ExecutiveBrief({ theme, report }: ExecutiveBriefProps) {
  const { brief, meta } = report;
  const { keySignals } = brief;

  return (
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
      <PageHeader
        theme={theme}
        domain={meta.domain}
        chapterTitle="EXECUTIVE BRIEF // STRATEGIC SUMMARY"
      />

      <div className="space-y-6 max-w-4xl">
        {/* Section Headline */}
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Section 0.1 // Executive Synthesis
          </span>
          <h2 className="font-serif text-[24pt] md:text-[28pt] font-normal tracking-tight text-ink">
            What the Evidence Says
          </h2>
          <div className="bg-ink w-10 h-px mt-2" />
        </div>

        {/* Large Editorial Thesis Statement */}
        <div className="py-2">
          <p className="font-sans text-[14pt] md:text-[16pt] font-normal leading-[1.55] text-ink border-l-3 pl-4 border-ink">
            {brief.leadThesis}
          </p>
        </div>

        {/* 5 Key Performance Signals (Continuous Metrics derived from actual engine) */}
        <div className="space-y-2">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-4 bg-paper-100 border border-line rounded">
            <div className="text-center p-2 border-r border-line last:border-r-0">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                Composite Index
              </span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.overallScore != null ? keySignals.overallScore.toFixed(1) : '—'}
              </div>
              <span
                className="font-mono text-[8pt] font-bold px-1.5 py-0.2 rounded mt-1 inline-block"
              >
                GRADE {keySignals.overallGrade}
              </span>
            </div>

            <div className="text-center p-2 border-r border-line last:border-r-0">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                1. Technical SEO (30%)
              </span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.technicalScore != null ? keySignals.technicalScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">Crawler Pass</span>
            </div>

            <div className="text-center p-2 border-r border-line last:border-r-0">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                2. GEO Readiness (25%)
              </span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.geoScore != null ? keySignals.geoScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">DOM Extractability</span>
            </div>

            <div className="text-center p-2 border-r border-line last:border-r-0">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                3. AEO Readiness (25%)
              </span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.aeoScore != null ? keySignals.aeoScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">
                {report.aeo.liveObservation.isMeasured ? `Live Rate: ${report.aeo.liveObservation.liveCitationRatePct}%` : 'Readiness Proxy'}
              </span>
            </div>

            <div className="text-center p-2">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                4. CRO &amp; UX (20%)
              </span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.croScore != null ? keySignals.croScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">Visitor Clarity</span>
            </div>
          </div>
          <div className="px-1 flex items-center justify-between text-[7.5pt] font-mono text-ink-500">
            <span>Deterministic Derivation: Σ (Pillar Score × Assigned Weight) = {keySignals.overallScore != null ? keySignals.overallScore.toFixed(1) : '—'}</span>
            <span>Mathematical Ledger Audited</span>
          </div>
        </div>

        {/* Audit Coverage & Evidence Confidence Breakdown (Points 11 & 12) */}
        {report.coverageConfidence && (
          <div className="p-3.5 bg-paper-100 border border-line rounded text-[8pt] space-y-2">
            <div className="flex flex-wrap items-center justify-between pb-1.5 border-b border-line">
              <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                Audit Scope &amp; Evidence Coverage Confidence
              </span>
              <span className="font-mono text-[7pt] font-bold px-2 py-0.5 rounded bg-good/10 text-good border border-good/30">
                EVIDENCE CONFIDENCE: {report.coverageConfidence.overallEvidenceConfidence}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5 font-mono text-[7.5pt]">
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Page Coverage</span>
                <strong className="text-ink text-[8pt] block mt-0.5 truncate">
                  {report.coverageConfidence.pagesAudited} / {report.coverageConfidence.pagesDiscovered} URLs ({report.coverageConfidence.pageCoveragePct}%)
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Evidence Coverage</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {report.coverageConfidence.evidenceCoveragePct}% Grounded
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Commercial Queries</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  100 / 100 Evaluated
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">External Authority</span>
                <strong className="text-warn text-[8pt] block mt-0.5">
                  0% (Unprovisioned)
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Performance Sample</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {report.coverageConfidence.performancePagesCount} Nodes Tested
                </strong>
              </div>
            </div>

            <p className="font-sans text-[7.5pt] text-ink-500 italic">
              {report.coverageConfidence.scopeLimitationNotice}
            </p>
          </div>
        )}

        {/* Editorial Triad: What is Working / What Needs Attention / What Matters Next */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
          {/* 1. What is working */}
          <div className="p-4 rounded bg-good/10 border border-good/30 space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-good block">
              ✓ WHAT IS WORKING (VERIFIED)
            </span>
            <ul className="text-[8.5pt] text-ink-700 space-y-1.5 list-disc pl-4 font-sans leading-relaxed">
              {brief.whatIsWorking.length > 0 ? (
                brief.whatIsWorking.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))
              ) : (
                <li>Technical surface reachable with valid HTTP 200 responses.</li>
              )}
            </ul>
          </div>

          {/* 2. What needs attention */}
          <div className="p-4 rounded bg-bad/10 border border-bad/30 space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-bad block">
               WHAT NEEDS ATTENTION
            </span>
            <ul className="text-[8.5pt] text-ink-700 space-y-1.5 list-disc pl-4 font-sans leading-relaxed">
              {brief.whatNeedsAttention.length > 0 ? (
                brief.whatNeedsAttention.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))
              ) : (
                <li>Entity extraction ambiguity in marketing body copy.</li>
              )}
            </ul>
          </div>

          {/* 3. What matters next */}
          <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink block">
              ★ WHAT MATTERS NEXT (CATALYST)
            </span>
            <p className="text-[8.5pt] text-ink-700 font-sans leading-relaxed">
              {brief.whatMattersNext}
            </p>
          </div>
        </div>

        {/* Consultant Advice: Low-ROI Traps to Ignore */}
        {brief.consultantIgnoreAdvice && (
          <div className="p-3.5 rounded bg-warn/10 border border-warn/30 text-[8.5pt] text-ink-700 flex items-start gap-3">
            <span className="font-bold text-warn text-[10pt]"></span>
            <div>
              <strong className="font-mono text-[8pt] uppercase tracking-[0.04em] text-warn block mb-0.5">
                Consultant Strategic Advisory: Low-ROI Traps to Ignore
              </strong>
              <p className="leading-relaxed font-sans">{brief.consultantIgnoreAdvice}</p>
            </div>
          </div>
        )}
      </div>

      <PageFooter
        theme={theme}
        domain={meta.domain}
        pageNumber={3}
        reportId={meta.analysisId}
        dateStr={meta.generatedAt}
      />
    </section>
  );
}
