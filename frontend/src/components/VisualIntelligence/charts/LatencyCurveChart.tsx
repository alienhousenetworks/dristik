import React, { useState } from 'react';
import { ChartSpecification } from '../../../types';

interface LatencyCurveChartProps {
  chart: ChartSpecification;
}

export function LatencyCurveChart({ chart }: LatencyCurveChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const points: Array<{ label: string; value: number; full_url: string }> = chart.data?.points || [];
  const fastThreshold = chart.data?.fast_threshold || 200;
  const warningThreshold = chart.data?.warning_threshold || 800;

  if (points.length === 0) return null;

  const width = 500;
  const height = 220;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 25;
  const padBottom = 45;

  const graphWidth = width - padLeft - padRight;
  const graphHeight = height - padTop - padBottom;

  const maxVal = Math.max(warningThreshold * 1.25, ...points.map((p) => p.value));

  const getX = (index: number) => {
    if (points.length === 1) return padLeft + graphWidth / 2;
    return padLeft + (index / (points.length - 1)) * graphWidth;
  };

  const getY = (val: number) => {
    const clamped = Math.min(val, maxVal);
    return padTop + graphHeight - (clamped / maxVal) * graphHeight;
  };

  // Build SVG smooth path or polyline
  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.value)}`)
    .join(' ');

  const areaD = points.length > 0
    ? `${pathD} L ${getX(points.length - 1)} ${padTop + graphHeight} L ${getX(0)} ${padTop + graphHeight} Z`
    : '';

  const fastY = getY(fastThreshold);
  const warnY = getY(warningThreshold);

  return (
    <div className="flex flex-col w-full">
      <div className="relative w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible min-w-[380px]">
          <defs>
            <linearGradient id="latencyAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0284c7" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#0284c7" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line
            x1={padLeft}
            y1={padTop + graphHeight}
            x2={padLeft + graphWidth}
            y2={padTop + graphHeight}
            stroke="currentColor"
            className="text-line"
            strokeWidth="1"
          />

          {/* 200ms Fast Threshold Line */}
          {fastY > padTop && fastY < padTop + graphHeight && (
            <g>
              <line
                x1={padLeft}
                y1={fastY}
                x2={padLeft + graphWidth}
                y2={fastY}
                stroke="#16a34a"
                strokeWidth="1.25"
                strokeDasharray="4 3"
                opacity="0.85"
              />
              <text
                x={padLeft + graphWidth - 4}
                y={fastY - 4}
                textAnchor="end"
                className="fill-emerald-600 dark:fill-emerald-400 text-[10px] font-mono font-bold"
              >
                200ms Fast
              </text>
            </g>
          )}

          {/* 800ms Warning Threshold Line */}
          {warnY > padTop && warnY < padTop + graphHeight && (
            <g>
              <line
                x1={padLeft}
                y1={warnY}
                x2={padLeft + graphWidth}
                y2={warnY}
                stroke="#dc2626"
                strokeWidth="1.25"
                strokeDasharray="4 3"
                opacity="0.85"
              />
              <text
                x={padLeft + graphWidth - 4}
                y={warnY - 4}
                textAnchor="end"
                className="fill-red-600 dark:fill-red-400 text-[10px] font-mono font-bold"
              >
                800ms Warning
              </text>
            </g>
          )}

          {/* Area under curve */}
          <path d={areaD} fill="url(#latencyAreaGrad)" />

          {/* Main Curve */}
          <path
            d={pathD}
            fill="none"
            stroke="#0284c7"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Y Axis tick labels */}
          <text x={padLeft - 8} y={padTop + 4} textAnchor="end" className="fill-ink-400 text-[10px] font-mono">
            {Math.round(maxVal)}ms
          </text>
          <text x={padLeft - 8} y={padTop + graphHeight / 2} textAnchor="end" className="fill-ink-400 text-[10px] font-mono">
            {Math.round(maxVal / 2)}ms
          </text>
          <text x={padLeft - 8} y={padTop + graphHeight} textAnchor="end" className="fill-ink-400 text-[10px] font-mono">
            0ms
          </text>

          {/* Data Points */}
          {points.map((p, i) => {
            const cx = getX(i);
            const cy = getY(p.value);
            const isHovered = hoveredIndex === i;
            const isSlow = p.value > warningThreshold;
            const isFast = p.value <= fastThreshold;

            return (
              <g
                key={i}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 6 : 4}
                  fill="#ffffff"
                  stroke={isSlow ? '#dc2626' : (isFast ? '#16a34a' : '#0284c7')}
                  strokeWidth={isHovered ? 3 : 2}
                  className="transition-all duration-150"
                />
                {/* X Axis label */}
                <text
                  x={cx}
                  y={padTop + graphHeight + 18}
                  textAnchor="middle"
                  className={`text-[10px] font-mono transition-colors ${
                    isHovered ? 'fill-sky-600 font-bold' : 'fill-ink-600 dark:fill-ink-400'
                  }`}
                >
                  {p.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredIndex !== null && (
          <div className="absolute top-1 left-1/2 -translate-x-1/2 bg-paper-50 dark:bg-ink-900 border border-line px-3 py-2 rounded shadow-md text-xs z-10 animate-fade-in pointer-events-none whitespace-nowrap">
            <span className="font-mono text-ink font-semibold block truncate max-w-[280px]">
              {points[hoveredIndex].full_url}
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="font-bold text-sky-600">TTFB: {points[hoveredIndex].value} ms</span>
              <span className="text-ink-400">·</span>
              <span className={points[hoveredIndex].value <= fastThreshold ? 'text-good font-medium' : (points[hoveredIndex].value > warningThreshold ? 'text-bad font-medium' : 'text-amber-600 font-medium')}>
                {points[hoveredIndex].value <= fastThreshold ? '⚡ Fast (<200ms)' : (points[hoveredIndex].value > warningThreshold ? '⚠️ Slow (>800ms)' : 'Moderate')}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-between gap-4 mt-3 pt-2.5 border-t border-line/60 text-xs text-ink-500">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> &lt;200ms (Optimal)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> &gt;800ms (Crawl Drag)
          </span>
        </div>
        <span className="font-mono text-[11px]">Server Response Latency Curve</span>
      </div>
    </div>
  );
}
