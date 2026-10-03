import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { PageHeader, PageFooter } from './PageHeaderFooter';
import { RadarChart } from '../../components/VisualIntelligence/charts/RadarChart';
import { SeverityDonutChart } from '../../components/VisualIntelligence/charts/SeverityDonutChart';
import { ChartSpecification } from '../../types';

interface AuditSnapshotProps {
  theme: ReportTheme;
  report: NormalizedReport;
  radarChart?: ChartSpecification | null;
  donutChart?: ChartSpecification | null;
}

export function AuditSnapshot({
  theme,
  report,
  radarChart,
  donutChart,
}: AuditSnapshotProps) {
  const { scorecard, meta, visual } = report;

  return (
    <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-white border-b-2 border-slate-200">
      <PageHeader
        theme={theme}
        domain={meta.domain}
        chapterTitle="AUDIT SNAPSHOT // DIAGNOSTIC MATRIX"
      />

      <div className="space-y-6 max-w-4xl">
        {/* Section Headline */}
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.2em] text-slate-500 block mb-1">
            Section 0.2 // Macro Diagnostics
          </span>
          <h2 className="font-serif text-[24pt] md:text-[28pt] font-normal tracking-tight text-slate-950">
            Audit Snapshot &amp; Cognitive Matrix
          </h2>
          <div className="w-16 h-[2.5px] mt-2" style={{ backgroundColor: theme.accent }}></div>
        </div>

        {/* 1. Tri-Perspective Cognitive Diagnosis */}
        <div>
          <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-600 mb-2">
            Tri-Perspective Cognitive Diagnosis
          </h3>
          <p className="text-[8.5pt] text-slate-600 mb-3 font-sans">
            Independent evaluation of this web property across three distinct classes of automated and human consumers.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[8.5pt]">
            <div className="p-3.5 border border-slate-200 rounded bg-slate-50 space-y-1">
              <div className="flex items-center gap-1.5 pb-1 border-b border-slate-200">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span className="font-mono font-bold uppercase text-[8pt] text-slate-800">
                  1. Human Visitor (CRO)
                </span>
              </div>
              <p className="text-slate-700 leading-relaxed font-sans pt-1">
                {scorecard.perspectives.human}
              </p>
            </div>

            <div className="p-3.5 border border-slate-200 rounded bg-slate-50 space-y-1">
              <div className="flex items-center gap-1.5 pb-1 border-b border-slate-200">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                <span className="font-mono font-bold uppercase text-[8pt] text-slate-800">
                  2. Search Spider (SEO)
                </span>
              </div>
              <p className="text-slate-700 leading-relaxed font-sans pt-1">
                {scorecard.perspectives.searchSpider}
              </p>
            </div>

            <div className="p-3.5 border border-slate-200 rounded bg-slate-50 space-y-1">
              <div className="flex items-center gap-1.5 pb-1 border-b border-slate-200">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span className="font-mono font-bold uppercase text-[8pt] text-slate-800">
                  3. AI Answer Engines (GEO)
                </span>
              </div>
              <p className="text-slate-700 leading-relaxed font-sans pt-1">
                {scorecard.perspectives.answerEngine}
              </p>
            </div>
          </div>
        </div>

        {/* 2. Visual Diagnostic Charts (Radar & Donut) */}
        <div>
          <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-600 mb-2">
            Visual Intelligence &amp; Defect Distribution
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 border border-slate-200 rounded bg-slate-50/60">
            {/* Radar Chart */}
            <div className="flex flex-col items-center justify-center p-3 bg-white border border-slate-200 rounded">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 mb-1">
                5-Pillar Score Radar vs Baseline
              </span>
              <p className="text-[7.5pt] text-slate-500 mb-2 text-center">
                Target performance mapped against industry standard across core digital pillars
              </p>
              {radarChart ? (
                <div className="w-full max-w-[270px]">
                  <RadarChart chart={radarChart} />
                </div>
              ) : (
                <div className="py-12 text-center text-xs text-slate-400 font-mono italic">
                  Continuous multidimensional radar mapping active
                </div>
              )}
            </div>

            {/* Donut Chart */}
            <div className="flex flex-col items-center justify-center p-3 bg-white border border-slate-200 rounded">
              <span className="font-mono text-[8pt] font-bold uppercase tracking-wider text-slate-700 mb-1">
                Empirical Defect Severity Distribution
              </span>
              <p className="text-[7.5pt] text-slate-500 mb-2 text-center">
                Total {report.appendices.findings.length} findings categorized by business risk tier
              </p>
              {donutChart ? (
                <div className="w-full max-w-[270px]">
                  <SeverityDonutChart chart={donutChart} />
                </div>
              ) : (
                <div className="py-12 text-center text-xs text-slate-400 font-mono italic">
                  Defect distribution mapped across findings register
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 3. Spotlight Empirical Metrics */}
        <div>
          <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-600 mb-2">
            Spotlight Empirical Metrics
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[8.5pt]">
            {visual.spotlightMetrics.map((metric, idx) => (
              <div key={idx} className="p-3 border border-slate-200 rounded bg-slate-50">
                <span className="font-mono text-[7.5pt] uppercase font-bold text-slate-500 block truncate">
                  {metric.label}
                </span>
                <span className="text-xl font-serif font-bold text-slate-900 block mt-1">
                  {metric.value}
                </span>
                <span className="text-[7.5pt] text-slate-600 block mt-0.5 font-sans leading-tight">
                  {metric.significance}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 4. Score Calculation Ledger (Deterministic Composite Derivation) */}
        {scorecard.ledger && scorecard.ledger.length > 0 && (
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between pb-1 border-b border-slate-200">
              <h3 className="font-mono text-[8.5pt] font-bold uppercase tracking-wider text-slate-700">
                Score Calculation Ledger (Deterministic Mathematical Traceability)
              </h3>
              <span className="font-mono text-[7.5pt] text-slate-500">
                Composite = Σ (Raw Score × Assigned Weight)
              </span>
            </div>

            <table className="w-full text-[8.5pt] border-collapse border border-slate-200">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-left font-mono text-[7.5pt] text-slate-600 uppercase">
                  <th className="py-2 px-3">Audit Pillar / Category</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Raw Score</th>
                  <th className="py-2 px-3">Weight (%)</th>
                  <th className="py-2 px-3 text-right">Contribution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white font-mono">
                {scorecard.ledger.map((row) => (
                  <tr key={row.categoryKey} className="hover:bg-slate-50/50">
                    <td className="py-2 px-3 font-sans font-semibold text-slate-900">{row.pillar}</td>
                    <td className="py-2 px-3 text-[7.5pt]">
                      <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 font-bold">
                        {row.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-bold">{row.rawScore != null ? `${row.rawScore}` : '—'}</td>
                    <td className="py-2 px-3 text-slate-600">{row.weightPct}%</td>
                    <td className="py-2 px-3 text-right font-bold text-slate-900">
                      +{row.contribution.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100/90 border-t-2 border-slate-300 font-mono text-[8.5pt]">
                  <td colSpan={3} className="py-2 px-3 font-bold font-sans text-slate-900">
                    Total Deterministic Composite Score
                  </td>
                  <td className="py-2 px-3 text-slate-600 font-bold">100.0%</td>
                  <td className="py-2 px-3 text-right font-bold text-slate-950 text-[10pt]">
                    {scorecard.calculatedComposite ?? scorecard.overallScore} / 100
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      <PageFooter
        theme={theme}
        domain={meta.domain}
        pageNumber={4}
        reportId={meta.analysisId}
        dateStr={meta.generatedAt}
      />
    </section>
  );
}
