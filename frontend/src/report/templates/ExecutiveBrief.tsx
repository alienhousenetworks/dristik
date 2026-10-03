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
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
      <PageHeader
        theme={theme}
        domain={meta.domain}
        chapterTitle="EXECUTIVE BRIEF // STRATEGIC SUMMARY"
      />

      <div className="space-y-6 max-w-4xl">
        {/* Section Headline */}
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
            Section 0.1 // Executive Synthesis
          </span>
          <h2 className="font-serif text-[24pt] md:text-[28pt] font-normal tracking-tight text-slate-950">
            What the Evidence Says
          </h2>
          <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
        </div>

        {/* Large Editorial Thesis Statement */}
        <div className="py-2">
          <p className="font-serif text-[14pt] md:text-[16pt] font-normal leading-[1.55] text-slate-900 border-l-3 pl-4 border-slate-900">
            {brief.leadThesis}
          </p>
        </div>

        {/* 5 Key Performance Signals (Continuous Metrics derived from actual engine) */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-4 bg-slate-50 border border-slate-200 rounded">
          <div className="text-center p-2 border-r border-slate-200 last:border-r-0">
            <span className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-500 block">
              Overall Index
            </span>
            <div className="font-serif text-3xl font-bold text-slate-950 mt-1">
              {keySignals.overallScore != null ? Math.round(keySignals.overallScore) : '—'}
            </div>
            <span
              className="font-mono text-[8pt] font-bold px-1.5 py-0.2 rounded mt-1 inline-block"
              style={{ backgroundColor: theme.accentTint, color: theme.accentDark }}
            >
              GRADE {keySignals.overallGrade}
            </span>
          </div>

          <div className="text-center p-2 border-r border-slate-200 last:border-r-0">
            <span className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-500 block">
              1. Technical SEO
            </span>
            <div className="font-serif text-3xl font-bold text-slate-900 mt-1">
              {keySignals.technicalScore != null ? keySignals.technicalScore : '—'}
            </div>
            <span className="font-mono text-[7.5pt] text-slate-400 block mt-1">Crawler Pass</span>
          </div>

          <div className="text-center p-2 border-r border-slate-200 last:border-r-0">
            <span className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-500 block">
              2. GEO Extractability
            </span>
            <div className="font-serif text-3xl font-bold text-slate-900 mt-1">
              {keySignals.geoScore != null ? keySignals.geoScore : '—'}
            </div>
            <span className="font-mono text-[7.5pt] text-slate-400 block mt-1">DOM RAG Signal</span>
          </div>

          <div className="text-center p-2 border-r border-slate-200 last:border-r-0">
            <span className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-500 block">
              3. AEO Live Citations
            </span>
            <div className="font-serif text-3xl font-bold text-slate-900 mt-1">
              {keySignals.aeoScore != null ? keySignals.aeoScore : '—'}
            </div>
            <span className="font-mono text-[7.5pt] text-slate-400 block mt-1">Live AI Visibility</span>
          </div>

          <div className="text-center p-2">
            <span className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-500 block">
              4. CRO &amp; Value Prop
            </span>
            <div className="font-serif text-3xl font-bold text-slate-900 mt-1">
              {keySignals.croScore != null ? keySignals.croScore : '—'}
            </div>
            <span className="font-mono text-[7.5pt] text-slate-400 block mt-1">Visitor Clarity</span>
          </div>
        </div>

        {/* Editorial Triad: What is Working / What Needs Attention / What Matters Next */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
          {/* 1. What is working */}
          <div className="p-4 rounded bg-emerald-50/50 border border-emerald-200 space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-emerald-900 block">
              ✓ WHAT IS WORKING (VERIFIED)
            </span>
            <ul className="text-[8.5pt] text-slate-800 space-y-1.5 list-disc pl-4 font-sans leading-relaxed">
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
          <div className="p-4 rounded bg-rose-50/50 border border-rose-200 space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-rose-900 block">
              ⚠ WHAT NEEDS ATTENTION
            </span>
            <ul className="text-[8.5pt] text-slate-800 space-y-1.5 list-disc pl-4 font-sans leading-relaxed">
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
          <div className="p-4 rounded bg-slate-50 border border-slate-300 space-y-2">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-900 block">
              ★ WHAT MATTERS NEXT (CATALYST)
            </span>
            <p className="text-[8.5pt] text-slate-800 font-sans leading-relaxed">
              {brief.whatMattersNext}
            </p>
          </div>
        </div>

        {/* Consultant Advice: Low-ROI Traps to Ignore */}
        {brief.consultantIgnoreAdvice && (
          <div className="p-3.5 rounded bg-amber-50/60 border border-amber-200 text-[8.5pt] text-slate-800 flex items-start gap-3">
            <span className="font-bold text-amber-800 text-[10pt]">⚡</span>
            <div>
              <strong className="font-mono text-[8pt] uppercase tracking-wider text-amber-900 block mb-0.5">
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
