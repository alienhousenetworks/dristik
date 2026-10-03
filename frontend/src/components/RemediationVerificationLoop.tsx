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
    <div className={`space-y-4 font-sans ${inline ? 'p-3 bg-paper-100 border border-line rounded' : 'p-5 bg-paper-50 border border-line rounded shadow-xs'}`}>
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.04em] text-ink-700 bg-paper-100 px-2 py-0.5 border border-line rounded">
              Continuous Website Assurance
            </span>
            <span className="font-mono text-xs text-ink-500">
              Finding ID: <strong className="text-ink">{finding.finding_id}</strong>
            </span>
          </div>
          <h4 className="text-base font-bold text-ink mt-1">
            Automatic Remediation Verification Loop
          </h4>
          <p className="text-xs text-ink-600 mt-0.5">
            Fix &rarr; Recrawl &rarr; Recheck &rarr; Compare &rarr; Certify · <em>Real live HTTP &amp; DOM assertion test</em>
          </p>
        </div>

        <button
          type="button"
          disabled={isRunning}
          onClick={handleRunLoop}
          className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all shadow-xs flex items-center gap-2 cursor-pointer ${
            isRunning
              ? 'bg-paper-200 text-ink-500 cursor-not-allowed'
              : isResolved
              ? 'bg-good/10 hover:bg-good/10 text-white'
              : isFailed
              ? 'bg-warn/10 hover:bg-warn/10 text-white'
              : 'bg-paper-100 hover:bg-paper-100 text-white'
          }`}
        >
          {isRunning ? (
            <>
              <span className="w-2 h-2 rounded-full bg-paper-100 animate-ping" />
              <span>Recrawling &amp; Testing Live Host...</span>
            </>
          ) : isResolved ? (
            <>
              <span>✓ Certified Resolved (Re-verify live)</span>
            </>
          ) : isFailed ? (
            <>
              <span> Unresolved (Retry Live Verification)</span>
            </>
          ) : (
            <>
              <span> Trigger Live Verification</span>
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
                  ? 'bg-paper-100 border-line text-ink-700 font-bold shadow-xs'
                  : isPassed
                  ? 'bg-good/10 border-good/30 text-good'
                  : isFailed && isCurrent
                  ? 'bg-bad/10 border-bad/30 text-bad'
                  : 'bg-paper-100 border-line text-ink-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span>{st.label}</span>
                {isPassed && <span className="text-good font-bold">✓</span>}
              </div>
              <span className="text-[9px] text-ink-500 hidden sm:block truncate mt-0.5">
                {st.desc}
              </span>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="p-3 bg-bad/10 border border-bad/30 text-xs text-bad rounded font-mono">
          ✕ {error}
        </div>
      )}

      {/* Before vs After Comparison Matrix */}
      {verificationReport ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Before Box */}
            <div className="p-3.5 bg-bad/10 border border-bad/30 rounded space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.04em] text-bad">
                  Before (Audit Baseline)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bad/10 text-bad font-bold border border-bad/30">
                  FAILS COMPLIANCE
                </span>
              </div>
              <p className="text-xs text-bad font-medium whitespace-pre-line leading-relaxed">
                {verificationReport.before_state}
              </p>
              <div className="pt-2 border-t border-bad/30 text-[11px] text-bad font-mono">
                Initial Detection: Recorded during primary crawl
              </div>
            </div>

            {/* After Box */}
            <div className={`p-3.5 rounded space-y-2 border ${
              isResolved
                ? 'bg-good/10 border-good/30'
                : 'bg-warn/10 border-warn/30'
            }`}>
              <div className="flex items-center justify-between">
                <span className={`font-mono text-[10px] font-bold uppercase tracking-[0.04em] ${
                  isResolved ? 'text-good' : 'text-warn'
                }`}>
                  After (Live Verification)
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                  isResolved
                    ? 'bg-good/10 text-good border-good/30'
                    : 'bg-warn/10 text-warn border-warn/30'
                }`}>
                  {verificationReport.status}
                </span>
              </div>

              {/* Real Recrawl Telemetry Strip */}
              {(verificationReport.recrawl_status_code != null || verificationReport.recrawl_ttfb_ms != null) && (
                <div className="flex flex-wrap gap-2 text-[10px] font-mono p-1.5 bg-paper-50/70 rounded border border-line text-ink-700">
                  {verificationReport.recrawl_status_code != null && (
                    <span>HTTP Status: <strong className={verificationReport.recrawl_status_code === 200 ? 'text-good' : 'text-bad'}>{verificationReport.recrawl_status_code}</strong></span>
                  )}
                  {verificationReport.recrawl_ttfb_ms != null && (
                    <span>· TTFB: <strong>{verificationReport.recrawl_ttfb_ms}ms</strong></span>
                  )}
                  {verificationReport.recrawl_content_type && (
                    <span>· Type: <span className="text-ink-500">{verificationReport.recrawl_content_type.split(';')[0]}</span></span>
                  )}
                </div>
              )}

              {/* Checklist assertions with real pass/fail indicators */}
              <div className="space-y-1.5 pt-1">
                {verificationReport.checks.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    {c.passed ? (
                      <span className="text-good font-bold text-sm leading-none">✓</span>
                    ) : (
                      <span className="text-bad font-bold text-sm leading-none">✕</span>
                    )}
                    <div>
                      <span className={`font-semibold ${c.passed ? 'text-ink' : 'text-bad'}`}>
                        {c.name}
                      </span>
                      <p className={`text-[11px] font-mono ${c.passed ? 'text-ink-600' : 'text-bad'}`}>
                        {c.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Certificate / Verification Summary Badge */}
          <div className="p-3 bg-ink text-white rounded flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
            <div className="flex items-center gap-3">
              <span className="text-base text-good">
                {isResolved ? '' : ''}
              </span>
              <div>
                <span className="text-[10px] text-ink-400 uppercase tracking-[0.04em] block">
                  Verification Verdict &amp; Impact
                </span>
                <div className="flex items-center gap-2">
                  <span className={`font-bold text-sm ${isResolved ? 'text-good' : 'text-warn'}`}>
                    {verificationReport.status}
                  </span>
                  {isResolved && verificationReport.score_delta ? (
                    <span className="text-good text-[11px] font-bold">
                      (+{verificationReport.score_delta} pts recovered)
                    </span>
                  ) : (
                    <span className="text-ink-400 text-[11px]">
                      ({verificationReport.passed_checks_count ?? 0}/{verificationReport.total_checks_count ?? 0} assertions met)
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="text-right text-[11px] text-ink-300">
              <div>
                Evidence Seal:{' '}
                <strong className="text-warn">{verificationReport.evidence_seal}</strong>
              </div>
              <div className="text-[10px] text-ink-400">
                Tested against {websiteUrl} · {verificationReport.certified_by || 'Dristik Continuous Assurance'}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-6 border border-dashed border-line rounded text-center space-y-2 bg-paper-100">
          <p className="text-xs font-mono text-ink-600">
            Remediation verification has not yet been executed for this finding.
          </p>
          <p className="text-[11px] text-ink-500 max-w-md mx-auto">
            Once a developer deploys the fix, click <strong>"Trigger Live Verification"</strong> above to recrawl the live target URL and verify assertions in real time.
          </p>
        </div>
      )}
    </div>
  );
}
