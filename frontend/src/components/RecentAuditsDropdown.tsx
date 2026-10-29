import React, { useEffect, useRef, useState } from 'react';
import { AnalysisSummary } from '../types';
import { deleteAnalysis, listAnalyses } from '../services/api';

interface RecentAuditsDropdownProps {
  currentAnalysisId?: string;
  onSelectAudit: (analysisId: string) => void;
  onNewAudit?: () => void;
  onAuditDeleted?: (analysisId: string, label?: string) => void | Promise<void>;
  className?: string;
}

export function RecentAuditsDropdown({
  currentAnalysisId,
  onSelectAudit,
  onNewAudit,
  onAuditDeleted,
  className = '',
}: RecentAuditsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [audits, setAudits] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [deleteError, setDeleteError] = useState<string | null>(null);
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
    const onChange = () => load();
    window.addEventListener('dristik:audits-changed', onChange);
    return () => window.removeEventListener('dristik:audits-changed', onChange);
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
      return 'bg-paper-100 text-ink-700 dark:bg-paper-100 dark:text-ink-700 border-line animate-pulse';
    }
    if (score == null) return 'bg-paper-200 text-ink-500 border-line';
    if (score >= 80) return 'bg-good/10 text-good dark:bg-good/10 dark:text-good border-good/30';
    if (score >= 60) return 'bg-warn/10 text-warn dark:bg-warn/10 dark:text-warn border-warn/30';
    return 'bg-bad/10 text-bad dark:bg-bad/10 dark:text-bad border-bad/30';
  };

  return (
    <div ref={menuRef} className={`relative inline-block text-left ${className}`}>
      <button
        type="button"
        onClick={() => {
          if (!isOpen) load();
          setIsOpen(!isOpen);
        }}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-line hover:border-ink bg-paper-50 dark:bg-ink-900 text-ink-700 dark:text-ink-200 text-xs font-medium transition-colors shadow-2xs"
        title="Browse and revisit past website audits"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <span>Audits</span>
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
              <span className="label text-[10px] text-ink-700 block">Audit Archive &amp; Revisit</span>
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
          {deleteError && (
            <p className="px-3 py-2 text-[11px] text-bad border-b border-line">{deleteError}</p>
          )}
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
                  <div
                    key={item.analysis_id}
                    className={`w-full text-left p-3 transition-colors flex items-center justify-between gap-2 hover:bg-paper-100 dark:hover:bg-ink-800/80 ${
                      isSelected ? 'bg-paper-200 border-l-2 border-line' : ''
                    }`}
                  >
                    <button
                      type="button"
                      className="min-w-0 pr-2 text-left flex-1"
                      onClick={() => {
                        onSelectAudit(item.analysis_id);
                        setIsOpen(false);
                      }}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-ink truncate block text-xs">
                          {item.domain}
                        </span>
                        {isSelected && (
                          <span className="text-[9px] font-mono text-ink-700 font-bold uppercase bg-paper-200 px-1.5 py-0.2 rounded">
                            Active
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-ink-400 font-mono block mt-0.5">
                        {dateStr} · {item.page_count} page{item.page_count === 1 ? '' : 's'}
                      </span>
                    </button>

                    <div className="shrink-0 flex items-center gap-1.5">
                      <button
                        type="button"
                        className="shrink-0 px-2 py-1 text-[11px] font-semibold text-bad border border-bad/40 rounded hover:bg-bad/10"
                        title={`Delete audit for ${item.domain}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeleteError(null);
                          if (onAuditDeleted) {
                            void onAuditDeleted(item.analysis_id, item.domain || item.website_url);
                            return;
                          }
                          void deleteAnalysis(item.analysis_id)
                            .then(() => setAudits((prev) => prev.filter((row) => row.analysis_id !== item.analysis_id)))
                            .catch((err: unknown) => {
                              setDeleteError(err instanceof Error ? err.message : 'Could not delete the audit.');
                            });
                        }}
                      >
                        Delete
                      </button>
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
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
