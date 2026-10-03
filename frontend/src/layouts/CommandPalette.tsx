import React, { useEffect, useMemo, useRef, useState } from 'react';
import { SearchField } from '../components/ui';

export interface CommandAction {
  id: string;
  label: string;
  group: string;
  keywords?: string;
  onSelect: () => void;
}

export function CommandPalette({
  open,
  onClose,
  actions,
}: {
  open: boolean;
  onClose: () => void;
  actions: CommandAction[];
}) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions;
    return actions.filter((action) => `${action.label} ${action.group} ${action.keywords || ''}`.toLowerCase().includes(q));
  }, [actions, query]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActive(0);
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActive((index) => Math.min(index + 1, Math.max(results.length - 1, 0)));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActive((index) => Math.max(index - 1, 0));
      } else if (event.key === 'Enter' && results[active]) {
        event.preventDefault();
        results[active].onSelect();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, results, active, onClose]);

  if (!open) return null;

  let lastGroup = '';

  return (
    <div className="fixed inset-0 z-command flex items-start justify-center p-4 pt-[12vh]">
      <button type="button" className="scrim absolute inset-0" aria-label="Close command menu" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command menu"
        className="relative w-full max-w-xl card shadow-overlay overflow-hidden"
      >
        <div className="p-3 border-b border-line">
          <SearchField autoFocus value={query} onChange={setQuery} placeholder="Search pages, audits, and actions" label="Command menu" />
          <p className="mt-2 text-[11px] text-ink-400">↑↓ to move · Enter to open · Esc to close</p>
        </div>
        <div ref={listRef} className="max-h-[50vh] overflow-y-auto py-1" role="listbox">
          {results.length === 0 && <p className="px-4 py-8 text-center text-sm text-ink-500">No matches.</p>}
          {results.map((action, index) => {
            const showGroup = action.group !== lastGroup;
            lastGroup = action.group;
            return (
              <React.Fragment key={action.id}>
                {showGroup && <p className="px-3 pt-3 pb-1 text-[10px] uppercase tracking-[0.04em] text-ink-400 font-semibold">{action.group}</p>}
                <button
                  type="button"
                  role="option"
                  aria-selected={index === active}
                  className={`w-full text-left px-3 py-2 text-sm ${index === active ? 'bg-paper-200 text-ink' : 'text-ink-700 hover:bg-paper-100'}`}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => {
                    action.onSelect();
                    onClose();
                  }}
                >
                  {action.label}
                </button>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
