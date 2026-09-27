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

    // Dynamic synthesis fallback
    const findings = report.findings || [];
    const findingsMap: Record<string, string> = {};
    for (const f of findings) {
      const text = `${f.title} ${f.finding} ${f.description || ''}`.toLowerCase();
      if (!findingsMap.positioning && (text.includes('h1') || text.includes('positioning') || text.includes('headline'))) {
        findingsMap.positioning = f.finding_id;
      }
      if (!findingsMap.taxonomy && (text.includes('taxonomy') || text.includes('service') || text.includes('entity'))) {
        findingsMap.taxonomy = f.finding_id;
      }
      if (!findingsMap.schema && (text.includes('schema') || text.includes('json-ld') || text.includes('structured data'))) {
        findingsMap.schema = f.finding_id;
      }
      if (!findingsMap.duplicate_meta && (text.includes('duplicate') || text.includes('canonical') || text.includes('meta'))) {
        findingsMap.duplicate_meta = f.finding_id;
      }
      if (!findingsMap.icp && (text.includes('icp') || text.includes('audience') || text.includes('landing'))) {
        findingsMap.icp = f.finding_id;
      }
      if (!findingsMap.trust && (text.includes('case study') || text.includes('trust') || text.includes('proof'))) {
        findingsMap.trust = f.finding_id;
      }
      if (!findingsMap.crawl && (text.includes('sitemap') || text.includes('robots') || text.includes('crawl'))) {
        findingsMap.crawl = f.finding_id;
      }
      if (!findingsMap.answerability && (text.includes('answer') || text.includes('faq') || text.includes('question') || text.includes('citation'))) {
        findingsMap.answerability = f.finding_id;
      }
      if (!findingsMap.performance && (text.includes('vitals') || text.includes('ttfb') || text.includes('speed'))) {
        findingsMap.performance = f.finding_id;
      }
      if (!findingsMap.hierarchy && (text.includes('hierarchy') || text.includes('heading') || text.includes('h2'))) {
        findingsMap.hierarchy = f.finding_id;
      }
    }

    const defaultActions: ExecutiveActionItem[] = [
      {
        rank: 1,
        priority: 'P0',
        action: 'Define service taxonomy',
        impact: 'Very High',
        effort: 'Low',
        expected_outcome: 'Category clarity & unambiguous entity mapping',
        estimated_engineer_hours: 4,
        dependencies: [],
        validation: 'Automated retest: Taxonomy terms registered in DOM AST and canonical URL paths',
        category: 'GEO',
        related_finding_id: findingsMap.taxonomy,
      },
      {
        rank: 2,
        priority: 'P0',
        action: 'Rewrite homepage positioning',
        impact: 'Very High',
        effort: 'Low',
        expected_outcome: 'Improve visitor comprehension & instant value recognition',
        estimated_engineer_hours: 3,
        dependencies: [],
        validation: 'Automated retest: Homepage H1 & title contain explicit service category',
        category: 'UX_CONVERSION',
        related_finding_id: findingsMap.positioning,
      },
      {
        rank: 3,
        priority: 'P1',
        action: 'Create service schema',
        impact: 'High',
        effort: 'Medium',
        expected_outcome: 'Better entity understanding & AI knowledge graph ingestion',
        estimated_engineer_hours: 5,
        dependencies: ['Define service taxonomy'],
        validation: 'Automated retest: Schema Validator verifies valid Service & Organization JSON-LD',
        category: 'SCHEMA',
        related_finding_id: findingsMap.schema,
      },
      {
        rank: 4,
        priority: 'P1',
        action: 'Fix metadata duplication',
        impact: 'High',
        effort: 'Low',
        expected_outcome: 'Better page differentiation & clean SERP snippets',
        estimated_engineer_hours: 3,
        dependencies: [],
        validation: 'Automated retest: 100% unique <title> and meta descriptions across crawled URLs',
        category: 'ON_PAGE_SEO',
        related_finding_id: findingsMap.duplicate_meta,
      },
      {
        rank: 5,
        priority: 'P1',
        action: 'Add ICP landing pages',
        impact: 'High',
        effort: 'Medium',
        expected_outcome: 'Better commercial qualification & dedicated intent routes',
        estimated_engineer_hours: 6,
        dependencies: ['Define service taxonomy'],
        validation: 'Automated retest: Target ICP paths return HTTP 200 with >400 words depth',
        category: 'CONTENT',
        related_finding_id: findingsMap.icp,
      },
      {
        rank: 6,
        priority: 'P1',
        action: 'Add case studies & proof points',
        impact: 'High',
        effort: 'Medium',
        expected_outcome: 'Trust validation & decision confidence',
        estimated_engineer_hours: 5,
        dependencies: ['Add ICP landing pages'],
        validation: 'Automated retest: Social proof elements and quantifiable metrics identified',
        category: 'TRUST_AUTHORITY',
        related_finding_id: findingsMap.trust,
      },
      {
        rank: 7,
        priority: 'P2',
        action: 'Configure sitemap & robots directives',
        impact: 'Medium',
        effort: 'Low',
        expected_outcome: 'Crawlability & zero index waste',
        estimated_engineer_hours: 2,
        dependencies: [],
        validation: 'Automated retest: robots.txt allows AI/search bots; sitemap.xml returns 200',
        category: 'TECHNICAL_SEO',
        related_finding_id: findingsMap.crawl,
      },
      {
        rank: 8,
        priority: 'P2',
        action: 'Format structured Q&A for answer engines',
        impact: 'High',
        effort: 'Medium',
        expected_outcome: 'AI Search citation readiness & snippet extraction',
        estimated_engineer_hours: 4,
        dependencies: ['Define service taxonomy'],
        validation: 'Automated retest: FAQPage schema or semantic Q&A blocks verified in AST',
        category: 'AI_SEARCH',
        related_finding_id: findingsMap.answerability,
      },
      {
        rank: 9,
        priority: 'P2',
        action: 'Remediate TTFB & Core Web Vitals bottlenecks',
        impact: 'Medium',
        effort: 'Medium',
        expected_outcome: 'Page experience & crawl budget optimization',
        estimated_engineer_hours: 4,
        dependencies: [],
        validation: 'Automated retest: Server response TTFB < 400ms across tested endpoints',
        category: 'TECHNICAL_SEO',
        related_finding_id: findingsMap.performance,
      },
      {
        rank: 10,
        priority: 'P2',
        action: 'Standardize semantic heading hierarchy',
        impact: 'Medium',
        effort: 'Low',
        expected_outcome: 'Content scannability & assistive parsing integrity',
        estimated_engineer_hours: 2,
        dependencies: [],
        validation: 'Automated retest: DOM heading tree has single H1 and sequential H2/H3 levels',
        category: 'ON_PAGE_SEO',
        related_finding_id: findingsMap.hierarchy,
      },
    ];

    const totalHours = defaultActions.reduce((acc, a) => acc + a.estimated_engineer_hours, 0);

    return {
      actions: defaultActions,
      total_engineer_hours: totalHours,
      dependencies_flow: 'Define service taxonomy → Create service schema → Add ICP landing pages → Add case studies',
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
        return 'bg-red-100 text-red-800 border-red-300';
      case 'P1':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  const getImpactBadge = (impact: string) => {
    switch (impact) {
      case 'Very High':
        return 'text-purple-700 font-bold';
      case 'High':
        return 'text-emerald-700 font-semibold';
      case 'Medium':
        return 'text-blue-700';
      default:
        return 'text-slate-600';
    }
  };

  const getEffortBadge = (effort: string) => {
    switch (effort) {
      case 'Low':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'Medium':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-red-50 text-red-700 border-red-200';
    }
  };

  return (
    <div
      className={
        isReportVariant
          ? 'space-y-4 font-sans text-slate-900'
          : 'space-y-4'
      }
    >
      {/* Header & Meta Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold uppercase tracking-wider text-blue-900 bg-blue-50 px-2 py-0.5 border border-blue-200 rounded">
              Leadership Execution Matrix
            </span>
            <span className="text-xs font-mono text-slate-500">
              Top 10 High-ROI Actions
            </span>
          </div>
          <h3 className="text-xl font-serif font-bold text-slate-900 mt-1">
            Top 10 Actions Plan
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">
            Prioritized by commercial impact and implementation velocity. Every action includes automated retest criteria.
          </p>
        </div>

        {/* Priority Filter Chips */}
        <div className="flex items-center gap-1.5 font-mono text-xs">
          <span className="text-slate-400 text-[11px] mr-1">Filter:</span>
          {(['ALL', 'P0', 'P1', 'P2'] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriorityFilter(p)}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                priorityFilter === p
                  ? 'bg-blue-950 text-white font-bold shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
              }`}
            >
              {p}
              {p === 'ALL' ? ` (${plan.actions.length})` : ` (${plan.actions.filter((a) => a.priority === p).length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Implementation Summary Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 bg-slate-50 border border-slate-300 rounded text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <span className="text-blue-900 text-base">⏱</span>
          <div>
            <span className="text-[10px] text-slate-500 uppercase block font-semibold">
              Estimated Implementation
            </span>
            <span className="font-bold text-slate-900 text-sm">
              {plan.total_engineer_hours} engineer-hours
            </span>
            <span className="text-slate-500 text-[11px] ml-1">
              (~{(plan.total_engineer_hours / 40).toFixed(1)} dev-weeks)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 md:border-l md:border-slate-200 md:pl-3">
          <span className="text-emerald-700 text-base">🔗</span>
          <div>
            <span className="text-[10px] text-slate-500 uppercase block font-semibold">
              Critical Path Dependencies
            </span>
            <span className="text-[11px] text-slate-800 font-sans leading-tight block">
              {plan.dependencies_flow || 'No dependency path was stored.'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 md:border-l md:border-slate-200 md:pl-3">
          <span className="text-blue-700 text-base">✓</span>
          <div>
            <span className="text-[10px] text-slate-500 uppercase block font-semibold">
              Validation Mechanism
            </span>
            <span className="font-bold text-emerald-800 text-[11px] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block animate-pulse" />
              Automated Retest Engine Ready
            </span>
          </div>
        </div>
      </div>

      {/* Top 10 Actions Table */}
      <div className="border border-slate-300 rounded overflow-hidden shadow-xs bg-white">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/90 text-slate-700 border-b border-slate-300 text-[10px] uppercase font-mono tracking-wider font-semibold">
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
          <tbody className="divide-y divide-slate-200">
            {filteredActions.map((item) => {
              const isSelected = selectedActionRank === item.rank;

              return (
                <React.Fragment key={item.rank}>
                  <tr
                    onClick={() => setSelectedActionRank(isSelected ? null : item.rank)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-50/90 font-medium'
                        : item.priority === 'P0'
                        ? 'bg-red-50/20 hover:bg-slate-50'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="p-3 text-center font-mono font-bold text-slate-400">
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
                        <span className="font-semibold text-slate-900 text-sm">
                          {item.action}
                        </span>
                        {item.category && (
                          <span className="text-[10px] font-mono px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded border border-slate-200">
                            {categoryLabel(item.category)}
                          </span>
                        )}
                      </div>
                      {item.dependencies && item.dependencies.length > 0 && (
                        <p className="text-[10px] text-slate-500 font-mono mt-0.5">
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
                    <td className="p-3 text-slate-700 font-sans text-xs max-w-xs">
                      {item.expected_outcome}
                    </td>
                    <td className="p-3 text-center font-mono font-bold text-slate-800">
                      {item.estimated_engineer_hours}h
                    </td>
                    <td className="p-3 text-right font-sans">
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <span className="text-emerald-600">✓</span>
                        <span>retest ready</span>
                      </span>
                    </td>
                  </tr>

                  {/* Expanded Detail Panel */}
                  {isSelected && (
                    <tr className="bg-slate-50/95 border-b border-blue-200">
                      <td colSpan={8} className="p-4 space-y-3 font-sans">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="space-y-2 border-r border-slate-200 pr-4">
                            <span className="font-mono font-bold uppercase tracking-wider text-slate-600 text-[10px] block">
                              Automated Retest &amp; Verification Condition
                            </span>
                            <div className="p-2.5 bg-white border border-slate-300 rounded font-mono text-slate-800 text-[11px] leading-relaxed">
                              {item.validation}
                            </div>
                            <div className="flex items-center gap-2 text-slate-500 text-[11px]">
                              <span>Status:</span>
                              <span className="text-amber-700 font-semibold font-mono">
                                Pending Execution
                              </span>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <span className="font-mono font-bold uppercase tracking-wider text-slate-600 text-[10px] block">
                              Prerequisites &amp; Traceability
                            </span>
                            <div className="text-xs text-slate-700 space-y-1.5">
                              <div>
                                <span className="font-medium text-slate-900">Dependencies: </span>
                                <span className="font-mono text-slate-600">
                                  {item.dependencies && item.dependencies.length > 0
                                    ? item.dependencies.join(' → ')
                                    : 'None (Immediate standalone execution)'}
                                </span>
                              </div>
                              {item.related_finding_id && (
                                <div className="flex items-center gap-2 pt-1">
                                  <span className="font-medium text-slate-900">Associated Finding:</span>
                                  <span className="font-mono text-[11px] bg-blue-100 text-blue-900 px-1.5 py-0.5 rounded border border-blue-200">
                                    {item.related_finding_id}
                                  </span>
                                  {onNavigateFinding && (
                                    <button
                                      type="button"
                                      onClick={() => onNavigateFinding(item.related_finding_id!)}
                                      className="text-blue-700 hover:underline font-mono text-[11px]"
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
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
