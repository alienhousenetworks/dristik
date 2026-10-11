import React from 'react';
import { formatPercentPoints } from '../../lib/format';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface ExecutiveBriefProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

function ratioText(ratio: { numerator: number; denominator: number } | null, empty: string): string {
  if (!ratio || ratio.denominator <= 0) return empty;
  return `${ratio.numerator}/${ratio.denominator}`;
}

function weightCaption(row: NormalizedReport['scorecard']['ledger'][number] | undefined): string {
  if (!row) return 'Not in this composite';
  const nominal = `${row.nominalWeightPct}% nominal`;
  if (!row.included) return `${nominal} · excluded`;
  if (row.nominalWeightPct !== row.weightPct) return `${nominal} · ${row.weightPct}% effective`;
  return `${row.weightPct}%`;
}

function GoogleChannelCard({
  title,
  channel,
}: {
  title: string;
  channel: NormalizedReport['googlePerformance']['searchConsole'];
}) {
  return (
    <div className="bg-paper-50 p-2.5 rounded border border-line space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[7pt] font-bold uppercase tracking-[0.04em] text-ink-700">{title}</span>
        <span className="font-mono text-[6.5pt] font-bold px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
          {channel.state}
        </span>
      </div>
      {channel.state === 'MEASURED' && (channel.property || channel.period) && (
        <p className="font-mono text-[7pt] text-ink-500">
          {[channel.property, channel.period].filter(Boolean).join(' · ')}
        </p>
      )}
      {channel.state === 'MEASURED' && channel.metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-1.5">
          {channel.metrics.map((metric) => (
            <div key={metric.label}>
              <span className="text-ink-400 block text-[6.5pt] uppercase">{metric.label}</span>
              <strong className="text-ink text-[8pt]">{metric.value}</strong>
            </div>
          ))}
        </div>
      )}
      {channel.state === 'MEASURED' && channel.rows.length > 0 && (
        <ul className="space-y-0.5">
          {channel.rows.map((row) => (
            <li key={row.label} className="text-ink-700">
              <span className="font-semibold">{row.label}</span>
              {row.detail ? <span className="text-ink-500"> — {row.detail}</span> : null}
            </li>
          ))}
        </ul>
      )}
      {channel.state !== 'MEASURED' && (
        <p className="font-sans text-[7.5pt] text-ink-600 leading-relaxed">{channel.notice}</p>
      )}
    </div>
  );
}

function GooglePerformance({ report }: { report: NormalizedReport }) {
  return (
    <div className="p-3.5 bg-paper-100 border border-line rounded text-[8pt] space-y-2">
      <div className="flex flex-wrap items-center justify-between pb-1.5 border-b border-line">
        <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
          Google Search Console &amp; Analytics
        </span>
        <span className="font-mono text-[7pt] text-ink-500">Shown only when this audit retrieved them</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 font-mono text-[7.5pt]">
        <GoogleChannelCard title="Search Console" channel={report.googlePerformance.searchConsole} />
        <GoogleChannelCard title="Analytics 4" channel={report.googlePerformance.analytics} />
      </div>
    </div>
  );
}

export function ExecutiveBrief({ theme, report }: ExecutiveBriefProps) {
  const { brief, meta } = report;
  const { keySignals } = brief;
  const ledger = report.scorecard.ledger;
  const technicalRow = ledger.find((row) => row.categoryKey === 'TECHNICAL_SEO');
  const geoRow = ledger.find((row) => row.categoryKey === 'GEO');
  const aeoRow = ledger.find((row) => row.categoryKey === 'AEO');
  const croRow = ledger.find((row) => row.categoryKey === 'UX_CONVERSION');

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
                {report.scorecard.coverageLabel}
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
                1. Technical SEO
              </span>
              <span className="font-mono text-[6.5pt] text-ink-400 block">{weightCaption(technicalRow)}</span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.technicalScore != null ? keySignals.technicalScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">Crawler Pass</span>
            </div>

            <div className="text-center p-2 border-r border-line last:border-r-0">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                2. GEO Readiness
              </span>
              <span className="font-mono text-[6.5pt] text-ink-400 block">{weightCaption(geoRow)}</span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.geoScore != null ? keySignals.geoScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">DOM Extractability</span>
            </div>

            <div className="text-center p-2 border-r border-line last:border-r-0">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                3. Live citations
              </span>
              <span className="font-mono text-[6.5pt] text-ink-400 block">{weightCaption(aeoRow)}</span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.aeoScore != null ? keySignals.aeoScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">
                {report.aeo.liveObservation.isMeasured
                  ? `Live citation ${formatPercentPoints(report.aeo.liveObservation.liveCitationRatePct)}`
                  : 'Not measured'}
              </span>
            </div>

            <div className="text-center p-2">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                4. CRO &amp; UX
              </span>
              <span className="font-mono text-[6.5pt] text-ink-400 block">{weightCaption(croRow)}</span>
              <div className="font-sans text-3xl font-bold text-ink mt-1">
                {keySignals.croScore != null ? keySignals.croScore : '—'}
              </div>
              <span className="font-mono text-[7.5pt] text-ink-400 block mt-1">Copy and DOM only</span>
            </div>
          </div>
          <div className="px-1 space-y-1 text-[7.5pt] font-mono text-ink-500">
            <div className="flex items-center justify-between gap-3">
              <span>Same composite as the calculation ledger: Σ (pillar score × effective weight) = {keySignals.overallScore != null ? keySignals.overallScore.toFixed(1) : '—'}</span>
              <span>{report.scorecard.coverageLabel}</span>
            </div>
            {report.scorecard.partialCoverage && (
              <p className="font-sans text-ink-600 leading-relaxed">
                Partial-coverage composite. Excluded: {report.scorecard.excludedPillars.join('; ') || 'none'}.
                Nominal weights stay 30% SEO, 25% GEO, 25% live citations, and 20% CRO. Effective weights are the nominal weights of the measured pillars scaled to 100%. This total is not comparable to a fully measured audit.
              </p>
            )}
            <p className="font-sans text-ink-600 leading-relaxed">{report.conversion.croBoundary}</p>
          </div>
        </div>

        {/* Audit Coverage & Evidence Confidence Breakdown (Points 11 & 12) */}
        {report.coverageConfidence && (
          <div className="p-3.5 bg-paper-100 border border-line rounded text-[8pt] space-y-2">
            <div className="flex flex-wrap items-center justify-between pb-1.5 border-b border-line">
              <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                Audit Scope &amp; Evidence Coverage Confidence
              </span>
              <span className="font-mono text-[7pt] font-bold px-2 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
                EVIDENCE CONFIDENCE: {report.coverageConfidence.overallEvidenceConfidence}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5 font-mono text-[7.5pt]">
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Page Coverage</span>
                <strong className="text-ink text-[8pt] block mt-0.5 truncate">
                  {report.coverageConfidence.pagesDiscovered != null
                    ? `${report.coverageConfidence.pagesAudited} / ${report.coverageConfidence.pagesDiscovered} (${formatPercentPoints(report.coverageConfidence.pageCoveragePct)})`
                    : `${report.coverageConfidence.pagesAudited} analyzed`}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Evidence coverage</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {report.coverageConfidence.evidenceCoveragePct == null
                    ? 'Not recorded'
                    : `${formatPercentPoints(report.coverageConfidence.evidenceCoveragePct)} of score inputs`}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Question coverage</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {ratioText(report.coverageConfidence.questionCoverage, 'Not assessed')}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Answerability</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {ratioText(report.coverageConfidence.answerability, 'Not assessed')}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Claim grounding</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {ratioText(report.coverageConfidence.claimGrounding, 'Not recorded')}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Live AI queries</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {report.coverageConfidence.liveQueriesExecuted > 0
                    ? `${report.coverageConfidence.liveQueriesExecuted} completed`
                    : report.coverageConfidence.liveQueriesAttempted > 0
                      ? `${report.coverageConfidence.liveQueriesAttempted} attempted, 0 completed`
                      : 'Not executed'}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">External Authority</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {report.coverageConfidence.externalAuthorityLabel}
                </strong>
              </div>
              <div className="bg-paper-50 p-2 rounded border border-line">
                <span className="text-ink-400 block text-[6.5pt] uppercase">Server response sample</span>
                <strong className="text-ink text-[8pt] block mt-0.5">
                  {report.coverageConfidence.performancePagesCount} URL TTFB {report.coverageConfidence.performancePagesCount === 1 ? 'sample' : 'samples'}
                </strong>
              </div>
            </div>

            <p className="font-sans text-[7.5pt] text-ink-500 italic">
              {report.coverageConfidence.scopeLimitationNotice}
              {' '}Question coverage is completed assessments over questions in scope. Answerability is questions with a supporting passage over questions assessed. Claim grounding is supported claims over claims evaluated. A completed question is not an answered question.
            </p>
          </div>
        )}

        <GooglePerformance report={report} />

        {/* Editorial Triad: What is Working / What Needs Attention / What Matters Next */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
          {/* 1. What is working */}
          <div className="p-4 rounded bg-good/10 border border-good/30 space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-good block">
              ✓ WHAT IS WORKING (OBSERVED)
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
