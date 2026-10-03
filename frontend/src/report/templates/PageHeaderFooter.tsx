import React from 'react';
import { ReportTheme } from '../brandTheme';

interface PageHeaderFooterProps {
  theme: ReportTheme;
  domain: string;
  chapterTitle?: string;
  pageNumber?: number | string;
  reportId?: string;
  dateStr?: string;
}

export function PageHeader({
  theme,
  domain,
  chapterTitle,
}: PageHeaderFooterProps) {
  return (
    <div className="report-running-header flex items-center justify-between pb-2 mb-6 border-b border-slate-200 text-[8pt] text-slate-500 font-sans tracking-wider uppercase">
      <div className="flex items-center gap-2">
        <span className="font-bold text-slate-900 font-mono tracking-normal">DRISTIK</span>
        <span className="text-slate-300">/</span>
        <span className="font-medium text-slate-600">Enterprise Digital Intelligence</span>
      </div>
      {chapterTitle && (
        <div className="font-mono text-[7.5pt] font-semibold tracking-wider text-slate-700">
          {chapterTitle}
        </div>
      )}
      <div className="font-mono text-[7.5pt] text-slate-500">
        {domain}
      </div>
    </div>
  );
}

export function PageFooter({
  theme,
  domain,
  pageNumber,
  reportId,
  dateStr,
}: PageHeaderFooterProps) {
  return (
    <div className="report-running-footer mt-auto pt-3 border-t border-slate-200 flex items-center justify-between text-[7.5pt] font-mono text-slate-400">
      <div>
        <span className="font-bold text-slate-700">CONFIDENTIAL</span>
        <span className="mx-1.5 text-slate-300">·</span>
        <span>Prepared for {domain}</span>
      </div>
      <div>
        <span>{reportId ? `Run: ${reportId.slice(0, 14)}` : ''}</span>
        {dateStr && <span className="ml-2">{dateStr.slice(0, 10)}</span>}
      </div>
      <div className="font-bold text-slate-700">
        {pageNumber != null ? `PAGE ${pageNumber}` : ''}
      </div>
    </div>
  );
}
