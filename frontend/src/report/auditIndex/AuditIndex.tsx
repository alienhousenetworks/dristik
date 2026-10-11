import React from 'react';
import { ExecutiveReport } from '../../types';
import { AUDIT_PARTS } from './catalog';
import { resolveAuditIndex, STATUS_LABEL } from './resolveAuditIndex';
import { SectionStatus } from './types';

function statusClass(status: SectionStatus): string {
  switch (status) {
    case 'ISSUE_VERIFIED':
      return 'text-bad border-bad/30 bg-bad/10';
    case 'INFERRED':
      return 'text-warn border-warn/30 bg-warn/10';
    case 'NO_ISSUE':
      return 'text-good border-good/30 bg-good/10';
    case 'MEASURED':
      return 'text-ink border-line bg-paper-100';
    default:
      return 'text-ink-500 border-line bg-paper-50';
  }
}

export function AuditIndex({
  report,
  expandChecks = false,
}: {
  report: ExecutiveReport;
  expandChecks?: boolean;
}) {
  const index = resolveAuditIndex(report);
  const countLine = (Object.keys(STATUS_LABEL) as SectionStatus[])
    .filter((status) => index.counts[status] > 0)
    .map((status) => `${index.counts[status]} ${STATUS_LABEL[status].toLowerCase()}`)
    .join(' · ');

  return (
    <div className="space-y-6">
      <p className="text-sm text-ink-600 leading-relaxed">{index.sampleNotice}</p>
      <p className="font-mono text-[11px] text-ink-500">{countLine}</p>
      {AUDIT_PARTS.map((part) => {
        const sections = index.sections.filter((section) => section.part === part.id);
        if (sections.length === 0) return null;
        return (
          <div key={part.id} className="space-y-3">
            <h3 className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-500">
              Part {part.id} — {part.title}
            </h3>
            <div className="divide-y divide-line border-y border-line">
              {sections.map((section) => (
                <article key={section.number} className="py-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h4 className="text-sm font-semibold text-ink">
                      <span className="font-mono text-ink-400 mr-2">{section.number}</span>
                      {section.title}
                    </h4>
                    <span className={`font-mono text-[10px] px-1.5 py-0.5 border ${statusClass(section.status)}`}>
                      {STATUS_LABEL[section.status]}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-ink-700 leading-relaxed">{section.summary}</p>
                  <p className="mt-1 font-mono text-[10px] text-ink-400">{section.coverage}</p>
                  {section.findings.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {section.findings.map((finding) => (
                        <li key={finding.id} className="text-xs text-ink-700">
                          <span className="font-mono">{finding.id}</span>
                          {' · '}
                          {finding.severity}
                          {' · '}
                          {finding.title}
                          <span className="text-ink-400"> · {finding.scope}</span>
                        </li>
                      ))}
                      {section.findingCount > section.findings.length && (
                        <li className="text-xs text-ink-400">
                          {section.findingCount - section.findings.length} more findings in this section
                        </li>
                      )}
                    </ul>
                  )}
                  <details {...(expandChecks ? { open: true } : {})} className="mt-2">
                    <summary className="cursor-pointer font-mono text-[10px] text-ink-500">
                      {section.checks.length} checks in this section
                    </summary>
                    <ul className="mt-1 columns-1 sm:columns-2 gap-x-6">
                      {section.checks.map((check) => (
                        <li key={check} className="text-xs text-ink-600 leading-snug break-inside-avoid">
                          {check}
                        </li>
                      ))}
                    </ul>
                  </details>
                </article>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
