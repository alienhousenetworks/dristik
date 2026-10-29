import React, { useMemo, useState, useRef, useEffect } from 'react';
import { ExecutiveReport, ChartSpecification } from '../types';
import { buildReportTheme } from '../report/brandTheme';
import { normalizeExecutiveReport } from '../report/models/normalizedReport';
import { synthesizeVisualIntelligenceFallback } from '../lib/visualSynthesizerFallback';
import { shortPillarLabel } from '../report/models/scoreLedger';

// Adaptive Publication Framework & Pagination Engine
import {
  ReportFamily,
  detectReportFamily,
  buildPublicationManifest,
  PublicationCustomization,
} from '../report/adaptivePublication';
import {
  computePublicationPagination,
  measureDomChapterSpans,
} from '../report/paginationEngine';

// Editorial Publication Chapter Templates
import { CoverPage } from '../report/templates/CoverPage';
import { PublicationFrontMatter } from '../report/templates/PublicationFrontMatter';
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
import { ClosingPage } from '../report/templates/ClosingPage';

export interface AuditPdfReportProps {
  report: ExecutiveReport;
  defaultExhaustive?: boolean;
  defaultFamily?: ReportFamily | 'AUTO';
  onClose?: () => void;
}

export function AuditPdfReport({
  report,
  defaultExhaustive = false,
  defaultFamily = 'AUTO',
  onClose,
}: AuditPdfReportProps) {
  // Publication Customization State
  const [selectedFamily, setSelectedFamily] = useState<ReportFamily | 'AUTO'>(defaultFamily);
  const [exhaustiveMode, setExhaustiveMode] = useState(defaultExhaustive);
  const [includeToc, setIncludeToc] = useState(true);
  const [includeFrontMatter, setIncludeFrontMatter] = useState(true);
  const [includeAppendices, setIncludeAppendices] = useState(true);
  const [customTitle, setCustomTitle] = useState('');
  const [customSubtitle, setCustomSubtitle] = useState('');
  const [customClassification, setCustomClassification] = useState('STRICTLY CONFIDENTIAL // C-SUITE DOSSIER');
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [domSpans, setDomSpans] = useState<Record<string, number>>({});
  const containerRef = useRef<HTMLElement | null>(null);

  // 1. Normalize data model (enforces Zero-Fake standard)
  const normalized = useMemo(() => normalizeExecutiveReport(report), [report]);

  // 2. Programmatically detect report family
  const detectedFamily = useMemo(() => detectReportFamily(normalized), [normalized]);
  const activeFamily: ReportFamily = selectedFamily === 'AUTO' ? detectedFamily : selectedFamily;

  // 3. Build accessible Brand Theme (WCAG AA 4.5:1 contrast calibrated)
  const theme = useMemo(() => {
    const rawColor =
      normalized.meta.rawBrandColor ||
      (report.business_profile as any)?.brand_color ||
      (report.business_profile as any)?.theme_color ||
      null;
    return buildReportTheme(rawColor);
  }, [normalized.meta.rawBrandColor, report.business_profile]);

  // 4. Build Publication Manifest
  const manifest = useMemo(() => {
    const customization: PublicationCustomization = {
      titleOverride: customTitle.trim() || undefined,
      subtitleOverride: customSubtitle.trim() || undefined,
      classificationOverride: customClassification.trim() || undefined,
      includeToc,
      includeFrontMatter,
      includeAppendices,
      exhaustiveMode,
    };
    return buildPublicationManifest(normalized, activeFamily, customization);
  }, [
    normalized,
    activeFamily,
    customTitle,
    customSubtitle,
    customClassification,
    includeToc,
    includeFrontMatter,
    includeAppendices,
    exhaustiveMode,
  ]);

  // 5. Measure and compute stable pagination
  useEffect(() => {
    if (typeof window !== 'undefined' && containerRef.current) {
      const measured = measureDomChapterSpans(containerRef.current);
      if (Object.keys(measured).length > 0) {
        setDomSpans(measured);
      }
    }
  }, [manifest, activeFamily, exhaustiveMode]);

  const pagination = useMemo(
    () => computePublicationPagination(manifest, normalized, domSpans),
    [manifest, normalized, domSpans]
  );

  // 6. Resolve visual intelligence payload & vector charts
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

  // Check which chapters are enabled in the active manifest
  const hasChapter = (id: string) => manifest.chapters.some((c) => c.id === id);
  const getChapterLoc = (id: string) => pagination.locations[id];

  return (
    <article
      ref={containerRef}
      className="dristik-editorial-report text-ink bg-paper-50 max-w-5xl mx-auto font-sans leading-normal selection:bg-paper-200"
    >
      {/* Screen-Only Control Toolbar (Hidden in Print) */}
      <div className="no-print sticky top-2 z-40 mb-4 p-3 bg-ink text-white rounded-lg shadow-lg flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold tracking-[0.04em] text-good">DRISTIK AUDIT BOOK</span>
          <span className="text-ink-500">|</span>
          <span className="px-2 py-0.5 rounded bg-ink-800 border border-line text-sky-400">
            {selectedFamily === 'AUTO' ? `Auto: ${manifest.familyDisplayName}` : manifest.familyDisplayName}
          </span>
          <span className="text-ink-500">|</span>
          <span className="text-ink-300">
            {pagination.totalPhysicalPages} Pages ({pagination.status === 'STABLE_CONVERGED' ? '✓ Converged' : 'Measuring'})
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setShowSettingsModal(true)}
            className="px-2.5 py-1 rounded border border-line hover:bg-ink-800 transition-colors cursor-pointer"
            title="Configure publication profile, title, confidentiality, and chapters"
          >
            ⚙ Publication Options
          </button>
          <button
            type="button"
            onClick={() => setExhaustiveMode(!exhaustiveMode)}
            className="px-2.5 py-1 rounded border border-line hover:bg-ink-800 transition-colors cursor-pointer"
          >
            {exhaustiveMode ? 'Full 100-Questions' : 'Executive Digest'}
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="px-3 py-1 rounded bg-good/20 hover:bg-good/30 text-white font-bold border border-good/40 transition-colors cursor-pointer"
          >
            Print / Save PDF
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-2 py-1 rounded hover:bg-ink-800 text-ink-400 hover:text-white transition-colors cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Screen-Only Publication Settings Modal */}
      {showSettingsModal && (
        <div className="no-print fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-paper-50 text-ink border-2 border-line rounded-lg max-w-lg w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-2">
              <h3 className="font-bold font-sans text-lg">Publication Configuration</h3>
              <button
                type="button"
                onClick={() => setShowSettingsModal(false)}
                className="text-ink-400 hover:text-ink font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {/* Report Family / Profile Selector */}
              <div>
                <label className="font-mono font-bold uppercase tracking-wider block mb-1">
                  Report Family / Publication Profile
                </label>
                <select
                  value={selectedFamily}
                  onChange={(e) => setSelectedFamily(e.target.value as any)}
                  className="w-full p-2 rounded bg-paper-100 border border-line text-ink font-sans"
                >
                  <option value="AUTO">Auto-Detect ({detectedFamily})</option>
                  <option value="COMPLETE">Complete Website Intelligence Audit</option>
                  <option value="SEO">Technical SEO & Organic Search Audit Book</option>
                  <option value="GEO">Generative Engine Optimization (GEO) Book</option>
                  <option value="AEO">Answer Engine Optimization (AEO) Book</option>
                  <option value="CRO">Conversion Experience & CRO Audit Book</option>
                  <option value="COMPETITOR">Competitive Digital Visibility Analysis</option>
                  <option value="HYBRID">Multi-Discipline / Hybrid Audit Book</option>
                  <option value="CUSTOM">Custom Digital Intelligence Dossier</option>
                </select>
              </div>

              {/* Title Override */}
              <div>
                <label className="font-mono font-bold uppercase tracking-wider block mb-1">
                  Custom Publication Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder={manifest.title}
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full p-2 rounded bg-paper-100 border border-line text-ink font-sans"
                />
              </div>

              {/* Subtitle Override */}
              <div>
                <label className="font-mono font-bold uppercase tracking-wider block mb-1">
                  Custom Subtitle (Optional)
                </label>
                <input
                  type="text"
                  placeholder={manifest.subtitle}
                  value={customSubtitle}
                  onChange={(e) => setCustomSubtitle(e.target.value)}
                  className="w-full p-2 rounded bg-paper-100 border border-line text-ink font-sans"
                />
              </div>

              {/* Confidentiality Classification */}
              <div>
                <label className="font-mono font-bold uppercase tracking-wider block mb-1">
                  Confidentiality Classification
                </label>
                <select
                  value={customClassification}
                  onChange={(e) => setCustomClassification(e.target.value)}
                  className="w-full p-2 rounded bg-paper-100 border border-line text-ink font-sans"
                >
                  <option value="STRICTLY CONFIDENTIAL // C-SUITE DOSSIER">STRICTLY CONFIDENTIAL // C-SUITE DOSSIER</option>
                  <option value="RESTRICTED // BOARD DOSSIER">RESTRICTED // BOARD DOSSIER</option>
                  <option value="INTERNAL AUDIT ADVISORY">INTERNAL AUDIT ADVISORY</option>
                  <option value="CLIENT CONFIDENTIAL">CLIENT CONFIDENTIAL</option>
                  <option value="UNRESTRICTED EXECUTIVE SUMMARY">UNRESTRICTED EXECUTIVE SUMMARY</option>
                </select>
              </div>

              {/* Content Inclusions */}
              <div className="pt-2 border-t border-line space-y-2">
                <span className="font-mono font-bold uppercase tracking-wider block mb-1">
                  Document Sections
                </span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeFrontMatter}
                    onChange={(e) => setIncludeFrontMatter(e.target.checked)}
                  />
                  <span>Include Front Matter & Scope Protocol</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeToc}
                    onChange={(e) => setIncludeToc(e.target.checked)}
                  />
                  <span>Include Table of Contents</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeAppendices}
                    onChange={(e) => setIncludeAppendices(e.target.checked)}
                  />
                  <span>Include Technical Appendices & Findings Register</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-line">
              <button
                type="button"
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-1.5 rounded bg-ink text-white font-bold"
              >
                Apply &amp; Re-Paginate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. COVER PAGE (Dedicated full bleed A4)                                   */}
      {/* ========================================================================= */}
      <CoverPage theme={theme} report={normalized} manifest={manifest} />

      {/* ========================================================================= */}
      {/* 2. FRONT MATTER: IDENTIFICATION & SCOPE PROTOCOL                          */}
      {/* ========================================================================= */}
      {manifest.includeFrontMatter && (
        <PublicationFrontMatter
          theme={theme}
          report={normalized}
          manifest={manifest}
          pageNumber={pagination.locations['front_matter_details']?.logicalPageNumber || 'i'}
        />
      )}

      {/* ========================================================================= */}
      {/* 3. TABLE OF CONTENTS WITH REAL CONVERGED BOOK PAGINATION                  */}
      {/* ========================================================================= */}
      {manifest.includeToc && (
        <TableOfContents
          theme={theme}
          domain={normalized.meta.domain}
          brandName={normalized.meta.brandName}
          analysisId={normalized.meta.analysisId}
          dateStr={normalized.meta.generatedAt}
          isRealCompetitorDataAvailable={normalized.competitive.isRealCompetitorDataAvailable}
          manifest={manifest}
          pagination={pagination}
          pageNumber={pagination.locations['front_matter_toc']?.logicalPageNumber || 'ii'}
        />
      )}

      {/* ========================================================================= */}
      {/* PART I: EXECUTIVE SYNTHESIS & SCORECARD                                   */}
      {/* ========================================================================= */}
      {hasChapter('ch_brief') && (
        <>
          <ExecutiveBrief
            theme={theme}
            report={normalized}
            pageNumber={getChapterLoc('ch_brief')?.logicalPageNumber || 1}
          />
          <AuditSnapshot
            theme={theme}
            report={normalized}
            radarChart={radarChart}
            donutChart={donutChart}
            pageNumber={
              typeof getChapterLoc('ch_brief')?.logicalPageNumber === 'number'
                ? (getChapterLoc('ch_brief')!.logicalPageNumber as number) + 1
                : 2
            }
          />
        </>
      )}

      {/* ========================================================================= */}
      {/* PART II: ADAPTIVE DISCIPLINE CHAPTERS                                     */}
      {/* ========================================================================= */}

      {/* Chapter 01: Discoverability & Technical SEO */}
      {hasChapter('ch_seo') && (
        <Chapter01TechnicalSeo
          theme={theme}
          report={normalized}
          latencyChart={latencyChart}
          pageNumber={getChapterLoc('ch_seo')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_seo')?.chapterNumber}
        />
      )}

      {/* Chapter 02: Generative Engine Optimization (GEO) */}
      {hasChapter('ch_geo') && (
        <Chapter02Geo
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_geo')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_geo')?.chapterNumber}
        />
      )}

      {/* Chapter 03: Answer Engine Visibility (AEO) & AI Citations */}
      {hasChapter('ch_aeo') && (
        <Chapter03Aeo
          theme={theme}
          report={normalized}
          engineChart={engineChart}
          exhaustiveMode={exhaustiveMode}
          pageNumber={getChapterLoc('ch_aeo')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_aeo')?.chapterNumber}
        />
      )}

      {/* Chapter 04: Competitive Intelligence & Knowledge Graph */}
      {hasChapter('ch_competitive') && (
        <Chapter04Competitive
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_competitive')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_competitive')?.chapterNumber}
        />
      )}

      {/* Chapter 05: Conversion Ergonomics & Production Copy */}
      {hasChapter('ch_conversion') && (
        <Chapter05Conversion
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_conversion')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_conversion')?.chapterNumber}
        />
      )}

      {/* Chapter 06: Page-by-Page Audit Review */}
      {hasChapter('ch_page_by_page') && (
        <Chapter06PageByPage
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_page_by_page')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_page_by_page')?.chapterNumber}
        />
      )}

      {/* ========================================================================= */}
      {/* PART III: REMEDIATION & GOVERNANCE                                        */}
      {/* ========================================================================= */}

      {/* Chapter 07: Strategic Priorities & 90-Day Implementation Roadmap */}
      {hasChapter('ch_roadmap') && (
        <Chapter07Roadmap
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_roadmap')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_roadmap')?.chapterNumber}
        />
      )}

      {/* Master Audit Index Matrix (Complete Website Intelligence profile) */}
      {hasChapter('ch_audit_index') && (
        <AuditIndexChapter
          theme={theme}
          report={report}
          domain={normalized.meta.domain}
          pageNumber={getChapterLoc('ch_audit_index')?.logicalPageNumber || 'Index'}
        />
      )}

      {/* Chapter 08: Research Methodology & Sampling Parameters */}
      {hasChapter('ch_methodology') && (
        <MethodologyChapter
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_methodology')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_methodology')?.chapterNumber}
        />
      )}

      {/* ========================================================================= */}
      {/* PART IV: APPENDICES & TECHNICAL REGISTERS                                 */}
      {/* ========================================================================= */}
      {manifest.includeAppendices && hasChapter('ch_appendix') && (
        <AppendixLedger
          theme={theme}
          report={normalized}
          pageNumber={getChapterLoc('ch_appendix')?.logicalPageNumber}
          chapterNumber={getChapterLoc('ch_appendix')?.chapterNumber}
        />
      )}

      {/* ========================================================================= */}
      {/* 5. CLOSING PAGE (Assurance Seal, Verification Protocol & Attestation)    */}
      {/* ========================================================================= */}
      <ClosingPage
        theme={theme}
        report={normalized}
        manifest={manifest}
        pageNumber={pagination.locations['closing_page']?.logicalPageNumber}
      />
    </article>
  );
}
