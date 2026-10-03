import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';

interface CoverPageProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function CoverPage({ theme, report }: CoverPageProps) {
  const { meta, brief, scorecard } = report;

  return (
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-4 border-slate-950 relative overflow-hidden">
      {/* Background Accent Geometry (Subtle editorial watermark) */}
      <div
        className="absolute top-0 right-0 w-96 h-96 -mr-24 -mt-24 rounded-full opacity-[0.035] pointer-events-none"
        style={{ backgroundColor: theme.accent }}
      />

      {/* Top Classification Header */}
      <div className="border-b-2 border-slate-900 pb-4 flex flex-wrap items-baseline justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10pt] font-extrabold tracking-[0.22em] text-slate-950">
            DRISTIK
          </span>
          <span className="text-slate-300">/</span>
          <span className="font-mono text-[8pt] font-semibold uppercase tracking-[0.18em] text-slate-600">
            Enterprise Intelligence Advisory
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-[8pt] font-bold uppercase tracking-widest px-2.5 py-0.5 border border-red-300 bg-red-50 text-red-800 rounded">
            STRICTLY CONFIDENTIAL // C-SUITE ONLY
          </span>
          <span className="font-mono text-[8pt] font-semibold text-slate-500">
            DOSSIER REF: {meta.analysisId.slice(0, 10)}
          </span>
        </div>
      </div>

      {/* Main Publication Title & Brand Hero */}
      <div className="my-auto space-y-6 max-w-4xl py-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 border border-slate-300 text-slate-800 text-[8.5pt] font-mono uppercase tracking-[0.2em] font-semibold">
          <span>Independent Digital Asset Intelligence Audit</span>
        </div>

        <h1 className="font-serif text-[38pt] md:text-[46pt] font-normal leading-[1.08] tracking-tight text-slate-950">
          Digital Intelligence Dossier
        </h1>

        <div className="flex items-center gap-3 pt-1">
          <div className="w-12 h-[3px]" style={{ backgroundColor: theme.accent }}></div>
          <p className="font-mono text-[11pt] font-semibold tracking-wider text-slate-600 uppercase">
            SEO · GEO · AEO · CRO · TECHNICAL GOVERNANCE
          </p>
        </div>

        {/* Client Subject Box */}
        <div className="pt-4 pb-2">
          <span className="font-mono text-[8.5pt] uppercase tracking-wider text-slate-500 block mb-1">
            Subject Entity of Investigation:
          </span>
          <div className="text-[28pt] md:text-[34pt] font-serif font-bold text-slate-950 tracking-tight leading-none">
            {meta.brandName}
          </div>
          <p className="font-mono text-[10pt] text-slate-600 mt-2">
            {meta.websiteUrl}
          </p>
        </div>

        {/* Lead Synthesis Statement */}
        <p className="font-serif text-[12.5pt] leading-[1.65] text-slate-700 max-w-3xl border-l-2 pl-4 border-slate-300">
          {brief.leadThesis}
        </p>
      </div>

      {/* Bottom Block: Scorecard Pill, Certification Seal & Formal Engagement Metadata */}
      <div className="border-t-2 border-slate-900 pt-6 mt-8 space-y-6">
        {/* Score & Seal Row */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div className="flex items-center gap-4">
            <div className="p-3 px-5 border border-slate-300 bg-slate-50 rounded">
              <span className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-500 block">
                Composite Discoverability Score
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="font-serif text-3xl font-bold text-slate-950">
                  {scorecard.overallScore != null ? Math.round(scorecard.overallScore) : '—'}
                </span>
                <span className="font-mono text-xs text-slate-500">/ 100</span>
                <span
                  className="font-mono text-xs font-bold px-2 py-0.5 rounded ml-2"
                  style={{ backgroundColor: theme.accentTint, color: theme.accentDark }}
                >
                  GRADE {scorecard.grade}
                </span>
              </div>
            </div>

            <div className="hidden sm:block text-[8pt] text-slate-600 font-sans max-w-xs leading-relaxed">
              Synthesized across {meta.pagesAnalyzed} crawled URLs, {meta.evidenceCount} verified AST DOM facts, and live multi-engine answer checks.
            </div>
          </div>

          <div className="text-right">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-emerald-300 bg-emerald-50 text-emerald-900 rounded font-mono text-[8pt] font-bold tracking-wider uppercase">
              <span>★</span>
              <span>CERTIFIED ZERO-FAKE GROUND TRUTH</span>
            </div>
            <p className="text-[7.5pt] font-mono text-slate-400 mt-1">
              Cryptographically verifiable DOM evidence hash registry
            </p>
          </div>
        </div>

        {/* Engagement Metadata Table (Institutional PwC / Deloitte Style) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[8pt]">
          <div>
            <span className="font-mono text-[7pt] uppercase tracking-wider text-slate-400 block">
              Audit Date & Timestamp
            </span>
            <span className="font-semibold text-slate-800 mt-0.5 block font-mono">
              {meta.generatedAt.slice(0, 10)}
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-wider text-slate-400 block">
              Pages Analyzed
            </span>
            <span className="font-semibold text-slate-800 mt-0.5 block font-mono">
              {meta.pagesAnalyzed} Primary Origin URLs
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-wider text-slate-400 block">
              Evidence Sources
            </span>
            <span className="font-semibold text-slate-800 mt-0.5 block font-mono">
              {meta.evidenceCount} Sealed AST Citations
            </span>
          </div>

          <div>
            <span className="font-mono text-[7pt] uppercase tracking-wider text-slate-400 block">
              Inspection Policy Pack
            </span>
            <span className="font-semibold text-slate-800 mt-0.5 block font-mono">
              {meta.policyPack}
            </span>
          </div>
        </div>

        {/* Footer publisher accreditation */}
        <div className="flex items-center justify-between text-[7pt] font-mono text-slate-400 pt-3 border-t border-slate-100">
          <span>PUBLISHED BY DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS</span>
          <span>DOCUMENT CLASSIFICATION: C-SUITE CONFIDENTIAL</span>
        </div>
      </div>
    </section>
  );
}
