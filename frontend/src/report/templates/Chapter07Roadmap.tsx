import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter07RoadmapProps {
  theme: ReportTheme;
  report: NormalizedReport;
  pageNumber?: number | string;
  chapterNumber?: string;
}

export function Chapter07Roadmap({
  theme,
  report,
  pageNumber,
  chapterNumber = '07',
}: Chapter07RoadmapProps) {
  const { priorities, meta, remediation } = report;
  const detailsPageNumber = typeof pageNumber === 'number' ? pageNumber + 1 : pageNumber;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber={chapterNumber}
        subtitle="ENGINEERING ACTION PLAN &amp; 90-DAY MILESTONES"
        title="Strategic Priorities &amp; Implementation Roadmap"
        description="Prioritized, phased execution blueprint designed for immediate engineering deployment. Formulates exact file path remedies, impact × effort rankings, and expected commercial returns."
        domain={meta.domain}
        whyThisMatters="Discoverability audits only deliver enterprise value when translated into deterministic code changes and prioritized engineering sprints."
        howWeMeasuredIt="Algorithmic impact vs. effort scoring, developer implementation hour estimation, and closed-loop verification acceptance tests."
        whatWasAnalyzed="Top-10 executive remediation items, 3-phase execution timeline (NOW / NEXT / ONGOING), and estimated commercial upside."
        pageNumber={typeof pageNumber === 'number' ? pageNumber : undefined}
      />

      {/* 2. Analytical Data Page - Action Plan & Roadmap */}
      <section
        id="ch_roadmap"
        data-chapter-id="ch_roadmap"
        className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
      >
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="07 / STRATEGIC PRIORITIES // ACTION PLAN & ROADMAP"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Phased Execution
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              Executive Top-10 Action Plan
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          {/* Top 10 Actions Table */}
          <div className="space-y-2">
            <table className="w-full text-[8pt] border-collapse border border-line">
              <thead>
                <tr className="bg-paper-100 border-b border-line text-left font-mono text-[7.5pt] text-ink-600 uppercase">
                  <th className="py-2 px-2" style={{ width: '5%' }}>#</th>
                  <th className="py-2 px-3" style={{ width: '28%' }}>Remediation Action &amp; Area</th>
                  <th className="py-2 px-3" style={{ width: '12%' }}>Impact</th>
                  <th className="py-2 px-3" style={{ width: '12%' }}>Effort</th>
                  <th className="py-2 px-3">Expected Commercial Outcome &amp; Validation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {priorities.top10Actions.map((act) => (
                  <tr key={act.rank} className="hover:bg-paper-100">
                    <td className="py-2 px-2 font-mono font-bold text-ink">
                      {act.rank}
                    </td>
                    <td className="py-2 px-3 font-semibold text-ink font-sans">
                      {act.action}
                      <span className="font-mono text-[7pt] text-ink-500 block mt-0.5">
                        Priority: {act.priority} · Ref: {act.findingId || `ACT_${act.rank}`}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="font-mono font-bold text-good bg-good/10 px-1.5 py-0.5 rounded border border-good/30 text-[7.5pt]">
                        {act.impact}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[7.5pt] text-ink-700">
                      {act.effort || '—'}{act.engineerHours != null ? ` (${act.engineerHours}h)` : ''}
                    </td>
                    <td className="py-2 px-3 text-ink-700 font-sans leading-relaxed">
                      {act.outcome}
                      <em className="text-ink-500 block text-[7.5pt] mt-0.5">Acceptance: {act.validation}</em>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-3.5 bg-paper-100 border border-line rounded space-y-2 text-[8pt]">
            <div className="flex items-center justify-between pb-1 border-b border-line">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                Remediation state
              </span>
              <span className="font-mono text-[7pt] font-bold px-1.5 py-0.5 rounded bg-paper-200 text-ink-700 border border-line">
                {remediation.label}
              </span>
            </div>
            <p className="font-sans text-ink-700 leading-relaxed">{remediation.detail}</p>
            <p className="font-mono text-[7pt] text-ink-500">
              Recommendation, generated patch, applied change, and independently verified fix are separate states.
            </p>
          </div>

          {/* Editorial NOW / NEXT / ONGOING Roadmap Tree */}
          <div className="p-4 rounded bg-paper-100 border border-line space-y-4">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-700 block pb-1 border-b border-line">
              Editorial 90-Day Implementation Timeline
            </span>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[8pt]">
              {/* NOW (Days 1 - 7) */}
              <div className="space-y-1.5 p-3 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-bad/10 text-bad border border-bad/30 block w-fit">
                  PHASE 1 // NOW (DAYS 1–7)
                </span>
                <strong className="font-sans text-[9pt] text-ink block pt-1">
                  Fix Technical Blockers
                </strong>
                <ul className="text-ink-600 space-y-1 list-disc pl-4 font-sans text-[7.5pt]">
                  <li>Deploy canonical 301 consolidation patches</li>
                  <li>Resolve broken redirect chains and 404 targets</li>
                  <li>Publish /llms.txt AI crawler permission manifesto</li>
                </ul>
              </div>

              {/* NEXT (Days 8 - 30) */}
              <div className="space-y-1.5 p-3 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-warn/10 text-warn border border-warn/30 block w-fit">
                  PHASE 2 // NEXT (DAYS 8–30)
                </span>
                <strong className="font-sans text-[9pt] text-ink block pt-1">
                  Strengthen Entity Signals
                </strong>
                <ul className="text-ink-600 space-y-1 list-disc pl-4 font-sans text-[7.5pt]">
                  <li>Deploy JSON-LD Organization &amp; Service schemas</li>
                  <li>Implement character-safe title and meta tag pairs</li>
                  <li>Inject factual entity attribution passages</li>
                </ul>
              </div>

              {/* ONGOING (Days 31 - 90) */}
              <div className="space-y-1.5 p-3 bg-paper-50 border border-line rounded">
                <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-good/10 text-good border border-good/30 block w-fit">
                  PHASE 3 // ONGOING (DAYS 31–90)
                </span>
                <strong className="font-sans text-[9pt] text-ink block pt-1">
                  Assurance &amp; Governance
                </strong>
                <ul className="text-ink-600 space-y-1 list-disc pl-4 font-sans text-[7.5pt]">
                  <li>Closed-loop remediation verification against AST</li>
                  <li>Continuous regression monitoring across 100 queries</li>
                  <li>Monthly answer engine citation re-evaluation</li>
                </ul>
              </div>
            </div>
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
