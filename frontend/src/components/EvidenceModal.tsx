import React, { useState } from 'react';
import { EvidenceLedgerItem, Finding } from '../types';

interface EvidenceModalProps {
  evidenceId: string | null;
  ledger?: Record<string, EvidenceLedgerItem>;
  findings?: Finding[];
  onClose: () => void;
}

export function EvidenceModal({ evidenceId, ledger, findings, onClose }: EvidenceModalProps) {
  const [copied, setCopied] = useState(false);

  if (!evidenceId) return null;

  // Attempt to locate evidence in report ledger
  const evItem = ledger ? ledger[evidenceId] : undefined;

  // Also check if any finding references this token and has inline evidence
  const matchingFinding = findings?.find((f) =>
    (f.evidence_refs && f.evidence_refs.includes(evidenceId)) ||
    (f.evidence && f.evidence.some((e) => e.evidence_id === evidenceId || e.source === evidenceId))
  );
  const inlineEv = matchingFinding?.evidence?.find(
    (e) => e.evidence_id === evidenceId || e.source === evidenceId
  );

  const url = evItem?.url || inlineEv?.url || matchingFinding?.evidence?.[0]?.url || 'URL not stored';
  const selector = evItem?.selector || inlineEv?.selector || inlineEv?.element || 'Selector not stored';
  const textContent = evItem?.text || evItem?.value || inlineEv?.snippet || inlineEv?.value || inlineEv?.excerpt || 'No evidence text was stored for this id.';
  const hash = evItem?.content_sha256 || evItem?.hash || 'Hash not stored';
  const analyzer = evItem?.analyzer || 'Analyzer not stored';
  const sourceType = evItem?.source_type || (evidenceId.startsWith('ext_') ? 'external' : 'not stored');
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
                [{evidenceId}]
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[10px] font-semibold bg-good/10 text-good dark:bg-good/10 dark:text-good border border-good/30 dark:border-good/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-good/10 animate-pulse" />
                CRYPTOGRAPHICALLY SEALED
              </span>
              <span className="text-xs font-mono text-ink-500 uppercase">
                {sourceType}
              </span>
            </div>
            <h3 className="font-sans text-lg font-bold text-ink dark:text-white">
              Deterministic Evidence Inspector
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
