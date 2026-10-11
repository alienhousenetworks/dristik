import React from 'react';
import { ExecutiveReport, Finding, TabId } from '../types';
import { PageHeader } from './ui';

const SEVERITY_RANK: Record<string, number> = {
  CRITICAL: 5,
  HIGH: 4,
  MEDIUM: 3,
  LOW: 2,
  INFO: 1,
};

function rankFinding(finding: Finding): number[] {
  const business = SEVERITY_RANK[finding.calibrated_impact?.business_impact || ''] || finding.impact || 0;
  const confidence = finding.calibrated_impact?.confidence ?? finding.confidence ?? 0;
  return [business, confidence, -(finding.effort || 5), SEVERITY_RANK[finding.severity] || 0];
}

function compareFindings(left: Finding, right: Finding): number {
  const a = rankFinding(left);
  const b = rankFinding(right);
  for (let index = 0; index < a.length; index += 1) {
    if (a[index] !== b[index]) return b[index] - a[index];
  }
  return 0;
}

function channelState(report: ExecutiveReport, channel: 'search_console' | 'analytics'): string {
  return report.google_performance?.[channel]?.state || 'NOT_CONNECTED';
}

export function OperatingWorkflow({
  stage,
  report,
  onSelectTab,
}: {
  stage: 'discover' | 'decide' | 'execute' | 'prove';
  report: ExecutiveReport;
  onSelectTab: (tab: TabId) => void;
}) {
  const findings = [...(report.findings || [])].sort(compareFindings);
  const visibility = report.ai_visibility_scorecard;
  const patches = [...(report.remediation_patches || []), ...(report.code_patches || [])];
  const resolved = findings.filter((finding) => {
    const status = finding.remediation_verification?.status || finding.resolution_status;
    return status === 'RESOLVED' || status === 'VERIFIED';
  }).length;

  if (stage === 'discover') {
    return (
      <section className="space-y-6">
        <PageHeader
          kicker="01 / Discover"
          title="Brand intelligence"
          description="Domain profile, crawl coverage, technical health, AI citation coverage, and data freshness. SEO, GEO, AEO, CRO, and authority stay in their own sections."
        />
        <div className="grid gap-4 md:grid-cols-2">
          <article className="card p-5 space-y-2">
            <p className="label">Domain</p>
            <p className="text-lg text-ink">{report.domain || report.website_url}</p>
            <p className="text-sm text-ink-500">Report generated {report.generated_at || 'at an unknown time'}.</p>
          </article>
          <article className="card p-5 space-y-2">
            <p className="label">Crawl</p>
            <p className="text-sm text-ink-700">
              {report.crawl_manifest?.pages?.length ?? 'Unknown'} pages in the crawl manifest.
            </p>
            <button type="button" className="text-sm text-ink underline" onClick={() => onSelectTab('pages')}>
              Open the page inspector
            </button>
          </article>
          <article className="card p-5 space-y-2">
            <p className="label">AI visibility</p>
            <p className="text-sm text-ink-700">
              Status: {visibility?.status || 'not measured'}.
              {visibility?.successful_runs != null ? ` ${visibility.successful_runs} successful runs` : ''}
              {visibility?.queries != null ? ` across ${visibility.queries} prompts` : ''}.
            </p>
            {visibility?.mention_rate_pct != null && (
              <p className="font-mono text-sm text-ink">Mention rate {visibility.mention_rate_pct}%</p>
            )}
            {visibility?.citation_rate_pct != null && (
              <p className="font-mono text-sm text-ink">Citation rate {visibility.citation_rate_pct}%</p>
            )}
            <p className="text-sm text-ink-500">
              Not queried: {(visibility?.surfaces_not_queried || ['Google AI Overviews', 'Google AI Mode', 'Bing Copilot']).join(', ')}.
            </p>
            <p className="text-sm text-ink-500">
              {visibility?.measurement_note || visibility?.not_measured_reason || 'These rates stay separate. They are not folded into one score.'}
            </p>
            <button type="button" className="text-sm text-ink underline" onClick={() => onSelectTab('geo')}>
              Open GEO
            </button>
          </article>
          <article className="card p-5 space-y-2">
            <p className="label">Connected sources</p>
            <p className="text-sm text-ink-700">Search Console: {channelState(report, 'search_console')}</p>
            <p className="text-sm text-ink-700">Analytics: {channelState(report, 'analytics')}</p>
            <p className="text-sm text-ink-700">
              External authority: {report.external_authority ? 'attached' : 'not attached'}
            </p>
          </article>
        </div>
      </section>
    );
  }

  if (stage === 'decide') {
    return (
      <section className="space-y-6">
        <PageHeader
          kicker="02 / Decide"
          title="Prioritized opportunity center"
          description="Findings stay in the evidence ledger. This order uses business impact, confidence, lower effort, then technical severity."
        />
        {findings.length === 0 ? (
          <p className="text-sm text-ink-500">This audit has no findings to rank.</p>
        ) : (
          <ol className="space-y-3">
            {findings.slice(0, 12).map((finding, index) => (
              <li key={finding.finding_id} className="card p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-ink font-medium">{index + 1}. {finding.title}</p>
                  <p className="font-mono text-xs text-ink-500">{finding.severity} · {finding.category}</p>
                </div>
                <p className="mt-2 text-sm text-ink-600">{finding.why_it_matters || finding.description}</p>
                <p className="mt-2 text-xs text-ink-400">
                  Confidence {finding.confidence_label || finding.confidence}
                  {finding.evidence_scope ? ` · ${finding.evidence_scope}` : ''}
                  {finding.evidence_refs?.length ? ` · ${finding.evidence_refs.length} evidence refs` : ' · no evidence ref'}
                </p>
              </li>
            ))}
          </ol>
        )}
        <button type="button" className="text-sm text-ink underline" onClick={() => onSelectTab('findings')}>
          Open the full evidence ledger
        </button>
      </section>
    );
  }

  if (stage === 'execute') {
    return (
      <section className="space-y-6">
        <PageHeader
          kicker="03 / Execute"
          title="Remediation workspace"
          description="Patch previews stay in the developer patch pack. Consequential factual changes need a person. An agent does not deploy to production on its own."
        />
        <p className="text-sm text-ink-500">
          A merged change is a deployment record. It is not a citation increase and it is not a revenue increase.
        </p>
        {patches.length === 0 ? (
          <p className="text-sm text-ink-500">This audit has no patches yet. The findings and roadmap are unchanged.</p>
        ) : (
          <ul className="space-y-3">
            {patches.slice(0, 12).map((patch) => (
              <li key={patch.patch_id} className="card p-4">
                <p className="text-ink font-medium">{patch.title}</p>
                <p className="mt-1 font-mono text-xs text-ink-500">
                  {patch.patch_id}
                  {'risk_level' in patch && patch.risk_level ? ` · ${patch.risk_level}` : ''}
                  {'approval_status' in patch && patch.approval_status ? ` · ${patch.approval_status}` : ''}
                  {'release_status' in patch && patch.release_status ? ` · ${patch.release_status}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-4">
          <button type="button" className="text-sm text-ink underline" onClick={() => onSelectTab('patches')}>
            Open the patch pack
          </button>
          <button type="button" className="text-sm text-ink underline" onClick={() => onSelectTab('verification')}>
            Open verification
          </button>
        </div>
      </section>
    );
  }

  const search = report.google_performance?.search_console;
  const analytics = report.google_performance?.analytics;
  return (
    <section className="space-y-6">
      <PageHeader
        kicker="04 / Prove"
        title="Impact and evidence center"
        description="Technical checks, visibility measurements, and business outcomes stay in separate layers. A higher score is not attributed to a patch unless the measurement says so."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <article className="card p-5 space-y-2">
          <p className="label">Technical verification</p>
          <p className="font-mono text-2xl text-ink">{resolved}<span className="text-base text-ink-400">/{findings.length}</span></p>
          <p className="text-sm text-ink-500">Findings with a resolved or verified re-check. The rest stay open.</p>
        </article>
        <article className="card p-5 space-y-2">
          <p className="label">Search visibility</p>
          <p className="text-sm text-ink-700">
            {visibility?.successful_runs
              ? `${visibility.successful_runs} successful observations. Mention and citation rates are separate.`
              : 'No live AI visibility measurement is attached. Nothing is filled in as zero citations.'}
          </p>
          {visibility?.repeats != null && visibility.repeats > 0 && (
            <p className="text-sm text-ink-500">
              {visibility.repeats} repeats are a budget. They are not, by themselves, a precision guarantee.
            </p>
          )}
        </article>
        <article className="card p-5 space-y-2">
          <p className="label">Business outcome</p>
          <p className="text-sm text-ink-700">Search Console: {search?.state || 'NOT_CONNECTED'}</p>
          <p className="text-sm text-ink-700">Analytics: {analytics?.state || 'NOT_CONNECTED'}</p>
          {search?.state === 'MEASURED' && (
            <p className="font-mono text-sm text-ink">{search.clicks ?? '—'} clicks · {search.impressions ?? '—'} impressions</p>
          )}
          {analytics?.state === 'MEASURED' && (
            <p className="font-mono text-sm text-ink">{analytics.sessions ?? '—'} sessions · {analytics.conversions ?? '—'} conversions</p>
          )}
          <p className="text-sm text-ink-500">
            Observed values are not an associated-revenue model and not an incremental-impact estimate.
          </p>
        </article>
      </div>
      <button type="button" className="text-sm text-ink underline" onClick={() => onSelectTab('report')}>
        Open the presentation report
      </button>
    </section>
  );
}
