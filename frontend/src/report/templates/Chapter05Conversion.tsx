import React from 'react';
import { ReportTheme } from '../brandTheme';
import { countWords } from '../models/copyCounts';
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
  const headlineWords = countWords(copySuite?.hero_headline);
  const blockWords = countWords(`${copySuite?.hero_headline || ''} ${copySuite?.hero_subhead || ''}`);
  const blockStatus = blockWords >= 40 && blockWords <= 60 ? 'within 40–60' : blockWords < 40 ? 'under 40' : 'over 60';

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="05"
        subtitle="VISITOR VALUE PROPOSITION &amp; COPY"
        title="Conversion Ergonomics &amp; Production Copy"
        description="Above-the-fold value proposition, automated form screening when a form audit ran, and character counts only when a copy recommendation was generated."
        domain={meta.domain}
        whyThisMatters="Discoverability gains are wasted if visitors encounter ambiguous value propositions, unlabeled lead capture forms, or truncated SERP titles that lower click-through rates."
        howWeMeasuredIt="Recorded hero copy, an automated form-label screen when that audit ran, and character counts on generated recommendations. This is not a WCAG certification."
        whatWasAnalyzed="Hero copy on sampled pages, form labels when a form audit ran, and contradictions recorded by the audit."
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
                Crawled value proposition
              </span>
              <p className="font-sans text-[11pt] font-normal italic text-ink leading-snug">
                {conversion.fiveSecondHook ? `"${conversion.fiveSecondHook}"` : 'Not determinable from the crawled evidence.'}
              </p>
              <p className="text-[7.5pt] text-ink-500 font-sans">
                {conversion.fiveSecondNotice}
              </p>
            </div>

            <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-600 block">
                Lead capture forms
              </span>
              <div className="flex items-center gap-2">
                <span className={`font-mono text-[8pt] font-bold px-2 py-0.5 rounded border ${
                  conversion.formCount == null
                    ? 'bg-paper-200 text-ink-700 border-line'
                    : 'bg-paper-100 text-ink border-line'
                }`}>
                  {conversion.formAccessibilityStatus}
                </span>
                <span className="font-mono text-[7.5pt] text-ink-500">
                  {conversion.formCount == null
                    ? 'No form audit on this run'
                    : `${conversion.formCount} form(s) in the automated screen`}
                </span>
              </div>
              <p className="text-[7.5pt] text-ink-600 font-sans">
                {conversion.croBoundary} Automated screening is not a WCAG certification and it is not a measured conversion rate.
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
                Counts apply only to generated recommendations
              </span>
            </div>

            <div className="border border-line rounded divide-y divide-line text-[8pt] bg-paper-50">
              {/* Title Tag */}
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-[7.5pt]">
                  <span className="font-bold text-ink">RECOMMENDED TITLE TAG</span>
                  <span className="text-ink-600 font-bold">
                    {copySuite?.title ? `${copySuite.title_char_count} characters · ${copySuite.title_status}` : 'Not generated'}
                  </span>
                </div>
                <p className="font-sans text-[10pt] text-ink font-medium">
                  {copySuite?.title || 'No title recommendation was generated.'}
                </p>
              </div>

              {/* Meta Description */}
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-[7.5pt]">
                  <span className="font-bold text-ink">RECOMMENDED META DESCRIPTION</span>
                  <span className="text-ink-600 font-bold">
                    {copySuite?.meta_description ? `${copySuite.meta_char_count} characters · ${copySuite.meta_status}` : 'Not generated'}
                  </span>
                </div>
                <p className="text-ink-700 font-sans leading-relaxed">
                  {copySuite?.meta_description || 'No meta description recommendation was generated.'}
                </p>
              </div>

              {/* H1 Heading Outline */}
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between font-mono text-[7.5pt]">
                  <span className="font-bold text-ink">RECOMMENDED PRIMARY H1 HEADLINE</span>
                  <span className="text-ink-500 font-mono">
                    {copySuite?.hero_headline ? `${headlineWords} words in this headline` : 'Not generated'}
                  </span>
                </div>
                <p className="font-sans text-[10.5pt] text-ink font-normal">
                  {copySuite?.hero_headline || 'No headline recommendation was generated.'}
                </p>
                {copySuite?.hero_subhead && (
                  <p className="font-mono text-[7.5pt] text-ink-500">
                    Headline and subhead together: {blockWords} words ({blockStatus} for the 40–60 word block). The headline count above is only the H1.
                  </p>
                )}
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
                <span className="font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded bg-warn/10 text-warn">
                  Suggested — not deployed
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
