import React from 'react';
import { ExecutiveReport } from '../../types';
import { ReportTheme } from '../brandTheme';
import { AuditIndex } from '../auditIndex/AuditIndex';
import { PageFooter, PageHeader } from './PageHeaderFooter';

export function AuditIndexChapter({
  theme,
  report,
  domain,
}: {
  theme: ReportTheme;
  report: ExecutiveReport;
  domain: string;
}) {
  return (
    <section className="report-page-break p-8 md:p-14 bg-paper-50 border-b-2 border-line">
      <PageHeader theme={theme} domain={domain} chapterTitle="MASTER AUDIT INDEX" />
      <div className="space-y-4">
        <div>
          <span className="font-mono text-[8pt] font-bold uppercase tracking-[0.04em] text-ink-500 block mb-1">
            Sections 01–55 and appendices A–O
          </span>
          <h2 className="font-serif text-[24pt] font-normal text-ink">Master audit index</h2>
          <p className="mt-2 text-sm text-ink-600 leading-relaxed max-w-3xl">
            Every section in the audit taxonomy is listed. A section is measured, inferred, or verified only from this run.
            Not tested and data unavailable are not scores of zero. Not applicable means the module was not selected for this site.
          </p>
        </div>
        <AuditIndex report={report} expandChecks />
      </div>
      <PageFooter theme={theme} domain={domain} pageNumber="Index" />
    </section>
  );
}
