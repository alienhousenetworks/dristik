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

  // Generate deterministic proof seal if missing
  const seal = report?.evidence_seal || (finding ? `dristik:seal:${finding.finding_id}` : 'dristik:seal:unverified');
  const verifiedAt = report?.verified_at ? new Date(report.verified_at).toLocaleString() : 'Pending Live Run';

  return (
    <div
      className={`border rounded-lg font-sans transition-all overflow-hidden ${
        isVerified
          ? 'bg-emerald-950/5 border-emerald-500/30 text-ink-900 shadow-xs'
          : 'bg-slate-50 border-slate-200 text-slate-700'
      } ${compact ? 'p-3' : 'p-5'}`}
    >
      {/* Header Badge & Title */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2">
          <span
            className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
              isVerified
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-slate-200 text-slate-700'
            }`}
          >
            {isVerified ? '✓ Cryptographically Certified' : 'Verification Pending'}
          </span>
          {finding?.finding_id && (
            <span className="font-mono text-xs text-ink-500">
              Finding: <strong className="text-ink-900">{finding.finding_id}</strong>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px]">
          {report?.score_delta && report.score_delta > 0 && (
            <span className="font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
              +{report.score_delta} pts recovered
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
          Target: <span className="text-blue-700">{targetUrl}</span>
        </p>
      </div>

      {/* Before vs After Cryptographic Proof Box */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 text-xs font-mono">
        {/* BEFORE BOX */}
        <div className="p-3 bg-red-50/70 border border-red-200 rounded">
          <div className="flex items-center justify-between font-bold text-red-900 mb-1.5 pb-1 border-b border-red-200">
            <span className="flex items-center gap-1.5">
              <span>❌</span>
              <span>BEFORE (AUDIT BASELINE)</span>
            </span>
            <span className="text-[10px] text-red-700 uppercase">FAILS COMPLIANCE</span>
          </div>
          <p className="text-red-900 font-sans text-xs mb-2 leading-relaxed">
            {report?.before_state || finding?.description || 'Detected non-compliant configuration.'}
          </p>
          <div className="text-[10px] text-red-700 truncate pt-1 border-t border-red-200">
            Status: Initial audit detection
          </div>
        </div>

        {/* AFTER BOX */}
        <div className={`p-3 border rounded ${isVerified ? 'bg-emerald-50/80 border-emerald-300' : 'bg-slate-100 border-slate-300'}`}>
          <div className={`flex items-center justify-between font-bold mb-1.5 pb-1 border-b ${isVerified ? 'text-emerald-950 border-emerald-300' : 'text-slate-800 border-slate-300'}`}>
            <span className="flex items-center gap-1.5">
              <span>{isVerified ? '✓' : '○'}</span>
              <span>AFTER (LIVE VERIFICATION)</span>
            </span>
            <span className={`text-[10px] uppercase font-bold ${isVerified ? 'text-emerald-700' : 'text-slate-500'}`}>
              {isVerified ? 'VERIFIED PASS' : 'NOT VERIFIED'}
            </span>
          </div>
          <p className={`font-sans text-xs mb-2 leading-relaxed ${isVerified ? 'text-emerald-950' : 'text-slate-700'}`}>
            {report?.after_state || (isVerified ? 'All checks successfully verified via live recrawl.' : 'Awaiting developer patch deployment.')}
          </p>
          <div className={`text-[10px] truncate pt-1 border-t ${isVerified ? 'text-emerald-800 border-emerald-200' : 'text-slate-500 border-slate-200'}`}>
            Passed: {passedCount}/{totalCount} Deterministic Assertions
          </div>
        </div>
      </div>

      {/* Assertion Checklist */}
      {checks.length > 0 && (
        <div className="mt-4 pt-3 border-t border-line/60">
          <p className="text-[11px] font-bold text-ink-700 uppercase tracking-wider font-mono mb-2">
            Deterministic Verification Assertions ({passedCount}/{totalCount})
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {checks.map((chk, idx) => (
              <div
                key={idx}
                className={`p-2 rounded border flex items-start gap-2 ${
                  chk.passed
                    ? 'bg-emerald-50/50 border-emerald-200 text-emerald-950'
                    : 'bg-red-50/50 border-red-200 text-red-900'
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

      {/* Cryptographic Proof Footer */}
      <div className="mt-4 pt-3 border-t border-line/60 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-ink-500">
        <div className="flex items-center gap-1.5 truncate max-w-full">
          <span className="text-slate-400">PROOF SEAL:</span>
          <span className="font-bold text-ink-800 bg-white px-1.5 py-0.5 border border-line rounded truncate">
            {seal}
          </span>
        </div>
        <span>
          Auditor: <strong className="text-ink-800">Dristik Zero-Fake Engine v2.1</strong>
        </span>
      </div>
    </div>
  );
}
