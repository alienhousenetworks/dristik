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
            <div className="flex items-center justify-between pb-1 border-b border-line">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-700">
                Remediation Roadmap by Time Horizon
              </span>
              <span className="font-mono text-[7pt] text-ink-500">
                Total Items: {(priorities.roadmapNow?.length || 0) + (priorities.roadmapNext?.length || 0) + (priorities.roadmapOngoing?.length || 0)}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[8pt]">
              {/* NOW (Days 1 - 7) */}
              <div className="space-y-2 p-3 bg-paper-50 border border-line rounded flex flex-col justify-between">
                <div>
                  <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-bad/10 text-bad border border-bad/30 block w-fit">
                    PHASE 1 // NOW (DAYS 1–7)
                  </span>
                  <strong className="font-sans text-[9pt] text-ink block pt-1.5 pb-1">
                    Critical Blockers &amp; Quick Wins
                  </strong>
                  {priorities.roadmapNow && priorities.roadmapNow.length > 0 ? (
                    <ul className="text-ink-600 space-y-2 font-sans text-[7.5pt]">
                      {priorities.roadmapNow.slice(0, 4).map((item, i) => (
                        <li key={i} className="border-l-2 border-bad/40 pl-2 py-0.5">
                          <div className="font-semibold text-ink leading-tight">
                            {item.title || item.description}
                          </div>
                          <div className="font-mono text-[7pt] text-ink-500 mt-0.5 flex flex-wrap gap-1.5 items-center">
                            {item.priority_badge && (
                              <span className="text-bad font-bold">{item.priority_badge}</span>
                            )}
                            {item.owner_role && <span>· {item.owner_role}</span>}
                            {item.estimated_hours && <span>· {item.estimated_hours}</span>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-ink-500 font-sans text-[7.5pt] italic">No immediate blockers identified in current scan.</p>
                  )}
                </div>
              </div>

              {/* NEXT (Days 8 - 30) */}
              <div className="space-y-2 p-3 bg-paper-50 border border-line rounded flex flex-col justify-between">
                <div>
                  <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-warn/10 text-warn border border-warn/30 block w-fit">
                    PHASE 2 // NEXT (DAYS 8–30)
                  </span>
                  <strong className="font-sans text-[9pt] text-ink block pt-1.5 pb-1">
                    Entity &amp; Architecture Foundations
                  </strong>
                  {priorities.roadmapNext && priorities.roadmapNext.length > 0 ? (
                    <ul className="text-ink-600 space-y-2 font-sans text-[7.5pt]">
                      {priorities.roadmapNext.slice(0, 4).map((item, i) => (
                        <li key={i} className="border-l-2 border-warn/40 pl-2 py-0.5">
                          <div className="font-semibold text-ink leading-tight">
                            {item.title || item.description}
                          </div>
                          <div className="font-mono text-[7pt] text-ink-500 mt-0.5 flex flex-wrap gap-1.5 items-center">
                            {item.priority_badge && (
                              <span className="text-warn font-bold">{item.priority_badge}</span>
                            )}
                            {item.owner_role && <span>· {item.owner_role}</span>}
                            {item.estimated_hours && <span>· {item.estimated_hours}</span>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-ink-500 font-sans text-[7.5pt] italic">Foundation elements meet baseline standards.</p>
                  )}
                </div>
              </div>

              {/* ONGOING (Days 31 - 90) */}
              <div className="space-y-2 p-3 bg-paper-50 border border-line rounded flex flex-col justify-between">
                <div>
                  <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-good/10 text-good border border-good/30 block w-fit">
                    PHASE 3 // ONGOING (DAYS 31–90)
                  </span>
                  <strong className="font-sans text-[9pt] text-ink block pt-1.5 pb-1">
                    Strategic CRO &amp; AI Dominance
                  </strong>
                  {priorities.roadmapOngoing && priorities.roadmapOngoing.length > 0 ? (
                    <ul className="text-ink-600 space-y-2 font-sans text-[7.5pt]">
                      {priorities.roadmapOngoing.slice(0, 4).map((item, i) => (
                        <li key={i} className="border-l-2 border-good/40 pl-2 py-0.5">
                          <div className="font-semibold text-ink leading-tight">
                            {item.title || item.description}
                          </div>
                          <div className="font-mono text-[7pt] text-ink-500 mt-0.5 flex flex-wrap gap-1.5 items-center">
                            {item.priority_badge && (
                              <span className="text-good font-bold">{item.priority_badge}</span>
                            )}
                            {item.owner_role && <span>· {item.owner_role}</span>}
                            {item.estimated_hours && <span>· {item.estimated_hours}</span>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-ink-500 font-sans text-[7.5pt] italic">Continuous monitoring and regression verification active.</p>
                  )}
                </div>
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
