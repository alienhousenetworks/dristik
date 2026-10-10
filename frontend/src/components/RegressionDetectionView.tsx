import React, { useMemo } from 'react';
import { ExecutiveReport, RegressionReport, AuditSnapshot, RegressionItem } from '../types';
import { scoreTone } from '../lib/format';
import { buildDisplayedScore } from '../lib/displayedAuditScore';

interface RegressionDetectionViewProps {
  report: ExecutiveReport;
  variant?: 'card' | 'report_section';
}

const DEMO_SEALS = new Set([
  'sha256:7f3a8b291c4e09f',
  'sha256:9b1c4e820f17a32',
  'sha256:4d8e72f91a3c650',
]);

const DEMO_RUNS = new Set(['Sep 24|27', 'Oct 02|61']);

function parseSnapshotDay(dateStr: string, now: Date): Date | null {
  const text = (dateStr || '').trim();
  const withYear = text.match(/^([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})$/);
  if (withYear) {
    const parsed = new Date(`${withYear[1]} ${withYear[2]}, ${withYear[3]}`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const monthDay = text.match(/^([A-Za-z]+)\s+(\d{1,2})$/);
  if (!monthDay) return null;
  const parsed = new Date(`${monthDay[1]} ${monthDay[2]}, ${now.getFullYear()}`);
  if (Number.isNaN(parsed.getTime())) return null;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  const ahead = (day.getTime() - today.getTime()) / 86400000;
  if (ahead > 120) {
    day.setFullYear(day.getFullYear() - 1);
  }
  return day;
}

function isSimulatedSnapshot(snap: AuditSnapshot, now = new Date()): boolean {
  if (DEMO_SEALS.has(snap.evidence_seal || '')) return true;
  const scoreKey = `${snap.date}|${Number(snap.score)}`;
  if (DEMO_RUNS.has(scoreKey)) return true;
  const parsed = parseSnapshotDay(snap.date, now);
  if (!parsed) return false;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  return day.getTime() > today.getTime();
}

function auditDate(generatedAt?: string): string {
  if (!generatedAt) return 'This audit';
  const matched = generatedAt.match(/^([A-Za-z]+\s+\d{1,2},\s+\d{4})/);
  if (matched) return matched[1];
  const parsed = new Date(generatedAt);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }
  return generatedAt;
}

function formatDelta(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return rounded > 0 ? `+${text}` : text;
}

function snapshotFromReport(report: ExecutiveReport): RegressionReport {
  const displayed = buildDisplayedScore(report).composite;
  const score = displayed != null ? displayed : report.scores?.overall_score;
  const seal = report.sealed_evidence_snapshot_id || report.analysis_id || report.report_id || 'current';
  const categoryScores: Record<string, number> = {};
  const categories = report.scores?.category_scores || {};
  for (const [key, value] of Object.entries(categories)) {
    if (key === 'GEO' && typeof report.geo_readiness?.extractability_score === 'number') {
      categoryScores[key] = report.geo_readiness.extractability_score;
      continue;
    }
    if (value && typeof value.score === 'number') categoryScores[key] = value.score;
  }
  const snap: AuditSnapshot = {
    snapshot_id: seal,
    run_label: 'Run #001',
    date: auditDate(report.generated_at),
    score: typeof score === 'number' ? score : 0,
    category_scores: categoryScores,
    evidence_seal: report.sealed_evidence_snapshot_id || 'not sealed',
    verified_schema_types: report.geo_readiness?.schema_types || [],
    findings_count: report.findings?.length || 0,
    status: 'HEALTHY',
  };
  return {
    has_regression: false,
    regression_count: 0,
    score_delta: 0,
    current_run: snap,
    regressions: [],
    historical_timeline: typeof score === 'number' ? [snap] : [],
    summary: 'First sealed audit. No earlier snapshot was measured, so there is no regression to report.',
    detected_at: report.generated_at || '',
  };
}

function sanitizeRegression(report: RegressionReport): RegressionReport {
  const timeline = (report.historical_timeline || []).filter((snap) => !isSimulatedSnapshot(snap));
  const dropped = timeline.length !== (report.historical_timeline || []).length;
  const baselineKept = !!report.baseline_run && timeline.some((snap) => snap.snapshot_id === report.baseline_run?.snapshot_id);
  if (!dropped && timeline.length > 0 && (timeline.length < 2 || baselineKept || !report.baseline_run)) {
    return { ...report, historical_timeline: timeline };
  }
  if (timeline.length >= 2 && baselineKept) {
    return { ...report, historical_timeline: timeline };
  }
  const current = timeline[timeline.length - 1];
  return {
    has_regression: false,
    regression_count: 0,
    score_delta: 0,
    current_run: current,
    regressions: [],
    historical_timeline: timeline,
    summary: 'First sealed audit. No earlier snapshot was measured, so there is no regression to report.',
    detected_at: report.detected_at,
  };
}

function statusLabel(status: string): string {
  if (status === 'REGRESSION') return 'Regressed';
  if (status === 'IMPROVED') return 'Improved';
  return 'Baseline';
}

export function RegressionDetectionView({
  report,
  variant = 'card',
}: RegressionDetectionViewProps) {
  const regressionData = useMemo<RegressionReport>(() => {
    const incoming = report.regression_report;
    if (incoming && Array.isArray(incoming.historical_timeline) && incoming.historical_timeline.length > 0) {
      return sanitizeRegression(incoming);
    }
    return snapshotFromReport(report);
  }, [report]);

  const timeline = regressionData.historical_timeline || [];
  const current = regressionData.current_run || timeline[timeline.length - 1];
  const baseline = regressionData.baseline_run;
  const comparable = timeline.length >= 2 && !!baseline && !!current;
  const overallRegressed = comparable && regressionData.score_delta < 0;
  const items: RegressionItem[] = comparable ? regressionData.regressions || [] : [];
  const isReportVariant = variant === 'report_section';

  return (
    <div className={`space-y-4 font-sans ${isReportVariant ? 'text-ink' : ''}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.04em] text-ink-700 bg-paper-200 px-2 py-0.5 border border-line rounded">
              Continuous Website Assurance
            </span>
            <span className="text-xs font-mono text-ink-500">
              Sealed snapshot diff
            </span>
          </div>
          <h3 className="text-xl font-sans font-bold text-ink mt-1">
            Automated Regression Detection
          </h3>
          <p className="text-xs text-ink-600 mt-0.5">
            Compares this audit with earlier sealed crawls of the same site. A drop is reported only when both runs were measured.
          </p>
        </div>

        {overallRegressed && (
          <div className="flex items-center gap-2 bg-bad/10 border border-bad/30 px-3 py-1.5 rounded text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-bad/10" />
            <span className="font-bold text-bad uppercase">
              Score down since the previous audit
            </span>
          </div>
        )}
      </div>

      <div className="p-4 bg-paper-100 border border-line rounded shadow-xs space-y-3">
        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.04em] text-ink-500 block">
          Sequential audit snapshot chain
        </span>

        {timeline.length === 0 ? (
          <p className="text-sm text-ink-600">
            This audit has no sealed score yet, so there is nothing to compare.
          </p>
        ) : (
          <div className={`grid grid-cols-1 gap-3 ${timeline.length > 1 ? 'md:grid-cols-3' : 'md:grid-cols-1 max-w-sm'}`}>
            {timeline.map((snap, idx) => {
              const isCurrent = idx === timeline.length - 1;
              const isBaseline = comparable && snap.snapshot_id === baseline?.snapshot_id;
              return (
                <div
                  key={`${snap.snapshot_id}-${idx}`}
                  className={`p-3.5 rounded border ${
                    isCurrent && snap.status === 'REGRESSION'
                      ? 'bg-bad/10 border-bad/30'
                      : isBaseline
                      ? 'bg-paper-50 border-line'
                      : 'bg-paper-50 border-line'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono font-bold text-xs text-ink">
                      {snap.run_label}
                    </span>
                    <span className="text-[11px] font-mono text-ink-500">
                      {snap.date}
                    </span>
                  </div>

                  <div className="flex items-baseline justify-between mb-2">
                    <span className="text-[11px] text-ink-500 font-mono">Score:</span>
                    <span className={`text-2xl font-mono font-bold ${scoreTone(snap.score)}`}>
                      {Math.round(snap.score)}
                      <span className="text-xs text-ink-400 font-normal"> / 100</span>
                    </span>
                  </div>

                  <div className="space-y-1 pt-2 border-t border-line text-[10px] font-mono">
                    <div className="text-ink-600">
                      <span className="block text-ink-500">Evidence seal</span>
                      <span className="text-ink-700 break-all">{snap.evidence_seal}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-ink-500">Status:</span>
                      <span
                        className={`px-1.5 py-0.2 rounded font-bold uppercase ${
                          snap.status === 'REGRESSION'
                            ? 'bg-bad/10 text-bad'
                            : snap.status === 'IMPROVED'
                            ? 'bg-good/10 text-good'
                            : 'bg-paper-200 text-ink-700'
                        }`}
                      >
                        {statusLabel(snap.status)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!comparable && timeline.length > 0 && (
          <p className="text-xs text-ink-600 leading-relaxed">
            {regressionData.summary} The next audit of this domain is compared with this seal.
          </p>
        )}
      </div>

      {comparable && (
        <div className={`border rounded p-5 space-y-4 ${overallRegressed || items.length > 0 ? 'border-bad/30 bg-bad/10' : 'border-line bg-paper-50'}`}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
            <div>
              <h4 className="text-base font-bold text-ink">
                {items.length > 0
                  ? `${items.length} measured drop${items.length === 1 ? '' : 's'} since ${baseline.run_label}`
                  : `No measured drop since ${baseline.run_label}`}
              </h4>
              <p className="text-xs text-ink-700 mt-1 font-mono">
                {current.run_label} ({current.date}) vs {baseline.run_label} ({baseline.date}) · Overall score {Math.round(baseline.score)} → {Math.round(current.score)} ({formatDelta(regressionData.score_delta)} pts)
              </p>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-paper-200 text-ink border border-line font-bold">
              Delta: {formatDelta(regressionData.score_delta)} pts
            </span>
          </div>

          {items.length > 0 && (
            <div className="space-y-2.5">
              {items.map((item, idx) => (
                <div
                  key={`${item.title}-${idx}`}
                  className="p-3 bg-paper-50 border border-line rounded flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold uppercase ${
                          item.severity === 'CRITICAL'
                            ? 'bg-bad/10 text-bad border border-bad/30'
                            : item.severity === 'HIGH'
                            ? 'bg-warn/10 text-warn border border-warn/30'
                            : 'bg-paper-200 text-ink-700 border border-line'
                        }`}
                      >
                        {item.severity}
                      </span>
                      <span className="font-bold text-ink text-sm">{item.title}</span>
                      <span className="text-[10px] font-mono text-ink-500">[{item.category}]</span>
                    </div>
                    <p className="text-[11px] text-ink-600 leading-relaxed font-sans">{item.description}</p>
                  </div>
                  {item.dimension_delta != null && (
                    <div className="font-mono font-bold text-bad whitespace-nowrap text-sm">
                      {formatDelta(item.dimension_delta)} pts
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="text-[11px] font-mono text-ink-500">
            Evidence seal {current.evidence_seal}
          </p>
        </div>
      )}
    </div>
  );
}
