import React, { useMemo, useState } from 'react';
import { Badge, Button } from '../../ui';
import { seoApi, SeoRemediationTask, SeoVerificationResult } from '../../../services/seoApi';
import { AlertTriangle, Calendar, CheckCircle2, Clock, Play } from 'lucide-react';

interface SeoRemediationCenterProps {
  auditId: string;
  tasks: SeoRemediationTask[];
  onTasksUpdated?: () => void;
}

type CenterView = 'kanban' | 'list' | 'matrix' | 'roadmap' | 'calendar' | 'verification';

const KANBAN_COLUMNS = [
  { id: 'REMEDIATION_PLANNED', label: 'Planned' },
  { id: 'IN_PROGRESS', label: 'In Progress' },
  { id: 'FIX_SUBMITTED', label: 'Fix Submitted (Awaiting Verify)' },
  { id: 'VERIFIED_FIXED', label: 'Verified Fixed' },
];

export function SeoRemediationCenter({ auditId, tasks, onTasksUpdated }: SeoRemediationCenterProps) {
  const [view, setView] = useState<CenterView>('kanban');
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<SeoVerificationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleVerify = async (task: SeoRemediationTask) => {
    setVerifyingId(task.task_id);
    setErrorMsg(null);
    setLastResult(null);
    try {
      const targetUrl = task.affected_scope?.sample_urls?.[0];
      const res = await seoApi.verifyTask(auditId, task.task_id, {
        target_url: targetUrl,
        rule_id: task.before_evidence?.rule_id || task.problem,
      });
      setLastResult(res);
      onTasksUpdated?.();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Verification failed. Task remains unverified.');
    } finally {
      setVerifyingId(null);
    }
  };

  const handleAdvanceStatus = async (task: SeoRemediationTask, nextStatus: 'IN_PROGRESS' | 'FIX_SUBMITTED') => {
    try {
      await seoApi.updateTask(auditId, task.task_id, { status: nextStatus });
      onTasksUpdated?.();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to update task status.');
    }
  };

  const roadmapBuckets = useMemo(() => {
    return {
      '7 Days (P0 Blockers)': tasks.filter((t) => t.priority === 'P0'),
      '30 Days (P1 High Impact)': tasks.filter((t) => t.priority === 'P1'),
      '60 Days (P2 Structural)': tasks.filter((t) => t.priority === 'P2'),
      '90 Days (P3 Governance)': tasks.filter((t) => !['P0', 'P1', 'P2'].includes(t.priority)),
    };
  }, [tasks]);

  const verificationQueue = useMemo(
    () => tasks.filter((t) => t.verification_status !== 'VERIFIED_FIXED'),
    [tasks]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">SEO Remediation &amp; Verification Center</h3>
          <p className="text-xs text-ink-500">
            Assign fixes, track approvals, compare before/after evidence, and run independent live re-crawl verification. Fixed is never Verified until automated checks pass.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1 p-1 rounded-xl border border-line bg-paper-subtle">
          {(
            [
              ['kanban', 'Kanban'],
              ['list', 'List'],
              ['matrix', 'Priority Matrix'],
              ['roadmap', '7/30/60/90 Roadmap'],
              ['calendar', 'Calendar'],
              ['verification', `Verification Queue (${verificationQueue.length})`],
            ] as Array<[CenterView, string]>
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setView(id)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg ${
                view === id ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:text-ink'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {errorMsg}
        </div>
      )}

      {/* 6-Row Before/After Live Verification Comparison */}
      {lastResult && (
        <div className="rounded-xl border border-line bg-paper p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-ink">
              {lastResult.passed ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-amber-600" />}
              <span>Before / After Verification Comparison — {lastResult.task_id} ({lastResult.verification_status})</span>
            </div>
            <Badge tone={lastResult.passed ? 'good' : 'warn'}>{lastResult.passed ? 'PASSED' : 'STILL OPEN'}</Badge>
          </div>
          <p className="text-xs text-ink-600">{lastResult.check_summary}</p>
          <table className="w-full text-left text-xs border border-line rounded-lg overflow-hidden">
            <thead>
              <tr className="bg-paper-subtle border-b border-line text-[10px] uppercase text-ink-400">
                <th className="p-2">Dimension</th>
                <th className="p-2">Before</th>
                <th className="p-2">After (Live Re-crawl)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line font-mono text-[11px]">
              {lastResult.comparison_rows.map((r) => (
                <tr key={r.dimension}>
                  <td className="p-2 font-sans font-semibold text-ink">{r.dimension}</td>
                  <td className="p-2 text-ink-500">{r.before}</td>
                  <td className="p-2 text-ink">{r.after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {view === 'kanban' && (
        <div className="grid gap-4 md:grid-cols-4">
          {KANBAN_COLUMNS.map((col) => {
            const colTasks = tasks.filter((t) => {
              const eff = t.verification_status === 'VERIFIED_FIXED' ? 'VERIFIED_FIXED' : t.status || 'REMEDIATION_PLANNED';
              return eff === col.id;
            });
            return (
              <div key={col.id} className="rounded-xl border border-line bg-paper-subtle p-3 space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-line">
                  <span className="text-xs font-bold text-ink">{col.label}</span>
                  <Badge tone="neutral">{colTasks.length}</Badge>
                </div>
                {colTasks.length === 0 ? (
                  <p className="text-[11px] text-ink-400 py-4 text-center">No tasks</p>
                ) : (
                  colTasks.map((t) => (
                    <div key={t.task_id} className="p-3 rounded-lg bg-paper border border-line space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <Badge tone={t.priority === 'P0' ? 'bad' : t.priority === 'P1' ? 'warn' : 'neutral'}>{t.priority}</Badge>
                        <span className="font-mono text-[10px] text-ink-400">{t.task_id}</span>
                      </div>
                      <p className="font-semibold text-ink line-clamp-2">{t.problem}</p>
                      <p className="text-[11px] text-ink-500">{t.owner} · {t.effort}</p>
                      <div className="flex flex-wrap gap-1 pt-1">
                        {col.id === 'REMEDIATION_PLANNED' && (
                          <Button size="sm" variant="ghost" onClick={() => handleAdvanceStatus(t, 'IN_PROGRESS')} className="text-[11px] h-6 px-2">
                            Start
                          </Button>
                        )}
                        {col.id === 'IN_PROGRESS' && (
                          <Button size="sm" variant="ghost" onClick={() => handleAdvanceStatus(t, 'FIX_SUBMITTED')} className="text-[11px] h-6 px-2">
                            Submit Fix
                          </Button>
                        )}
                        {col.id !== 'VERIFIED_FIXED' && (
                          <Button size="sm" variant="secondary" disabled={verifyingId === t.task_id} onClick={() => handleVerify(t)} className="text-[11px] h-6 px-2">
                            {verifyingId === t.task_id ? 'Verifying...' : 'Run Retest'}
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            );
          })}
        </div>
      )}

      {view === 'list' && (
        <div className="rounded-xl border border-line bg-paper overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-subtle text-[10px] uppercase text-ink-400">
                <th className="p-3">Task ID</th>
                <th className="p-3">Priority</th>
                <th className="p-3">Problem</th>
                <th className="p-3">Owner / Dept</th>
                <th className="p-3">Effort</th>
                <th className="p-3">Verification</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {tasks.map((t) => (
                <tr key={t.task_id}>
                  <td className="p-3 font-mono text-ink-500">{t.task_id}</td>
                  <td className="p-3"><Badge tone={t.priority === 'P0' ? 'bad' : 'warn'}>{t.priority}</Badge></td>
                  <td className="p-3 font-medium text-ink">{t.problem}</td>
                  <td className="p-3 text-ink-600">{t.owner} ({t.department})</td>
                  <td className="p-3 font-mono text-ink-500">{t.effort}</td>
                  <td className="p-3"><Badge tone={t.verification_status === 'VERIFIED_FIXED' ? 'good' : 'neutral'}>{t.verification_status}</Badge></td>
                  <td className="p-3 text-right">
                    <Button size="sm" variant="secondary" disabled={verifyingId === t.task_id} onClick={() => handleVerify(t)} className="text-xs h-7">
                      <Play className="w-3 h-3 mr-1" /> Verify
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {view === 'matrix' && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/20 space-y-2">
            <h4 className="text-xs font-bold uppercase text-rose-700">Quick Wins &amp; Critical (P0 / P1)</h4>
            {tasks.filter((t) => t.priority === 'P0' || t.priority === 'P1').map((t) => (
              <div key={t.task_id} className="p-2.5 rounded bg-paper border border-line text-xs flex justify-between">
                <span className="font-semibold text-ink">{t.problem}</span>
                <span className="font-mono text-ink-400">{t.effort}</span>
              </div>
            ))}
          </div>
          <div className="p-4 rounded-xl border border-line bg-paper-subtle space-y-2">
            <h4 className="text-xs font-bold uppercase text-ink-600">Scheduled &amp; Iterative (P2 / P3)</h4>
            {tasks.filter((t) => t.priority !== 'P0' && t.priority !== 'P1').map((t) => (
              <div key={t.task_id} className="p-2.5 rounded bg-paper border border-line text-xs flex justify-between">
                <span className="font-semibold text-ink">{t.problem}</span>
                <span className="font-mono text-ink-400">{t.effort}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {view === 'roadmap' && (
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(roadmapBuckets).map(([bucket, items]) => (
            <div key={bucket} className="p-4 rounded-xl border border-line bg-paper space-y-2">
              <div className="flex items-center justify-between border-b border-line pb-2">
                <h4 className="text-xs font-bold uppercase text-ink">{bucket}</h4>
                <Badge tone="neutral">{items.length}</Badge>
              </div>
              {items.length === 0 ? (
                <p className="text-xs text-ink-400">No items in this window.</p>
              ) : (
                items.map((t) => (
                  <div key={t.task_id} className="p-2.5 rounded bg-paper-subtle border border-line text-xs space-y-1">
                    <div className="font-semibold text-ink">{t.problem}</div>
                    <div className="text-[11px] text-ink-500">Acceptance: {t.acceptance_criteria}</div>
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      )}

      {view === 'calendar' && (
        <div className="p-4 rounded-xl border border-line bg-paper space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-ink">
            <Calendar className="w-4 h-4 text-primary" /> Scheduled Delivery &amp; Retest Calendar
          </div>
          {tasks.map((t) => (
            <div key={t.task_id} className="p-3 rounded-lg bg-paper-subtle border border-line text-xs flex items-center justify-between">
              <div>
                <p className="font-semibold text-ink">{t.problem}</p>
                <p className="text-[11px] text-ink-500">{t.owner} · Due: {t.due_date || 'Unscheduled'}</p>
              </div>
              <Badge tone="neutral">{t.status}</Badge>
            </div>
          ))}
        </div>
      )}

      {view === 'verification' && (
        <div className="space-y-3">
          {verificationQueue.length === 0 ? (
            <div className="p-6 rounded-xl border border-line bg-paper-subtle text-center text-xs text-ink-500">
              All remediation tasks have passed independent live verification.
            </div>
          ) : (
            verificationQueue.map((t) => (
              <div key={t.task_id} className="p-4 rounded-xl border border-line bg-paper flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2">
                    <Badge tone={t.priority === 'P0' ? 'bad' : 'warn'}>{t.priority}</Badge>
                    <code className="text-ink-400">{t.task_id}</code>
                    <Badge tone="neutral">{t.verification_status}</Badge>
                  </div>
                  <p className="font-semibold text-ink">{t.problem}</p>
                  <p className="text-ink-500">Protocol: {t.verification_protocol}</p>
                </div>
                <Button size="sm" disabled={verifyingId === t.task_id} onClick={() => handleVerify(t)} className="text-xs shrink-0">
                  {verifyingId === t.task_id ? <><Clock className="w-3.5 h-3.5 mr-1 animate-spin" /> Retesting...</> : <><Play className="w-3.5 h-3.5 mr-1" /> Run Live Retest</>}
                </Button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
