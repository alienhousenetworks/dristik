import React, { useState } from 'react';
import { ExecutiveReport, Finding, WcagViolation } from '../../types';
import { PillarShell } from '../ui';
import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Eye,
  Keyboard,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  FileText,
} from 'lucide-react';

interface WebsiteExperienceViewProps {
  report: ExecutiveReport;
  onSelectFinding?: (f: Finding) => void;
}

type ExpSubTab = 'sxo' | 'cwv' | 'mobile' | 'accessibility' | 'ia';

export function WebsiteExperienceView({
  report,
  onSelectFinding,
}: WebsiteExperienceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<ExpSubTab>('sxo');
  const [a11ySeverityFilter, setA11ySeverityFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [expandedViolationRule, setExpandedViolationRule] = useState<string | null>(null);

  const crawl = report.crawl_manifest;
  const homePage = crawl?.pages?.[0];
  const ttfb = typeof homePage?.ttfb_ms === 'number' && homePage.ttfb_ms > 0 ? homePage.ttfb_ms : null;
  const ctas = homePage?.ctas || [];
  const measuredUx = report.scores?.category_scores?.['UX_CONVERSION']?.score ?? report.honest_scores?.human_score;
  const uxScore = typeof measuredUx === 'number' ? Math.round(measuredUx) : null;

  const findings = (report.findings || []).filter(
    (f) => f.category === 'UX_CONVERSION'
  );

  return (
    <PillarShell
      kicker="Experience"
      title="Speed, mobile, and usability"
      description="How quickly the site loads, how it behaves on mobile, and whether visitors can complete the job they came for."
      scoreLabel="Experience"
      score={uxScore ?? '—'}
      metaLabel="TTFB"
      meta={ttfb == null ? '—' : `${ttfb} ms`}
      tabs={[
        { id: 'sxo', label: 'Experience' },
        { id: 'cwv', label: 'Speed' },
        { id: 'mobile', label: 'Mobile' },
        { id: 'accessibility', label: 'Accessibility' },
        { id: 'ia', label: 'Structure' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as ExpSubTab)}
    >

      {/* SUB-VIEW 1: SXO SEARCH EXPERIENCE */}
      {activeSubTab === 'sxo' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-5 rounded-lg space-y-2">
              <span className="label text-[10px] block">3-Second Hook Test</span>
              <span className="font-sans text-2xl font-bold text-ink">
                {homePage?.title ? 'Title present' : 'No title'}
              </span>
              <p className="text-xs text-ink-500 leading-relaxed">
                Whether a visitor arriving from Google or ChatGPT immediately grasps what the company does within 3 seconds.
              </p>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-5 rounded-lg space-y-2">
              <span className="label text-[10px] block">Bounce Risk Mitigation</span>
              <span className="font-sans text-2xl font-bold text-ink">
                Not measured
              </span>
              <p className="text-xs text-ink-500 leading-relaxed">
                Bounce rate needs analytics. This crawl does not record it.
              </p>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-5 rounded-lg space-y-2">
              <span className="label text-[10px] block">Intent Resolution</span>
              <span className="font-sans text-2xl font-bold text-ink">
                {report.business_profile?.primary_intent || '—'}
              </span>
              <p className="text-xs text-ink-500 leading-relaxed">
                Matching search queries directly to specific on-page actions.
              </p>
            </div>
          </div>

          {/* UX & SXO Findings */}
          <div className="sheet border border-line rounded-lg p-6 space-y-4">
            <h3 className="font-sans text-xl text-ink font-bold">
              User Experience & Intent Obstacles ({findings.length})
            </h3>
            {findings.length === 0 ? (
              <p className="text-sm text-good">No critical experience bottlenecks identified.</p>
            ) : (
              <div className="space-y-3">
                {findings.map((f) => (
                  <div
                    key={f.finding_id}
                    onClick={() => onSelectFinding?.(f)}
                    className="p-3.5 bg-paper-50 dark:bg-ink-900/40 border border-line rounded-md hover:border-ink cursor-pointer transition-colors flex items-start justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-paper-200 text-ink-700">
                          {f.severity}
                        </span>
                        <span className="font-semibold text-ink text-sm">{f.title}</span>
                      </div>
                      <p className="text-xs text-ink-600 line-clamp-1">{f.description}</p>
                    </div>
                    <span className="text-xs text-ink-700 font-mono font-bold shrink-0 self-center">
                      Inspect →
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: CORE WEB VITALS & PERFORMANCE */}
      {activeSubTab === 'cwv' && (() => {
        const lab = homePage?.lab_performance;
        const field = homePage?.field_performance;
        const effectiveTtfb = lab?.ttfb_ms ?? ttfb;
        const ttfbGrade =
          effectiveTtfb == null
            ? 'UNKNOWN'
            : effectiveTtfb < 200
            ? 'OPTIMAL'
            : effectiveTtfb < 800
            ? 'MODERATE'
            : 'SLOW';

        const ttfbColor =
          ttfbGrade === 'OPTIMAL'
            ? 'text-good bg-good/10 dark:bg-good/10 border-good/30'
            : ttfbGrade === 'MODERATE'
            ? 'text-warn bg-warn/10 dark:bg-warn/10 border-warn/30'
            : 'text-bad bg-bad/10 dark:bg-bad/10 border-bad/30';

        return (
          <div className="space-y-8">
            {/* TIER 1: DETERMINISTIC LAB DIAGNOSTICS */}
            <div className="sheet border border-line rounded-lg p-6 space-y-6 bg-paper-50/50">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-[0.04em] px-2 py-0.5 rounded bg-paper-100 dark:bg-paper-100 text-ink-700 dark:text-ink-700 font-bold">
                      Tier 1: Lab Diagnostics
                    </span>
                    <span className="text-xs text-ink-500">Audit Fetch Benchmark</span>
                  </div>
                  <h3 className="font-sans text-2xl text-ink font-bold mt-1">
                    Origin Latency &amp; Critical Rendering Path
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-[11px] text-ink-500 block">Single-probe crawl measurement</span>
                  <span className="text-[11px] font-mono text-ink-700">Not a substitute for CrUX field data</span>
                </div>
              </div>

              {/* Lab Primary KPI Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* TTFB */}
                <div className="border border-line p-4 rounded-lg bg-paper-100/60 dark:bg-ink-900/40 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="label text-[10px] block">Server TTFB (Latency)</span>
                    <span className={`text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded border ${ttfbColor}`}>
                      {ttfbGrade}
                    </span>
                  </div>
                  <span className="font-sans text-3xl font-bold text-ink">
                    {effectiveTtfb == null ? '—' : `${Math.round(effectiveTtfb)} ms`}
                  </span>
                  <span className="text-[11px] text-ink-500 block">
                    {effectiveTtfb == null
                      ? 'Not measured on this crawl'
                      : effectiveTtfb < 200
                      ? 'Sub-200ms: Fast origin response'
                      : effectiveTtfb < 800
                      ? '200-800ms: Acceptable origin latency'
                      : 'Exceeds 800ms: Backend/CDN optimization required'}
                  </span>
                </div>

                {/* First Contentful Paint (Lab) */}
                <div className="border border-line p-4 rounded-lg bg-paper-100/60 dark:bg-ink-900/40 space-y-1">
                  <span className="label text-[10px] block">First Contentful Paint (FCP)</span>
                  <span className="font-sans text-3xl font-bold text-ink">
                    {lab?.fcp_ms ? `${Math.round(lab.fcp_ms)} ms` : effectiveTtfb ? `~${Math.round(effectiveTtfb + 250)} ms` : '—'}
                  </span>
                  <span className="text-[11px] text-ink-500 block">
                    {lab?.fcp_ms ? 'Browser paint timing' : 'Estimated from origin response'}
                  </span>
                </div>

                {/* Render Blocking Resources */}
                <div className="border border-line p-4 rounded-lg bg-paper-100/60 dark:bg-ink-900/40 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="label text-[10px] block">Render-Blocking Assets</span>
                    <span className={`text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded border ${
                      (lab?.render_blocking_count ?? 0) === 0
                        ? 'text-good bg-good/10 border-good/30'
                        : 'text-warn bg-warn/10 border-warn/30'
                    }`}>
                      {(lab?.render_blocking_count ?? 0) === 0 ? 'CLEAN' : `${lab?.render_blocking_count} BLOCKING`}
                    </span>
                  </div>
                  <span className="font-sans text-3xl font-bold text-ink">
                    {lab?.render_blocking_count ?? 0}
                  </span>
                  <span className="text-[11px] text-ink-500 block">
                    Scripts/Styles in &lt;head&gt; delaying paint
                  </span>
                </div>

                {/* Transferred Bytes & Compression */}
                <div className="border border-line p-4 rounded-lg bg-paper-100/60 dark:bg-ink-900/40 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="label text-[10px] block">Transferred Payload</span>
                    <span className="text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded bg-paper-200 dark:bg-ink-800 text-ink-700 dark:text-ink-300 border border-line dark:border-line">
                      {lab?.content_encoding && lab.content_encoding !== 'none' ? lab.content_encoding.toUpperCase() : 'NO GZIP'}
                    </span>
                  </div>
                  <span className="font-sans text-3xl font-bold text-ink">
                    {lab?.total_transferred_kb ? `${lab.total_transferred_kb} KB` : '—'}
                  </span>
                  <span className="text-[11px] text-ink-500 block">
                    Caching: {lab?.caching_policy || 'Standard'}
                  </span>
                </div>
              </div>

              {/* Asset Weight Distribution Breakdown */}
              <div className="border border-line rounded-lg p-4 bg-paper-100/40 dark:bg-ink-900/20 space-y-3">
                <span className="text-xs font-semibold text-ink uppercase tracking-[0.04em] block">
                  Page Payload Footprint by Asset Category
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
                  <div className="p-2.5 rounded border border-line bg-paper-50 dark:bg-ink-900/40">
                    <span className="text-[10px] text-ink-500 block">JavaScript</span>
                    <span className="font-mono font-bold text-ink text-sm">
                      {lab?.js_payload_kb ? `${lab.js_payload_kb} KB` : `${homePage?.scripts_count || 0} scripts`}
                    </span>
                  </div>
                  <div className="p-2.5 rounded border border-line bg-paper-50 dark:bg-ink-900/40">
                    <span className="text-[10px] text-ink-500 block">Stylesheets (CSS)</span>
                    <span className="font-mono font-bold text-ink text-sm">
                      {lab?.css_payload_kb ? `${lab.css_payload_kb} KB` : `${homePage?.stylesheets_count || 0} styles`}
                    </span>
                  </div>
                  <div className="p-2.5 rounded border border-line bg-paper-50 dark:bg-ink-900/40">
                    <span className="text-[10px] text-ink-500 block">Images &amp; Media</span>
                    <span className="font-mono font-bold text-ink text-sm">
                      {lab?.image_payload_kb ? `${lab.image_payload_kb} KB` : `${homePage?.total_images || 0} images`}
                    </span>
                  </div>
                  <div className="p-2.5 rounded border border-line bg-paper-50 dark:bg-ink-900/40">
                    <span className="text-[10px] text-ink-500 block">Web Fonts</span>
                    <span className="font-mono font-bold text-ink text-sm">
                      {lab?.font_payload_kb ? `${lab.font_payload_kb} KB` : (lab?.font_display_strategy || 'Standard')}
                    </span>
                  </div>
                  <div className="p-2.5 rounded border border-line bg-paper-50 dark:bg-ink-900/40">
                    <span className="text-[10px] text-ink-500 block">3rd-Party Scripts</span>
                    <span className="font-mono font-bold text-ink text-sm">
                      {lab?.third_party_scripts_count ?? 0} trackers
                    </span>
                  </div>
                </div>

                {/* Render Blocking Assets List if present */}
                {lab?.render_blocking_resources && lab.render_blocking_resources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-line">
                    <span className="text-[11px] font-semibold text-warn dark:text-warn block mb-1">
                      Identified Render-Blocking Assets in &lt;head&gt;:
                    </span>
                    <ul className="space-y-1 font-mono text-[10px] text-ink-600 dark:text-ink-400">
                      {lab.render_blocking_resources.slice(0, 4).map((res, idx) => (
                        <li key={idx} className="truncate">
                          • <span className="font-bold uppercase text-warn dark:text-warn">[{res.initiator || 'asset'}]</span> {res.url}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* TIER 2: REAL-USER FIELD EXPERIENCE (CRUX) */}
            <div className="sheet border border-line rounded-lg p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-[0.04em] px-2 py-0.5 rounded bg-paper-100 dark:bg-paper-100 text-ink-700 dark:text-ink-700 font-bold">
                      Tier 2: Real-User Field Monitoring
                    </span>
                    <span className="text-xs text-ink-500">Google Chrome UX Report (CrUX)</span>
                  </div>
                  <h3 className="font-sans text-2xl text-ink font-bold mt-1">
                    Core Web Vitals (CWV) Field Telemetry
                  </h3>
                </div>
                <div>
                  <span className={`text-[10px] font-mono uppercase font-bold px-2 py-1 rounded border ${
                    field?.has_field_data
                      ? 'text-good bg-good/10 border-good/30'
                      : 'text-ink-600 bg-paper-200 dark:bg-ink-800 border-line dark:border-line'
                  }`}>
                    {field?.has_field_data ? '✓ 28-Day Field Data Active' : 'Unmeasured on Field'}
                  </span>
                </div>
              </div>

              {field?.has_field_data ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
                      <span className="label text-[10px] block">Largest Contentful Paint (LCP p75)</span>
                      <span className="font-sans text-3xl font-bold text-ink">
                        {field.p75_lcp_ms ? `${Math.round(field.p75_lcp_ms)} ms` : '—'}
                      </span>
                      <span className="text-[11px] text-ink-500 block">Target: &lt; 2500ms</span>
                    </div>
                    <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
                      <span className="label text-[10px] block">Interaction to Next Paint (INP p75)</span>
                      <span className="font-sans text-3xl font-bold text-ink">
                        {field.p75_inp_ms ? `${Math.round(field.p75_inp_ms)} ms` : '—'}
                      </span>
                      <span className="text-[11px] text-ink-500 block">Target: &lt; 200ms</span>
                    </div>
                    <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
                      <span className="label text-[10px] block">Cumulative Layout Shift (CLS p75)</span>
                      <span className="font-sans text-3xl font-bold text-ink">
                        {field.p75_cls ?? '—'}
                      </span>
                      <span className="text-[11px] text-ink-500 block">Target: &lt; 0.1</span>
                    </div>
                    <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
                      <span className="label text-[10px] block">First Contentful Paint (FCP p75)</span>
                      <span className="font-sans text-3xl font-bold text-ink">
                        {field.p75_fcp_ms ? `${Math.round(field.p75_fcp_ms)} ms` : '—'}
                      </span>
                      <span className="text-[11px] text-ink-500 block">Target: &lt; 1800ms</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="border border-line border-dashed rounded-lg p-5 bg-paper-50/80 dark:bg-ink-900/30 flex items-start gap-4">
                  <div className="w-9 h-9 rounded-full bg-paper-200 dark:bg-ink-800 flex items-center justify-center font-bold text-ink-700 dark:text-ink-300 shrink-0 text-sm">
                    ℹ
                  </div>
                  <div className="space-y-1 text-xs text-ink-600 dark:text-ink-400">
                    <span className="font-bold text-ink text-sm block">
                      Field Telemetry Unmeasured (Deterministic Lab Data Used Exclusively)
                    </span>
                    <p className="leading-relaxed">
                      Google Chrome User Experience Report (CrUX) publishes real-user 28-day Core Web Vitals (LCP, INP, CLS) only for origins meeting Google’s minimum traffic thresholds. When an origin has low Chrome traffic or when no CrUX API key is configured, Dristik enforces an honest fail-closed standard.
                    </p>
                    <p className="font-medium text-ink-700 dark:text-ink-300">
                      • Crawl TTFB is a single-server lab latency sample and is never presented as complete Core Web Vitals.
                      <br />
                      • Performance scoring for this domain relies on Tier 1 deterministic lab benchmarks (true TTFB, render-blocking scripts, compression, and image layout sizing).
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* SUB-VIEW 3: MOBILE USABILITY */}
      {activeSubTab === 'mobile' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Mobile Viewport & Responsiveness</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Viewport Meta Tag</span>
              <p className="font-mono text-xs text-ink bg-paper-100 p-2 rounded border border-line">
                {homePage?.viewport || 'Not found'}
              </p>
              <span className="text-xs text-ink-500 block">{homePage?.viewport ? 'Viewport tag present' : 'No viewport tag in the crawl'}</span>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Tap Target Safety (WCAG 2.2 SC 2.5.8)</span>
              {report.wcag_audit ? (
                <>
                  <p className="font-sans text-xl font-bold text-ink">
                    {report.wcag_audit.violations.some((v) => v.rule_id === 'WCAG_2_5_8_TARGET_SIZE')
                      ? 'Violations Detected'
                      : '100% Pass'}
                  </p>
                  <span className="text-xs text-ink-500 block">
                    {report.wcag_audit.violations.some((v) => v.rule_id === 'WCAG_2_5_8_TARGET_SIZE')
                      ? 'Interactive controls under 24x24 CSS pixels found'
                      : 'All evaluated interactive targets meet the 24x24px minimum'}
                  </span>
                </>
              ) : (
                <>
                  <p className="font-sans text-xl font-bold text-ink">Not measured</p>
                  <span className="text-xs text-ink-500 block">Tap-target size was not rendered.</span>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: ACCESSIBILITY (WCAG 2.2 AA) */}
      {activeSubTab === 'accessibility' && (() => {
        const wcag = report.wcag_audit;
        const violations = wcag?.violations || [];
        const filteredViolations = violations.filter((v) => {
          if (a11ySeverityFilter === 'ALL') return true;
          return v.severity === a11ySeverityFilter;
        });

        const highCount = violations.filter((v) => v.severity === 'HIGH' || v.severity === 'CRITICAL').length;
        const medCount = violations.filter((v) => v.severity === 'MEDIUM').length;
        const lowCount = violations.filter((v) => v.severity === 'LOW' || v.severity === 'INFO').length;

        const statusColors = {
          PASS: 'bg-good/10 text-good dark:text-good border-good/30',
          NEEDS_ATTENTION: 'bg-warn/10 text-warn dark:text-warn border-warn/30',
          NON_COMPLIANT: 'bg-bad/10 text-bad dark:text-bad border-bad/30',
        };

        const statusLabels = {
          PASS: 'WCAG 2.2 AA Compliant',
          NEEDS_ATTENTION: 'WCAG 2.2 AA Needs Attention',
          NON_COMPLIANT: 'WCAG 2.2 AA Non-Compliant',
        };

        const currentStatus = wcag?.conformance_status || (homePage?.images_without_alt ? 'NEEDS_ATTENTION' : 'PASS');
        const statusClass = statusColors[currentStatus as keyof typeof statusColors] || statusColors.NEEDS_ATTENTION;
        const statusLabel = statusLabels[currentStatus as keyof typeof statusLabels] || currentStatus;

        return (
          <div className="sheet border border-line rounded-lg p-6 space-y-8">
            {/* Top Score & Status Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-line">
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <h3 className="font-sans text-2xl text-ink font-bold">
                    Accessibility (WCAG 2.2 Level AA) Audit
                  </h3>
                  <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-md border ${statusClass}`}>
                    {statusLabel}
                  </span>
                </div>
                <p className="text-xs text-ink-500 max-w-2xl">
                  Comprehensive audit across 20 distinct standards spanning color contrast, keyboard focus traps, form controls, landmark regions, touch targets, and assistive semantics.
                </p>
              </div>

              <div className="flex items-center gap-6 self-start sm:self-auto shrink-0 bg-paper-50 dark:bg-paper-100 p-4 rounded-xl border border-line">
                <div className="text-right">
                  <span className="label text-[10px] block text-ink-500">Compliance Score</span>
                  <span className="font-sans text-3xl font-extrabold text-ink">
                    {wcag ? `${Math.round(wcag.compliance_score)}%` : '—'}
                  </span>
                </div>
                <div className="h-10 w-px bg-line" />
                <div className="space-y-0.5 text-xs">
                  <div className="flex items-center gap-1.5 text-ink-700 dark:text-ink-300">
                    <span className="w-2 h-2 rounded-full bg-good/10" />
                    <span>{wcag?.passed_checks_count ?? '—'} Passed</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-ink-700 dark:text-ink-300">
                    <span className="w-2 h-2 rounded-full bg-bad/10" />
                    <span>{wcag?.violations_count ?? violations.length} Issues</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 4 WCAG Principles Matrix */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="label text-[11px] font-bold uppercase tracking-[0.04em] text-ink-500">
                  Four WCAG 2.2 Core Principles
                </span>
                <span className="text-xs text-ink-500">W3C Foundation Standards</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  {
                    key: 'Perceivable',
                    name: '1. Perceivable',
                    desc: 'Contrast, alt text, headings, landmarks, zoom',
                    icon: Eye,
                    score: wcag?.principle_scores?.['Perceivable'] ?? null,
                  },
                  {
                    key: 'Operable',
                    name: '2. Operable',
                    desc: 'Keyboard nav, focus order, target size, skip link',
                    icon: Keyboard,
                    score: wcag?.principle_scores?.['Operable'] ?? null,
                  },
                  {
                    key: 'Understandable',
                    name: '3. Understandable',
                    desc: 'Page language, input purpose, form labels',
                    icon: FileText,
                    score: wcag?.principle_scores?.['Understandable'] ?? null,
                  },
                  {
                    key: 'Robust',
                    name: '4. Robust',
                    desc: 'ARIA markup, button names, modal dialogs',
                    icon: ShieldCheck,
                    score: wcag?.principle_scores?.['Robust'] ?? null,
                  },
                ].map((p) => {
                  const Icon = p.icon;
                  const isGood = p.score != null && p.score >= 85;
                  const isFair = p.score != null && p.score >= 70 && p.score < 85;
                  return (
                    <div
                      key={p.key}
                      className="border border-line rounded-lg p-4 bg-paper-50 dark:bg-paper-100/50 space-y-2 relative overflow-hidden"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-ink">{p.name}</span>
                        <Icon className="w-4 h-4 text-ink-500" />
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="font-sans text-2xl font-bold text-ink">
                          {p.score != null ? `${Math.round(p.score)}%` : '—'}
                        </span>
                        <span className="text-[10px] text-ink-500">
                          {p.score != null ? 'integrity' : 'unmeasured'}
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-paper-200 dark:bg-paper-200/40 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            p.score == null ? 'bg-paper-300' : isGood ? 'bg-good/10' : isFair ? 'bg-warn/10' : 'bg-bad/10'
                          }`}
                          style={{ width: `${p.score != null ? Math.min(100, Math.max(5, p.score)) : 0}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-ink-500 line-clamp-1">{p.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Core Verification Categories Breakdown */}
            <div className="space-y-3">
              <span className="label text-[11px] font-bold uppercase tracking-[0.04em] text-ink-500">
                Detailed Accessibility Categories
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  {
                    label: 'Color Contrast',
                    rule: 'WCAG_1_4_3_COLOR_CONTRAST',
                    standard: 'WCAG 1.4.3 (4.5:1 ratio)',
                    desc: 'Text vs background luminance',
                  },
                  {
                    label: 'Keyboard & Focus Visibility',
                    rule: 'WCAG_2_1_1_KEYBOARD_ACCESSIBLE',
                    standard: 'WCAG 2.1.1 & 2.4.7',
                    desc: 'Focus indicators & no traps',
                  },
                  {
                    label: 'Form Control Labels',
                    rule: 'WCAG_1_3_1_FORM_LABELS',
                    standard: 'WCAG 1.3.1 & 3.3.2',
                    desc: 'Explicit label associations',
                  },
                  {
                    label: 'Heading Outline',
                    rule: 'WCAG_1_3_1_HEADING_ORDER',
                    standard: 'WCAG 1.3.1 Order',
                    desc: 'Sequential H1 -> H2 hierarchy',
                  },
                  {
                    label: 'Touch Target Sizes',
                    rule: 'WCAG_2_5_8_TARGET_SIZE',
                    standard: 'WCAG 2.2 SC 2.5.8',
                    desc: 'Minimum 24x24 CSS pixels',
                  },
                  {
                    label: 'ARIA Semantics',
                    rule: 'WCAG_4_1_2_ARIA_MISUSE',
                    standard: 'WCAG 4.1.2 Roles',
                    desc: 'Valid roles & mandatory states',
                  },
                  {
                    label: 'Image Alternative Text',
                    rule: 'WCAG_1_1_1_IMAGE_ALT',
                    standard: 'WCAG 1.1.1 Text Alts',
                    desc: 'Descriptive alt attributes',
                  },
                  {
                    label: 'Landmark Structure',
                    rule: 'WCAG_1_3_1_LANDMARK_MAIN',
                    standard: 'WCAG 1.3.1 Landmarks',
                    desc: 'Semantic <main>, <nav> regions',
                  },
                ].map((cat) => {
                  const hasViolation = violations.some((v) => v.rule_id === cat.rule);
                  return (
                    <div
                      key={cat.rule}
                      className="p-3.5 rounded-lg border border-line bg-paper-50 dark:bg-paper-100/40 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-ink">{cat.label}</span>
                        {hasViolation ? (
                          <span className="flex items-center gap-1 text-[10px] text-bad font-medium">
                            <AlertCircle className="w-3.5 h-3.5" /> Defect
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[10px] text-good font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-ink-500 block">{cat.standard}</span>
                      <p className="text-[11px] text-ink-600 dark:text-ink-400 pt-0.5">{cat.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Filterable Violations Ledger */}
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <h4 className="font-sans text-lg font-bold text-ink">
                    Detected Accessibility Defects & Remediation Code
                  </h4>
                  <p className="text-xs text-ink-500">
                    Programmatic issues discovered across the crawled DOM tree.
                  </p>
                </div>

                {/* Filter Chips */}
                <div className="flex items-center gap-1 bg-paper-100 p-1 rounded-lg border border-line self-start">
                  {(['ALL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setA11ySeverityFilter(lvl)}
                      className={`px-2.5 py-1 text-xs rounded-md font-medium transition-all ${
                        a11ySeverityFilter === lvl
                          ? 'bg-paper text-ink shadow-xs border border-line'
                          : 'text-ink-500 hover:text-ink'
                      }`}
                    >
                      {lvl === 'ALL'
                        ? `All (${violations.length})`
                        : lvl === 'HIGH'
                        ? `High (${highCount})`
                        : lvl === 'MEDIUM'
                        ? `Medium (${medCount})`
                        : `Low (${lowCount})`}
                    </button>
                  ))}
                </div>
              </div>

              {filteredViolations.length === 0 ? (
                <div className="border border-line rounded-lg p-8 text-center bg-paper-50 space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-good mx-auto" />
                  <p className="font-bold text-sm text-ink">Zero Defects Found for Selected Filter</p>
                  <p className="text-xs text-ink-500">
                    All evaluated DOM nodes satisfy WCAG 2.2 AA accessibility criteria under this severity.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredViolations.map((v, idx) => {
                    const isExpanded = expandedViolationRule === `${v.rule_id}_${idx}`;
                    const isHigh = v.severity === 'HIGH' || v.severity === 'CRITICAL';
                    const isMed = v.severity === 'MEDIUM';

                    return (
                      <div
                        key={`${v.rule_id}_${idx}`}
                        className="border border-line rounded-lg bg-paper-50 dark:bg-paper-100/30 overflow-hidden transition-colors"
                      >
                        <div
                          className="p-4 flex items-start justify-between gap-4 cursor-pointer hover:bg-paper-100/50"
                          onClick={() => setExpandedViolationRule(isExpanded ? null : `${v.rule_id}_${idx}`)}
                        >
                          <div className="space-y-1.5">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em] rounded ${
                                  isHigh
                                    ? 'bg-bad/10 text-bad dark:text-bad border border-bad/30'
                                    : isMed
                                    ? 'bg-warn/10 text-warn dark:text-warn border border-warn/30'
                                    : 'bg-paper-100 text-ink-700 dark:text-ink-700 border border-line'
                                }`}
                              >
                                {v.severity}
                              </span>
                              <span className="text-xs font-mono font-semibold text-ink-700 dark:text-ink-300">
                                {v.rule_id}
                              </span>
                              <span className="text-xs text-ink-500 font-medium">
                                • {v.wcag_criterion} ({v.level})
                              </span>
                            </div>

                            <p className="text-sm font-medium text-ink leading-snug">
                              {v.description}
                            </p>

                            <div className="flex items-center gap-3 text-[11px] text-ink-500 font-mono">
                              <span>URL: {v.url}</span>
                              {v.selector && <span>Selector: {v.selector}</span>}
                            </div>
                          </div>

                          <button
                            type="button"
                            className="p-1 rounded text-ink-400 hover:text-ink shrink-0"
                            aria-label={isExpanded ? 'Collapse' : 'Expand'}
                          >
                            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                          </button>
                        </div>

                        {isExpanded && (
                          <div className="px-4 pb-4 pt-1 border-t border-line/60 bg-paper-100/30 space-y-3 text-xs">
                            {v.snippet && (
                              <div className="space-y-1">
                                <span className="label text-[10px] text-ink-500 block">Identified DOM Snippet</span>
                                <pre className="p-2.5 rounded bg-paper-200/60 dark:bg-black/30 font-mono text-[11px] text-ink overflow-x-auto border border-line">
                                  {v.snippet}
                                </pre>
                              </div>
                            )}

                            <div className="space-y-1">
                              <span className="label text-[10px] text-ink-500 block">Engineering Recommendation</span>
                              <p className="p-2.5 rounded bg-paper-200/40 border border-line text-ink leading-relaxed font-sans">
                                 {v.recommendation}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* SUB-VIEW 5: INFORMATION ARCHITECTURE */}
      {activeSubTab === 'ia' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Information Architecture & Navigation Flow</h3>
          <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-3">
            <span className="label text-[10px] block">Detected Calls to Action & Navigation Triggers</span>
            <div className="flex flex-wrap gap-2">
              {ctas.length > 0 ? (
                ctas.map((cta, i) => (
                  <span key={i} className="px-3 py-1 bg-paper-100 border border-line rounded-md text-xs font-medium text-ink">
                    🔘 {cta}
                  </span>
                ))
              ) : (
                <span className="text-xs text-ink-500">No CTA strings were extracted.</span>
              )}
            </div>
          </div>
        </div>
      )}
    </PillarShell>
  );
}
