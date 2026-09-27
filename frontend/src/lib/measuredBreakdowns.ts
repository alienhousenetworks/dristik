import { ExecutiveReport } from '../types';
import { categoryLabel } from './format';

export interface MeasuredBar {
  label: string;
  value: number;
}

export interface MeasuredBreakdown {
  id: string;
  title: string;
  note: string;
  bars: MeasuredBar[];
}

function counts(items: string[]): MeasuredBar[] {
  const tally = new Map<string, number>();
  for (const item of items) {
    tally.set(item, (tally.get(item) || 0) + 1);
  }
  return Array.from(tally.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);
}

/**
 * Breakdowns the score radar and severity donut do not already show.
 * A chart is returned only when the split itself is informative.
 */
export function measuredBreakdowns(report: ExecutiveReport): MeasuredBreakdown[] {
  const charts: MeasuredBreakdown[] = [];
  const findings = report.findings || [];

  const categoryBars = counts(
    findings.map((finding) => categoryLabel(String(finding.category || 'Other')))
  ).filter((bar) => bar.value > 0);
  if (categoryBars.length >= 2) {
    charts.push({
      id: 'chart_findings_by_category',
      title: 'Findings by category',
      note: 'Where the recorded findings sit. Severity is a separate chart.',
      bars: categoryBars,
    });
  }

  const questions = report.geo_readiness?.questions || [];
  const questionBars = counts(questions.map((question) => question.status || 'Unspecified'));
  if (questions.length >= 3 && questionBars.length >= 2) {
    charts.push({
      id: 'chart_geo_answer_status',
      title: 'Buyer questions by answer status',
      note: 'On-page answerability from the crawled pages. This is not a live citation count.',
      bars: questionBars,
    });
  }

  const rubricBars = counts(
    findings
      .map((finding) => finding.confidence_rubric)
      .filter((band): band is 'CERTAIN' | 'LIKELY' | 'GUESSING' =>
        band === 'CERTAIN' || band === 'LIKELY' || band === 'GUESSING')
  );
  if (rubricBars.length >= 2) {
    charts.push({
      id: 'chart_confidence_rubric',
      title: 'Finding confidence',
      note: 'Certain means two sources agree. Guessing is not treated as a measured defect.',
      bars: rubricBars,
    });
  }

  return charts;
}
