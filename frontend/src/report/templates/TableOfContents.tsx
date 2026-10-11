import React from 'react';
import { ReportTheme } from '../brandTheme';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface TableOfContentsProps {
  theme: ReportTheme;
  domain: string;
  brandName: string;
  analysisId: string;
  dateStr: string;
  isRealCompetitorDataAvailable?: boolean;
}

export function getChapterDirectory(isRealCompetitorDataAvailable: boolean = false) {
  return [
    {
      num: '00',
      title: 'Executive Brief & Audit Snapshot',
      desc: 'High-level synthesis, 4 core signals, 5-Pillar Scorecard, Tri-Perspective cognitive diagnosis, and visual diagnostic matrix.',
      pageEst: 3,
    },
    {
      num: '01',
      title: 'Discoverability & Technical SEO',
      desc: 'Crawl architecture, canonical host routing, 301 consolidation, TTFB latency curves, robots.txt directives, and XML sitemaps.',
      pageEst: 5,
    },
    {
      num: '02',
      title: 'Generative Engine Optimization (GEO)',
      desc: 'Layer 1 first-party DOM extractability, 8-dimension breakdown, /llms.txt AI-bot permissions, and entity attribution rewrites.',
      pageEst: 8,
    },
    {
      num: '03',
      title: 'Answer Engine Visibility (AEO)',
      desc: 'Layer 2 live visibility across ChatGPT, Perplexity, Google AIO, Claude & Gemini. 100-Question dynamic sandbox digest & Re-Query uplift delta.',
      pageEst: 11,
    },
    {
      num: '04',
      title: isRealCompetitorDataAvailable
        ? 'Competitive Intelligence & Knowledge Graph'
        : 'Knowledge Graph & Entity Readiness',
      desc: isRealCompetitorDataAvailable
        ? 'Recorded competitor bake-off, schema types extracted from the sample, and social meta presence.'
        : 'Schema types extracted from the sample, social meta presence, and the unmeasured competitor benchmark.',
      pageEst: 14,
    },
  {
    num: '05',
    title: 'Conversion Ergonomics & Production Copy',
    desc: 'Crawled value-proposition copy, form screening when a form audit ran, and character counts on generated copy. Not a timed test or a WCAG certification.',
    pageEst: 16,
  },
  {
    num: '06',
    title: 'Page-by-Page Audit Review',
    desc: 'Sampled URL inventory only: SERP metadata, H1 outlines, and copy recommendations for the analyzed URLs.',
    pageEst: 18,
  },
  {
    num: '07',
    title: 'Strategic Priorities & 90-Day Roadmap',
    desc: 'Executive Top-10 Action Plan with effort/impact calculations, NOW / NEXT / ONGOING roadmap, and commercial financial model.',
    pageEst: 20,
  },
  {
    num: '08',
    title: 'Research Methodology & Sampling Parameters',
    desc: 'Audit scope, crawl depth boundaries, multi-engine testing protocol, confidence algorithms, and known operational limitations.',
    pageEst: 22,
  },
  {
    num: '09',
    title: 'Institutional Findings Register & Evidence Ledger',
    desc: 'Exhaustive verified defect register, production code patches with file paths, cryptographic verification proofs, and SHA-256 AST ledger.',
    pageEst: 23,
  },
];
}

export const CHAPTER_DIRECTORY = getChapterDirectory(false);

export function TableOfContents({
  theme,
  domain,
  brandName,
  analysisId,
  dateStr,
  isRealCompetitorDataAvailable = false,
}: TableOfContentsProps) {
  const chapters = getChapterDirectory(isRealCompetitorDataAvailable);

  return (
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
      <PageHeader theme={theme} domain={domain} chapterTitle="TABLE OF CONTENTS // DOCUMENT ARCHITECTURE" />

      <div className="space-y-6">
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Publication Index &amp; Information Architecture
          </span>
          <h2 className="font-serif text-[24pt] md:text-[28pt] font-normal tracking-tight text-ink">
            Table of Contents
          </h2>
          <div className="bg-ink w-10 h-px mt-2" />
        </div>

        {/* Chapter Table */}
        <div className="divide-y divide-line border-t border-b border-line">
          {chapters.map((ch) => (
            <div key={ch.num} className="py-2.5 flex items-start justify-between gap-4 text-[8.5pt]">
              <div className="flex items-start gap-3 flex-1">
                <span className="font-mono font-bold text-ink-400 w-6 pt-0.5">
                  {ch.num}
                </span>
                <div>
                  <h3 className="font-sans font-bold text-ink text-[10pt] leading-tight">
                    {ch.title}
                  </h3>
                  <p className="text-ink-600 font-sans text-[8pt] leading-relaxed mt-0.5">
                    {ch.desc}
                  </p>
                </div>
              </div>
              <div className="font-mono text-[8.5pt] text-ink-400 pt-0.5">
                p. {ch.pageEst}
              </div>
            </div>
          ))}
        </div>

        {/* "How to Read This Report" - Dual Layer Architecture */}
        <div className="p-4 rounded bg-paper-100 border border-line mt-6 text-[8.5pt]">
          <h4 className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-700 mb-2">
            HOW TO READ THIS PUBLICATION: DUAL-LAYER GOVERNANCE
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-ink-700 leading-relaxed font-sans">
            <div>
              <strong className="text-ink block font-sans text-[9pt] mb-0.5">
                1. Executive Narrative Layer (Pages 3 – 21)
              </strong>
              Designed for board and executive leadership. Synthesizes macro performance signals, competitive standing, conversion ergonomics, and the 90-day commercial impact roadmap.
            </div>
            <div>
              <strong className="text-ink block font-sans text-[9pt] mb-0.5">
                2. Technical Evidence &amp; Proof Layer (Pages 22+)
              </strong>
              Designed for engineering and search teams. Provides deterministic AST proof, exact code patch diffs, file paths, and cryptographic SHA-256 evidence IDs for every single claim.
            </div>
          </div>
        </div>
      </div>

      <PageFooter
        theme={theme}
        domain={domain}
        pageNumber={2}
        reportId={analysisId}
        dateStr={dateStr}
      />
    </section>
  );
}
