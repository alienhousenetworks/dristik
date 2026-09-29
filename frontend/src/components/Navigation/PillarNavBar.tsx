import React from 'react';
import { TabId, ExecutiveReport } from '../../types';
import { synthesizePillars } from '../../lib/pillarSynthesis';
import { cn, ScorePill } from '../ui';
import {
  LayoutDashboard,
  Search,
  Sparkles,
  Bot,
  Zap,
  Swords,
  Landmark,
  FileSpreadsheet,
  FileCheck2,
  FileCode2,
  CalendarClock,
  ShieldCheck,
  FileText,
  PlusCircle,
  Coins,
} from 'lucide-react';

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
  pagesCount = 0,
  onNewAudit,
}: PillarNavBarProps) {
  const rollup = synthesizePillars(report);
  const patchesCount = (report?.code_patches?.length || 0) + (report?.remediation_patches?.length || 0);

  // Group 1: Executive
  const executiveItems = [
    {
      id: 'overview' as TabId,
      label: 'Executive Overview',
      icon: LayoutDashboard,
      score: report && typeof report.scores?.overall_score === 'number' ? Math.round(report.scores.overall_score) : undefined,
    },
    {
      id: 'report' as TabId,
      label: 'Presentation Report',
      icon: FileText,
    },
  ];

  // Group 2: Core Disciplines (Separated & Industry Standard)
  const disciplineItems = [
    {
      id: 'seo' as TabId,
      label: 'SEO (Technical & On-Page)',
      icon: Search,
      score: report ? rollup.seo.score : undefined,
      badge: rollup.seo.findingsCount || undefined,
    },
    {
      id: 'geo' as TabId,
      label: 'GEO (Generative Engines)',
      icon: Sparkles,
      score: report ? rollup.geo.score : undefined,
      badge: rollup.geo.findingsCount || undefined,
    },
    {
      id: 'aeo' as TabId,
      label: 'AEO (Answer Engine & Agents)',
      icon: Bot,
      score: report ? rollup.aeo.score : undefined,
      badge: rollup.aeo.findingsCount || undefined,
    },
    {
      id: 'cro' as TabId,
      label: 'CRO & UX Optimization',
      icon: Zap,
      score: report ? rollup.cro.score : undefined,
      badge: rollup.cro.findingsCount || undefined,
    },
    {
      id: 'competitors' as TabId,
      label: 'Competitor Intelligence',
      icon: Swords,
      score: report ? rollup.competitors.score : undefined,
      badge: rollup.competitors.findingsCount || undefined,
    },
    {
      id: 'external_authority' as TabId,
      label: 'External Authority',
      icon: Landmark,
      score: undefined,
      badge: undefined,
    },
  ];

  // Group 3: Diagnostics
  const diagnosticItems = [
    {
      id: 'pages' as TabId,
      label: 'Page Inspector',
      icon: FileSpreadsheet,
      badge: pagesCount || report?.crawl_manifest?.pages?.length || undefined,
    },
    {
      id: 'findings' as TabId,
      label: 'Evidence Ledger',
      icon: FileCheck2,
      badge: findingsCount || report?.findings?.length || undefined,
    },
    {
      id: 'costing' as TabId,
      label: 'Unit Economics & Cost Ledger',
      icon: Coins,
      badge: report?.telemetry?.estimated_cost_usd ? `$${report.telemetry.estimated_cost_usd.toFixed(2)}` : undefined,
    },
  ];

  // Group 4: Engineering & Remediation
  const engineeringItems = [
    {
      id: 'patches' as TabId,
      label: 'Dev Patch Pack',
      icon: FileCode2,
      badge: patchesCount || undefined,
    },
    {
      id: 'roadmap' as TabId,
      label: 'Action Roadmap',
      icon: CalendarClock,
    },
    {
      id: 'verification' as TabId,
      label: 'Verification & Regression',
      icon: ShieldCheck,
    },
  ];

  // Helper to determine if a tab is active (supporting aliases)
  const isTabActive = (id: TabId) => {
    if (tab === id) return true;
    if (id === 'seo' && (tab === 'search_intelligence' || tab === 'search_console')) return true;
    if (id === 'geo' && (tab === 'ai_search_intelligence' || tab === 'ai_citations' || tab === 'ai_search')) return true;
    if (id === 'aeo' && tab === 'brand_entity_intelligence') return true;
    if (id === 'cro' && (tab === 'conversion_intelligence' || tab === 'website_experience')) return true;
    if (id === 'competitors' && (tab === 'perspectives' || tab === 'lead_gen')) return true;
    if ((id === 'costing' || id === 'costs') && (tab === 'costing' || tab === 'costs')) return true;
    return false;
  };

  return (
    <aside className="no-print lg:w-64 xl:w-72 shrink-0 border-b lg:border-b-0 lg:border-r border-line bg-paper-100/80 backdrop-blur-sm">
      <nav className="lg:sticky lg:top-14 lg:h-[calc(100vh-3.5rem)] lg:overflow-y-auto px-3 py-3 lg:px-4 lg:py-5 flex lg:flex-col gap-5 overflow-x-auto">
        
        {/* EXECUTIVE */}
        <div className="space-y-1">
          <p className="hidden lg:block text-[10px] font-mono font-bold uppercase tracking-[0.14em] text-ink-400 px-2.5 mb-1.5">
            Executive
          </p>
          {executiveItems.map((item) => {
            const Icon = item.icon;
            const active = isTabActive(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={cn('workspace-link text-xs font-medium', active && 'is-active')}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className={cn("w-4 h-4 shrink-0", active ? "text-paper-100" : "text-ink-500")} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.score != null && <ScorePill score={item.score} />}
              </button>
            );
          })}
        </div>

        {/* CORE DISCIPLINES */}
        <div className="space-y-1">
          <div className="flex items-center justify-between px-2.5 mb-1.5">
            <p className="hidden lg:block text-[10px] font-mono font-bold uppercase tracking-[0.14em] text-ink-400">
              Core Disciplines
            </p>
            <span className="hidden lg:inline text-[9px] font-mono px-1.5 py-0.5 rounded bg-pine/10 text-pine font-semibold">
              Separated
            </span>
          </div>
          {disciplineItems.map((item) => {
            const Icon = item.icon;
            const active = isTabActive(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={cn('workspace-link text-xs font-medium', active && 'is-active')}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className={cn("w-4 h-4 shrink-0", active ? "text-paper-100" : "text-ink-500")} />
                  <span className="truncate">{item.label}</span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {item.badge != null && (
                    <span className={cn(
                      "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                      active ? "bg-white/20 text-paper-100" : "bg-ink/5 text-ink-600"
                    )}>
                      {item.badge}
                    </span>
                  )}
                  {item.score != null && <ScorePill score={item.score} />}
                </div>
              </button>
            );
          })}
        </div>

        {/* DEEP DIAGNOSTICS */}
        <div className="space-y-1">
          <p className="hidden lg:block text-[10px] font-mono font-bold uppercase tracking-[0.14em] text-ink-400 px-2.5 mb-1.5">
            Diagnostics
          </p>
          {diagnosticItems.map((item) => {
            const Icon = item.icon;
            const active = isTabActive(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={cn('workspace-link text-xs font-medium', active && 'is-active')}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className={cn("w-4 h-4 shrink-0", active ? "text-paper-100" : "text-ink-500")} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge != null && (
                  <span className={cn(
                    "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                    active ? "bg-white/20 text-paper-100" : "bg-ink/5 text-ink-600"
                  )}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* ENGINEERING & REMEDIATION */}
        <div className="space-y-1">
          <p className="hidden lg:block text-[10px] font-mono font-bold uppercase tracking-[0.14em] text-ink-400 px-2.5 mb-1.5">
            Engineering
          </p>
          {engineeringItems.map((item) => {
            const Icon = item.icon;
            const active = isTabActive(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={cn('workspace-link text-xs font-medium', active && 'is-active')}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className={cn("w-4 h-4 shrink-0", active ? "text-paper-100" : "text-ink-500")} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge != null && (
                  <span className={cn(
                    "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                    active ? "bg-white/20 text-paper-100" : "bg-ink/5 text-ink-600"
                  )}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {onNewAudit && (
          <div className="lg:mt-auto lg:pt-4 border-t border-line/60">
            <button
              type="button"
              onClick={onNewAudit}
              className="workspace-link text-xs text-ink-600 hover:text-ink font-semibold"
            >
              <div className="flex items-center gap-2">
                <PlusCircle className="w-4 h-4 text-pine" />
                <span>New Audit</span>
              </div>
            </button>
          </div>
        )}
      </nav>
    </aside>
  );
}
