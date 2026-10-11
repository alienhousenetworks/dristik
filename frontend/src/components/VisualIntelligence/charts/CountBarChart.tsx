import React from 'react';
import { ChartSpecification } from '../../../types';

function formatValue(value: number, unit?: string): string {
  if (unit === '%') return `${value}%`;
  if (unit) return `${value} ${unit}`;
  return String(value);
}

export function CountBarChart({ chart }: { chart: ChartSpecification }) {
  const bars: Array<{ label: string; value: number }> = chart.data?.bars || [];
  const max = Math.max(1, ...bars.map((bar) => bar.value || 0));
  const scale = typeof chart.data?.scaleMax === 'number' && chart.data.scaleMax > 0
    ? chart.data.scaleMax
    : max;
  const unit = typeof chart.data?.unit === 'string' ? chart.data.unit : undefined;
  if (bars.length === 0) return null;

  return (
    <div className="w-full space-y-3 py-2">
      {bars.map((bar) => (
        <div key={bar.label}>
          <div className="flex items-baseline justify-between gap-3 text-xs font-mono text-ink">
            <span className="truncate" title={bar.label}>{bar.label}</span>
            <span className="shrink-0">{formatValue(bar.value, unit)}</span>
          </div>
          <div className="mt-1 h-2 bg-line">
            <div
              className="h-2 bg-ink"
              style={{ width: `${bar.value <= 0 ? 0 : Math.max(4, Math.round((bar.value / scale) * 100))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
