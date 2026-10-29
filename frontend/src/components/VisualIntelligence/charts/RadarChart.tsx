import React, { useState } from 'react';
import { ChartSpecification } from '../../../types';

interface RadarChartProps {
  chart: ChartSpecification;
}

export function RadarChart({ chart }: RadarChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const labels: string[] = chart.data?.labels || [];
  const targetValues: number[] = chart.data?.target_values || [];
  const benchmarkValues: number[] = chart.data?.benchmark_values || [];
  const maxValue = chart.config?.max_value || 100;
  const targetLabel = chart.config?.target_label || 'Target Site';
  const benchmarkLabel = chart.config?.benchmark_label || 'Industry Baseline';

  const size = 360;
  const center = size / 2;
  const radius = center - 78;
  const total = labels.length;

  if (total === 0) return null;

  // Compute coordinate for a value at a given index
  const getCoordinates = (index: number, val: number) => {
    const angle = (Math.PI * 2 / total) * index - Math.PI / 2;
    const r = (Math.min(val, maxValue) / maxValue) * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  // Build SVG polygon points string
  const targetPoints = targetValues
    .map((v, i) => {
      const { x, y } = getCoordinates(i, v);
      return `${x},${y}`;
    })
    .join(' ');

  const benchmarkPoints = benchmarkValues
    .map((v, i) => {
      const { x, y } = getCoordinates(i, v);
      return `${x},${y}`;
    })
    .join(' ');

  const levels = [0.2, 0.4, 0.6, 0.8, 1.0];

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full max-w-[340px] aspect-square">
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full overflow-visible">
          {/* Radial Grid Web */}
          {levels.map((lvl, idx) => {
            const r = radius * lvl;
            return (
              <circle
                key={idx}
                cx={center}
                cy={center}
                r={r}
                fill="none"
                stroke="currentColor"
                className="text-line opacity-40 dark:opacity-20"
                strokeDasharray={idx === levels.length - 1 ? 'none' : '3 3'}
                strokeWidth={idx === levels.length - 1 ? '1.5' : '1'}
              />
            );
          })}

          {/* Spokes from center to outer ring */}
          {labels.map((_, i) => {
            const { x, y } = getCoordinates(i, maxValue);
            return (
              <line
                key={i}
                x1={center}
                y1={center}
                x2={x}
                y2={y}
                stroke="currentColor"
                className="text-line opacity-50 dark:opacity-30"
                strokeWidth="1"
              />
            );
          })}

          {benchmarkValues.length > 0 && (
            <polygon
              points={benchmarkPoints}
              fill="none"
              stroke="#a8aeb6"
              strokeWidth="1.75"
              strokeDasharray="4 3"
              opacity="0.8"
            />
          )}

          {/* Target Site Polygon with Gradient Fill */}
          <defs>
            <linearGradient id="radarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#171a20" stopOpacity="0.16" />
              <stop offset="100%" stopColor="#171a20" stopOpacity="0.03" />
            </linearGradient>
          </defs>
          <polygon
            points={targetPoints}
            fill="url(#radarGrad)"
            stroke="#171a20"
            strokeWidth="2"
            className="transition-all duration-300"
          />

          {/* Target Data Points */}
          {targetValues.map((v, i) => {
            const { x, y } = getCoordinates(i, v);
            const isHovered = hoveredIndex === i;
            return (
              <g key={i} className="cursor-pointer" onMouseEnter={() => setHoveredIndex(i)} onMouseLeave={() => setHoveredIndex(null)}>
                <circle
                  cx={x}
                  cy={y}
                  r={isHovered ? 6.5 : 4.5}
                  fill="#ffffff"
                  stroke="#171a20"
                  strokeWidth={isHovered ? 3 : 2}
                  className="transition-all duration-150"
                />
              </g>
            );
          })}

          {/* Axis Labels */}
          {labels.map((lbl, i) => {
            const angle = (Math.PI * 2 / total) * i - Math.PI / 2;
            const labelRadius = radius + 28;
            const x = center + labelRadius * Math.cos(angle);
            const y = center + labelRadius * Math.sin(angle);
            const score = targetValues[i] ?? 0;
            const isHovered = hoveredIndex === i;

            let textAnchor: 'middle' | 'start' | 'end' = 'middle';
            if (Math.cos(angle) > 0.35) textAnchor = 'start';
            else if (Math.cos(angle) < -0.35) textAnchor = 'end';

            return (
              <text
                key={i}
                x={x}
                y={y}
                textAnchor={textAnchor}
                dominantBaseline="central"
                className={`text-[10px] font-mono select-none transition-colors duration-150 ${
                  isHovered ? 'fill-ink font-bold' : 'fill-ink-700 dark:fill-ink-300 font-medium'
                }`}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <tspan x={x} dy="-0.45em">{lbl}</tspan>
                <tspan x={x} dy="1.15em" className="font-bold fill-ink">{score}</tspan>
              </text>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredIndex !== null && (
          <div className="absolute top-2 right-2 bg-paper-50 dark:bg-ink-900 border border-line p-2.5 rounded-lg shadow-md text-xs z-10 animate-fade-in pointer-events-none">
            <span className="font-bold text-ink block">{labels[hoveredIndex]}</span>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-ink-700 font-semibold">{targetLabel}: {targetValues[hoveredIndex]}/100</span>
              <span className="text-ink-400">·</span>
              <span className="text-ink-500">Benchmark: {benchmarkValues[hoveredIndex]}/100</span>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-5 mt-4 pt-3 border-t border-line/60 w-full text-xs">
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-sm bg-paper-200 border border-line" />
          <span className="text-ink-700 font-medium">{targetLabel}</span>
        </div>
        {benchmarkValues.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-0.5 border-t-2 border-dashed border-line" />
            <span className="text-ink-500">{benchmarkLabel}</span>
          </div>
        )}
      </div>
    </div>
  );
}
