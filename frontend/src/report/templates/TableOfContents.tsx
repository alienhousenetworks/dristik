import React from 'react';
import { ReportTheme } from '../brandTheme';
import { PageHeader, PageFooter } from './PageHeaderFooter';
import { PublicationManifest, PublicationChapterDescriptor } from '../adaptivePublication';
import { PaginationState } from '../paginationEngine';

interface TableOfContentsProps {
  theme: ReportTheme;
  domain: string;
  brandName?: string;
  analysisId?: string;
  dateStr?: string;
  isRealCompetitorDataAvailable?: boolean;
  manifest?: PublicationManifest;
  pagination?: PaginationState;
  pageNumber?: string | number;
}

export function TableOfContents({
  theme,
  domain,
  brandName,
  analysisId,
  dateStr,
  isRealCompetitorDataAvailable = false,
  manifest,
  pagination,
  pageNumber = 'ii',
}: TableOfContentsProps) {
  // Use chapters from manifest if provided, or default fallback
  const chapters: PublicationChapterDescriptor[] = manifest?.chapters || [
    {
      id: 'ch_brief',
      number: '00',
      part: 'PART I: EXECUTIVE DIAGNOSTIC & BASELINE',
      title: 'Executive Brief & Audit Snapshot',
      shortTitle: 'EXECUTIVE BRIEF',
      description: 'High-level synthesis, 4 core signals, 5-Pillar Scorecard, and Tri-Perspective cognitive diagnosis.',
    },
    {
      id: 'ch_seo',
      number: '01',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Discoverability & Technical SEO',
      shortTitle: 'TECHNICAL SEO',
      description: 'Crawl architecture, canonical host routing, 301 consolidation, TTFB latency curves, robots.txt directives, and XML sitemaps.',
    },
    {
      id: 'ch_geo',
      number: '02',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Generative Engine Optimization (GEO)',
      shortTitle: 'GEO READINESS',
      description: 'Layer 1 first-party DOM extractability, 8-dimension breakdown, /llms.txt AI-bot permissions, and entity attribution rewrites.',
    },
    {
      id: 'ch_aeo',
      number: '03',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Answer Engine Visibility (AEO)',
      shortTitle: 'AEO CITATIONS',
      description: 'Layer 2 live visibility across ChatGPT, Perplexity, Google AIO, Claude & Gemini. 100-Question dynamic sandbox digest.',
    },
    {
      id: 'ch_competitive',
      number: '04',
      part: 'PART II: AUDIT CHAPTERS',
      title: isRealCompetitorDataAvailable
        ? 'Competitive Intelligence & Knowledge Graph'
        : 'Knowledge Graph & Entity Readiness',
      shortTitle: 'COMPETITIVE INTELLIGENCE',
      description: isRealCompetitorDataAvailable
        ? 'Recorded competitor bake-off, schema types extracted from the sample, and social meta presence.'
        : 'Schema types extracted from the sample and unmeasured competitor benchmark notice.',
    },
    {
      id: 'ch_conversion',
      number: '05',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Conversion Ergonomics & Production Copy',
      shortTitle: 'CONVERSION ERGONOMICS',
      description: 'Crawled value-proposition copy, CTA hierarchy, and character counts on generated copy.',
    },
    {
      id: 'ch_page_by_page',
      number: '06',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Page-by-Page Audit Review',
      shortTitle: 'PAGE-BY-PAGE REVIEW',
      description: 'Sampled URL inventory: SERP metadata, H1 outlines, and copy recommendations for the analyzed URLs.',
    },
    {
      id: 'ch_roadmap',
      number: '07',
      part: 'PART III: REMEDIATION & GOVERNANCE',
      title: 'Strategic Priorities & 90-Day Roadmap',
      shortTitle: '90-DAY ROADMAP',
      description: 'Executive Top-10 Action Plan with effort/impact calculations, NOW / NEXT / ONGOING roadmap, and commercial model.',
    },
    {
      id: 'ch_methodology',
      number: '08',
      part: 'PART III: REMEDIATION & GOVERNANCE',
      title: 'Research Methodology & Sampling Parameters',
      shortTitle: 'METHODOLOGY',
      description: 'Audit scope, crawl depth boundaries, multi-engine testing protocol, confidence algorithms, and operational limitations.',
    },
    {
      id: 'ch_appendix',
      number: '09',
      part: 'PART IV: APPENDICES & TECHNICAL REGISTERS',
      title: 'Institutional Findings Register & Evidence Ledger',
      shortTitle: 'EVIDENCE REGISTERS',
      description: 'Exhaustive verified defect register, production code patches with file paths, and cryptographic SHA-256 AST ledger.',
      isAppendix: true,
    },
  ];

  // Group chapters by Part
  const parts: Array<{ partTitle: string; items: PublicationChapterDescriptor[] }> = [];
  chapters.forEach((ch) => {
    const partName = ch.part || 'MAIN AUDIT BODY';
    let existingPart = parts.find((p) => p.partTitle === partName);
    if (!existingPart) {
      existingPart = { partTitle: partName, items: [] };
      parts.push(existingPart);
    }
    existingPart.items.push(ch);
  });

  return (
    <section
      data-chapter-id="front_matter_toc"
      className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
    >
      <PageHeader
        theme={theme}
        domain={domain}
        chapterTitle="TABLE OF CONTENTS // DOCUMENT ARCHITECTURE"
      />

      <div className="space-y-6 max-w-4xl my-auto py-2">
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Publication Index &amp; Information Architecture
          </span>
          <h2 className="font-serif text-[24pt] md:text-[28pt] font-normal tracking-tight text-ink">
            Table of Contents
          </h2>
          <div className="bg-ink w-10 h-px mt-2" />
        </div>

        {/* Dynamic Part & Chapter Tree with Leader Dots & Real Page Numbers */}
        <div className="space-y-5 border-t border-b border-line py-3">
          {/* Front Matter Line */}
          <div className="space-y-1">
            <div className="font-mono text-[7pt] font-extrabold uppercase tracking-[0.08em] text-ink-400">
              FRONT MATTER
            </div>
            <div className="flex items-baseline justify-between text-[8.5pt]">
              <div className="flex items-baseline gap-2 flex-1">
                <span className="font-mono font-bold text-ink-400 w-7">FM</span>
                <span className="font-sans font-semibold text-ink">
                  Document Identification &amp; Measurement Scope
                </span>
                <span className="flex-1 border-b border-dotted border-ink-300 mx-2 mb-1" />
              </div>
              <span className="font-mono font-semibold text-ink-500 pl-2">
                p. i
              </span>
            </div>
          </div>

          {/* Body Parts */}
          {parts.map((p) => (
            <div key={p.partTitle} className="space-y-1.5">
              <div className="font-mono text-[7pt] font-extrabold uppercase tracking-[0.08em] text-ink-500 border-t border-line/60 pt-2">
                {p.partTitle}
              </div>

              {p.items.map((ch) => {
                const targetPage = pagination?.locations[ch.id]?.logicalPageNumber;
                const pageLabel = targetPage != null ? `p. ${targetPage}` : 'p. —';

                return (
                  <div key={ch.id} className="py-1">
                    <div className="flex items-baseline justify-between text-[8.5pt]">
                      <a
                        href={`#${ch.id}`}
                        className="flex items-baseline gap-2 flex-1 hover:text-sky-700 transition-colors group"
                      >
                        <span className="font-mono font-bold text-ink-500 w-7">
                          {ch.number}
                        </span>
                        <span className="font-sans font-bold text-ink text-[9pt] group-hover:underline">
                          {ch.title}
                        </span>
                        <span className="flex-1 border-b border-dotted border-ink-300 mx-2 mb-1" />
                      </a>
                      <span className="font-mono font-bold text-ink-700 pl-2">
                        {pageLabel}
                      </span>
                    </div>
                    {ch.description && (
                      <p className="text-ink-600 font-sans text-[7.5pt] leading-relaxed pl-9 pr-12">
                        {ch.description}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          ))}

          {/* Closing Attestation Line */}
          <div className="pt-2 border-t border-line/60">
            <div className="flex items-baseline justify-between text-[8.5pt]">
              <div className="flex items-baseline gap-2 flex-1">
                <span className="font-mono font-bold text-ink-400 w-7">FIN</span>
                <span className="font-sans font-semibold text-ink">
                  Audit Assurance Seal &amp; Governance Attestation
                </span>
                <span className="flex-1 border-b border-dotted border-ink-300 mx-2 mb-1" />
              </div>
              <span className="font-mono font-semibold text-ink-500 pl-2">
                p. {pagination?.locations['closing_page']?.logicalPageNumber != null ? pagination.locations['closing_page'].logicalPageNumber : 'End'}
              </span>
            </div>
          </div>
        </div>

        {/* Summary Footer Notice */}
        <div className="p-3 rounded bg-paper-100 border border-line flex items-center justify-between text-[7.5pt] font-mono text-ink-600">
          <span>
            {pagination?.status === 'STABLE_CONVERGED'
              ? '✓ STABLE PAGINATION SEALED'
              : 'PAGINATION CONVERGING'}
          </span>
          <span>
            {manifest ? `${manifest.chapters.length} Active Chapters · ${pagination?.totalPhysicalPages || 24} Total Pages` : ''}
          </span>
        </div>
      </div>

      <PageFooter
        theme={theme}
        domain={domain}
        pageNumber={pageNumber}
        reportId={analysisId}
        dateStr={dateStr}
      />
    </section>
  );
}
