import React, { useState } from 'react';
import { Finding, RemediationVerificationReport, VerificationCheckItem } from '../types';

interface RemediationVerificationLoopProps {
  finding: Finding;
  websiteUrl: string;
  analysisId?: string;
  onVerificationComplete?: (report: RemediationVerificationReport) => void;
  inline?: boolean;
}

export function RemediationVerificationLoop({
  finding,
  websiteUrl,
  analysisId,
  onVerificationComplete,
  inline = false,
}: RemediationVerificationLoopProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [activeStage, setActiveStage] = useState<'IDLE' | 'FIX' | 'RECRAWL' | 'RECHECK' | 'COMPARE' | 'CERTIFY'>(
    finding.remediation_verification?.stage as any || (finding.resolution_status === 'RESOLVED' ? 'CERTIFY' : 'IDLE')
  );
  const [verificationReport, setVerificationReport] = useState<RemediationVerificationReport | null>(
    finding.remediation_verification || null
  );
  const [error, setError] = useState<string | null>(null);

  const stages = [
    { key: 'FIX', label: '1. Fix Applied', desc: 'Remediation patch ready' },
    { key: 'RECRAWL', label: '2. Live Recrawl', desc: 'Live DOM & target re-fetch' },
    { key: 'RECHECK', label: '3. Recheck', desc: 'Deterministic assertions' },
    { key: 'COMPARE', label: '4. Compare', desc: 'Before vs After delta' },
    { key: 'CERTIFY', label: '5. Certify', desc: 'Cryptographic SHA-256 seal' },
  ];

  const handleRunLoop = async () => {
    setIsRunning(true);
    setError(null);
    setActiveStage('RECRAWL');

    try {
      // Direct live API call to execute real recrawl and deterministic assertions
      const res = await fetch('/api/v1/remediation/verify-finding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          finding_id: finding.finding_id,
          analysis_id: analysisId,
          website_url: websiteUrl,
          target_url: websiteUrl,
          finding_title: finding.title,
          finding_category: finding.category,
          finding_text: finding.finding || finding.title,
          finding_description: finding.description,
          finding_recommendation: finding.recommendation,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Verification call failed (HTTP ${res.status})`);
      }

      const report: RemediationVerificationReport = await res.json();

      // Truthful stage and status derived strictly from actual server verification
      setActiveStage(report.stage as any || (report.status === 'RESOLVED' ? 'CERTIFY' : 'RECHECK'));
      setVerificationReport(report);
      finding.remediation_verification = report;
      finding.resolution_status = report.status;
      onVerificationComplete?.(report);
    } catch (e: any) {
      setError(e?.message || 'Verification loop encountered an error.');
      setActiveStage('IDLE');
    } finally {
      setIsRunning(false);
    }
  };

  const isResolved = verificationReport?.status === 'RESOLVED';
  const isFailed = verificationReport && !isResolved;

  return (
    <div className={`space-y-4 font-sans ${inline ? 'p-3 bg-slate-50 border border-slate-200 rounded' : 'p-5 bg-white border border-slate-300 rounded shadow-xs'}`}>
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-blue-900 bg-blue-50 px-2 py-0.5 border border-blue-200 rounded">
              Continuous Website Assurance
            </span>
            <span className="font-mono text-xs text-slate-500">
              Finding ID: <strong className="text-slate-900">{finding.finding_id}</strong>
            </span>
          </div>
          <h4 className="text-base font-bold text-slate-900 mt-1">
            Automatic Remediation Verification Loop
          </h4>
          <p className="text-xs text-slate-600 mt-0.5">
            Fix &rarr; Recrawl &rarr; Recheck &rarr; Compare &rarr; Certify · <em>Real live HTTP &amp; DOM assertion test</em>
          </p>
        </div>

        <button
          type="button"
          disabled={isRunning}
          onClick={handleRunLoop}
          className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all shadow-xs flex items-center gap-2 cursor-pointer ${
            isRunning
              ? 'bg-slate-200 text-slate-500 cursor-not-allowed'
              : isResolved
              ? 'bg-emerald-700 hover:bg-emerald-800 text-white'
              : isFailed
              ? 'bg-amber-700 hover:bg-amber-800 text-white'
              : 'bg-blue-950 hover:bg-blue-900 text-white'
          }`}
        >
          {isRunning ? (
            <>
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
              <span>Recrawling &amp; Testing Live Host...</span>
            </>
          ) : isResolved ? (
            <>
              <span>✓ Certified Resolved (Re-verify live)</span>
            </>
          ) : isFailed ? (
            <>
              <span>⚠️ Unresolved (Retry Live Verification)</span>
            </>
          ) : (
            <>
              <span>⚡ Trigger Live Verification</span>
            </>
          )}
        </button>
      </div>

      {/* 5-Stage Stepper Ribbon */}
      <div className="grid grid-cols-5 gap-1.5 font-mono text-[10px]">
        {stages.map((st, idx) => {
          const isCurrent = activeStage === st.key;
          const isPassed =
            isResolved ||
            (activeStage === 'CERTIFY' && isResolved) ||
            (activeStage === 'COMPARE' && idx < 3) ||
            (activeStage === 'RECHECK' && idx < 2) ||
            (activeStage === 'RECRAWL' && idx < 1);

          return (
            <div
              key={st.key}
              className={`p-2 rounded border transition-colors ${
                isCurrent
                  ? 'bg-blue-100 border-blue-400 text-blue-950 font-bold shadow-xs'
                  : isPassed
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                  : isFailed && isCurrent
                  ? 'bg-red-50 border-red-300 text-red-900'
                  : 'bg-slate-50 border-slate-200 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span>{st.label}</span>
                {isPassed && <span className="text-emerald-700 font-bold">✓</span>}
              </div>
              <span className="text-[9px] text-slate-500 hidden sm:block truncate mt-0.5">
                {st.desc}
              </span>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-xs text-red-700 rounded font-mono">
          ✕ {error}
        </div>
      )}

      {/* Before vs After Comparison Matrix */}
      {verificationReport ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Before Box */}
            <div className="p-3.5 bg-red-50/40 border border-red-200 rounded space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-red-900">
                  Before (Audit Baseline)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-100 text-red-800 font-bold border border-red-200">
                  FAILS COMPLIANCE
                </span>
              </div>
              <p className="text-xs text-red-950 font-medium whitespace-pre-line leading-relaxed">
                {verificationReport.before_state}
              </p>
              <div className="pt-2 border-t border-red-100 text-[11px] text-red-700 font-mono">
                Initial Detection: Recorded during primary crawl
              </div>
            </div>

            {/* After Box */}
            <div className={`p-3.5 rounded space-y-2 border ${
              isResolved
                ? 'bg-emerald-50/50 border-emerald-300'
                : 'bg-amber-50/50 border-amber-300'
            }`}>
              <div className="flex items-center justify-between">
                <span className={`font-mono text-[10px] font-bold uppercase tracking-wider ${
                  isResolved ? 'text-emerald-900' : 'text-amber-900'
                }`}>
                  After (Live Verification)
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                  isResolved
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : 'bg-amber-100 text-amber-900 border-amber-300'
                }`}>
                  {verificationReport.status}
                </span>
              </div>

              {/* Real Recrawl Telemetry Strip */}
              {(verificationReport.recrawl_status_code != null || verificationReport.recrawl_ttfb_ms != null) && (
                <div className="flex flex-wrap gap-2 text-[10px] font-mono p-1.5 bg-white/70 rounded border border-slate-200 text-slate-700">
                  {verificationReport.recrawl_status_code != null && (
                    <span>HTTP Status: <strong className={verificationReport.recrawl_status_code === 200 ? 'text-emerald-700' : 'text-red-700'}>{verificationReport.recrawl_status_code}</strong></span>
                  )}
                  {verificationReport.recrawl_ttfb_ms != null && (
                    <span>· TTFB: <strong>{verificationReport.recrawl_ttfb_ms}ms</strong></span>
                  )}
                  {verificationReport.recrawl_content_type && (
                    <span>· Type: <span className="text-slate-500">{verificationReport.recrawl_content_type.split(';')[0]}</span></span>
                  )}
                </div>
              )}

              {/* Checklist assertions with real pass/fail indicators */}
              <div className="space-y-1.5 pt-1">
                {verificationReport.checks.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    {c.passed ? (
                      <span className="text-emerald-700 font-bold text-sm leading-none">✓</span>
                    ) : (
                      <span className="text-red-600 font-bold text-sm leading-none">✕</span>
                    )}
                    <div>
                      <span className={`font-semibold ${c.passed ? 'text-slate-900' : 'text-red-900'}`}>
                        {c.name}
                      </span>
                      <p className={`text-[11px] font-mono ${c.passed ? 'text-slate-600' : 'text-red-700'}`}>
                        {c.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Certificate / Verification Summary Badge */}
          <div className="p-3 bg-slate-900 text-white rounded flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
            <div className="flex items-center gap-3">
              <span className="text-base text-emerald-400">
                {isResolved ? '🛡️' : '⚠️'}
              </span>
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  Verification Verdict &amp; Impact
                </span>
                <div className="flex items-center gap-2">
                  <span className={`font-bold text-sm ${isResolved ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {verificationReport.status}
                  </span>
                  {isResolved && verificationReport.score_delta ? (
                    <span className="text-emerald-300 text-[11px] font-bold">
                      (+{verificationReport.score_delta} pts recovered)
                    </span>
                  ) : (
                    <span className="text-slate-400 text-[11px]">
                      ({verificationReport.passed_checks_count ?? 0}/{verificationReport.total_checks_count ?? 0} assertions met)
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="text-right text-[11px] text-slate-300">
              <div>
                Evidence Seal:{' '}
                <strong className="text-amber-300">{verificationReport.evidence_seal}</strong>
              </div>
              <div className="text-[10px] text-slate-400">
                Tested against {websiteUrl} · {verificationReport.certified_by || 'Dristik Continuous Assurance'}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-6 border border-dashed border-slate-300 rounded text-center space-y-2 bg-slate-50/50">
          <p className="text-xs font-mono text-slate-600">
            Remediation verification has not yet been executed for this finding.
          </p>
          <p className="text-[11px] text-slate-500 max-w-md mx-auto">
            Once a developer deploys the fix, click <strong>"Trigger Live Verification"</strong> above to recrawl the live target URL and verify assertions in real time.
          </p>
        </div>
      )}
    </div>
  );
}
