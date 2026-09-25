import React, { useState } from 'react';
import { ChartSpecification } from '../../../types';

interface EngineComparisonBarChartProps {
  chart: ChartSpecification;
}

export function EngineComparisonBarChart({ chart }: EngineComparisonBarChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const engines: Array<{ name: string; readiness: number; benchmark: number; status: string }> =
    chart.data?.engines || [];

  if (engines.length === 0) {
    if (chart.data?.visibility_status === 'NOT_MEASURED') {
      return (
        <p className="mt-4 text-sm text-ink-600 leading-relaxed">
          Live engine citations were not measured for this audit. On-page AI readiness is scored separately and is not a ChatGPT, Perplexity, or AI Overview rank.
        </p>
      );
    }
    return null;
  }

  const getStatusBadge = (status: string, readiness: number) => {
    if (readiness >= 70 || status === 'Cited') {
      return 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-300';
    }
    if (readiness >= 50 || status === 'Partial') {
      return 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-300';
    }
    return 'bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border-red-300';
  };

  return (
    <div className="flex flex-col gap-4 w-full py-1">
      {engines.map((eng, idx) => {
        const isHovered = hoveredIdx === idx;
        const delta = eng.readiness - eng.benchmark;
        return (
          <div
            key={idx}
            className={`p-3 rounded-lg border transition-all ${
              isHovered
                ? 'bg-paper-100 dark:bg-ink-800/90 border-pine/40 shadow-xs'
                : 'bg-paper-50 dark:bg-ink-900/40 border-line hover:border-line-dark'
            }`}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            {/* Header row: Engine Name + Status Badge + Score */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-xs sm:text-sm text-ink">{eng.name}</span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${getStatusBadge(eng.status, eng.readiness)}`}>
                  {eng.status}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold text-pine">{eng.readiness}%</span>
                <span className="text-[11px] font-mono text-ink-400">vs {eng.benchmark}% target</span>
              </div>
            </div>

            {/* Dual Bar / Progress Track */}
            <div className="relative w-full h-3.5 bg-paper-200 dark:bg-ink-700/60 rounded-full overflow-hidden">
              {/* Benchmark Goal Marker Line */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-ink-400 dark:bg-ink-300 z-10"
                style={{ left: `${eng.benchmark}%` }}
                title={`Industry Target: ${eng.benchmark}%`}
              />

              {/* Target Readiness Fill */}
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  eng.readiness >= 70
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-500'
                    : eng.readiness >= 50
                    ? 'bg-gradient-to-r from-amber-500 to-yellow-500'
                    : 'bg-gradient-to-r from-rose-500 to-red-600'
                }`}
                style={{ width: `${eng.readiness}%` }}
              />
            </div>

            {/* Sub-label showing delta */}
            <div className="flex items-center justify-between text-[11px] text-ink-500 mt-1 font-mono">
              <span>0% Extractability</span>
              <span className={delta >= 0 ? 'text-good font-semibold' : 'text-bad font-semibold'}>
                {delta >= 0 ? `+${delta}% Above Target` : `${delta}% Gap to Target`}
              </span>
              <span>100% Citation Ready</span>
            </div>
          </div>
        );
      })}

      {/* Footer Legend */}
      <div className="flex items-center justify-between text-xs text-ink-500 pt-2 border-t border-line/60">
        <div className="flex items-center gap-4">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-600" /> Active Citation
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2.5 border-r-2 border-ink-500" /> Benchmark Goal
          </span>
        </div>
        <span className="font-mono text-[11px]">Generative Engine Extraction Matrix</span>
      </div>
    </div>
  );
}
