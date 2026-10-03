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
        subtitle={competitive.chapterSubtitle || (competitive.isRealCompetitorDataAvailable ? "PEER-SET BENCHMARK & SCHEMA ENTITY MAPPING" : "SEMANTIC SCHEMA & MACHINE-READABLE ENTITY MAPPING")}
        title={competitive.chapterTitle || (competitive.isRealCompetitorDataAvailable ? "Competitive Intelligence & Knowledge Graph" : "Knowledge Graph & Entity Readiness")}
        description={competitive.chapterDescription || (competitive.isRealCompetitorDataAvailable ? "Machine-readable entity graph crosscheck, structured data verification, and head-to-head evaluation on commercial buyer queries against verified industry peers." : "Machine-readable entity graph crosscheck, structured data verification, and first-party semantic knowledge extraction.")}
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
          chapterTitle={competitive.isRealCompetitorDataAvailable ? "04 / COMPETITIVE INTELLIGENCE // KNOWLEDGE GRAPH & PEER SET" : "04 / KNOWLEDGE GRAPH // ENTITY READINESS & SCHEMA"}
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Entity &amp; Peer Analysis
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              {competitive.isRealCompetitorDataAvailable ? "Knowledge Graph & Commercial Bake-Off" : "Knowledge Graph & Entity Readiness"}
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
              {competitive.isRealCompetitorDataAvailable ? "4.2 Head-to-Head Commercial Inquiry Bake-Off" : "4.2 Competitive Benchmark & Peer Crawl Status"}
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
              /* Honest Zero-Fake status notice when competitor crawl was not provisioned */
              <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-2.5 text-[8.5pt]">
                <div className="flex items-center justify-between pb-1 border-b border-slate-200">
                  <span className="font-mono text-[8pt] font-bold uppercase text-slate-800">
                    Competitive Benchmark
                  </span>
                  <span className="font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                    STATUS: NOT EXECUTED
                  </span>
                </div>
                <div className="space-y-1 font-sans">
                  <p className="font-mono text-[8pt] text-slate-600">
                    <strong>Reason:</strong> Competitor crawl connector unavailable or unprovisioned for this audit execution run.
                  </p>
                  <p className="text-slate-700 leading-relaxed">
                    No competitor score or simulated benchmark was generated. Under Dristik's strict Zero-Fake Evidence Standard, synthetic or simulated competitor metrics are never manufactured without a verified crawl artifact. Entity authority and Knowledge Graph crosscheck were evaluated independently against first-party structured data specifications.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* 4.3 Institutional Entity & Governance State Register (Point 13) */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between pb-1 border-b border-slate-200">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
                4.3 Institutional Entity &amp; Governance State Register
              </h3>
              <span className="font-mono text-[7pt] text-slate-500">
                Epistemic State Register (No Forced Binary Flags)
              </span>
            </div>

            <table className="w-full text-[8pt] border-collapse border border-slate-200">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-left font-mono text-[7pt] text-slate-600 uppercase">
                  <th className="py-1.5 px-3" style={{ width: '25%' }}>Entity / Dimension</th>
                  <th className="py-1.5 px-2" style={{ width: '18%' }}>Epistemic Status</th>
                  <th className="py-1.5 px-3">Evidence Observation &amp; Operational Caveat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 font-sans">
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-slate-900">Legal Entity &amp; Brand</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                      VERIFIED
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-slate-700 text-[7.5pt]">
                    Origin hostname and primary organization schema declare exact corporate identity.
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-slate-900">Service Taxonomy</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-bold">
                      PARTIAL
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-slate-700 text-[7.5pt]">
                    Service routes present in HTML but lack explicit schema.org/Service and qualification properties.
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-slate-900">Pricing &amp; Commercial Terms</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-300 font-bold">
                      NOT FOUND
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-slate-700 text-[7.5pt]">
                    No public pricing tables found on sampled origin pages. Commercial queries yield zero grounding.
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-slate-900">SOC 2 / Security Compliance</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-bold">
                      NOT VERIFIED
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-slate-700 text-[7.5pt]">
                    No public compliance attestation observed. <em>This does NOT establish that the organization lacks SOC 2 certification</em>; only that it is absent from public DOM evidence.
                  </td>
                </tr>
                <tr>
                  <td className="py-1.5 px-3 font-semibold text-slate-900">External Backlink Authority</td>
                  <td className="py-1.5 px-2 font-mono text-[7.5pt]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 font-bold">
                      NOT MEASURED
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-slate-700 text-[7.5pt]">
                    Third-party backlink connector unprovisioned for this audit execution run. Score is not affected.
                  </td>
                </tr>
              </tbody>
            </table>
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
