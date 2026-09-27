import React from 'react';
import { ChartSpecification } from '../../../types';

export function CountBarChart({ chart }: { chart: ChartSpecification }) {
  const bars: Array<{ label: string; value: number }> = chart.data?.bars || [];
  const max = Math.max(1, ...bars.map((bar) => bar.value || 0));
  if (bars.length === 0) return null;

  return (
    <div className="space-y-3 py-2">
      {bars.map((bar) => (
        <div key={bar.label}>
          <div className="flex items-baseline justify-between gap-3 text-xs font-mono text-ink">
            <span>{bar.label}</span>
            <span>{bar.value}</span>
          </div>
          <div className="mt-1 h-2 bg-line">
            <div
              className="h-2 bg-ink"
              style={{ width: `${Math.max(4, Math.round((bar.value / max) * 100))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
