import React from 'react';
import { CroEvidenceDissection, Finding } from '../types';

interface CroEvidenceDissectionCardProps {
  dissection?: CroEvidenceDissection;
  finding?: Finding;
  onOpenConnectors?: () => void;
}

function isCannedDissection(dissection?: CroEvidenceDissection): boolean {
  if (!dissection) return true;
  const blob = JSON.stringify(dissection);
  return blob.includes('REQUEST CUSTOM BUILD') || blob.includes('62.4') || blob.includes('Y:845') || blob.includes('14.2%');
}

export function CroEvidenceDissectionCard({
  dissection,
  onOpenConnectors,
}: CroEvidenceDissectionCardProps) {
  if (isCannedDissection(dissection)) {
    return (
      <div className="rounded-xl border border-line bg-paper-50 p-5 space-y-2">
        <h4 className="font-serif text-base font-bold text-ink">Conversion notes</h4>
        <p className="text-sm text-ink-600">
          Abandonment, CTA click rate, and form completion were not measured. Connect GA4 or a CRM before those rates appear.
        </p>
        {onOpenConnectors && (
          <button type="button" onClick={onOpenConnectors} className="text-xs font-mono text-pine underline">
            Open connectors
          </button>
        )}
      </div>
    );
  }

  const analytics = dissection!.requires_analytics || {};
  const connected = dissection!.analytics_connected && dissection!.grounded_metrics;

  return (
    <div className="rounded-xl border border-line bg-paper-50 p-5 space-y-4">
      <h4 className="font-serif text-base font-bold text-ink">Conversion notes from the crawl</h4>
      <ul className="space-y-1 text-xs font-mono text-ink-800">
        {(dissection!.observed_facts || []).map((fact, i) => (
          <li key={i}>{fact}</li>
        ))}
      </ul>
      {dissection!.inferred_impact ? (
        <p className="text-xs text-ink-600">{dissection!.inferred_impact}</p>
      ) : null}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
        <div className="p-2 border border-line rounded bg-white">
          Abandonment: {connected ? analytics.actual_abandonment_rate : 'UNKNOWN'}
        </div>
        <div className="p-2 border border-line rounded bg-white">
          CTA conversion: {connected ? analytics.cta_conversion_rate : 'UNKNOWN'}
        </div>
        <div className="p-2 border border-line rounded bg-white">
          Form completion: {connected ? analytics.form_completion_rate : 'UNKNOWN'}
        </div>
      </div>
    </div>
  );
}
