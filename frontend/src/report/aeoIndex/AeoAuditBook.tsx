import React from 'react';
import { ExecutiveReport } from '../../types';
import { AEO_PARTS } from './catalog';
import { AeoStatus, AEO_STATUS_LABEL, resolveAeoAudit } from './resolveAeoAudit';

function statusClass(status: AeoStatus): string {
  switch (status) {
    case 'ISSUE_SAMPLE':
      return 'text-bad border-bad/30 bg-bad/10';
    case 'CLEAN_SAMPLE':
      return 'text-good border-good/30 bg-good/10';
    case 'VERIFIED':
      return 'text-ink border-line bg-paper-100';
    case 'INFERRED':
      return 'text-warn border-warn/30 bg-warn/10';
    default:
      return 'text-ink-500 border-line bg-paper-50';
  }
}

export function AeoAuditBook({ report }: { report: ExecutiveReport }) {
  const audit = resolveAeoAudit(report);
  const countLine = (Object.keys(AEO_STATUS_LABEL) as AeoStatus[])
    .filter((status) => audit.counts[status] > 0)
    .map((status) => `${audit.counts[status]} ${AEO_STATUS_LABEL[status].toLowerCase()}`)
    .join(' · ');

  return (
    <div className="space-y-8">
      <p className="text-sm text-ink-700 leading-relaxed">{audit.sampleNotice}</p>
      <p className="font-mono text-[11px] text-ink-500">{countLine}</p>
      {AEO_PARTS.map((part) => {
        const sections = audit.sections.filter((section) => section.part === part.id);
        if (sections.length === 0) return null;
        return (
          <section key={part.id} className="space-y-4">
            <h3 className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-500">
              Part {part.id} — {part.title}
            </h3>
            {sections.map((section) => (
              <article key={section.number} className="border border-line bg-paper">
                <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-4 py-3">
                  <h4 className="text-sm font-semibold text-ink">
                    <span className="mr-2 font-mono text-ink-400">{section.number}</span>
                    {section.title}
                  </h4>
                  <span className={`border px-1.5 py-0.5 font-mono text-[10px] ${statusClass(section.status)}`}>
                    {AEO_STATUS_LABEL[section.status]}
                  </span>
                </header>
                <p className="px-4 pt-3 text-sm leading-relaxed text-ink-700">{section.summary}</p>
                <div className="space-y-3 px-4 py-4">
                  {section.checks.map((check) => (
                    <div key={check.label} className="border-l-2 border-line pl-3">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h5 className="text-sm font-medium text-ink">{check.label}</h5>
                        <span className={`border px-1.5 py-0.5 font-mono text-[10px] ${statusClass(check.status)}`}>
                          {AEO_STATUS_LABEL[check.status]}
                        </span>
                      </div>
                      <p className="mt-1 text-sm leading-relaxed text-ink-700">{check.result}</p>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </section>
        );
      })}
    </div>
  );
}
