import React, { useState } from 'react';
import { Badge, Button } from '../../ui';
import { Finding } from '../../../types';
import { seoApi, SeoRemediationTask, SeoVerificationResult } from '../../../services/seoApi';
import { AlertTriangle, Check, CheckCircle2, Clock, Copy, Play, X } from 'lucide-react';

interface FindingDetailDrawerProps {
  finding: Finding | null;
  auditId?: string;
  task?: SeoRemediationTask | null;
  onClose: () => void;
  onUpdateStatus?: (findingId: string, newStatus: string) => void;
}

export function FindingDetailDrawer({
  finding,
  auditId,
  task,
  onClose,
  onUpdateStatus,
}: FindingDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<'patch' | 'instructions' | 'evidence' | 'verification'>('patch');
  const [copiedPatch, setCopiedPatch] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifResult, setVerifResult] = useState<SeoVerificationResult | null>(null);
  const [verifError, setVerifError] = useState<string | null>(null);

  if (!finding) return null;

  const currentStatus = finding.resolution_status || finding.verification_status || 'VERIFIED';
  const affectedUrls: string[] = Array.isArray((finding as any).affected_urls)
    ? (finding as any).affected_urls
    : (finding as any).url
      ? [(finding as any).url]
      : [];

  const impl = task?.implementation;
  const codeSnippet =
    impl?.code_diff_snippet ||
    `# Remediation Directive for ${finding.finding_id}\n# Apply verified fix: ${finding.recommendation || finding.description || 'Resolve finding per evidence.'}`;

  const handleCopy = (code: string) => {
    navigator.clipboard?.writeText(code);
    setCopiedPatch(true);
    setTimeout(() => setCopiedPatch(false), 2000);
  };

  // Real live backend re-crawl verification (NEVER setTimeout!)
  const handleTriggerVerification = async () => {
    if (!auditId) {
      setVerifError('Audit ID is required to run backend re-crawl verification.');
      return;
    }
    setIsVerifying(true);
    setVerifError(null);
    setVerifResult(null);
    try {
      const taskId = task?.task_id || `REM_${finding.finding_id}`;
      const res = await seoApi.verifyTask(auditId, taskId, {
        target_url: affectedUrls[0],
        rule_id: (finding as any).rule_id || finding.title,
      });
      setVerifResult(res);
      if (res.passed && res.verification_status === 'VERIFIED_FIXED') {
        onUpdateStatus?.(finding.finding_id, 'VERIFIED_FIXED');
      }
    } catch (err: any) {
      setVerifError(err?.message || 'Live verification request failed. Finding remains open.');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-ink-950/40 backdrop-blur-xs flex justify-end">
      <div className="relative w-full max-w-3xl bg-paper dark:bg-paper-900 border-l border-line shadow-2xl flex flex-col h-full">
        <div className="p-5 border-b border-line bg-paper-subtle space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge tone={finding.severity === 'CRITICAL' ? 'bad' : finding.severity === 'HIGH' ? 'warn' : 'neutral'}>
                {finding.severity}
              </Badge>
              <span className="font-mono text-xs font-bold text-ink-400">{finding.finding_id}</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                {currentStatus}
              </span>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg text-ink-400 hover:text-ink hover:bg-paper-100">
              <X className="w-5 h-5" />
            </button>
          </div>

          <h3 className="text-base font-bold text-ink leading-snug">{finding.title}</h3>

          <div className="flex flex-wrap items-center gap-3 text-xs text-ink-500">
            <span>Category: <strong className="text-ink">{finding.category}</strong></span>
            <span>·</span>
            <span>Effort: <strong className="text-ink">{task?.effort || 'Estimate pending'}</strong></span>
            <span>·</span>
            <span>Affected URLs: <strong className="text-ink">{affectedUrls.length}</strong></span>
            {(finding as any).root_cause_id && (
              <>
                <span>·</span>
                <span>Root Cause: <code className="text-ink">{(finding as any).root_cause_id}</code></span>
              </>
            )}
          </div>

          <div className="flex items-center gap-2 pt-2 border-t border-line/60">
            {[
              { id: 'patch', label: 'Implementation Directive' },
              { id: 'instructions', label: 'Diagnosis & Scope' },
              { id: 'evidence', label: 'Empirical Evidence' },
              { id: 'verification', label: 'Live Re-crawl Verification' },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id as any)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                  activeTab === t.id ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:bg-paper-100'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'patch' && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-semibold text-ink-500 uppercase">Stack:</span>
                  <Badge tone={impl?.stack_confidence === 'DETECTED' ? 'good' : 'neutral'}>
                    {impl?.platform || 'GENERIC_HTML'} ({impl?.stack_confidence || 'GENERIC_FALLBACK'})
                  </Badge>
                </div>
                <Button size="sm" variant="secondary" onClick={() => handleCopy(codeSnippet)} className="text-xs">
                  {copiedPatch ? <><Check className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Copied</> : <><Copy className="w-3.5 h-3.5 mr-1" /> Copy Directive</>}
                </Button>
              </div>

              {impl?.target_file_pattern && (
                <p className="text-xs text-ink-500">
                  Target template/config: <code className="font-mono text-ink">{impl.target_file_pattern}</code>
                </p>
              )}

              <div className="rounded-xl border border-line bg-paper-950 text-paper-50 p-4 font-mono text-xs overflow-x-auto">
                <pre className="whitespace-pre-wrap">{codeSnippet}</pre>
              </div>

              <div className="p-4 rounded-xl border border-line bg-paper-subtle space-y-2 text-xs text-ink-700">
                <h4 className="font-bold text-ink uppercase">Acceptance Criteria &amp; Instructions</h4>
                <p>{impl?.instructions || finding.recommendation || finding.description}</p>
                {task?.acceptance_criteria && (
                  <p className="pt-1 border-t border-line/60"><strong>Acceptance Criteria:</strong> {task.acceptance_criteria}</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'instructions' && (
            <div className="space-y-4">
              <div className="card p-4 space-y-2 bg-paper-subtle border border-line">
                <h4 className="text-xs font-bold uppercase text-ink-500">Technical Diagnosis &amp; Impact</h4>
                <p className="text-xs text-ink-700 leading-relaxed">{finding.description || task?.problem}</p>
                {task?.seo_impact && <p className="text-xs text-ink-600"><strong>SEO Impact:</strong> {task.seo_impact}</p>}
              </div>
              <div className="card p-4 space-y-2 bg-paper-subtle border border-line">
                <h4 className="text-xs font-bold uppercase text-ink-500">Affected URL Scope ({affectedUrls.length})</h4>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {affectedUrls.length > 0 ? (
                    affectedUrls.map((u, idx) => (
                      <div key={idx} className="font-mono text-xs text-ink p-1.5 rounded bg-paper border border-line truncate">{u}</div>
                    ))
                  ) : (
                    <p className="text-xs text-ink-500">Site-level or unscoped finding.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase text-ink-500">Empirical Observations</h4>
              {finding.evidence && finding.evidence.length > 0 ? (
                finding.evidence.map((ev, i) => (
                  <div key={i} className="p-3 rounded-lg border border-line bg-paper-subtle text-xs space-y-1">
                    <p className="font-mono text-ink-500 text-[10px]">Element: {ev.element}</p>
                    <p className="font-mono text-ink font-semibold">{ev.value}</p>
                    {ev.snippet && <pre className="p-2 rounded bg-paper font-mono text-[11px] mt-1">{ev.snippet}</pre>}
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-lg bg-paper-subtle border border-line text-xs text-ink-500">
                  Evidence references: {((finding as any).evidence_refs || (finding as any).evidence_ids || []).join(', ') || 'None attached.'}
                </div>
              )}
            </div>
          )}

          {activeTab === 'verification' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-line bg-paper-subtle space-y-3">
                <div className="flex items-center gap-2">
                  <Play className="w-4 h-4 text-primary" />
                  <h4 className="text-sm font-bold text-ink">Independent Live Re-crawl Verification</h4>
                </div>
                <p className="text-xs text-ink-500 leading-relaxed">
                  Marking a task complete does not verify it. Triggering verification sends an SSRF-checked backend re-crawl to{' '}
                  <code>{affectedUrls[0] || 'target URL'}</code> and evaluates deterministic acceptance criteria before transitioning to <code>VERIFIED_FIXED</code>.
                </p>

                <Button size="sm" onClick={handleTriggerVerification} disabled={isVerifying} className="text-xs">
                  {isVerifying ? (
                    <><Clock className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Re-crawling Live URL...</>
                  ) : (
                    <><Play className="w-3.5 h-3.5 mr-1.5" /> Execute Re-crawl Verification</>
                  )}
                </Button>

                {verifError && (
                  <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center gap-2 text-xs text-rose-800">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
                    <span>{verifError}</span>
                  </div>
                )}

                {verifResult && (
                  <div className="space-y-3">
                    <div
                      className={`p-3 rounded-lg border flex items-center gap-2 text-xs ${
                        verifResult.passed
                          ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                          : 'bg-amber-50 border-amber-200 text-amber-800'
                      }`}
                    >
                      {verifResult.passed ? <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />}
                      <span>
                        <strong>{verifResult.verification_status}:</strong> {verifResult.check_summary}
                      </span>
                    </div>

                    {verifResult.comparison_rows.length > 0 && (
                      <table className="w-full text-left text-xs border border-line rounded-lg overflow-hidden">
                        <thead>
                          <tr className="bg-paper border-b border-line text-[10px] uppercase text-ink-400">
                            <th className="p-2">Dimension</th>
                            <th className="p-2">Before</th>
                            <th className="p-2">After (Live)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-line font-mono text-[11px]">
                          {verifResult.comparison_rows.map((row) => (
                            <tr key={row.dimension}>
                              <td className="p-2 font-sans font-semibold text-ink">{row.dimension}</td>
                              <td className="p-2 text-ink-500">{row.before}</td>
                              <td className="p-2 text-ink">{row.after}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-line bg-paper-subtle flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-ink-500">Lifecycle State:</span>
            <select
              value={currentStatus}
              onChange={(e) => onUpdateStatus?.(finding.finding_id, e.target.value)}
              className="py-1 px-2 text-xs rounded border border-line bg-paper text-ink"
            >
              <option value="VERIFIED">VERIFIED</option>
              <option value="PRIORITIZED">PRIORITIZED</option>
              <option value="REMEDIATION_PLANNED">REMEDIATION_PLANNED</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="FIX_SUBMITTED">FIX_SUBMITTED</option>
              <option value="ACCEPTED_RISK">ACCEPTED_RISK</option>
              <option value="DEFERRED">DEFERRED</option>
              <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              {currentStatus === 'VERIFIED_FIXED' && <option value="VERIFIED_FIXED">VERIFIED_FIXED</option>}
            </select>
          </div>
          <Button size="sm" variant="secondary" onClick={onClose} className="text-xs">Close</Button>
        </div>
      </div>
    </div>
  );
}
