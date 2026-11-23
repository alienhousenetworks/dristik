import React, { useState } from 'react';
import { Card } from '../../ui';
import { GeoEnterpriseBundle, geoApi } from '../../../services/geoApi';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Info,
  Play,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

interface GeoExecutiveDashboardProps {
  bundle: GeoEnterpriseBundle;
  domain: string;
  websiteUrl: string;
  onRefreshBundle: (auditId?: string) => Promise<void>;
  onNavigateTab: (tab: string) => void;
}

function pctLabel(val: number | null | undefined): string {
  return val == null ? 'Unmeasured' : `${val}%`;
}

export function GeoExecutiveDashboard({
  bundle,
  domain,
  websiteUrl,
  onRefreshBundle,
  onNavigateTab,
}: GeoExecutiveDashboardProps) {
  const { audit, scorecard, platforms, findings, remediation_pack } = bundle;
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [brandName, setBrandName] = useState(audit.brand_name || domain.split('.')[0]);
  const [industry, setIndustry] = useState(bundle.scope?.industry || '');
  const [competitorsText, setCompetitorsText] = useState((bundle.scope?.competitors || []).join(', '));
  const [budgetUsd, setBudgetUsd] = useState(String(audit.budget_usd ?? 5));
  const [repetitions, setRepetitions] = useState(String(scorecard.coverage?.repeat_test_count || 1));

  const handleLaunchAudit = async () => {
    setRunning(true);
    setRunError(null);
    try {
      const comps = competitorsText
        .split(',')
        .map((c: string) => c.trim())
        .filter(Boolean);
      const res = await geoApi.createAudit({
        target_url: websiteUrl || `https://${domain}/`,
        brand_name: brandName.trim() || undefined,
        industry: industry.trim(),
        competitors: comps,
        mode: 'standard',
        repetitions: Math.max(1, Math.min(5, Number(repetitions) || 1)),
        budget_usd: Math.max(0, Number(budgetUsd) || 5),
        max_prompts: 18,
      });
      await onRefreshBundle(res.audit.audit_id);
    } catch (err: any) {
      setRunError(err?.message || 'Could not execute Enterprise GEO Audit.');
    } finally {
      setRunning(false);
    }
  };

  const obs = scorecard.observed_metrics || {};
  const cov = scorecard.coverage;
  const tasks = remediation_pack?.tasks || [];
  const verifiedTasks = tasks.filter((t) => t.status === 'verified').length;

  return (
    <div className="space-y-6">
      {/* Publication Status & Firewall Disclosure Banner */}
      <Card className="p-4 border-l-4 border-l-pine bg-paper-50 flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-pine/10 text-pine border border-pine/30">
              {audit.publication_status}
            </span>
            <span className="font-mono text-[10px] text-ink-500">
              Methodology: {scorecard.methodology_version} · Audit ID: {audit.audit_id}
            </span>
          </div>
          <p className="text-xs text-ink-700 leading-relaxed flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-pine shrink-0 mt-0.5" />
            <span>{scorecard.methodology_disclosure}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => onNavigateTab('methodology')}
          className="text-xs font-mono font-semibold text-pine hover:underline flex items-center gap-1"
        >
          Methodology &amp; Weights <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </Card>

      {/* Dual Separated Scorecards (Phase 12 & Phase 14) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="p-5 space-y-2 border-l-4 border-l-good">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold">
              1. Observed GEO Performance
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-paper-200 text-ink font-bold">
              {scorecard.observed_performance_status}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-ink">
              {scorecard.observed_performance_score != null ? scorecard.observed_performance_score : 'Unmeasured'}
            </span>
            {scorecard.observed_performance_score != null && <span className="text-xs text-ink-500">/ 100 · Grade {scorecard.observed_performance_grade}</span>}
          </div>
          <p className="text-xs text-ink-600">
            Mentions: <strong>{pctLabel(obs.brand_mention_rate_pct)}</strong> · Recommendations: <strong>{pctLabel(obs.recommendation_rate_pct)}</strong> · Citations: <strong>{pctLabel(obs.citation_observation_rate_pct)}</strong>
          </p>
          <p className="text-[11px] font-mono text-ink-500">
            Runs: {cov.successful_prompt_executions}/{cov.total_planned_prompts} planned · Platforms tested: {cov.tested_platforms.length}
          </p>
        </Card>

        <Card className="p-5 space-y-2 border-l-4 border-l-pine">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold">
              2. GEO Readiness &amp; Optimization
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-paper-200 text-ink font-bold">
              {scorecard.readiness_status}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-ink">
              {scorecard.readiness_score != null ? scorecard.readiness_score : 'Unmeasured'}
            </span>
            {scorecard.readiness_score != null && <span className="text-xs text-ink-500">/ 100 · Grade {scorecard.readiness_grade}</span>}
          </div>
          <p className="text-xs text-ink-600">
            Entity consistency, content clarity/extractability, technical retrieval access, and external authority signals.
          </p>
          <p className="text-[11px] font-mono text-ink-500">
            Pages analyzed: {bundle.pages.length} · Confidence: {cov.evidence_confidence ?? 'N/A'}
          </p>
        </Card>

        <Card className="p-5 space-y-2 border-l-4 border-l-warn">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-ink-500 font-semibold">
              Remediation &amp; Verification
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-warn/10 text-warn font-bold">
              {findings.length} Findings
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-ink">{verifiedTasks}/{tasks.length}</span>
            <span className="text-xs text-ink-500">verified tasks</span>
          </div>
          <p className="text-xs text-ink-600">
            Consolidated post-audit fixing pack across departments. Developer deployments require independent verification.
          </p>
          <button
            type="button"
            onClick={() => onNavigateTab('remediation')}
            className="text-xs font-semibold text-pine hover:underline flex items-center gap-1"
          >
            Open Remediation Center <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>
      </div>

      {/* Audit Launcher & Scope Configuration */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-pine" /> Run Canonical Enterprise GEO Audit
            </h3>
            <p className="text-xs text-ink-500">
              Executes the 9-department GEO DAG with branded vs non-branded prompt suites, cost caps, and QA gates.
            </p>
          </div>
          <button
            type="button"
            onClick={handleLaunchAudit}
            disabled={running}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-pine text-white text-xs font-semibold rounded hover:bg-pine/90 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            {running ? 'Running GEO Audit…' : 'Launch GEO Audit'}
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
          <label className="space-y-1">
            <span className="font-mono text-[10px] uppercase text-ink-500">Brand Name</span>
            <input value={brandName} onChange={(e) => setBrandName(e.target.value)} className="w-full px-2.5 py-1.5 border border-line rounded bg-white" />
          </label>
          <label className="space-y-1">
            <span className="font-mono text-[10px] uppercase text-ink-500">Industry</span>
            <input value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="e.g. workflow automation" className="w-full px-2.5 py-1.5 border border-line rounded bg-white" />
          </label>
          <label className="space-y-1">
            <span className="font-mono text-[10px] uppercase text-ink-500">Competitors (comma)</span>
            <input value={competitorsText} onChange={(e) => setCompetitorsText(e.target.value)} placeholder="Competitor A, Competitor B" className="w-full px-2.5 py-1.5 border border-line rounded bg-white" />
          </label>
          <label className="space-y-1">
            <span className="font-mono text-[10px] uppercase text-ink-500">Budget Cap ($)</span>
            <input type="number" min="0" step="0.5" value={budgetUsd} onChange={(e) => setBudgetUsd(e.target.value)} className="w-full px-2.5 py-1.5 border border-line rounded bg-white" />
          </label>
          <label className="space-y-1">
            <span className="font-mono text-[10px] uppercase text-ink-500">Repeats</span>
            <input type="number" min="1" max="5" value={repetitions} onChange={(e) => setRepetitions(e.target.value)} className="w-full px-2.5 py-1.5 border border-line rounded bg-white" />
          </label>
        </div>
        {runError && <p className="text-xs text-bad font-mono">{runError}</p>}
      </Card>

      {/* Platform-Specific Scorecards (Phase 14) */}
      <Card className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <Bot className="w-4 h-4 text-pine" /> Platform-Specific GEO Scorecards
            </h3>
            <p className="text-xs text-ink-500">
              Each platform displays exact testing mode, model version, and coverage. Untested platforms never display synthetic scores.
            </p>
          </div>
          <button type="button" onClick={() => onNavigateTab('connectors')} className="text-xs font-mono text-pine hover:underline">
            Configure Providers
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {platforms.map((p) => {
            const tested = p.prompts_succeeded > 0;
            return (
              <div key={p.platform_id} className="p-4 rounded border border-line bg-paper-50 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-sm text-ink">{p.display_name}</span>
                  <span className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded border ${tested ? 'bg-good/10 text-good border-good/30' : 'bg-paper-200 text-ink-600 border-line'}`}>
                    {tested ? 'OBSERVED' : p.data_quality_state}
                  </span>
                </div>
                <p className="font-mono text-[10px] text-ink-500 truncate" title={p.active_model}>
                  {p.active_model} · {p.testing_mode}
                </p>
                {tested ? (
                  <div className="grid grid-cols-3 gap-1 pt-1 text-center">
                    <div className="p-1.5 bg-white rounded border border-line">
                      <div className="text-[9px] font-mono text-ink-500">Mentions</div>
                      <div className="text-sm font-bold text-ink">{pctLabel(p.mention_rate_pct)}</div>
                    </div>
                    <div className="p-1.5 bg-white rounded border border-line">
                      <div className="text-[9px] font-mono text-ink-500">Recs</div>
                      <div className="text-sm font-bold text-good">{pctLabel(p.recommendation_rate_pct)}</div>
                    </div>
                    <div className="p-1.5 bg-white rounded border border-line">
                      <div className="text-[9px] font-mono text-ink-500">Citations</div>
                      <div className="text-sm font-bold text-pine">{pctLabel(p.citation_rate_pct)}</div>
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-ink-500 italic">
                    Not tested — configure credentials to observe live visibility.
                  </p>
                )}
                <div className="text-[10px] font-mono text-ink-500 flex justify-between pt-1 border-t border-line/60">
                  <span>Runs: {p.prompts_succeeded}/{p.prompts_attempted ?? '—'}</span>
                  <span>Cost: {p.total_cost_usd != null ? `$${p.total_cost_usd.toFixed(4)}` : 'Unmeasured'}</span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 7-Dimension Proposed Methodology Breakdown */}
      <Card className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <Activity className="w-4 h-4 text-pine" /> 7-Dimension GEO Methodology Breakdown (100% Weight Total)
          </h3>
          <span className="text-[11px] font-mono text-ink-500">Active weight measured: {scorecard.active_weight_pct}%</span>
        </div>
        <div className="space-y-2.5">
          {scorecard.dimensions.map((d) => (
            <div key={d.dimension_key} className="p-3 rounded border border-line bg-white flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-[220px]">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-ink">{d.dimension_name}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-paper-100 text-ink-600">{d.proposed_weight_pct}%</span>
                  <span className="text-[9px] font-mono uppercase text-ink-400">
                    {d.scorecard_group === 'observed_performance' ? 'Observed Outcome' : 'Readiness Factor'}
                  </span>
                </div>
                {d.notes[0] && <p className="text-[11px] text-ink-500 mt-0.5">{d.notes[0]}</p>}
              </div>
              <div className="flex items-center gap-3">
                <div className="w-36 h-2 bg-paper-200 rounded overflow-hidden">
                  <div
                    className={`h-full ${d.score == null ? 'bg-ink-300' : d.score >= 75 ? 'bg-good' : d.score >= 50 ? 'bg-warn' : 'bg-bad'}`}
                    style={{ width: `${d.score != null ? Math.min(100, d.score) : 12}%` }}
                  />
                </div>
                <span className="font-mono text-xs font-bold w-24 text-right text-ink">
                  {d.score != null ? `${d.score}/100 (${d.grade})` : d.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Priority Findings Preview */}
      <Card className="p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-bad" /> Priority GEO Findings ({findings.length})
          </h3>
          <button type="button" onClick={() => onNavigateTab('findings')} className="text-xs font-mono text-pine hover:underline">
            View All Findings
          </button>
        </div>
        {findings.length === 0 ? (
          <p className="text-xs text-ink-500 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-good" /> No critical GEO issues flagged in this snapshot.
          </p>
        ) : (
          <div className="space-y-2">
            {findings.slice(0, 5).map((f) => (
              <div key={f.finding_id} className="p-3 rounded border border-line bg-paper-50 flex flex-wrap items-start justify-between gap-2 text-xs">
                <div className="space-y-0.5 max-w-3xl">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-ink">{f.finding_id}</span>
                    <span className={`font-mono text-[10px] uppercase px-1.5 py-0.5 rounded font-bold ${f.severity === 'critical' || f.severity === 'high' ? 'bg-bad/10 text-bad' : 'bg-warn/10 text-warn'}`}>
                      {f.severity}
                    </span>
                    <span className="font-semibold text-ink">{f.title}</span>
                  </div>
                  <p className="text-ink-600">{f.description}</p>
                </div>
                <span className="font-mono text-[10px] text-ink-500">{f.evidence_ids.length} evidence ref(s)</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
