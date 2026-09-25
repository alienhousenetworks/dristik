import React from 'react';
import { TelemetryData } from '../types';
import { costBasisCaption, formatAuditCost, formatMs } from '../lib/format';

interface TelemetryProps {
  telemetry: TelemetryData;
}

export function Telemetry({ telemetry }: TelemetryProps) {
  const items = [
    { label: 'Tokens', value: telemetry.total_tokens ? telemetry.total_tokens.toLocaleString() : '0' },
    { label: 'Model calls', value: String(telemetry.model_calls_count || 0) },
    { label: 'Latency', value: formatMs(telemetry.total_latency_ms) },
    { label: 'Cost', value: formatAuditCost(telemetry) },
  ];
  const models = (telemetry.models_used || []).join(' · ');
  const basis = costBasisCaption(telemetry.cost_basis);

  return (
    <dl className="no-print flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-400">
      {items.map((item) => (
        <div key={item.label} className="flex items-baseline gap-1.5">
          <dt>{item.label}</dt>
          <dd className="font-mono text-ink-500">{item.value}</dd>
        </div>
      ))}
      {(models || basis) && (
        <div className="flex items-baseline gap-1.5">
          <dt>Model</dt>
          <dd className="font-mono text-ink-500">
            {models || '—'}
            {basis ? ` · ${basis}` : ''}
          </dd>
        </div>
      )}
    </dl>
  );
}
