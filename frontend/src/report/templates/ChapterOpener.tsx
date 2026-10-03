import React from 'react';
import { ReportTheme } from '../brandTheme';
import { DESIGN_TOKENS } from '../designTokens';

interface ChapterOpenerProps {
  theme: ReportTheme;
  chapterNumber: string; // e.g. "01"
  title: string;
  subtitle: string;
  description: string;
  domain: string;
  whyThisMatters: string;
  howWeMeasuredIt: string;
  whatWasAnalyzed: string;
  pageNumber?: number;
}

export function ChapterOpener({
  theme,
  chapterNumber,
  title,
  subtitle,
  description,
  domain,
  whyThisMatters,
  howWeMeasuredIt,
  whatWasAnalyzed,
  pageNumber,
}: ChapterOpenerProps) {
  return (
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
      {/* Top publisher running bar */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 text-[8pt] font-mono tracking-wider uppercase text-slate-500">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-900">DRISTIK</span>
          <span className="text-slate-300">/</span>
          <span>ENTERPRISE ADVISORY DOSSIER</span>
        </div>
        <div>
          <span>CHAPTER {chapterNumber}</span>
          <span className="mx-2 text-slate-300">·</span>
          <span>{domain}</span>
        </div>
      </div>

      {/* Main Chapter Lead Block */}
      <div className="my-auto space-y-6 max-w-4xl py-6">
        {/* Chapter Number & Minimal Geometric Motif */}
        <div className="flex items-baseline justify-between">
          <div
            className={DESIGN_TOKENS.typography.chapterNumber}
            style={{ color: theme.accent }}
          >
            {chapterNumber}
          </div>
          {/* Minimal accent graphic */}
          <div className="hidden sm:flex items-center gap-1.5 opacity-80">
            <span className="w-12 h-[2px]" style={{ backgroundColor: theme.accent }}></span>
            <span className="w-3 h-3 rounded-full border-2" style={{ borderColor: theme.accent }}></span>
            <span className="w-32 h-[1px] bg-slate-300"></span>
          </div>
        </div>

        {/* Pillar Subtitle */}
        <div className="font-mono text-[9pt] font-bold uppercase tracking-[0.2em] text-slate-500">
          {subtitle}
        </div>

        {/* Large Chapter Title */}
        <h1 className="font-serif text-[32pt] md:text-[38pt] font-normal leading-[1.12] tracking-tight text-slate-950">
          {title}
        </h1>

        {/* Editorial Description */}
        <p className="font-serif text-[13pt] md:text-[14pt] font-normal leading-[1.6] text-slate-700 max-w-3xl">
          {description}
        </p>

        {/* Client-Brand Accent Rule */}
        <div className="w-24 h-[3px] mt-4" style={{ backgroundColor: theme.accent }}></div>
      </div>

      {/* Structured 3-Part Framing Grid (Why Matters / How Measured / What Analyzed) */}
      <div className="border-t border-slate-200 pt-6 mt-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-[8.5pt]">
          {/* 1. Why this matters */}
          <div className="space-y-1.5 p-4 rounded bg-slate-50 border border-slate-200/80">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-500 block">
              01 // WHY THIS MATTERS
            </span>
            <p className="text-slate-800 leading-relaxed font-sans">
              {whyThisMatters}
            </p>
          </div>

          {/* 2. How we measured it */}
          <div className="space-y-1.5 p-4 rounded bg-slate-50 border border-slate-200/80">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-500 block">
              02 // HOW WE MEASURED IT
            </span>
            <p className="text-slate-800 leading-relaxed font-sans">
              {howWeMeasuredIt}
            </p>
          </div>

          {/* 3. What was analyzed */}
          <div className="space-y-1.5 p-4 rounded bg-slate-50 border border-slate-200/80">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-500 block">
              03 // WHAT WAS ANALYZED
            </span>
            <p className="text-slate-800 leading-relaxed font-sans">
              {whatWasAnalyzed}
            </p>
          </div>
        </div>

        {/* Bottom Running Footer on Opener */}
        <div className="flex items-center justify-between text-[7.5pt] font-mono text-slate-400 mt-6 pt-3 border-t border-slate-100">
          <span>CONFIDENTIAL // PREPARED FOR {domain}</span>
          <span>{pageNumber != null ? `PAGE ${pageNumber}` : ''}</span>
        </div>
      </div>
    </section>
  );
}
