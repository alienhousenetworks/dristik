import React from 'react';
import { ExecutiveReport, TabId } from '../types';
import { synthesizePillars } from '../lib/pillarSynthesis';
import { cn } from './ui';

interface WebsiteIntelligenceTriadHeroProps {
  report: ExecutiveReport;
  onNavigate: (tab: TabId) => void;
  activeTab?: TabId;
}

export function WebsiteIntelligenceTriadHero({
  report,
  onNavigate,
}: WebsiteIntelligenceTriadHeroProps) {
  const rollup = synthesizePillars(report);

  const pillars: Array<{
    id: TabId;
    label: string;
    score: number;
    hint: string;
  }> = [
    {
      id: 'search_intelligence',
      label: 'Search',
      score: rollup.search_intelligence.score,
      hint: rollup.search_intelligence.headline,
    },
    {
      id: 'ai_search_intelligence',
      label: 'AI search',
      score: rollup.ai_search_intelligence.score,
      hint: rollup.ai_search_intelligence.headline,
    },
    {
      id: 'website_experience',
      label: 'Experience',
      score: rollup.sxo_score,
      hint: 'Speed, mobile, and how easy the site is to use.',
    },
    {
      id: 'conversion_intelligence',
      label: 'Conversion',
      score: rollup.conversion_intelligence.score,
      hint: rollup.conversion_intelligence.headline,
    },
    {
      id: 'brand_entity_intelligence',
      label: 'Brand',
      score: rollup.brand_entity_intelligence.score,
      hint: rollup.brand_entity_intelligence.headline,
    },
  ];

  const overall = Math.round(report.scores?.overall_score || 0);
  const tone = overall >= 80 ? 'text-good' : overall >= 60 ? 'text-warn' : 'text-bad';

  return (
    <section className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <p className="label">Audit</p>
          <h2 className="font-serif text-3xl text-ink tracking-tight mt-1">{report.domain}</h2>
          <p className="text-sm text-ink-500 mt-1">{report.website_url}</p>
        </div>
        <div className="text-left sm:text-right">
          <p className="label">Overall</p>
          <p className={cn('font-serif text-5xl leading-none mt-1', tone)}>{overall}</p>
          <p className="text-sm text-ink-500 mt-1">
            {report.scores?.grade} · {report.scores?.health_label}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
        {pillars.map((pillar) => (
          <button
            key={pillar.id}
            type="button"
            onClick={() => onNavigate(pillar.id)}
            className="card p-4 text-left hover:border-ink-300 transition-colors"
          >
            <div className="flex items-baseline justify-between gap-2">
              <p className="label">{pillar.label}</p>
              <p className="font-serif text-2xl text-ink leading-none">{pillar.score}</p>
            </div>
            <p className="mt-2 text-xs text-ink-500 leading-relaxed line-clamp-2">{pillar.hint}</p>
          </button>
        ))}
      </div>
    </section>
  );
}
