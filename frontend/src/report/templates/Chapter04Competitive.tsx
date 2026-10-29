import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter04CompetitiveProps {
  theme: ReportTheme;
  report: NormalizedReport;
  pageNumber?: number | string;
  chapterNumber?: string;
}

export function Chapter04Competitive({
  theme,
  report,
  pageNumber,
  chapterNumber = '04',
}: Chapter04CompetitiveProps) {
  const { competitive, meta } = report;
  const detailsPageNumber = typeof pageNumber === 'number' ? pageNumber + 1 : pageNumber;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber={chapterNumber}
        subtitle={competitive.chapterSubtitle || (competitive.isRealCompetitorDataAvailable ? "PEER-SET BENCHMARK & SCHEMA ENTITY MAPPING" : "SEMANTIC SCHEMA & MACHINE-READABLE ENTITY MAPPING")}
        title={competitive.chapterTitle || (competitive.isRealCompetitorDataAvailable ? "Competitive Intelligence & Knowledge Graph" : "Knowledge Graph & Entity Readiness")}
        description={competitive.chapterDescription || (competitive.isRealCompetitorDataAvailable ? "Machine-readable entity graph crosscheck, structured data verification, and head-to-head evaluation on commercial buyer queries against verified industry peers." : "Machine-readable entity graph crosscheck, structured data verification, and first-party semantic knowledge extraction.")}
        domain={meta.domain}
        whyThisMatters="Answer engines and search algorithms resolve queries against semantic knowledge graphs. Unstructured or ambiguous entity declarations dilute domain authority."
        howWeMeasuredIt={competitive.isRealCompetitorDataAvailable
          ? 'Schema.org types extracted from the sampled pages, plus the recorded competitor bake-off.'
          : 'Schema.org types extracted from the sampled pages. No competitor benchmark ran.'}
        whatWasAnalyzed={competitive.isRealCompetitorDataAvailable
          ? 'Structured data types on the sample and the recorded competitor bake-off.'
          : 'Structured data types on the sampled pages. Competitor queries were not run.'}
        pageNumber={typeof pageNumber === 'number' ? pageNumber : undefined}
      />

      {/* 2. Analytical Data Page */}
      <section
        id="ch_competitive"
        data-chapter-id="ch_competitive"
        className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
      >
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle={competitive.isRealCompetitorDataAvailable ? "04 / COMPETITIVE INTELLIGENCE // KNOWLEDGE GRAPH & PEER SET" : "04 / KNOWLEDGE GRAPH // ENTITY READINESS & SCHEMA"}
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Entity &amp; Peer Analysis
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              {competitive.isRealCompetitorDataAvailable ? "Knowledge Graph & Commercial Bake-Off" : "Knowledge Graph & Entity Readiness"}
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          {/* 4.1 Schema.org Knowledge Graph Health */}
          <div className="space-y-2">
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
              4.1 Schema.org types on the sample
            </h3>
            <table className="w-full text-[8.5pt] border-collapse border border-line">
              <tbody>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100 w-1/3">
                    Observed Schema.org Types
                  </th>
                  <td className="py-2 px-3 font-mono text-[8pt] text-ink">
                    {competitive.schemaTypes.length > 0
                      ? competitive.schemaTypes.join(', ')
                      : 'None observed on crawled sample nodes'}
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    Entity Graph Quality Standard
                  </th>
                  <td className="py-2 px-3 font-semibold text-ink">
                    {competitive.schemaAssessmentSummary}
                  </td>
                </tr>
                <tr className="border-b border-line">
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
                    Entity Graph Summary
                  </th>
                  <td className="py-2 px-3 text-ink-700 font-sans leading-relaxed">
                    {competitive.entitySummary}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 px-3 text-left font-semibold text-ink-600 bg-paper-100">
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
            <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
              {competitive.isRealCompetitorDataAvailable ? "4.2 Head-to-Head Commercial Inquiry Bake-Off" : "4.2 Competitive Benchmark & Peer Crawl Status"}
            </h3>

            {competitive.isRealCompetitorDataAvailable && competitive.bakeoffResults ? (
              <div className="space-y-3">
                <p className="text-[8.5pt] text-ink-700 font-sans">
                  Recorded competitor: <strong>{competitive.competitorName}</strong>. This bake-off is not a live citation measurement.
                </p>
                <div className="border border-line rounded divide-y divide-line text-[8pt]">
                  {(competitive.bakeoffResults.evaluations || []).slice(0, 4).map((row, i) => (
                    <div key={i} className="p-3 bg-paper-50 flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <strong className="font-sans text-[9pt] text-ink block">
                          "{row.question_title}"
                        </strong>
                        <p className="text-ink-600 font-sans">{row.commercial_takeaway}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="font-mono text-[8pt] font-bold px-2 py-0.5 rounded bg-good/10 text-good border border-good/30">
                          Winner: {row.winner}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* Honest Zero-Fake status notice when competitor crawl was not provisioned */
              <div className="p-4 rounded bg-paper-100 border border-line space-y-2.5 text-[8.5pt]">
                <div className="flex items-center justify-between pb-1 border-b border-line">
                  <span className="font-mono text-[8pt] font-bold uppercase text-ink-700">
                    Competitive Benchmark
                  </span>
                  <span className="font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded bg-paper-200 text-ink-700">
                    STATUS: NOT EXECUTED
                  </span>
                </div>
                <div className="space-y-1 font-sans">
                  <p className="font-mono text-[8pt] text-ink-600">
                    <strong>Reason:</strong> Competitor crawl connector unavailable or unprovisioned for this audit execution run.
                  </p>
                  <p className="text-ink-700 leading-relaxed">
                    No competitor score or simulated benchmark was generated. Under Dristik's strict Zero-Fake Evidence Standard, synthetic or simulated competitor metrics are never manufactured without a verified crawl artifact. Entity authority and Knowledge Graph crosscheck were evaluated independently against first-party structured data specifications.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* 4.3 Institutional Entity & Governance State Register (Point 13) */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between pb-1 border-b border-line">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                4.3 Institutional Entity &amp; Governance State Register
              </h3>
              <span className="font-mono text-[7pt] text-ink-500">
                Epistemic State Register (No Forced Binary Flags)
              </span>
            </div>

            <table className="w-full text-[8pt] border-collapse border border-line">
              <thead>
                <tr className="bg-paper-100 border-b border-line text-left font-mono text-[7pt] text-ink-600 uppercase">
                  <th className="py-1.5 px-3" style={{ width: '25%' }}>Entity / Dimension</th>
                  <th className="py-1.5 px-2" style={{ width: '18%' }}>Epistemic Status</th>
                  <th className="py-1.5 px-3">Evidence Observation &amp; Operational Caveat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line font-sans">
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-ink">Organization schema</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 border border-line font-bold">
                      {competitive.schemaTypes.some((type) => /organization/i.test(type)) ? 'PRESENT' : 'NOT RECORDED'}
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-ink-700 text-[7.5pt]">
                    {competitive.schemaTypes.some((type) => /organization/i.test(type))
                      ? 'Organization is among the schema types extracted from the sample. That is not an independent legal-identity verification.'
                      : 'Organization was not in the schema types extracted from the sample.'}
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-ink">Service schema</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 border border-line font-bold">
                      {competitive.schemaTypes.some((type) => /service/i.test(type)) ? 'PRESENT' : 'NOT RECORDED'}
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-ink-700 text-[7.5pt]">
                    {competitive.schemaTypes.some((type) => /service/i.test(type))
                      ? 'Service is among the schema types extracted from the sample.'
                      : 'Service was not in the schema types extracted from the sample.'}
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-ink">Pricing and compliance</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 border border-line font-bold">
                      NOT ASSESSED
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-ink-700 text-[7.5pt]">
                    This register does not check pricing pages or compliance attestations. Absence here is not a finding.
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-ink">Backlink authority</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-500 border border-line font-bold">
                      NOT MEASURED
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-ink-700 text-[7.5pt]">
                    No backlink provider was read for this run. The score is not affected.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={detailsPageNumber}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
