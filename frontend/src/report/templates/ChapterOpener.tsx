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
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
      {/* Top publisher running bar */}
      <div className="flex items-center justify-between pb-3 border-b border-line text-[8pt] font-mono tracking-[0.04em] uppercase text-ink-500">
        <div className="flex items-center gap-2">
          <span className="font-bold text-ink">DRISTIK</span>
          <span className="text-ink-300">/</span>
          <span>ENTERPRISE ADVISORY DOSSIER</span>
        </div>
        <div>
          <span>CHAPTER {chapterNumber}</span>
          <span className="mx-2 text-ink-300">·</span>
          <span>{domain}</span>
        </div>
      </div>

      {/* Main Chapter Lead Block */}
      <div className="my-auto space-y-6 max-w-4xl py-6">
        {/* Chapter Number & Minimal Geometric Motif */}
        <div className="flex items-baseline justify-between">
          <div
            className={DESIGN_TOKENS.typography.chapterNumber}
          >
            {chapterNumber}
          </div>
          {/* Minimal accent graphic */}
          <div className="hidden sm:flex items-center gap-1.5 opacity-80">
            <span className="bg-ink w-10 h-px" />
            <span className="w-32 h-[1px] bg-paper-300"></span>
          </div>
        </div>

        {/* Pillar Subtitle */}
        <div className="font-mono text-[9pt] font-bold uppercase tracking-[0.04em] text-ink-500">
          {subtitle}
        </div>

        {/* Large Chapter Title */}
        <h1 className="font-serif text-[32pt] md:text-[38pt] font-normal leading-[1.12] tracking-tight text-ink">
          {title}
        </h1>

        {/* Editorial Description */}
        <p className="font-sans text-[13pt] md:text-[14pt] font-normal leading-[1.6] text-ink-700 max-w-3xl">
          {description}
        </p>

        {/* Client-Brand Accent Rule */}
        <div className="bg-ink w-10 h-px mt-4" />
      </div>

      {/* Structured 3-Part Framing Grid (Why Matters / How Measured / What Analyzed) */}
      <div className="border-t border-line pt-6 mt-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-[8.5pt]">
          {/* 1. Why this matters */}
          <div className="space-y-1.5 p-4 rounded bg-paper-100 border border-line">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block">
              01 // WHY THIS MATTERS
            </span>
            <p className="text-ink-700 leading-relaxed font-sans">
              {whyThisMatters}
            </p>
          </div>

          {/* 2. How we measured it */}
          <div className="space-y-1.5 p-4 rounded bg-paper-100 border border-line">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block">
              02 // HOW WE MEASURED IT
            </span>
            <p className="text-ink-700 leading-relaxed font-sans">
              {howWeMeasuredIt}
            </p>
          </div>

          {/* 3. What was analyzed */}
          <div className="space-y-1.5 p-4 rounded bg-paper-100 border border-line">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block">
              03 // WHAT WAS ANALYZED
            </span>
            <p className="text-ink-700 leading-relaxed font-sans">
              {whatWasAnalyzed}
            </p>
          </div>
        </div>

        {/* Bottom Running Footer on Opener */}
        <div className="flex items-center justify-between text-[7.5pt] font-mono text-ink-400 mt-6 pt-3 border-t border-line">
          <span>CONFIDENTIAL // PREPARED FOR {domain}</span>
          <span>{pageNumber != null ? `PAGE ${pageNumber}` : ''}</span>
        </div>
      </div>
    </section>
  );
}
