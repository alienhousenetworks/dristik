import React, { useState, useMemo } from 'react';
import { ExecutiveReport, ExecutiveActionItem, Category } from '../types';
import { categoryLabel, humanize } from '../lib/format';

interface ExecutiveTopActionsProps {
  report: ExecutiveReport;
  variant?: 'card' | 'report_section';
  onNavigateFinding?: (findingId: string) => void;
}

export function ExecutiveTopActions({
  report,
  variant = 'card',
  onNavigateFinding,
}: ExecutiveTopActionsProps) {
  const [priorityFilter, setPriorityFilter] = useState<'ALL' | 'P0' | 'P1' | 'P2'>('ALL');
  const [selectedActionRank, setSelectedActionRank] = useState<number | null>(null);

  // Derive or use precomputed top_10_actions
  const plan = useMemo(() => {
    if (report.top_10_actions && report.top_10_actions.actions?.length > 0) {
      return report.top_10_actions;
    }

    // Derive actions purely from real crawl findings — zero fake fallbacks
    const findings = report.findings || [];
    if (findings.length > 0) {
      const severityMap: Record<string, { priority: 'P0' | 'P1' | 'P2'; impact: string; effort: string; hours: number }> = {
        CRITICAL: { priority: 'P0', impact: 'Very High', effort: 'Low', hours: 4 },
        HIGH: { priority: 'P1', impact: 'High', effort: 'Medium', hours: 3 },
        MEDIUM: { priority: 'P2', impact: 'Medium', effort: 'Low', hours: 2 },
        LOW: { priority: 'P2', impact: 'Low', effort: 'Low', hours: 1 },
        INFO: { priority: 'P2', impact: 'Informational', effort: 'Low', hours: 1 },
      };

      const sortedFindings = [...findings].sort((a, b) => {
        const order: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };
        return (order[a.severity] ?? 5) - (order[b.severity] ?? 5);
      });

      const dynamicActions: ExecutiveActionItem[] = sortedFindings.slice(0, 10).map((f, idx) => {
        const meta = severityMap[f.severity] || { priority: 'P2' as const, impact: 'Medium', effort: 'Low', hours: 2 };
        return {
          rank: idx + 1,
          priority: meta.priority,
          action: f.title || f.finding || 'Remediate detected defect',
          impact: meta.impact,
          effort: meta.effort,
          expected_outcome: f.recommendation || 'Resolve defect in compliance with zero-fake standards',
          estimated_engineer_hours: meta.hours,
          dependencies: [],
          validation: `Automated retest: ${f.title || 'Finding'} verified fixed against live DOM`,
          category: f.category || 'TECHNICAL_SEO',
          related_finding_id: f.finding_id,
        };
      });

      const totalHours = dynamicActions.reduce((acc, a) => acc + a.estimated_engineer_hours, 0);
      return {
        actions: dynamicActions,
        total_engineer_hours: totalHours,
        dependencies_flow: dynamicActions.slice(0, 3).map((a) => a.action).join(' → ') || 'Linear remediation',
        validation_mode: 'automated_retest',
      };
    }

    return {
      actions: [],
      total_engineer_hours: 0,
      dependencies_flow: 'None required',
      validation_mode: 'automated_retest',
    };
  }, [report]);

  const filteredActions = useMemo(() => {
    if (priorityFilter === 'ALL') return plan.actions;
    return plan.actions.filter((a) => a.priority === priorityFilter);
  }, [plan.actions, priorityFilter]);

  const isReportVariant = variant === 'report_section';

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'P0':
        return 'bg-bad/10 text-bad border-bad/30';
      case 'P1':
        return 'bg-warn/10 text-warn border-warn/30';
      default:
        return 'bg-paper-200 text-ink-700 border-line';
    }
  };

  const getImpactBadge = (impact: string) => {
    switch (impact) {
      case 'Very High':
        return 'text-ink-700 font-bold';
      case 'High':
        return 'text-good font-semibold';
      case 'Medium':
        return 'text-ink-700';
      default:
        return 'text-ink-600';
    }
  };

  const getEffortBadge = (effort: string) => {
    switch (effort) {
      case 'Low':
        return 'bg-good/10 text-good border-good/30';
      case 'Medium':
        return 'bg-warn/10 text-warn border-warn/30';
      default:
        return 'bg-bad/10 text-bad border-bad/30';
    }
  };

  return (
    <div
      className={
        isReportVariant
          ? 'space-y-4 font-sans text-ink'
          : 'space-y-4'
      }
    >
      {/* Header & Meta Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold uppercase tracking-[0.04em] text-ink-700 bg-paper-100 px-2 py-0.5 border border-line rounded">
              Leadership Execution Matrix
            </span>
            <span className="text-xs font-mono text-ink-500">
              Top 10 High-ROI Actions
            </span>
          </div>
          <h3 className="text-xl font-sans font-bold text-ink mt-1">
            Top 10 Actions Plan
          </h3>
          <p className="text-xs text-ink-600 mt-0.5">
            Prioritized by commercial impact and implementation velocity. Every action includes automated retest criteria.
          </p>
        </div>

        {/* Priority Filter Chips */}
        <div className="flex items-center gap-1.5 font-mono text-xs">
          <span className="text-ink-400 text-[11px] mr-1">Filter:</span>
          {(['ALL', 'P0', 'P1', 'P2'] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriorityFilter(p)}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                priorityFilter === p
                  ? 'bg-paper-100 text-white font-bold shadow-xs'
                  : 'bg-paper-200 text-ink-700 hover:bg-paper-200 border border-line'
              }`}
            >
              {p}
              {p === 'ALL' ? ` (${plan.actions.length})` : ` (${plan.actions.filter((a) => a.priority === p).length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Implementation Summary Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 bg-paper-100 border border-line rounded text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <span className="text-ink-700 text-base">⏱</span>
          <div>
            <span className="text-[10px] text-ink-500 uppercase block font-semibold">
              Estimated Implementation
            </span>
            <span className="font-bold text-ink text-sm">
              {plan.total_engineer_hours} engineer-hours
            </span>
            <span className="text-ink-500 text-[11px] ml-1">
              (~{(plan.total_engineer_hours / 40).toFixed(1)} dev-weeks)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 md:border-l md:border-line md:pl-3">
          <span className="text-good text-base">🔗</span>
          <div>
            <span className="text-[10px] text-ink-500 uppercase block font-semibold">
              Critical Path Dependencies
            </span>
            <span className="text-[11px] text-ink-700 font-sans leading-tight block">
              {plan.dependencies_flow || 'No dependency path was stored.'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 md:border-l md:border-line md:pl-3">
          <span className="text-ink-700 text-base">✓</span>
          <div>
            <span className="text-[10px] text-ink-500 uppercase block font-semibold">
              Validation Mechanism
            </span>
            <span className="font-bold text-good text-[11px] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-good/10 inline-block animate-pulse" />
              Automated Retest Engine Ready
            </span>
          </div>
        </div>
      </div>

      {/* Top 10 Actions Table */}
      <div className="border border-line rounded overflow-hidden shadow-xs bg-paper-50">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-paper-200 text-ink-700 border-b border-line text-[10px] uppercase font-mono tracking-[0.04em] font-semibold">
              <th className="p-3 text-center w-12">#</th>
              <th className="p-3 text-center w-16">Priority</th>
              <th className="p-3">Action &amp; Target Category</th>
              <th className="p-3 text-center w-24">Impact</th>
              <th className="p-3 text-center w-20">Effort</th>
              <th className="p-3">Expected Outcome</th>
              <th className="p-3 text-center w-20">Est. Hours</th>
              <th className="p-3 text-right">Validation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {filteredActions.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-ink-500 font-mono text-xs">
                  No prioritized action items found for this crawl sample.
                </td>
              </tr>
            ) : (
              filteredActions.map((item) => {
              const isSelected = selectedActionRank === item.rank;

              return (
                <React.Fragment key={item.rank}>
                  <tr
                    onClick={() => setSelectedActionRank(isSelected ? null : item.rank)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-paper-100 font-medium'
                        : item.priority === 'P0'
                        ? 'bg-bad/10 hover:bg-paper-100'
                        : 'hover:bg-paper-100'
                    }`}
                  >
                    <td className="p-3 text-center font-mono font-bold text-ink-400">
                      {item.rank}
                    </td>
                    <td className="p-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded font-mono font-bold border text-[11px] ${getPriorityBadge(
                          item.priority
                        )}`}
                      >
                        {item.priority}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-ink text-sm">
                          {item.action}
                        </span>
                        {item.category && (
                          <span className="text-[10px] font-mono px-1.5 py-0.2 bg-paper-200 text-ink-600 rounded border border-line">
                            {categoryLabel(item.category)}
                          </span>
                        )}
                      </div>
                      {item.dependencies && item.dependencies.length > 0 && (
                        <p className="text-[10px] text-ink-500 font-mono mt-0.5">
                          Prerequisite: {item.dependencies.join(', ')}
                        </p>
                      )}
                    </td>
                    <td className={`p-3 text-center font-sans text-xs ${getImpactBadge(item.impact)}`}>
                      {item.impact}
                    </td>
                    <td className="p-3 text-center font-mono">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${getEffortBadge(
                          item.effort
                        )}`}
                      >
                        {item.effort}
                      </span>
                    </td>
                    <td className="p-3 text-ink-700 font-sans text-xs max-w-xs">
                      {item.expected_outcome}
                    </td>
                    <td className="p-3 text-center font-mono font-bold text-ink-700">
                      {item.estimated_engineer_hours}h
                    </td>
                    <td className="p-3 text-right font-sans">
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-good/10 text-good border border-good/30">
                        <span className="text-good">✓</span>
                        <span>retest ready</span>
                      </span>
                    </td>
                  </tr>

                  {/* Expanded Detail Panel */}
                  {isSelected && (
                    <tr className="bg-paper-100 border-b border-line">
                      <td colSpan={8} className="p-4 space-y-3 font-sans">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="space-y-2 border-r border-line pr-4">
                            <span className="font-mono font-bold uppercase tracking-[0.04em] text-ink-600 text-[10px] block">
                              Automated Retest &amp; Verification Condition
                            </span>
                            <div className="p-2.5 bg-paper-50 border border-line rounded font-mono text-ink-700 text-[11px] leading-relaxed">
                              {item.validation}
                            </div>
                            <div className="flex items-center gap-2 text-ink-500 text-[11px]">
                              <span>Status:</span>
                              <span className="text-warn font-semibold font-mono">
                                Pending Execution
                              </span>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <span className="font-mono font-bold uppercase tracking-[0.04em] text-ink-600 text-[10px] block">
                              Prerequisites &amp; Traceability
                            </span>
                            <div className="text-xs text-ink-700 space-y-1.5">
                              <div>
                                <span className="font-medium text-ink">Dependencies: </span>
                                <span className="font-mono text-ink-600">
                                  {item.dependencies && item.dependencies.length > 0
                                    ? item.dependencies.join(' → ')
                                    : 'None (Immediate standalone execution)'}
                                </span>
                              </div>
                              {item.related_finding_id && (
                                <div className="flex items-center gap-2 pt-1">
                                  <span className="font-medium text-ink">Associated Finding:</span>
                                  <span className="font-mono text-[11px] bg-paper-100 text-ink-700 px-1.5 py-0.5 rounded border border-line">
                                    {item.related_finding_id}
                                  </span>
                                  {onNavigateFinding && (
                                    <button
                                      type="button"
                                      onClick={() => onNavigateFinding(item.related_finding_id!)}
                                      className="text-ink-700 hover:underline font-mono text-[11px]"
                                    >
                                      Inspect Finding Evidence →
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })
          )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
