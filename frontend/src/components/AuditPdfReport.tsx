import React, { useMemo, useState } from 'react';
import { ExecutiveReport, ChartSpecification } from '../types';
import { buildReportTheme } from '../report/brandTheme';
import { normalizeExecutiveReport } from '../report/models/normalizedReport';
import { synthesizeVisualIntelligenceFallback } from '../lib/visualSynthesizerFallback';
import { shortPillarLabel } from '../report/models/scoreLedger';

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
import { AuditIndexChapter } from '../report/templates/AuditIndexChapter';
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

  const radarChart = useMemo<ChartSpecification | null>(() => {
    const rows = normalized.scorecard.ledger.filter((row) => row.included && row.rawScore != null);
    if (rows.length === 0) return charts.find((c) => c.chart_type === 'radar') || null;
    return {
      id: 'chart_pillar_radar',
      chart_type: 'radar',
      title: 'Ledger pillar scores',
      subtitle: 'Same scores as the calculation ledger.',
      ai_insight: normalized.scorecard.compositeFormula,
      category: 'OVERALL',
      data: {
        labels: rows.map((row) => shortPillarLabel(row.categoryKey)),
        target_values: rows.map((row) => row.rawScore as number),
        benchmark_values: [],
      },
      config: {
        max_value: 100,
        target_label: normalized.meta.domain,
        benchmark_label: '',
      },
      is_recommended: true,
      priority_order: 1,
    };
  }, [charts, normalized.meta.domain, normalized.scorecard.compositeFormula, normalized.scorecard.ledger]);
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
          { label: 'Critical', count: counts.CRITICAL, color: '#a82620' },
          { label: 'High', count: counts.HIGH, color: '#c45c26' },
          { label: 'Medium', count: counts.MEDIUM, color: '#925a08' },
          { label: 'Low', count: counts.LOW, color: '#5c6b7a' },
          { label: 'Info', count: counts.INFO, color: '#8b939c' },
        ].filter((segment) => segment.count > 0),
      },
    };
  }, [charts, report.findings]);

  return (
    <article className="dristik-editorial-report text-ink bg-paper-50 max-w-5xl mx-auto font-sans leading-normal selection:bg-paper-200">
      {/* Screen-Only Control Toolbar (Hidden in Print) */}
      <div className="no-print sticky top-2 z-40 mb-4 p-3 bg-ink text-white rounded-lg shadow-lg flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="font-bold tracking-[0.04em] text-good">DRISTIK PUBLICATION ENGINE</span>
          <span className="text-ink-500">|</span>
          <span>Theme: {theme.isClientThemed ? 'Client Accent Calibrated' : 'Dristik Standard'}</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setExhaustiveMode(!exhaustiveMode)}
            className="px-2.5 py-1 rounded border border-line hover:bg-ink-800 transition-colors cursor-pointer"
          >
            Mode: {exhaustiveMode ? 'Exhaustive (100 Questions)' : 'Executive Digest'}
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="px-3 py-1 rounded bg-good/10 hover:bg-good/10 text-white font-bold transition-colors cursor-pointer"
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

      <AuditIndexChapter theme={theme} report={report} domain={normalized.meta.domain} />

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
