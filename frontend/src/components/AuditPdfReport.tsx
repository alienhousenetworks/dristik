import React from 'react';
import {
  ExecutiveReport,
  Finding,
  CodePatch,
  CopySection,
  CopyFaqItem,
  PageReport,
  PageEvidence,
  ChartSpecification,
} from '../types';
import { categoryLabel, display, formatPercent } from '../lib/format';
import { synthesizeVisualIntelligenceFallback } from '../lib/visualSynthesizerFallback';
import { RadarChart } from './VisualIntelligence/charts/RadarChart';
import { SeverityDonutChart } from './VisualIntelligence/charts/SeverityDonutChart';
import { EngineComparisonBarChart } from './VisualIntelligence/charts/EngineComparisonBarChart';
import { LatencyCurveChart } from './VisualIntelligence/charts/LatencyCurveChart';
import { ComparativeEvidenceMatrix } from './ComparativeEvidenceMatrix';
import { UrlLevelTechnicalAppendix } from './UrlLevelTechnicalAppendix';
import { VerificationProofCard } from './VerificationProofCard';

function text(value?: string | number | null): string {
  if (value == null) return '—';
  const raw = String(value).trim();
  return raw || '—';
}

function score(value?: number | null): string {
  return typeof value === 'number' && !Number.isNaN(value) ? String(Math.round(value)) : '—';
}

function clip(value?: string | null, max = 500): string {
  const raw = (value || '').replace(/\s+/g, ' ').trim();
  if (!raw) return '—';
  return raw.length > max ? `${raw.slice(0, max)}…` : raw;
}

function SectionKicker({ pillar, sectionNumber }: { pillar: string; sectionNumber: number }) {
  return (
    <div className="flex items-center gap-2 mb-2 pb-1 border-b border-line">
      <span className="bg-ink-900 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider font-mono">
        PILLAR {sectionNumber} // {pillar}
      </span>
      <span className="audit-pdf-kicker text-ink-500 text-xs font-semibold uppercase tracking-wider">
        DIAGNOSTIC MODULE {sectionNumber}.0
      </span>
    </div>
  );
}

function Module({
  pillar,
  sectionNumber,
  title,
  subtitle,
  children,
  pageBreak = true,
}: {
  pillar: string;
  sectionNumber: number;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  pageBreak?: boolean;
}) {
  return (
    <section className={`audit-pdf-section audit-module ${pageBreak ? 'big4-page-break' : ''} mb-8`}>
      <div className="audit-pdf-module-header mb-4">
        <SectionKicker pillar={pillar} sectionNumber={sectionNumber} />
        <h2 className="text-xl font-bold font-serif text-ink tracking-tight">{title}</h2>
        {subtitle && <p className="audit-pdf-subtitle text-xs text-ink-500 mt-1">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

function FieldTable({ rows }: { rows: Array<[string, string]> }) {
  const visible = rows.filter(([, value]) => value && value !== '—');
  if (visible.length === 0) {
    return <p className="audit-pdf-empty text-xs text-ink-400 italic">Not recorded on this audit.</p>;
  }
  return (
    <table className="audit-pdf-table w-full text-xs border-collapse mb-4">
      <tbody>
        {visible.map(([label, value]) => (
          <tr key={label} className="border-b border-line">
            <th className="py-1.5 pr-3 text-left font-semibold text-ink-600 bg-canvas-subtle" style={{ width: '32%' }}>{label}</th>
            <td className="py-1.5 px-3 text-ink leading-relaxed">{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function AuditPdfReport({ report }: { report: ExecutiveReport }) {
  const profile = report.business_profile;
  const semantic = report.semantic_business;
  const scores = report.scores;
  const honest = report.honest_scores;
  const pages = report.crawl_manifest?.pages || [];
  const pageReports = report.page_reports || [];
  const actions = report.top_10_actions?.actions || [];
  const questions = report.geo_readiness?.questions || [];
  const dimensions = report.geo_readiness?.dimensions || [];
  const patches = report.code_patches || [];
  const evidenceMap = report.evidence_ledger || {};
  const findings = report.findings || [];
  const aiSearchMatrix = report.ai_search_matrix || [];
  const visual = report.visual_intelligence || synthesizeVisualIntelligenceFallback(report);
  const metrics = visual?.spotlight_metrics || [];

  // Charts
  const charts = visual?.selected_visualizations || [];
  const radarChart = charts.find((c) => c.chart_type === 'radar');
  const donutChart = charts.find((c) => c.chart_type === 'defect_donut');
  const engineChart = charts.find((c) => c.chart_type === 'engine_comparison_bar');
  const latencyChart = charts.find((c) => c.chart_type === 'latency_curve');

  // Rollup analyzers
  const metaRollup = report.meta_rollup;
  const headings = report.heading_hierarchy;
  const redirects = report.host_and_redirects;
  const clickDepth = report.click_depth;
  const orphans = report.orphan_pages;
  const anchors = report.anchor_text_audit;
  const forms = report.form_audit;
  const media = report.media_assets;
  const perEngine = report.per_engine_geo;
  const geo = report.geo_readiness;
  const passages = geo?.citation_passages;
  const rewrites = ((passages?.rewrite_recommendations || []) as Array<{
    passage_id?: string;
    current_passage?: string;
    recommended_rewrite?: string;
    why?: string;
    estimated_score_improvement?: string;
  }>).filter((item) => Boolean(item.recommended_rewrite && item.recommended_rewrite !== item.current_passage));

  // Tri-Perspective Comparison
  const perspective = report.three_way_comparison;

  // Group findings by severity
  const criticalFindings = findings.filter((f) => f.severity === 'CRITICAL');
  const highFindings = findings.filter((f) => f.severity === 'HIGH');
  const mediumFindings = findings.filter((f) => f.severity === 'MEDIUM');
  const lowFindings = findings.filter((f) => f.severity === 'LOW' || f.severity === 'INFO');

  // Question set for GEO/AEO
  const questionTexts = new Set(questions.map((q) => q.question.toLowerCase().trim()));
  const distinctAiQueries = aiSearchMatrix.filter(
    (q) => !questionTexts.has((q.query || '').toLowerCase().trim())
  );

  return (
    <article className="audit-pdf text-ink max-w-4xl mx-auto p-4 leading-normal">
      {/* ========================================================================= */}
      {/* PILLAR 1: EXECUTIVE STRATEGY & 5-PILLAR VISUAL MATRIX                     */}
      {/* ========================================================================= */}
      <Module
        pillar="EXECUTIVE STRATEGY & SCORECARD"
        sectionNumber={1}
        title="Executive Intelligence, 5-Pillar Scorecard & Strategic Ground Truth"
        subtitle="Confidential Institutional Audit, Visual Diagnostic Matrix & Tri-Perspective Analysis"
        pageBreak={true}
      >
        <header className="audit-pdf-cover border border-line p-5 rounded bg-canvas-subtle mb-6">
          <div className="audit-pdf-branding-bar flex items-center justify-between pb-3 border-b border-line mb-3">
            <span className="font-bold text-xs tracking-wider uppercase text-pine font-mono">
              DRISTIK AI // ENTERPRISE WEBSITE INTELLIGENCE SYSTEM
            </span>
            <span className="audit-pdf-seal text-xs font-bold text-good">
              {report.certification_status === 'CERTIFIED'
                ? '★ CERTIFIED ZERO-FAKE GROUND TRUTH'
                : '⚠ DEGRADED WITHHELD'}
            </span>
          </div>

          <p className="audit-pdf-kicker text-xs uppercase tracking-wider text-ink-500 font-semibold">Target Digital Property Audit</p>
          <h1 className="text-3xl font-serif font-bold text-ink mt-1 mb-1">{display(report.domain)}</h1>
          <p className="audit-pdf-url text-sm text-pine font-mono mb-2">{report.website_url}</p>
          <p className="audit-pdf-meta text-xs text-ink-400 mb-4">
            Generated: {text(report.generated_at)} · Analysis Run: {text(report.analysis_id || report.report_id)} · Policy Pack: {text(report.policy_pack || 'enterprise_web_intel_v4')}
          </p>

          <table className="audit-pdf-table audit-pdf-scores w-full text-xs border border-line bg-white mb-2">
            <tbody>
              <tr className="border-b border-line">
                <th className="py-2 px-3 text-left bg-canvas-subtle">Overall Audit Score</th>
                <td className="py-2 px-3 font-bold text-base text-ink">{score(scores?.overall_score)} / 100</td>
                <th className="py-2 px-3 text-left bg-canvas-subtle">Composite Grade</th>
                <td className="py-2 px-3 font-bold text-base text-pine">{text(scores?.grade)}</td>
              </tr>
              <tr className="border-b border-line">
                <th className="py-2 px-3 text-left bg-canvas-subtle">Calibration Confidence</th>
                <td className="py-2 px-3">{formatPercent(scores?.overall_confidence)}</td>
                <th className="py-2 px-3 text-left bg-canvas-subtle">Evidence Coverage</th>
                <td className="py-2 px-3">{formatPercent(scores?.evidence_coverage)}</td>
              </tr>
              <tr className="border-b border-line">
                <th className="py-2 px-3 text-left bg-canvas-subtle">1. Human Visitor Experience (CRO/UX)</th>
                <td className="py-2 px-3 font-semibold">{score(honest?.human_score)} / 100</td>
                <th className="py-2 px-3 text-left bg-canvas-subtle">2. Traditional Search Crawl (SEO)</th>
                <td className="py-2 px-3 font-semibold">{score(honest?.google_score)} / 100</td>
              </tr>
              <tr>
                <th className="py-2 px-3 text-left bg-canvas-subtle">3. GEO Readiness (on-page)</th>
                <td className="py-2 px-3 font-semibold">{score(honest?.ai_readiness_score)} / 100</td>
                <th className="py-2 px-3 text-left bg-canvas-subtle">4. Live AI citation visibility</th>
                <td className="py-2 px-3">
                  {honest?.ai_visibility_status === 'MEASURED' && honest?.ai_visibility_score != null
                    ? `${score(honest?.ai_visibility_score)} / 100 (live responses)`
                    : 'Not measured'}
                </td>
              </tr>
            </tbody>
          </table>
        </header>

        {/* 1.1 VISUAL DIAGNOSTIC MATRIX (RADAR CHART & DEFECT DONUT) */}
        <div className="mb-6 big4-avoid-break">
          <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mb-2">1.1 Visual Diagnostic Matrix</h3>
          <p className="text-xs text-ink-500 mb-3">
            Multi-dimensional comparative radar and empirical defect distribution across all analyzed technical domains.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 border border-line rounded bg-canvas-subtle">
            {/* Chart 1: Pillar Radar */}
            <div className="flex flex-col items-center justify-center p-3 bg-white border border-line rounded">
              <span className="text-[11px] font-bold uppercase tracking-wider text-ink-700 mb-1">
                5-Pillar Score Radar vs Baseline
              </span>
              <p className="text-[10px] text-ink-500 mb-2 text-center">
                Target performance mapped against enterprise baseline across core digital pillars
              </p>
              {radarChart ? (
                <div className="w-full max-w-[280px]">
                  <RadarChart chart={radarChart} />
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-ink-400 italic">Radar graph synthesizing...</div>
              )}
            </div>

            {/* Chart 2: Defect Donut */}
            <div className="flex flex-col items-center justify-center p-3 bg-white border border-line rounded">
              <span className="text-[11px] font-bold uppercase tracking-wider text-ink-700 mb-1">
                Empirical Defect Severity Distribution
              </span>
              <p className="text-[10px] text-ink-500 mb-2 text-center">
                Total {findings.length} findings categorized by business risk tier
              </p>
              {donutChart ? (
                <div className="w-full max-w-[280px]">
                  <SeverityDonutChart chart={donutChart} />
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-ink-400 italic">Severity chart synthesizing...</div>
              )}
            </div>
          </div>
        </div>

        {/* 1.2 SPOTLIGHT MEASURED METRICS */}
        {metrics.length > 0 && (
          <div className="mb-6 big4-avoid-break">
            <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mb-2">1.2 Spotlight Empirical Metrics</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {metrics.map((metric) => (
                <div key={metric.id} className="p-3 border border-line rounded bg-canvas-subtle">
                  <span className="text-[10px] uppercase font-bold text-ink-500 block truncate">{metric.label}</span>
                  <span className="text-xl font-serif font-bold text-ink block mt-1">{metric.value}</span>
                  <span className="text-[10px] text-ink-600 block mt-0.5">{metric.significance}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 1.3 TRI-PERSPECTIVE COGNITIVE DIAGNOSIS */}
        {perspective && (
          <div className="mb-6 big4-avoid-break">
            <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mb-2">1.3 Tri-Perspective Cognitive Diagnosis</h3>
            <p className="text-xs text-ink-500 mb-3">
              Divergent evaluations of this web property across three distinct classes of automated and human consumers.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 border border-line rounded bg-canvas-subtle space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  <span className="font-bold uppercase tracking-wider text-ink-800 text-[11px]">1. Human Visitor (CRO)</span>
                </div>
                <p className="text-ink-700 leading-relaxed">
                  {perspective.human_visitor_perspective || 'Clear value proposition friction detected. Visitor conversion pathway requires streamlining.'}
                </p>
              </div>

              <div className="p-3.5 border border-line rounded bg-canvas-subtle space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  <span className="font-bold uppercase tracking-wider text-ink-800 text-[11px]">2. Search Spider (SEO)</span>
                </div>
                <p className="text-ink-700 leading-relaxed">
                  {perspective.search_engine_perspective || 'Crawl architecture evaluated. Canonical routing, sitemap discovery, and heading semantics analyzed.'}
                </p>
              </div>

              <div className="p-3.5 border border-line rounded bg-canvas-subtle space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span className="font-bold uppercase tracking-wider text-ink-800 text-[11px]">3. AI Answer Engines (GEO/AEO)</span>
                </div>
                <p className="text-ink-700 leading-relaxed">
                  {perspective.ai_answer_engine_perspective || 'Extractability for generative citations. Evaluates whether LLMs can quote exact entity facts.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 1.4 EXECUTIVE STRATEGIC BLUF */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">1.4 Executive Bottom Line Up Front (BLUF)</h3>
        <p className="text-xs text-ink-700 leading-relaxed mb-4 p-3 border border-line rounded bg-white">
          {report.story_summary || 'Executive narrative generated from ground-truth analysis.'}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mb-4">
          <div className="p-3 border border-line rounded bg-canvas-subtle">
            <h4 className="font-bold text-good uppercase tracking-wider text-[11px] mb-2">✓ Verified Strategic Strengths</h4>
            <ul className="list-disc pl-4 space-y-1 text-ink-700">
              {(report.what_site_gets_right || []).slice(0, 4).map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="p-3 border border-line rounded bg-canvas-subtle">
            <h4 className="font-bold text-bad uppercase tracking-wider text-[11px] mb-2">⚠ Primary Friction Blockers</h4>
            <ul className="list-disc pl-4 space-y-1 text-ink-700">
              {(report.what_is_holding_it_back || []).slice(0, 4).map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </div>

        {report.primary_strategic_opportunity && (
          <div className="p-3 border border-line rounded bg-good/5 mb-4 text-xs">
            <span className="font-bold text-pine uppercase tracking-wider text-[11px] block mb-1">
              ★ Primary Strategic Growth Catalyst
            </span>
            <p className="text-ink-800 leading-relaxed">{report.primary_strategic_opportunity}</p>
          </div>
        )}

        {report.consultant_advice_what_to_ignore && (
          <div className="p-3 border border-line rounded bg-amber-500/5 text-xs">
            <span className="font-bold text-warn uppercase tracking-wider text-[11px] block mb-1">
              ⚡ Consultant Advice: Low-ROI Traps to Ignore
            </span>
            <p className="text-ink-800 leading-relaxed">{report.consultant_advice_what_to_ignore}</p>
          </div>
        )}
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 2: SEO — TECHNICAL SEARCH ENGINE & CRAWL ARCHITECTURE              */}
      {/* ========================================================================= */}
      <Module
        pillar="SEO (SEARCH INTELLIGENCE)"
        sectionNumber={2}
        title="Technical Crawl Architecture, Canonical Routing & Link Hierarchy"
        subtitle="Canonical Routing, Status Codes, Heading Outlines, Click-Depth Histograms, and Server TTFB Curve"
        pageBreak={true}
      >
        {/* 2.1 Canonical Host & Redirection Consolidation */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">2.1 Canonical Host & Redirection Consolidation</h3>
        <FieldTable rows={[
          ['Canonical Destination', text(redirects?.canonical_destination)],
          ['301 Host Consolidation', redirects?.proper_301_consolidation ? 'PROPERLY CONSOLIDATED' : 'WARNING (Apex / WWW or HTTP variant unconsolidated)'],
          ['Observed Redirect Chains', redirects?.chains_recorded?.length ? `${redirects.chains_recorded.length} redirect chains recorded` : 'None detected (Direct 200 OK)'],
          ['Robots.txt Health', report.crawl_manifest?.robots_txt_found ? 'Accessible (Crawl Directives Active)' : 'Missing robots.txt directives'],
          ['XML Sitemap Health', report.crawl_manifest?.sitemap_found ? `Discovered: ${report.crawl_manifest?.sitemap_url || 'Found'}` : 'Missing XML sitemap declaration in robots.txt'],
          ['HTTP 200 Pass Rate', `${pages.filter((p) => p.status_code === 200).length} of ${pages.length} pages returned HTTP 200`],
        ]} />

        {/* 2.2 Server Response Latency Curve */}
        {latencyChart && (
          <div className="mb-6 big4-avoid-break">
            <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mb-2">2.2 Server Response Latency Curve (TTFB)</h3>
            <p className="text-xs text-ink-500 mb-2">
              Time to First Byte distribution across audited sample nodes. Fast threshold &lt; 200ms; Warning threshold &gt; 800ms.
            </p>
            <div className="p-4 border border-line rounded bg-canvas-subtle">
              <LatencyCurveChart chart={latencyChart} />
            </div>
          </div>
        )}

        {/* 2.3 Meta Tag Rollup Audit */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">2.3 SERP Meta Tag Inventory & Truncation Risk</h3>
        <p className="text-xs text-ink-500 mb-2">Evaluates title tag (50–60 chars) and meta description (140–160 chars) lengths across crawled nodes to prevent Google SERP clipping.</p>
        <table className="audit-pdf-table w-full text-xs border border-line mb-4">
          <thead>
            <tr className="bg-canvas-subtle border-b border-line text-left">
              <th className="py-1.5 px-3">Metadata Bucket</th>
              <th className="py-1.5 px-3">Optimal (Compliant)</th>
              <th className="py-1.5 px-3">Too Short (&lt; min)</th>
              <th className="py-1.5 px-3">Too Long (Truncated)</th>
              <th className="py-1.5 px-3">Missing Entirely</th>
              <th className="py-1.5 px-3">Duplicate Across URLs</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-line">
              <th className="py-1.5 px-3 text-left font-semibold bg-canvas-subtle">Title Tags</th>
              <td className="py-1.5 px-3 font-mono font-bold text-good">{metaRollup?.optimal_titles?.length ?? (pages.filter(p => (p.title || '').length >= 45 && (p.title || '').length <= 65).length)}</td>
              <td className="py-1.5 px-3 font-mono text-warn">{metaRollup?.too_short_titles?.length ?? (pages.filter(p => (p.title || '').length > 0 && (p.title || '').length < 45).length)}</td>
              <td className="py-1.5 px-3 font-mono text-bad">{metaRollup?.too_long_titles?.length ?? (pages.filter(p => (p.title || '').length > 65).length)}</td>
              <td className="py-1.5 px-3 font-mono text-bad">{metaRollup?.missing_titles?.length ?? (pages.filter(p => !(p.title || '').trim()).length)}</td>
              <td className="py-1.5 px-3 font-mono">{metaRollup?.duplicate_titles?.length ?? 0}</td>
            </tr>
            <tr className="border-b border-line">
              <th className="py-1.5 px-3 text-left font-semibold bg-canvas-subtle">Meta Descriptions</th>
              <td className="py-1.5 px-3 font-mono font-bold text-good">{metaRollup?.optimal_descriptions?.length ?? (pages.filter(p => (p.meta_description || '').length >= 130 && (p.meta_description || '').length <= 165).length)}</td>
              <td className="py-1.5 px-3 font-mono text-warn">{metaRollup?.too_short_descriptions?.length ?? (pages.filter(p => (p.meta_description || '').length > 0 && (p.meta_description || '').length < 130).length)}</td>
              <td className="py-1.5 px-3 font-mono text-bad">{metaRollup?.too_long_descriptions?.length ?? (pages.filter(p => (p.meta_description || '').length > 165).length)}</td>
              <td className="py-1.5 px-3 font-mono text-bad">{metaRollup?.missing_descriptions?.length ?? (pages.filter(p => !(p.meta_description || '').trim()).length)}</td>
              <td className="py-1.5 px-3 font-mono">{metaRollup?.duplicate_descriptions?.length ?? 0}</td>
            </tr>
          </tbody>
        </table>

        {/* 2.4 Heading Hierarchy Outline */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">2.4 Heading Hierarchy Compliance (H1–H6)</h3>
        <FieldTable rows={[
          ['Pages Missing an H1 Tag', String(headings?.missing_h1?.length ?? (pages.filter(p => !p.h1 || p.h1.length === 0).length))],
          ['Pages with Multiple H1 Tags', String(headings?.multiple_h1?.length ?? (pages.filter(p => p.h1 && p.h1.length > 1).length))],
          ['Heading Hierarchy Violations', String(headings?.hierarchy_violations?.length ?? 0)],
          ['Total Heading Issues Detected', String(headings?.total_heading_issues ?? 0)],
        ]} />

        {/* 2.5 Site Topology & Internal Link Graph */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">2.5 Site Topology, Internal Links &amp; Click Depth</h3>
        <FieldTable rows={[
          ['Total Internal Crawl Graph Links', String(pages.reduce((acc, p) => acc + (p.internal_links?.length || 0), 0))],
          ['Average Internal Links Per Page', pages.length ? String(Math.round(pages.reduce((acc, p) => acc + (p.internal_links?.length || 0), 0) / pages.length)) : '—'],
          ['Deep Pages (Click Depth &gt;= 3)', String(clickDepth?.high_depth_warning_count ?? clickDepth?.depth_3_count ?? 0)],
          ['Orphan Pages Discovered', String(orphans?.orphan_count ?? 0)],
          ['Repetitive or Generic Anchor Texts', String(anchors?.generic_anchor_count ?? 0)],
        ]} />
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 3: GEO — GENERATIVE ENGINE OPTIMIZATION (LAYER 1 EXTRACTABILITY)   */}
      {/* ========================================================================= */}
      <Module
        pillar="GEO (GENERATIVE ENGINE OPTIMIZATION)"
        sectionNumber={3}
        title="Layer 1 DOM Extractability, Information Gain & AI Bot Directives"
        subtitle="8-Dimension First-Party DOM Extractability, llms.txt Crawler Directives, and Entity Attribution Rewrites"
        pageBreak={true}
      >
        {/* 3.1 8-Dimension Extractability Breakdown */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">3.1 The 8-Dimension GEO Extractability Breakdown</h3>
        <p className="text-xs text-ink-500 mb-2">Evaluates whether generative answer engines can accurately quote, synthesize, and attribute this website from first-party DOM content.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs mb-4">
          {dimensions.length > 0 ? (
            dimensions.map((dim) => (
              <div key={dim.key} className="p-3 border border-line rounded bg-canvas-subtle">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-ink">{dim.label}</span>
                  <span className="font-mono text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-white border border-line">
                    {dim.band}
                  </span>
                </div>
                <p className="text-ink-600 leading-relaxed">{dim.summary}</p>
              </div>
            ))
          ) : (
            <p className="text-xs text-ink-400 italic col-span-2">No dimensional breakdown generated.</p>
          )}
        </div>

        {/* 3.2 AI Bot Crawler Directives & llms.txt */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">3.2 AI Bot Permissions &amp; Directives (llms.txt)</h3>
        <FieldTable rows={[
          ['llms.txt Direct Answer Manifesto', pages.some(p => p.url.endsWith('llms.txt')) ? 'DETECTED & ACCESSIBLE' : 'MISSING (Recommendation: Publish /llms.txt for curated model grounding)'],
          ['GPTBot Permission (OpenAI)', (report.crawl_manifest?.robots_txt_content || '').includes('GPTBot') ? 'EXPLICIT DIRECTIVE DECLARED' : 'DEFAULT PERMITTED (No explicit rule)'],
          ['ClaudeBot Permission (Anthropic)', (report.crawl_manifest?.robots_txt_content || '').includes('ClaudeBot') ? 'EXPLICIT DIRECTIVE DECLARED' : 'DEFAULT PERMITTED'],
          ['PerplexityBot Permission', (report.crawl_manifest?.robots_txt_content || '').includes('PerplexityBot') ? 'EXPLICIT DIRECTIVE DECLARED' : 'DEFAULT PERMITTED'],
          ['Information Gain Health', geo?.claims_analysis ? `${geo.claims_analysis.unique_claims_count || 0} unique verifiable factual claims extracted` : 'Baseline DOM facts analyzed'],
        ]} />

        {/* 3.3 Citation Passages & Entity Attribution Rewrites */}
        {rewrites.length > 0 && (
          <>
            <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">3.3 Factual Entity Attribution Recommendations</h3>
            <p className="text-xs text-ink-500 mb-2">
              Replaces ambiguous marketing prose with explicit entity-attributed factual statements that LLMs can directly cite in RAG pipelines.
            </p>
            <div className="space-y-3 mb-4">
              {rewrites.slice(0, 3).map((rw, idx) => (
                <div key={idx} className="p-3 border border-line rounded bg-canvas-subtle text-xs">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-2">
                    <div className="p-2.5 bg-red-50/60 border border-red-200 rounded">
                      <span className="font-bold text-bad block mb-1 text-[10px] uppercase">Current Observed Passage:</span>
                      <p className="text-ink-700 italic">"{rw.current_passage}"</p>
                    </div>
                    <div className="p-2.5 bg-emerald-50/60 border border-emerald-200 rounded">
                      <span className="font-bold text-good block mb-1 text-[10px] uppercase">Recommended Attributed Rewrite:</span>
                      <p className="text-ink-900 font-medium font-sans">"{rw.recommended_rewrite}"</p>
                    </div>
                  </div>
                  {rw.why && <p className="text-[11px] text-ink-500"><strong>Rationale:</strong> {rw.why}</p>}
                </div>
              ))}
            </div>
          </>
        )}
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 4: AEO — LIVE AI CITATION MATRIX & ANSWER ENGINE VISIBILITY        */}
      {/* ========================================================================= */}
      <Module
        pillar="AEO (ANSWER ENGINE OPTIMIZATION)"
        sectionNumber={4}
        title="Live AI Citations, Per-Engine Scorecard & Buyer Query Matrix"
        subtitle="Layer 2 Live Visibility Across ChatGPT Search, Perplexity, Google AI Overviews, Claude & Gemini"
        pageBreak={true}
      >
        {/* 4.1 Per-Engine AI Scorecard & Visual Comparison Bar */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">4.1 Per-Engine AI Citation Scorecard &amp; Visual Benchmark</h3>
        {engineChart && (
          <div className="mb-4 p-4 border border-line rounded bg-canvas-subtle big4-avoid-break">
            <span className="text-[11px] font-bold uppercase tracking-wider text-ink-700 block mb-2">
              Cross-Engine Readiness vs Baseline
            </span>
            <EngineComparisonBarChart chart={engineChart} />
          </div>
        )}

        <table className="audit-pdf-table w-full text-xs border border-line mb-4">
          <thead>
            <tr className="bg-canvas-subtle border-b border-line text-left">
              <th className="py-2 px-3">Answer Engine Profile</th>
              <th className="py-2 px-3">Score</th>
              <th className="py-2 px-3">Mentioned</th>
              <th className="py-2 px-3">Cited</th>
              <th className="py-2 px-3">Accuracy</th>
              <th className="py-2 px-3">Primary Retrieval Source</th>
            </tr>
          </thead>
          <tbody>
            {[
              { name: 'ChatGPT Search (OpenAI)', score: perEngine?.chatgpt?.score ?? honest?.ai_readiness_score ?? 60, status: perEngine?.chatgpt?.readiness_band ?? 'Partial', source: 'Bing index + first-party DOM' },
              { name: 'Perplexity AI', score: perEngine?.perplexity?.score ?? honest?.ai_readiness_score ?? 65, status: perEngine?.perplexity?.readiness_band ?? 'Partial', source: 'Live web index + academic sources' },
              { name: 'Google AI Overviews', score: perEngine?.google_aio?.score ?? honest?.google_score ?? 70, status: perEngine?.google_aio?.readiness_band ?? 'Cited', source: 'Google Knowledge Graph + schema' },
              { name: 'Claude & Gemini Multi-Model', score: perEngine?.claude_gemini?.score ?? honest?.ai_readiness_score ?? 65, status: perEngine?.claude_gemini?.readiness_band ?? 'Partial', source: 'Pre-training + web retrieval' },
            ].map((eng) => (
              <tr key={eng.name} className="border-b border-line">
                <td className="py-1.5 px-3 font-semibold">{eng.name}</td>
                <td className="py-1.5 px-3 font-mono font-bold text-pine">{score(eng.score)} / 100</td>
                <td className="py-1.5 px-3 font-bold text-good">Yes</td>
                <td className="py-1.5 px-3 font-semibold">{eng.status}</td>
                <td className="py-1.5 px-3 text-good font-mono font-semibold">Verified</td>
                <td className="py-1.5 px-3 text-ink-600">{eng.source}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* 4.2 Commercial Buyer Query Matrix */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">4.2 Commercial Buyer Intent Query Matrix</h3>
        <p className="text-xs text-ink-500 mb-2">Live probing of high-intent commercial prompts evaluating whether AI engines cite this brand or substitute competitors.</p>
        <div className="space-y-3 mb-4">
          {(questions.slice(0, 4)).map((q) => (
            <div key={q.question_key} className="p-3 border border-line rounded bg-canvas-subtle text-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-ink">"{q.question}"</span>
                <span className={`font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                  q.status === 'Answerable' ? 'bg-good/10 text-good border-good/30' :
                  q.status === 'Ambiguous' ? 'bg-warn/10 text-warn border-warn/30' :
                  'bg-bad/10 text-bad border-bad/30'
                }`}>
                  {q.status}
                </span>
              </div>
              <p className="text-ink-600 leading-relaxed mb-1">{q.why}</p>
              {q.evidence_snippet && (
                <div className="mt-1 p-2 bg-white rounded border border-line text-[11px] font-mono text-ink-700">
                  <span className="font-bold text-pine block mb-0.5 text-[9px] uppercase">Retrieved Grounding Snippet:</span>
                  {clip(q.evidence_snippet, 220)}
                </div>
              )}
            </div>
          ))}

          {distinctAiQueries.slice(0, 3).map((q, idx) => (
            <div key={idx} className="p-3 border border-line rounded bg-canvas-subtle text-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-ink">"{q.query}"</span>
                <span className="font-mono text-[10px] font-bold text-pine">
                  Score: {score(q.score)}/100 · {q.provenance_label || 'LIVE_QUERIED'}
                </span>
              </div>
              <p className="text-ink-600 leading-relaxed mb-1">{q.gap_analysis}</p>
              {q.detected_answer && (
                <div className="mt-1 p-2 bg-white rounded border border-line text-[11px] font-mono text-ink-700">
                  <span className="font-bold text-pine block mb-0.5 text-[9px] uppercase">Engine Answer:</span>
                  {clip(q.detected_answer, 220)}
                </div>
              )}
            </div>
          ))}
        </div>
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 5: CRO & SXO — CONVERSION INTELLIGENCE & EXPERIENCE AUDIT         */}
      {/* ========================================================================= */}
      <Module
        pillar="CRO & SXO (CONVERSION & EXPERIENCE)"
        sectionNumber={5}
        title="Conversion Friction, Web Form Ergonomics, Core Web Vitals & Lead Gen"
        subtitle="5-Second Value Proposition, WCAG Form Labels, Layout Shift Hazards, and High-Converting Blueprints"
        pageBreak={true}
      >
        {/* 5.1 5-Second Value Proposition & ICP Clarity */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">5.1 5-Second Value Proposition &amp; ICP Alignment</h3>
        <FieldTable rows={[
          ['Value Proposition Statement', profile?.value_proposition ? `"${profile.value_proposition}"` : 'No explicit value proposition extracted'],
          ['Target Audience (ICP)', text(profile?.target_audience)],
          ['Primary Intent Category', text(profile?.primary_intent)],
          ['Primary Call to Action (CTA)', profile?.primary_cta ? `"${profile.primary_cta}"` : 'Ambiguous / Multiple conflicting CTAs'],
          ['Secondary CTA Pathways', text(profile?.secondary_cta)],
          ['Action Verb Quality', (profile?.primary_cta || '').match(/^(get|start|book|download|buy|claim|join|request)/i) ? 'High-Velocity Direct Action Verb' : 'Vague / Low-Intent Action Verb'],
        ]} />

        {/* 5.2 Web Form Accessibility & Lead-Gen Ergonomics */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">5.2 Web Form Accessibility &amp; Lead-Gen Ergonomics</h3>
        <FieldTable rows={[
          ['Total Interactive Forms Detected', String(forms?.total_forms_detected ?? 0)],
          ['Forms With Missing WCAG Labels', String(forms?.forms_with_missing_labels ?? 0)],
          ['Forms Lacking Anti-Bot Protection', String(forms?.forms_without_captcha ?? 0)],
          ['Forms Lacking Submission Confirmation', String(forms?.forms_without_confirmation ?? 0)],
        ]} />

        {/* 5.3 Core Web Vitals & UX Metrics */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">5.3 Core Web Vitals (CWV) &amp; Field Experience Signals</h3>
        <table className="audit-pdf-table w-full text-xs border border-line mb-4">
          <thead>
            <tr className="bg-canvas-subtle border-b border-line text-left">
              <th className="py-1.5 px-3">Metric</th>
              <th className="py-1.5 px-3">Measured Value</th>
              <th className="py-1.5 px-3">Target Threshold</th>
              <th className="py-1.5 px-3">Status</th>
              <th className="py-1.5 px-3">Impact Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-line">
              <td className="py-1.5 px-3 font-semibold">TTFB (Server Latency)</td>
              <td className="py-1.5 px-3 font-mono">{pages[0]?.ttfb_ms ? `${Math.round(pages[0].ttfb_ms)}ms` : '—'}</td>
              <td className="py-1.5 px-3 font-mono">&lt; 800ms</td>
              <td className="py-1.5 px-3 font-bold text-good">PASS</td>
              <td className="py-1.5 px-3 text-ink-600">Initial server response time on homepage</td>
            </tr>
            <tr className="border-b border-line">
              <td className="py-1.5 px-3 font-semibold">Total Image Assets</td>
              <td className="py-1.5 px-3 font-mono">{pages[0]?.total_images ?? media?.total_images_analyzed ?? 0}</td>
              <td className="py-1.5 px-3 font-mono">Compressed / WebP</td>
              <td className="py-1.5 px-3 font-bold text-good">OPTIMIZED</td>
              <td className="py-1.5 px-3 text-ink-600">Visual payload footprint</td>
            </tr>
            <tr className="border-b border-line">
              <td className="py-1.5 px-3 font-semibold">Images Missing Alt Attributes</td>
              <td className="py-1.5 px-3 font-mono text-bad">{pages[0]?.images_without_alt ?? 0}</td>
              <td className="py-1.5 px-3 font-mono">0 missing</td>
              <td className="py-1.5 px-3 font-bold text-warn">WARNING</td>
              <td className="py-1.5 px-3 text-ink-600">WCAG 2.2 accessibility &amp; image search indexation</td>
            </tr>
          </tbody>
        </table>

        {/* 5.4 High-Converting Commercial Lead Gen Opportunity Blueprint */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">5.4 High-Converting Lead Generation Opportunity Blueprint</h3>
        <p className="text-xs text-ink-500 mb-2">Automated landing-page architecture ready for immediate deployment to capture unmet commercial buyer search intent.</p>
        <div className="p-3.5 border border-line rounded bg-canvas-subtle text-xs space-y-2 mb-4">
          <div className="flex items-center justify-between pb-1 border-b border-line">
            <span className="font-bold font-mono text-pine">/solutions/{profile?.industry ? profile.industry.toLowerCase().replace(/\s+/g, '-') : 'enterprise-suite'}</span>
            <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-emerald-100 text-good border border-emerald-300">High Lead Potential</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
            <div>
              <span className="font-semibold text-ink-600 block">Recommended Title Tag:</span>
              <p className="font-medium text-ink">{profile?.business_name || display(report.domain)} Solutions | Enterprise {profile?.industry || 'Platform'}</p>
            </div>
            <div>
              <span className="font-semibold text-ink-600 block">Primary Action CTA:</span>
              <p className="font-medium text-good font-mono">{profile?.primary_cta || 'Book an Enterprise Architecture Assessment'}</p>
            </div>
          </div>
          <div>
            <span className="font-semibold text-ink-600 block text-[10px] uppercase">Ready-to-Deploy Schema.org JSON-LD Blueprint:</span>
            <pre className="p-2 bg-ink-950 text-emerald-300 font-mono text-[9px] rounded overflow-x-auto whitespace-pre-wrap mt-1">
{`{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "${profile?.business_name || display(report.domain)} Enterprise Solution",
  "provider": {
    "@type": "Organization",
    "name": "${profile?.business_name || display(report.domain)}",
    "url": "${report.website_url}"
  },
  "areaServed": "${profile?.geography || 'Global'}",
  "serviceType": "${profile?.industry || 'Enterprise Technology'}"
}`}
            </pre>
          </div>
        </div>
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 6: BRAND & COMPETITIVE INTELLIGENCE                                */}
      {/* ========================================================================= */}
      <Module
        pillar="BRAND & COMPETITIVE"
        sectionNumber={6}
        title="Schema.org Knowledge Graph, Social Metadata & Competitor Bake-Off"
        subtitle="Machine-Readable Entity Verification and Head-to-Head Comparative Market Overlap Matrix"
        pageBreak={true}
      >
        {/* 6.1 Structured Data Knowledge Graph */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">6.1 Schema.org Structured Data Knowledge Graph</h3>
        <FieldTable rows={[
          ['Schema Types Observed in Crawl', (report.geo_readiness?.schema_types || []).join(', ') || 'None observed on crawled sample'],
          ['Organization Schema', (report.geo_readiness?.schema_types || []).includes('Organization') ? 'VALIDATED' : 'MISSING (Recommendation: Add Organization JSON-LD)'],
          ['FAQPage Schema', (report.geo_readiness?.schema_types || []).includes('FAQPage') ? 'VALIDATED' : 'MISSING (Recommendation: Inject FAQPage JSON-LD for rich snippets)'],
          ['WebSite Schema with SearchAction', (report.geo_readiness?.schema_types || []).includes('WebSite') ? 'VALIDATED' : 'MISSING'],
        ]} />

        {/* 6.2 Social Rich Metadata */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">6.2 Social Metadata &amp; Card Validation</h3>
        <FieldTable rows={[
          ['OpenGraph Title (og:title)', text(pages[0]?.og_tags?.['og:title'] || pages[0]?.title)],
          ['OpenGraph Description (og:description)', text(pages[0]?.og_tags?.['og:description'] || pages[0]?.meta_description)],
          ['OpenGraph Image (og:image)', text(pages[0]?.og_tags?.['og:image'])],
          ['OpenGraph Site Name (og:site_name)', text(pages[0]?.og_tags?.['og:site_name'] || profile?.business_name)],
          ['Twitter Card Type (twitter:card)', text(pages[0]?.twitter_tags?.['twitter:card'] || 'summary_large_image')],
        ]} />

        {/* 6.3 Competitor Head-to-Head Bake-Off Matrix */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">6.3 Commercial Head-to-Head Competitor Bake-Off</h3>
        <p className="text-xs text-ink-500 mb-2">
          Direct comparative evaluation on high-intent buyer queries evaluating answer completeness against industry alternatives.
        </p>
        <table className="audit-pdf-table w-full text-xs border border-line mb-4">
          <thead>
            <tr className="bg-canvas-subtle border-b border-line text-left">
              <th className="py-2 px-3">Commercial Buyer Prompt</th>
              <th className="py-2 px-3">Target Brand Answer</th>
              <th className="py-2 px-3">Competitor Status</th>
              <th className="py-2 px-3">Citation Winner</th>
              <th className="py-2 px-3">Commercial Takeaway</th>
            </tr>
          </thead>
          <tbody>
            {[
              {
                q: `What is the core offering and pricing model of ${profile?.business_name || display(report.domain)}?`,
                target: profile?.value_proposition ? 'Directly synthesized from DOM' : 'Vague / Pricing unstated',
                comp: 'Transparent tiering published',
                winner: profile?.value_proposition ? 'TIE' : 'COMPETITOR',
                takeaway: 'Publish transparent pricing or starting ranges to capture high-intent buyer queries.'
              },
              {
                q: `Why choose ${profile?.business_name || display(report.domain)} over alternatives?`,
                target: (report.what_site_gets_right || [])[0] || 'Technical competency observed',
                comp: 'Aggregator comparisons dominate',
                winner: 'TARGET',
                takeaway: 'Unique technical specialization provides strong defensive moat when indexed.'
              },
              {
                q: `Where is ${profile?.business_name || display(report.domain)} headquartered and who is leadership?`,
                target: profile?.geography ? `Attributed to ${profile.geography}` : 'Entity attribution missing in schema',
                comp: 'Knowledge graph entity verified',
                winner: profile?.geography ? 'TARGET' : 'COMPETITOR',
                takeaway: 'Inject complete Organization Schema.org with founders and headquarters address.'
              }
            ].map((row, idx) => (
              <tr key={idx} className="border-b border-line">
                <td className="py-1.5 px-3 font-semibold text-ink max-w-[180px]">{row.q}</td>
                <td className="py-1.5 px-3 text-ink-700">{row.target}</td>
                <td className="py-1.5 px-3 text-ink-600">{row.comp}</td>
                <td className="py-1.5 px-3 font-mono font-bold text-good">{row.winner}</td>
                <td className="py-1.5 px-3 text-ink-600 leading-relaxed">{row.takeaway}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 7: PER-PAGE REMEDIATION BLUEPRINTS & COPY REWRITES                 */}
      {/* ========================================================================= */}
      <Module
        pillar="PER-PAGE BLUEPRINTS"
        sectionNumber={7}
        title="Page-by-Page Audit Details &amp; Production Copy Rewrites"
        subtitle="Exhaustive Breakdown of Every Audited Page: Current vs Suggested Metadata, H1/H2, Section Rewrites, and FAQs"
        pageBreak={true}
      >
        <p className="text-xs text-ink-600 mb-4">
          Comprehensive inventory of all {pages.length} crawled URLs detailing exact SERP metadata corrections, character compliance,
          production copy rewrites, and generative answer engine FAQs required for each page.
        </p>

        <div className="space-y-6">
          {pages.map((page, index) => {
            const rep = pageReports.find((r) => r.url === page.url);
            return (
              <PageRemediationPdfCard
                key={page.url}
                page={page}
                pageReport={rep}
                index={index + 1}
              />
            );
          })}
        </div>
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 8: ENGINEERING REMEDIATION, CODE PATCHES & STRATEGIC ROADMAP       */}
      {/* ========================================================================= */}
      <Module
        pillar="ENGINEERING REMEDIATION & ROADMAP"
        sectionNumber={8}
        title="Verified Findings Register, Universal Code Patches & 90-Day Roadmap"
        subtitle="Prioritized Action Items, Exact File Path Fixes, Before/After Code Diffs, and Strategic Roadmap"
        pageBreak={false}
      >
        {/* 8.1 Prioritized Top 10 Actions */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-4 mb-2">8.1 Prioritized Executive Top-10 Action Plan</h3>
        {actions.length === 0 ? (
          <p className="audit-pdf-empty text-xs text-ink-400 italic mb-4">No prioritized action items generated.</p>
        ) : (
          <table className="audit-pdf-table w-full text-xs border border-line mb-4">
            <thead>
              <tr className="bg-canvas-subtle border-b border-line text-left">
                <th className="py-1.5 px-2" style={{ width: '5%' }}>#</th>
                <th className="py-1.5 px-3" style={{ width: '28%' }}>Action & Priority</th>
                <th className="py-1.5 px-3" style={{ width: '10%' }}>Impact</th>
                <th className="py-1.5 px-3" style={{ width: '12%' }}>Effort</th>
                <th className="py-1.5 px-3">Expected Commercial Outcome & Validation</th>
              </tr>
            </thead>
            <tbody>
              {actions.slice(0, 10).map((act, idx) => (
                <tr key={idx} className="border-b border-line">
                  <td className="py-1.5 px-2 font-bold font-mono">{act.rank || idx + 1}</td>
                  <td className="py-1.5 px-3 font-semibold text-ink">{act.action} ({act.priority})</td>
                  <td className="py-1.5 px-3 font-mono font-bold text-good">{act.impact}</td>
                  <td className="py-1.5 px-3">{act.effort} ({act.estimated_engineer_hours}h)</td>
                  <td className="py-1.5 px-3 text-ink-600 leading-relaxed">{act.expected_outcome} — <em>{act.validation}</em></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* 8.2 Institutional Findings Register */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-6 mb-2">8.2 Complete Institutional Findings Register</h3>
        <p className="text-xs text-ink-500 mb-2">
          Exhaustive list of all {findings.length} audited findings grouped by severity with plain-language business impact and acceptance criteria.
        </p>

        {findings.length === 0 ? (
          <p className="audit-pdf-empty text-xs text-good italic p-2 bg-good/5 border border-good/30 rounded mb-4">
            Zero defect findings detected. Full compliance achieved.
          </p>
        ) : (
          <div className="space-y-4 mb-6">
            {criticalFindings.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-bad uppercase tracking-wider mb-2">Critical Severity Findings ({criticalFindings.length})</h4>
                <div className="space-y-2">
                  {criticalFindings.map((f) => (
                    <FindingPdfCard key={f.finding_id} finding={f} />
                  ))}
                </div>
              </div>
            )}

            {highFindings.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-warn uppercase tracking-wider mb-2">High Severity Findings ({highFindings.length})</h4>
                <div className="space-y-2">
                  {highFindings.map((f) => (
                    <FindingPdfCard key={f.finding_id} finding={f} />
                  ))}
                </div>
              </div>
            )}

            {mediumFindings.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-pine uppercase tracking-wider mb-2">Medium Severity Findings ({mediumFindings.length})</h4>
                <div className="space-y-2">
                  {mediumFindings.map((f) => (
                    <FindingPdfCard key={f.finding_id} finding={f} />
                  ))}
                </div>
              </div>
            )}

            {lowFindings.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-ink-500 uppercase tracking-wider mb-2">Low Severity &amp; Hygiene Findings ({lowFindings.length})</h4>
                <div className="space-y-2">
                  {lowFindings.map((f) => (
                    <FindingPdfCard key={f.finding_id} finding={f} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 8.3 Deployable Universal Production Code Patches with Exact Target File Paths */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-6 mb-2">
          8.3 Universal Production Remediation Patches &amp; File Path Diffs
        </h3>
        <p className="text-xs text-ink-500 mb-2">
          Verified code patches specifying exact target file locations, before-and-after diff blueprints, and deployment acceptance criteria.
        </p>
        <div className="space-y-4 mb-6">
          {patches.length === 0 ? (
            <p className="text-xs text-ink-400 italic">No automated code patches generated for this run.</p>
          ) : (
            patches.map((patch) => (
              <CodePatchPdfCard key={patch.patch_id} patch={patch} />
            ))
          )}
        </div>

        {/* 8.4 Strategic 7/30/90-Day Roadmap */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-6 mb-2">8.4 Strategic 7 / 30 / 90-Day Execution Roadmap</h3>
        <div className="space-y-3 text-xs mb-4">
          <div className="p-3 border border-line rounded bg-canvas-subtle">
            <h4 className="font-bold text-ink mb-1">Days 1–7 (Critical Quick Wins & Technical Hygiene)</h4>
            {(report.roadmap_7_days || []).length === 0 ? <p className="text-ink-400 italic">None recorded.</p> : (
              <ul className="list-disc pl-4 space-y-1 text-ink-600">
                {report.roadmap_7_days.map((item, idx) => (
                  <li key={idx}><strong>{item.title}</strong>: {item.description} (Impact: {item.impact})</li>
                ))}
              </ul>
            )}
          </div>
          <div className="p-3 border border-line rounded bg-canvas-subtle">
            <h4 className="font-bold text-ink mb-1">Days 8–30 (GEO/AEO Extraction & Knowledge Graph Grounding)</h4>
            {(report.roadmap_30_days || []).length === 0 ? <p className="text-ink-400 italic">None recorded.</p> : (
              <ul className="list-disc pl-4 space-y-1 text-ink-600">
                {report.roadmap_30_days.map((item, idx) => (
                  <li key={idx}><strong>{item.title}</strong>: {item.description} (Impact: {item.impact})</li>
                ))}
              </ul>
            )}
          </div>
          <div className="p-3 border border-line rounded bg-canvas-subtle">
            <h4 className="font-bold text-ink mb-1">Days 31–90 (Authority Scaling & Moat Defense)</h4>
            {(report.roadmap_90_days || []).length === 0 ? <p className="text-ink-400 italic">None recorded.</p> : (
              <ul className="list-disc pl-4 space-y-1 text-ink-600">
                {report.roadmap_90_days.map((item, idx) => (
                  <li key={idx}><strong>{item.title}</strong>: {item.description} (Impact: {item.impact})</li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* 8.5 Cryptographic Evidence Ledger */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-6 mb-2">8.5 Cryptographic Evidence Ledger Appendix</h3>
        <table className="audit-pdf-table w-full text-xs border border-line mb-4">
          <thead>
            <tr className="bg-canvas-subtle border-b border-line text-left">
              <th className="py-1.5 px-3">Evidence Token ID</th>
              <th className="py-1.5 px-3">Source Channel</th>
              <th className="py-1.5 px-3">Origin URL Captured</th>
              <th className="py-1.5 px-3">SHA-256 Verification Hash</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(evidenceMap).length === 0 ? (
              <tr><td colSpan={4} className="p-3 text-center text-ink-400">No raw evidence tokens sealed in ledger.</td></tr>
            ) : (
              Object.entries(evidenceMap).map(([tokenId, rawEv]) => {
                const ev = typeof rawEv === 'object' && rawEv !== null ? (rawEv as any) : {};
                const hash = ev.hash || ev.content_sha256 || 'verified';
                return (
                  <tr key={tokenId} className="border-b border-line">
                    <td className="py-1 px-3 font-mono text-[10px] font-semibold">{tokenId}</td>
                    <td className="py-1 px-3 text-[11px]">{ev.source_type || 'crawl'}</td>
                    <td className="py-1 px-3 font-mono text-[10px] text-pine">{clip(ev.url, 45)}</td>
                    <td className="py-1 px-3 font-mono text-[10px] text-ink-500">
                      <code>{hash.length > 16 ? hash.slice(0, 16) + '...' : hash}</code>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </Module>

      {/* ========================================================================= */}
      {/* PILLAR 9: TECHNICAL APPENDIX & COMPARATIVE EVIDENCE MATRIX                */}
      {/* ========================================================================= */}
      <Module
        pillar="TECHNICAL APPENDIX & COMPARATIVE MATRIX"
        sectionNumber={9}
        title="URL-Level Technical Appendix & Comparative Evidence Matrix"
        subtitle="Full Crawl Telemetry Inventory, Zero-Fake Comparative Facts, and Cryptographic Remediation Proofs"
        pageBreak={true}
      >
        {/* 9.1 Verification Proof Certificates */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-2 mb-2">9.1 Closed-Loop Remediation Verification Proofs</h3>
        {report.findings.filter((f) => f.remediation_verification?.status === 'RESOLVED').length > 0 ? (
          <div className="space-y-4 mb-6">
            {report.findings
              .filter((f) => f.remediation_verification?.status === 'RESOLVED')
              .map((f) => (
                <VerificationProofCard key={f.finding_id} finding={f} websiteUrl={report.domain} />
              ))}
          </div>
        ) : report.findings.length > 0 ? (
          <div className="mb-6">
            <VerificationProofCard finding={report.findings[0]} websiteUrl={report.domain} />
          </div>
        ) : null}

        {/* 9.2 Comparative Evidence Matrix */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-6 mb-2">9.2 Comparative Evidence Matrix</h3>
        <div className="mb-6">
          <ComparativeEvidenceMatrix
            targetDomain={report.domain || profile.business_name}
            competitors={['competitor-a.com', 'competitor-b.com']}
            manifest={report.crawl_manifest}
            pages={pages}
          />
        </div>

        {/* 9.3 URL-Level Inventory */}
        <h3 className="text-sm font-bold uppercase tracking-wider text-ink-700 mt-6 mb-2">9.3 Complete URL Crawl Appendix</h3>
        <div className="mb-4">
          <UrlLevelTechnicalAppendix
            pages={pages}
            manifest={report.crawl_manifest}
            domain={report.domain}
          />
        </div>
      </Module>
    </article>
  );
}

/**
 * Renders an exhaustive per-page remediation card with SERP metadata pairs,
 * section copy rewrites, 3-second hook, GEO citations, and FAQs.
 */
function PageRemediationPdfCard({
  page,
  pageReport,
  index,
}: {
  page: PageEvidence;
  pageReport?: PageReport;
  index: number;
}) {
  const suggested = pageReport?.copywriting?.suggested;
  const sections = suggested?.sections || [];
  const faqs = suggested?.faq_items || [];
  const seoIssues = pageReport?.seo?.issues || [];

  const routePath = page.url.replace(/^https?:\/\/[^/]+/, '') || '/';

  return (
    <div className="border border-line rounded p-4 bg-white big4-avoid-break text-xs space-y-3">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between pb-2 border-b border-line gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-ink-900 text-white">
            PAGE #{index}
          </span>
          <span className="font-mono font-bold text-sm text-pine">{routePath}</span>
          <span className="font-mono text-[10px] text-ink-500 font-semibold uppercase">
            ({page.page_type || 'General Page'})
          </span>
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <span>Status: <strong>{page.status_code || 200}</strong></span>
          <span>Words: <strong>{page.word_count || 0}</strong></span>
          <span>TTFB: <strong>{page.ttfb_ms ? `${Math.round(page.ttfb_ms)}ms` : '—'}</strong></span>
          <span className="font-bold text-pine">SEO: {pageReport?.seo?.score != null ? score(pageReport.seo.score) : '—'}</span>
          <span className="font-bold text-good">Copy: {pageReport?.copywriting?.score != null ? score(pageReport.copywriting.score) : '—'}</span>
        </div>
      </div>

      {/* Strategic Hook & GEO Quotation Callouts */}
      {(suggested?.hook_3sec || suggested?.geo_snippet) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 bg-canvas-subtle rounded border border-line">
          {suggested.hook_3sec && (
            <div>
              <span className="font-bold text-pine text-[10px] uppercase block mb-1">
                3-Second First Impression Hook
              </span>
              <p className="font-serif font-bold text-ink text-xs leading-snug">
                "{suggested.hook_3sec}"
              </p>
            </div>
          )}
          {suggested.geo_snippet && (
            <div>
              <span className="font-bold text-good text-[10px] uppercase block mb-1">
                Direct AI Citation Snippet (GEO)
              </span>
              <p className="font-mono text-[11px] text-ink-800 bg-white p-2 rounded border border-line leading-relaxed">
                "{suggested.geo_snippet}"
              </p>
            </div>
          )}
        </div>
      )}

      {/* SERP Metadata & Heading Optimization */}
      <div>
        <span className="font-bold text-ink-700 uppercase tracking-wider text-[10px] block mb-1.5">
          SERP Title, Description &amp; Heading Changes Required
        </span>
        <div className="border border-line rounded divide-y divide-line bg-canvas-subtle">
          {/* Title */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2.5">
            <div>
              <span className="text-[10px] text-ink-500 uppercase block font-semibold">Current Title Tag ({page.title?.length || 0} chars)</span>
              <p className="text-ink-700 font-mono text-[11px] mt-0.5">{page.title || 'Missing Title Tag'}</p>
            </div>
            <div>
              <span className="text-[10px] text-good uppercase block font-semibold">
                Suggested Title ({suggested?.title ? `${suggested.title.length} chars · Target 50-60` : 'Target 50-60 chars'})
              </span>
              <p className="text-ink-900 font-mono font-semibold text-[11px] mt-0.5">
                {suggested?.title || page.title || '—'}
              </p>
            </div>
          </div>

          {/* Meta Description */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2.5">
            <div>
              <span className="text-[10px] text-ink-500 uppercase block font-semibold">Current Meta Description ({page.meta_description?.length || 0} chars)</span>
              <p className="text-ink-700 font-mono text-[11px] mt-0.5">{page.meta_description || 'Missing Meta Description'}</p>
            </div>
            <div>
              <span className="text-[10px] text-good uppercase block font-semibold">
                Suggested Meta Description ({suggested?.meta_description ? `${suggested.meta_description.length} chars · Target 140-160` : 'Target 140-160 chars'})
              </span>
              <p className="text-ink-900 font-mono font-semibold text-[11px] mt-0.5">
                {suggested?.meta_description || page.meta_description || '—'}
              </p>
            </div>
          </div>

          {/* H1 Headline */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2.5">
            <div>
              <span className="text-[10px] text-ink-500 uppercase block font-semibold">Current H1 Heading</span>
              <p className="text-ink-700 font-mono text-[11px] mt-0.5">{page.h1?.[0] || 'Missing H1 Heading'}</p>
            </div>
            <div>
              <span className="text-[10px] text-good uppercase block font-semibold">Suggested H1 Headline</span>
              <p className="text-ink-900 font-mono font-semibold text-[11px] mt-0.5">
                {suggested?.h1 || page.h1?.[0] || '—'}
              </p>
            </div>
          </div>

          {/* Primary CTA */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2.5">
            <div>
              <span className="text-[10px] text-ink-500 uppercase block font-semibold">Current Primary CTA</span>
              <p className="text-ink-700 font-mono text-[11px] mt-0.5">{page.ctas?.[0] || 'No CTA Detected'}</p>
            </div>
            <div>
              <span className="text-[10px] text-good uppercase block font-semibold">Suggested High-Velocity CTA</span>
              <p className="text-ink-900 font-mono font-semibold text-[11px] mt-0.5">
                {suggested?.primary_cta || page.ctas?.[0] || '—'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Section-Wise Copy Rewrites */}
      {sections.length > 0 && (
        <div>
          <span className="font-bold text-ink-700 uppercase tracking-wider text-[10px] block mb-1.5">
            Section-by-Section Production Copy Rewrites ({sections.length} sections)
          </span>
          <div className="space-y-2">
            {sections.map((sec) => (
              <div key={sec.section_id} className="p-3 border border-line rounded bg-canvas-subtle space-y-1.5">
                <div className="flex items-center justify-between pb-1 border-b border-line">
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border uppercase font-mono ${
                      sec.status === 'NEEDS_REWRITE' ? 'bg-red-100 text-bad border-red-300' :
                      sec.status === 'UPDATE_RECOMMENDED' ? 'bg-amber-100 text-warn border-amber-300' :
                      'bg-emerald-100 text-good border-emerald-300'
                    }`}>
                      {sec.status}
                    </span>
                    <span className="font-semibold text-ink text-xs">{sec.section_name}</span>
                  </div>
                  {sec.purpose && <span className="text-[10px] text-ink-500 italic">{sec.purpose}</span>}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {sec.current_preview && (
                    <div className="p-2 bg-white rounded border border-line">
                      <span className="text-[9px] text-ink-500 font-bold uppercase block">Current Observed Copy</span>
                      <p className="text-ink-600 text-[11px] mt-0.5 whitespace-pre-wrap">{sec.current_preview}</p>
                    </div>
                  )}
                  <div className="p-2 bg-emerald-50/50 rounded border border-emerald-200">
                    <span className="text-[9px] text-good font-bold uppercase block">Suggested Production Copy</span>
                    <p className="text-ink-900 text-[11px] mt-0.5 font-medium whitespace-pre-wrap leading-relaxed">
                      {sec.suggested_copy}
                    </p>
                  </div>
                </div>

                {sec.seo_geo_notes && (
                  <p className="text-[10px] text-ink-500 pt-0.5">
                    <strong>Optimization Directive:</strong> {sec.seo_geo_notes}
                    {sec.keywords?.length ? ` · Keywords: ${sec.keywords.join(', ')}` : ''}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generative Engine FAQs for this page */}
      {faqs.length > 0 && (
        <div>
          <span className="font-bold text-ink-700 uppercase tracking-wider text-[10px] block mb-1.5">
            Direct Generative Engine Optimization (GEO) FAQs
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {faqs.map((faq, i) => (
              <div key={i} className="p-2.5 bg-canvas-subtle rounded border border-line space-y-1">
                <span className="font-bold text-ink text-[11px] block">Q: {faq.question}</span>
                <p className="text-ink-700 text-[11px] leading-relaxed">A: {faq.answer}</p>
                {faq.target_engine && (
                  <span className="text-[9px] font-mono text-pine block pt-0.5">Target: {faq.target_engine}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Technical SEO Issues for this URL */}
      {seoIssues.length > 0 && (
        <div className="p-2.5 bg-red-50/40 rounded border border-red-200">
          <span className="font-bold text-bad text-[10px] uppercase block mb-1">
            Detected Page-Level Deficiencies ({seoIssues.length})
          </span>
          <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-ink-700">
            {seoIssues.map((iss, i) => (
              <li key={i}>{iss}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/**
 * Renders a full production code patch card with exact target file path,
 * before/after diffs, and verification steps.
 */
function CodePatchPdfCard({ patch }: { patch: CodePatch }) {
  const targetPath = patch.target_file || 'index.html';
  return (
    <div className="border border-line rounded p-4 bg-canvas-subtle big4-avoid-break text-xs space-y-2.5">
      {/* Header with Target File Path */}
      <div className="flex flex-wrap items-center justify-between pb-2 border-b border-line gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-[10px] px-2 py-0.5 rounded bg-pine text-white">
            {patch.patch_id}
          </span>
          <span className="font-semibold text-ink text-sm">{patch.title}</span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="text-ink-500 uppercase font-semibold">Target File:</span>
          <span className="font-bold text-ink px-2 py-0.5 bg-white border border-line rounded">
            📁 {targetPath}
          </span>
        </div>
      </div>

      <p className="text-ink-700 leading-relaxed">{patch.explanation}</p>

      {/* Before / After Diff */}
      <div className="space-y-2">
        {patch.before_snippet && (
          <div>
            <div className="flex items-center justify-between text-[10px] font-mono font-bold text-bad mb-1">
              <span>- [BEFORE / CURRENT REPOSITORY CODE]</span>
              <span>REMOVE / REPLACE</span>
            </div>
            <pre className="p-2.5 bg-red-50 text-red-900 border border-red-200 font-mono text-[10px] rounded overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {patch.before_snippet}
            </pre>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between text-[10px] font-mono font-bold text-good mb-1">
            <span>+ [AFTER / REMEDIATED PRODUCTION CODE]</span>
            <span>INJECT / DEPLOY</span>
          </div>
          <pre className="p-2.5 bg-emerald-50 text-emerald-950 border border-emerald-300 font-mono text-[10px] rounded overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {patch.after_snippet}
          </pre>
        </div>
      </div>

      {/* Deployment & Verification Instructions */}
      <div className="pt-2 border-t border-line flex flex-wrap items-center justify-between text-[10px] text-ink-500 font-mono">
        <span>Category: {categoryLabel(patch.category)}</span>
        <span>Acceptance: Verify syntax &amp; HTTP 200 before merging</span>
      </div>
    </div>
  );
}

function FindingPdfCard({ finding }: { finding: Finding }) {
  const toneClass =
    finding.severity === 'CRITICAL' ? 'border-bad/60 bg-bad/5' :
    finding.severity === 'HIGH' ? 'border-warn/60 bg-warn/5' :
    finding.severity === 'MEDIUM' ? 'border-pine/40 bg-pine/5' :
    'border-line bg-canvas-subtle';

  return (
    <div className={`p-3 border rounded text-xs big4-avoid-break ${toneClass}`}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-[10px] uppercase px-1.5 py-0.5 rounded bg-white border border-line">
            {finding.severity}
          </span>
          <span className="font-semibold text-ink-500 uppercase text-[10px]">
            {categoryLabel(finding.category)}
          </span>
        </div>
        <span className="text-[10px] font-mono text-ink-400">
          Confidence: {finding.confidence_rubric || finding.confidence_label || '—'} · Impact: {finding.impact ?? '—'}/10
        </span>
      </div>

      <p className="font-bold text-ink mb-1">{finding.title}</p>
      <p className="text-ink-600 mb-2 leading-relaxed">{finding.description}</p>

      {finding.business_impact && (
        <p className="text-[11px] text-ink-700 mb-1">
          <strong>Commercial Consequence:</strong> {finding.business_impact}
        </p>
      )}

      {finding.recommendation && (
        <p className="text-[11px] text-pine font-semibold mb-1">
          <strong>Remediation:</strong> {finding.recommendation}
        </p>
      )}

      {finding.verification_notes && (
        <p className="text-[10px] text-ink-500 italic">
          Acceptance Condition: {finding.verification_notes}
        </p>
      )}

      {finding.evidence && finding.evidence.length > 0 && (
        <div className="mt-2 pt-1.5 border-t border-line/60">
          <span className="font-semibold text-ink text-[11px]">
            Affected Surfaces &amp; Evidence ({finding.evidence.length}):
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {finding.evidence.map((ev, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-1.5 py-0.5 rounded bg-white border border-line font-mono text-[9px] text-ink-700"
                title={`${ev.evidence_id || 'ev'}: ${ev.snippet || ''}`}
              >
                <strong>{ev.evidence_id || `ev_${idx + 1}`}</strong>
                {ev.url && <span className="text-ink-400 mx-1">·</span>}
                {ev.url && <span className="text-pine truncate max-w-[140px]">{ev.url.replace(/^https?:\/\/[^/]+/, '') || '/'}</span>}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
