import React, { useEffect, useState } from 'react';
import { Badge } from '../../ui';
import { api } from '../../../services/http';
import { ExecutiveReport } from '../../../types';

type ChapterStatus =
  | 'ISSUE_VERIFIED'
  | 'NO_ISSUE'
  | 'MEASURED'
  | 'INFERRED'
  | 'DATA_UNAVAILABLE'
  | 'NOT_TESTED'
  | 'NOT_APPLICABLE';

interface ScoreRow {
  category: string;
  score: number | null;
  status: 'sealed' | 'not_scored';
  note: string;
}

interface Subchapter {
  subchapter_id: string;
  title: string;
  status: ChapterStatus;
  note: string;
}

interface Chapter {
  chapter: number;
  title: string;
  status: ChapterStatus;
  summary: string;
  subchapters: Subchapter[];
}

interface AgentRow {
  agent_id: string;
  status: 'completed' | 'partial' | 'unavailable' | 'failed';
  coverage_note: string;
  error_code?: string | null;
  prompt_version?: string | null;
}

interface CardSection {
  number: number;
  heading: string;
  body: string;
}

interface FindingCard {
  finding_id: string;
  title: string;
  sections: CardSection[];
}

export interface EnterpriseSeoAssessment {
  report_stage: string;
  coverage: {
    statement: string;
    sampling_status: string;
    urls_discovered: number | null;
    urls_crawled: number | null;
  };
  scores: ScoreRow[];
  chapters: Chapter[];
  agents: AgentRow[];
  findings: Array<{
    finding_id: string;
    severity: string;
    scope: string;
    verification_status: string;
    evaluation_state?: string;
  }>;
  cards: FindingCard[];
  limitations: string[];
  diagnostic_summary?: string;
  deferred_modules?: string[];
}

const STATUS_LABEL: Record<ChapterStatus, string> = {
  ISSUE_VERIFIED: 'Issue verified',
  NO_ISSUE: 'No issue in the checked sample',
  MEASURED: 'Measured',
  INFERRED: 'Inferred',
  DATA_UNAVAILABLE: 'Data unavailable',
  NOT_TESTED: 'Not tested',
  NOT_APPLICABLE: 'Not applicable',
};

function statusTone(status: ChapterStatus): 'bad' | 'good' | 'warn' | 'neutral' | 'pine' {
  if (status === 'ISSUE_VERIFIED') return 'bad';
  if (status === 'NO_ISSUE') return 'good';
  if (status === 'INFERRED') return 'warn';
  if (status === 'MEASURED') return 'pine';
  return 'neutral';
}

function shortUrlPath(url?: string): string {
  if (!url) return '/';
  return url.replace(/^https?:\/\/[^/]+/i, '') || '/';
}

export function EnterpriseSeoPanel({
  assessment,
  report,
}: {
  assessment: EnterpriseSeoAssessment;
  report?: ExecutiveReport;
}) {
  const sourceUnavailable = assessment.agents.filter(
    (agent) => agent.status === 'unavailable' && !agent.agent_id.startsWith('seo.ai.'),
  );
  const aiHeld = assessment.agents.filter(
    (agent) => agent.agent_id.startsWith('seo.ai.') && agent.status !== 'completed',
  );
  const pages = (report?.crawl_manifest?.pages || report?.page_reports || []) as Array<Record<string, any>>;
  const allFindings = report?.findings || [];

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <p className="label">Coverage</p>
        <p className="text-body text-ink leading-relaxed">{assessment.coverage.statement}</p>
        {assessment.diagnostic_summary ? (
          <p className="text-sm text-ink leading-relaxed">{assessment.diagnostic_summary}</p>
        ) : null}
        <p className="text-sm text-ink-500">
          Report stage {assessment.report_stage}. Sampling {assessment.coverage.sampling_status}.
          {' '}
          {sourceUnavailable.length === 1
            ? '1 specialist is unavailable because its source was not stored.'
            : `${sourceUnavailable.length} specialists are unavailable because their source was not stored.`}
          {aiHeld.length === 1
            ? ' 1 AI specialist loaded a versioned prompt and did not publish a judgment.'
            : aiHeld.length > 1
              ? ` ${aiHeld.length} AI specialists loaded a versioned prompt and did not publish a judgment.`
              : ''}
        </p>
        {assessment.deferred_modules && assessment.deferred_modules.length > 0 ? (
          <p className="text-sm text-ink-500">
            Not executed in this phase: {assessment.deferred_modules.join(', ')}.
          </p>
        ) : null}
      </section>

      <section className="space-y-3">
        <h3 className="section-title">Scores</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          {assessment.scores.map((score) => (
            <div key={score.category} className="card p-4 space-y-1">
              <p className="label">{score.category}</p>
              <p className="font-mono text-xl text-ink">{score.score == null ? 'Not scored' : score.score}</p>
              <p className="text-sm text-ink-500 leading-relaxed">{score.note}</p>
            </div>
          ))}
        </div>
      </section>

      {pages.length > 0 && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="section-title">Page-by-Page &amp; URL-Level Optimization Dossiers</h3>
              <p className="text-xs text-ink-500">
                Full empirical website inspection across {pages.length} crawled URL(s): HTTP response, metadata, headings, schema JSON-LD, internal links, and page-specific optimization actions.
              </p>
            </div>
            <Badge tone="pine">{pages.length} URLs Audited</Badge>
          </div>

          <div className="space-y-3">
            {pages.map((pg, idx) => {
              const url = String(pg.url || '');
              const title = String(pg.title || '—');
              const meta = String(pg.meta_description || '—');
              const h1s: string[] = Array.isArray(pg.h1) ? pg.h1 : [];
              const h2Count = Array.isArray(pg.h2) ? pg.h2.length : 0;
              const wordCount = Number(pg.word_count || 0);
              const status = Number(pg.status_code || 200);
              const canonical = String(pg.canonical_url || '');
              const schemas: string[] = Array.isArray(pg.schema_types) ? pg.schema_types : [];
              const inLinks = Number(pg.internal_links_count ?? (Array.isArray(pg.internal_links) ? pg.internal_links.length : 0));
              const exLinks = Number(pg.external_links_count ?? (Array.isArray(pg.external_links) ? pg.external_links.length : 0));
              const totalImg = Number(pg.total_images ?? pg.image_count ?? 0);
              const missingAlt = Number(pg.images_without_alt ?? 0);
              const pageFindings = allFindings.filter((f) => {
                const urls = (f as any).affected_urls;
                return (Array.isArray(urls) && urls.includes(url)) || (f as any).url === url;
              });

              return (
                <div key={url || idx} className="card p-4 space-y-3 border-l-4 border-l-pine-600">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2">
                    <div>
                      <span className="font-mono text-sm font-semibold text-ink">{url}</span>
                      <span className="ml-2 text-xs text-ink-400">({shortUrlPath(url) === '/' ? 'Homepage' : 'Commercial / Content Page'})</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={status === 200 ? 'good' : 'bad'}>HTTP {status}</Badge>
                      <Badge tone={schemas.length > 0 ? 'good' : 'warn'}>
                        {schemas.length > 0 ? `Schema: ${schemas.join(', ')}` : '0 JSON-LD Schema'}
                      </Badge>
                      <Badge tone={pageFindings.length > 0 ? 'warn' : 'good'}>
                        {pageFindings.length} Issue(s)
                      </Badge>
                    </div>
                  </div>

                  <div className="grid gap-2 text-xs sm:grid-cols-2">
                    <div className="rounded bg-paper-50 p-2.5 border border-line/60">
                      <p className="font-mono text-[10px] uppercase text-ink-400">Title Tag ({title === '—' ? 0 : title.length} chars)</p>
                      <p className="mt-0.5 font-medium text-ink">{title}</p>
                    </div>
                    <div className="rounded bg-paper-50 p-2.5 border border-line/60">
                      <p className="font-mono text-[10px] uppercase text-ink-400">Meta Description ({meta === '—' ? 0 : meta.length} chars)</p>
                      <p className="mt-0.5 text-ink-700">{meta}</p>
                    </div>
                    <div className="rounded bg-paper-50 p-2.5 border border-line/60">
                      <p className="font-mono text-[10px] uppercase text-ink-400">Primary H1 ({h1s.length}) &amp; H2s ({h2Count})</p>
                      <p className="mt-0.5 font-medium text-ink">{h1s.length > 0 ? h1s.join(' | ') : 'Missing H1'}</p>
                    </div>
                    <div className="rounded bg-paper-50 p-2.5 border border-line/60">
                      <p className="font-mono text-[10px] uppercase text-ink-400">DOM &amp; Link Signals</p>
                      <p className="mt-0.5 text-ink-700">
                        {wordCount} words · Canonical: {canonical ? 'Self-referencing' : 'Missing'} · Links: {inLinks} in / {exLinks} out · Alt gaps: {missingAlt}/{totalImg}
                      </p>
                    </div>
                  </div>

                  {pageFindings.length > 0 && (
                    <div className="rounded bg-paper-100/70 p-2.5 text-xs space-y-1">
                      <p className="font-semibold text-ink">Page-Specific Findings &amp; Remediation Directives:</p>
                      <ul className="list-disc pl-4 space-y-1 text-ink-700">
                        {pageFindings.slice(0, 5).map((pf) => (
                          <li key={pf.finding_id}>
                            <span className="font-medium text-ink">{pf.title}:</span>{' '}
                            {pf.recommendation}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h3 className="section-title">Chapters</h3>
        <div className="space-y-2">
          {assessment.chapters.map((chapter) => (
            <details key={chapter.chapter} className="card p-4">
              <summary className="flex cursor-pointer items-center justify-between gap-3">
                <span className="text-sm font-medium text-ink">
                  {String(chapter.chapter).padStart(2, '0')} {chapter.title}
                </span>
                <Badge tone={statusTone(chapter.status)}>{STATUS_LABEL[chapter.status]}</Badge>
              </summary>
              <p className="mt-3 text-sm text-ink-500 leading-relaxed">{chapter.summary}</p>
              <ul className="mt-3 space-y-2">
                {chapter.subchapters.map((sub) => (
                  <li key={sub.subchapter_id} className="flex items-start justify-between gap-3 text-sm">
                    <span className="text-ink-700">
                      <span className="font-mono text-ink-400">{sub.subchapter_id}</span> {sub.title}
                      <span className="mt-1 block text-ink-500">{sub.note}</span>
                    </span>
                    <Badge tone={statusTone(sub.status)}>{STATUS_LABEL[sub.status]}</Badge>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="section-title">Findings</h3>
        {assessment.cards.length === 0 ? (
          <p className="text-sm text-ink-500">No validated finding was published from the stored evidence.</p>
        ) : (
          assessment.cards.map((card) => {
            const finding = assessment.findings.find((item) => item.finding_id === card.finding_id);
            return (
              <details key={card.finding_id} className="card p-4">
                <summary className="cursor-pointer text-sm font-medium text-ink">
                  {card.title}
                  {finding ? ` · ${finding.evaluation_state ? `${finding.evaluation_state} · ` : ''}${finding.severity} · ${finding.scope} · ${finding.verification_status}` : ''}
                </summary>
                <div className="mt-4 space-y-3">
                  {card.sections.map((section) => (
                    <div key={section.number}>
                      <p className="label">{section.number}. {section.heading}</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-ink-700 leading-relaxed">{section.body}</p>
                    </div>
                  ))}
                </div>
              </details>
            );
          })
        )}
      </section>

      <section className="space-y-2">
        <h3 className="section-title">Limitations</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-500">
          {assessment.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export function EnterpriseSeoAudit({
  analysisId,
  report,
}: {
  analysisId?: string;
  report?: ExecutiveReport;
}) {
  const [assessment, setAssessment] = useState<EnterpriseSeoAssessment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return undefined;
    let cancelled = false;
    setAssessment(null);
    setError(null);
    api<EnterpriseSeoAssessment>(
      `/api/v1/reports/${analysisId}/seo/enterprise`,
      {},
      'Enterprise SEO assessment failed',
    )
      .then((payload) => {
        if (!cancelled) setAssessment(payload);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Enterprise SEO assessment failed');
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  if (!analysisId) {
    return <p className="text-sm text-ink-500">Open a saved analysis to build the enterprise SEO assessment.</p>;
  }
  if (error) {
    return <p className="text-sm text-bad">{error}</p>;
  }
  if (!assessment) {
    return <p className="text-sm text-ink-500">Building the enterprise assessment from the sealed report.</p>;
  }
  return <EnterpriseSeoPanel assessment={assessment} report={report} />;
}
