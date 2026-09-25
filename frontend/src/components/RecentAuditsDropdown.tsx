import React, { useEffect, useRef, useState } from 'react';
import { AnalysisSummary } from '../types';
import { listAnalyses } from '../services/api';

interface RecentAuditsDropdownProps {
  currentAnalysisId?: string;
  onSelectAudit: (analysisId: string) => void;
  onNewAudit?: () => void;
  className?: string;
}

export function RecentAuditsDropdown({
  currentAnalysisId,
  onSelectAudit,
  onNewAudit,
  className = '',
}: RecentAuditsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [audits, setAudits] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const list = await listAnalyses(30);
      setAudits(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [currentAnalysisId]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const onDocClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [isOpen]);

  const filtered = audits.filter((a) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return a.domain.toLowerCase().includes(q) || a.website_url.toLowerCase().includes(q);
  });

  const getScoreBadge = (score: number | null | undefined, status: string) => {
    if (status === 'in_progress' || status === 'ingesting' || status === 'reasoning') {
      return 'bg-sky-100 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300 border-sky-300 animate-pulse';
    }
    if (score == null) return 'bg-paper-200 text-ink-500 border-line';
    if (score >= 80) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300';
    if (score >= 60) return 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300';
    return 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border-red-300';
  };

  return (
    <div ref={menuRef} className={`relative inline-block text-left ${className}`}>
      <button
        type="button"
        onClick={() => {
          if (!isOpen) load();
          setIsOpen(!isOpen);
        }}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-line hover:border-pine bg-paper-50 dark:bg-ink-900 text-ink-700 dark:text-ink-200 text-xs font-medium transition-colors shadow-2xs"
        title="Browse and revisit past website audits"
      >
        <span className="text-pine">📂</span>
        <span>Audits History</span>
        {audits.length > 0 && (
          <span className="font-mono text-[10px] bg-paper-200 dark:bg-ink-800 text-ink-600 px-1.5 py-0.5 rounded">
            {audits.length}
          </span>
        )}
        <span className="text-[10px] text-ink-400">▼</span>
      </button>

      {isOpen && (
        <div className="absolute left-0 sm:right-0 sm:left-auto mt-2 w-80 sm:w-96 rounded-xl bg-paper-50 dark:bg-ink-900 border border-line shadow-xl z-50 overflow-hidden animate-fade-in text-xs">
          {/* Top action header */}
          <div className="p-3 border-b border-line bg-paper-100/70 dark:bg-ink-800/60 flex items-center justify-between gap-2">
            <div>
              <span className="label text-[10px] text-pine block">Audit Archive &amp; Revisit</span>
              <span className="font-semibold text-ink text-xs">Previous Missions</span>
            </div>
            {onNewAudit && (
              <button
                type="button"
                onClick={() => {
                  onNewAudit();
                  setIsOpen(false);
                }}
                className="btn-primary text-[11px] px-2.5 py-1 rounded font-semibold flex items-center gap-1 shadow-2xs"
              >
                <span>+</span> New Audit
              </button>
            )}
          </div>

          {/* Search box if >= 4 audits */}
          {audits.length >= 4 && (
            <div className="p-2 border-b border-line">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search domain..."
                className="w-full px-2.5 py-1.5 text-xs bg-paper-50 dark:bg-ink-950 border border-line rounded focus:outline-none focus:border-pine"
              />
            </div>
          )}

          {/* List of audits */}
          <div className="max-h-72 overflow-y-auto divide-y divide-line/60 scrollbar-thin">
            {loading && audits.length === 0 ? (
              <div className="p-4 text-center text-ink-400">Loading audit history...</div>
            ) : filtered.length === 0 ? (
              <div className="p-4 text-center text-ink-400">
                {query ? 'No matching audits found.' : 'No previous audits stored yet.'}
              </div>
            ) : (
              filtered.map((item) => {
                const isSelected = item.analysis_id === currentAnalysisId;
                const dateStr = item.started_at
                  ? new Date(item.started_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '';

                return (
                  <button
                    key={item.analysis_id}
                    type="button"
                    onClick={() => {
                      onSelectAudit(item.analysis_id);
                      setIsOpen(false);
                    }}
                    className={`w-full text-left p-3 transition-colors flex items-center justify-between gap-2 hover:bg-paper-100 dark:hover:bg-ink-800/80 ${
                      isSelected ? 'bg-pine/10 border-l-2 border-pine' : ''
                    }`}
                  >
                    <div className="min-w-0 pr-2">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-ink truncate block text-xs">
                          {item.domain}
                        </span>
                        {isSelected && (
                          <span className="text-[9px] font-mono text-pine font-bold uppercase bg-pine/15 px-1.5 py-0.2 rounded">
                            Active
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-ink-400 font-mono block mt-0.5">
                        {dateStr} · {item.page_count} page{item.page_count === 1 ? '' : 's'}
                      </span>
                    </div>

                    <div className="shrink-0 flex items-center gap-1.5">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${getScoreBadge(
                          item.score_overall,
                          item.status
                        )}`}
                      >
                        {item.score_overall != null
                          ? `${Math.round(item.score_overall)}/100`
                          : item.status === 'completed'
                          ? 'Done'
                          : item.status}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
