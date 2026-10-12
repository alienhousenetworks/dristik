import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { AUDIT_PARTS } from './catalog';
import { ChapterPanel } from './ChapterPanel';
import { resolveAuditIndex, STATUS_LABEL } from './resolveAuditIndex';
import { AuditedCheck, SectionStatus } from './types';

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

function severityClass(sev: string): string {
  switch (sev?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-bad text-white';
    case 'HIGH':
      return 'bg-bad/20 text-bad border-bad/40';
    case 'MEDIUM':
      return 'bg-warn/20 text-warn border-warn/40';
    default:
      return 'bg-paper-100 text-ink-600 border-line';
  }
}

type CheckFilter = 'ALL' | 'ISSUES' | 'MEASURED' | 'GAPS';

export function AuditIndex({
  report,
  expandChecks = false,
}: {
  report: ExecutiveReport;
  expandChecks?: boolean;
}) {
  const index = resolveAuditIndex(report);
  const [filter, setFilter] = useState<CheckFilter>('ALL');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const toggleSection = (num: string) => {
    setExpandedSections((prev) => ({ ...prev, [num]: !prev[num] }));
  };

  const countLine = (Object.keys(STATUS_LABEL) as SectionStatus[])
    .filter((status) => index.counts[status] > 0)
    .map((status) => `${index.counts[status]} ${STATUS_LABEL[status].toLowerCase()}`)
    .join(' · ');

  const filterChecks = (checks: AuditedCheck[]): AuditedCheck[] => {
    if (filter === 'ISSUES') return checks.filter((c) => c.status === 'ISSUE_VERIFIED');
    if (filter === 'MEASURED') return checks.filter((c) => c.status === 'MEASURED' || c.status === 'NO_ISSUE');
    if (filter === 'GAPS') return checks.filter((c) => c.status === 'DATA_UNAVAILABLE' || c.status === 'NOT_TESTED' || c.status === 'NOT_APPLICABLE');
    return checks;
  };

  return (
    <div className="space-y-6">
      {/* Scope & Methodology Bar */}
      <div className="border border-line bg-paper-50 p-4 rounded-sm space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-ink-800">{index.sampleNotice}</p>
          <span className="font-mono text-[11px] text-ink-500 uppercase tracking-wider bg-paper-100 border border-line px-2 py-0.5 rounded">
            Enterprise SEO Audit Standard (55 Chapters · Appendices A–O)
          </span>
        </div>
        <p className="font-mono text-[11px] text-ink-500">{countLine}</p>

        {/* Filter bar */}
        <div className="pt-2 flex flex-wrap items-center gap-2 border-t border-line/60">
          <span className="text-xs font-mono text-ink-400">Filter checks:</span>
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-2 py-0.5 text-xs font-mono border rounded ${
              filter === 'ALL' ? 'bg-ink text-paper border-ink' : 'bg-paper text-ink-600 border-line hover:border-ink-400'
            }`}
          >
            All Checks
          </button>
          <button
            type="button"
            onClick={() => setFilter('ISSUES')}
            className={`px-2 py-0.5 text-xs font-mono border rounded ${
              filter === 'ISSUES' ? 'bg-bad text-white border-bad' : 'bg-paper text-bad border-bad/30 hover:bg-bad/5'
            }`}
          >
            Verified Issues Only
          </button>
          <button
            type="button"
            onClick={() => setFilter('MEASURED')}
            className={`px-2 py-0.5 text-xs font-mono border rounded ${
              filter === 'MEASURED' ? 'bg-good text-white border-good' : 'bg-paper text-good border-good/30 hover:bg-good/5'
            }`}
          >
            Measured / Clean
          </button>
          <button
            type="button"
            onClick={() => setFilter('GAPS')}
            className={`px-2 py-0.5 text-xs font-mono border rounded ${
              filter === 'GAPS' ? 'bg-ink-600 text-white border-ink-600' : 'bg-paper text-ink-500 border-line hover:border-ink-400'
            }`}
          >
            Data Gaps &amp; Untested
          </button>
        </div>
      </div>

      {/* Chapters rendered by Part */}
      {AUDIT_PARTS.map((part) => {
        const sections = index.sections.filter((section) => section.part === part.id);
        if (sections.length === 0) return null;
        return (
          <div key={part.id} className="space-y-4">
            <div className="flex items-center gap-2 border-b-2 border-line pb-1.5">
              <h3 className="font-mono text-xs font-bold uppercase tracking-[0.06em] text-ink-700">
                Part {part.id} — {part.title}
              </h3>
            </div>
            <div className="space-y-4">
              {sections.map((section) => {
                const visibleChecks = filterChecks(section.auditedChecks || []);
                const isAutoOpen = expandChecks || expandedSections[section.number] || visibleChecks.some((c) => c.status === 'ISSUE_VERIFIED');

                return (
                  <article
                    key={section.number}
                    className="border border-line bg-paper rounded-sm p-4 transition-shadow hover:shadow-xs"
                  >
                    {/* Header */}
                    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line/60 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-ink-400 bg-paper-100 px-1.5 py-0.5 rounded border border-line">
                            {section.number}
                          </span>
                          <h4 className="text-base font-semibold text-ink tracking-tight">
                            {section.title}
                          </h4>
                        </div>
                        <p className="mt-1 font-mono text-[10px] text-ink-400">{section.coverage}</p>
                      </div>
                      <span className={`font-mono text-[11px] font-semibold px-2 py-0.5 border rounded ${statusClass(section.status)}`}>
                        {STATUS_LABEL[section.status]}
                      </span>
                    </div>

                    {/* Section Summary */}
                    <p className="mt-2.5 text-sm text-ink-800 leading-relaxed">
                      {section.summary}
                    </p>

                    <ChapterPanel
                      report={report}
                      number={section.number}
                      lineStatuses={(section.auditedChecks || []).map((check) => check.status)}
                    />

                    {/* Verified Empirical Findings */}
                    {section.findings.length > 0 && (
                      <div className="mt-3 space-y-1.5">
                        <span className="font-mono text-[10px] uppercase tracking-wider text-bad font-semibold">
                          Verified Defects Recorded ({section.findingCount}):
                        </span>
                        <div className="space-y-1.5">
                          {section.findings.map((f) => (
                            <div
                              key={f.id}
                              className="border border-bad/30 bg-bad/5 p-2 rounded text-xs space-y-1"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-1">
                                <div className="flex items-center gap-1.5">
                                  <span className={`px-1 py-0.2 text-[9px] font-mono font-bold border rounded ${severityClass(f.severity)}`}>
                                    {f.severity}
                                  </span>
                                  <span className="font-mono text-[10px] text-ink-500 font-bold">
                                    {f.id}
                                  </span>
                                  <span className="font-mono text-[10px] px-1 py-0.2 bg-paper border border-line text-ink-500 rounded">
                                    {f.scope}
                                  </span>
                                </div>
                              </div>
                              <p className="text-ink-900 font-medium">{f.title}</p>
                              {f.action && (
                                <p className="text-ink-600 text-[11px]">
                                  <strong className="text-ink-700">Recommended Action:</strong> {f.action}
                                </p>
                              )}
                            </div>
                          ))}
                          {section.findingCount > section.findings.length && (
                            <p className="text-xs text-ink-400 font-mono">
                              +{section.findingCount - section.findings.length} more recorded finding(s) in the register
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Audited Checks & Diagnostic Proofs Ledger */}
                    <div className="mt-3.5 border-t border-line/60 pt-2.5">
                      <details open={isAutoOpen} className="group">
                        <summary className="cursor-pointer font-mono text-[11px] text-ink-600 font-medium flex items-center justify-between select-none">
                          <span className="flex items-center gap-1.5">
                            <span className="group-open:rotate-90 transition-transform">▸</span>
                            <span>
                              Sub-index evidence · {visibleChecks.length} of {section.checks.length} lines
                            </span>
                          </span>
                          <span className="text-[10px] text-ink-400">
                            Click to toggle check proofs
                          </span>
                        </summary>

                        <div className="mt-2.5 space-y-2 pl-2 border-l border-line">
                          {visibleChecks.map((check) => (
                            <div
                              key={check.label}
                              className={`p-2 rounded border text-xs transition-colors ${
                                check.status === 'ISSUE_VERIFIED'
                                  ? 'border-bad/30 bg-bad/5'
                                  : check.status === 'NO_ISSUE'
                                  ? 'border-good/30 bg-good/5'
                                  : 'border-line/60 bg-paper-50/50'
                              }`}
                            >
                              <div className="flex flex-wrap items-baseline justify-between gap-1.5">
                                <h5 className="font-semibold text-ink-900 text-xs">
                                  {check.label}
                                </h5>
                                <span className={`font-mono text-[9px] px-1.5 py-0.5 border rounded ${statusClass(check.status)}`}>
                                  {STATUS_LABEL[check.status]}
                                </span>
                              </div>
                              <p className="mt-1 text-ink-700 leading-relaxed text-[11px]">
                                {check.result}
                              </p>
                            </div>
                          ))}
                          {visibleChecks.length === 0 && (
                            <p className="text-xs text-ink-400 italic py-1">
                              No checks match current filter ({filter}).
                            </p>
                          )}
                        </div>
                      </details>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
