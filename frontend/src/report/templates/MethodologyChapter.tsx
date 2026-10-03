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
                04 // SCORING ENGINE &amp; MATHEMATICAL TRANSPARENCY
              </span>
              <p className="text-slate-800 font-sans leading-relaxed">
                Composite scores are continuous (0–100) and deterministically derived from verified pillar results: Technical Discoverability (30%), Generative Extractability (25%), Answer Engine Citations (25%), and CRO &amp; Value Proposition (20%). Every score is auditable in the Score Calculation Ledger with exact contribution arithmetic.
              </p>
            </div>
          </div>

          {/* 16-Stage Dristik Enterprise Pipeline Architecture (Point 18) */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8pt]">
            <div className="flex items-center justify-between pb-1 border-b border-slate-200">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700">
                End-to-End Enterprise Intelligence Pipeline (16-Stage Deterministic Graph)
              </span>
              <span className="font-mono text-[7pt] text-slate-500">
                Every Output Retains an Immutable EvidenceRef
              </span>
            </div>

            <div className="p-3 bg-white border border-slate-200 rounded font-mono text-[7pt] overflow-x-auto text-slate-800 leading-relaxed whitespace-pre-wrap">
              DISCOVER → CRAWL → NORMALIZE → EVIDENCE GRAPH → COVERAGE ANALYSIS → DETERMINISTIC MEASUREMENT
                 ↓
              REASONERS: [ Technical SEO ∥ GEO Extraction ∥ CRO Conversion ]
                 ↓
              CROSS-ANALYST CORRELATION → CONTRADICTION ENGINE &amp; CRITIC → SYNTHESIS &amp; SCORING
                 ↓
              DEFECT PRIORITIZATION → REMEDIATION PATCH GENERATOR → STAGING APPLY → AUTOMATED RECRAWL → VERIFY → MONITOR
            </div>
          </div>

          {/* 4-Layer AI Visibility Architecture (Point 10) */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8pt]">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block pb-1 border-b border-slate-200">
              4-Layer AI Visibility &amp; Citability Architecture
            </span>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 font-sans text-[7.5pt]">
              <div className="bg-white p-2.5 rounded border border-slate-200 space-y-1">
                <span className="font-mono font-bold text-[7pt] text-slate-500 block">LAYER 1 // SURFACE</span>
                <strong className="text-slate-900 block">Website Evidence</strong>
                <p className="text-slate-600 text-[7pt]">
                  DOM AST, HTML structure, HTTP headers, Schema.org, robots.txt, and TTFB latency.
                </p>
              </div>

              <div className="bg-white p-2.5 rounded border border-slate-200 space-y-1">
                <span className="font-mono font-bold text-[7pt] text-slate-500 block">LAYER 2 // EXTRACTION</span>
                <strong className="text-slate-900 block">Extractability</strong>
                <p className="text-slate-600 text-[7pt]">
                  Ability of LLM parsers &amp; search spiders to cleanly extract entity facts without ambiguity.
                </p>
              </div>

              <div className="bg-white p-2.5 rounded border border-slate-200 space-y-1">
                <span className="font-mono font-bold text-[7pt] text-slate-500 block">LAYER 3 // CITATION</span>
                <strong className="text-slate-900 block">Retrieval &amp; Citation</strong>
                <p className="text-slate-600 text-[7pt]">
                  Empirical frequency with which live answer engines cite the domain on buyer queries.
                </p>
              </div>

              <div className="bg-white p-2.5 rounded border border-slate-200 space-y-1">
                <span className="font-mono font-bold text-[7pt] text-slate-500 block">LAYER 4 // ACCURACY</span>
                <strong className="text-slate-900 block">Answer Quality</strong>
                <p className="text-slate-600 text-[7pt]">
                  Degree to which AI-generated answers accurately convey ICP, capabilities, and pricing.
                </p>
              </div>
            </div>
          </div>

          {/* 5-Tier Epistemic Evidence Classification (Point 9) */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8pt]">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block pb-1 border-b border-slate-200">
              5-Tier Epistemic Evidence Classification
            </span>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-2 font-mono text-[7pt]">
              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="text-emerald-700 font-bold block">1. OBSERVED</span>
                <p className="font-sans text-[6.8pt] text-slate-600 mt-0.5">
                  Directly captured DOM text, HTTP headers, status codes, SHA-256 sealed.
                </p>
              </div>

              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="text-blue-700 font-bold block">2. MEASURED</span>
                <p className="font-sans text-[6.8pt] text-slate-600 mt-0.5">
                  Calculated directly from observed data (e.g. latency, extractability index).
                </p>
              </div>

              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="text-amber-700 font-bold block">3. DERIVED</span>
                <p className="font-sans text-[6.8pt] text-slate-600 mt-0.5">
                  Model-derived estimations (commercial value at risk, query answerability).
                </p>
              </div>

              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="text-purple-700 font-bold block">4. RECOMMENDED</span>
                <p className="font-sans text-[6.8pt] text-slate-600 mt-0.5">
                  Prescriptive code remediation patches and strategic architecture proposals.
                </p>
              </div>

              <div className="bg-white p-2 rounded border border-slate-200">
                <span className="text-slate-700 font-bold block">5. UNMEASURED</span>
                <p className="font-sans text-[6.8pt] text-slate-600 mt-0.5">
                  Unexecuted dimensions explicitly labeled rather than estimated or simulated.
                </p>
              </div>
            </div>
          </div>

          {/* Known Operational Limitations & What Dristik Does NOT Know */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8.5pt]">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block">
              Known Operational Limitations &amp; Epistemic Boundaries
            </span>
            <ul className="text-slate-700 space-y-1.5 list-disc pl-4 font-sans text-[8pt] leading-relaxed">
              {methodology.knownLimitations.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
              <li>
                <strong>Epistemic Boundary ("What Dristik Does NOT Know"):</strong> Uncrawled routes, private intranet endpoints, authenticated portals, and third-party commercial transaction databases remain strictly outside this audit. Absence of public proof (e.g. SOC 2 attestation) does not establish absence of institutional compliance.
              </li>
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
