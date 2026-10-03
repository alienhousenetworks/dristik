import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter04CompetitiveProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function Chapter04Competitive({
  theme,
  report,
}: Chapter04CompetitiveProps) {
  const { competitive, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="04"
        subtitle="PEER-SET BENCHMARK &amp; SCHEMA ENTITY MAPPING"
        title="Competitive Intelligence &amp; Knowledge Graph"
        description="Machine-readable entity graph crosscheck, structured data verification, and head-to-head evaluation on commercial buyer queries against verified industry peers."
        domain={meta.domain}
        whyThisMatters="Answer engines and search algorithms resolve queries against semantic knowledge graphs. Unstructured or ambiguous entity declarations dilute domain authority."
        howWeMeasuredIt="Schema.org JSON-LD AST extraction, knowledge graph reconciliation, and head-to-head empirical query bake-offs."
        whatWasAnalyzed="Structured data types (Organization, WebSite, Service, FAQ), OpenGraph consistency, and verified commercial query winners."
        pageNumber={12}
      />

      {/* 2. Analytical Data Page */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="04 / COMPETITIVE INTELLIGENCE // KNOWLEDGE GRAPH & PEER SET"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Entity &amp; Peer Analysis
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              Knowledge Graph &amp; Commercial Bake-Off
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          {/* 4.1 Schema.org Knowledge Graph Health */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              4.1 Schema.org Structured Entity Verification
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-slate-200">
              <tbody>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50 w-1/3">
                    Observed Schema.org Types
                  </th>
                  <td className="py-2 px-3 font-mono text-[8pt] text-slate-900">
                    {competitive.schemaTypes.length > 0
                      ? competitive.schemaTypes.join(', ')
                      : 'None observed on crawled sample nodes'}
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    Entity Graph Quality Standard
                  </th>
                  <td className="py-2 px-3 font-semibold text-slate-900">
                    {competitive.schemaAssessmentSummary}
                  </td>
                </tr>
                <tr className="border-b border-slate-200">
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    Entity Graph Summary
                  </th>
                  <td className="py-2 px-3 text-slate-700 font-sans leading-relaxed">
                    {competitive.entitySummary}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 px-3 text-left font-semibold text-slate-600 bg-slate-50">
                    Social Graph Metadata (OG / Twitter)
                  </th>
                  <td className="py-2 px-3 font-mono text-[8pt]">
                    {competitive.socialMetaStatus}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 4.2 Head-to-Head Commercial Bake-Off (Strict Zero-Fake Rule) */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
              4.2 Head-to-Head Commercial Inquiry Bake-Off
            </h3>

            {competitive.isRealCompetitorDataAvailable && competitive.bakeoffResults ? (
              <div className="space-y-3">
                <p className="text-[8.5pt] text-slate-700 font-sans">
                  Head-to-head empirical testing against verified market peer: <strong>{competitive.competitorName}</strong>
                </p>
                <div className="border border-slate-200 rounded divide-y divide-slate-200 text-[8pt]">
                  {(competitive.bakeoffResults.evaluations || []).slice(0, 4).map((row, i) => (
                    <div key={i} className="p-3 bg-white flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <strong className="font-serif text-[9pt] text-slate-900 block">
                          "{row.question_title}"
                        </strong>
                        <p className="text-slate-600 font-sans">{row.commercial_takeaway}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                          Winner: {row.winner}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* Honest zero-fake notice when competitor crawl was not provisioned */
              <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2 text-[8.5pt]">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[8pt] font-bold uppercase px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                    PEER CRAWL STATUS: INDEPENDENT EVALUATION
                  </span>
                </div>
                <p className="text-slate-700 font-sans leading-relaxed">
                  A direct peer website crawl was not provisioned for this audit execution run. Under Dristik's strict Zero-Fake Evidence Standard, synthetic or placeholder competitor data is never generated. Entity authority and Knowledge Graph crosscheck were evaluated independently against first-party structured data specifications.
                </p>
              </div>
            )}
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={13}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
