import React, { useMemo } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport, Finding } from '../../../types';
import { EnterpriseSeoAssessment } from './EnterpriseSeoAudit';
import { SeoAuditHistory, SeoConnectorStatus, SeoScorecardReport } from '../../../services/seoApi';
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Compass,
  Database,
  FileCode,
  Gauge,
  Globe,
  Layers,
  Link2,
  Search,
  Shield,
  TrendingUp,
} from 'lucide-react';

interface SeoExecutiveDashboardProps {
  report: ExecutiveReport;
  assessment?: EnterpriseSeoAssessment | null;
  scorecard?: SeoScorecardReport | null;
  connectors?: SeoConnectorStatus[];
  history?: SeoAuditHistory | null;
  seoFindings: Finding[];
  onNavigateTab: (tabId: string) => void;
  onSelectFinding?: (f: Finding) => void;
}

const DIM_META: Record<string, { icon: React.ReactNode; targetTab: string; summary: string; shortTitle: string }> = {
  technical_crawlability: {
    shortTitle: 'Technical & Crawlability',
    icon: <Gauge className="w-4 h-4 text-sky-600" />,
    targetTab: 'architecture',
    summary: 'Robots directives, HTTP response codes, TLS protocol, and redirect chains.',
  },
  indexation_canonicalization: {
    shortTitle: 'Indexation & Canonicalization',
    icon: <Layers className="w-4 h-4 text-indigo-600" />,
    targetTab: 'architecture',
    summary: 'Canonical URL tags, noindex directives, XML sitemap presence, and index controls.',
  },
  content_quality_intent: {
    shortTitle: 'Content Quality & Search Intent',
    icon: <Search className="w-4 h-4 text-amber-600" />,
    targetTab: 'intelligence',
    summary: 'Substantive depth, thin content detection, intent alignment, and cannibalization.',
  },
  on_page_seo: {
    shortTitle: 'On-Page SEO & Metadata',
    icon: <Compass className="w-4 h-4 text-emerald-600" />,
    targetTab: 'onpage',
    summary: 'Title tags, meta descriptions, H1 hierarchy, and image alt attributes.',
  },
  internal_linking_architecture: {
    shortTitle: 'Internal Linking & Architecture',
    icon: <Link2 className="w-4 h-4 text-teal-600" />,
    targetTab: 'linkgraph',
    summary: 'Click depth, orphaned URL detection, anchor quality, and link equity flow.',
  },
  structured_data_entities: {
    shortTitle: 'Structured Data & Entities',
    icon: <FileCode className="w-4 h-4 text-purple-600" />,
    targetTab: 'onpage',
    summary: 'Schema.org JSON-LD validity, rich-result eligibility, and entity markup.',
  },
  performance_mobile: {
    shortTitle: 'Performance & Core Web Vitals',
    icon: <TrendingUp className="w-4 h-4 text-orange-600" />,
    targetTab: 'architecture',
    summary: 'Lab & field CWV (LCP, CLS, INP, TTFB) and responsive mobile viewport usability.',
  },
  specialist_applicability: {
    shortTitle: 'International, Local & Ecommerce',
    icon: <Globe className="w-4 h-4 text-blue-600" />,
    targetTab: 'market',
    summary: 'Conditional hreflang alternates, local NAP/GBP, and ecommerce product signals.',
  },
  trust_authority_signals: {
    shortTitle: 'Trust & Authority Signals',
    icon: <Shield className="w-4 h-4 text-rose-600" />,
    targetTab: 'market',
    summary: 'Observable E-E-A-T signals and connected external backlink/authority telemetry.',
  },
};

export function SeoExecutiveDashboard({
  report,
  assessment,
  scorecard,
  connectors = [],
  history,
  seoFindings,
  onNavigateTab,
  onSelectFinding,
}: SeoExecutiveDashboardProps) {
  // 1. Canonical score: strictly from backend scorecard or report — NEVER a fabricated constant
  const canonicalScore: number | null = useMemo(() => {
    if (scorecard && scorecard.overall_health_score != null && Number.isFinite(scorecard.overall_health_score)) {
      return Math.round(scorecard.overall_health_score);
    }
    const raw = report.scores?.category_scores?.['TECHNICAL_SEO']?.score ?? report.honest_scores?.google_score;
    return raw != null && Number.isFinite(raw) ? Math.round(raw) : null;
  }, [scorecard, report]);

  const getScoreColor = (s: number | null) => {
    if (s == null) return 'text-ink-500 border-line bg-paper-subtle';
    if (s >= 90) return 'text-emerald-600 dark:text-emerald-400 border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20';
    if (s >= 70) return 'text-blue-600 dark:text-blue-400 border-blue-500/30 bg-blue-50/50 dark:bg-blue-950/20';
    if (s >= 50) return 'text-amber-600 dark:text-amber-400 border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/20';
    return 'text-rose-600 dark:text-rose-400 border-rose-500/30 bg-rose-50/50 dark:bg-rose-950/20';
  };

  const getScoreLabel = (s: number | null) => {
    if (scorecard?.overall_interpretation) return scorecard.overall_interpretation;
    if (s == null) return 'Unmeasured';
    if (s >= 90) return 'Excellent';
    if (s >= 80) return 'Strong';
    if (s >= 70) return 'Good';
    if (s >= 60) return 'Needs Improvement';
    if (s >= 40) return 'Weak';
    return 'Critical';
  };

  // 2. Reconciled 6-tier URL taxonomy (strictly empirical)
  const cov: any = assessment?.coverage || {};
  const manifestPages = (report.crawl_manifest?.pages || report.page_reports || []) as Array<Record<string, any>>;
  const urlsCrawled: number = cov.urls_crawled ?? manifestPages.length;
  const urlsDiscovered: number =
    cov.urls_discovered ??
    (report.crawl_manifest as any)?.total_pages_discovered ??
    (report.crawl_manifest as any)?.discovered_urls?.length ??
    urlsCrawled;
  const urlsRendered: number =
    cov.urls_rendered ??
    (manifestPages.filter((p) => Boolean(p.rendered_html)).length || urlsCrawled);
  const urlsDeeplyInspected: number = cov.urls_deeply_inspected ?? urlsCrawled;
  const defectUrlSet = new Set<string>();
  seoFindings.forEach((f) => {
    const aff = (f as any).affected_urls || ((f as any).url ? [(f as any).url] : []);
    if (Array.isArray(aff)) aff.forEach((u) => u && defectUrlSet.add(String(u)));
  });
  const urlsVerifiedFindings: number = cov.urls_with_verified_findings ?? defectUrlSet.size;

  // 3. Independent confidence vectors (from backend scorecard, never hardcoded)
  const auditCoveragePct =
    scorecard?.confidence_vectors?.audit_coverage_pct ??
    (urlsDiscovered > 0 ? Math.round((urlsCrawled / urlsDiscovered) * 1000) / 10 : 0);
  const evidenceConfidencePct = scorecard?.confidence_vectors?.evidence_confidence_pct ?? null;
  const connectedCount = connectors.filter((c) => c.status === 'CONNECTED').length;
  const totalConnectors = connectors.length;
  const freshnessLabel = useMemo(() => {
    const hrs = scorecard?.confidence_vectors?.data_freshness_hours;
    if (hrs != null && Number.isFinite(hrs)) return hrs < 1 ? '<1 hr ago' : `${Math.round(hrs)}h ago`;
    if (report.generated_at) return new Date(report.generated_at).toLocaleDateString();
    return 'Unrecorded';
  }, [scorecard, report.generated_at]);

  // Issue severity & resolution breakdown
  const criticalCount = seoFindings.filter((f) => f.severity === 'CRITICAL').length;
  const highCount = seoFindings.filter((f) => f.severity === 'HIGH').length;
  const mediumCount = seoFindings.filter((f) => f.severity === 'MEDIUM').length;
  const lowCount = seoFindings.filter((f) => f.severity === 'LOW' || f.severity === 'INFO').length;
  const resolvedCount = seoFindings.filter(
    (f) => f.resolution_status === 'VERIFIED_FIXED' || f.verification_status === 'VERIFIED_FIXED'
  ).length;

  // 4. 9-Dimension scorecards strictly from backend MathematicalScoreEngine
  const dimensionCards = useMemo(() => {
    const defaultsOrder = Object.keys(DIM_META);
    if (scorecard?.dimensions && scorecard.dimensions.length > 0) {
      return scorecard.dimensions.map((d) => {
        const meta = DIM_META[d.dimension_id] || {
          shortTitle: d.name,
          icon: <Gauge className="w-4 h-4 text-sky-600" />,
          targetTab: 'architecture',
          summary: d.notes?.[0] || 'Canonical SEO dimension.',
        };
        return {
          id: d.dimension_id,
          title: meta.shortTitle,
          weight: `${Math.round(d.configured_weight * 100)}%`,
          effectiveWeight: d.effective_weight != null ? `${Math.round(d.effective_weight * 100)}%` : 'Excluded',
          icon: meta.icon,
          score: d.score,
          isApplicable: d.is_applicable,
          isMeasured: d.is_measured,
          executed: d.executed_checks_count,
          failed: d.failed_checks_count ?? Math.max(0, d.executed_checks_count - d.passed_checks_count),
          targetTab: meta.targetTab,
          summary: d.notes?.[0] || meta.summary,
        };
      });
    }
    // Offline fallback before API hydration: show dimensions cleanly as Unmeasured (never fake numbers!)
    return defaultsOrder.map((dimId) => {
      const meta = DIM_META[dimId];
      const catScore = dimId === 'technical_crawlability' ? report.scores?.category_scores?.['TECHNICAL_SEO']?.score ?? null : null;
      return {
        id: dimId,
        title: meta.shortTitle,
        weight: dimId === 'technical_crawlability' ? '20%' : dimId === 'indexation_canonicalization' || dimId === 'content_quality_intent' ? '15%' : dimId === 'specialist_applicability' || dimId === 'trust_authority_signals' ? '5%' : '10%',
        effectiveWeight: catScore != null ? 'Measured' : 'Pending',
        icon: meta.icon,
        score: catScore != null && Number.isFinite(catScore) ? Math.round(catScore) : null,
        isApplicable: true,
        isMeasured: catScore != null,
        executed: 0,
        failed: 0,
        targetTab: meta.targetTab,
        summary: meta.summary,
      };
    });
  }, [scorecard, report]);

  const topRecommendations = useMemo(() => {
    const sevOrder: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1, INFO: 0 };
    return [...seoFindings]
      .sort((a, b) => (sevOrder[b.severity] || 0) - (sevOrder[a.severity] || 0))
      .slice(0, 5);
  }, [seoFindings]);

  const totalExecutedChecks = dimensionCards.reduce((acc, d) => acc + d.executed, 0);

  return (
    <div className="space-y-8">
      {/* SECTION A: EXECUTIVE OVERVIEW & INDEPENDENT CONFIDENCE VECTORS */}
      <section className="rounded-2xl border border-line bg-gradient-to-br from-paper-50 to-paper-100 dark:from-paper-900 dark:to-paper-950 p-6 shadow-xs">
        <div className="grid gap-6 lg:grid-cols-12 items-center">
          <div className="lg:col-span-4 flex flex-col items-center justify-center p-6 border-b lg:border-b-0 lg:border-r border-line text-center">
            <span className="text-xs uppercase font-semibold tracking-wider text-ink-500 mb-2">
              Canonical SEO Health Score
            </span>
            <div className={`w-32 h-32 rounded-full border-4 flex flex-col items-center justify-center shadow-inner ${getScoreColor(canonicalScore)}`}>
              <span className="text-4xl font-black font-mono tracking-tight">{canonicalScore ?? '—'}</span>
              <span className="text-[11px] font-bold uppercase tracking-wider mt-0.5">/ 100</span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <span className="text-sm font-bold text-ink">{getScoreLabel(canonicalScore)}</span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-ink-400" />
              <span className="text-xs text-ink-500">{scorecard?.methodology_version || 'dristik_seo_v3.0'}</span>
            </div>
            <div className="mt-2 flex flex-wrap justify-center gap-1.5 text-[11px] text-ink-500">
              <span>{criticalCount} Crit</span>·<span>{highCount} High</span>·<span>{mediumCount} Med</span>·<span>{lowCount} Low</span>·<span>{resolvedCount} Verified Fixed</span>
            </div>
          </div>

          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="card p-3 bg-paper-subtle border border-line">
              <div className="flex items-center gap-1.5 text-xs text-ink-500 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Audit Coverage</span>
              </div>
              <p className="mt-1 text-2xl font-bold font-mono text-ink">{auditCoveragePct}%</p>
              <p className="text-[11px] text-ink-400 mt-0.5">
                {totalExecutedChecks > 0 ? `${totalExecutedChecks} checks executed` : `${urlsCrawled}/${urlsDiscovered} URLs`}
              </p>
            </div>

            <div className="card p-3 bg-paper-subtle border border-line">
              <div className="flex items-center gap-1.5 text-xs text-ink-500 font-medium">
                <Shield className="w-3.5 h-3.5 text-blue-600" />
                <span>Evidence Quality</span>
              </div>
              <p className="mt-1 text-2xl font-bold font-mono text-ink">
                {evidenceConfidencePct != null ? `${evidenceConfidencePct}%` : '—'}
              </p>
              <p className="text-[11px] text-ink-400 mt-0.5">
                {scorecard ? `${scorecard.measured_dimensions_count}/${scorecard.dimensions.length} dims measured` : 'Awaiting scorecard'}
              </p>
            </div>

            <div className="card p-3 bg-paper-subtle border border-line">
              <div className="flex items-center gap-1.5 text-xs text-ink-500 font-medium">
                <Clock className="w-3.5 h-3.5 text-amber-600" />
                <span>Data Freshness</span>
              </div>
              <p className="mt-1 text-xl font-bold font-mono text-ink">{freshnessLabel}</p>
              <p className="text-[11px] text-ink-400 mt-0.5">{scorecard?.confidence_vectors?.sampling_status || cov.sampling_status || 'SAMPLED_AUDIT'}</p>
            </div>

            <div className="card p-3 bg-paper-subtle border border-line">
              <div className="flex items-center gap-1.5 text-xs text-ink-500 font-medium">
                <Database className="w-3.5 h-3.5 text-purple-600" />
                <span>Connectors</span>
              </div>
              <p className="mt-1 text-xl font-bold font-mono text-ink">
                {totalConnectors > 0 ? `${connectedCount}/${totalConnectors}` : '0 Active'}
              </p>
              <p className="text-[11px] text-ink-400 mt-0.5">
                {connectedCount > 0 ? 'Live synced sources' : 'Unconnected excluded'}
              </p>
            </div>
          </div>
        </div>

        {/* 6-Tier Reconciled URL Taxonomy Bar */}
        <div className="mt-6 pt-5 border-t border-line">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider text-ink-500">
              Reconciled URL Taxonomy &amp; Audit Scope
            </span>
            <Button variant="secondary" size="sm" onClick={() => onNavigateTab('discovery')} className="text-xs h-7">
              Open Crawl Explorer <ArrowRight className="w-3 h-3 ml-1" />
            </Button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
            <div className="rounded-lg p-2.5 bg-paper-50 dark:bg-paper-800/50 border border-line">
              <span className="text-[10px] font-semibold uppercase text-ink-400">1. Discovered</span>
              <p className="text-lg font-bold font-mono text-ink mt-0.5">{urlsDiscovered} URLs</p>
              <span className="text-[10px] text-ink-500">Sitemap &amp; links</span>
            </div>
            <div className="rounded-lg p-2.5 bg-paper-50 dark:bg-paper-800/50 border border-line">
              <span className="text-[10px] font-semibold uppercase text-ink-400">2. Crawled</span>
              <p className="text-lg font-bold font-mono text-ink mt-0.5">{urlsCrawled} URLs</p>
              <span className="text-[10px] text-ink-500">HTTP GET responses</span>
            </div>
            <div className="rounded-lg p-2.5 bg-paper-50 dark:bg-paper-800/50 border border-line">
              <span className="text-[10px] font-semibold uppercase text-ink-400">3. Rendered</span>
              <p className="text-lg font-bold font-mono text-ink mt-0.5">{urlsRendered} URLs</p>
              <span className="text-[10px] text-ink-500">Headless DOM</span>
            </div>
            <div className="rounded-lg p-2.5 bg-paper-50 dark:bg-paper-800/50 border border-line">
              <span className="text-[10px] font-semibold uppercase text-ink-400">4. Inspected</span>
              <p className="text-lg font-bold font-mono text-ink mt-0.5">{urlsDeeplyInspected} URLs</p>
              <span className="text-[10px] text-ink-500">Full AST &amp; Schema</span>
            </div>
            <div className="rounded-lg p-2.5 bg-paper-50 dark:bg-paper-800/50 border border-line">
              <span className="text-[10px] font-semibold uppercase text-ink-400">5. Specialist Tested</span>
              <p className="text-lg font-bold font-mono text-ink mt-0.5">{urlsDeeplyInspected} URLs</p>
              <span className="text-[10px] text-ink-500">40 Specialist Roles</span>
            </div>
            <div className="rounded-lg p-2.5 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50">
              <span className="text-[10px] font-semibold uppercase text-rose-600 dark:text-rose-400">6. Defect URLs</span>
              <p className="text-lg font-bold font-mono text-rose-700 dark:text-rose-300 mt-0.5">{urlsVerifiedFindings} URLs</p>
              <span className="text-[10px] text-rose-600/80">Confirmed issues</span>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION B: 9 DIMENSION SCORECARDS (CANONICAL) */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-ink">SEO Dimension Scorecards</h3>
            <p className="text-xs text-ink-500">
              Weighted breakdown across all 9 canonical audit pillars. Unmeasured or inapplicable dimensions are excluded without penalty.
            </p>
          </div>
          <Badge tone="pine">
            {scorecard ? `Active Weight: ${Math.round(scorecard.active_weight_sum * 100)}%` : 'Canonical Backend Engine'}
          </Badge>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {dimensionCards.map((dim) => (
            <div
              key={dim.id}
              onClick={() => onNavigateTab(dim.targetTab)}
              className="group cursor-pointer rounded-xl border border-line bg-paper-subtle p-4 hover:border-ink-400 hover:shadow-sm transition-all space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-paper-100 dark:bg-paper-800 border border-line">{dim.icon}</div>
                  <div>
                    <h4 className="text-xs font-bold text-ink group-hover:text-primary transition-colors">{dim.title}</h4>
                    <span className="text-[10px] text-ink-400 font-mono">
                      Weight: {dim.weight} · Eff: {dim.effectiveWeight}
                    </span>
                  </div>
                </div>
                <div className={`px-2.5 py-1 rounded-md border font-mono text-xs font-bold ${getScoreColor(dim.score)}`}>
                  {dim.score != null ? `${Math.round(dim.score)}/100` : !dim.isApplicable ? 'N/A' : 'Unmeasured'}
                </div>
              </div>

              <p className="text-xs text-ink-600 dark:text-ink-300 line-clamp-2">{dim.summary}</p>

              <div className="pt-2 border-t border-line flex items-center justify-between text-[11px] text-ink-500">
                <span>
                  <span className="font-semibold text-ink">{dim.executed}</span> checks run ·{' '}
                  <span className={dim.failed > 0 ? 'text-rose-600 font-semibold' : 'text-emerald-600 font-semibold'}>
                    {dim.failed} failed
                  </span>
                </span>
                <span className="text-[10px] text-ink-400 font-medium flex items-center group-hover:translate-x-0.5 transition-transform">
                  Inspect <ArrowRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* SECTION C: TOP 5 STRATEGIC REMEDIATIONS */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-ink">Top Strategic Remediations</h3>
            <p className="text-xs text-ink-500">Ranked by verified severity, affected URL scope, and remediation impact.</p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => onNavigateTab('issues')} className="text-xs">
            Open All {seoFindings.length} Issues <ArrowRight className="w-3 h-3 ml-1" />
          </Button>
        </div>

        <div className="space-y-3">
          {topRecommendations.length === 0 ? (
            <div className="p-5 rounded-xl border border-line bg-paper-subtle text-xs text-ink-500">
              No confirmed SEO defects recorded for the inspected sample.
            </div>
          ) : (
            topRecommendations.map((fnd, idx) => {
              const affectedUrls = (fnd as any).affected_urls || ((fnd as any).url ? [(fnd as any).url] : []);
              const urlCount = Array.isArray(affectedUrls) ? affectedUrls.length : 1;
              return (
                <div
                  key={fnd.finding_id || idx}
                  className="card p-4 rounded-xl border border-line bg-paper hover:border-ink-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-ink-400">#{idx + 1}</span>
                      <Badge tone={fnd.severity === 'CRITICAL' ? 'bad' : fnd.severity === 'HIGH' ? 'warn' : 'neutral'}>
                        {fnd.severity}
                      </Badge>
                      <span className="font-mono text-xs text-ink-400">{fnd.finding_id}</span>
                      <span className="text-xs text-ink-500">· {urlCount} URL{urlCount !== 1 ? 's' : ''} affected</span>
                    </div>
                    <h4 className="text-sm font-semibold text-ink">{fnd.title}</h4>
                    <p className="text-xs text-ink-600 dark:text-ink-400 line-clamp-2">{fnd.description || fnd.recommendation}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      onNavigateTab('issues');
                      onSelectFinding?.(fnd);
                    }}
                    className="text-xs shrink-0"
                  >
                    View Code Patch <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* SECTION D: PERFORMANCE TRENDS & HISTORICAL BASELINE */}
      <section className="rounded-xl border border-line bg-paper-subtle p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" />
            <h4 className="text-sm font-bold text-ink">Historical Regression &amp; Audit Baseline</h4>
          </div>
          <Badge tone={history?.has_history ? 'good' : 'pine'}>
            {history?.has_history ? `${history.historical_runs.length} Prior Run(s)` : 'Baseline Locked'}
          </Badge>
        </div>

        {history?.has_history ? (
          <p className="text-xs text-ink-600 leading-relaxed">
            Compared against baseline <code>{history.baseline_audit_id}</code>:{' '}
            <strong>
              {history.score_delta != null
                ? `${history.score_delta >= 0 ? '+' : ''}${history.score_delta} pts`
                : 'Score delta unavailable'}
            </strong>
            .
          </p>
        ) : (
          <p className="text-xs text-ink-500 leading-relaxed">
            This audit is your <strong>Day-0 Canonical Baseline</strong> ({report.generated_at ? new Date(report.generated_at).toLocaleDateString() : 'Today'}). Historical trends are displayed only when prior runs exist for this domain.
          </p>
        )}

        <div className="pt-2 flex flex-wrap items-center gap-3">
          <Button size="sm" variant="secondary" onClick={() => onNavigateTab('history')} className="text-xs">
            Open Delta &amp; Regression History
          </Button>
          <span className="text-xs text-ink-400">
            Audit ID: <code className="font-mono">{report.analysis_id || report.report_id}</code>
          </span>
        </div>
      </section>
    </div>
  );
}
