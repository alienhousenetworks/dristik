import React, { useMemo, useState } from 'react';
import { ExecutiveReport, ChartSpecification } from '../types';
import { buildReportTheme } from '../report/brandTheme';
import { normalizeExecutiveReport } from '../report/models/normalizedReport';
import { synthesizeVisualIntelligenceFallback } from '../lib/visualSynthesizerFallback';

// Editorial Publication Chapter Templates
import { CoverPage } from '../report/templates/CoverPage';
import { TableOfContents } from '../report/templates/TableOfContents';
import { ExecutiveBrief } from '../report/templates/ExecutiveBrief';
import { AuditSnapshot } from '../report/templates/AuditSnapshot';
import { Chapter01TechnicalSeo } from '../report/templates/Chapter01TechnicalSeo';
import { Chapter02Geo } from '../report/templates/Chapter02Geo';
import { Chapter03Aeo } from '../report/templates/Chapter03Aeo';
import { Chapter04Competitive } from '../report/templates/Chapter04Competitive';
import { Chapter05Conversion } from '../report/templates/Chapter05Conversion';
import { Chapter06PageByPage } from '../report/templates/Chapter06PageByPage';
import { Chapter07Roadmap } from '../report/templates/Chapter07Roadmap';
import { MethodologyChapter } from '../report/templates/MethodologyChapter';
import { AppendixLedger } from '../report/templates/AppendixLedger';

export interface AuditPdfReportProps {
  report: ExecutiveReport;
  defaultExhaustive?: boolean;
}

export function AuditPdfReport({
  report,
  defaultExhaustive = false,
}: AuditPdfReportProps) {
  const [exhaustiveMode, setExhaustiveMode] = useState(defaultExhaustive);

  // 1. Normalize data model (enforces Zero-Fake standard)
  const normalized = useMemo(() => normalizeExecutiveReport(report), [report]);

  // 2. Build accessible Brand Theme (WCAG AA 4.5:1 contrast calibrated)
  const theme = useMemo(() => {
    const rawColor =
      normalized.meta.rawBrandColor ||
      (report.business_profile as any)?.brand_color ||
      (report.business_profile as any)?.theme_color ||
      null;
    return buildReportTheme(rawColor);
  }, [normalized.meta.rawBrandColor, report.business_profile]);

  // 3. Resolve visual intelligence payload & vector charts
  const visual = report.visual_intelligence || synthesizeVisualIntelligenceFallback(report);
  const charts = visual?.selected_visualizations || [];

  const radarChart = useMemo(
    () => charts.find((c) => c.chart_type === 'radar') || null,
    [charts]
  );
  const engineChart = useMemo(
    () => charts.find((c) => c.chart_type === 'engine_comparison_bar') || null,
    [charts]
  );
  const latencyChart = useMemo(
    () => charts.find((c) => c.chart_type === 'latency_curve') || null,
    [charts]
  );

  // Synchronized defect donut chart matching actual findings
  const donutChart = useMemo<ChartSpecification | null>(() => {
    const rawDonut = charts.find((c) => c.chart_type === 'defect_donut');
    const findings = report.findings || [];
    if (rawDonut && rawDonut.data?.total === findings.length) {
      return rawDonut;
    }
    if (findings.length === 0) return rawDonut || null;

    const counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
    findings.forEach((f) => {
      const sev = String(f.severity || '').toUpperCase();
      if (counts[sev] !== undefined) counts[sev]++;
    });

    return {
      id: 'defect_donut',
      chart_type: 'defect_donut' as const,
      title: 'Empirical Defect Severity Distribution',
      subtitle: `${findings.length} findings categorized by business risk tier`,
      ai_insight: 'Categorization of findings by business risk tier',
      category: 'EXECUTIVE',
      data: {
        total: findings.length,
        segments: [
          { label: 'Critical', count: counts.CRITICAL, color: '#dc2626' },
          { label: 'High', count: counts.HIGH, color: '#f97316' },
          { label: 'Medium', count: counts.MEDIUM, color: '#eab308' },
          { label: 'Low', count: counts.LOW, color: '#3b82f6' },
          { label: 'Info', count: counts.INFO, color: '#94a3b8' },
        ],
      },
    };
  }, [charts, report.findings]);

  return (
    <article className="dristik-editorial-report text-slate-900 bg-white max-w-5xl mx-auto font-sans leading-normal selection:bg-slate-200">
      {/* Screen-Only Control Toolbar (Hidden in Print) */}
      <div className="no-print sticky top-2 z-40 mb-4 p-3 bg-slate-900 text-white rounded-lg shadow-lg flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="font-bold tracking-wider text-emerald-400">DRISTIK PUBLICATION ENGINE</span>
          <span className="text-slate-500">|</span>
          <span>Theme: {theme.isClientThemed ? 'Client Accent Calibrated' : 'Dristik Standard'}</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setExhaustiveMode(!exhaustiveMode)}
            className="px-2.5 py-1 rounded border border-slate-700 hover:bg-slate-800 transition-colors cursor-pointer"
          >
            Mode: {exhaustiveMode ? 'Exhaustive (100 Questions)' : 'Executive Digest'}
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-colors cursor-pointer"
          >
            Print / Save PDF
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* COVER PAGE (Full Bleed A4)                                                */}
      {/* ========================================================================= */}
      <CoverPage theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* TABLE OF CONTENTS & EXECUTIVE BRIEFING GUIDE                              */}
      {/* ========================================================================= */}
      <TableOfContents
        theme={theme}
        domain={normalized.meta.domain}
        brandName={normalized.meta.brandName}
        analysisId={normalized.meta.analysisId}
        dateStr={normalized.meta.generatedAt}
        isRealCompetitorDataAvailable={normalized.competitive.isRealCompetitorDataAvailable}
      />

      {/* ========================================================================= */}
      {/* EXECUTIVE BRIEF: "WHAT THE EVIDENCE SAYS"                                 */}
      {/* ========================================================================= */}
      <ExecutiveBrief theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* AUDIT SNAPSHOT: 5-PILLAR SCORECARD & COGNITIVE DIAGNOSTIC                 */}
      {/* ========================================================================= */}
      <AuditSnapshot
        theme={theme}
        report={normalized}
        radarChart={radarChart}
        donutChart={donutChart}
      />

      {/* ========================================================================= */}
      {/* CHAPTER 01: DISCOVERABILITY & TECHNICAL SEO ARCHITECTURE                  */}
      {/* ========================================================================= */}
      <Chapter01TechnicalSeo
        theme={theme}
        report={normalized}
        latencyChart={latencyChart}
      />

      {/* ========================================================================= */}
      {/* CHAPTER 02: GENERATIVE ENGINE OPTIMIZATION (GEO)                          */}
      {/* ========================================================================= */}
      <Chapter02Geo theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* CHAPTER 03: ANSWER ENGINE VISIBILITY (AEO) & AI CITATIONS                 */}
      {/* ========================================================================= */}
      <Chapter03Aeo
        theme={theme}
        report={normalized}
        engineChart={engineChart}
        exhaustiveMode={exhaustiveMode}
      />

      {/* ========================================================================= */}
      {/* CHAPTER 04: COMPETITIVE INTELLIGENCE & KNOWLEDGE GRAPH                    */}
      {/* ========================================================================= */}
      <Chapter04Competitive theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* CHAPTER 05: CONVERSION ERGONOMICS & PRODUCTION COPY                       */}
      {/* ========================================================================= */}
      <Chapter05Conversion theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* CHAPTER 06: PAGE-BY-PAGE AUDIT REVIEW                                     */}
      {/* ========================================================================= */}
      <Chapter06PageByPage theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* CHAPTER 07: STRATEGIC PRIORITIES & 90-DAY IMPLEMENTATION ROADMAP          */}
      {/* ========================================================================= */}
      <Chapter07Roadmap theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* CHAPTER 08: RESEARCH METHODOLOGY & SAMPLING PROTOCOL                      */}
      {/* ========================================================================= */}
      <MethodologyChapter theme={theme} report={normalized} />

      {/* ========================================================================= */}
      {/* CHAPTER 09: INSTITUTIONAL FINDINGS REGISTER & EVIDENCE LEDGER             */}
      {/* ========================================================================= */}
      <AppendixLedger theme={theme} report={normalized} />
    </article>
  );
}
