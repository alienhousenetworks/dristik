import React, { useState } from 'react';
import { Card } from '../../ui';
import { GeoEnterpriseBundle, GeoRemediationTaskRecord, geoApi } from '../../../services/geoApi';
import { CheckCircle2, ClipboardList, GitBranch, Rocket, ShieldCheck, Wrench } from 'lucide-react';

interface GeoRemediationVerificationWorkspaceProps {
  bundle: GeoEnterpriseBundle;
  mode: 'findings' | 'recommendations' | 'remediation' | 'verification';
  onRefreshBundle: (auditId?: string) => Promise<void>;
}

export function GeoRemediationVerificationWorkspace({
  bundle,
  mode,
  onRefreshBundle,
}: GeoRemediationVerificationWorkspaceProps) {
  const [viewMode, setViewMode] = useState<'list' | 'kanban' | 'departments'>('list');
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [deployRef, setDeployRef] = useState('release-geo-fix-01');
  const [verifyHtml, setVerifyHtml] = useState('');
  const [sroKeyword, setSroKeyword] = useState('');
  const [sroResult, setSroResult] = useState<Record<string, any> | null>(null);
  const [sroRunning, setSroRunning] = useState(false);
  const [rsSignal, setRsSignal] = useState('S06');
  const [rsResult, setRsResult] = useState<Record<string, any> | null>(null);
  const [rsRunning, setRsRunning] = useState(false);

  const handleRunSro = async () => {
    if (!sroKeyword.trim()) return;
    setSroRunning(true);
    try {
      const targetUrl = bundle.audit.domain.startsWith('http')
        ? bundle.audit.domain
        : `https://${bundle.audit.domain}`;
      const res = await fetch('/api/v1/geo-pipeline/sro/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_url: targetUrl, keyword: sroKeyword.trim() }),
      });
      if (res.ok) setSroResult(await res.json());
    } finally {
      setSroRunning(false);
    }
  };

  const handleRunRankSignal = async () => {
    if (!sroKeyword.trim()) return;
    setRsRunning(true);
    setRsResult(null);
    try {
      const targetUrl = bundle.audit.domain.startsWith('http')
        ? bundle.audit.domain
        : `https://${bundle.audit.domain}`;
      const res = await fetch('/api/v1/geo-pipeline/rank-signal/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          signal_id: rsSignal,
          keyword: sroKeyword.trim(),
          target_url: targetUrl,
          max_trials: 20,
        }),
      });
      const text = await res.text();
      const lines = text.split('\n');
      for (let i = lines.length - 1; i >= 0; i--) {
        if (lines[i].startsWith('data: ')) {
          try {
            setRsResult(JSON.parse(lines[i].slice(6)));
            break;
          } catch {
            // ignore partial line
          }
        }
      }
    } finally {
      setRsRunning(false);
    }
  };

  const tasks = bundle.remediation_pack?.tasks || [];
  const verifications = bundle.verifications || [];

  const handleAction = async (fn: () => Promise<any>, okMsg: string) => {
    setActionMsg(null);
    try {
      await fn();
      setActionMsg(okMsg);
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (err: any) {
      setActionMsg(err?.message || 'Action blocked (verify role permissions).');
    }
  };

  if (mode === 'findings') {
    return (
      <Card className="p-5 space-y-4">
        <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
          <ClipboardList className="w-4 h-4 text-pine" /> Canonical GEO Findings Registry ({bundle.findings.length})
        </h3>
        {bundle.findings.length === 0 ? (
          <p className="text-xs text-ink-500">No open GEO findings recorded.</p>
        ) : (
          <div className="space-y-3">
            {bundle.findings.map((f) => (
              <div key={f.finding_id} className="p-4 rounded border border-line bg-paper-50 space-y-1.5 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-ink">{f.finding_id}</span>
                    <span className={`font-mono text-[10px] uppercase px-1.5 py-0.5 rounded font-bold ${f.severity === 'critical' || f.severity === 'high' ? 'bg-bad/10 text-bad' : 'bg-warn/10 text-warn'}`}>
                      {f.severity}
                    </span>
                    <span className="font-semibold text-ink">{f.title}</span>
                  </div>
                  <span className="font-mono text-[10px] text-ink-500">Dept {f.department} · {f.category}</span>
                </div>
                <p className="text-ink-700">{f.description}</p>
                <p className="text-ink-600"><strong>Root Cause:</strong> {f.root_cause}</p>
                <p className="text-pine"><strong>Recommendation:</strong> {f.recommendation}</p>
                <div className="font-mono text-[10px] text-ink-500 pt-1">
                  Evidence IDs: {f.evidence_ids.join(', ') || 'Hypothesis pending evidence'}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    );
  }

  if (mode === 'recommendations') {
    return (
      <Card className="p-5 space-y-4">
        <h3 className="font-sans font-bold text-ink text-base">Prioritized Strategic GEO Recommendations ({bundle.recommendations.length})</h3>
        {bundle.recommendations.length === 0 ? (
          <p className="text-xs text-ink-500">Run an Enterprise GEO Audit to synthesize consolidated recommendations.</p>
        ) : (
          <div className="space-y-3">
            {bundle.recommendations.map((r: any) => (
              <div key={r.recommendation_id} className="p-4 rounded border border-line bg-paper-50 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-ink">{r.title}</span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white border border-line">
                    Priority {r.priority_score} · Impact: {r.expected_impact} · Effort: {r.effort}
                  </span>
                </div>
                <p className="text-ink-700">{r.rationale}</p>
                <p className="font-mono text-[10px] text-ink-500">Owner: {r.owner_department} · Findings: {(r.finding_ids || []).join(', ')}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    );
  }

  if (mode === 'verification') {
    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-4">
          <div>
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-good" /> Independent GEO Verification Queue &amp; Before/After Proof
            </h3>
            <p className="text-xs text-ink-500">
              Developers cannot self-verify fixes. Independent verification separates <strong>Implementation Verified</strong> from <strong>Observed AI Outcome Improved</strong>.
            </p>
          </div>
          <div className="p-3 rounded border border-line bg-paper-50 space-y-2 text-xs">
            <label className="block font-mono text-[10px] uppercase text-ink-500">
              Post-Deployment HTML Snapshot (optional; leave empty to live re-crawl target URL)
            </label>
            <textarea
              rows={2}
              value={verifyHtml}
              onChange={(e) => setVerifyHtml(e.target.value)}
              placeholder="Paste updated HTML or JSON-LD snapshot for independent verification..."
              className="w-full p-2 border border-line rounded bg-white font-mono text-[11px]"
            />
          </div>
          {actionMsg && <p className="text-xs font-mono text-pine">{actionMsg}</p>}
          {tasks.length === 0 ? (
            <p className="text-xs text-ink-500">No remediation tasks in verification queue.</p>
          ) : (
            <div className="space-y-3">
              {tasks.map((t) => (
                <div key={t.task_id} className="p-4 rounded border border-line bg-white text-xs space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-ink">{t.task_id} · {t.title}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-paper-100 border border-line">
                        Status: {t.status}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          handleAction(
                            () =>
                              geoApi.verifyTask(t.task_id, {
                                after_html: verifyHtml.trim() || undefined,
                                live_recrawl: !verifyHtml.trim(),
                              }),
                            `Independent verification executed for ${t.task_id}.`,
                          )
                        }
                        className="px-3 py-1 bg-good text-white rounded font-semibold"
                      >
                        Run Independent Verify
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3 font-mono text-[10px] text-ink-600">
                    <span>Implementation Verified: {t.implementation_verified == null ? 'Pending' : t.implementation_verified ? 'Yes' : 'No'}</span>
                    <span>Observed AI Outcome Improved: {t.outcome_improved || 'NOT_TESTED'}</span>
                    {t.deployment_ref && <span>Deployment: {t.deployment_ref}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5 space-y-4">
          <div>
            <h4 className="font-sans font-bold text-ink text-sm">SRO Selection Rate &amp; Rank Signal A/B Experiment Lab</h4>
            <p className="text-xs text-ink-500">
              Measure Gemini grounding word-budget share (SRO) and run credit-native paired A/B passage experiments (code-built signals: 1 credit, LLM signals: 2 credits, unused trials refunded on early stop).
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <input
              type="text"
              value={sroKeyword}
              onChange={(e) => setSroKeyword(e.target.value)}
              placeholder="Target buyer keyword (e.g. best enterprise crm)"
              className="flex-1 min-w-[220px] px-3 py-1.5 rounded border border-line bg-white"
            />
            <button
              type="button"
              disabled={sroRunning || !sroKeyword.trim()}
              onClick={handleRunSro}
              className="px-3 py-1.5 rounded bg-ink text-white font-mono disabled:opacity-50"
            >
              {sroRunning ? 'Running SRO...' : 'Run SRO Analysis'}
            </button>
            <select
              value={rsSignal}
              onChange={(e) => setRsSignal(e.target.value)}
              className="px-2 py-1.5 rounded border border-line bg-white font-mono"
            >
              <option value="S05">S05: Bullet List (1 cr)</option>
              <option value="S06">S06: Freshness Clause (1 cr)</option>
              <option value="S12">S12: Question Heading (1 cr)</option>
              <option value="S13">S13: Bold Query Terms (1 cr)</option>
              <option value="S00">S00: Placebo Calibration (2 cr)</option>
              <option value="S02">S02: Specific Number/Stat (2 cr)</option>
              <option value="S04">S04: Named Source (2 cr)</option>
            </select>
            <button
              type="button"
              disabled={rsRunning || !sroKeyword.trim()}
              onClick={handleRunRankSignal}
              className="px-3 py-1.5 rounded bg-pine text-white font-mono disabled:opacity-50"
            >
              {rsRunning ? 'Testing Signal...' : 'Run Rank Signal A/B'}
            </button>
          </div>
          {sroResult && (
            <div className="p-3 rounded border border-line bg-paper-50 text-xs space-y-1">
              <div className="font-mono font-bold text-ink">
                SRO Score: {sroResult.overall_score ?? 'NOT_CONFIGURED'} · Gemini Selection Rate: {sroResult.grounding?.selection_rate_pct ?? 'N/A'}% ({sroResult.data_quality_state})
              </div>
              <p className="text-ink-700">{sroResult.summary}</p>
            </div>
          )}
          {rsResult && (
            <div className="p-3 rounded border border-line bg-paper-50 text-xs space-y-1">
              {rsResult.message ? (
                <p className="text-bad font-mono">{rsResult.message}</p>
              ) : (
                <>
                  <div className="font-mono font-bold text-ink">
                    {rsResult.signal_id} ({rsResult.signal_name}) · Verdict: {rsResult.verdict} · Wins: {rsResult.wins}/{rsResult.n_valid}
                  </div>
                  <div className="font-mono text-[10px] text-ink-600">
                    95% CI: [{rsResult.ci_lo}, {rsResult.ci_hi}] · Credits charged: {rsResult.credits?.charged_credits} (refunded: {rsResult.credits?.refunded_credits})
                  </div>
                </>
              )}
            </div>
          )}
        </Card>

        {verifications.length > 0 && (
          <Card className="p-5 space-y-3">
            <h4 className="font-sans font-bold text-ink text-sm">Recorded Independent Verification Runs ({verifications.length})</h4>
            {verifications.map((v: any) => (
              <div key={v.verification_id} className="p-3 rounded border border-line bg-paper-50 text-xs space-y-1">
                <div className="flex justify-between font-mono text-[10px]">
                  <span>{v.verification_id} · Task {v.task_id}</span>
                  <span>Verified by: {v.verified_by} · Overall: {v.overall_status}</span>
                </div>
                <div className="text-ink-700">
                  Content verified: <strong>{String(v.content_update_verified ?? 'N/A')}</strong> · Schema verified: <strong>{String(v.structured_data_verified ?? 'N/A')}</strong> · Outcome improved: <strong>{v.outcome_improved}</strong>
                </div>
              </div>
            ))}
          </Card>
        )}
      </div>
    );
  }

  // Remediation Center (List / Kanban / Departments)
  const statuses = ['open', 'approved', 'in_progress', 'deployed', 'verified', 'blocked', 'regressed'];
  const deptPackages = bundle.remediation_pack?.department_packages || {};

  return (
    <div className="space-y-6">
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <Wrench className="w-4 h-4 text-pine" /> Consolidated GEO Remediation Center ({tasks.length} Tasks · 13 Deliverables)
            </h3>
            <p className="text-xs text-ink-500">
              {bundle.remediation_pack?.executive_summary || 'Generated after all specialist findings and root causes are consolidated.'}
            </p>
          </div>
          <div className="flex gap-1.5 text-xs">
            {(['list', 'kanban', 'departments'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setViewMode(m)}
                className={`px-2.5 py-1 rounded border font-mono uppercase text-[10px] ${viewMode === m ? 'bg-ink text-white border-ink' : 'bg-white border-line'}`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs bg-paper-50 p-2.5 rounded border border-line">
          <Rocket className="w-3.5 h-3.5 text-pine" />
          <span className="font-mono text-[10px] uppercase text-ink-500">Deployment Ref:</span>
          <input value={deployRef} onChange={(e) => setDeployRef(e.target.value)} className="px-2 py-1 border border-line rounded bg-white font-mono text-xs" />
          {actionMsg && <span className="font-mono text-[11px] text-pine ml-auto">{actionMsg}</span>}
        </div>

        {viewMode === 'kanban' ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {['open', 'approved', 'deployed', 'verified'].map((col) => {
              const colTasks = tasks.filter((t) => t.status === col || (col === 'open' && !statuses.includes(t.status)));
              return (
                <div key={col} className="p-3 rounded border border-line bg-paper-50 space-y-2">
                  <div className="font-mono text-[10px] uppercase font-bold text-ink-600">
                    {col} ({colTasks.length})
                  </div>
                  {colTasks.map((t) => (
                    <div key={t.task_id} className="p-2.5 rounded bg-white border border-line text-xs space-y-1">
                      <div className="font-mono text-[10px] text-pine font-bold">{t.task_id} · {t.priority}</div>
                      <div className="font-semibold text-ink">{t.title}</div>
                      <div className="text-[10px] text-ink-500">{t.department}</div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        ) : viewMode === 'departments' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {Object.entries(deptPackages).map(([dept, ids]) => (
              <div key={dept} className="p-4 rounded border border-line bg-paper-50 space-y-1.5">
                <div className="font-bold text-ink">{dept} ({ids.length} tasks)</div>
                <div className="font-mono text-[10px] text-ink-600">{ids.join(', ')}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((t: GeoRemediationTaskRecord) => (
              <div key={t.task_id} className="p-4 rounded border border-line bg-white text-xs space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-pine">{t.task_id}</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper-100 border border-line font-bold">{t.priority}</span>
                    <span className="font-semibold text-ink">{t.title}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-paper-100">{t.status}</span>
                    <button
                      type="button"
                      onClick={() => handleAction(() => geoApi.approveTask(t.task_id), `Approved ${t.task_id}.`)}
                      className="px-2 py-1 border border-line rounded hover:bg-paper-50 font-mono text-[10px]"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAction(() => geoApi.deployTask(t.task_id, deployRef), `Marked ${t.task_id} deployed (${deployRef}); awaiting independent verification.`)}
                      className="px-2 py-1 bg-ink text-white rounded font-mono text-[10px]"
                    >
                      Mark Deployed
                    </button>
                  </div>
                </div>
                <p className="text-ink-700">{t.proposed_change}</p>
                {t.dependencies.length > 0 && (
                  <p className="text-[10px] font-mono text-ink-500 flex items-center gap-1">
                    <GitBranch className="w-3 h-3" /> Depends on: {t.dependencies.join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
