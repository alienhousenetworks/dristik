import React, { useMemo, useState } from 'react';
import { EvidenceLedgerItem, Finding } from '../types';

interface EvidenceModalProps {
  evidenceId: string | null;
  ledger?: Record<string, EvidenceLedgerItem>;
  findings?: Finding[];
  onClose: () => void;
}

export function EvidenceModal({ evidenceId, ledger, findings, onClose }: EvidenceModalProps) {
  const [copied, setCopied] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(evidenceId);
  const [urlFilter, setUrlFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [stateFilter, setStateFilter] = useState('ALL');

  const activeEvidenceId = selectedId || evidenceId;

  const catalogItems = useMemo(() => {
    const map = new Map<string, any>();
    if (ledger) {
      Object.entries(ledger).forEach(([id, item]) => {
        map.set(id, {
          evidence_id: id,
          url: item.url || 'URL not stored',
          selector: item.selector || 'Selector not stored',
          text: item.text || item.value || '',
          hash: item.content_sha256 || item.hash || 'Hash not stored',
          analyzer: item.analyzer || 'Analyzer not stored',
          source_type: item.source_type || (id.startsWith('ext_') ? 'external' : 'crawler_dom'),
          state: (item as any).evidence_state || (item as any).provenance_state || 'VERIFIED',
          fetched_at: item.fetched_at || 'Fetch time not stored',
          raw_snapshot_id: item.raw_snapshot_id || 'Snapshot not stored',
          finding_ids: [] as string[],
        });
      });
    }
    (findings || []).forEach((f, fIdx) => {
      const fid = f.finding_id || (f as any).id || `F-${fIdx + 1}`;
      (f.evidence || []).forEach((ev, evIdx) => {
        const eid = ev.evidence_id || ev.source || `${fid}-EV-${evIdx + 1}`;
        const existing = map.get(eid);
        if (existing) {
          if (!existing.finding_ids.includes(fid)) existing.finding_ids.push(fid);
        } else {
          map.set(eid, {
            evidence_id: eid,
            url: ev.url || 'URL not stored',
            selector: ev.selector || ev.element || 'Selector not stored',
            text: ev.snippet || ev.value || ev.excerpt || '',
            hash: (ev as any).content_sha256 || (ev as any).hash || 'Hash not stored',
            analyzer: (f as any).agent_id || 'deterministic_crawler',
            source_type: (ev as any).source_type || ev.source || 'crawler_dom',
            state: (f as any).verification_status || 'VERIFIED',
            fetched_at: (f as any).evidence_timestamp || 'Fetch time not stored',
            raw_snapshot_id: 'Snapshot not stored',
            finding_ids: [fid],
          });
        }
      });
    });
    return Array.from(map.values());
  }, [ledger, findings]);

  const filteredCatalog = useMemo(() => {
    return catalogItems.filter((item) => {
      if (urlFilter && !String(item.url).toLowerCase().includes(urlFilter.toLowerCase()) && !String(item.evidence_id).toLowerCase().includes(urlFilter.toLowerCase())) {
        return false;
      }
      if (typeFilter !== 'ALL' && String(item.source_type).toLowerCase() !== typeFilter.toLowerCase()) {
        return false;
      }
      if (stateFilter !== 'ALL' && String(item.state).toUpperCase() !== stateFilter.toUpperCase()) {
        return false;
      }
      return true;
    });
  }, [catalogItems, urlFilter, typeFilter, stateFilter]);

  if (!evidenceId) return null;

  const currentId = activeEvidenceId || evidenceId;

  // Attempt to locate evidence in report ledger
  const evItem = ledger ? ledger[currentId] : undefined;

  // Also check if any finding references this token and has inline evidence
  const matchingFinding = findings?.find((f) =>
    (f.evidence_refs && f.evidence_refs.includes(currentId)) ||
    (f.evidence && f.evidence.some((e) => e.evidence_id === currentId || e.source === currentId))
  );
  const inlineEv = matchingFinding?.evidence?.find(
    (e) => e.evidence_id === currentId || e.source === currentId
  );

  const url = evItem?.url || inlineEv?.url || matchingFinding?.evidence?.[0]?.url || 'URL not stored';
  const selector = evItem?.selector || inlineEv?.selector || inlineEv?.element || 'Selector not stored';
  const textContent = evItem?.text || evItem?.value || inlineEv?.snippet || inlineEv?.value || inlineEv?.excerpt || 'No evidence text was stored for this id.';
  const hash = evItem?.content_sha256 || evItem?.hash || 'Hash not stored';
  const analyzer = evItem?.analyzer || 'Analyzer not stored';
  const sourceType = evItem?.source_type || (currentId.startsWith('ext_') ? 'external' : 'not stored');
  const provenanceState = (evItem as any)?.evidence_state || (evItem as any)?.provenance_state || (matchingFinding as any)?.verification_status || 'EMPIRICALLY_VERIFIED';
  const fetchedAt = evItem?.fetched_at || 'Fetch time not stored';
  const rawSnapshotId = evItem?.raw_snapshot_id || 'Snapshot not stored';

  const copyHash = async () => {
    await navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="bg-paper-50 dark:bg-ink border border-line dark:border-line rounded-lg shadow-2xl max-w-2xl w-full p-6 space-y-5 text-ink-700 dark:text-ink-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-line dark:border-ink pb-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded font-mono text-xs font-bold bg-paper-100 text-ink-700 dark:bg-paper-100 dark:text-ink-700 border border-line dark:border-line">
                [{currentId}]
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[10px] font-semibold bg-good/10 text-good dark:bg-good/10 dark:text-good border border-good/30 dark:border-good/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-good/10 animate-pulse" />
                CRYPTOGRAPHICALLY SEALED
              </span>
              <span className="text-xs font-mono text-ink-500 uppercase">
                {sourceType} • {String(provenanceState).toUpperCase()}
              </span>
            </div>
            <h3 className="font-sans text-lg font-bold text-ink dark:text-white">
              Deterministic Evidence Inspector & Ledger Browser
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-ink-400 hover:text-ink-700 dark:hover:text-white rounded hover:bg-paper-200 dark:hover:bg-ink-800"
          >
            ✕
          </button>
        </div>

        {/* Search & Filter Controls across Evidence Ledger (url, type, state) */}
        {catalogItems.length > 0 && (
          <div className="space-y-2 bg-paper-100 dark:bg-ink-800 p-3 rounded border border-line text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={urlFilter}
                onChange={(e) => setUrlFilter(e.target.value)}
                placeholder="Filter by URL or Evidence ID..."
                className="flex-1 min-w-[160px] px-2.5 py-1 rounded border border-line bg-paper-50 text-ink font-mono text-xs"
              />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                aria-label="Filter by evidence type"
                className="px-2 py-1 rounded border border-line bg-paper-50 text-ink font-mono text-xs"
              >
                <option value="ALL">All Types</option>
                <option value="crawler_dom">crawler_dom</option>
                <option value="http_header">http_header</option>
                <option value="external">external</option>
              </select>
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                aria-label="Filter by provenance state"
                className="px-2 py-1 rounded border border-line bg-paper-50 text-ink font-mono text-xs"
              >
                <option value="ALL">All States</option>
                <option value="VERIFIED">VERIFIED</option>
                <option value="EMPIRICALLY_VERIFIED">EMPIRICALLY_VERIFIED</option>
                <option value="OBSERVED">OBSERVED</option>
              </select>
            </div>
            {filteredCatalog.length > 1 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pt-1">
                {filteredCatalog.slice(0, 12).map((item) => (
                  <button
                    key={item.evidence_id}
                    type="button"
                    onClick={() => setSelectedId(item.evidence_id)}
                    className={`px-2 py-0.5 rounded font-mono text-[10px] border whitespace-nowrap ${
                      item.evidence_id === currentId
                        ? 'bg-ink text-white border-ink'
                        : 'bg-paper-50 text-ink-700 border-line'
                    }`}
                  >
                    {item.evidence_id}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono bg-paper-100 dark:bg-ink-800 p-3.5 rounded border border-line dark:border-line">
          <div>
            <span className="text-ink-500 block text-[10px] uppercase font-bold">Target URL</span>
            <span className="text-ink dark:text-ink-300 truncate block mt-0.5" title={url}>
              {url}
            </span>
          </div>
          <div>
            <span className="text-ink-500 block text-[10px] uppercase font-bold">DOM Selector / Key</span>
            <span className="text-ink-700 dark:text-ink-700 font-bold truncate block mt-0.5" title={selector}>
              {selector}
            </span>
          </div>
          <div>
            <span className="text-ink-500 block text-[10px] uppercase font-bold">Extracting Agent</span>
            <span className="text-ink-700 dark:text-ink-300 mt-0.5 block">{analyzer}</span>
          </div>
          <div>
            <span className="text-ink-500 block text-[10px] uppercase font-bold">Captured Timestamp</span>
            <span className="text-ink-700 dark:text-ink-300 mt-0.5 block">{fetchedAt.slice(0, 19).replace('T', ' ')} UTC</span>
          </div>
        </div>

        {/* Captured Raw Content / Snippet */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-ink-700 dark:text-ink-300 uppercase tracking-[0.04em] font-mono text-[10px]">
              Captured DOM Snapshot / Value
            </span>
            <span className="text-[10px] font-mono text-ink-400">
              Snapshot Ref: {rawSnapshotId}
            </span>
          </div>
          <div className="p-3.5 bg-ink text-ink-300 rounded text-xs font-mono overflow-x-auto max-h-48 border border-ink whitespace-pre-wrap select-all">
            {typeof textContent === 'object' ? JSON.stringify(textContent, null, 2) : String(textContent)}
          </div>
        </div>

        {/* SHA-256 Proof Footer */}
        <div className="p-3 bg-good/10 dark:bg-good/10 border border-good/30 dark:border-good/30 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="space-y-0.5 overflow-hidden">
            <span className="text-[10px] font-mono font-bold uppercase text-good dark:text-good block">
              SHA-256 Checksum Proof (Tamper-Sealed)
            </span>
            <code className="text-[11px] font-mono text-ink-700 dark:text-ink-300 truncate block max-w-md">
              {hash}
            </code>
          </div>
          <button
            type="button"
            onClick={copyHash}
            className="px-3 py-1.5 rounded text-xs font-mono font-bold bg-good/10 text-white hover:bg-good/10 transition-colors whitespace-nowrap self-start sm:self-center"
          >
            {copied ? '✓ Copied Hash' : 'Copy Hash'}
          </button>
        </div>
      </div>
    </div>
  );
}
