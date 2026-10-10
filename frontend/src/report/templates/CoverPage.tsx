import React from 'react';
import { formatPercentPoints } from '../../lib/format';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';

interface CoverPageProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function CoverPage({ report }: CoverPageProps) {
  const { meta, brief, scorecard } = report;

  return (
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-4 border-ink relative overflow-hidden">
      {/* Top Classification Header */}
      <div className="border-b-2 border-ink pb-4 flex flex-wrap items-baseline justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10pt] font-extrabold tracking-[0.04em] text-ink">
            DRISTIK
          </span>
          <span className="text-ink-300">/</span>
          <span className="font-mono text-[8pt] font-semibold uppercase tracking-[0.04em] text-ink-600">
            Enterprise Intelligence Advisory
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] px-2.5 py-0.5 border border-bad/30 bg-bad/10 text-bad rounded">
            STRICTLY CONFIDENTIAL // C-SUITE ONLY
          </span>
          <span className="font-mono text-[8pt] font-semibold text-ink-500">
            DOSSIER REF: {meta.analysisId.slice(0, 10)}
          </span>
        </div>
      </div>

      {/* Main Publication Title & Brand Hero */}
      <div className="my-auto space-y-6 max-w-4xl py-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-paper-200 border border-line text-ink-700 text-[8.5pt] font-mono uppercase tracking-[0.04em] font-semibold">
          <span>Independent Digital Asset Intelligence Audit</span>
        </div>

        <h1 className="font-serif text-[38pt] md:text-[46pt] font-normal leading-[1.08] tracking-tight text-ink">
          Digital Intelligence Dossier
        </h1>

        <div className="flex items-center gap-3 pt-1">
          <div className="bg-ink w-10 h-px" />
          <p className="font-mono text-[11pt] font-semibold tracking-[0.04em] text-ink-600 uppercase">
            SEO · GEO · AEO · CRO · TECHNICAL GOVERNANCE
          </p>
        </div>

        {/* Client Subject Box */}
        <div className="pt-4 pb-2">
          <span className="font-mono text-[8.5pt] uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Subject Entity of Investigation:
          </span>
          <div className="text-[28pt] md:text-[34pt] font-serif font-bold text-ink tracking-tight leading-none">
            {meta.brandName}
          </div>
          <p className="font-mono text-[10pt] text-ink-600 mt-2">
            {meta.websiteUrl}
          </p>
        </div>

        {/* Lead Synthesis Statement */}
        <p className="font-sans text-[12.5pt] leading-[1.65] text-ink-700 max-w-3xl border-l-2 pl-4 border-line">
          {brief.leadThesis}
        </p>
      </div>

      {/* Bottom Block: Scorecard Pill, Certification Seal & Formal Engagement Metadata */}
      <div className="border-t-2 border-ink pt-6 mt-8 space-y-6">
        {/* Score & Seal Row */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-line">
          <div className="flex flex-wrap items-center gap-3">
            <div className="p-3 px-5 border border-line bg-paper-100 rounded">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                Composite Discoverability Score
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="font-sans text-3xl font-bold text-ink">
                  {scorecard.overallScore != null ? scorecard.overallScore.toFixed(1) : '—'}
                </span>
                <span className="font-mono text-xs text-ink-500">/ 100</span>
                <span
                  className="font-mono text-xs font-bold px-2 py-0.5 rounded ml-2"
                >
                  GRADE {scorecard.grade}
                </span>
              </div>
            </div>

            {/* Audit Crawl Scope & Coverage Notice */}
            <div className="p-3 px-4 border border-line bg-paper-100 rounded">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                Audit Crawl Coverage
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="font-sans text-xl font-bold text-ink">
                  {meta.discoveredUrlsCount != null
                    ? `${meta.pagesAnalyzed} / ${meta.discoveredUrlsCount}`
                    : meta.pagesAnalyzed}
                </span>
                <span className="font-mono text-xs text-ink-500">URLs</span>
                {meta.sampleCoveragePct != null && (
                  <span className="font-mono text-[7.5pt] font-bold px-1.5 py-0.2 rounded bg-paper-200 text-ink-700 ml-1">
                    {formatPercentPoints(meta.sampleCoveragePct)}
                  </span>
                )}
              </div>
              <span className="font-mono text-[6.5pt] text-ink-500 block mt-0.5">
                Same total as the calculation ledger. Applies only to the audited sample.
              </span>
            </div>
          </div>

          <div className="text-right">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-good/30 bg-good/10 text-good rounded font-mono text-[8pt] font-bold tracking-[0.04em] uppercase">
              <span>★</span>
              <span>EVIDENCE-GOVERNED AUDIT SPECIFICATION</span>
            </div>
            <p className="text-[7.5pt] font-mono text-ink-500 mt-1">
              Empirically verified AST ground truth · SHA-256 sealed ledger
            </p>
          </div>
        </div>

        {/* Engagement Metadata Table (Institutional PwC / Deloitte Style) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[8pt]">
          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Audit Date & Timestamp
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {meta.generatedAt.slice(0, 10)}
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Pages Analyzed
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {meta.pagesAnalyzed} Primary Origin URLs
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Evidence Sources
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {meta.evidenceCount} Sealed AST Citations
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Inspection Policy Pack
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {meta.policyPack}
            </span>
          </div>
        </div>

        {/* Footer publisher accreditation */}
        <div className="flex items-center justify-between text-[7pt] font-mono text-ink-400 pt-3 border-t border-line">
          <span>PUBLISHED BY DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS</span>
          <span>DOCUMENT CLASSIFICATION: C-SUITE CONFIDENTIAL</span>
        </div>
      </div>
    </section>
  );
}
