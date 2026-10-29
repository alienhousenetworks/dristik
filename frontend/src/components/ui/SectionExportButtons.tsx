import React from 'react';
import { FileText, Download } from 'lucide-react';
import { getSectionPdfUrl, getSectionPptxUrl } from '../../services/api';

interface SectionExportButtonsProps {
  analysisId?: string;
  sectionKey: string;
  sectionLabel: string;
}

export function SectionExportButtons({ analysisId, sectionKey, sectionLabel }: SectionExportButtonsProps) {
  if (!analysisId) return null;
  const pdfUrl = getSectionPdfUrl(analysisId, sectionKey);
  const pptxUrl = getSectionPptxUrl(analysisId, sectionKey);

  return (
    <div className="flex items-center gap-2">
      <a
        href={pdfUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-paper-100 hover:bg-paper-200 dark:bg-dark-surface dark:hover:bg-dark-surface/80 text-ink dark:text-light border border-line transition-colors shadow-xs"
        title={`Open printable ${sectionLabel} PDF report`}
      >
        <FileText className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
        PDF
      </a>
      <a
        href={pptxUrl}
        download
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
        title={`Download ${sectionLabel} PowerPoint presentation deck`}
      >
        <Download className="w-3.5 h-3.5" />
        PPT
      </a>
    </div>
  );
}
