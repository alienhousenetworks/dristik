import React, { useState } from 'react';
import { ChartSpecification } from '../../../types';

interface SeverityDonutChartProps {
  chart: ChartSpecification;
}

export function SeverityDonutChart({ chart }: SeverityDonutChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const total: number = chart.data?.total || 0;
  const segments: Array<{ label: string; count: number; color: string }> = chart.data?.segments || [];

  if (total === 0 || segments.length === 0) return null;

  const size = 200;
  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Calculate offsets for segments
  let accumulatedPercent = 0;
  const arcSegments = segments.map((seg) => {
    const percent = total > 0 ? seg.count / total : 0;
    const strokeDasharray = `${percent * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedPercent * circumference;
    accumulatedPercent += percent;
    return {
      ...seg,
      percent: Math.round(percent * 100),
      strokeDasharray,
      strokeDashoffset,
    };
  });

  return (
    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 w-full py-2">
      {/* SVG Donut Ring */}
      <div className="relative w-[180px] h-[180px] shrink-0">
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full -rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            className="text-line opacity-30"
            strokeWidth={strokeWidth}
          />

          {/* Arcs */}
          {arcSegments.map((seg, idx) => {
            if (seg.count === 0) return null;
            const isHovered = hoveredIdx === idx;
            return (
              <circle
                key={idx}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={seg.strokeDasharray}
                strokeDashoffset={seg.strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-200 cursor-pointer"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            );
          })}
        </svg>

        {/* Center Metric */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="font-serif text-3xl font-bold text-ink leading-none">
            {hoveredIdx !== null ? arcSegments[hoveredIdx].count : total}
          </span>
          <span className="label text-[10px] text-ink-500 mt-1 uppercase tracking-wider">
            {hoveredIdx !== null ? arcSegments[hoveredIdx].label : 'Total Defects'}
          </span>
          {hoveredIdx !== null && (
            <span className="text-[11px] font-mono font-bold mt-0.5" style={{ color: arcSegments[hoveredIdx].color }}>
              {arcSegments[hoveredIdx].percent}% share
            </span>
          )}
        </div>
      </div>

      {/* Legend & Breakdown List */}
      <div className="flex flex-col gap-2.5 w-full max-w-[240px]">
        {arcSegments.map((seg, idx) => {
          const isHovered = hoveredIdx === idx;
          return (
            <div
              key={idx}
              className={`flex items-center justify-between p-2 rounded-md transition-all cursor-pointer border ${
                isHovered ? 'bg-paper-100 dark:bg-ink-800 border-line shadow-2xs' : 'border-transparent hover:bg-paper-50'
              }`}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: seg.color }} />
                <span className="text-xs font-medium text-ink-700 dark:text-ink-300">{seg.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-ink">{seg.count}</span>
                <span className="text-[10px] font-mono text-ink-400">({seg.percent}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
