import React, { useState } from 'react';
import { Card } from '../../ui';
import {
  CRO_BUSINESS_MODELS,
  CroEnterpriseBundle,
  CroEnterpriseFinding,
  croApi,
} from '../../../services/croApi';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Play,
  ShieldAlert,
  Target,
  TrendingUp,
} from 'lucide-react';

interface CroExecutiveDashboardProps {
  bundle: CroEnterpriseBundle;
  domain: string;
  websiteUrl: string;
  onRefreshBundle: (auditId?: string) => Promise<void>;
  onNavigateTab: (tab: string) => void;
}

const SOURCE_BADGE: Record<string, { label: string; cls: string }> = {
  direct_technical: { label: 'Confirmed Technical Defect', cls: 'bg-bad/10 text-bad border-bad/30' },
  browser_test: { label: 'Confirmed Browser Failure', cls: 'bg-bad/10 text-bad border-bad/30' },
  analytics_observation: { label: 'Measured Funnel Behavior', cls: 'bg-indigo-500/10 text-indigo-700 border-indigo-300' },
  user_research: { label: 'User Research', cls: 'bg-emerald-500/10 text-emerald-700 border-emerald-300' },
  heuristic_observation: { label: 'Expert Heuristic Assessment', cls: 'bg-warn/10 text-warn border-warn/30' },
  ai_hypothesis: { label: 'Hypothesis (Needs Validation)', cls: 'bg-paper-200 text-ink-700 border-line' },
  experiment_result: { label: 'Experiment-Supported', cls: 'bg-good/10 text-good border-good/30' },
};

export function CroExecutiveDashboard({
  bundle,
  domain,
  websiteUrl,
  onRefreshBundle,
  onNavigateTab,
}: CroExecutiveDashboardProps) {
  const { audit, scorecard, findings, remediation_pack, experiments } = bundle;
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [businessType, setBusinessType] = useState(
    bundle.department_artifacts?.strategy_summary?.business_model || 'saas',
  );
  const [primaryGoal, setPrimaryGoal] = useState(
    bundle.department_artifacts?.strategy_summary?.primary_conversion || '',
  );
  const [targetCustomers, setTargetCustomers] = useState('');
  const [aov, setAov] = useState('');
  const [profileSaved, setProfileSaved] = useState<string | null>(null);

  const handleRunLiveAudit = async () => {
    setRunning(true);
    setRunError(null);
    try {
      const res = await croApi.createAudit({
        target_url: websiteUrl || `https://${domain}/`,
        mode: 'standard',
        safe_mode: true,
        use_live_browser: false,
        business_config: {
          business_type: businessType !== 'unknown' ? businessType : undefined,
          primary_conversion: primaryGoal.trim() || undefined,
          target_customers: targetCustomers.trim() || undefined,
          average_order_value: aov ? Number(aov) : undefined,
        },
      });
      await onRefreshBundle(res.audit.audit_id);
    } catch (err: any) {
      setRunError(err?.message || 'Could not execute CRO audit.');
    } finally {
      setRunning(false);
    }
  };

  const handleSaveProfile = async () => {
    setProfileSaved(null);
    try {
      await croApi.updateBusinessProfile({
        domain,
        website_url: websiteUrl || `https://${domain}/`,
        business_type: businessType,
        primary_conversion: primaryGoal.trim() || undefined,
        target_customers: targetCustomers.trim() || undefined,
        average_order_value: aov ? Number(aov) : undefined,
      });
      setProfileSaved('CRO business profile and conversion goal registry saved.');
    } catch (err: any) {
      setProfileSaved(err?.message || 'Could not save profile.');
    }
  };

  const tasks = remediation_pack?.tasks || [];
  const verifiedTasks = tasks.filter((t) => t.status === 'verified').length;
  const functionalIssues = findings.filter((f) => f.source_type === 'direct_technical' || f.source_type === 'browser_test').length;
  const mobileDim = scorecard.experience_dimensions.find((d) => d.dimension_id === 'mobile_accessibility');
  const primaryCrMetric = scorecard.business_performance_metrics.find((m) => /conversion rate/i.test(m.metric));
  const rpvMetric = scorecard.business_performance_metrics.find((m) => /revenue per visitor/i.test(m.metric));

  return (
    <div className="space-y-6">
      {/* Three Strictly Separated CRO Scorecards (Phase 20 & Phase 26) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="p-5 space-y-2 border-l-4 border-l-ink">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold">
              1. CRO Experience Score
            </span>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-paper-200 text-ink font-bold">
              Grade {scorecard.experience_grade}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-ink">
              {scorecard.experience_score == null ? 'Unmeasured' : `${scorecard.experience_score.toFixed(1)}`}
            </span>
            {scorecard.experience_score != null && <span className="text-sm text-ink-500">/ 100</span>}
          </div>
          <p className="text-xs text-ink-600">
            Weighted across {scorecard.experience_active_weight_pct}% evaluated framework weight. Measures observed website usability, functional reliability, and conversion-path readiness.
          </p>
          <p className="text-[11px] font-mono text-ink-500">
            Methodology: {scorecard.methodology_version} · Confidence: {scorecard.confidence ?? 'N/A'}
          </p>
        </Card>

        <Card className="p-5 space-y-2 border-l-4 border-l-indigo-500">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold">
              2. Conversion Measurement Score
            </span>
            <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-700 font-semibold">
              {scorecard.measurement_status}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-ink">
              {scorecard.measurement_score == null ? 'Unmeasured' : `${scorecard.measurement_score.toFixed(1)}`}
            </span>
            {scorecard.measurement_score != null && <span className="text-sm text-ink-500">/ 100</span>}
          </div>
          <p className="text-xs text-ink-600">
            Measures analytics installation, duplicate-free tracking, goal event coverage, and data quality independently of website UX.
          </p>
          <p className="text-[11px] font-mono text-ink-500">
            Analytics completeness: {scorecard.analytics_completeness_pct ?? 0}% · Scope coverage: {scorecard.scope_coverage_pct ?? 0}%
          </p>
        </Card>

        <Card className="p-5 space-y-2 border-l-4 border-l-emerald-600">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold">
              3. Measured Business Performance
            </span>
            <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 font-semibold">
              {scorecard.business_performance_status.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <p className="text-[10px] font-mono uppercase text-ink-500">Primary Conv. Rate</p>
              <p className="text-lg font-bold text-ink">
                {primaryCrMetric?.value != null ? `${primaryCrMetric.value}%` : 'Unavailable'}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase text-ink-500">Revenue / Visitor</p>
              <p className="text-lg font-bold text-ink">
                {rpvMetric?.value != null ? `${rpvMetric.unit || '$'}${rpvMetric.value}` : 'Unavailable'}
              </p>
            </div>
          </div>
          <p className="text-xs text-ink-600">
            Actual conversion &amp; revenue KPIs from authorized connectors. Never converted into an arbitrary quality score or zeroed when disconnected.
          </p>
        </Card>
      </div>

      {/* Top Operational Indicators */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="p-3.5">
          <p className="text-[10px] font-mono uppercase text-ink-500">Functional Issues</p>
          <p className="text-xl font-bold text-bad mt-1">{functionalIssues}</p>
          <p className="text-[11px] text-ink-500">Confirmed defects</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[10px] font-mono uppercase text-ink-500">Total Findings</p>
          <p className="text-xl font-bold text-ink mt-1">{findings.length}</p>
          <p className="text-[11px] text-ink-500">{audit.critical_findings_count} critical</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[10px] font-mono uppercase text-ink-500">Mobile &amp; A11y</p>
          <p className="text-xl font-bold text-ink mt-1">
            {mobileDim?.score != null ? `${mobileDim.score}` : 'Unmeasured'}
          </p>
          <p className="text-[11px] text-ink-500">Weight 10%</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[10px] font-mono uppercase text-ink-500">Remediation Pack</p>
          <p className="text-xl font-bold text-ink mt-1">
            {verifiedTasks}/{tasks.length}
          </p>
          <p className="text-[11px] text-ink-500">Verified tasks</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[10px] font-mono uppercase text-ink-500">Experiments</p>
          <p className="text-xl font-bold text-ink mt-1">{experiments.length}</p>
          <p className="text-[11px] text-ink-500">A/B proposals</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[10px] font-mono uppercase text-ink-500">QA Gate Status</p>
          <p className="text-sm font-mono font-bold uppercase text-ink mt-2">
            {(audit.qa_status || 'pending').replace(/_/g, ' ')}
          </p>
          <p className="text-[11px] text-ink-500">
            Evidence coverage {scorecard.evidence_coverage_pct != null ? `${scorecard.evidence_coverage_pct}%` : 'Not measured'}
          </p>
        </Card>
      </div>

      {/* Business Context Configurator & On-Demand CRO Audit Launcher */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-ink flex items-center gap-2">
              <Target className="w-4 h-4 text-ink-700" />
              Business Profile, Conversion Goals &amp; Audit Orchestrator
            </h3>
            <p className="text-xs text-ink-500 mt-0.5">
              Configure your business model and primary conversion objective. Unknown inputs stay marked unknown rather than invented.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSaveProfile}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink"
            >
              Save Business Profile
            </button>
            <button
              type="button"
              disabled={running}
              onClick={handleRunLiveAudit}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-ink text-white hover:opacity-90 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              {running ? 'Running 11-Stage CRO Audit...' : 'Run Enterprise CRO Audit'}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <label className="text-xs text-ink-600 space-y-1">
            <span className="font-semibold">Business Model (12 supported)</span>
            <select
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              className="w-full rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs text-ink"
            >
              {CRO_BUSINESS_MODELS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-ink-600 space-y-1">
            <span className="font-semibold">Primary Conversion Objective</span>
            <input
              type="text"
              value={primaryGoal}
              onChange={(e) => setPrimaryGoal(e.target.value)}
              placeholder="e.g., Paid subscription, Qualified demo"
              className="w-full rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs text-ink"
            />
          </label>
          <label className="text-xs text-ink-600 space-y-1">
            <span className="font-semibold">Target Audience / ICP</span>
            <input
              type="text"
              value={targetCustomers}
              onChange={(e) => setTargetCustomers(e.target.value)}
              placeholder="Leave blank to keep unknown"
              className="w-full rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs text-ink"
            />
          </label>
          <label className="text-xs text-ink-600 space-y-1">
            <span className="font-semibold">Average Order / Lead Value (optional)</span>
            <input
              type="number"
              min="0"
              value={aov}
              onChange={(e) => setAov(e.target.value)}
              placeholder="Unknown if blank"
              className="w-full rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs text-ink"
            />
          </label>
        </div>
        {profileSaved && <p className="text-xs text-good font-medium">{profileSaved}</p>}
        {runError && <p className="text-xs text-bad font-medium">{runError}</p>}
      </Card>

      {/* 10 Weighted CRO Experience Dimensions Breakdown */}
      <Card className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-ink">10 Weighted CRO Experience Dimensions (100% Framework)</h3>
            <p className="text-xs text-ink-500">
              Weighted formula excludes inapplicable or unexecuted checks from the denominator without penalty.
            </p>
          </div>
          <span className="text-xs font-mono text-ink-500">Safe Mode: {audit.safe_mode ? 'ON' : 'OFF'}</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {scorecard.experience_dimensions.map((dim) => (
            <div key={dim.dimension_id} className="rounded-lg border border-line p-3 space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-ink">{dim.name}</span>
                <span className="font-mono text-xs text-ink-600">
                  {dim.score == null ? 'Unmeasured' : `${dim.score.toFixed(1)}/100`} · {dim.configured_weight_pct}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-paper-200 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    dim.score == null ? 'bg-ink-300' : dim.score >= 80 ? 'bg-good' : dim.score >= 60 ? 'bg-warn' : 'bg-bad'
                  }`}
                  style={{ width: `${dim.score == null ? 0 : Math.max(4, Math.min(100, dim.score))}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono text-ink-500">
                <span>
                  {dim.executed_checks}/{dim.total_checks} checks · {dim.status}
                </span>
                <span>{(dim.evidence_types || []).join(', ') || 'none'}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Highest-Priority Findings with Explicit Evidence Classification Badges */}
      <Card className="p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-ink flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-warn" />
            Highest-Priority CRO Findings (Evidence Class Separated)
          </h3>
          <button
            type="button"
            onClick={() => onNavigateTab('remediation')}
            className="text-xs font-semibold text-ink underline inline-flex items-center gap-1"
          >
            Open Consolidated Remediation Center <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
        {findings.length === 0 ? (
          <p className="text-xs text-ink-500">No high-priority CRO defects observed in the current sample.</p>
        ) : (
          <div className="space-y-2.5">
            {findings.slice(0, 6).map((f: CroEnterpriseFinding) => {
              const badge = SOURCE_BADGE[f.source_type] || { label: f.source_type, cls: 'bg-paper-200 text-ink-700 border-line' };
              return (
                <div key={f.finding_id} className="rounded-lg border border-line p-3.5 space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-bold text-ink-500">{f.finding_id}</span>
                      <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                        f.severity === 'critical' ? 'bg-bad/15 text-bad' : f.severity === 'high' ? 'bg-warn/15 text-warn' : 'bg-paper-200 text-ink-700'
                      }`}>
                        {f.severity}
                      </span>
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-ink-500">Dept {f.department} · {f.owner_role}</span>
                  </div>
                  <p className="text-sm font-semibold text-ink">{f.title}</p>
                  <p className="text-xs text-ink-600">{f.description}</p>
                  <p className="text-xs text-ink-700">
                    <span className="font-semibold">Recommended fix:</span> {f.recommendation}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Disclosures & Methodology Guardrails */}
      {scorecard.disclosures.length > 0 && (
        <Card className="p-4 bg-paper-50 space-y-1.5">
          <p className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" /> Epistemic &amp; Measurement Disclosures
          </p>
          <ul className="list-disc pl-5 text-xs text-ink-600 space-y-1">
            {scorecard.disclosures.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
