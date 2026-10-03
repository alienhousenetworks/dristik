import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface Chapter07RoadmapProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function Chapter07Roadmap({
  theme,
  report,
}: Chapter07RoadmapProps) {
  const { priorities, meta } = report;

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="07"
        subtitle="ENGINEERING ACTION PLAN &amp; 90-DAY MILESTONES"
        title="Strategic Priorities &amp; Implementation Roadmap"
        description="Prioritized, phased execution blueprint designed for immediate engineering deployment. Formulates exact file path remedies, impact × effort rankings, and expected commercial returns."
        domain={meta.domain}
        whyThisMatters="Discoverability audits only deliver enterprise value when translated into deterministic code changes and prioritized engineering sprints."
        howWeMeasuredIt="Algorithmic impact vs. effort scoring, developer implementation hour estimation, and closed-loop verification acceptance tests."
        whatWasAnalyzed="Top-10 executive remediation items, 3-phase execution timeline (NOW / NEXT / ONGOING), and estimated commercial upside."
        pageNumber={18}
      />

      {/* 2. Analytical Data Page - Action Plan & Roadmap */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="07 / STRATEGIC PRIORITIES // ACTION PLAN & ROADMAP"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
              Phased Execution
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-slate-950">
              Executive Top-10 Action Plan
            </h2>
            <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
          </div>

          {/* Top 10 Actions Table */}
          <div className="space-y-2">
            <table className="w-full text-[8pt] border-collapse border border-slate-200">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-left font-mono text-[7.5pt] text-slate-600 uppercase">
                  <th className="py-2 px-2" style={{ width: '5%' }}>#</th>
                  <th className="py-2 px-3" style={{ width: '28%' }}>Remediation Action &amp; Area</th>
                  <th className="py-2 px-3" style={{ width: '12%' }}>Impact</th>
                  <th className="py-2 px-3" style={{ width: '12%' }}>Effort</th>
                  <th className="py-2 px-3">Expected Commercial Outcome &amp; Validation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {priorities.top10Actions.map((act) => (
                  <tr key={act.rank} className="hover:bg-slate-50/50">
                    <td className="py-2 px-2 font-mono font-bold text-slate-900">
                      {act.rank}
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-900 font-sans">
                      {act.action}
                      <span className="font-mono text-[7pt] text-slate-500 block mt-0.5">
                        Priority: {act.priority}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="font-mono font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 text-[7.5pt]">
                        {act.impact}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[7.5pt] text-slate-700">
                      {act.effort} ({act.engineerHours}h)
                    </td>
                    <td className="py-2 px-3 text-slate-700 font-sans leading-relaxed">
                      {act.outcome}
                      <em className="text-slate-500 block text-[7.5pt] mt-0.5">Acceptance: {act.validation}</em>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Editorial NOW / NEXT / ONGOING Roadmap Tree */}
          <div className="p-4 rounded bg-slate-50 border border-slate-200 space-y-4">
            <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 block pb-1 border-b border-slate-200">
              Editorial 90-Day Implementation Timeline
            </span>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[8pt]">
              {/* NOW (Days 1 - 7) */}
              <div className="space-y-1.5 p-3 bg-white border border-slate-200 rounded">
                <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 block w-fit">
                  PHASE 1 // NOW (DAYS 1–7)
                </span>
                <strong className="font-serif text-[9pt] text-slate-900 block pt-1">
                  Fix Technical Blockers
                </strong>
                <ul className="text-slate-600 space-y-1 list-disc pl-4 font-sans text-[7.5pt]">
                  <li>Deploy canonical 301 consolidation patches</li>
                  <li>Resolve broken redirect chains and 404 targets</li>
                  <li>Publish /llms.txt AI crawler permission manifesto</li>
                </ul>
              </div>

              {/* NEXT (Days 8 - 30) */}
              <div className="space-y-1.5 p-3 bg-white border border-slate-200 rounded">
                <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 block w-fit">
                  PHASE 2 // NEXT (DAYS 8–30)
                </span>
                <strong className="font-serif text-[9pt] text-slate-900 block pt-1">
                  Strengthen Entity Signals
                </strong>
                <ul className="text-slate-600 space-y-1 list-disc pl-4 font-sans text-[7.5pt]">
                  <li>Deploy JSON-LD Organization &amp; Service schemas</li>
                  <li>Implement character-safe title and meta tag pairs</li>
                  <li>Inject factual entity attribution passages</li>
                </ul>
              </div>

              {/* ONGOING (Days 31 - 90) */}
              <div className="space-y-1.5 p-3 bg-white border border-slate-200 rounded">
                <span className="font-mono text-[7.5pt] font-bold uppercase px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 block w-fit">
                  PHASE 3 // ONGOING (DAYS 31–90)
                </span>
                <strong className="font-serif text-[9pt] text-slate-900 block pt-1">
                  Assurance &amp; Governance
                </strong>
                <ul className="text-slate-600 space-y-1 list-disc pl-4 font-sans text-[7.5pt]">
                  <li>Closed-loop remediation verification against AST</li>
                  <li>Continuous regression monitoring across 100 queries</li>
                  <li>Monthly answer engine citation re-evaluation</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Financial Exposure Note (If Calculated) */}
          {priorities.financialModel && (
            <div className="p-3.5 rounded bg-slate-50 border border-slate-200 text-[8pt] text-slate-800 flex items-start gap-3">
              <span className="font-mono font-bold text-slate-700 text-[9pt] pt-0.5">$</span>
              <div>
                <strong className="font-mono text-[7.5pt] uppercase tracking-wider text-slate-900 block mb-0.5">
                  Commercial Opportunity &amp; Inaction Cost Model
                </strong>
                <p className="font-sans leading-relaxed text-slate-700">
                  {priorities.financialModel.monthlyLossEstimate}. Expected outcome upon roadmap deployment: {priorities.financialModel.projectedLift}. {priorities.financialModel.basisSummary}
                </p>
              </div>
            </div>
          )}
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={19}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}
