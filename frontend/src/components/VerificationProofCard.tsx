import React from 'react';
import { Finding, RemediationVerificationReport } from '../types';

interface VerificationProofCardProps {
  finding?: Finding;
  report?: RemediationVerificationReport;
  websiteUrl?: string;
  compact?: boolean;
}

export function VerificationProofCard({
  finding,
  report: explicitReport,
  websiteUrl,
  compact = false,
}: VerificationProofCardProps) {
  const report = explicitReport || finding?.remediation_verification;
  const isVerified = report?.status === 'RESOLVED';
  const checks = report?.checks || [];
  const passedCount = report?.passed_checks_count ?? checks.filter((c) => c.passed).length;
  const totalCount = report?.total_checks_count ?? checks.length;
  const targetUrl = report?.target_url || websiteUrl || 'Target Surface';

  if (!report && !finding) {
    return null;
  }

  const seal = report?.evidence_seal || 'No evidence seal recorded';
  const verifiedAt = report?.verified_at ? new Date(report.verified_at).toLocaleString() : 'Pending Live Run';
  const measuredDelta = report?.score_delta_is_measured === true && typeof report.score_delta === 'number';

  return (
    <div
      className={`border rounded-lg font-sans transition-all overflow-hidden ${
        isVerified
          ? 'bg-good/10 border-good/30 text-ink-900 shadow-xs'
          : 'bg-paper-100 border-line text-ink-700'
      } ${compact ? 'p-3' : 'p-5'}`}
    >
      {/* Header Badge & Title */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2">
          <span
            className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-[0.04em] ${
              isVerified
                ? 'bg-good/10 text-white shadow-xs'
                : 'bg-paper-200 text-ink-700'
            }`}
          >
            {isVerified ? 'Technical condition resolved' : 'Verification pending'}
          </span>
          {finding?.finding_id && (
            <span className="font-mono text-xs text-ink-500">
              Finding: <strong className="text-ink-900">{finding.finding_id}</strong>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px]">
          {measuredDelta && (
            <span className="font-bold text-ink bg-paper-100 px-2 py-0.5 rounded border border-line">
              Measured change {report?.score_delta}. Not an AI citation result.
            </span>
          )}
          <span className="text-ink-400 text-[10px]">
            {isVerified ? `Timestamp: ${verifiedAt}` : 'Awaiting re-crawl verification'}
          </span>
        </div>
      </div>

      {/* Main Issue / Verification Narrative */}
      <div className="mt-3">
        <h4 className="text-sm font-bold text-ink-900">
          {finding?.title || 'Remediation Proof Certificate'}
        </h4>
        <p className="text-xs text-ink-600 mt-1 font-mono truncate">
          Target: <span className="text-ink-700">{targetUrl}</span>
        </p>
      </div>

      {/* Before vs After Cryptographic Proof Box */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 text-xs font-mono">
        {/* BEFORE BOX */}
        <div className="p-3 bg-bad/10 border border-bad/30 rounded">
          <div className="flex items-center justify-between font-bold text-bad mb-1.5 pb-1 border-b border-bad/30">
            <span className="flex items-center gap-1.5">
              <span></span>
              <span>BEFORE (AUDIT BASELINE)</span>
            </span>
            <span className="text-[10px] text-bad uppercase">Recorded condition</span>
          </div>
          <p className="text-bad font-sans text-xs mb-2 leading-relaxed">
            {report?.before_state || finding?.description || 'Detected non-compliant configuration.'}
          </p>
          <div className="text-[10px] text-bad truncate pt-1 border-t border-bad/30">
            Status: Initial audit detection
          </div>
        </div>

        {/* AFTER BOX */}
        <div className={`p-3 border rounded ${isVerified ? 'bg-good/10 border-good/30' : 'bg-paper-200 border-line'}`}>
          <div className={`flex items-center justify-between font-bold mb-1.5 pb-1 border-b ${isVerified ? 'text-good border-good/30' : 'text-ink-700 border-line'}`}>
            <span className="flex items-center gap-1.5">
              <span>{isVerified ? '✓' : '○'}</span>
              <span>AFTER (LIVE VERIFICATION)</span>
            </span>
            <span className={`text-[10px] uppercase font-bold ${isVerified ? 'text-good' : 'text-ink-500'}`}>
              {isVerified ? 'VERIFIED PASS' : 'NOT VERIFIED'}
            </span>
          </div>
          <p className={`font-sans text-xs mb-2 leading-relaxed ${isVerified ? 'text-good' : 'text-ink-700'}`}>
            {report?.after_state || (isVerified ? 'All checks successfully verified via live recrawl.' : 'Awaiting developer patch deployment.')}
          </p>
          <div className={`text-[10px] truncate pt-1 border-t ${isVerified ? 'text-good border-good/30' : 'text-ink-500 border-line'}`}>
            Passed: {passedCount}/{totalCount} Deterministic Assertions
          </div>
        </div>
      </div>

      {/* Assertion Checklist */}
      {checks.length > 0 && (
        <div className="mt-4 pt-3 border-t border-line/60">
          <p className="text-[11px] font-bold text-ink-700 uppercase tracking-[0.04em] font-mono mb-2">
            Deterministic Verification Assertions ({passedCount}/{totalCount})
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {checks.map((chk, idx) => (
              <div
                key={idx}
                className={`p-2 rounded border flex items-start gap-2 ${
                  chk.passed
                    ? 'bg-good/10 border-good/30 text-good'
                    : 'bg-bad/10 border-bad/30 text-bad'
                }`}
              >
                <span className="font-bold text-xs mt-0.5">
                  {chk.passed ? '✓' : '✕'}
                </span>
                <div className="min-w-0">
                  <p className="font-bold font-mono text-[11px] truncate">{chk.name}</p>
                  <p className="text-[10px] text-ink-600 leading-tight mt-0.5">{chk.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(report?.technical_verification || report?.verification_scope_note) && (
        <p className="mt-4 text-[11px] text-ink-600 leading-relaxed">
          Technical: {report.technical_verification || 'not recorded'}.
          {' '}Visibility: {report.visibility_verification || 'not measured'}.
          {' '}Business: {report.business_verification || 'not measured'}.
          {report.verification_scope_note ? ` ${report.verification_scope_note}` : ''}
        </p>
      )}

      {/* Evidence seal footer */}
      <div className="mt-4 pt-3 border-t border-line/60 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-ink-500">
        <div className="flex items-center gap-1.5 truncate max-w-full">
          <span className="text-ink-400">EVIDENCE SEAL:</span>
          <span className="font-bold text-ink-700 bg-paper-50 px-1.5 py-0.5 border border-line rounded truncate">
            {seal}
          </span>
        </div>
        <span>
          Recorded by: <strong className="text-ink-700">{report?.certified_by || 'Dristik verification record'}</strong>
        </span>
      </div>
    </div>
  );
}
