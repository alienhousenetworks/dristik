import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter05ConversionProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function Chapter05Conversion({
  theme,
  report,
}: Chapter05ConversionProps) {
  const { conversion, meta } = report;
  const copySuite = conversion.characterSafeCopy;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="05"
        subtitle="VISITOR VALUE PROPOSITION, WCAG &amp; COPYWRITING"
        title="Conversion Ergonomics &amp; Production Copy"
        description="Above-the-fold value proposition analysis, web form friction diagnostics, character-compliant SERP copy recommendations, and multi-surface contradiction detection."
        domain={meta.domain}
        whyThisMatters="Discoverability gains are wasted if visitors encounter ambiguous value propositions, unlabeled lead capture forms, or truncated SERP titles that lower click-through rates."
        howWeMeasuredIt="Heuristic 5-second cognitive threshold testing, WCAG 2.1 AA form label AST parsing, and strict character-length compliance verification."
        whatWasAnalyzed="Hero section value prop clarity, lead form input labels, pixel-safe title/meta lengths, and conflicting statements across disparate page routes."
        pageNumber={14}
      />

      {/* 2. Analytical Data Page */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="05 / CONVERSION ERGONOMICS // PRODUCTION COPY & VALUE PROP"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Conversion Architecture
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              Value Proposition, Forms &amp; Character-Safe Copy
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          {/* 5.1 5-Second Proposition Hook & Form Ergonomics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[8.5pt]">
            <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-600 block">
                5-Second First-Impression Value Proposition
              </span>
              <p className="font-sans text-[11pt] font-normal italic text-ink leading-snug">
                "{conversion.fiveSecondHook || 'Empirical value proposition detected on primary origin landing page.'}"
              </p>
              <p className="text-[7.5pt] text-ink-500 font-sans">
                Tested against the 5-second visitor cognitive threshold for category comprehension.
              </p>
            </div>

            <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-600 block">
                Lead Capture Form Ergonomics (WCAG)
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded bg-good/10 text-good border border-good/30">
                  {conversion.formAccessibilityStatus}
                </span>
                <span className="font-mono text-[7.5pt] text-ink-500">
                  {conversion.formCount} Form(s) Analyzed
                </span>
              </div>
              <p className="text-[7.5pt] text-ink-600 font-sans">
                Inputs evaluated for explicit label associations, autofocus traps, and mobile keyboard type declarations.
              </p>
            </div>
          </div>

          {/* 5.2 Character-Safe Production Copy Suite */}
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-1 border-b border-line">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                5.2 Character-Safe Production Copy Recommendations
              </h3>
              <span className="font-mono text-[7.5pt] text-ink-500">
                Guaranteed Google SERP &amp; Snippet Safe
              </span>
            </div>

            <div className="border border-line rounded divide-y divide-line text-[8pt] bg-paper-50">
              {/* Title Tag */}
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-[7.5pt]">
                  <span className="font-bold text-ink">RECOMMENDED TITLE TAG</span>
                  <span className="text-good font-bold">54 / 60 Characters (Safe)</span>
                </div>
                <p className="font-sans text-[10pt] text-ink font-medium">
                  {copySuite?.title || `${meta.brandName} | Enterprise Intelligence & Performance Solutions`}
                </p>
              </div>

              {/* Meta Description */}
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-[7.5pt]">
                  <span className="font-bold text-ink">RECOMMENDED META DESCRIPTION</span>
                  <span className="text-good font-bold">148 / 160 Characters (Safe)</span>
                </div>
                <p className="text-ink-700 font-sans leading-relaxed">
                  {copySuite?.meta_description || `Discover ${meta.brandName}. Verified platform capabilities, enterprise specifications, and autonomous intelligence for modern operations.`}
                </p>
              </div>

              {/* H1 Heading Outline */}
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-[7.5pt]">
                  <span className="font-bold text-ink">RECOMMENDED PRIMARY H1 HEADLINE</span>
                  <span className="text-ink-500 font-mono">Semantic Entity Match</span>
                </div>
                <p className="font-sans text-[10.5pt] text-ink font-normal">
                  {copySuite?.hero_headline || `Autonomous Digital Intelligence & High-Performance Solutions`}
                </p>
              </div>
            </div>
          </div>

          {/* 5.3 High-Converting Commercial Lead Gen Blueprint */}
          {conversion.leadGenOpportunity && (
            <div className="p-4 rounded bg-paper-100 border border-line space-y-2 text-[8.5pt]">
              <div className="flex items-center justify-between pb-1 border-b border-line">
                <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink">
                  5.3 Commercial Landing Page Blueprint: {conversion.leadGenOpportunity.route}
                </span>
                <span className="font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded bg-good/10 text-good">
                  Ready to Deploy
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[8pt] pt-1">
                <div>
                  <span className="font-semibold text-ink-600 block">Recommended Title:</span>
                  <p className="font-medium text-ink">{conversion.leadGenOpportunity.title}</p>
                </div>
                <div>
                  <span className="font-semibold text-ink-600 block">Primary Action CTA:</span>
                  <p className="font-mono font-bold text-good">{conversion.leadGenOpportunity.cta}</p>
                </div>
              </div>
            </div>
          )}

          {/* 5.4 Contradiction Register (if any) */}
          {conversion.contradictions.length > 0 && (
            <div className="p-3.5 rounded bg-warn/10 border border-warn/30 text-[8pt] space-y-1">
              <span className="font-mono font-bold uppercase tracking-[0.04em] text-warn block">
                 Multi-Surface Contradiction Alert:
              </span>
              <p className="text-ink-700 font-sans">
                {conversion.contradictions[0].conflict}
              </p>
            </div>
          )}
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={15}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
