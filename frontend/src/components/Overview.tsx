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
import { synthesizePillars } from '../lib/pillarSynthesis';
import { display, scoreTone } from '../lib/format';
import { ExecutiveTopActions } from './ExecutiveTopActions';
import { CalibrationLeaders } from './CalibrationAxes';
import { Card, Section } from './ui';
import {
  Search,
  Sparkles,
  Bot,
  Zap,
  Swords,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Building2,
  Target,
  FileCheck,
} from 'lucide-react';

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
  onOpenConnectors?: (tabId?: any) => void;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="label mb-1">{label}</p>
      <p className="text-ink-700 font-medium">{value}</p>
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
        /* fallback */
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
  const rollup = synthesizePillars(report);
  const activeContradictions = contradictions || (semantic?.contradiction ? [semantic.contradiction] : []);
  const overallScore = Math.round(scores.overall_score || 75);

  const disciplineCards = [
    {
      id: 'seo' as TabId,
      name: 'SEO: Technical & On-Page',
      shortName: 'SEO',
      icon: Search,
      score: rollup.seo.score,
      grade: rollup.seo.grade,
      summary: 'Robots.txt, XML sitemap, redirects, click depth, headings, meta tags, and internal link equity.',
      issuesCount: rollup.seo.findingsCount,
      color: 'text-pine',
    },
    {
      id: 'geo' as TabId,
      name: 'GEO: Generative Engines',
      shortName: 'GEO',
      icon: Sparkles,
      score: rollup.geo.score,
      grade: rollup.geo.grade,
      summary: 'GEO Readiness is on-page extractability. Live AI citation visibility is a separate measurement.',
      issuesCount: rollup.geo.findingsCount,
      color: 'text-emerald-700',
    },
    {
      id: 'aeo' as TabId,
      name: 'AEO: Answer Engine & Agents',
      shortName: 'AEO',
      icon: Bot,
      score: rollup.aeo.score,
      grade: rollup.aeo.grade,
      summary: 'Schema.org JSON-LD graphs, AI crawler directives, llms.txt, and 50-question deterministic extractability.',
      issuesCount: rollup.aeo.findingsCount,
      color: 'text-cyan-700',
    },
    {
      id: 'cro' as TabId,
      name: 'CRO: Conversion & UX',
      shortName: 'CRO',
      icon: Zap,
      score: rollup.cro.score,
      grade: rollup.cro.grade,
      summary: 'Form friction diagnostics, 5-second value proposition clarity, CTAs, and visual UX inspection.',
      issuesCount: rollup.cro.findingsCount,
      color: 'text-amber-700',
    },
    {
      id: 'competitors' as TabId,
      name: 'Competitor Intelligence',
      shortName: 'Competitors',
      icon: Swords,
      score: rollup.competitors.score,
      grade: rollup.competitors.grade,
      summary: 'Head-to-head intent bake-offs, side-by-side metric benchmarks, and market gap discovery.',
      issuesCount: rollup.competitors.findingsCount,
      color: 'text-rose-700',
    },
  ];

  return (
    <div className="space-y-8">
      {/* ─────────────────────────────────────────────────────────────
          1. ENTERPRISE SCORECARD HERO
          ───────────────────────────────────────────────────────────── */}
      <Card className="p-6 sm:p-8 bg-paper-100/90 border border-line relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase tracking-widest text-pine font-bold">
                Enterprise Executive Scorecard
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                Certified
              </span>
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-ink font-semibold tracking-tight">
              {report?.domain || profile?.business_name || 'Website Audit Intelligence'}
            </h1>
            <p className="text-xs text-ink-600 leading-relaxed">
              Overall Website Readiness from the crawled sample. GEO Readiness is separate from live AI citation visibility.
            </p>
            {typeof report?.crawl_manifest?.crawl_health?.sampling_note === 'string' && (
              <p className="text-xs text-ink-700 leading-relaxed border-l-2 border-pine/40 pl-3">
                {String(report.crawl_manifest.crawl_health.sampling_note)}
              </p>
            )}
          </div>

          <div className="flex items-center gap-4 shrink-0 bg-paper-50 p-4 rounded-xl border border-line">
            <div className="text-right">
              <span className="label text-[10px] text-ink-500 block">Overall Score</span>
              <span className={`font-serif text-4xl sm:text-5xl font-bold leading-none ${scoreTone(overallScore)}`}>
                {overallScore}
              </span>
              <span className="text-xs text-ink-400 block mt-0.5">/ 100</span>
            </div>
            <div className="h-12 w-px bg-line" />
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-1.5 font-mono">
                <span className="text-ink-400">Pages:</span>
                <span className="font-bold text-ink">{report?.crawl_manifest?.pages?.length || 1}</span>
              </div>
              <div className="flex items-center gap-1.5 font-mono">
                <span className="text-ink-400">Issues:</span>
                <span className="font-bold text-ink">{report?.findings?.length || 0}</span>
              </div>
              <div className="flex items-center gap-1.5 font-mono">
                <span className="text-ink-400">Patches:</span>
                <span className="font-bold text-good">{(report?.code_patches?.length || 0) + (report?.remediation_patches?.length || 0)} ready</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* ─────────────────────────────────────────────────────────────
          2. CORE DISCIPLINE WORKSPACE TILES (Direct Jump Links)
          ───────────────────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3 px-1">
          <p className="text-xs font-mono font-bold uppercase tracking-wider text-ink-500">
            Core Disciplines (Separated)
          </p>
          <span className="text-xs text-ink-400">Click card to open dedicated workspace</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {disciplineCards.map((disc) => {
            const Icon = disc.icon;
            return (
              <div
                key={disc.id}
                onClick={() => onNavigate?.(disc.id)}
                className="card p-5 hover:border-pine hover:shadow-md transition-all cursor-pointer space-y-3 flex flex-col justify-between group"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${disc.color}`} />
                      <span className="font-semibold text-ink text-sm">{disc.shortName}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`font-mono text-sm font-bold ${scoreTone(disc.score || 70)}`}>
                        {disc.score != null ? Math.round(disc.score) : '—'}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-paper-200 text-ink-600">
                        {disc.grade}
                      </span>
                    </div>
                  </div>
                  <h3 className="font-serif text-base font-semibold text-ink group-hover:text-pine transition-colors">
                    {disc.name}
                  </h3>
                  <p className="text-xs text-ink-500 line-clamp-2 leading-relaxed">
                    {disc.summary}
                  </p>
                </div>

                <div className="pt-2 border-t border-line/60 flex items-center justify-between text-xs">
                  <span className="font-mono text-ink-400 text-[11px]">
                    {disc.issuesCount} findings logged
                  </span>
                  <span className="text-pine font-medium flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                    Inspect <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. IDENTITY CONFLICTS (If Any)
          ───────────────────────────────────────────────────────────── */}
      {activeContradictions.length > 0 && (
        <Card className="border-l-4 border-warn rounded-l-none">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <p className="label text-warn flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" /> Identity & Categorization Conflict
            </p>
            <span className="text-xs text-ink-500">
              {activeContradictions[0].confidence != null
                ? `${Math.round(activeContradictions[0].confidence * 100)}% confidence`
                : 'Calibrating'}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs mb-2">
            <Field label="Declared Site Type" value={activeContradictions[0].declared_type || 'Unspecified'} />
            <Field label="Detected DOM Signals" value={display(activeContradictions[0].detected_type)} />
          </div>
          <p className="text-xs text-ink-700 leading-relaxed">
            {formatContradictionText(activeContradictions[0].reason)}
          </p>
        </Card>
      )}

      {/* ─────────────────────────────────────────────────────────────
          4. EXECUTIVE STORY & PRIMARY OPPORTUNITY
          ───────────────────────────────────────────────────────────── */}
      <Section title="Executive Summary & Opportunity">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2 space-y-2 p-5">
            <p className="label text-ink-500">Executive Narrative</p>
            <p className="text-sm text-ink-700 leading-relaxed font-serif text-[15px]">
              {display(story)}
            </p>
            <CalibrationLeaders findings={report?.findings || []} />
          </Card>
          <Card className="space-y-2 p-5 bg-pine/5 border-pine/20">
            <p className="label text-pine flex items-center gap-1">
              <Lightbulb className="w-3.5 h-3.5" /> Primary Strategic Opportunity
            </p>
            <p className="text-xs text-ink-800 leading-relaxed font-medium">
              {display(opportunity)}
            </p>
          </Card>
        </div>
      </Section>

      {/* ─────────────────────────────────────────────────────────────
          5. STRATEGIC SIGNALS: WORKING VS BLOCKERS VS WHAT TO IGNORE
          ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5 space-y-3">
          <div className="flex items-center gap-1.5 text-good">
            <CheckCircle2 className="w-4 h-4" />
            <h4 className="label text-good">What Site Gets Right</h4>
          </div>
          {strengths.length === 0 ? (
            <p className="text-xs text-ink-400">—</p>
          ) : (
            <ul className="space-y-2 text-xs text-ink-700 list-disc pl-4">
              {strengths.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5 space-y-3">
          <div className="flex items-center gap-1.5 text-warn">
            <AlertTriangle className="w-4 h-4" />
            <h4 className="label text-warn">What Is Holding It Back</h4>
          </div>
          {blockers.length === 0 ? (
            <p className="text-xs text-ink-400">—</p>
          ) : (
            <ul className="space-y-2 text-xs text-ink-700 list-disc pl-4">
              {blockers.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5 space-y-3">
          <div className="flex items-center gap-1.5 text-ink-500">
            <FileCheck className="w-4 h-4" />
            <h4 className="label text-ink-500">What to Ignore (Low ROI)</h4>
          </div>
          <p className="text-xs text-ink-600 leading-relaxed">
            {display(ignore)}
          </p>
        </Card>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          6. BUSINESS PROFILE & SEMANTIC GROUNDING
          ───────────────────────────────────────────────────────────── */}
      <Section title="Business Profile & Positioning">
        <Card className="p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <Field label="Business Name" value={profile.business_name || report?.domain || '—'} />
            <Field label="Industry / Niche" value={`${profile.industry || 'General'} · ${profile.niche || 'Web'}`} />
            <Field label="Target Audience" value={profile.target_audience || 'General Commercial'} />
            <Field label="Business Model" value={profile.business_model || 'Enterprise / B2B'} />
          </div>

          <div className="pt-3 border-t border-line text-xs grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="label mb-1">5-Second Value Proposition</p>
              <p className="text-ink-700 italic">&quot;{profile.value_proposition || 'Not explicitly extracted'}&quot;</p>
            </div>
            <div>
              <p className="label mb-1">Primary Call to Action (CTA)</p>
              <p className="text-good font-mono font-bold">&quot;{profile.primary_cta || 'Not extracted'}&quot;</p>
            </div>
          </div>
        </Card>
      </Section>

      {/* ─────────────────────────────────────────────────────────────
          7. TOP 10 EXECUTIVE PRIORITY ACTIONS
          ───────────────────────────────────────────────────────────── */}
      {report && (
        <Section title="Priority Remediation Plan">
          <ExecutiveTopActions
            report={report}
          />
        </Section>
      )}
    </div>
  );
}
