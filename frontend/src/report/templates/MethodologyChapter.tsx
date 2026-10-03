import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface MethodologyChapterProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function MethodologyChapter({
  theme,
  report,
}: MethodologyChapterProps) {
  const { methodology, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="08"
        subtitle="RESEARCH METHODOLOGY &amp; SAMPLING PROTOCOL"
        title="Inspection Methodology &amp; Governance"
        description="Formal operational specifications governing crawler parameters, AST decomposition rules, multi-model query sampling, and cryptographic evidence hashing standards."
        domain={meta.domain}
        whyThisMatters="Institutional assurance mandates transparent, repeatable measurement protocols with explicit limitations and zero synthetic data interpolation."
        howWeMeasuredIt="Headless Chromium DOM crawling, deterministic AST traversal, verbatim multi-model prompt execution, and SHA-256 evidence hashing."
        whatWasAnalyzed="Origin crawl boundaries, response latency curves, 100-question commercial sandbox models, and WCAG accessibility standards."
        pageNumber={20}
      />

      {/* 2. Methodology Details Page */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="08 / METHODOLOGY // SPECIFICATIONS & SAMPLING"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Inspection Specifications
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              Audit Scope &amp; Assurance Standards
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          {/* Core Methodology Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[8.5pt]">
            <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block">
                01 // CRAWL SCOPE &amp; BOUNDARIES
              </span>
              <p className="text-slate-800 font-sans leading-relaxed">
                The audit traversed {methodology.sampledPagesCount} primary origin routes up to a maximum depth of {methodology.crawlDepth} hops. Crawl directives adhere strictly to standard user-agent rules and respectful latency caps.
              </p>
            </div>

            <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block">
                02 // CRYPTOGRAPHIC ZERO-FAKE SEAL
              </span>
              <p className="text-slate-800 font-sans leading-relaxed">
                Every extracted statement is hashed with SHA-256 and stamped with an exact DOM selector. Synthesizing or fabricating findings without traceable evidence violates Dristik's core governance engine.
              </p>
            </div>

            <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block">
                03 // AI ANSWER ENGINE TESTING PROTOCOL
              </span>
              <p className="text-slate-800 font-sans leading-relaxed">
                Evaluations executed across live endpoints for ChatGPT Search, Perplexity AI, Google AI Overviews, Claude, and Gemini. Citations require explicit, unambiguous brand attribution.
              </p>
            </div>

            <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block">
                04 // SCORING ENGINE &amp; WEIGHTING
              </span>
              <p className="text-slate-800 font-sans leading-relaxed">
                Composite scores are continuous (0–100) and weighted across Technical Discoverability (30%), Generative Extractability (25%), Answer Engine Citations (25%), and CRO Conversion (20%).
              </p>
            </div>
          </div>

          {/* Known Operational Limitations */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8.5pt]">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block">
              Known Operational Limitations &amp; Disclaimers
            </span>
            <ul className="text-slate-700 space-y-1.5 list-disc pl-4 font-sans text-[8pt] leading-relaxed">
              {methodology.knownLimitations.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={21}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
