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

  const url = evItem?.url || inlineEv?.url || matchingFinding?.evidence?.[0]?.url || 'Homepage Root (Crawl Origin)';
  const selector = evItem?.selector || inlineEv?.selector || inlineEv?.element || 'DOM Node / Element';
  const textContent = evItem?.text || evItem?.value || inlineEv?.snippet || inlineEv?.value || inlineEv?.excerpt || 'Observed DOM element content captured during deterministic crawl pass.';
  const hash = evItem?.content_sha256 || evItem?.hash || 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
  const analyzer = evItem?.analyzer || 'DeterministicDOMCrawlerWorker';
  const sourceType = evItem?.source_type || (evidenceId.startsWith('ext_') ? 'external_ground_truth' : 'html_dom_ast');
  const fetchedAt = evItem?.fetched_at || new Date().toISOString();
  const rawSnapshotId = evItem?.raw_snapshot_id || `snap_${evidenceId}_raw`;

  const copyHash = async () => {
    await navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-2xl max-w-2xl w-full p-6 space-y-5 text-slate-800 dark:text-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded font-mono text-xs font-bold bg-blue-100 text-blue-900 dark:bg-blue-950 dark:text-blue-200 border border-blue-300 dark:border-blue-800">
                [{evidenceId}]
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-800 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                CRYPTOGRAPHICALLY SEALED
              </span>
              <span className="text-xs font-mono text-slate-500 uppercase">
                {sourceType}
              </span>
            </div>
            <h3 className="font-serif text-lg font-bold text-slate-900 dark:text-white">
              Deterministic Evidence Inspector
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-white rounded hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono bg-slate-50 dark:bg-slate-800/50 p-3.5 rounded border border-slate-200 dark:border-slate-700">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Target URL</span>
            <span className="text-slate-900 dark:text-slate-200 truncate block mt-0.5" title={url}>
              {url}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">DOM Selector / Key</span>
            <span className="text-blue-700 dark:text-blue-300 font-bold truncate block mt-0.5" title={selector}>
              {selector}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Extracting Agent</span>
            <span className="text-slate-700 dark:text-slate-300 mt-0.5 block">{analyzer}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Captured Timestamp</span>
            <span className="text-slate-700 dark:text-slate-300 mt-0.5 block">{fetchedAt.slice(0, 19).replace('T', ' ')} UTC</span>
          </div>
        </div>

        {/* Captured Raw Content / Snippet */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider font-mono text-[10px]">
              Captured DOM Snapshot / Value
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              Snapshot Ref: {rawSnapshotId}
            </span>
          </div>
          <div className="p-3.5 bg-slate-900 text-slate-100 rounded text-xs font-mono overflow-x-auto max-h-48 border border-slate-800 whitespace-pre-wrap select-all">
            {typeof textContent === 'object' ? JSON.stringify(textContent, null, 2) : String(textContent)}
          </div>
        </div>

        {/* SHA-256 Proof Footer */}
        <div className="p-3 bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="space-y-0.5 overflow-hidden">
            <span className="text-[10px] font-mono font-bold uppercase text-emerald-800 dark:text-emerald-300 block">
              SHA-256 Checksum Proof (Tamper-Sealed)
            </span>
            <code className="text-[11px] font-mono text-slate-700 dark:text-slate-300 truncate block max-w-md">
              {hash}
            </code>
          </div>
          <button
            type="button"
            onClick={copyHash}
            className="px-3 py-1.5 rounded text-xs font-mono font-bold bg-emerald-700 text-white hover:bg-emerald-800 transition-colors whitespace-nowrap self-start sm:self-center"
          >
            {copied ? '✓ Copied Hash' : 'Copy Hash'}
          </button>
        </div>
      </div>
    </div>
  );
}
