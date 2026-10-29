import React, { useState, useMemo } from 'react';
import { RoadmapItem } from '../types';
import { categoryLabel, display } from '../lib/format';
import { Card } from './ui';
import {
  Clock,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Layers,
  Filter,
  ArrowUpRight,
  Code2,
  Sparkles,
} from 'lucide-react';

interface RoadmapProps {
  days7: RoadmapItem[];
  days30: RoadmapItem[];
  days90: RoadmapItem[];
  onSelectFinding?: (findingId: string) => void;
}

type DisciplineFilter = 'ALL' | 'TECHNICAL' | 'SCHEMA' | 'CONTENT' | 'GEO_AEO' | 'CRO_UX';

function getPriorityBadgeStyle(priority?: string, timeframe?: string) {
  const p = (priority || '').toUpperCase();
  if (p.includes('P0') || timeframe === '7_days') {
    return 'bg-bad/10 text-bad border-bad/30 dark:bg-bad/20 dark:text-bad dark:border-bad/40';
  }
  if (p.includes('P1') || timeframe === '30_days') {
    return 'bg-warn/15 text-warn border-warn/40 dark:bg-warn/25 dark:text-warn dark:border-warn/50';
  }
  return 'bg-accent/10 text-accent border-accent/30 dark:bg-accent/20 dark:text-accent dark:border-accent/40';
}

function RoadmapCard({
  item,
  onSelectFinding,
}: {
  item: RoadmapItem;
  onSelectFinding?: (findingId: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const badgeClass = getPriorityBadgeStyle(item.priority_badge, item.timeframe);
  const priorityText = item.priority_badge || (item.timeframe === '7_days' ? 'P0 Blocker' : item.timeframe === '30_days' ? 'P1 Sprint' : 'P2 Strategic');

  return (
    <li className="group rounded-xl border border-line/80 bg-paper-50/70 p-4 transition-all duration-150 hover:border-line-hover hover:bg-white hover:shadow-sm dark:bg-ink-900/60 dark:hover:bg-ink-900">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-bold tracking-wider uppercase ${badgeClass}`}>
            {priorityText}
          </span>
          <span className="rounded-md border border-line bg-paper-100/80 px-2 py-0.5 text-[11px] font-medium text-ink-600 dark:bg-ink-800 dark:text-ink-400">
            {categoryLabel(item.category)}
          </span>
        </div>

        {item.estimated_hours && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ink-500">
            <Clock className="h-3 w-3 text-ink-400" />
            {item.estimated_hours}
          </span>
        )}
      </div>

      <h4 className="mt-2.5 text-sm font-semibold text-ink leading-snug group-hover:text-ink-900 dark:group-hover:text-white">
        {item.title}
      </h4>

      <p className="mt-1.5 text-xs text-ink-600 leading-relaxed dark:text-ink-300">
        {display(item.description)}
      </p>

      {item.owner_role && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-500">
          <UserCheck className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
          <span className="font-medium text-ink-700 dark:text-ink-200">Owner:</span>
          <span>{item.owner_role}</span>
        </div>
      )}

      {item.verification_step && (
        <div className="mt-3 rounded-lg border border-line/60 bg-paper-100/50 p-2.5 text-[11px] text-ink-600 dark:bg-ink-800/40 dark:text-ink-300">
          <div className="flex items-center gap-1.5 font-semibold text-ink-700 dark:text-ink-200">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>Verification Protocol:</span>
          </div>
          <p className="mt-1 leading-normal">{item.verification_step}</p>
        </div>
      )}

      <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 border-t border-line/50 pt-2 text-[11px] text-ink-400">
        <div className="flex items-center gap-2">
          <span>Impact: <b className="text-ink-700 dark:text-ink-200">{display(item.impact)}</b></span>
          <span>·</span>
          <span>Effort: <b className="text-ink-700 dark:text-ink-200">{display(item.effort)}</b></span>
        </div>

        {item.related_finding_id && onSelectFinding && (
          <button
            type="button"
            onClick={() => onSelectFinding(item.related_finding_id!)}
            className="inline-flex items-center gap-1 font-semibold text-teal-600 hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
          >
            <span>Evidence</span>
            <ArrowUpRight className="h-3 w-3" />
          </button>
        )}
      </div>
    </li>
  );
}

function Column({
  title,
  subtitle,
  items,
  badgeTone,
  onSelectFinding,
}: {
  title: string;
  subtitle: string;
  items: RoadmapItem[];
  badgeTone: string;
  onSelectFinding?: (findingId: string) => void;
}) {
  return (
    <Card className="flex flex-col border-line/90">
      <div className="border-b border-line pb-3 mb-4">
        <div className="flex items-center justify-between">
          <h3 className="font-sans text-xl font-bold text-ink">{title}</h3>
          <span className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-bold ${badgeTone}`}>
            {items.length} {items.length === 1 ? 'Action' : 'Actions'}
          </span>
        </div>
        <p className="mt-1 text-xs text-ink-500 leading-normal">{subtitle}</p>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-line bg-paper-100/40 px-4 py-8 text-center text-sm text-ink-500">
          <CheckCircle2 className="h-8 w-8 text-emerald-500/70 mb-2" />
          <p className="font-medium text-ink-700">No pending actions</p>
          <p className="mt-1 text-xs text-ink-500 max-w-[200px]">All verified criteria for this execution horizon have been resolved.</p>
        </div>
      ) : (
        <ol className="space-y-3.5 flex-1 overflow-y-auto">
          {items.map((item, index) => (
            <RoadmapCard
              key={`${item.title}-${index}`}
              item={item}
              onSelectFinding={onSelectFinding}
            />
          ))}
        </ol>
      )}
    </Card>
  );
}

export function Roadmap({
  days7,
  days30,
  days90,
  onSelectFinding,
}: RoadmapProps) {
  const [filter, setFilter] = useState<DisciplineFilter>('ALL');

  const filterMatches = (item: RoadmapItem): boolean => {
    if (filter === 'ALL') return true;
    const cat = String(item.category || '').toUpperCase();
    if (filter === 'TECHNICAL') {
      return cat.includes('TECHNICAL') || cat.includes('CRAWL') || cat.includes('SECURITY') || cat.includes('HOST');
    }
    if (filter === 'SCHEMA') {
      return cat.includes('SCHEMA');
    }
    if (filter === 'CONTENT') {
      return cat.includes('CONTENT') || cat.includes('E_E_A_T') || cat.includes('TOPICAL');
    }
    if (filter === 'GEO_AEO') {
      return cat.includes('GEO') || cat.includes('AEO') || cat.includes('AI_SEARCH');
    }
    if (filter === 'CRO_UX') {
      return cat.includes('UX') || cat.includes('CONVERSION') || cat.includes('CRO');
    }
    return true;
  };

  const filtered7 = useMemo(() => days7.filter(filterMatches), [days7, filter]);
  const filtered30 = useMemo(() => days30.filter(filterMatches), [days30, filter]);
  const filtered90 = useMemo(() => days90.filter(filterMatches), [days90, filter]);

  const totalActions = days7.length + days30.length + days90.length;
  const p0Count = days7.length;

  return (
    <div className="space-y-6">
      {/* Header and Filter Bar */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="label">STRATEGIC REMEDIATION BOARD</span>
            {p0Count > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full border border-bad/30 bg-bad/10 px-2 py-0.5 text-[11px] font-bold text-bad">
                <AlertTriangle className="h-3 w-3" />
                {p0Count} Critical P0 Blockers
              </span>
            )}
          </div>
          <h2 className="font-sans text-3xl font-extrabold text-ink tracking-tight mt-1">
            Prioritized Execution Roadmap
          </h2>
          <p className="text-sm text-ink-500 mt-1 max-w-3xl">
            Institutional 7 / 30 / 90 day tactical execution boards with assigned owner roles, estimated engineer-hours, and automated retest verification protocols.
          </p>
        </div>

        {/* Discipline Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-line bg-paper-100/60 p-1 dark:bg-ink-900/60">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              filter === 'ALL'
                ? 'bg-white text-ink shadow-sm dark:bg-ink-800 dark:text-white'
                : 'text-ink-600 hover:text-ink dark:text-ink-400 dark:hover:text-ink-200'
            }`}
          >
            All ({totalActions})
          </button>
          <button
            type="button"
            onClick={() => setFilter('TECHNICAL')}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              filter === 'TECHNICAL'
                ? 'bg-white text-ink shadow-sm dark:bg-ink-800 dark:text-white'
                : 'text-ink-600 hover:text-ink dark:text-ink-400 dark:hover:text-ink-200'
            }`}
          >
            Technical & Infrastructure
          </button>
          <button
            type="button"
            onClick={() => setFilter('SCHEMA')}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              filter === 'SCHEMA'
                ? 'bg-white text-ink shadow-sm dark:bg-ink-800 dark:text-white'
                : 'text-ink-600 hover:text-ink dark:text-ink-400 dark:hover:text-ink-200'
            }`}
          >
            Structured Data
          </button>
          <button
            type="button"
            onClick={() => setFilter('GEO_AEO')}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              filter === 'GEO_AEO'
                ? 'bg-white text-ink shadow-sm dark:bg-ink-800 dark:text-white'
                : 'text-ink-600 hover:text-ink dark:text-ink-400 dark:hover:text-ink-200'
            }`}
          >
            GEO & AEO Citations
          </button>
          <button
            type="button"
            onClick={() => setFilter('CRO_UX')}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              filter === 'CRO_UX'
                ? 'bg-white text-ink shadow-sm dark:bg-ink-800 dark:text-white'
                : 'text-ink-600 hover:text-ink dark:text-ink-400 dark:hover:text-ink-200'
            }`}
          >
            CRO & Conversion
          </button>
          <button
            type="button"
            onClick={() => setFilter('CONTENT')}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              filter === 'CONTENT'
                ? 'bg-white text-ink shadow-sm dark:bg-ink-800 dark:text-white'
                : 'text-ink-600 hover:text-ink dark:text-ink-400 dark:hover:text-ink-200'
            }`}
          >
            Content & Copy
          </button>
        </div>
      </div>

      {/* 3-Horizon Tactical Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Column
          title="7 Days"
          subtitle="P0 High-Impact Blockers & Quick Wins (Immediate sprint)"
          items={filtered7}
          badgeTone="bg-bad/10 text-bad border border-bad/30"
          onSelectFinding={onSelectFinding}
        />
        <Column
          title="30 Days"
          subtitle="P1 Core Architecture & Answer Engine Indexing (Month 1)"
          items={filtered30}
          badgeTone="bg-warn/15 text-warn border border-warn/40"
          onSelectFinding={onSelectFinding}
        />
        <Column
          title="90 Days"
          subtitle="P2 Strategic Moats, E-E-A-T & Authority Compounding (Quarter 1)"
          items={filtered90}
          badgeTone="bg-accent/10 text-accent border border-accent/30"
          onSelectFinding={onSelectFinding}
        />
      </div>
    </div>
  );
}
