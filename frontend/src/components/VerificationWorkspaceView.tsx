import React from 'react';
import { ExecutiveReport } from '../types';
import { VerificationProofCard } from './VerificationProofCard';
import { RegressionDetectionView } from './RegressionDetectionView';
import { ComparativeEvidenceMatrix } from './ComparativeEvidenceMatrix';
import { Card } from './ui';
import { ShieldCheck, RefreshCw, CheckCircle2, History } from 'lucide-react';

interface VerificationWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
}

export function VerificationWorkspaceView({ report, analysisId }: VerificationWorkspaceViewProps) {
  const verifiedFindings = (report.findings || []).filter(
    (f) => f.remediation_verification || f.verification_status === 'VERIFIED'
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-line pb-4">
        <span className="text-[10px] font-mono uppercase tracking-widest text-pine font-bold block">
          Remediation & Quality Assurance
        </span>
        <h2 className="font-serif text-3xl text-ink font-semibold">Verification & Regression Testing</h2>
        <p className="text-xs text-ink-500 mt-1">
          Cryptographically sealed DOM evidence verification and automated regression testing loop.
        </p>
      </div>

      {/* Verification Pipeline Stages */}
      <Card className="p-5 space-y-4">
        <h3 className="font-serif text-lg text-ink font-semibold">Remediation Verification Loop</h3>
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 text-xs">
          {[
            { step: '1. FIX', desc: 'Apply developer patch', done: true },
            { step: '2. RECRAWL', desc: 'Deterministic re-fetch', done: true },
            { step: '3. RECHECK', desc: 'Rule selector re-eval', done: true },
            { step: '4. COMPARE', desc: 'Diff before vs after', done: true },
            { step: '5. CERTIFY', desc: 'Seal evidence integrity', done: true },
          ].map((s, i) => (
            <div key={i} className="p-3 rounded bg-paper-50 border border-line space-y-1">
              <span className="font-mono font-bold text-pine text-[11px] block">{s.step}</span>
              <p className="text-ink-600 text-[11px]">{s.desc}</p>
              <span className="text-[10px] text-good font-semibold flex items-center gap-1 pt-1">
                <CheckCircle2 className="w-3 h-3" /> Active
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* Regression Detection */}
      {report.regression_report && (
        <RegressionDetectionView report={report} />
      )}

      {/* Comparative Benchmark — Pending Competitor Crawl */}
      <ComparativeEvidenceMatrix
        targetDomain={report.domain}
        manifest={report.crawl_manifest}
        pages={report.crawl_manifest?.pages}
        report={report}
      />

      {/* Sample Verified Evidence Cards */}
      {verifiedFindings.length > 0 && (
        <div className="space-y-4">
          <h3 className="font-serif text-lg text-ink font-semibold">Certified Verification Proofs</h3>
          <div className="space-y-4">
            {verifiedFindings.slice(0, 3).map((f) => (
              <VerificationProofCard key={f.finding_id} finding={f} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
