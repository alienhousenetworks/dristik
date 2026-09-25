import React, { useState } from 'react';
import { ExecutiveReport, ChartSpecification, SpotlightMetric, VisualIntelligencePayload } from '../../types';
import { synthesizeVisualIntelligenceFallback } from '../../lib/visualSynthesizerFallback';
import { RadarChart } from './charts/RadarChart';
import { LatencyCurveChart } from './charts/LatencyCurveChart';
import { SeverityDonutChart } from './charts/SeverityDonutChart';
import { EngineComparisonBarChart } from './charts/EngineComparisonBarChart';
import { JourneyFunnelChart } from './charts/JourneyFunnelChart';

interface AdaptiveVisualIntelligenceProps {
  report: ExecutiveReport;
  compact?: boolean;
}

export function AdaptiveVisualIntelligence({ report, compact = false }: AdaptiveVisualIntelligenceProps) {
  // Use precomputed visual intelligence from backend report, or dynamically synthesize via fallback
  const visualPayload: VisualIntelligencePayload =
    report.visual_intelligence || synthesizeVisualIntelligenceFallback(report);

  const [activeChartIds, setActiveChartIds] = useState<string[]>(
    visualPayload.selected_visualizations.map((c) => c.id)
  );
  const [showCustomizer, setShowCustomizer] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');

  const allAvailableCharts = visualPayload.selected_visualizations;

  const toggleChart = (chartId: string) => {
    setActiveChartIds((prev) =>
      prev.includes(chartId)
        ? prev.filter((id) => id !== chartId)
        : [...prev, chartId]
    );
  };

  const displayedCharts = allAvailableCharts
    .filter((c) => activeChartIds.includes(c.id))
    .filter((c) => categoryFilter === 'ALL' || c.category === categoryFilter);

  const getMetricStatusStyle = (status: string) => {
    switch (status) {
      case 'good':
        return 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200';
      case 'warning':
        return 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border-amber-200';
      case 'bad':
        return 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/40 border-red-200';
      default:
        return 'text-ink-700 dark:text-ink-300 bg-paper-100 dark:bg-ink-900 border-line';
    }
  };

  const renderChartBody = (chart: ChartSpecification) => {
    switch (chart.chart_type) {
      case 'radar':
        return <RadarChart chart={chart} />;
      case 'latency_curve':
        return <LatencyCurveChart chart={chart} />;
      case 'defect_donut':
        return <SeverityDonutChart chart={chart} />;
      case 'engine_comparison_bar':
        return <EngineComparisonBarChart chart={chart} />;
      case 'journey_funnel':
        return <JourneyFunnelChart chart={chart} />;
      default:
        return <RadarChart chart={chart} />;
    }
  };

  return (
    <section className="card p-5 sm:p-6 space-y-6">
      <div className="space-y-3 border-b border-line pb-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <p className="label">Charts</p>
            <h3 className="font-serif text-2xl text-ink mt-1">Visual summary</h3>
          </div>
          <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
            <span className="score-pill">{visualPayload.audit_case_profile}</span>
            <button
              type="button"
              onClick={() => setShowCustomizer(!showCustomizer)}
              className="btn-secondary px-3 py-1.5 text-xs"
            >
              {showCustomizer ? 'Done' : 'Customize'}
            </button>
          </div>
        </div>
        <p className="text-sm text-ink-500 leading-relaxed">
          {visualPayload.ai_rationale}
        </p>

        {/* Customizer Toolbar Drawer */}
        {showCustomizer && (
          <div className="bg-paper-100/80 dark:bg-ink-800/80 border border-line p-4 rounded-lg space-y-3 animate-fade-in text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-ink uppercase tracking-wider text-[11px]">
                Toggle Active Visualizations for this Audit
              </span>
              <span className="text-ink-400 font-mono text-[10px]">
                {activeChartIds.length} of {allAvailableCharts.length} active
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {allAvailableCharts.map((c) => {
                const isActive = activeChartIds.includes(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleChart(c.id)}
                    className={`px-3 py-1.5 rounded-md font-medium text-xs border transition-all flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-pine text-white border-pine shadow-xs'
                        : 'bg-paper-50 dark:bg-ink-900 text-ink-500 border-line hover:border-ink-400'
                    }`}
                  >
                    <span>{isActive ? '✓' : '+'}</span>
                    {c.title}
                  </button>
                );
              })}
            </div>

            {/* Filter by Category */}
            <div className="flex items-center gap-2 pt-2 border-t border-line/60">
              <span className="text-ink-500 font-mono text-[11px]">Pillar Filter:</span>
              {['ALL', 'OVERALL', 'TECHNICAL_SEO', 'GEO', 'UX_CONVERSION'].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-2.5 py-0.5 rounded text-[11px] font-mono ${
                    categoryFilter === cat
                      ? 'bg-pine/15 text-pine font-bold'
                      : 'text-ink-500 hover:text-ink'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. Spotlight Metric Numbers Row                                */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="label">Key metrics</span>
          <span className="text-xs text-ink-400">{report.domain}</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {visualPayload.spotlight_metrics.map((metric: SpotlightMetric) => (
            <div
              key={metric.id}
              className="bg-paper-50 dark:bg-ink-900/60 border border-line rounded-lg p-3.5 flex flex-col justify-between hover:border-pine/50 transition-all group"
              title={metric.significance}
            >
              <div>
                <span className="label text-[10px] block truncate text-ink-500">{metric.label}</span>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="font-serif text-2xl sm:text-3xl font-bold text-ink leading-tight">
                    {metric.value}
                  </span>
                  {metric.unit && (
                    <span className="text-[11px] font-mono text-ink-400 font-medium">{metric.unit}</span>
                  )}
                </div>
              </div>

              <div className="mt-2.5 pt-2 border-t border-line/60 flex items-center justify-between">
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-semibold ${getMetricStatusStyle(
                    metric.status
                  )}`}
                >
                  {metric.change_indicator || 'Calibrated'}
                </span>
                <span className="text-[10px] text-ink-400 group-hover:text-pine transition-colors cursor-help">
                  ℹ️
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 3. Dynamic Charts Adaptive Grid                                */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="label text-pine text-xs">AI-Selected Visual Diagnostics</span>
          <span className="text-[11px] font-mono text-ink-400">{displayedCharts.length} Visualizations Rendered</span>
        </div>

        {displayedCharts.length === 0 ? (
          <div className="bg-paper-50 border border-line p-8 rounded-lg text-center text-ink-500 text-sm">
            No charts match the active filters. Click "Customize Visuals" above to reactivate charts.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {displayedCharts.map((chart) => {
              // Full-width spans for wide charts like Engine Matrix or Latency Curve if odd
              const isFullWidth = chart.chart_type === 'engine_comparison_bar' && displayedCharts.length % 2 !== 0;

              return (
                <div
                  key={chart.id}
                  className={`bg-paper-50 dark:bg-ink-900/40 border border-line rounded-xl p-5 sm:p-6 flex flex-col justify-between shadow-2xs hover:border-line-dark transition-all ${
                    isFullWidth ? 'lg:col-span-2' : ''
                  }`}
                >
                  {/* Chart Header */}
                  <div>
                    <div className="flex items-center justify-between gap-2 border-b border-line pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-pine" />
                          <h4 className="font-serif text-lg sm:text-xl font-bold text-ink">
                            {chart.title}
                          </h4>
                        </div>
                        <p className="text-xs text-ink-500 mt-0.5">{chart.subtitle}</p>
                      </div>
                      <span className="text-[10px] font-mono bg-paper-100 dark:bg-ink-800 text-ink-600 px-2 py-1 rounded border border-line">
                        {chart.category}
                      </span>
                    </div>

                    {/* AI Strategic Takeaway Insight */}
                    <div className="mt-3.5 bg-paper-100/90 dark:bg-ink-800/60 p-3 rounded-md border border-line/80 text-xs text-ink-700 dark:text-ink-300 leading-relaxed">
                      <span className="font-bold text-pine font-mono block text-[10px] uppercase tracking-wider mb-0.5">
                        💡 AI Strategic Takeaway
                      </span>
                      {chart.ai_insight}
                    </div>
                  </div>

                  {/* Chart Body */}
                  <div className="mt-5 flex items-center justify-center min-h-[220px]">
                    {renderChartBody(chart)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
