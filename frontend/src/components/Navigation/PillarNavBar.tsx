import React from 'react';
import { TabId, ExecutiveReport } from '../../types';
import { synthesizePillars } from '../../lib/pillarSynthesis';
import { cn, ScorePill } from '../ui';

interface PillarNavBarProps {
  tab: TabId;
  onSelectTab: (tab: TabId) => void;
  report?: ExecutiveReport;
  findingsCount?: number;
  pagesCount?: number;
  onNewAudit?: () => void;
}

export function PillarNavBar({
  tab,
  onSelectTab,
  report,
  findingsCount = 0,
  onNewAudit,
}: PillarNavBarProps) {
  const rollup = synthesizePillars(report);

  const results: Array<{ id: TabId; label: string; score?: number }> = [
    { id: 'overview', label: 'Overview', score: report ? Math.round(report.scores?.overall_score || 0) : undefined },
    { id: 'search_intelligence', label: 'Search', score: report ? rollup.search_intelligence.score : undefined },
    { id: 'ai_search_intelligence', label: 'AI search', score: report ? rollup.ai_search_intelligence.score : undefined },
    { id: 'website_experience', label: 'Experience', score: report ? rollup.sxo_score : undefined },
    { id: 'conversion_intelligence', label: 'Conversion', score: report ? rollup.conversion_intelligence.score : undefined },
    { id: 'brand_entity_intelligence', label: 'Brand', score: report ? rollup.brand_entity_intelligence.score : undefined },
  ];

  const actions: Array<{ id: TabId; label: string; badge?: number }> = [
    { id: 'findings', label: 'Findings', badge: findingsCount || undefined },
    { id: 'roadmap', label: 'Roadmap' },
    { id: 'report', label: 'Report' },
  ];

  return (
    <aside className="no-print lg:w-56 xl:w-[15.5rem] shrink-0 border-b lg:border-b-0 lg:border-r border-line bg-paper-100/70">
      <nav className="lg:sticky lg:top-14 lg:h-[calc(100vh-3.5rem)] lg:overflow-y-auto px-3 py-3 lg:px-3 lg:py-5 flex lg:flex-col gap-1 overflow-x-auto">
        <p className="hidden lg:block label px-2 mb-1">Results</p>
        {results.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectTab(item.id)}
            className={cn('workspace-link', tab === item.id && 'is-active')}
          >
            <span>{item.label}</span>
            {item.score != null && <ScorePill score={item.score} />}
          </button>
        ))}

        <p className="hidden lg:block label px-2 mt-5 mb-1">Actions</p>
        <div className="hidden lg:block h-px bg-line my-1 lg:hidden" />
        {actions.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectTab(item.id)}
            className={cn('workspace-link', tab === item.id && 'is-active')}
          >
            <span>{item.label}</span>
            {item.badge != null && (
              <span className={cn('score-pill', tab === item.id ? 'border-white/20 text-paper-100' : '')}>
                {item.badge}
              </span>
            )}
          </button>
        ))}

        {onNewAudit && (
          <div className="lg:mt-auto lg:pt-6">
            <button type="button" onClick={onNewAudit} className="workspace-link text-ink-500">
              New audit
            </button>
          </div>
        )}
      </nav>
    </aside>
  );
}
