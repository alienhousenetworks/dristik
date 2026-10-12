import React from 'react';
import { ExecutiveReport } from '../../types';
import { ChartBar, ChartSpec, chapterVisuals, evidenceBars } from './chapterSeries';
import { SectionStatus } from './types';

function BarChart({ chart }: { chart: ChartSpec }) {
  const peak = Math.max(...chart.bars.map((bar) => bar.value), 1);
  const width = 640;
  const labelW = 168;
  const barMax = 390;
  const rowH = 26;
  const height = 12 + rowH * chart.bars.length;
  return (
    <figure className="mt-3 border border-line bg-paper p-3">
      <figcaption>
        <p className="text-sm font-medium text-ink">{chart.title}</p>
        <p className="mt-1 text-xs leading-relaxed text-ink-500">{chart.note}</p>
      </figcaption>
      <svg role="img" aria-label={chart.title} viewBox={`0 0 ${width} ${height}`} className="mt-2 w-full">
        {chart.bars.map((bar: ChartBar, index) => {
          const y = 4 + index * rowH;
          const barWidth = bar.value <= 0 ? 0 : Math.max(2, (bar.value / peak) * barMax);
          return (
            <g key={bar.label}>
              <text x="0" y={y + 14} fill="currentColor" fontSize="12" className="fill-ink">
                {bar.label.slice(0, 32)}
              </text>
              <rect x={labelW} y={y} width={barWidth} height="16" className="fill-ink" />
              <text x={labelW + barWidth + 8} y={y + 14} fill="currentColor" fontSize="12" className="fill-ink">
                {Number.isInteger(bar.value) ? String(bar.value) : bar.value.toFixed(1)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export function ChapterPanel({
  report,
  number,
  lineStatuses,
}: {
  report: ExecutiveReport;
  number: string;
  lineStatuses: SectionStatus[];
}) {
  const visual = chapterVisuals(report, number);
  const mix: ChartSpec = {
    title: 'Sub-index evidence states',
    note: 'How many checklist lines in this chapter landed in each evidence state. This is not a pass rate for URLs that were not fetched.',
    bars: evidenceBars(lineStatuses),
  };
  const charts = mix.bars.length ? [mix, ...visual.charts] : visual.charts;
  return (
    <div className="mt-3 border border-line bg-paper-50 p-3">
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.06em] text-ink-500">Data sources</p>
      <ul className="mt-2 space-y-1">
        {visual.sources.map((source) => (
          <li key={source.name} className="text-xs leading-relaxed text-ink-700">
            <span className="mr-2 font-mono text-[10px] font-bold uppercase text-ink">{source.state}</span>
            <span className="font-medium text-ink">{source.name}</span>
            <span> — {source.detail}</span>
          </li>
        ))}
      </ul>
      {charts.map((chart) => (
        <BarChart key={chart.title} chart={chart} />
      ))}
      {visual.gap ? <p className="mt-2 text-xs leading-relaxed text-ink-500">{visual.gap}</p> : null}
    </div>
  );
}
