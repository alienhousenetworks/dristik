import React from 'react';
import { Database, Info } from 'lucide-react';
import { ExecutiveReport } from '../../types';
import { ChartBar, ChartSpec, chapterVisuals, evidenceBars } from './chapterSeries';
import { SectionStatus } from './types';

function getBarColor(label: string, chartTitle: string, value: number): string {
  const normLabel = label.toLowerCase();
  const normTitle = chartTitle.toLowerCase();

  // HTTP status codes
  if (normLabel.includes('http 200') || normLabel.includes('2xx')) {
    return 'bg-emerald-500';
  }
  if (normLabel.includes('http 3')) {
    return 'bg-sky-500';
  }
  if (normLabel.includes('http 4') || normLabel.includes('http 5') || normLabel.includes('error')) {
    return 'bg-rose-500';
  }

  // Latency & TTFB (ms)
  if (normTitle.includes('ttfb') || normTitle.includes('latency') || normTitle.includes('response time')) {
    if (value > 600) return 'bg-rose-500';
    if (value > 300) return 'bg-amber-500';
    return 'bg-emerald-500';
  }

  // Core Web Vitals (LCP ms)
  if (normTitle.includes('lcp')) {
    if (value > 2500) return 'bg-rose-500';
    if (value > 1200) return 'bg-amber-500';
    return 'bg-emerald-500';
  }

  // Score bars (0 - 100)
  if (normTitle.includes('score')) {
    if (value >= 80) return 'bg-emerald-500';
    if (value >= 60) return 'bg-amber-500';
    return 'bg-rose-500';
  }

  // Evidence states
  if (normLabel.includes('verified') || normLabel.includes('defect')) {
    return 'bg-rose-500';
  }
  if (normLabel.includes('clean') || normLabel.includes('measured') || normLabel.includes('no issue')) {
    return 'bg-emerald-500';
  }
  if (normLabel.includes('inferred')) {
    return 'bg-amber-500';
  }
  if (normLabel.includes('unavailable') || normLabel.includes('not tested')) {
    return 'bg-slate-400';
  }

  // AI response rates
  if (normLabel.includes('mention') || normLabel.includes('citation')) {
    return 'bg-indigo-500';
  }

  return 'bg-pine-600 dark:bg-pine-400';
}

function ModernBarChart({ chart }: { chart: ChartSpec }) {
  const peak = Math.max(...chart.bars.map((bar) => bar.value), 1);

  return (
    <figure className="mt-3 rounded-lg border border-line/70 bg-paper-50/60 p-3.5 transition-all dark:bg-ink-950/20">
      <figcaption className="mb-3 space-y-0.5">
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          <p className="text-xs font-semibold tracking-tight text-ink">{chart.title}</p>
          <span className="font-mono text-[10px] text-ink-400">
            {chart.bars.length} {chart.bars.length === 1 ? 'metric' : 'metrics'}
          </span>
        </div>
        <p className="text-[11px] leading-relaxed text-ink-500">{chart.note}</p>
      </figcaption>

      <div className="space-y-2">
        {chart.bars.map((bar: ChartBar) => {
          const percent = bar.value <= 0 ? 0 : Math.min(100, Math.max(3, (bar.value / peak) * 100));
          const barColor = getBarColor(bar.label, chart.title, bar.value);
          const formattedVal = Number.isInteger(bar.value) ? String(bar.value) : bar.value.toFixed(1);

          return (
            <div key={bar.label} className="group space-y-1">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span
                  className="truncate font-mono text-[11px] font-medium text-ink-800 transition-colors group-hover:text-ink dark:text-ink-200"
                  title={bar.label}
                >
                  {bar.label}
                </span>
                <span className="font-mono text-[11px] font-bold tracking-tight text-ink">
                  {formattedVal}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-paper-200/70 dark:bg-ink-800/60">
                <div
                  style={{ width: `${percent}%` }}
                  className={`h-full rounded-full transition-all duration-500 ease-out ${barColor}`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </figure>
  );
}

function sourceStateClass(state: string): string {
  const norm = state.toLowerCase();
  if (norm.includes('measured')) {
    return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
  }
  if (norm.includes('unavailable') || norm.includes('failed')) {
    return 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30';
  }
  if (norm.includes('inferred')) {
    return 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30';
  }
  if (norm.includes('not tested')) {
    return 'bg-slate-500/15 text-slate-700 dark:text-slate-400 border-slate-500/30';
  }
  return 'bg-paper-100 text-ink-500 border-line';
}

function buildEmpiricalTableForChapter(
  report: ExecutiveReport,
  chapterNum: string,
): { title: string; columns: string[]; rows: string[][] } | null {
  const pages = ((report.crawl_manifest as any)?.pages || report.page_reports || []) as Array<Record<string, any>>;
  if (!pages.length) return null;

  const shortPath = (u?: string) => (u ? u.replace(/^https?:\/\/[^/]+/i, '') || '/' : '/');
  const ch = parseInt(chapterNum, 10);

  // Chapters 03-07: Crawlability, Indexation, HTTP Status, Sitemap, Canonicals
  if (ch >= 3 && ch <= 7) {
    return {
      title: 'Empirical Crawl, Indexation & Canonical Ledger',
      columns: ['URL Path', 'HTTP Status', 'Indexable', 'Canonical Directive', 'Click Depth'],
      rows: pages.slice(0, 12).map((p) => [
        shortPath(p.url),
        `HTTP ${p.status_code ?? 200}`,
        String(p.robots_meta || '').toLowerCase().includes('noindex') ? 'Noindex' : 'Indexable',
        p.canonical_url ? 'Self-referencing' : 'Missing',
        `Depth ${p.click_depth ?? (shortPath(p.url) === '/' ? 0 : 1)}`,
      ]),
    };
  }

  // Chapters 08-12: Titles, Snippets, Headings, Content Quality, Internal Links & Media
  if (ch >= 8 && ch <= 12) {
    return {
      title: 'Empirical On-Page Metadata, Headings & Content Matrix',
      columns: ['URL Path', 'Title Tag (Len)', 'Meta Description (Len)', 'Primary H1', 'Words & Alt Gaps'],
      rows: pages.slice(0, 12).map((p) => {
        const title = String(p.title || '—');
        const meta = String(p.meta_description || '—');
        const h1 = Array.isArray(p.h1) && p.h1.length > 0 ? String(p.h1[0]) : 'Missing H1';
        const wc = Number(p.word_count || 0);
        const missingAlt = Number(p.images_without_alt || 0);
        const totalImg = Number(p.total_images ?? p.image_count ?? 0);
        return [
          shortPath(p.url),
          `${title.slice(0, 38)} (${title === '—' ? 0 : title.length}c)`,
          `${meta.slice(0, 42)}... (${meta === '—' ? 0 : meta.length}c)`,
          h1.slice(0, 36),
          `${wc}w · ${missingAlt}/${totalImg} missing alt`,
        ];
      }),
    };
  }

  // Chapters 13-15: Core Web Vitals, Latency, Mobile & Rendering
  if (ch >= 13 && ch <= 15) {
    return {
      title: 'Empirical Performance, Viewport & Rendering Telemetry',
      columns: ['URL Path', 'Response Latency', 'Viewport Meta', 'HTML Lang', 'Internal / Ext Links'],
      rows: pages.slice(0, 12).map((p) => [
        shortPath(p.url),
        p.load_time_ms ? `${Math.round(Number(p.load_time_ms))} ms` : 'Measured in crawl',
        p.has_viewport !== false ? 'Present' : 'Missing',
        p.html_lang || (p.has_html_lang ? 'Present' : 'Missing'),
        `${p.internal_links_count ?? (Array.isArray(p.internal_links) ? p.internal_links.length : 0)} in / ${p.external_links_count ?? (Array.isArray(p.external_links) ? p.external_links.length : 0)} out`,
      ]),
    };
  }

  // Chapters 16-24: Schema, Entities, E-E-A-T, Security
  return {
    title: 'Empirical Structured Data (JSON-LD) & Entity Signals',
    columns: ['URL Path', 'Detected Schema Types', 'Rich Result Eligibility', 'HTTPS / Transport'],
    rows: pages.slice(0, 12).map((p) => {
      const schemas: string[] = Array.isArray(p.schema_types) ? p.schema_types : [];
      return [
        shortPath(p.url),
        schemas.length > 0 ? schemas.join(', ') : 'None (0 JSON-LD blocks)',
        schemas.length > 0 ? 'Eligible' : 'Ineligible (Missing JSON-LD)',
        String(p.url || '').startsWith('https://') ? 'HTTPS Active' : 'HTTP',
      ];
    }),
  };
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
    note: 'How many specialist questions in this chapter have a recorded judgment. This is not a pass rate.',
    bars: evidenceBars(lineStatuses),
  };
  const charts = mix.bars.length ? [mix, ...visual.charts] : visual.charts;
  const empiricalTable = buildEmpiricalTableForChapter(report, number);

  return (
    <div className="mt-3.5 rounded-lg border border-line/80 bg-paper-50/40 p-3.5 dark:bg-ink-950/10">
      {/* Data Sources Header & Chips */}
      <div>
        <div className="flex items-center gap-1.5 text-ink-500">
          <Database className="h-3 w-3 text-pine-600 dark:text-pine-400" />
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.06em] text-ink-500">
            Data sources
          </p>
        </div>

        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {visual.sources.map((source) => (
            <div
              key={source.name}
              className="flex items-start gap-2 rounded-md border border-line/60 bg-paper p-2.5 shadow-2xs transition-all hover:border-line"
            >
              <span
                className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider border ${sourceStateClass(
                  source.state
                )}`}
              >
                {source.state}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-ink">{source.name}</p>
                <p className="text-[11px] leading-tight text-ink-500">{source.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Visual Telemetry Charts */}
      {charts.length > 0 && (
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          {charts.map((chart) => (
            <ModernBarChart key={chart.title} chart={chart} />
          ))}
        </div>
      )}

      {/* Empirical Website Page Inspection Table */}
      {empiricalTable && (
        <div className="mt-3 rounded-lg border border-line/70 bg-paper p-3 overflow-x-auto">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-ink">{empiricalTable.title}</p>
            <span className="font-mono text-[10px] text-ink-400">
              {empiricalTable.rows.length} crawled URL(s)
            </span>
          </div>
          <table className="w-full text-left border-collapse text-[11px]">
            <thead>
              <tr className="border-b border-line text-ink-500 font-mono text-[10px] uppercase">
                {empiricalTable.columns.map((col) => (
                  <th key={col} className="py-1.5 px-2 font-semibold">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line/50">
              {empiricalTable.rows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-paper-50/80">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className={`py-1.5 px-2 ${cIdx === 0 ? 'font-mono font-medium text-ink' : 'text-ink-700'}`}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Data Gap Callout */}
      {visual.gap ? (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-line/70 bg-paper-100/60 p-2.5 text-xs text-ink-600 dark:bg-ink-900/20 dark:text-ink-400">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" />
          <span className="leading-relaxed">{visual.gap}</span>
        </div>
      ) : null}
    </div>
  );
}
