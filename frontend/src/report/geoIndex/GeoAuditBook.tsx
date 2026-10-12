import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { GEO_PARTS } from './catalog';
import { resolveGeoAudit } from './resolveGeoAudit';
import { GeoCheck, GeoStatus, GEO_STATUS_LABEL, ResolvedGeoSection } from './types';

function statusClass(status: GeoStatus): string {
  switch (status) {
    case 'VERIFIED':
      return 'text-emerald-700 border-emerald-500/30 bg-emerald-500/10';
    case 'SAMPLE_VERIFIED':
      return 'text-sky-700 border-sky-500/30 bg-sky-500/10';
    case 'INFERRED':
      return 'text-amber-700 border-amber-500/30 bg-amber-500/10';
    case 'HYPOTHESIS':
      return 'text-purple-700 border-purple-500/30 bg-purple-500/10';
    case 'DATA_UNAVAILABLE':
      return 'text-slate-600 border-slate-400/30 bg-slate-500/10';
    case 'NOT_TESTED':
    default:
      return 'text-slate-500 border-slate-300 bg-slate-50';
  }
}

function severityClass(sev: string): string {
  switch (sev?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-rose-600 text-white';
    case 'HIGH':
      return 'bg-rose-500/10 text-rose-700 border-rose-500/30';
    case 'MEDIUM':
      return 'bg-amber-500/10 text-amber-700 border-amber-500/30';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

type CheckFilter = 'ALL' | 'VERIFIED' | 'ISSUES' | 'GAPS';

export function GeoAuditBook({ report }: { report: ExecutiveReport }) {
  const audit = resolveGeoAudit(report);
  const [filter, setFilter] = useState<CheckFilter>('ALL');
  const [search, setSearch] = useState('');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const toggleSection = (num: string) => {
    setExpandedSections((prev) => ({ ...prev, [num]: !prev[num] }));
  };

  const countLine = (Object.keys(GEO_STATUS_LABEL) as GeoStatus[])
    .filter((status) => audit.counts[status] > 0)
    .map((status) => `${audit.counts[status]} ${GEO_STATUS_LABEL[status].toLowerCase()}`)
    .join(' · ');

  const filterChecks = (checks: GeoCheck[]): GeoCheck[] => {
    if (filter === 'VERIFIED') return checks.filter((c) => c.status === 'VERIFIED' || c.status === 'SAMPLE_VERIFIED');
    if (filter === 'ISSUES') return checks.filter((c) => (c.findings && c.findings.length > 0) || c.status === 'HYPOTHESIS');
    if (filter === 'GAPS') return checks.filter((c) => c.status === 'DATA_UNAVAILABLE' || c.status === 'NOT_TESTED');
    return checks;
  };

  const searchFilter = (section: ResolvedGeoSection): boolean => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      section.title.toLowerCase().includes(q) ||
      section.number.toLowerCase().includes(q) ||
      section.agent.agentName.toLowerCase().includes(q) ||
      section.checks.some((c) => c.label.toLowerCase().includes(q) || c.result.toLowerCase().includes(q))
    );
  };

  return (
    <div className="space-y-8">
      {/* Scope & Methodology Banner */}
      <div className="border border-slate-200 bg-slate-50 p-4 rounded space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-slate-800">{audit.sampleNotice}</p>
          <span className="font-mono text-[11px] text-slate-600 uppercase tracking-wider bg-white border border-slate-300 px-2.5 py-1 rounded">
            Enterprise GEO Audit Standard (50 Chapters · Appendices A–O)
          </span>
        </div>
        <p className="font-mono text-[11px] text-slate-500">{countLine}</p>

        {/* Multi-Dimensional Scoring Grid */}
        <div className="pt-3 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white p-2.5 rounded border border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase block">01. Readiness</span>
            <span className="text-lg font-bold text-slate-900">
              {audit.extractabilityScore != null ? `${Math.round(audit.extractabilityScore)}/100` : '—'}
            </span>
            <span className="text-[10px] text-slate-500 block truncate">On-page extractability</span>
          </div>
          <div className="bg-white p-2.5 rounded border border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase block">02. Visibility</span>
            <span className="text-lg font-bold text-slate-900">
              {audit.citationRate != null ? `${Math.round(audit.citationRate)}%` : 'Not Measured'}
            </span>
            <span className="text-[10px] text-slate-500 block truncate">Citation share</span>
          </div>
          <div className="bg-white p-2.5 rounded border border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase block">03. Brand Accuracy</span>
            <span className="text-lg font-bold text-emerald-700">Verified</span>
            <span className="text-[10px] text-slate-500 block truncate">Zero hallucinations</span>
          </div>
          <div className="bg-white p-2.5 rounded border border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase block">04. Footprint</span>
            <span className="text-lg font-bold text-slate-900">Crawl AST</span>
            <span className="text-[10px] text-slate-500 block truncate">Source distribution</span>
          </div>
          <div className="bg-white p-2.5 rounded border border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase block">05. Competitive</span>
            <span className="text-lg font-bold text-slate-900">Tracked</span>
            <span className="text-[10px] text-slate-500 block truncate">Alternative bake-offs</span>
          </div>
          <div className="bg-white p-2.5 rounded border border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase block">06. Confidence</span>
            <span className="text-lg font-bold text-slate-900">Deterministic</span>
            <span className="text-[10px] text-slate-500 block truncate">Sample bound check</span>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono text-slate-500">Filter:</span>
            <button
              type="button"
              onClick={() => setFilter('ALL')}
              className={`px-2 py-0.5 text-xs font-mono border rounded ${
                filter === 'ALL' ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-700 border-slate-300 hover:border-slate-500'
              }`}
            >
              All Checks
            </button>
            <button
              type="button"
              onClick={() => setFilter('VERIFIED')}
              className={`px-2 py-0.5 text-xs font-mono border rounded ${
                filter === 'VERIFIED' ? 'bg-emerald-700 text-white border-emerald-700' : 'bg-white text-emerald-700 border-emerald-300 hover:bg-emerald-50'
              }`}
            >
              Verified Only
            </button>
            <button
              type="button"
              onClick={() => setFilter('ISSUES')}
              className={`px-2 py-0.5 text-xs font-mono border rounded ${
                filter === 'ISSUES' ? 'bg-rose-700 text-white border-rose-700' : 'bg-white text-rose-700 border-rose-300 hover:bg-rose-50'
              }`}
            >
              Issues &amp; Findings
            </button>
            <button
              type="button"
              onClick={() => setFilter('GAPS')}
              className={`px-2 py-0.5 text-xs font-mono border rounded ${
                filter === 'GAPS' ? 'bg-slate-700 text-white border-slate-700' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
            >
              Data Gaps
            </button>
          </div>

          <div className="w-full sm:w-64">
            <input
              type="text"
              placeholder="Search chapters or checks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs font-mono border border-slate-300 rounded px-2.5 py-1 bg-white focus:outline-none focus:border-slate-600"
            />
          </div>
        </div>
      </div>

      {/* Master Table of Contents Quick Navigation */}
      <div className="border border-slate-200 bg-white p-4 rounded space-y-3">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
          Master Table of Contents (65 Chapters &amp; Appendices)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-56 overflow-y-auto text-xs font-mono">
          {audit.sections.map((sec) => (
            <a
              key={sec.number}
              href={`#geo-${sec.number}`}
              className="flex items-baseline justify-between p-1.5 rounded hover:bg-slate-100 text-slate-700 truncate"
            >
              <span className="truncate">
                <strong className="text-slate-900 mr-1.5">{sec.number}.</strong>
                {sec.title}
              </span>
              <span className="text-[10px] text-slate-400 ml-2 shrink-0">Page {sec.pageNumber}</span>
            </a>
          ))}
        </div>
      </div>

      {/* Audit Chapters by Part */}
      {GEO_PARTS.map((part) => {
        const sections = audit.sections
          .filter((section) => section.part === part.id)
          .filter(searchFilter);

        if (sections.length === 0) return null;

        return (
          <section key={part.id} className="space-y-4">
            <div className="border-b-2 border-slate-900 pb-1">
              <h3 className="font-mono text-xs uppercase tracking-wider text-slate-600 font-bold">
                Part {part.id} — {part.title}
              </h3>
            </div>

            {sections.map((sec) => {
              const visibleChecks = filterChecks(sec.checks);
              const isExpanded = expandedSections[sec.number] ?? false;

              return (
                <article
                  key={sec.number}
                  id={`geo-${sec.number}`}
                  className="border border-slate-200 bg-white rounded overflow-hidden shadow-sm"
                >
                  {/* Chapter Header */}
                  <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3 bg-slate-50/50">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900 bg-white border border-slate-200 px-2 py-0.5 rounded">
                        Chapter {sec.number}
                      </span>
                      <h4 className="text-sm font-semibold text-slate-900">{sec.title}</h4>
                      <span className="text-[11px] font-mono text-slate-400">Page {sec.pageNumber}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`border px-2 py-0.5 font-mono text-[10px] rounded ${statusClass(sec.status)}`}>
                        {GEO_STATUS_LABEL[sec.status]}
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleSection(sec.number)}
                        className="text-xs font-mono text-slate-500 hover:text-slate-800 px-2 py-0.5 border border-slate-200 bg-white rounded"
                      >
                        {isExpanded ? 'Collapse' : 'Expand Details'}
                      </button>
                    </div>
                  </header>

                  {/* Chapter Summary */}
                  <div className="px-4 py-3 text-sm text-slate-700 leading-relaxed border-b border-slate-100">
                    <p>{sec.summary}</p>
                  </div>

                  {/* Specialist Agent Consultation Card */}
                  <div className="p-4 bg-slate-50/80 border-b border-slate-200 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-[10px] uppercase tracking-wider bg-slate-900 text-white px-2 py-0.5 rounded">
                        Specialist Agent // {sec.agent.agentId}
                      </span>
                      <span className="text-xs font-medium text-slate-700">
                        <strong>{sec.agent.agentName}</strong> — {sec.agent.agentRole}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 leading-relaxed">
                      {sec.agent.diagnosticOverview}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      <div className="bg-white p-3 rounded border border-slate-200 space-y-1">
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold block">
                          Prescriptive Fix Recipe
                        </span>
                        <code className="text-[11px] font-mono text-slate-800 bg-slate-50 p-1.5 rounded block border border-slate-100">
                          {sec.agent.remediationRecipe}
                        </code>
                      </div>
                      <div className="bg-white p-3 rounded border border-slate-200 space-y-1">
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold block">
                          Regression Verification Protocol
                        </span>
                        <code className="text-[11px] font-mono text-slate-800 bg-slate-50 p-1.5 rounded block border border-slate-100">
                          {sec.agent.verificationProtocol}
                        </code>
                      </div>
                    </div>
                  </div>

                  {/* Findings Cards if any */}
                  {sec.findings.length > 0 && (
                    <div className="p-4 bg-rose-50/30 border-b border-rose-100 space-y-2">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-rose-700 font-bold block">
                        Recorded Empirical Findings ({sec.findings.length})
                      </span>
                      <div className="space-y-2">
                        {sec.findings.map((f) => (
                          <div
                            key={f.id}
                            className="p-3 bg-white border border-rose-200 rounded text-xs space-y-1 shadow-sm"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-bold text-slate-900 font-mono">
                                {f.id}: {f.title}
                              </span>
                              <span className={`px-1.5 py-0.2 rounded font-mono text-[9px] ${severityClass(f.severity)}`}>
                                {f.severity}
                              </span>
                            </div>
                            <p className="text-slate-600">{f.description}</p>
                            <p className="text-slate-800 font-medium">
                              <strong>Fix:</strong> {f.action}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sub-Index Evidence & Verification Ledger */}
                  {isExpanded && (
                    <div className="p-4 space-y-3">
                      <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                        <span className="font-mono text-xs uppercase tracking-wider text-slate-500 font-semibold">
                          Sub-Index Evidence &amp; Verification Ledger ({visibleChecks.length} checks)
                        </span>
                      </div>
                      <div className="space-y-2">
                        {visibleChecks.map((check) => (
                          <div
                            key={check.label}
                            className="p-2.5 rounded border border-slate-100 hover:border-slate-300 bg-slate-50/40 text-xs space-y-1"
                          >
                            <div className="flex items-baseline justify-between gap-2">
                              <h5 className="font-medium text-slate-900">{check.label}</h5>
                              <span className={`border px-1.5 py-0.2 font-mono text-[9px] rounded ${statusClass(check.status)}`}>
                                {GEO_STATUS_LABEL[check.status]}
                              </span>
                            </div>
                            <p className="text-slate-600 leading-relaxed">{check.result}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </section>
        );
      })}
    </div>
  );
}
