import React from 'react';
import {
  BusinessProfile,
  OverallScoreResult,
  SemanticBusinessRepresentation,
  ContradictionReport,
  HonestScores,
  ExecutiveReport,
  TabId,
} from '../types';
import { categoryLabel, display, formatPercent, humanize, scoreBar, scoreTone } from '../lib/format';
import { WebsiteIntelligenceTriadHero } from './WebsiteIntelligenceTriadHero';
import { AdaptiveVisualIntelligence } from './VisualIntelligence/AdaptiveVisualIntelligence';
import { Card, Section } from './ui';

interface OverviewProps {
  scores: OverallScoreResult;
  honestScores?: HonestScores;
  profile: BusinessProfile;
  semantic?: SemanticBusinessRepresentation;
  contradictions?: ContradictionReport[];
  story: string;
  opportunity: string;
  strengths: string[];
  blockers: string[];
  ignore: string;
  report?: ExecutiveReport;
  onNavigate?: (tab: TabId) => void;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="label mb-1">{label}</p>
      <p className="text-ink-700">{value}</p>
    </div>
  );
}

function formatContradictionText(raw: any): string {
  if (!raw) return '';
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        const parsed = JSON.parse(trimmed.replace(/'/g, '"'));
        const parts = [];
        if (parsed.contradiction) parts.push(parsed.contradiction);
        if (parsed.evidence) parts.push(parsed.evidence);
        if (parsed.business_impact) parts.push(`Business Impact: ${parsed.business_impact}`);
        if (parts.length > 0) return parts.join(' — ');
      } catch {
        // Fall back to clean string
      }
    }
    return raw;
  }
  if (typeof raw === 'object') {
    const parts = [];
    if (raw.contradiction) parts.push(raw.contradiction);
    if (raw.evidence) parts.push(raw.evidence);
    if (raw.business_impact) parts.push(`Business Impact: ${raw.business_impact}`);
    if (parts.length > 0) return parts.join(' — ');
  }
  return String(raw);
}

export function Overview({
  scores,
  honestScores,
  profile,
  semantic,
  contradictions,
  story,
  opportunity,
  strengths,
  blockers,
  ignore,
  report,
  onNavigate,
}: OverviewProps) {
  const categories = Object.entries(scores.category_scores || {});
  const activeContradictions = contradictions || (semantic?.contradiction ? [semantic.contradiction] : []);
  const comparison = report?.three_way_comparison;

  return (
    <div className="space-y-10">
      {report && (
        <WebsiteIntelligenceTriadHero
          report={report}
          onNavigate={onNavigate || (() => {})}
          activeTab="overview"
        />
      )}

      {activeContradictions.length > 0 && (
        <Card className="border-l-4 border-warn rounded-l-none">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <p className="label text-warn">Identity conflict</p>
            <span className="text-xs text-ink-500">
              {activeContradictions[0].confidence != null
                ? `${Math.round(activeContradictions[0].confidence * 100)}% confidence`
                : 'Calibrating'}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm mb-3">
            <Field label="Declared type" value={activeContradictions[0].declared_type || 'Unspecified'} />
            <Field label="Detected type" value={display(activeContradictions[0].detected_type)} />
          </div>
          <p className="text-sm text-ink-700 leading-relaxed">
            {formatContradictionText(activeContradictions[0].reason)}
          </p>
        </Card>
      )}

      <Section title="Executive summary">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2">
            <p className="label mb-2">Story</p>
            <p className="text-ink-700 leading-relaxed">{display(story)}</p>
          </Card>
          <Card>
            <p className="label mb-2">Main opportunity</p>
            <p className="text-ink-700 leading-relaxed">{display(opportunity)}</p>
          </Card>
        </div>
      </Section>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <p className="label mb-3">Working</p>
          {strengths.length === 0 ? (
            <p className="text-ink-400">—</p>
          ) : (
            <ul className="space-y-2 text-sm text-ink-700">
              {strengths.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <p className="label mb-3">Holding it back</p>
          {blockers.length === 0 ? (
            <p className="text-ink-400">—</p>
          ) : (
            <ul className="space-y-2 text-sm text-ink-700">
              {blockers.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <p className="label mb-3">Ignore for now</p>
          <p className="text-sm text-ink-700 leading-relaxed">{display(ignore)}</p>
        </Card>
      </div>

      {honestScores && (
        <Section title="Honest scores" description="Human clarity and Google crawl quality are scored from the crawl. AI readiness is on-page. Live citations stay blank until an engine is queried.">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <p className="label mb-1">Human</p>
              <p className="font-serif text-3xl text-ink">{Math.round(honestScores.human_score)}</p>
              <p className="mt-2 text-xs text-ink-500 leading-relaxed">{display(honestScores.human_summary)}</p>
            </Card>
            <Card>
              <p className="label mb-1">Search</p>
              <p className="font-serif text-3xl text-ink">{Math.round(honestScores.google_score)}</p>
              <p className="mt-2 text-xs text-ink-500 leading-relaxed">{display(honestScores.google_summary)}</p>
            </Card>
            <Card>
              <p className="label mb-1">AI readiness</p>
              <p className="font-serif text-3xl text-ink">
                {honestScores.ai_readiness_score != null ? Math.round(honestScores.ai_readiness_score) : '—'}
              </p>
              <p className="mt-2 text-xs text-ink-500 leading-relaxed">On-page extractability. Not a ChatGPT rank.</p>
            </Card>
            <Card>
              <p className="label mb-1">Live citations</p>
              <p className="font-serif text-3xl text-ink">
                {honestScores.ai_visibility_status === 'MEASURED' && honestScores.ai_visibility_score != null
                  ? Math.round(honestScores.ai_visibility_score)
                  : '—'}
              </p>
              <p className="mt-2 text-xs text-ink-500 leading-relaxed">
                {honestScores.ai_visibility_status === 'MEASURED' ? 'Measured by a live engine run.' : 'Not measured on this audit.'}
              </p>
            </Card>
          </div>
        </Section>
      )}

      {report?.agent_readiness && (
        <Section title="Agent readiness" description="Whether a crawler can extract this site. Not a live citation rank.">
          <Card>
            <p className="font-serif text-3xl text-ink">
              {report.agent_readiness.score != null ? Math.round(report.agent_readiness.score) : '—'}
            </p>
            <p className="mt-2 text-sm text-ink-700">{display(report.agent_readiness.summary)}</p>
            <ul className="mt-4 space-y-2 text-sm text-ink-700">
              {report.agent_readiness.signals.map((signal) => (
                <li key={signal.key}>
                  <span className="font-mono text-xs text-ink-500">{signal.status}</span> {signal.summary}
                </li>
              ))}
            </ul>
          </Card>
        </Section>
      )}

      {semantic && (
        <Section title="Business identity">
          <Card>
            {semantic.llm_status === 'failed' && (
              <div className="mb-4 p-3 rounded-lg bg-bad/5 border border-bad/20">
                <p className="label text-bad mb-1">Identity unavailable</p>
                <p className="text-sm text-ink-700">
                  {semantic.llm_failure_reason || semantic.consensus_summary || 'Business intelligence did not return a result.'}
                </p>
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <Field label="Business model" value={display(semantic.business_model)} />
              <Field label="Website type" value={display(semantic.website_type)} />
              <Field label="Industry" value={[display(semantic.industry), display(semantic.sub_industry)].filter((v) => v !== '—').join(' · ') || '—'} />
              <Field
                label="Audience"
                value={semantic.target_audience?.slice(0, 2).join(' · ') || display(profile.target_audience)}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-5 pt-5 border-t border-line">
              <Field label="Name" value={display(profile.business_name)} />
              <Field label="Intent" value={humanize(semantic.primary_intent || profile.primary_intent)} />
              <Field label="Primary CTA" value={display(profile.primary_cta)} />
            </div>
            {semantic.journey_stages && semantic.journey_stages.length > 0 && (
              <div className="mt-5 pt-5 border-t border-line">
                <p className="label mb-2">Customer journey</p>
                <p className="text-sm text-ink-700">{semantic.journey_stages.join(' → ')}</p>
              </div>
            )}
          </Card>
        </Section>
      )}

      {comparison && (
        <Section title="Three perspectives">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <p className="label mb-2">Human visitor</p>
              <p className="text-sm text-ink-700 leading-relaxed">{display(comparison.human_visitor_perspective)}</p>
            </Card>
            <Card>
              <p className="label mb-2">Search engine</p>
              <p className="text-sm text-ink-700 leading-relaxed">{display(comparison.search_engine_perspective)}</p>
            </Card>
            <Card>
              <p className="label mb-2">Answer engine</p>
              <p className="text-sm text-ink-700 leading-relaxed">{display(comparison.ai_answer_engine_perspective)}</p>
            </Card>
          </div>
        </Section>
      )}

      {report && <AdaptiveVisualIntelligence report={report} />}

      <Section title="Category scores" description={`Confidence ${formatPercent(scores.overall_confidence)} · Evidence ${formatPercent(scores.evidence_coverage)}`}>
        {categories.length === 0 ? (
          <p className="text-ink-400">—</p>
        ) : (
          <Card>
            <div className="space-y-5">
              {categories.map(([key, cat]) => (
                <div key={key}>
                  <div className="flex items-baseline justify-between gap-4 mb-1.5">
                    <span className="text-ink">{categoryLabel(key)}</span>
                    <span className={`font-mono text-sm ${scoreTone(cat.score)}`}>
                      {Math.round(cat.score)}
                      <span className="text-ink-400"> / 100</span>
                    </span>
                  </div>
                  <div className="h-1 bg-ink-300/40 rounded-full overflow-hidden">
                    <div className={`h-full ${scoreBar(cat.score)}`} style={{ width: `${Math.max(2, cat.score)}%` }} />
                  </div>
                  <p className="mt-2 text-sm text-ink-500">{display(cat.summary)}</p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </Section>
    </div>
  );
}
