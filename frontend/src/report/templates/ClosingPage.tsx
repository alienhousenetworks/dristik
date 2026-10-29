import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { PublicationManifest } from '../adaptivePublication';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface ClosingPageProps {
  theme: ReportTheme;
  report: NormalizedReport;
  manifest: PublicationManifest;
  pageNumber?: string | number;
}

export function ClosingPage({
  theme,
  report,
  manifest,
  pageNumber,
}: ClosingPageProps) {
  const { meta } = report;

  return (
    <section
      data-chapter-id="closing_page"
      className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-4 border-ink text-ink relative"
    >
      <PageHeader
        theme={theme}
        domain={meta.domain}
        chapterTitle="AUDIT CONCLUSION // INDEPENDENT ASSURANCE SEAL"
      />

      <div className="my-auto space-y-8 max-w-4xl py-6">
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Audit Conclusion &amp; Governance Attestation
          </span>
          <h2 className="font-serif text-[26pt] md:text-[32pt] font-normal tracking-tight text-ink">
            Certified Digital Intelligence Dossier
          </h2>
          <div className="bg-ink w-12 h-px mt-3" />
        </div>

        {/* Lead Attestation */}
        <div className="p-5 rounded bg-paper-100 border-2 border-line space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-line">
            <span className="font-mono text-[8.5pt] font-bold uppercase text-ink-800">
              ZERO-FAKE EVIDENCE GOVERNANCE SEAL
            </span>
            <span className="font-mono text-[7.5pt] font-bold px-2 py-0.5 rounded bg-good/10 text-good border border-good/30">
              AUDIT CERTIFIED
            </span>
          </div>
          <p className="font-sans text-[9pt] leading-relaxed text-ink-700">
            This dossier was compiled deterministically from live DOM AST traversals, network response header telemetry, and multi-model query evaluations conducted against <strong>{meta.domain}</strong>. No synthetic competitors, hallucinated performance statistics, or speculative ranking promises have been introduced.
          </p>
        </div>

        {/* Verification & Reproduction Instructions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[8pt]">
          <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
            <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700 block">
              01 // DEFECT REPRODUCTION &amp; PATCH APPLICATION
            </span>
            <p className="text-ink-600 font-sans leading-relaxed">
              Every identified defect is paired with a machine-verifiable code patch or configuration directive in Appendix B. Engineering teams can test and apply proposed patches in staging environments before production release.
            </p>
          </div>

          <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
            <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700 block">
              02 // CLOSED-LOOP RE-VERIFICATION
            </span>
            <p className="text-ink-600 font-sans leading-relaxed">
              Upon remediation deployment, initiate an automated regression re-crawl via the Dristik API to verify defect resolution against historical AST snapshots and update citation index telemetry.
            </p>
          </div>
        </div>

        {/* Audit Sign-off Block */}
        <div className="border-t border-b border-line py-4 grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-[7.5pt]">
          <div>
            <span className="text-ink-400 block uppercase">Prepared By</span>
            <span className="font-bold text-ink">Dristik Advisory Systems</span>
          </div>
          <div>
            <span className="text-ink-400 block uppercase">Report Reference</span>
            <span className="font-bold text-ink">{manifest.reportRef}</span>
          </div>
          <div>
            <span className="text-ink-400 block uppercase">Execution Date</span>
            <span className="font-bold text-ink">{manifest.auditDate}</span>
          </div>
          <div>
            <span className="text-ink-400 block uppercase">Classification</span>
            <span className="font-bold text-ink">{manifest.classification}</span>
          </div>
        </div>

        {/* Legal Disclaimer & Confidentiality Notice */}
        <div className="text-[7pt] font-mono text-ink-400 leading-normal space-y-1">
          <p>
            CONFIDENTIALITY NOTICE: The information contained in this digital publication is intended solely for the use of {meta.brandName} and designated authorized personnel. Unauthorized distribution, copying, or disclosure is strictly prohibited.
          </p>
          <p>
            MEASUREMENT LIMITATIONS: Observations reflect digital property conditions during the stated crawl window. Search engine algorithms and AI model outputs operate non-deterministically; past performance does not guarantee future indexing position.
          </p>
        </div>
      </div>

      <PageFooter
        theme={theme}
        domain={meta.domain}
        pageNumber={pageNumber}
        reportId={meta.analysisId}
        dateStr={meta.generatedAt}
      />
    </section>
  );
}
