import React, { useState, useMemo } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Sparkles,
  CloudOff,
  Clock,
  MinusCircle,
  Search,
  X,
  ChevronDown,
  ChevronRight,
  Filter,
  Layers,
  Copy,
  Check,
  Terminal,
  FileCode,
  Bug,
  TrendingDown,
  Wrench,
  Table,
  LayoutList,
  Info,
  Database,
  Globe,
  SlidersHorizontal,
  Bot,
  Zap,
} from 'lucide-react';
import { ExecutiveReport } from '../../types';
import { AUDIT_PARTS } from './catalog';
import { ChapterPanel } from './ChapterPanel';
import { resolveAuditIndex, STATUS_LABEL } from './resolveAuditIndex';
import { AuditedCheck, ResolvedAuditSection, SectionStatus } from './types';

// ============================================================================
// STYLING HELPERS & BADGES
// ============================================================================

export function getStatusTheme(status: SectionStatus) {
  switch (status) {
    case 'ISSUE_VERIFIED':
      return {
        badge: 'text-rose-700 dark:text-rose-400 bg-rose-500/15 border-rose-500/30',
        borderAccent: 'border-l-4 border-l-rose-500',
        icon: AlertTriangle,
        iconColor: 'text-rose-500',
        segmentColor: 'bg-rose-500',
      };
    case 'NO_ISSUE':
      return {
        badge: 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/15 border-emerald-500/30',
        borderAccent: 'border-l-4 border-l-emerald-500',
        icon: CheckCircle2,
        iconColor: 'text-emerald-500',
        segmentColor: 'bg-emerald-500',
      };
    case 'MEASURED':
      return {
        badge: 'text-sky-700 dark:text-sky-400 bg-sky-500/15 border-sky-500/30',
        borderAccent: 'border-l-4 border-l-sky-500',
        icon: Activity,
        iconColor: 'text-sky-500',
        segmentColor: 'bg-sky-500',
      };
    case 'INFERRED':
      return {
        badge: 'text-amber-700 dark:text-amber-400 bg-amber-500/15 border-amber-500/30',
        borderAccent: 'border-l-4 border-l-amber-500',
        icon: Sparkles,
        iconColor: 'text-amber-500',
        segmentColor: 'bg-amber-500',
      };
    case 'DATA_UNAVAILABLE':
      return {
        badge: 'text-slate-600 dark:text-slate-400 bg-slate-500/15 border-slate-400/30',
        borderAccent: 'border-l-4 border-l-slate-400',
        icon: CloudOff,
        iconColor: 'text-slate-400',
        segmentColor: 'bg-slate-400',
      };
    case 'NOT_TESTED':
      return {
        badge: 'text-slate-500 dark:text-slate-400 bg-slate-200/50 dark:bg-slate-800 border-slate-300 dark:border-slate-700',
        borderAccent: 'border-l-4 border-l-slate-300 dark:border-l-slate-700',
        icon: Clock,
        iconColor: 'text-slate-400',
        segmentColor: 'bg-slate-300 dark:bg-slate-700',
      };
    case 'NOT_APPLICABLE':
    default:
      return {
        badge: 'text-ink-400 bg-paper-100 border-line',
        borderAccent: 'border-l-4 border-l-line',
        icon: MinusCircle,
        iconColor: 'text-ink-300',
        segmentColor: 'bg-paper-200 dark:bg-ink-800',
      };
  }
}

function StatusPill({ status }: { status: SectionStatus }) {
  const theme = getStatusTheme(status);
  const Icon = theme.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-semibold border ${theme.badge}`}
    >
      <Icon className={`w-3.5 h-3.5 ${theme.iconColor}`} />
      <span>{STATUS_LABEL[status]}</span>
    </span>
  );
}

function severityClass(sev: string): string {
  switch (sev?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-rose-600 text-white shadow-xs border-rose-700';
    case 'HIGH':
      return 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/40';
    case 'MEDIUM':
      return 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/40';
    case 'LOW':
      return 'bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/40';
    default:
      return 'bg-paper-100 text-ink-600 border-line';
  }
}

type CheckFilter = 'ALL' | 'ISSUES' | 'MEASURED' | 'GAPS';
type ViewMode = 'DOSSIER' | 'MATRIX';

// ============================================================================
// MAIN COMPONENT: AuditIndex
// ============================================================================

export function AuditIndex({
  report,
  expandChecks = false,
}: {
  report: ExecutiveReport;
  expandChecks?: boolean;
}) {
  const index = useMemo(() => resolveAuditIndex(report), [report]);
  const [filter, setFilter] = useState<CheckFilter>('ALL');
  const [selectedPart, setSelectedPart] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [onlyWithDefects, setOnlyWithDefects] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('DOSSIER');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [expandedProofs, setExpandedProofs] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleSection = (num: string) => {
    setExpandedSections((prev) => {
      const isCurrentlyOpen = prev[num] !== false;
      return { ...prev, [num]: !isCurrentlyOpen };
    });
  };

  const toggleProofs = (num: string) => {
    setExpandedProofs((prev) => ({ ...prev, [num]: !prev[num] }));
  };

  const handleCopy = (text: string, id: string) => {
    try {
      if (navigator?.clipboard?.writeText) {
        navigator.clipboard.writeText(text);
      }
    } catch {
      // ignore
    }
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Expand / Collapse all
  const handleToggleAll = (expand: boolean) => {
    const newState: Record<string, boolean> = {};
    index.sections.forEach((s) => {
      newState[s.number] = expand;
    });
    setExpandedSections(newState);
    setExpandedProofs(newState);
  };

  // Filter sections based on user search, status filter, selected part, and defects toggle
  const filteredSections = useMemo(() => {
    return index.sections.filter((section) => {
      // 1. Part filter
      if (selectedPart !== 'ALL' && section.part !== selectedPart) {
        return false;
      }

      // 2. Defects only toggle
      if (onlyWithDefects && section.status !== 'ISSUE_VERIFIED' && section.findings.length === 0) {
        return false;
      }

      // 3. Status filter
      if (filter === 'ISSUES') {
        if (section.status !== 'ISSUE_VERIFIED' && section.findings.length === 0) return false;
      } else if (filter === 'MEASURED') {
        if (section.status !== 'MEASURED' && section.status !== 'NO_ISSUE') return false;
      } else if (filter === 'GAPS') {
        if (
          section.status !== 'DATA_UNAVAILABLE' &&
          section.status !== 'NOT_TESTED' &&
          section.status !== 'NOT_APPLICABLE'
        )
          return false;
      }

      // 4. Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const numMatch =
          section.number.toLowerCase() === q ||
          `ch ${section.number.toLowerCase()}` === q ||
          section.number.toLowerCase().includes(q);
        const titleMatch = section.title.toLowerCase().includes(q);
        const summaryMatch = section.summary.toLowerCase().includes(q);
        const agentMatch =
          section.analysis?.agentName?.toLowerCase().includes(q) ||
          section.analysis?.agentId?.toLowerCase().includes(q);
        const findingMatch = section.findings.some(
          (f) =>
            f.title.toLowerCase().includes(q) ||
            f.id.toLowerCase().includes(q) ||
            (f.action && f.action.toLowerCase().includes(q))
        );
        const checkMatch = section.auditedChecks.some(
          (c) => c.label.toLowerCase().includes(q) || c.result.toLowerCase().includes(q)
        );

        if (!numMatch && !titleMatch && !summaryMatch && !agentMatch && !findingMatch && !checkMatch) {
          return false;
        }
      }

      return true;
    });
  }, [index.sections, selectedPart, onlyWithDefects, filter, searchQuery]);

  // Total findings across all sections
  const totalFindingsCount = useMemo(() => {
    return index.sections.reduce((acc, s) => acc + s.findingCount, 0);
  }, [index.sections]);

  // Status breakdown counts
  const verifiedCount = index.counts['ISSUE_VERIFIED'] || 0;
  const measuredCleanCount = (index.counts['MEASURED'] || 0) + (index.counts['NO_ISSUE'] || 0);
  const inferredCount = index.counts['INFERRED'] || 0;
  const gapsCount =
    (index.counts['DATA_UNAVAILABLE'] || 0) +
    (index.counts['NOT_TESTED'] || 0) +
    (index.counts['NOT_APPLICABLE'] || 0);
  const totalChapters = index.sections.length || 70;

  // Crawled pages count
  const pagesCount = report.crawl_manifest?.pages?.length || 0;
  const discoveredCount = report.crawl_manifest?.total_pages_discovered || pagesCount;

  // Active parts that have sections
  const partsWithSections = useMemo(() => {
    return AUDIT_PARTS.map((p) => {
      const partSections = filteredSections.filter((s) => s.part === p.id);
      return {
        ...p,
        sections: partSections,
      };
    }).filter((p) => p.sections.length > 0);
  }, [filteredSections]);

  return (
    <div className="space-y-6">
      {/* ─────────────────────────────────────────────────────────────
          1. ENTERPRISE AUDIT COMMAND HUB & TELEMETRY
          ───────────────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-line/80 bg-paper-50/60 p-5 shadow-xs transition-all dark:bg-ink-950/20">
        {/* Top Scope & Standard Indicator */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1.5 rounded-md bg-pine-600/10 px-2.5 py-1 font-mono text-[11px] font-bold uppercase tracking-wider text-pine-700 dark:bg-pine-400/15 dark:text-pine-300">
                <ShieldCheck className="h-3.5 w-3.5" />
                Enterprise SEO Audit Standard
              </span>
              <span className="rounded-md border border-line bg-paper px-2 py-0.5 font-mono text-[11px] text-ink-500">
                55 Chapters · Appendices A–O
              </span>
            </div>
            <p className="text-sm font-medium text-ink-800 dark:text-ink-200">
              {index.sampleNotice}
            </p>
          </div>

          {/* Quick Scope Badge */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-lg border border-line bg-paper px-3 py-1.5 text-xs font-mono text-ink-600 shadow-2xs">
              <Globe className="h-3.5 w-3.5 text-pine-600" />
              <span>
                Deterministic Sample: <strong className="text-ink">{pagesCount}</strong> / {discoveredCount} URLs
              </span>
            </div>
          </div>
        </div>

        {/* Segmented Audit Telemetry Progress Strip */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-ink-500">
              Audit Telemetry Breakdown
            </span>
            <span className="font-mono text-[11px] text-ink-500">
              {verifiedCount} verified issues · {measuredCleanCount} clean/measured · {inferredCount} inferred · {gapsCount} gaps
            </span>
          </div>

          {/* Stacked Progress Bar */}
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-paper-200/80 p-0.5 shadow-inner dark:bg-ink-800">
            {verifiedCount > 0 && (
              <button
                type="button"
                onClick={() => setFilter('ISSUES')}
                title={`Verified Issues: ${verifiedCount} chapters (Click to filter)`}
                style={{ width: `${(verifiedCount / totalChapters) * 100}%` }}
                className="h-full rounded-l-full bg-rose-500 transition-opacity hover:opacity-85"
              />
            )}
            {measuredCleanCount > 0 && (
              <button
                type="button"
                onClick={() => setFilter('MEASURED')}
                title={`Measured & Clean: ${measuredCleanCount} chapters (Click to filter)`}
                style={{ width: `${(measuredCleanCount / totalChapters) * 100}%` }}
                className="h-full bg-emerald-500 transition-opacity hover:opacity-85"
              />
            )}
            {inferredCount > 0 && (
              <button
                type="button"
                onClick={() => setFilter('ALL')}
                title={`Inferred / Strategy: ${inferredCount} chapters`}
                style={{ width: `${(inferredCount / totalChapters) * 100}%` }}
                className="h-full bg-amber-500 transition-opacity hover:opacity-85"
              />
            )}
            {gapsCount > 0 && (
              <button
                type="button"
                onClick={() => setFilter('GAPS')}
                title={`Data Gaps & Untested: ${gapsCount} chapters (Click to filter)`}
                style={{ width: `${(gapsCount / totalChapters) * 100}%` }}
                className="h-full rounded-r-full bg-slate-400 transition-opacity hover:opacity-85"
              />
            )}
          </div>
        </div>

        {/* Key KPI Stats Grid */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
            <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400">
              <AlertTriangle className="h-3 w-3" />
              Verified Defects
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tracking-tight text-rose-700 dark:text-rose-300">
                {verifiedCount}
              </span>
              <span className="text-xs text-rose-600/80">chapters</span>
            </div>
            <p className="mt-0.5 text-[11px] text-ink-500">
              {totalFindingsCount} recorded finding{totalFindingsCount === 1 ? '' : 's'}
            </p>
          </div>

          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
            <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              Measured &amp; Clean
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tracking-tight text-emerald-700 dark:text-emerald-300">
                {measuredCleanCount}
              </span>
              <span className="text-xs text-emerald-600/80">chapters</span>
            </div>
            <p className="mt-0.5 text-[11px] text-ink-500">
              Deterministic DOM &amp; headers
            </p>
          </div>

          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
            <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              <Sparkles className="h-3 w-3" />
              Inferred &amp; Strategy
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tracking-tight text-amber-700 dark:text-amber-300">
                {inferredCount}
              </span>
              <span className="text-xs text-amber-600/80">chapters</span>
            </div>
            <p className="mt-0.5 text-[11px] text-ink-500">
              Executive &amp; architectural guidance
            </p>
          </div>

          <div className="rounded-lg border border-slate-400/20 bg-slate-500/5 p-3">
            <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-400">
              <CloudOff className="h-3 w-3" />
              Data Gaps &amp; Untested
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tracking-tight text-slate-700 dark:text-slate-300">
                {gapsCount}
              </span>
              <span className="text-xs text-slate-600/80">chapters</span>
            </div>
            <p className="mt-0.5 text-[11px] text-ink-500">
              Unconnected integrations
            </p>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. COMMAND TOOLBAR: SEARCH, FILTERS & VIEW MODE
          ───────────────────────────────────────────────────────────── */}
      <div className="sticky top-2 z-20 space-y-3 rounded-xl border border-line/80 bg-paper/95 p-3.5 shadow-sm backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Universal Search Input */}
          <div className="relative min-w-[260px] flex-1 sm:max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-ink-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search chapters, topics, checks, findings, or agent IDs..."
              className="w-full rounded-lg border border-line bg-paper-50/70 py-2 pl-9 pr-9 text-xs text-ink placeholder:text-ink-400 focus:border-pine-600 focus:bg-paper focus:outline-none focus:ring-1 focus:ring-pine-600"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 rounded-full p-0.5 text-ink-400 hover:text-ink"
                title="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center rounded-lg border border-line bg-paper-50 p-0.5">
              <button
                type="button"
                onClick={() => setViewMode('DOSSIER')}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  viewMode === 'DOSSIER'
                    ? 'bg-paper text-ink shadow-xs font-semibold'
                    : 'text-ink-500 hover:text-ink'
                }`}
                title="Card Dossier View"
              >
                <LayoutList className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Dossier Cards</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('MATRIX')}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  viewMode === 'MATRIX'
                    ? 'bg-paper text-ink shadow-xs font-semibold'
                    : 'text-ink-500 hover:text-ink'
                }`}
                title="Audit Matrix Table View"
              >
                <Table className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Matrix Table</span>
              </button>
            </div>

            {/* Expand / Collapse All */}
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => handleToggleAll(true)}
                className="rounded-lg border border-line bg-paper px-2.5 py-1.5 text-xs font-medium text-ink-600 hover:bg-paper-100"
              >
                Expand All
              </button>
              <button
                type="button"
                onClick={() => handleToggleAll(false)}
                className="rounded-lg border border-line bg-paper px-2.5 py-1.5 text-xs font-medium text-ink-600 hover:bg-paper-100"
              >
                Collapse All
              </button>
            </div>

            {/* Defects Only Toggle */}
            <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-line bg-paper px-2.5 py-1.5 text-xs font-medium text-ink-700 hover:bg-paper-50">
              <input
                type="checkbox"
                checked={onlyWithDefects}
                onChange={(e) => setOnlyWithDefects(e.target.checked)}
                className="rounded text-pine-600 focus:ring-pine-500"
              />
              <span>Defects Only</span>
            </label>
          </div>
        </div>

        {/* Status Filter Segment Pills */}
        <div className="flex flex-wrap items-center gap-2 border-t border-line/60 pt-2.5">
          <span className="font-mono text-[11px] text-ink-400">Filter checks:</span>

          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-xs transition-colors ${
              filter === 'ALL'
                ? 'bg-ink text-paper shadow-xs font-semibold'
                : 'border border-line bg-paper text-ink-600 hover:border-ink-400'
            }`}
          >
            <span>All Checks</span>
            <span className="rounded bg-paper-200/50 px-1 py-0.2 text-[10px] text-current">
              {index.sections.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setFilter('ISSUES')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-xs transition-colors ${
              filter === 'ISSUES'
                ? 'bg-rose-600 text-white shadow-xs font-semibold'
                : 'border border-rose-500/30 bg-paper text-rose-700 dark:text-rose-400 hover:bg-rose-500/10'
            }`}
          >
            <AlertTriangle className="h-3 w-3" />
            <span>Verified Issues Only</span>
            <span className="rounded bg-rose-500/20 px-1 py-0.2 text-[10px] font-bold">
              {verifiedCount}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setFilter('MEASURED')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-xs transition-colors ${
              filter === 'MEASURED'
                ? 'bg-emerald-600 text-white shadow-xs font-semibold'
                : 'border border-emerald-500/30 bg-paper text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/10'
            }`}
          >
            <CheckCircle2 className="h-3 w-3" />
            <span>Measured / Clean</span>
            <span className="rounded bg-emerald-500/20 px-1 py-0.2 text-[10px] font-bold">
              {measuredCleanCount}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setFilter('GAPS')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-xs transition-colors ${
              filter === 'GAPS'
                ? 'bg-slate-700 text-white shadow-xs font-semibold'
                : 'border border-line bg-paper text-ink-600 hover:border-ink-400'
            }`}
          >
            <CloudOff className="h-3 w-3" />
            <span>Data Gaps &amp; Untested</span>
            <span className="rounded bg-paper-200/60 px-1 py-0.2 text-[10px]">
              {gapsCount}
            </span>
          </button>
        </div>

        {/* Part Jump Selector */}
        <div className="flex items-center gap-1.5 overflow-x-auto border-t border-line/60 pt-2 text-xs no-scrollbar">
          <span className="shrink-0 font-mono text-[10px] uppercase text-ink-400">Jump to Part:</span>
          <button
            type="button"
            onClick={() => setSelectedPart('ALL')}
            className={`shrink-0 rounded px-2 py-0.5 font-mono text-[11px] transition-colors ${
              selectedPart === 'ALL'
                ? 'bg-pine-600 text-white font-bold'
                : 'bg-paper-100 text-ink-600 hover:bg-paper-200'
            }`}
          >
            All Parts
          </button>
          {AUDIT_PARTS.map((part) => (
            <button
              key={part.id}
              type="button"
              onClick={() => setSelectedPart(part.id)}
              className={`shrink-0 rounded px-2 py-0.5 font-mono text-[11px] transition-colors ${
                selectedPart === part.id
                  ? 'bg-pine-600 text-white font-bold'
                  : 'bg-paper-100 text-ink-600 hover:bg-paper-200'
              }`}
            >
              Part {part.id}
            </button>
          ))}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. MAIN CONTENT: DOSSIER CARDS VIEW OR MATRIX TABLE VIEW
          ───────────────────────────────────────────────────────────── */}

      {/* Empty State */}
      {filteredSections.length === 0 && (
        <div className="rounded-xl border border-line bg-paper p-12 text-center">
          <SlidersHorizontal className="mx-auto h-8 w-8 text-ink-300" />
          <h4 className="mt-3 text-base font-semibold text-ink">No matching audit chapters found</h4>
          <p className="mt-1 text-xs text-ink-500">
            No sections match your active search &ldquo;{searchQuery}&rdquo; and filter criteria.
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery('');
              setFilter('ALL');
              setSelectedPart('ALL');
              setOnlyWithDefects(false);
            }}
            className="mt-4 rounded-lg bg-pine-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-pine-700"
          >
            Reset All Filters
          </button>
        </div>
      )}

      {/* MATRIX TABLE VIEW */}
      {viewMode === 'MATRIX' && filteredSections.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-line bg-paper shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-line bg-paper-100/70 font-mono text-[11px] uppercase tracking-wider text-ink-500">
                <tr>
                  <th className="py-2.5 pl-4 pr-2">Ch #</th>
                  <th className="px-3 py-2.5">Title &amp; Scope</th>
                  <th className="px-3 py-2.5">Part</th>
                  <th className="px-3 py-2.5">Status</th>
                  <th className="px-3 py-2.5">Defects</th>
                  <th className="px-3 py-2.5">Specialist Agent</th>
                  <th className="py-2.5 pl-3 pr-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {filteredSections.map((section) => {
                  const theme = getStatusTheme(section.status);
                  const isExpanded = expandedSections[section.number];
                  return (
                    <React.Fragment key={section.number}>
                      <tr className="transition-colors hover:bg-paper-50">
                        <td className="py-3 pl-4 pr-2 font-mono font-bold text-ink-700">
                          {section.number}
                        </td>
                        <td className="px-3 py-3">
                          <p className="font-semibold text-ink">{section.title}</p>
                          <p className="truncate font-mono text-[10px] text-ink-400 max-w-sm">
                            {section.coverage}
                          </p>
                        </td>
                        <td className="px-3 py-3 font-mono text-[11px] text-ink-500">
                          Part {section.part}
                        </td>
                        <td className="px-3 py-3">
                          <StatusPill status={section.status} />
                        </td>
                        <td className="px-3 py-3">
                          {section.findingCount > 0 ? (
                            <span className="inline-flex items-center gap-1 rounded bg-rose-500/15 px-2 py-0.5 font-mono text-[11px] font-bold text-rose-700 dark:text-rose-400">
                              <AlertTriangle className="h-3 w-3" />
                              {section.findingCount} flagged
                            </span>
                          ) : (
                            <span className="font-mono text-[11px] text-ink-400">—</span>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          {section.analysis ? (
                            <span className="font-mono text-[11px] text-ink-700 dark:text-ink-300">
                              {section.analysis.agentName}
                            </span>
                          ) : (
                            <span className="font-mono text-[11px] text-ink-400">—</span>
                          )}
                        </td>
                        <td className="py-3 pl-3 pr-4 text-right">
                          <button
                            type="button"
                            onClick={() => toggleSection(section.number)}
                            className="rounded border border-line bg-paper px-2 py-1 font-mono text-[11px] font-medium text-ink-600 hover:bg-paper-100"
                          >
                            {isExpanded ? 'Hide' : 'Inspect'}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Row Inspector */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="bg-paper-50/60 p-4">
                            <div className="space-y-4">
                              <p className="text-sm leading-relaxed text-ink-800 dark:text-ink-200">
                                {section.summary}
                              </p>

                              <ChapterPanel
                                report={report}
                                number={section.number}
                                lineStatuses={(section.auditedChecks || []).map((check) => check.status)}
                              />

                              {/* Findings inline */}
                              {section.findings.length > 0 && (
                                <div className="space-y-2">
                                  <span className="font-mono text-[11px] font-bold uppercase text-rose-700">
                                    Verified Defects ({section.findingCount}):
                                  </span>
                                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                                    {section.findings.map((f) => (
                                      <div
                                        key={f.id}
                                        className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs"
                                      >
                                        <div className="flex items-center gap-1.5">
                                          <span
                                            className={`rounded border px-1.5 py-0.2 font-mono text-[9px] font-bold ${severityClass(
                                              f.severity
                                            )}`}
                                          >
                                            {f.severity}
                                          </span>
                                          <span className="font-mono text-[10px] text-ink-500">
                                            {f.id}
                                          </span>
                                        </div>
                                        <p className="mt-1 font-semibold text-ink">{f.title}</p>
                                        {f.action && (
                                          <p className="mt-1 text-ink-600">
                                            <strong>Action:</strong> {f.action}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
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
      )}

      {/* DOSSIER CARDS VIEW */}
      {viewMode === 'DOSSIER' &&
        partsWithSections.map((part) => (
          <div key={part.id} className="space-y-4">
            {/* Part Section Header */}
            <div className="flex items-center justify-between border-b-2 border-line/80 pb-2">
              <div className="flex items-center gap-2">
                <span className="rounded bg-paper-100 px-2 py-0.5 font-mono text-xs font-bold text-ink-600 border border-line">
                  Part {part.id}
                </span>
                <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink-800 dark:text-ink-100">
                  {part.title}
                </h3>
              </div>
              <span className="font-mono text-[11px] text-ink-400">
                {part.sections.length} {part.sections.length === 1 ? 'chapter' : 'chapters'}
              </span>
            </div>

            {/* Chapters In This Part */}
            <div className="space-y-4">
              {part.sections.map((section) => {
                const theme = getStatusTheme(section.status);
                const isAutoOpen =
                  expandedSections[section.number] !== false ||
                  expandChecks ||
                  Boolean(searchQuery.trim());

                return (
                  <article
                    key={section.number}
                    className={`rounded-xl border border-line/80 bg-paper p-5 shadow-xs transition-all hover:border-line hover:shadow-sm ${theme.borderAccent}`}
                  >
                    {/* Header */}
                    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line/60 pb-3.5">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-md border border-line bg-paper-100 px-2 py-0.5 font-mono text-xs font-bold text-ink-700 dark:bg-ink-900 dark:text-ink-300">
                            {section.number}
                          </span>
                          <h4 className="text-base font-semibold tracking-tight text-ink">
                            {section.title}
                          </h4>
                          {section.findingCount > 0 && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-500/10 px-2 py-0.2 font-mono text-[10px] font-bold text-rose-700 dark:text-rose-400">
                              <AlertTriangle className="h-3 w-3" />
                              {section.findingCount} Defect{section.findingCount === 1 ? '' : 's'}
                            </span>
                          )}
                        </div>
                        <p className="font-mono text-[11px] text-ink-400">{section.coverage}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        <StatusPill status={section.status} />
                        <button
                          type="button"
                          onClick={() => toggleSection(section.number)}
                          className="rounded-md p-1 text-ink-400 hover:bg-paper-100 hover:text-ink"
                          title="Toggle chapter details"
                        >
                          <ChevronDown
                            className={`h-4 w-4 transition-transform ${
                              isAutoOpen ? 'rotate-180' : ''
                            }`}
                          />
                        </button>
                      </div>
                    </div>

                    {/* Section Summary */}
                    <div className="mt-3.5 rounded-lg border border-line/60 bg-paper-50/50 p-3 text-sm leading-relaxed text-ink-800 dark:bg-ink-950/20 dark:text-ink-200">
                      {section.summary}
                    </div>

                    {/* Collapsible Body */}
                    {isAutoOpen && (
                      <div className="mt-4 space-y-4">
                        {/* Data Sources and Visual Telemetry */}
                        <ChapterPanel
                          report={report}
                          number={section.number}
                          lineStatuses={(section.auditedChecks || []).map((check) => check.status)}
                        />

                        {/* Specialist Agent Consultation Dossier */}
                        {section.analysis && (
                          <div className="overflow-hidden rounded-lg border border-line/80 bg-paper-50/40 shadow-2xs dark:bg-ink-950/20">
                            {/* Specialist Header */}
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line/70 bg-paper-100/60 px-4 py-2.5 dark:bg-ink-900/40">
                              <div className="flex items-center gap-2">
                                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-pine-600 text-white shadow-2xs">
                                  <Bot className="h-3.5 w-3.5" />
                                </span>
                                <div>
                                  <span className="text-xs font-semibold text-ink">
                                    {section.analysis.agentName}
                                  </span>
                                  <span className="ml-2 font-mono text-[10px] text-ink-400">
                                    {section.analysis.agentId}
                                  </span>
                                </div>
                              </div>
                              <span className="rounded bg-paper px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-pine-700 border border-pine-500/20 dark:text-pine-400">
                                Lead Specialist Review
                              </span>
                            </div>

                            {/* Dossier Structured Content */}
                            <div className="p-4 space-y-3 text-xs">
                              {/* Diagnostic Assessment */}
                              <div className="rounded-md border border-line/60 bg-paper p-3">
                                <span className="mb-1 block font-mono text-[10px] font-bold uppercase tracking-wider text-ink-500">
                                  Diagnostic Assessment
                                </span>
                                <p className="leading-relaxed text-ink-800 dark:text-ink-200">
                                  {section.analysis.executiveSummary}
                                </p>
                              </div>

                              {/* Technical Mechanics & Root Cause Dual Grid */}
                              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                <div className="rounded-md border border-line/60 bg-paper p-3">
                                  <span className="mb-1 flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-ink-500">
                                    <FileCode className="h-3 w-3 text-pine-600" />
                                    Technical Mechanics
                                  </span>
                                  <p className="leading-relaxed text-ink-700 dark:text-ink-300">
                                    {section.analysis.technicalMechanics}
                                  </p>
                                </div>

                                <div className="rounded-md border border-line/60 bg-paper p-3 space-y-2">
                                  <div>
                                    <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400">
                                      <Bug className="h-3 w-3" />
                                      Root Cause
                                    </span>
                                    <p className="mt-0.5 leading-relaxed text-ink-700 dark:text-ink-300">
                                      {section.analysis.rootCause}
                                    </p>
                                  </div>
                                  <div className="border-t border-line/60 pt-2">
                                    <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                                      <TrendingDown className="h-3 w-3" />
                                      Business Risk Exposure
                                    </span>
                                    <p className="mt-0.5 leading-relaxed text-ink-700 dark:text-ink-300">
                                      {section.analysis.businessImpact}
                                    </p>
                                  </div>
                                </div>
                              </div>

                              {/* Prescriptive Engineering Fix & Verification Protocol */}
                              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                <div className="rounded-md border border-line/60 bg-paper p-3">
                                  <div className="flex items-center justify-between pb-1.5">
                                    <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-ink-500">
                                      <Wrench className="h-3 w-3 text-pine-600" />
                                      Prescriptive Engineering Fix
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleCopy(section.analysis.remediation, `fix_${section.number}`)
                                      }
                                      className="flex items-center gap-1 font-mono text-[10px] text-ink-400 hover:text-ink"
                                      title="Copy remediation fix"
                                    >
                                      {copiedId === `fix_${section.number}` ? (
                                        <>
                                          <Check className="h-3 w-3 text-emerald-600" />
                                          <span className="text-emerald-600">Copied</span>
                                        </>
                                      ) : (
                                        <>
                                          <Copy className="h-3 w-3" />
                                          <span>Copy</span>
                                        </>
                                      )}
                                    </button>
                                  </div>
                                  <code className="block rounded bg-paper-100 p-2 font-mono text-[11px] leading-relaxed text-ink break-words dark:bg-ink-900/60">
                                    {section.analysis.remediation}
                                  </code>
                                </div>

                                <div className="rounded-md border border-line/60 bg-paper p-3">
                                  <div className="flex items-center justify-between pb-1.5">
                                    <span className="flex items-center gap-1 font-mono text-[10px] font-bold uppercase tracking-wider text-ink-500">
                                      <Terminal className="h-3 w-3 text-pine-600" />
                                      Verification Protocol
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleCopy(
                                          section.analysis.verificationMethod,
                                          `verify_${section.number}`
                                        )
                                      }
                                      className="flex items-center gap-1 font-mono text-[10px] text-ink-400 hover:text-ink"
                                      title="Copy verification protocol"
                                    >
                                      {copiedId === `verify_${section.number}` ? (
                                        <>
                                          <Check className="h-3 w-3 text-emerald-600" />
                                          <span className="text-emerald-600">Copied</span>
                                        </>
                                      ) : (
                                        <>
                                          <Copy className="h-3 w-3" />
                                          <span>Copy</span>
                                        </>
                                      )}
                                    </button>
                                  </div>
                                  <code className="block rounded bg-paper-100 p-2 font-mono text-[11px] leading-relaxed text-ink break-words dark:bg-ink-900/60">
                                    {section.analysis.verificationMethod}
                                  </code>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Verified Defects Registered */}
                        {section.findings.length > 0 && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="flex items-center gap-1 font-mono text-[11px] font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400">
                                <AlertTriangle className="h-3.5 w-3.5" />
                                Verified Defects Recorded ({section.findingCount})
                              </span>
                            </div>

                            <div className="grid grid-cols-1 gap-2.5">
                              {section.findings.map((f) => (
                                <div
                                  key={f.id}
                                  className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs space-y-1.5 shadow-2xs"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-1">
                                    <div className="flex items-center gap-1.5">
                                      <span
                                        className={`rounded border px-1.5 py-0.2 font-mono text-[9px] font-bold ${severityClass(
                                          f.severity
                                        )}`}
                                      >
                                        {f.severity}
                                      </span>
                                      <span className="font-mono text-[10px] font-bold text-ink-600">
                                        {f.id}
                                      </span>
                                      <span className="rounded border border-line bg-paper px-1.5 py-0.2 font-mono text-[10px] text-ink-500">
                                        {f.scope}
                                      </span>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => handleCopy(`${f.title}\nAction: ${f.action || ''}`, f.id)}
                                      className="font-mono text-[10px] text-ink-400 hover:text-ink flex items-center gap-1"
                                      title="Copy finding details"
                                    >
                                      {copiedId === f.id ? (
                                        <Check className="h-3 w-3 text-emerald-600" />
                                      ) : (
                                        <Copy className="h-3 w-3" />
                                      )}
                                    </button>
                                  </div>

                                  <p className="font-semibold text-ink-950 dark:text-ink-50">{f.title}</p>

                                  {f.action && (
                                    <div className="mt-1 flex items-start gap-1.5 rounded-md bg-paper/90 p-2 border border-line/60">
                                      <Wrench className="h-3.5 w-3.5 text-pine-600 shrink-0 mt-0.5" />
                                      <p className="text-[11px] text-ink-700 dark:text-ink-300">
                                        <strong className="text-ink">Recommended Action:</strong> {f.action}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              ))}

                              {section.findingCount > section.findings.length && (
                                <p className="font-mono text-xs text-ink-400 italic">
                                  +{section.findingCount - section.findings.length} more recorded finding(s) in the register
                                </p>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Audited Checks & Diagnostic Proofs Ledger */}
                        <div className="rounded-lg border border-line/70 bg-paper-50/40 p-3">
                          <button
                            type="button"
                            onClick={() => toggleProofs(section.number)}
                            className="flex w-full items-center justify-between font-mono text-xs font-semibold text-ink-700 hover:text-ink"
                          >
                            <span className="flex items-center gap-1.5">
                              <ChevronRight
                                className={`h-3.5 w-3.5 transition-transform ${
                                  expandedProofs[section.number] || expandChecks ? 'rotate-90' : ''
                                }`}
                              />
                              <span>
                                Specialist questions · {section.auditedChecks.length} {section.auditedChecks.length === 1 ? 'question' : 'questions'}
                              </span>
                            </span>
                            <span className="text-[10px] font-normal text-ink-400">
                              {expandedProofs[section.number] || expandChecks ? 'Click to collapse' : 'Click to inspect proofs'}
                            </span>
                          </button>

                          {(expandedProofs[section.number] || expandChecks) && (
                            <div className="mt-3 space-y-2 border-t border-line/60 pt-2.5">
                              {section.auditedChecks.map((check) => {
                                const checkTheme = getStatusTheme(check.status);
                                const CheckIcon = checkTheme.icon;

                                return (
                                  <div
                                    key={check.label}
                                    className={`rounded-lg border p-2.5 text-xs transition-colors ${
                                      check.status === 'ISSUE_VERIFIED'
                                        ? 'border-rose-500/30 bg-rose-500/5'
                                        : check.status === 'NO_ISSUE'
                                        ? 'border-emerald-500/30 bg-emerald-500/5'
                                        : 'border-line/60 bg-paper'
                                    }`}
                                  >
                                    <div className="flex flex-wrap items-baseline justify-between gap-1.5">
                                      <div className="flex items-center gap-1.5">
                                        <CheckIcon className={`h-3.5 w-3.5 ${checkTheme.iconColor}`} />
                                        <h5 className="font-semibold text-ink-900 dark:text-ink-100">
                                          {check.label}
                                        </h5>
                                      </div>
                                      <span
                                        className={`rounded border px-1.5 py-0.2 font-mono text-[9px] font-bold ${checkTheme.badge}`}
                                      >
                                        {STATUS_LABEL[check.status]}
                                      </span>
                                    </div>
                                    <p className="mt-1 leading-relaxed text-ink-700 dark:text-ink-300 text-[11px] pl-5">
                                      {check.result}
                                    </p>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </div>
        ))}
    </div>
  );
}

