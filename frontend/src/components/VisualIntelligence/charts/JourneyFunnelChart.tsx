import React, { useState } from 'react';
import { ChartSpecification } from '../../../types';

interface JourneyFunnelChartProps {
  chart: ChartSpecification;
}

export function JourneyFunnelChart({ chart }: JourneyFunnelChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const stages: Array<{ stage: string; score: number; drop_reason: string }> =
    chart.data?.stages || [];

  if (stages.length === 0) return null;

  return (
    <div className="flex flex-col gap-3 w-full py-1">
      {stages.map((st, idx) => {
        const isHovered = hoveredIdx === idx;
        // Width narrows down from 100% to ~55% across stages to form a visual funnel
        const widthPercent = Math.max(50, 100 - idx * 14);

        return (
          <div
            key={idx}
            className="flex flex-col items-center w-full"
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            {/* Funnel Stage Card */}
            <div
              className={`p-3 rounded-lg border transition-all duration-200 cursor-pointer ${
                isHovered
                  ? 'bg-paper-100 dark:bg-ink-800 border-pine shadow-sm scale-[1.01]'
                  : 'bg-paper-50 dark:bg-ink-900/50 border-line hover:border-line-dark'
              }`}
              style={{ width: `${widthPercent}%` }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-xs sm:text-sm text-ink truncate">{st.stage}</span>
                <span className="font-mono text-xs sm:text-sm font-bold text-pine">{st.score}% readiness</span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-2 bg-paper-200 dark:bg-ink-700/60 rounded-full overflow-hidden mt-1.5">
                <div
                  className="h-full bg-pine rounded-full transition-all duration-300"
                  style={{ width: `${st.score}%` }}
                />
              </div>

              {/* Drop reason friction tag */}
              <div className="mt-1.5 flex items-center gap-1 text-[11px] text-bad dark:text-red-400 font-mono">
                <span>⚠️ Friction:</span>
                <span className="truncate">{st.drop_reason}</span>
              </div>
            </div>

            {/* Downward transition chevron */}
            {idx < stages.length - 1 && (
              <div className="text-ink-400 text-xs py-0.5 select-none">↓</div>
            )}
          </div>
        );
      })}

      <div className="flex items-center justify-between text-xs text-ink-500 pt-2 border-t border-line/60 mt-1">
        <span>Top of Funnel (Discovery)</span>
        <span className="font-mono text-[11px]">Intent Friction Funnel</span>
        <span>Bottom of Funnel (Conversion)</span>
      </div>
    </div>
  );
}
