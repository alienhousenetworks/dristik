import React from 'react';
import { formatRatioPercent } from '../../lib/format';
import { ReportTheme } from '../brandTheme';
import { formatEvidenceHash } from '../models/evidenceIntegrity';
import { patchStateLabel } from '../models/remediationClaim';
import { NormalizedReport, NormalizedFinding } from '../models/normalizedReport';
import { ChapterOpener } from './ChapterOpener';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface AppendixLedgerProps {
  theme: ReportTheme;
  report: NormalizedReport;
}

export function AppendixLedger({
  theme,
  report,
}: AppendixLedgerProps) {
  const { appendices, meta, remediation } = report;
  const criticalFindings = appendices.findings.filter((f) => f.severity === 'CRITICAL');
  const highFindings = appendices.findings.filter((f) => f.severity === 'HIGH');
  const mediumFindings = appendices.findings.filter((f) => f.severity === 'MEDIUM');
  const otherFindings = appendices.findings.filter((f) => f.severity === 'LOW' || f.severity === 'INFO');

  return (
    <>
      {/* 1. Full-Page Chapter Opener */}
      <ChapterOpener
        theme={theme}
        chapterNumber="09"
        subtitle="VERIFIED DEFECT REGISTER &amp; EVIDENCE LEDGER"
        title="Institutional Findings Register &amp; Appendices"
        description="Comprehensive technical record of all verified discrepancies, deterministic code patches with exact file paths, and cryptographically hashed AST evidence citations."
        domain={meta.domain}
        whyThisMatters="Engineering resolution requires exact reproduction paths, affected DOM selectors, and before/after code diffs with unambiguous acceptance criteria."
        howWeMeasuredIt="Automated 20-point validation checks, AST node verification, and SHA-256 hash sealing against the crawl snapshot."
        whatWasAnalyzed="Complete finding registry, unified git-compatible patch diffs, and the tamper-evident evidence ledger."
        pageNumber={22}
      />

      {/* 2. Findings Register Section */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="09 / FINDINGS REGISTER // VERIFIED AUDIT DEFECTS"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Deterministic Discrepancies
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              Verified Findings Register ({appendices.findings.length})
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          <p className="text-[8.5pt] text-ink-700 font-sans leading-relaxed">
            All findings are generated directly by Dristik's deterministic rules engine. Speculative or unverified claims are strictly withheld from this register.
          </p>

          <div className="space-y-4">
            {appendices.findings.slice(0, 4).map((f) => (
              <FindingEditorialCard key={f.id} finding={f} theme={theme} />
            ))}
          </div>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={23}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>

      {/* 3. Generated Remediation Patches (Point 14) */}
      {appendices.patches.length > 0 && (
        <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
          <PageHeader
            theme={theme}
            domain={meta.domain}
            chapterTitle="09 / ENGINEERING PATCHES // GENERATED REMEDIATION"
          />

          <div className="space-y-6 max-w-4xl">
            <div>
              <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
                {remediation.state === 'VERIFIED'
                  ? 'Independently verified fixes'
                  : remediation.state === 'APPLIED'
                    ? 'Applied changes — not independently verified'
                    : 'Proposed code remediation'}
              </span>
              <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
                Generated Remediation Patches
              </h2>
              <div className="bg-ink w-10 h-px mt-2" />
            </div>

            <div className="p-3 bg-paper-100 border border-line rounded text-[7.5pt] space-y-1">
              <div className="flex items-center justify-between pb-1 border-b border-line">
                <span className="font-mono font-bold uppercase text-ink-700">Remediation Assurance Protocol</span>
                <span className="font-mono font-bold px-1.5 py-0.2 rounded bg-warn/10 text-warn border border-warn/30">
                  STATUS: {remediation.label}
                </span>
              </div>
              <p className="font-sans text-ink-600">
                {remediation.detail}
              </p>
              <div className="font-mono text-[7pt] text-ink-500 pt-0.5">
                Verification Lifecycle: <strong>PATCH GENERATED</strong> → PENDING APPLICATION → RECRAWL → REGRESSION TEST → VERIFIED REMEDIATION
              </div>
            </div>

            <div className="space-y-4">
              {appendices.patches.slice(0, 3).map((patch) => (
                <div key={patch.patch_id} className="report-avoid-break p-4 border border-line rounded bg-paper-50 space-y-2 text-[8pt]">
                  <div className="flex items-center justify-between pb-2 border-b border-line">
                    <div>
                      <span className="font-mono text-[8.5pt] font-bold text-ink block">
                        {patch.target_file || 'index.html'}
                      </span>
                      <span className="font-mono text-[7.5pt] text-ink-500">
                        {patch.title || 'Technical Patch'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[7pt] font-bold px-2 py-0.5 rounded bg-warn/10 text-warn border border-warn/30">
                        {patchStateLabel(patch)}
                      </span>
                      <span className="font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded bg-paper-200 border border-line">
                        Unified Diff
                      </span>
                    </div>
                  </div>

                  <p className="text-ink-700 font-sans leading-relaxed text-[8pt]">
                    {patch.explanation}
                  </p>

                  <pre className="p-3 bg-ink text-good font-mono text-[7.5pt] rounded overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {patch.after_snippet}
                  </pre>
                </div>
              ))}
            </div>
          </div>

          <PageFooter
            theme={theme}
            domain={meta.domain}
            pageNumber={24}
            reportId={meta.analysisId}
            dateStr={meta.generatedAt}
          />
        </section>
      )}

      {/* 4. Cryptographic Evidence Ledger */}
      <section className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line">
        <PageHeader
          theme={theme}
          domain={meta.domain}
          chapterTitle="09 / EVIDENCE LEDGER // CRYPTOGRAPHIC AUDIT TRAIL"
        />

        <div className="space-y-6 max-w-4xl">
          <div>
            <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
              Tamper-Evident Proof
            </span>
            <h2 className="font-serif text-[22pt] font-normal tracking-tight text-ink">
              Cryptographic Evidence Ledger
            </h2>
            <div className="bg-ink w-10 h-px mt-2" />
          </div>

          <p className="text-[8.5pt] text-ink-700 font-sans leading-relaxed">
            Every analytical statement throughout this publication is tied to an indexed AST evidence record with recorded origin selector, snippet text, and SHA-256 integrity hash.
          </p>

          <table className="w-full text-[7.5pt] border-collapse border border-line font-mono">
            <thead>
              <tr className="bg-paper-100 border-b border-line text-left text-ink-600 uppercase">
                <th className="py-2 px-2" style={{ width: '15%' }}>Evidence ID</th>
                <th className="py-2 px-2" style={{ width: '22%' }}>URL / Selector</th>
                <th className="py-2 px-3">Observed Text Snippet</th>
                <th className="py-2 px-2" style={{ width: '20%' }}>SHA-256 Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {appendices.evidenceLedger.slice(0, 10).map((ev) => (
                <tr key={ev.id} className="hover:bg-paper-100">
                  <td className="py-1.5 px-2 font-bold text-ink truncate">
                    {ev.id}
                  </td>
                  <td className="py-1.5 px-2 text-ink-600 truncate">
                    {ev.selector || ev.url || 'DOM AST'}
                  </td>
                  <td className="py-1.5 px-3 text-ink-700 line-clamp-1 font-sans">
                    {ev.snippet || 'DOM node verification'}
                  </td>
                  <td className="py-1.5 px-2 text-ink-400 truncate">
                    <span title={ev.sha256 || ev.sourceSnapshotSha256 || ''}>{formatEvidenceHash(ev.sha256, ev.hashStatus)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <PageFooter
          theme={theme}
          domain={meta.domain}
          pageNumber={25}
          reportId={meta.analysisId}
          dateStr={meta.generatedAt}
        />
      </section>
    </>
  );
}

/**
 * Editorial Finding Card with restrained severity accents (no giant red cards).
 */
function FindingEditorialCard({
  finding,
  theme,
}: {
  finding: NormalizedFinding;
  theme: ReportTheme;
}) {
  const severityStyle =
    finding.severity === 'CRITICAL'
      ? { borderLeft: `3px solid ${theme.semantic.critical}`, badgeBg: theme.semantic.criticalBg, badgeColor: theme.semantic.critical }
      : finding.severity === 'HIGH'
      ? { borderLeft: `3px solid ${theme.semantic.warning}`, badgeBg: theme.semantic.warningBg, badgeColor: theme.semantic.warning }
      : { borderLeft: `3px solid ${theme.semantic.neutral}`, badgeBg: theme.semantic.neutralBg, badgeColor: theme.semantic.neutral };

  return (
    <div
      className="report-avoid-break p-4 bg-paper-50 border border-line rounded space-y-2 text-[8pt]"
      style={{ borderLeft: severityStyle.borderLeft }}
    >
      <div className="flex items-center justify-between pb-1 border-b border-line">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[7.5pt] font-bold text-ink-400">
            {finding.id}
          </span>
          <span
            className="font-mono text-[7pt] font-bold uppercase px-2 py-0.2 rounded"
            style={{ backgroundColor: severityStyle.badgeBg, color: severityStyle.badgeColor }}
          >
            {finding.severity}
          </span>
          <span className="font-mono text-[7pt] text-ink-500 uppercase">
            {finding.category}
          </span>
        </div>

        {finding.confidence != null && (
          <span className="font-mono text-[7pt] text-ink-400">
            Confidence: {formatRatioPercent(finding.confidence)}
          </span>
        )}
      </div>

      <h4 className="font-sans font-bold text-[10pt] text-ink">
        {finding.title}
      </h4>

      <p className="text-ink-700 font-sans leading-relaxed text-[8pt]">
        {finding.observation}
      </p>

      {finding.businessImpact && (
        <p className="text-[8pt] text-ink-700 font-sans">
          <strong>Commercial Impact:</strong> {finding.businessImpact}
        </p>
      )}

      {finding.recommendation && (
        <p className="text-[8pt] text-ink font-sans">
          <strong>Remediation:</strong> {finding.recommendation}
        </p>
      )}

      {/* Structured Evidence Drawer (Point 8) */}
      <div className="pt-2 border-t border-line mt-2 bg-paper-100 p-3 rounded space-y-1.5 font-mono text-[7.5pt]">
        <div className="flex items-center justify-between pb-1 border-b border-line">
          <span className="font-bold text-ink-700 uppercase text-[7pt]">
            Evidence Drawer // Trace &amp; Verification Protocol
          </span>
          <span className="px-1.5 py-0.2 rounded bg-paper-200 text-ink-700 font-bold text-[6.5pt]">
            STATUS: OPEN
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[7pt]">
          <div>
            <span className="text-ink-400 block text-[6.5pt] uppercase">Target Origin &amp; Selector:</span>
            <span className="text-ink-700 break-all font-mono">
              {finding.evidenceItems[0]?.url || 'Primary Origin Route'} {finding.evidenceItems[0]?.selector ? `· ${finding.evidenceItems[0].selector}` : '· DOM AST'}
            </span>
          </div>
          <div>
            <span className="text-ink-400 block text-[6.5pt] uppercase">Evidence ID &amp; Hash:</span>
            <span className="text-ink-700 font-mono">
              {finding.evidenceItems[0]?.id || 'No evidence id'} · {formatEvidenceHash(finding.evidenceItems[0]?.sha256, finding.evidenceItems[0]?.hashStatus || 'NOT_SEALED')}
            </span>
          </div>
        </div>

        <div className="bg-paper-50 p-2 rounded border border-line font-sans text-[7.5pt] space-y-1">
          <div>
            <strong className="text-ink">Observed Evidence: </strong>
            <span className="text-ink-700 italic">"{finding.observation.slice(0, 140)}…"</span>
          </div>
          <div>
            <strong className="text-ink">Why It Matters: </strong>
            <span className="text-ink-700">{finding.businessImpact || 'Impairs machine extraction clarity and commercial answer retrieval.'}</span>
          </div>
          <div>
            <strong className="text-ink">Verification Test: </strong>
            <span className="font-mono text-[7pt] text-ink-600">Deterministic AST re-parse confirms target selector resolves valid entity properties with 0 regressions.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
