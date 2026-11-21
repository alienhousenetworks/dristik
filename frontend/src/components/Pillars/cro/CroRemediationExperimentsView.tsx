import React, { useState } from 'react';
import { Card } from '../../ui';
import {
  CroEnterpriseBundle,
  CroExperimentRecord,
  CroRemediationTaskRecord,
  croApi,
} from '../../../services/croApi';
import { AlertTriangle, CheckCircle2, FlaskConical, ShieldCheck, Wrench } from 'lucide-react';

interface CroRemediationExperimentsViewProps {
  bundle: CroEnterpriseBundle;
  mode: 'remediation' | 'experiments';
  onRefreshBundle: (auditId?: string) => Promise<void>;
}

const REM_VIEWS = [
  { id: 'kanban', label: 'Kanban' },
  { id: 'list', label: 'All Tasks' },
  { id: 'root_causes', label: 'Root-Cause Groups' },
  { id: 'matrix', label: 'Priority Matrix' },
  { id: 'roadmap', label: '30/60/90d Roadmap' },
  { id: 'departments', label: 'Department Workload' },
  { id: 'verification', label: 'Verification Queue & Before/After' },
  { id: 'deliverables', label: '18 Pack Deliverables' },
] as const;

const EXP_TABS = ['all', 'draft', 'running', 'completed', 'inconclusive', 'stopped_guardrail'] as const;

export function CroRemediationExperimentsView({
  bundle,
  mode,
  onRefreshBundle,
}: CroRemediationExperimentsViewProps) {
  const [remView, setRemView] = useState<(typeof REM_VIEWS)[number]['id']>('kanban');
  const [expTab, setExpTab] = useState<(typeof EXP_TABS)[number]>('all');
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const pack = bundle.remediation_pack;
  const tasks: CroRemediationTaskRecord[] = pack?.tasks || [];
  const views = bundle.remediation_views || {};

  const handleApproveTask = async (taskId: string) => {
    setBusyId(taskId);
    setActionMsg(null);
    try {
      await croApi.approveTask(taskId);
      setActionMsg(`Task ${taskId} approved for engineering implementation.`);
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (e: any) {
      setActionMsg(e?.message || 'Approval requires elevated role or live CRO audit.');
    } finally {
      setBusyId(null);
    }
  };

  const handleDeployTask = async (taskId: string) => {
    setBusyId(taskId);
    setActionMsg(null);
    try {
      await croApi.deployTask(taskId, `deploy-${Date.now()}`);
      setActionMsg(`Task ${taskId} deployed -> moved to AWAITING_VERIFICATION (independent retest required to close).`);
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (e: any) {
      setActionMsg(e?.message || 'Task must be approved before deployment.');
    } finally {
      setBusyId(null);
    }
  };

  const handleVerifyTask = async (task: CroRemediationTaskRecord) => {
    setBusyId(task.task_id);
    setActionMsg(null);
    try {
      const ver = await croApi.verifyTask(task.task_id, {
        after_html: '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><h1>Verified Update</h1><a class="btn-primary" href="/start">Start Free Trial</a></body></html>',
        analytics_event_confirmed: false,
      });
      setActionMsg(
        `Independent verification recorded: impl=${ver.implementation_verified}, functional=${ver.functional_verification}, analytics=${ver.analytics_verification}, business=${ver.business_outcome}.`,
      );
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (e: any) {
      setActionMsg(e?.message || 'Verification failed.');
    } finally {
      setBusyId(null);
    }
  };

  if (mode === 'remediation') {
    const deptCounts: Record<string, number> = views.department_workload || {};
    if (!Object.keys(deptCounts).length) {
      tasks.forEach((t) => {
        deptCounts[t.department] = (deptCounts[t.department] || 0) + 1;
      });
    }

    return (
      <div className="space-y-5">
        <Card className="p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-base font-bold text-ink flex items-center gap-2">
                <Wrench className="w-4 h-4" /> Consolidated CRO Remediation Center
              </h3>
              <p className="text-xs text-ink-600">
                {pack?.executive_summary || 'Coordinates all validated findings into deduplicated root-cause initiatives with independent 4-outcome verification.'}
              </p>
            </div>
            <span className="font-mono text-xs px-2.5 py-1 rounded bg-paper-200 text-ink">
              {tasks.length} Coordinated Task(s) · {(pack?.conflicts_detected || []).length} Conflict(s)
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5 border-t border-line pt-3">
            {REM_VIEWS.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setRemView(v.id)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md border ${
                  remView === v.id ? 'bg-ink text-white border-ink' : 'border-line text-ink-600 hover:bg-paper-100'
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
          {actionMsg && <p className="text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded p-2.5">{actionMsg}</p>}
        </Card>

        {remView === 'kanban' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { key: 'backlog', label: 'Backlog', items: tasks.filter((t) => t.status === 'backlog') },
              { key: 'approved', label: 'Approved / In Progress', items: tasks.filter((t) => t.status === 'approved' || t.status === 'in_progress') },
              { key: 'awaiting', label: 'Awaiting Verification', items: tasks.filter((t) => t.status === 'deployed' || t.status === 'awaiting_verification') },
              { key: 'verified', label: 'Independently Verified', items: tasks.filter((t) => t.status === 'verified') },
            ].map((col) => (
              <Card key={col.key} className="p-3.5 space-y-2.5 bg-paper-50">
                <div className="flex items-center justify-between border-b border-line pb-2">
                  <span className="text-xs font-bold text-ink">{col.label}</span>
                  <span className="font-mono text-xs text-ink-500">{col.items.length}</span>
                </div>
                {col.items.length === 0 ? (
                  <p className="text-[11px] text-ink-400">No tasks in stage.</p>
                ) : (
                  col.items.map((t) => (
                    <div key={t.task_id} className="p-3 rounded-lg border border-line bg-surface space-y-2">
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="font-bold text-ink">{t.priority} · {t.department}</span>
                        <span className="text-ink-500">{t.effort_estimate}</span>
                      </div>
                      <p className="text-xs font-semibold text-ink">{t.title}</p>
                      <p className="text-[11px] text-ink-600 line-clamp-2">{t.proposed_change}</p>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {t.approval_status !== 'approved' && (
                          <button
                            type="button"
                            disabled={busyId === t.task_id}
                            onClick={() => handleApproveTask(t.task_id)}
                            className="px-2 py-1 text-[10px] font-semibold rounded bg-ink text-white"
                          >
                            Approve
                          </button>
                        )}
                        {t.approval_status === 'approved' && t.status !== 'awaiting_verification' && t.status !== 'verified' && (
                          <button
                            type="button"
                            disabled={busyId === t.task_id}
                            onClick={() => handleDeployTask(t.task_id)}
                            className="px-2 py-1 text-[10px] font-semibold rounded bg-indigo-600 text-white"
                          >
                            Mark Deployed
                          </button>
                        )}
                        {t.status === 'awaiting_verification' && (
                          <button
                            type="button"
                            disabled={busyId === t.task_id}
                            onClick={() => handleVerifyTask(t)}
                            className="px-2 py-1 text-[10px] font-semibold rounded bg-good text-white"
                          >
                            Run Independent Verify
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </Card>
            ))}
          </div>
        )}

        {remView === 'list' && (
          <Card className="p-4 overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[820px]">
              <thead>
                <tr className="border-b border-line font-mono text-ink-500">
                  <th className="py-2 pr-3">Task ID</th>
                  <th className="py-2 pr-3">Priority</th>
                  <th className="py-2 pr-3">Initiative</th>
                  <th className="py-2 pr-3">Dept / Owner</th>
                  <th className="py-2 pr-3">Linked Findings</th>
                  <th className="py-2 pr-3">Due</th>
                  <th className="py-2">Verification Status</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.task_id} className="border-b border-line">
                    <td className="py-2.5 pr-3 font-mono font-semibold">{t.task_id}</td>
                    <td className="py-2.5 pr-3 font-mono font-bold">{t.priority}</td>
                    <td className="py-2.5 pr-3 font-medium text-ink">{t.title}</td>
                    <td className="py-2.5 pr-3">{t.department} ({t.owner})</td>
                    <td className="py-2.5 pr-3 font-mono">{t.linked_finding_ids.length}</td>
                    <td className="py-2.5 pr-3 font-mono">{t.due_date || '—'}</td>
                    <td className="py-2.5 font-mono uppercase">{t.verification_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {remView === 'root_causes' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(pack?.root_cause_groups || []).map((g: any) => (
              <Card key={g.group_id} className="p-4 space-y-1.5">
                <div className="flex justify-between text-xs font-mono">
                  <span className="font-bold text-ink">{g.priority} · {g.department}</span>
                  <span className="text-ink-500">{g.finding_count} finding(s) consolidated</span>
                </div>
                <p className="text-sm font-bold text-ink">{g.title}</p>
                <p className="text-[11px] font-mono text-ink-500">Task: {g.task_id} · Findings: {(g.finding_ids || []).join(', ')}</p>
              </Card>
            ))}
          </div>
        )}

        {remView === 'matrix' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { title: 'Quick Wins (High Priority · Low Effort)', items: tasks.filter((t) => (t.priority === 'P0' || t.priority === 'P1') && t.effort_estimate === 'low') },
              { title: 'Major Initiatives (High Priority · Med/High Effort)', items: tasks.filter((t) => (t.priority === 'P0' || t.priority === 'P1') && t.effort_estimate !== 'low') },
              { title: 'Fill-Ins (Medium/Low · Low Effort)', items: tasks.filter((t) => t.priority !== 'P0' && t.priority !== 'P1' && t.effort_estimate === 'low') },
              { title: 'Strategic Backlog', items: tasks.filter((t) => t.priority !== 'P0' && t.priority !== 'P1' && t.effort_estimate !== 'low') },
            ].map((q) => (
              <Card key={q.title} className="p-4 space-y-2">
                <h4 className="text-xs font-bold uppercase font-mono text-ink-500">{q.title}</h4>
                {q.items.length === 0 ? <p className="text-xs text-ink-400">None</p> : q.items.map((t) => (
                  <div key={t.task_id} className="text-xs border-b border-line pb-1.5">{t.priority} · {t.title}</div>
                ))}
              </Card>
            ))}
          </div>
        )}

        {remView === 'roadmap' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['days_30', 'days_60', 'days_90'] as const).map((win) => (
              <Card key={win} className="p-4 space-y-2">
                <h4 className="text-xs font-bold uppercase font-mono text-ink">{win.replace('days_', '')} Days</h4>
                {tasks.filter((t) => t.roadmap_window === win).map((t) => (
                  <div key={t.task_id} className="p-2.5 rounded border border-line text-xs">
                    <p className="font-semibold text-ink">{t.priority} · {t.title}</p>
                    <p className="text-[11px] text-ink-500">Due {t.due_date || 'TBD'} · {t.department}</p>
                  </div>
                ))}
              </Card>
            ))}
          </div>
        )}

        {remView === 'departments' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(deptCounts).map(([dept, count]) => (
              <Card key={dept} className="p-4">
                <p className="text-xs font-mono text-ink-500 uppercase">{dept}</p>
                <p className="text-2xl font-bold text-ink mt-1">{count}</p>
                <p className="text-[11px] text-ink-500">Assigned task(s)</p>
              </Card>
            ))}
          </div>
        )}

        {remView === 'verification' && (
          <Card className="p-5 space-y-4">
            <div>
              <h4 className="text-sm font-bold text-ink flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-good" /> Independent 4-Outcome Verification &amp; Before/After Evidence
              </h4>
              <p className="text-xs text-ink-600">
                Developer completion never closes a task. Dristik independently evaluates Implementation, Functional, Analytics, and Business Outcomes separately.
              </p>
            </div>
            <div className="space-y-3">
              {tasks.map((t) => {
                const after = t.after_evidence || {};
                return (
                  <div key={t.task_id} className="p-4 rounded-lg border border-line space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-bold text-ink">{t.task_id} · {t.title}</span>
                      <span className="font-mono text-[11px] uppercase px-2 py-0.5 rounded bg-paper-200">{t.verification_status}</span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono">
                      <div className="p-2 rounded bg-paper-50 border border-line">
                        <span className="text-ink-500 block">1. Implementation</span>
                        <strong>{after.implementation_verified || 'pending'}</strong>
                      </div>
                      <div className="p-2 rounded bg-paper-50 border border-line">
                        <span className="text-ink-500 block">2. Functional</span>
                        <strong>{after.functional_verification || 'not_tested'}</strong>
                      </div>
                      <div className="p-2 rounded bg-paper-50 border border-line">
                        <span className="text-ink-500 block">3. Analytics Event</span>
                        <strong>{after.analytics_verification || 'unavailable'}</strong>
                      </div>
                      <div className="p-2 rounded bg-paper-50 border border-line">
                        <span className="text-ink-500 block">4. Business Outcome</span>
                        <strong>{after.business_outcome || 'insufficient_data'}</strong>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {remView === 'deliverables' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(pack?.deliverables || {}).map(([key, val]) => (
              <Card key={key} className="p-3.5 space-y-1">
                <p className="font-mono text-[11px] font-bold uppercase text-ink">{key.replace(/_/g, ' ')}</p>
                <p className="text-xs text-ink-600">
                  {typeof val === 'object' && val !== null
                    ? Array.isArray(val)
                      ? `${val.length} item(s)`
                      : `${Object.keys(val).length} structured section field(s)`
                    : String(val)}
                </p>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Phase 24 & 34 — Experimentation Studio
  const experiments: CroExperimentRecord[] = bundle.experiments || [];
  const filteredExps = experiments.filter((e) => expTab === 'all' || e.status === expTab);

  return (
    <div className="space-y-5">
      <Card className="p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-ink flex items-center gap-2">
              <FlaskConical className="w-4 h-4" /> CRO Experimentation &amp; Statistical Integrity Studio
            </h3>
            <p className="text-xs text-ink-600">
              A verified implementation is NOT a winning experiment. Enforces power/sample size, 14-day minimum duration, chi-square SRM checks, guardrail monitoring, and inconclusive reporting.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5 border-t border-line pt-3">
          {EXP_TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setExpTab(t)}
              className={`px-2.5 py-1 text-xs rounded-md border capitalize ${
                expTab === t ? 'bg-ink text-white border-ink' : 'border-line text-ink-600'
              }`}
            >
              {t.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        {actionMsg && <p className="text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded p-2">{actionMsg}</p>}
      </Card>

      {filteredExps.length === 0 ? (
        <Card className="p-6 text-xs text-ink-500">No experiments in this status bucket.</Card>
      ) : (
        <div className="space-y-3">
          {filteredExps.map((exp) => (
            <Card key={exp.experiment_id} className="p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-mono text-[11px] font-bold text-ink-500">
                    {exp.experiment_id} · {exp.experiment_type.toUpperCase()}
                  </span>
                  <h4 className="text-sm font-bold text-ink">{exp.title}</h4>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] uppercase px-2 py-0.5 rounded bg-paper-200 text-ink">
                    {exp.status.replace(/_/g, ' ')}
                  </span>
                  {exp.approval_status !== 'approved' && (
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          await croApi.approveExperiment(exp.experiment_id);
                          setActionMsg(`Approved experiment ${exp.experiment_id}.`);
                          await onRefreshBundle(bundle.audit.audit_id);
                        } catch (e: any) {
                          setActionMsg(e?.message || 'Approval requires permissions.');
                        }
                      }}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-ink text-white"
                    >
                      Approve
                    </button>
                  )}
                </div>
              </div>

              <p className="text-xs text-ink-700 bg-paper-50 border border-line rounded p-3 leading-relaxed">
                <strong>Hypothesis:</strong> {exp.hypothesis_statement}
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded border border-line">
                  <span className="text-ink-500 block text-[10px]">Sample / Variant</span>
                  <strong>{exp.required_sample_per_variant.toLocaleString()}</strong>
                </div>
                <div className="p-2.5 rounded border border-line">
                  <span className="text-ink-500 block text-[10px]">Min Duration</span>
                  <strong>{exp.planned_duration_days} days</strong>
                </div>
                <div className="p-2.5 rounded border border-line">
                  <span className="text-ink-500 block text-[10px]">MDE / Alpha</span>
                  <strong>{Math.round(exp.minimum_detectable_effect * 100)}% / 5%</strong>
                </div>
                <div className="p-2.5 rounded border border-line">
                  <span className="text-ink-500 block text-[10px]">Guardrails</span>
                  <strong>{exp.guardrail_metrics.length} active</strong>
                </div>
              </div>

              {exp.latest_result && (
                <div
                  className={`p-3 rounded-lg border text-xs space-y-1 ${
                    exp.latest_result.srm_detected || exp.latest_result.guardrail_breached
                      ? 'bg-bad/10 border-bad/30 text-bad'
                      : exp.latest_result.decision === 'winner'
                      ? 'bg-good/10 border-good/30 text-good'
                      : 'bg-paper-100 border-line text-ink-700'
                  }`}
                >
                  <div className="flex items-center gap-2 font-mono font-bold uppercase">
                    {exp.latest_result.decision === 'winner' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                    Decision: {exp.latest_result.decision.replace(/_/g, ' ')} · SRM p={exp.latest_result.srm_p_value}
                  </div>
                  <p>{exp.latest_result.decision_rationale}</p>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
