import React from 'react';
import { ArrowRight, CheckCircle2, Database, Gauge, ShieldCheck } from 'lucide-react';
import { Card } from '../../ui';
import { SeoScorecardReport } from '../../../services/seoApi';

interface SeoScoreMethodologyProps {
  score: number | null;
  status?: string | null;
  checkedUrls: number;
  findingCount: number;
  scorecard?: SeoScorecardReport | null;
  onNavigate: (tab: string) => void;
}

const steps = [
  {
    number: '01',
    title: 'Collect observations',
    detail: 'Inspect the URLs, HTTP headers, raw HTML, and rendered DOM actually returned by this audit.',
    icon: Database,
  },
  {
    number: '02',
    title: 'Validate evidence',
    detail: 'Separate measured results from missing, unavailable, inferred, or untested data.',
    icon: ShieldCheck,
  },
  {
    number: '03',
    title: 'Calculate 9-dimension SEO index',
    detail: 'Compute S_SEO = Σ(W_d × S_d) / Σ(W_d) over applicable measured dimensions only.',
    icon: Gauge,
  },
  {
    number: '04',
    title: 'Verify remediations',
    detail: 'Track findings to stack-aware patches and re-crawl live URLs before marking VERIFIED_FIXED.',
    icon: CheckCircle2,
  },
];

export function SeoScoreMethodology({
  score,
  status,
  checkedUrls,
  findingCount,
  scorecard,
  onNavigate,
}: SeoScoreMethodologyProps) {
  const effectiveScore = scorecard?.overall_health_score ?? score;
  const unavailable = effectiveScore == null || !Number.isFinite(effectiveScore);
  const measurementState = unavailable
    ? 'Not measured'
    : status && ['PARTIAL', 'INCOMPLETE', 'SAMPLE_VERIFIED', 'SAMPLED_AUDIT'].includes(status.toUpperCase())
      ? 'Partial measurement'
      : 'Score available';

  return (
    <Card className="space-y-5 border-line bg-paper-50 p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-pine-600">How the rating works</p>
          <h3 className="mt-1 text-base font-semibold text-ink">From website evidence to an explainable SEO rating</h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-ink-500">
            This is the mathematical process behind the canonical scorecard ({scorecard?.methodology_version || 'dristik_seo_v3.0'}). Scores come from measured checks, not invented score weights; unavailable connectors or inapplicable dimensions are excluded from the denominator—never zeroed or treated as a pass.
          </p>
        </div>
        <div className="min-w-[140px] rounded-lg border border-line bg-paper-100 px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">Canonical SEO index</div>
          <div className="mt-1 font-mono text-2xl font-bold text-ink">{unavailable ? '—' : Math.round(effectiveScore)}</div>
          <div className="text-[10px] text-ink-500">/100 · {measurementState}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <React.Fragment key={step.number}>
              <div className="min-w-0 rounded-lg border border-line bg-paper-100/70 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-semibold text-pine-600">{step.number}</span>
                  <Icon className="h-4 w-4 text-pine-600" aria-hidden="true" />
                </div>
                <h4 className="mt-2 text-xs font-semibold text-ink">{step.title}</h4>
                <p className="mt-1 text-[11px] leading-5 text-ink-500">{step.detail}</p>
              </div>
              {index < steps.length - 1 && (
                <ArrowRight className="hidden h-4 w-4 self-center text-ink-400 md:hidden" aria-hidden="true" />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {scorecard?.dimensions && scorecard.dimensions.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-line bg-paper">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-subtle text-[10px] uppercase text-ink-400">
                <th className="py-2 px-3">Dimension</th>
                <th className="py-2 px-3">Configured Wt</th>
                <th className="py-2 px-3">Effective Wt</th>
                <th className="py-2 px-3">Checks Passed</th>
                <th className="py-2 px-3">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {scorecard.dimensions.map((d) => (
                <tr key={d.dimension_id}>
                  <td className="py-2 px-3 font-medium text-ink">{d.name}</td>
                  <td className="py-2 px-3 font-mono text-ink-600">{Math.round(d.configured_weight * 100)}%</td>
                  <td className="py-2 px-3 font-mono text-ink-600">
                    {d.effective_weight != null ? `${Math.round(d.effective_weight * 100)}%` : 'Excluded'}
                  </td>
                  <td className="py-2 px-3 font-mono text-ink-600">
                    {d.passed_checks_count}/{d.executed_checks_count}
                  </td>
                  <td className="py-2 px-3 font-mono font-bold text-ink">
                    {d.score != null ? `${Math.round(d.score)}/100` : !d.is_applicable ? 'Not Applicable' : 'Unmeasured'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-500">
          <span><strong className="text-ink">{checkedUrls}</strong> URLs in the saved crawl result</span>
          <span><strong className="text-ink">{findingCount}</strong> SEO findings in this report</span>
          {scorecard && (
            <span>
              Active weight denominator: <strong className="text-ink">{Math.round(scorecard.active_weight_sum * 100)}%</strong>
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => onNavigate('issues')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-pine-600 hover:underline"
        >
          Review evidence and gaps <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </Card>
  );
}
