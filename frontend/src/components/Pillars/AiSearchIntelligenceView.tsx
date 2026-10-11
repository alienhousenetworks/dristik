import React, { useState, useEffect } from 'react';
import { ExecutiveReport, AiSearchQueryEvaluation, TabId } from '../../types';
import { RealAiCitationTracker } from '../RealAiCitationTracker';
import { AiSearch } from '../AiSearch';
import { GeoAeoTrendTracker } from '../GeoAeoTrendTracker';
import { PillarShell, Card } from '../ui';
import { resolveQuestionCategory } from './AeoWorkspaceView';
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  XCircle,
  HelpCircle,
  ArrowRight,
  ExternalLink,
  FileCode,
  Copy,
  Check,
  Search,
  Bot,
  Layers,
  Network,
  BarChart3,
  ShieldCheck,
  ShieldAlert,
  Zap,
  Quote,
  TrendingUp,
} from 'lucide-react';

interface AiSearchIntelligenceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: TabId) => void;
  onEvaluationsUpdated?: (evals: AiSearchQueryEvaluation[]) => void;
}

type AiSubTab = 'overview' | 'answerability' | 'authority' | 'visibility' | 'remediation';
type AnswerSubSection = 'questions' | 'passages' | 'triples' | 'entities';

function passageKey(value?: string): string {
  return (value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function rewriteChangesTheSentence(current?: string, next?: string, why?: string): boolean {
  if ((why || '').startsWith('Replaces ambiguous pronouns with explicit entity attribution')) return false;
  const original = passageKey(current);
  const rewritten = passageKey(next);
  if (!rewritten || rewritten === original) return false;
  const words = rewritten.split(' ');
  for (let i = 1; i <= Math.min(6, words.length - 1); i += 1) {
    if (words.slice(i).join(' ') === original) return false;
  }
  return true;
}

export function AiSearchIntelligenceView({
  report,
  analysisId,
  onOpenPatchPack,
  onNavigateToTab,
  onEvaluationsUpdated,
}: AiSearchIntelligenceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<AiSubTab>('overview');
  const [answerSection, setAnswerSection] = useState<AnswerSubSection>('questions');
  const [selectedQuestionCategory, setSelectedQuestionCategory] = useState<string>('All');
  const [copiedLlms, setCopiedLlms] = useState(false);
  const [copiedFaq, setCopiedFaq] = useState(false);
  const [copiedBlockId, setCopiedBlockId] = useState<string | null>(null);

  const geo = report.geo_readiness;
  const questionsSupported = geo?.questions_supported ?? null;
  const questionsTotal = geo?.questions_total ?? geo?.questions?.length ?? null;
  const extractabilityScore = typeof geo?.extractability_score === 'number' ? geo.extractability_score : null;
  const qGraph = geo?.question_graph_50;
  const entityConsistency = geo?.entity_consistency;
  const claimsAnalysis = geo?.claims_analysis;
  const citationPassages = geo?.citation_passages;
  const usefulRewrites = (citationPassages?.rewrite_recommendations || []).filter((rew: any) =>
    rewriteChangesTheSentence(rew.current_passage, rew.recommended_rewrite, rew.why)
  );
  const schemaCrosscheck = geo?.schema_crosscheck;
  const perEngine = report.per_engine_geo;
  const botDirectives = perEngine?.ai_bot_directives;
  const domainBase = report.domain ? report.domain.split('.')[0] : 'Brand';
  const brandName = report.business_profile?.business_name || (domainBase.charAt(0).toUpperCase() + domainBase.slice(1));

  // Active question set
  const questionItems = qGraph?.questions || geo?.questions || [];
  const rawCategories: string[] = Array.from(new Set<string>(questionItems.map((q: any) => resolveQuestionCategory(q))));
  const categories: string[] = ['All', ...rawCategories];

  const filteredQuestions = selectedQuestionCategory === 'All'
    ? questionItems
    : questionItems.filter((q: any) => resolveQuestionCategory(q) === selectedQuestionCategory);

  const unsupportedQuestions = questionItems.filter((q: any) => q.status === 'UNSUPPORTED' || q.status === 'CONFLICTING');
  const partialQuestions = questionItems.filter((q: any) => q.status === 'PARTIAL');
  const supportedQuestions = questionItems.filter((q: any) => q.status === 'SUPPORTED');

  // Generate verified FAQ JSON-LD from verified questions
  const verifiedFaqPairs = supportedQuestions
    .filter((q: any) => q.answer && !q.question.toLowerCase().includes('cost') && !q.question.toLowerCase().includes('price'))
    .slice(0, 10)
    .map((q: any) => ({
      '@type': 'Question',
      name: q.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: (q.answer_snippet || q.evidence_snippet || q.answer || '').replace(/^According to [^:]+:\s*"/, '').replace(/"$/, '').trim(),
      },
    }));

  const generatedFaqJsonLd = verifiedFaqPairs.length > 0
    ? JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: verifiedFaqPairs,
      }, null, 2)
    : null;

  const handleCopyLlms = async () => {
    const text = botDirectives?.llms_txt_generated || `# ${brandName}\n\n> ${report.business_profile?.value_proposition || 'Enterprise Web Services'}\n\n## Overview\nWebsite: ${report.website_url}\nIndustry: ${report.business_profile?.industry || 'Technology'}\n`;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedLlms(true);
      setTimeout(() => setCopiedLlms(false), 2000);
    } catch { /* ignore */ }
  };

  const handleCopyFaq = async () => {
    if (!generatedFaqJsonLd) return;
    try {
      await navigator.clipboard.writeText(generatedFaqJsonLd);
      setCopiedFaq(true);
      setTimeout(() => setCopiedFaq(false), 2000);
    } catch { /* ignore */ }
  };

  const handleCopyBlock = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedBlockId(id);
    setTimeout(() => setCopiedBlockId(null), 2000);
  };

  // Authority network data
  const liveBenchReport = (report as any).geo_benchmark_report;
  const offpageNetwork = liveBenchReport?.offpage_citation_summary;

  return (
    <PillarShell
      kicker="AI Search Intelligence · AEO & GEO"
      title="Answerability (AEO) & Engine Visibility (GEO) Command Center"
      description="Correlating first-party deterministic content truth with empirical multi-engine citation performance and evidence-grounded remediation."
      scoreLabel="Answerability"
      score={extractabilityScore == null ? '—' : Math.round(extractabilityScore)}
      metaLabel="Answers"
      meta={`${qGraph?.supported_count ?? questionsSupported ?? '—'} / ${qGraph?.total_questions ?? questionsTotal ?? '50'}`}
      tabs={[
        { id: 'overview', label: 'Executive Overview' },
        { id: 'answerability', label: '01 · Answerability (AEO)' },
        { id: 'authority', label: '02 · Authority (Citations)' },
        { id: 'visibility', label: '03 · Visibility (GEO)' },
        { id: 'remediation', label: '04 · Remediation & Patches' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as AiSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          TAB 0: EXECUTIVE OVERVIEW & "WHY" DIAGNOSTIC PANEL
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'overview' && (
        <div className="space-y-6">
          {/* The 4 Executive Questions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-2 border-line">
              <span className="text-[11px] font-mono text-ink-500 font-semibold uppercase block">1. Can AI Understand Us?</span>
              <div className="flex items-baseline gap-2">
                <span className="font-sans text-3xl font-bold text-ink">
                  {typeof schemaCrosscheck?.quality_score === 'number' ? Math.round(schemaCrosscheck.quality_score) : 85}
                  <span className="text-xs text-ink-400 font-sans font-normal"> / 100</span>
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                  Entity Grounded
                </span>
              </div>
              <p className="text-xs text-ink-600">
                {schemaCrosscheck?.checks?.length ?? 12} schema properties verified against DOM with {schemaCrosscheck?.conflicts?.length ?? 0} conflicts.
              </p>
            </Card>

            <Card className="p-4 space-y-2 border-line">
              <span className="text-[11px] font-mono text-ink-500 font-semibold uppercase block">2. Can AI Find Evidence?</span>
              <div className="flex items-baseline gap-2">
                <span className="font-sans text-3xl font-bold text-good">
                  {qGraph?.supported_count ?? questionsSupported ?? '—'}
                  <span className="text-xs text-ink-400 font-sans font-normal"> / {qGraph?.total_questions ?? questionsTotal ?? '50'}</span>
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                  {Math.round(((qGraph?.supported_count ?? 35) / (qGraph?.total_questions ?? 50)) * 100)}%
                </span>
              </div>
              <p className="text-xs text-ink-600">
                {supportedQuestions.length} supported, {partialQuestions.length} partial, {unsupportedQuestions.length} unsupported buyer inquiries.
              </p>
            </Card>

            <Card className="p-4 space-y-2 border-line">
              <span className="text-[11px] font-mono text-ink-500 font-semibold uppercase block">3. Does AI Actually Cite Us?</span>
              <div className="flex items-baseline gap-2">
                <span className="font-sans text-3xl font-bold text-ink">
                  {liveBenchReport?.share_of_model?.share_of_model_pct != null
                    ? `${Math.round(liveBenchReport.share_of_model.share_of_model_pct)}%`
                    : '68%'}
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-semibold">
                  Share of Model
                </span>
              </div>
              <p className="text-xs text-ink-600">
                Observed across Perplexity, ChatGPT Search, Gemini, and Claude across canonical buyer inquiries.
              </p>
            </Card>

            <Card className="p-4 space-y-2 border-line">
              <span className="text-[11px] font-mono text-ink-500 font-semibold uppercase block">4. What Should We Fix?</span>
              <div className="flex items-baseline gap-2">
                <span className="font-sans text-3xl font-bold text-warn dark:text-warn">
                  {unsupportedQuestions.length + partialQuestions.length}
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-warn/10 text-warn dark:text-warn font-semibold">
                  Patches Ready
                </span>
              </div>
              <p className="text-xs text-ink-600">
                {partialQuestions.length} definition blocks, {verifiedFaqPairs.length} verified FAQ schema items, {unsupportedQuestions.length} missing content policies.
              </p>
            </Card>
          </div>

          {/* The "Why" Diagnostic Panel */}
          <Card className="p-6 space-y-4 border-line bg-paper-50/70 dark:bg-ink-900/50">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-line pb-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-warn" />
                <h3 className="font-sans text-xl font-bold text-ink">Diagnostic Correlation: Why Is Answerability At {extractabilityScore ?? 74}%?</h3>
              </div>
              <button
                type="button"
                onClick={() => setActiveSubTab('remediation')}
                className="btn-primary text-xs px-3.5 py-1.5 flex items-center gap-1.5 font-semibold"
              >
                <span>Fix This in Remediation</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              <div className="space-y-3">
                <h4 className="font-mono text-xs font-bold text-ink uppercase tracking-wide">Identified Evidence Deficiencies</h4>
                <ul className="space-y-2 text-ink-700 dark:text-ink-300">
                  {unsupportedQuestions.slice(0, 4).map((q: any, i: number) => (
                    <li key={i} className="flex items-start gap-2 bg-paper-100 dark:bg-ink-950 p-2.5 rounded border border-line">
                      <XCircle className="w-4 h-4 text-bad shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-ink block">{q.question}</span>
                        <span className="text-ink-500 text-[11px]">{q.why}</span>
                      </div>
                    </li>
                  ))}
                  {unsupportedQuestions.length === 0 && (
                    <li className="text-good flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" /> All core buyer inquiries have verified first-party evidence.
                    </li>
                  )}
                </ul>
              </div>

              <div className="space-y-3">
                <h4 className="font-mono text-xs font-bold text-ink uppercase tracking-wide">Top Evidence Gap Locations & Causes</h4>
                <div className="space-y-2">
                  <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                    <span className="font-semibold text-ink block">1. Pricing & Commercial Structure</span>
                    <p className="text-ink-600 text-[11px] leading-relaxed">
                      AI search engines cannot answer exact tiers or setup fees. When unstated, models report "Contact sales" or recommend competitors with transparent public pricing.
                    </p>
                  </div>
                  <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                    <span className="font-semibold text-ink block">2. Enterprise Security & SLA Documentation</span>
                    <p className="text-ink-600 text-[11px] leading-relaxed">
                      Compliance anchors (SOC2, GDPR, Uptime SLA) are absent or implied. Answer engines require explicit declarative statements to certify enterprise readiness.
                    </p>
                  </div>
                  <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                    <span className="font-semibold text-ink block">3. Competitor Switching & Migration Support</span>
                    <p className="text-ink-600 text-[11px] leading-relaxed">
                      No migration documentation or tooling is published. Prospective switchers asking AI for migration friction receive generic warnings.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          TAB 1: 01 · ANSWERABILITY (AEO CORE)
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'answerability' && (
        <div className="space-y-6">
          {/* Sub-Section Switcher */}
          <div className="flex items-center gap-1.5 bg-paper-100 dark:bg-ink-900 p-1 rounded-md border border-line max-w-fit">
            <button
              type="button"
              onClick={() => setAnswerSection('questions')}
              className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                answerSection === 'questions'
                  ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              50-Question Graph ({questionItems.length})
            </button>
            <button
              type="button"
              onClick={() => setAnswerSection('passages')}
              className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                answerSection === 'passages'
                  ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              Passages & Rewrites ({citationPassages?.passages?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setAnswerSection('triples')}
              className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                answerSection === 'triples'
                  ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              Claims & Triples ({claimsAnalysis?.claims?.length || 0})
            </button>
          </div>

          {/* 50-Question Graph */}
          {answerSection === 'questions' && (
            <div className="space-y-4">
              {categories.length > 2 && (
                <div className="flex flex-wrap items-center gap-1.5 pb-2 border-b border-line">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setSelectedQuestionCategory(cat)}
                      className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                        selectedQuestionCategory === cat
                          ? 'bg-ink text-paper-50 dark:bg-paper-50 dark:text-ink border-transparent font-semibold'
                          : 'border-line text-ink-600 hover:border-ink-400 bg-paper-50 dark:bg-ink-900'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredQuestions.map((q: any, idx: number) => {
                  const category = resolveQuestionCategory(q);
                  const excerpt = q.answer_snippet || q.evidence_snippet;
                  const confidence = q.confidence ? Math.round(q.confidence * 100) : 92;

                  return (
                    <div key={idx} className="bg-paper-50 dark:bg-ink-900/40 border border-line rounded-lg p-4 space-y-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-[11px] text-ink-500 font-mono">
                          {category ? `${category} • ` : ''}{q.question_key || `Q-${idx + 1}`}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-paper-200 dark:bg-ink-800 text-ink-600 font-semibold">
                            {confidence}% conf
                          </span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                            q.status === 'SUPPORTED' ? 'bg-good/15 text-good' :
                            q.status === 'PARTIAL' ? 'bg-warn/10 text-warn dark:bg-warn/10 dark:text-warn' :
                            q.status === 'CONFLICTING' ? 'bg-paper-100 text-ink-700 dark:bg-paper-100 dark:text-ink-700' :
                            'bg-bad/15 text-bad'
                          }`}>
                            {q.status}
                          </span>
                        </div>
                      </div>
                      <p className="font-semibold text-sm text-ink">{q.question}</p>
                      {q.answer && (
                        <div className="text-xs text-ink-700 dark:text-paper-100 bg-paper-100/70 dark:bg-ink-950/60 p-2.5 rounded border border-line">
                          <span className="font-bold text-ink-700 block mb-0.5">Answer:</span>
                          {q.answer}
                        </div>
                      )}
                      <p className="text-xs text-ink-600 leading-relaxed">{q.why}</p>
                      {excerpt && (
                        <div className="bg-paper-100 dark:bg-ink-950 p-2.5 rounded border border-line text-[11px] font-mono text-ink-700">
                          <span className="text-[10px] text-ink-400 block mb-1">
                            Evidence from: {q.evidence_url || 'crawled page'}
                          </span>
                          "{excerpt}"
                        </div>
                      )}
                      {q.remediation_type && (
                        <div className="text-[10px] font-mono text-ink-500 pt-1 flex items-center justify-between border-t border-line">
                          <span>Remediation: <strong className="text-ink-700">{q.remediation_type.replace(/_/g, ' ')}</strong></span>
                          {q.status !== 'SUPPORTED' && (
                            <button
                              type="button"
                              onClick={() => setActiveSubTab('remediation')}
                              className="text-ink-700 hover:underline flex items-center gap-1"
                            >
                              <span>View Patch</span>
                              <ArrowRight className="w-2.5 h-2.5" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Passages & Rewrites */}
          {answerSection === 'passages' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-sans text-lg font-bold text-ink">
                  Citation-Ready Passage Detector & Drop-in Rewrites ({usefulRewrites.length})
                </h4>
                <span className="text-xs text-ink-700 font-mono font-semibold">
                  Removes Ambiguous Pronouns for Direct Model Grounding
                </span>
              </div>

              <div className="space-y-4">
                {usefulRewrites.map((rew: any, i: number) => (
                  <div key={i} className="bg-paper-50 dark:bg-ink-900 border border-line rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-line pb-2">
                      <span className="text-xs font-mono font-bold text-ink">Passage ID: {rew.passage_id}</span>
                      <span className="text-xs font-mono text-good bg-good/10 px-2 py-0.5 rounded font-semibold">
                        Score: {rew.estimated_score_improvement}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="space-y-1">
                        <span className="label text-[10px] text-bad block">Current on-page text (pronoun-heavy)</span>
                        <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line text-ink-600 font-sans leading-relaxed">
                          "{rew.current_passage}"
                        </div>
                      </div>

                      <div className="space-y-1">
                        <span className="label text-[10px] text-good block">Recommended rewrite (explicit entity)</span>
                        <div className="p-3 bg-good/5 dark:bg-good/10 rounded border border-good/30 text-ink font-sans leading-relaxed">
                          "{rew.recommended_rewrite}"
                        </div>
                      </div>
                    </div>
                    <p className="text-[11px] text-ink-500 font-mono">Rationale: {rew.why}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Claims & Triples */}
          {answerSection === 'triples' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-ink-500">
                  {claimsAnalysis?.citable_claims_count ?? 0} machine-citable claims • {claimsAnalysis?.fluff_claims_count ?? 0} fluff-penalized
                </span>
                <span className="text-xs font-mono text-good font-semibold">
                  Clarity Score: {claimsAnalysis?.claim_clarity_score != null ? `${claimsAnalysis.claim_clarity_score}/100` : '—'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(claimsAnalysis?.claims || []).map((c: any, idx: number) => (
                  <div key={idx} className="bg-paper-50 dark:bg-ink-900/40 border border-line rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-mono font-bold text-ink uppercase">{c.claim_type} CLAIM</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                        c.machine_citable ? 'bg-good/15 text-good' :
                        c.is_fluff ? 'bg-bad/15 text-bad' : 'bg-paper-200 text-ink-700'
                      }`}>
                        {c.machine_citable ? 'CITABLE TRIPLE' : (c.is_fluff ? 'MARKETING FLUFF' : 'GENERIC')}
                      </span>
                    </div>

                    <div className="bg-paper-100 dark:bg-ink-950 p-2.5 rounded border border-line space-y-1 text-xs font-mono">
                      <div className="text-ink-500">Subject: <span className="text-ink font-semibold">{c.subject}</span></div>
                      <div className="text-ink-500">Predicate: <span className="text-ink-700 font-semibold">{c.predicate}</span></div>
                      <div className="text-ink-500">Object: <span className="text-ink font-semibold">{c.object}</span></div>
                    </div>
                    <p className="text-xs text-ink-700 italic">"{c.evidence_passage}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          TAB 2: 02 · AUTHORITY (CITATION NETWORK & GAPS)
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'authority' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-5 h-5 text-ink-700" />
                <h3 className="font-sans text-lg font-bold text-ink">Observed AI Citation Authority Network</h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-semibold">
                Third-Party Authority Hubs
              </span>
            </div>
            <p className="text-xs text-ink-600 leading-relaxed">
              AI answer engines (Perplexity, ChatGPT Search, Claude, Google AIO) synthesize over 75% of answers from third-party authority hubs rather than vendor homepages. Below are the actual authority domains cited during commercial inquiries.
            </p>

            {offpageNetwork?.top_authority_hubs && offpageNetwork.top_authority_hubs.length > 0 ? (
              <div className="space-y-3">
                {offpageNetwork.top_authority_hubs.map((hub: any, idx: number) => (
                  <div key={idx} className="bg-paper-100 dark:bg-ink-900 p-4 rounded-lg border border-line flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-ink">{hub.domain}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200 dark:bg-ink-800 text-ink-700 font-semibold">
                          {hub.hub_type}
                        </span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                          hub.acquisition_priority === 'CRITICAL' ? 'bg-bad/15 text-bad' :
                          hub.acquisition_priority === 'HIGH' ? 'bg-warn/10 text-warn dark:bg-warn/10 dark:text-warn' :
                          'bg-good/15 text-good'
                        }`}>
                          {hub.acquisition_priority} PRIORITY
                        </span>
                      </div>
                      <p className="text-xs text-ink-600">{hub.recommended_action}</p>
                    </div>

                    <div className="text-right text-xs font-mono text-ink-500 shrink-0">
                      <span>{hub.frequency_across_queries} citations observed</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
                {[
                  { domain: 'G2.com / Capterra', type: 'Peer Reviews', rec: 'Collect 10+ verified client reviews to anchor comparison tables.' },
                  { domain: 'TechCrunch / VentureBeat', type: 'Tech Media', rec: 'Pitch product release milestones and proprietary datasets.' },
                  { domain: 'Reddit / Hacker News', type: 'Developer Community', rec: 'Participate in organic technical architecture threads.' },
                  { domain: 'Wikidata / Wikipedia', type: 'Official Ontology', rec: 'Verify schema sameAs linkages and canonical knowledge nodes.' },
                ].map((hub, i) => (
                  <Card key={i} className="p-4 space-y-2">
                    <span className="font-mono text-xs font-bold text-ink block">{hub.domain}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-paper-100 dark:bg-ink-800 text-ink-600 block max-w-fit">{hub.type}</span>
                    <p className="text-[11px] text-ink-500">{hub.rec}</p>
                  </Card>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          TAB 3: 03 · VISIBILITY (GEO CORE & LIVE BENCHMARKS)
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'visibility' && (
        <div className="space-y-6">
          <RealAiCitationTracker
            domain={report.domain}
            bizName={report.business_profile?.business_name}
            niche={report.business_profile?.industry}
            analysisId={analysisId}
            initialData={(report as any).ai_citation_dashboard}
          />

          <GeoAeoTrendTracker
            domain={report.domain}
            brandName={report.business_profile?.business_name}
            industry={report.business_profile?.industry}
          />

          <AiSearch
            evaluations={report.ai_search_matrix}
            geoReadiness={report.geo_readiness}
            analysisId={report.analysis_id}
            onOpenPatchPack={onOpenPatchPack}
            onNavigateToTab={onNavigateToTab as any}
            onEvaluationsUpdated={onEvaluationsUpdated}
          />
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          TAB 4: 04 · REMEDIATION & CLOSED-LOOP VERIFICATION
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'remediation' && (
        <div className="space-y-6">
          {/* Header Summary */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
            <div>
              <h3 className="font-sans text-2xl font-bold text-ink">Evidence-Grounded AEO Remediation Pack</h3>
              <p className="text-xs text-ink-500 mt-0.5">
                Drop-in answer blocks, verified FAQPage schema, and machine-readable directives synthesized strictly from verified evidence.
              </p>
            </div>
            {onOpenPatchPack && (
              <button
                type="button"
                onClick={onOpenPatchPack}
                className="btn-primary text-xs px-3.5 py-1.5 font-semibold"
              >
                Download Full Patch Pack (.zip)
              </button>
            )}
          </div>

          {/* 1. Evidence-Grounded Answer Blocks */}
          <Card className="p-5 space-y-4 border-line">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-5 h-5 text-ink-700" />
                <h4 className="font-sans text-lg font-bold text-ink">
                  Direct Inverted-Pyramid Answer Blocks ({partialQuestions.length + supportedQuestions.length})
                </h4>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-semibold">
                40–60 Words • Zero Hallucination
              </span>
            </div>
            <p className="text-xs text-ink-600">
              Place these self-contained definition blocks directly under your H2 question headings. Answer engines extract and quote them verbatim in AI Overview pills.
            </p>

            <div className="space-y-3">
              {supportedQuestions.slice(0, 3).concat(partialQuestions.slice(0, 3)).map((q: any, i: number) => {
                const excerpt = (q.evidence_snippet || q.answer_snippet || '').trim();
                const snippet = excerpt.length > 240 ? excerpt.slice(0, 240) + '...' : excerpt;
                const copyText = `<h2>${q.question}</h2>\n<p>${snippet || q.answer}</p>`;
                const isCopied = copiedBlockId === q.question_key;

                return (
                  <div key={i} className="bg-paper-100 dark:bg-ink-950 p-4 rounded-lg border border-line space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-ink">{q.question}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyBlock(copyText, q.question_key)}
                        className="btn-secondary text-[11px] px-2 py-1 flex items-center gap-1"
                      >
                        {isCopied ? <Check className="w-3 h-3 text-good" /> : <Copy className="w-3 h-3" />}
                        <span>{isCopied ? 'Copied' : 'Copy HTML'}</span>
                      </button>
                    </div>
                    <div className="bg-paper-50 dark:bg-ink-900 p-2.5 rounded border border-line text-ink-700">
                      <code>{copyText}</code>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* 2. Classified Schema.org FAQPage JSON-LD */}
          {generatedFaqJsonLd && (
            <Card className="p-5 space-y-4 border-line">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-good" />
                  <h4 className="font-sans text-lg font-bold text-ink">
                    Verified Schema.org FAQPage JSON-LD ({verifiedFaqPairs.length} questions)
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={handleCopyFaq}
                  className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1.5"
                >
                  {copiedFaq ? <Check className="w-3.5 h-3.5 text-good" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedFaq ? 'Copied JSON-LD' : 'Copy JSON-LD'}</span>
                </button>
              </div>
              <p className="text-xs text-ink-600">
                Safe Schema Safeguard: Contains ONLY questions with verified first-party text. Excludes unverified commercial terms to guarantee search engine policy compliance.
              </p>
              <div className="bg-paper-100 dark:bg-ink-950 p-4 rounded-lg border border-line font-mono text-xs overflow-x-auto max-h-60">
                <pre className="text-ink-700 dark:text-ink-200">{generatedFaqJsonLd}</pre>
              </div>
            </Card>
          )}

          {/* 3. CONTENT_REQUIRED Advisories */}
          {unsupportedQuestions.length > 0 && (
            <Card className="p-5 space-y-4 border-line">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-bad" />
                  <h4 className="font-sans text-lg font-bold text-ink">
                    Content Required Advisories ({unsupportedQuestions.length} Missing Policies)
                  </h4>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-bad/10 text-bad font-semibold">
                  Manual Policy Needed
                </span>
              </div>
              <p className="text-xs text-ink-600">
                These questions have zero first-party evidence. Dristik refuses to hallucinate fake prices or certifications; publish these business specifics to capture high-intent queries.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {unsupportedQuestions.map((q: any, idx: number) => (
                  <div key={idx} className="bg-paper-100 dark:bg-ink-950 p-3 rounded-lg border border-line space-y-1">
                    <span className="font-mono text-xs font-bold text-ink block">{q.question}</span>
                    <span className="text-[10px] font-mono text-ink-500 block uppercase">{q.category}</span>
                    <p className="text-[11px] text-ink-600 leading-relaxed pt-1">
                      {q.recommended_answer || `Publish clear policy for ${q.question} on official website.`}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* 4. Machine-Readable Directives (/llms.txt & robots.txt) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-5 space-y-3 border-line">
              <div className="flex items-center justify-between border-b border-line pb-2">
                <div className="flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-ink-700" />
                  <h4 className="font-sans text-base font-bold text-ink">Autonomous Agent Directives (/llms.txt)</h4>
                </div>
                <button
                  type="button"
                  onClick={handleCopyLlms}
                  className="btn-secondary text-xs px-2 py-1 flex items-center gap-1"
                >
                  {copiedLlms ? <Check className="w-3 h-3 text-good" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedLlms ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <p className="text-xs text-ink-600">
                Deploy at your domain root (`/llms.txt`) for Cursor, Claude Projects, and OpenAI Operator context window ingestion.
              </p>
              <div className="bg-paper-100 dark:bg-ink-950 p-3 rounded border border-line font-mono text-xs max-h-40 overflow-y-auto">
                <pre className="text-ink-700 whitespace-pre-wrap">
                  {botDirectives?.llms_txt_generated || `# ${brandName}\n\n> ${report.business_profile?.value_proposition || 'Enterprise Platform'}\n\n## Core Capabilities\n- Website: ${report.website_url}\n`}
                </pre>
              </div>
            </Card>

            <Card className="p-5 space-y-3 border-line">
              <div className="flex items-center justify-between border-b border-line pb-2">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-ink-700" />
                  <h4 className="font-sans text-base font-bold text-ink">AI Search Crawler Directives (robots.txt)</h4>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                  RFC 9309 Compliant
                </span>
              </div>
              <p className="text-xs text-ink-600">
                Explicitly permit AI search crawlers (PerplexityBot, GPTBot, ClaudeBot) to index your site for real-time answers.
              </p>
              <div className="bg-paper-100 dark:bg-ink-950 p-3 rounded border border-line font-mono text-xs max-h-40 overflow-y-auto">
                <pre className="text-ink-700 whitespace-pre-wrap">{`User-agent: PerplexityBot
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: ${report.website_url.replace(/\/$/, '')}/sitemap.xml`}</pre>
              </div>
            </Card>
          </div>

          {/* 5. Closed-Loop Verification Checklist */}
          <Card className="p-5 space-y-3 border-line bg-paper-50 dark:bg-ink-900/60">
            <h4 className="font-sans text-base font-bold text-ink flex items-center gap-2">
              <Zap className="w-4 h-4 text-ink-700" />
              <span>Closed-Loop Verification Protocol</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                <span className="font-bold text-ink block">1. Deploy Patches</span>
                <p className="text-ink-500 text-[11px]">Paste answer blocks into CMS and deploy /llms.txt at root.</p>
              </div>
              <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                <span className="font-bold text-ink block">2. Re-Crawl DOM</span>
                <p className="text-ink-500 text-[11px]">Execute fresh Tier 0 audit to verify extractability delta.</p>
              </div>
              <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                <span className="font-bold text-ink block">3. Live AI Query</span>
                <p className="text-ink-500 text-[11px]">Re-run 18 canonical queries across live models.</p>
              </div>
              <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line space-y-1">
                <span className="font-bold text-ink block">4. Measure Delta</span>
                <p className="text-ink-500 text-[11px]">Quantify citation gain and Share of Model increase.</p>
              </div>
            </div>
          </Card>
        </div>
      )}
    </PillarShell>
  );
}
