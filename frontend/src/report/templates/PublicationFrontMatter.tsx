import React from 'react';
import { ReportTheme } from '../brandTheme';
import { NormalizedReport } from '../models/normalizedReport';
import { PublicationManifest } from '../adaptivePublication';
import { PageHeader, PageFooter } from './PageHeaderFooter';

interface PublicationFrontMatterProps {
  theme: ReportTheme;
  report: NormalizedReport;
  manifest: PublicationManifest;
  pageNumber?: string | number;
}

export function PublicationFrontMatter({
  theme,
  report,
  manifest,
  pageNumber = 'i',
}: PublicationFrontMatterProps) {
  const { meta, coverageConfidence } = report;

  return (
    <section
      data-chapter-id="front_matter_details"
      className="report-page-break p-8 md:p-14 min-h-[960px] flex flex-col justify-between bg-paper-50 border-b-2 border-line text-ink"
    >
      <PageHeader
        theme={theme}
        domain={meta.domain}
        chapterTitle="FRONT MATTER // DOCUMENT IDENTIFICATION & PROTOCOL"
      />

      <div className="space-y-6 max-w-4xl my-auto py-2">
        {/* Title */}
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Publication Metadata &amp; Reader Orientation
          </span>
          <h2 className="font-serif text-[24pt] md:text-[28pt] font-normal tracking-tight text-ink">
            Audit Identification &amp; Measurement Scope
          </h2>
          <div className="bg-ink w-10 h-px mt-2" />
        </div>

        {/* 1. Identification & Formal Scope Matrix */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[8.5pt]">
          <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
            <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700 block">
              01 // DOCUMENT SPECIFICATION
            </span>
            <div className="space-y-1 font-mono text-[8pt]">
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-ink-500">Publication Title:</span>
                <span className="font-semibold text-ink text-right">{manifest.title}</span>
              </div>
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-ink-500">Report Profile:</span>
                <span className="font-semibold text-ink">{manifest.familyDisplayName}</span>
              </div>
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-ink-500">Audited Entity:</span>
                <span className="font-semibold text-ink">{meta.brandName}</span>
              </div>
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-ink-500">Target Origin URL:</span>
                <span className="font-semibold text-ink">{meta.websiteUrl}</span>
              </div>
              <div className="flex justify-between border-b border-line pb-1">
                <span className="text-ink-500">Unique Dossier ID:</span>
                <span className="font-semibold text-ink">{meta.analysisId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-500">Audit Timestamp:</span>
                <span className="font-semibold text-ink">{meta.generatedAt}</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded bg-paper-100 border border-line space-y-2">
            <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700 block">
              02 // AUDIT SAMPLE &amp; COVERAGE NOTICE
            </span>
            <p className="text-ink-700 font-sans leading-relaxed text-[8pt]">
              This audit evaluated <strong>{meta.pagesAnalyzed} primary origin URLs</strong>{' '}
              {meta.discoveredUrlsCount != null && (
                <>out of {meta.discoveredUrlsCount} discovered boundary links ({report.meta.sampleCoveragePct != null ? `${report.meta.sampleCoveragePct.toFixed(1)}%` : ''} sample coverage)</>
              )}.
              Findings and recommendations apply strictly to the examined sample and crawl window. Uninspected routes or gated staging environments remain unmeasured.
            </p>
            <div className="p-2 rounded bg-paper-200 border border-line font-mono text-[7pt] text-ink-600 space-y-0.5">
              <div>• Classification: {manifest.classification}</div>
              <div>• Evidence Governance: Zero-Fake AST Protocol</div>
              <div>• SHA-256 Hashed Evidence Records: {meta.evidenceCount} snapshots</div>
            </div>
          </div>
        </div>

        {/* 2. How to Read This Report */}
        <div className="p-4 rounded bg-paper-100 border border-line space-y-2 text-[8.5pt]">
          <h4 className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-700">
            HOW TO READ THIS PUBLICATION: DUAL-LAYER GOVERNANCE
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-ink-700 leading-relaxed font-sans text-[8pt]">
            <div>
              <strong className="text-ink block font-sans text-[8.5pt] mb-0.5">
                Layer 1: Executive Narrative &amp; Strategic Diagnosis
              </strong>
              Designed for board and engineering leadership. Synthesizes macro discoverability signals, competitive standing, conversion ergonomics, and the prioritised 90-day remediation roadmap with commercial impact framing.
            </div>
            <div>
              <strong className="text-ink block font-sans text-[8.5pt] mb-0.5">
                Layer 2: Empirical Finding &amp; Evidence Ledger
              </strong>
              Engineered for technical implementation teams. Links every defect to verified DOM selectors, HTTP status traces, before/after code diffs, acceptance criteria, and cryptographic AST hashes for verification.
            </div>
          </div>
        </div>

        {/* 3. Measurement & Evidence Conventions */}
        <div className="border border-line rounded p-4 bg-paper-50 space-y-2.5">
          <span className="font-mono text-[7.5pt] font-bold uppercase tracking-[0.04em] text-ink-700 block">
            EVIDENCE CONVENTIONS &amp; ASSURANCE TAXONOMY
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[7.5pt] font-mono">
            <div className="p-2 rounded bg-paper-100 border border-line">
              <span className="font-bold text-good block mb-0.5">OBSERVED</span>
              <span className="text-ink-600 leading-tight block">Directly captured DOM, HTTP headers, or crawl records.</span>
            </div>
            <div className="p-2 rounded bg-paper-100 border border-line">
              <span className="font-bold text-sky-700 dark:text-sky-400 block mb-0.5">MEASURED</span>
              <span className="text-ink-600 leading-tight block">Deterministic metrics calculated from active telemetry.</span>
            </div>
            <div className="p-2 rounded bg-paper-100 border border-line">
              <span className="font-bold text-ink-700 block mb-0.5">DERIVED</span>
              <span className="text-ink-600 leading-tight block">Structured calculations based on stated inputs.</span>
            </div>
            <div className="p-2 rounded bg-paper-100 border border-line">
              <span className="font-bold text-warn block mb-0.5">RECOMMENDED</span>
              <span className="text-ink-600 leading-tight block">Proposed patch or architecture enhancement.</span>
            </div>
            <div className="p-2 rounded bg-paper-100 border border-line">
              <span className="font-bold text-ink-400 block mb-0.5">UNMEASURED</span>
              <span className="text-ink-600 leading-tight block">Dimension not tested — never scored as zero.</span>
            </div>
          </div>
          <p className="font-mono text-[6.8pt] text-ink-500 pt-1 leading-normal">
            * Integrity Note: A cryptographic SHA-256 hash verifies that a captured DOM snippet has not been modified. It does not independently prove that an interpretation or severity rating is correct. Speculative data is strictly excluded.
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
