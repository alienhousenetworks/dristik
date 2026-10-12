import React from 'react';
import { formatPercentPoints } from '../../lib/format';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { PublicationManifest } from '../adaptivePublication';

interface CoverPageProps {
  theme: ReportTheme;
  report: NormalizedReport;
  manifest?: PublicationManifest;
}

export function CoverPage({ report, manifest }: CoverPageProps) {
  const { meta, brief, scorecard } = report;

  const reportBadge = manifest?.reportTypeBadge || 'DIGITAL ASSET INTELLIGENCE AUDIT DOSSIER';
  const coverTitle = manifest?.title || 'Digital Intelligence Dossier';
  const coverSubtitle = manifest?.subtitle || 'SEO · GEO · AEO · CRO · TECHNICAL GOVERNANCE';
  const purposeSummary = manifest?.purposeSummary || brief.leadThesis;
  const classification = manifest?.classification || 'STRICTLY CONFIDENTIAL // C-SUITE DOSSIER';
  const reportRef = manifest?.reportRef || meta.analysisId.slice(0, 12).toUpperCase();
  const auditDate = manifest?.auditDate || meta.generatedAt.slice(0, 10);
  const reportingPeriod = manifest?.reportingPeriod || 'Observed audit crawl window';

  return (
    <section
      data-chapter-id="cover_page"
      className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-4 border-ink text-ink relative overflow-hidden"
    >
      {/* Top Header Hierarchy */}
      <div className="border-b-2 border-ink pb-4 flex flex-wrap items-baseline justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10pt] font-extrabold tracking-[0.06em] text-ink">
            DRISTIK
          </span>
          <span className="text-ink-300">/</span>
          <span className="font-mono text-[8pt] font-semibold uppercase tracking-[0.05em] text-ink-600">
            WEBSITE INTELLIGENCE / DIGITAL AUDIT SERIES
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] px-2.5 py-0.5 border border-line bg-paper-200 text-ink-700 rounded">
            {classification}
          </span>
          <span className="font-mono text-[8pt] font-semibold text-ink-500">
            REF: {reportRef}
          </span>
        </div>
      </div>

      {/* Main Publication Identity & Title Block */}
      <div className="my-auto space-y-6 max-w-4xl py-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-paper-200 border border-line text-ink-800 text-[8.5pt] font-mono uppercase tracking-[0.06em] font-bold">
          <span>{reportBadge}</span>
        </div>

        <h1 className="font-serif text-[36pt] md:text-[44pt] font-normal leading-[1.08] tracking-tight text-ink">
          {coverTitle}
        </h1>

        <div className="flex items-center gap-3 pt-1">
          <div className="bg-ink w-10 h-px" />
          <p className="font-mono text-[10.5pt] font-semibold tracking-[0.04em] text-ink-600 uppercase">
            {coverSubtitle}
          </p>
        </div>

        {/* Client Subject Box */}
        <div className="pt-4 pb-2">
          <span className="font-mono text-[8pt] uppercase tracking-[0.06em] text-ink-500 block mb-1">
            Subject Entity Under Audit:
          </span>
          <div className="text-[26pt] md:text-[32pt] font-serif font-bold text-ink tracking-tight leading-none">
            {meta.brandName}
          </div>
          <p className="font-mono text-[10pt] text-ink-600 mt-2">
            {meta.websiteUrl}
          </p>
        </div>

        {/* One-Sentence Scope & Purpose Statement */}
        <p className="font-sans text-[12pt] leading-[1.65] text-ink-700 max-w-3xl border-l-2 pl-4 border-line">
          {purposeSummary}
        </p>
      </div>

      {/* Bottom Block: Score & Audit Crawl Coverage Notice */}
      <div className="border-t-2 border-ink pt-6 mt-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-line">
          <div className="flex flex-wrap items-center gap-3">
            {/* Scorecard pill */}
            <div className="p-3 px-5 border border-line bg-paper-100 rounded">
              <span className="font-mono text-[7.5pt] uppercase tracking-[0.04em] text-ink-500 block">
                {scorecard.coverageLabel}
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="font-sans text-3xl font-bold text-ink">
                  {scorecard.overallScore != null ? scorecard.overallScore.toFixed(1) : '—'}
                </span>
                <span className="font-mono text-xs text-ink-500">/ 100</span>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded ml-2 bg-paper-200 border border-line">
                  GRADE {scorecard.grade}
                </span>
              </div>
            </div>

            {/* Crawl Scope & Coverage Notice */}
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
                <span className="font-mono text-xs text-ink-500">URLs Analyzed</span>
                {meta.sampleCoveragePct != null && (
                  <span className="font-mono text-[7.5pt] font-bold px-1.5 py-0.2 rounded bg-paper-200 text-ink-700 ml-1">
                    {formatPercentPoints(meta.sampleCoveragePct)}
                  </span>
                )}
              </div>
              <span className="font-mono text-[6.5pt] text-ink-500 block mt-0.5">
                Deterministic calculation applied strictly to the audited sample.
              </span>
            </div>
          </div>

          <div className="text-right">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-line bg-paper-200 text-ink-800 rounded font-mono text-[8pt] font-bold tracking-[0.04em] uppercase">
              <span>★</span>
              <span>ZERO-FAKE EVIDENCE SPECIFICATION</span>
            </div>
            <p className="text-[7.5pt] font-mono text-ink-500 mt-1">
              Evidence-linked findings · AST SHA-256 integrity stamped
            </p>
          </div>
        </div>

        {/* Engagement Metadata Table */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[8pt]">
          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Audit Date
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {auditDate}
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Reporting Period
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {reportingPeriod}
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Prepared By
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              Dristik Autonomous Intelligence
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-[0.04em] text-ink-400 block">
              Classification
            </span>
            <span className="font-semibold text-ink-700 mt-0.5 block font-mono">
              {classification}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
