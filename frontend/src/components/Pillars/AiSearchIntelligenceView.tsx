import React, { useState } from 'react';
import { ExecutiveReport, AiSearchQueryEvaluation, TabId } from '../../types';
import { RealAiCitationTracker } from '../RealAiCitationTracker';
import { AiSearch } from '../AiSearch';
import { GeoAeoTrendTracker } from '../GeoAeoTrendTracker';
import { PillarShell } from '../ui';
import { resolveQuestionCategory } from './AeoWorkspaceView';

interface AiSearchIntelligenceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: TabId) => void;
  onEvaluationsUpdated?: (evals: AiSearchQueryEvaluation[]) => void;
}

type AiSubTab = 'citations' | 'trends' | 'matrix' | 'extracts' | 'entities';
type ExtractSubSection = 'questions' | 'passages' | 'triples';
type EntitySubSection = 'surfaces' | 'schema';

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
  const [activeSubTab, setActiveSubTab] = useState<AiSubTab>('citations');
  const [extractSection, setExtractSection] = useState<ExtractSubSection>('questions');
  const [selectedQuestionCategory, setSelectedQuestionCategory] = useState<string>('All');
  const [entitySection, setEntitySection] = useState<EntitySubSection>('surfaces');

  const geo = report.geo_readiness;
  const questionsSupported = geo?.questions_supported ?? null;
  const questionsTotal = geo?.questions_total ?? geo?.questions?.length ?? null;
  const extractabilityScore = typeof geo?.extractability_score === 'number' ? geo.extractability_score : null;
  const qGraph = geo?.question_graph_50;
  const entityConsistency = geo?.entity_consistency;
  const claimsAnalysis = geo?.claims_analysis;
  const citationPassages = geo?.citation_passages;
  const usefulRewrites = (citationPassages?.rewrite_recommendations || []).filter((rew: { current_passage?: string; recommended_rewrite?: string; why?: string }) =>
    rewriteChangesTheSentence(rew.current_passage, rew.recommended_rewrite, rew.why)
  );
  const schemaCrosscheck = geo?.schema_crosscheck;

  // Active question set (prefers 50-question graph if present)
  const questionItems = qGraph?.questions || geo?.questions || [];
  const rawCategories: string[] = Array.from(new Set<string>(questionItems.map((q: any) => resolveQuestionCategory(q))));
  const categories: string[] = ['All', ...rawCategories];

  const filteredQuestions = selectedQuestionCategory === 'All'
    ? questionItems
    : questionItems.filter((q: any) => resolveQuestionCategory(q) === selectedQuestionCategory);

  return (
    <PillarShell
      kicker="AI search & GEO"
      title="Layer 1 AI Extractability & Live Citation Benchmark"
      description="Deterministic on-page machine extractability cross-referenced against live answer engine citations."
      scoreLabel="Extractability"
      score={extractabilityScore == null ? '—' : Math.round(extractabilityScore)}
      metaLabel="Answers"
      meta={`${qGraph?.supported_count ?? questionsSupported ?? '—'} / ${qGraph?.total_questions ?? questionsTotal ?? '—'}`}
      tabs={[
        { id: 'citations', label: 'Live Citations' },
        { id: 'extracts', label: 'AI Extractability' },
        { id: 'entities', label: 'Entity & Schema Grounding' },
        { id: 'matrix', label: 'Query Matrix' },
        { id: 'trends', label: 'Trend History' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as AiSubTab)}
    >

      {/* SUB-VIEW 1: LIVE MULTI-ENGINE CITATIONS */}
      {activeSubTab === 'citations' && (
        <RealAiCitationTracker
          domain={report.domain}
          bizName={report.business_profile?.business_name}
          niche={report.business_profile?.industry}
          analysisId={analysisId}
        />
      )}

      {/* SUB-VIEW: LONGITUDINAL TREND PIPELINE */}
      {activeSubTab === 'trends' && (
        <GeoAeoTrendTracker
          domain={report.domain}
          brandName={report.business_profile?.business_name}
          industry={report.business_profile?.industry}
        />
      )}

      {/* SUB-VIEW 2: COMMERCIAL QUERY MATRIX & LLM SIMULATION */}
      {activeSubTab === 'matrix' && (
        <AiSearch
          evaluations={report.ai_search_matrix}
          geoReadiness={report.geo_readiness}
          analysisId={report.analysis_id}
          onOpenPatchPack={onOpenPatchPack}
          onNavigateToTab={onNavigateToTab as any}
          onEvaluationsUpdated={onEvaluationsUpdated}
        />
      )}

      {/* SUB-VIEW 3: HIGH-DENSITY AI EXTRACTABILITY ENGINE (LAYER 1) */}
      {activeSubTab === 'extracts' && (
        <div className="space-y-6">
          {/* Executive Extractability KPI Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="sheet border border-line p-4 rounded-lg space-y-1 bg-paper-50 dark:bg-ink-900/40">
              <span className="label text-[10px] block text-ink-500">Layer 1 Extractability</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {extractabilityScore == null ? '—' : Math.round(extractabilityScore)}
                <span className="text-sm font-sans text-ink-400 font-normal">/100</span>
              </span>
              <span className="text-[11px] text-ink-500 block">Website-native proof</span>
            </div>

            <div className="sheet border border-line p-4 rounded-lg space-y-1 bg-paper-50 dark:bg-ink-900/40">
              <span className="label text-[10px] block text-ink-500">Answerability Score</span>
              <span className="font-serif text-3xl font-bold text-good">
                {qGraph?.supported_count ?? questionsSupported}
                <span className="text-sm font-sans text-ink-400 font-normal"> / {qGraph?.total_questions ?? questionsTotal}</span>
              </span>
              <span className="text-[11px] text-ink-500 block">First-party citable answers</span>
            </div>

            <div className="sheet border border-line p-4 rounded-lg space-y-1 bg-paper-50 dark:bg-ink-900/40">
              <span className="label text-[10px] block text-ink-500">Citation-Ready Passages</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {citationPassages?.highly_citable_count ?? 0}
                <span className="text-sm font-sans text-ink-400 font-normal"> blocks</span>
              </span>
              <span className="text-[11px] text-ink-500 block">
                {usefulRewrites.length} rewrites available
              </span>
            </div>

            <div className="sheet border border-line p-4 rounded-lg space-y-1 bg-paper-50 dark:bg-ink-900/40">
              <span className="label text-[10px] block text-ink-500">Claim Specificity</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {typeof claimsAnalysis?.aggregate_specificity_score === 'number' ? `${Math.round(claimsAnalysis.aggregate_specificity_score)}%` : '—'}
              </span>
              <span className="text-[11px] text-ink-500 block">
                {claimsAnalysis?.citable_claims_count ?? 0} verified triples
              </span>
            </div>
          </div>

          {/* Sub-Section Switcher */}
          <div className="sheet border border-line rounded-lg p-6 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-4">
              <div>
                <h3 className="font-serif text-2xl text-ink font-bold">
                  {extractSection === 'questions' && '50-Question Buyer Intent Answerability Graph'}
                  {extractSection === 'passages' && 'Citation-Ready Passage Detector & Drop-in Rewrites'}
                  {extractSection === 'triples' && 'Machine-Citable Factual Triples & Claims'}
                </h3>
                <p className="text-xs text-ink-500 mt-0.5">
                  {extractSection === 'questions' && 'How cleanly first-party crawled pages answer key commercial and technical queries without hallucination.'}
                  {extractSection === 'passages' && 'Stand-alone passages evaluated on attribution, density, and clarity with drop-in rewrites to maximize AI citations.'}
                  {extractSection === 'triples' && 'Structured (Subject, Predicate, Object) knowledge triples extracted from headings and declarative body text.'}
                </p>
              </div>

              <div className="flex items-center gap-1.5 bg-paper-100 dark:bg-ink-900 p-1 rounded-md border border-line">
                <button
                  type="button"
                  onClick={() => setExtractSection('questions')}
                  className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                    extractSection === 'questions'
                      ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                      : 'text-ink-600 hover:text-ink'
                  }`}
                >
                  Question Graph ({questionItems.length})
                </button>
                <button
                  type="button"
                  onClick={() => setExtractSection('passages')}
                  className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                    extractSection === 'passages'
                      ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                      : 'text-ink-600 hover:text-ink'
                  }`}
                >
                  Passages & Rewrites ({citationPassages?.passages?.length || 0})
                </button>
                <button
                  type="button"
                  onClick={() => setExtractSection('triples')}
                  className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                    extractSection === 'triples'
                      ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                      : 'text-ink-600 hover:text-ink'
                  }`}
                >
                  Claims & Triples ({claimsAnalysis?.claims?.length || 0})
                </button>
              </div>
            </div>

            {/* TAB 1: 50-QUESTION GRAPH */}
            {extractSection === 'questions' && (
              <div className="space-y-4">
                {/* Category Filter Pills */}
                {categories.length > 2 && (
                  <div className="flex flex-wrap items-center gap-1.5 pb-2">
                    {categories.map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setSelectedQuestionCategory(cat)}
                        className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
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
                    let pathname = '/';
                    if (q.evidence_url) {
                      try {
                        pathname = new URL(q.evidence_url, 'https://localhost').pathname || '/';
                      } catch {
                        pathname = q.evidence_url;
                      }
                    }
                    return (
                      <div key={idx} className="bg-paper-50 dark:bg-ink-900/40 border border-line rounded-lg p-4 space-y-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-[11px] text-ink-500 font-mono">
                            {category ? `${category} • ` : ''}{q.question_key || `Q-${idx + 1}`}
                          </span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                            q.status === 'SUPPORTED' ? 'bg-good/15 text-good' :
                            q.status === 'PARTIAL' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' :
                            q.status === 'CONFLICTING' ? 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300' :
                            'bg-bad/15 text-bad'
                          }`}>
                            {q.status}
                          </span>
                        </div>
                        <p className="font-semibold text-sm text-ink">{q.question}</p>
                        {q.answer && (
                          <div className="text-xs text-ink-800 dark:text-paper-100 bg-paper-100/70 dark:bg-ink-950/60 p-2.5 rounded border border-line">
                            <span className="font-bold text-pine block mb-0.5">Answer:</span>
                            {q.answer}
                          </div>
                        )}
                        <p className="text-xs text-ink-600 leading-relaxed">{q.why}</p>
                        {excerpt && (
                          <div className="bg-paper-100 dark:bg-ink-950 p-2.5 rounded border border-line text-[11px] font-mono text-ink-700">
                            <span className="text-[10px] text-ink-400 block mb-1">
                              Evidence from: {pathname}
                            </span>
                            "{excerpt}"
                          </div>
                        )}
                        {q.recommended_answer && q.status !== 'SUPPORTED' && (
                          <div className="text-xs text-ink-600 bg-pine/5 border border-pine/20 p-2 rounded">
                            <span className="font-bold text-pine block text-[11px] mb-0.5">Recommended Addition:</span>
                            {q.recommended_answer}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB 2: CITATION PASSAGES & DROP-IN REWRITES */}
            {extractSection === 'passages' && (
              <div className="space-y-6">
                {/* High Priority Rewrites */}
                {usefulRewrites.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-serif text-lg font-bold text-ink">
                        High-Impact Drop-In Rewrites ({usefulRewrites.length})
                      </h4>
                      <span className="text-xs text-pine font-mono font-semibold">
                        Optimized for Perplexity, SearchGPT & Gemini Grounding
                      </span>
                    </div>

                    <div className="space-y-4">
                      {usefulRewrites.map((rew: any, i: number) => (
                        <div key={i} className="bg-paper-50 dark:bg-ink-900 border border-line rounded-lg p-4 space-y-3">
                          <div className="flex items-center justify-between gap-2 border-b border-line pb-2">
                            <span className="text-xs font-mono font-bold text-ink">Passage ID: {rew.passage_id}</span>
                            <span className="text-xs font-mono text-good bg-good/10 px-2 py-0.5 rounded">
                              Score: {rew.estimated_score_improvement}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                            <div className="space-y-1">
                              <span className="label text-[10px] text-bad block">Current on-page text (vague or pronoun-heavy)</span>
                              <div className="p-3 bg-paper-100 dark:bg-ink-950 rounded border border-line text-ink-600 font-serif leading-relaxed">
                                "{rew.current_passage}"
                              </div>
                            </div>

                            <div className="space-y-1">
                              <span className="label text-[10px] text-good block">Recommended rewrite (machine-citable)</span>
                              <div className="p-3 bg-good/5 dark:bg-good/10 rounded border border-good/30 text-ink font-serif leading-relaxed">
                                "{rew.recommended_rewrite}"
                              </div>
                            </div>
                          </div>

                          <p className="text-[11px] text-ink-500 font-mono">
                            <span className="font-bold text-ink-700">Rationale:</span> {rew.why}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scanned Passages List */}
                <div className="space-y-3 pt-4 border-t border-line">
                  <h4 className="font-serif text-lg font-bold text-ink">
                    Scanned Passages & Suitability Scores ({citationPassages?.passages?.length || 0})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {(citationPassages?.passages || []).map((p: any, idx: number) => (
                      <div key={idx} className="bg-paper-50 dark:bg-ink-900/40 border border-line rounded-lg p-3.5 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs text-ink font-bold">{p.passage_id}</span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                            p.readiness_tier === 'HIGHLY_CITABLE' ? 'bg-good/15 text-good' :
                            p.readiness_tier === 'PARTIALLY_CITABLE' ? 'bg-amber-100 text-amber-800' :
                            'bg-bad/15 text-bad'
                          }`}>
                            {p.readiness_tier?.replace('_', ' ')} ({p.total_score}/100)
                          </span>
                        </div>
                        <p className="text-xs text-ink-800 leading-relaxed font-serif">"{p.raw_text}"</p>
                        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-line text-[10px] font-mono text-ink-500">
                          <span>Attribution: {p.subject_attribution_score}/25</span>
                          <span>Clarity: {p.standalone_clarity_score}/25</span>
                          <span>Density: {p.informational_gain_score}/25</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: CLAIMS & TRIPLES */}
            {extractSection === 'triples' && (
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
                        <div className="text-ink-500">Predicate: <span className="text-pine font-semibold">{c.predicate}</span></div>
                        <div className="text-ink-500">Object: <span className="text-ink font-semibold">{c.object}</span></div>
                      </div>

                      <p className="text-xs text-ink-700 italic">"{c.evidence_passage}"</p>

                      <div className="flex items-center justify-between text-[11px] font-mono pt-1 text-ink-500">
                        <span>Specificity: {Math.round(c.specificity_score * 100)}%</span>
                        <span>Verifiability: {Math.round(c.verifiability_score * 100)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: ENTITY & SCHEMA GROUNDING */}
      {activeSubTab === 'entities' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-4">
            <div>
              <h3 className="font-serif text-2xl text-ink font-bold">
                {entitySection === 'surfaces' ? 'Cross-Surface Entity Consistency' : 'Schema.org ↔ DOM Grounding Engine'}
              </h3>
              <p className="text-xs text-ink-500 mt-0.5">
                {entitySection === 'surfaces'
                  ? 'Verifying that Homepage, About, Services, Schema, and Footer identify the exact same business.'
                  : 'Comparing JSON-LD properties against visible DOM text to detect hidden markup and verify grounding.'}
              </p>
            </div>

            <div className="flex items-center gap-1.5 bg-paper-100 dark:bg-ink-900 p-1 rounded-md border border-line">
              <button
                type="button"
                onClick={() => setEntitySection('surfaces')}
                className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                  entitySection === 'surfaces'
                    ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                    : 'text-ink-600 hover:text-ink'
                }`}
              >
                5-Surface Consistency
              </button>
              <button
                type="button"
                onClick={() => setEntitySection('schema')}
                className={`text-xs font-mono px-3 py-1.5 rounded transition-colors ${
                  entitySection === 'schema'
                    ? 'bg-paper-50 dark:bg-ink-800 text-ink font-bold shadow-sm'
                    : 'text-ink-600 hover:text-ink'
                }`}
              >
                Schema ↔ HTML Match
              </button>
            </div>
          </div>

          {/* SECTION 1: 5 SURFACES AUDIT */}
          {entitySection === 'surfaces' && (
            <div className="space-y-6">
              {/* Fragmentation Alert if Present */}
              {entityConsistency?.discrepancies && entityConsistency.discrepancies.length > 0 && (
                <div className="p-4 bg-bad/5 border border-bad/30 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs font-mono text-bad uppercase tracking-wider">
                      Semantic Identity Fragmentation Detected ({entityConsistency.fragmentation_risk} RISK)
                    </span>
                    <span className="text-xs font-mono text-bad">
                      Score: {entityConsistency.overall_consistency_score}/100
                    </span>
                  </div>
                  <ul className="text-xs text-ink-800 space-y-1.5 list-disc list-inside">
                    {entityConsistency.discrepancies.map((d: any, idx: number) => (
                      <li key={idx}>
                        <span className="font-semibold text-bad uppercase">{d.field}:</span> {d.explanation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Surface Breakdown Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {entityConsistency?.surface_breakdown && Object.entries(entityConsistency.surface_breakdown).map(([sKey, sVal]: [string, any]) => (
                  <div key={sKey} className="bg-paper-50 dark:bg-ink-900/40 border border-line rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between border-b border-line pb-2">
                      <span className="text-xs font-mono font-bold text-ink uppercase">{sKey.replace('_', ' ')}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-100 dark:bg-ink-800 text-ink-600">
                        {typeof sVal.confidence === 'number' ? `Confidence ${Math.round(sVal.confidence * 100)}%` : 'Confidence not scored'}
                      </span>
                    </div>

                    <div className="space-y-1 text-xs">
                      <div>
                        <span className="text-ink-500 font-mono">Entity Brand:</span>{' '}
                        <span className="font-semibold text-ink">{sVal.brand_name_observed || 'Not observed'}</span>
                      </div>
                      <div>
                        <span className="text-ink-500 font-mono">Category:</span>{' '}
                        <span className="font-semibold text-pine">{sVal.category_observed || '—'}</span>
                      </div>
                      {sVal.locations_observed && sVal.locations_observed.length > 0 && (
                        <div>
                          <span className="text-ink-500 font-mono">Location:</span>{' '}
                          <span className="text-ink">{sVal.locations_observed.join(', ')}</span>
                        </div>
                      )}
                    </div>

                    <p className="text-[11px] text-ink-500 italic truncate pt-1 border-t border-line">
                      "{sVal.raw_evidence_snippet}"
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SECTION 2: SCHEMA ↔ HTML CROSSCHECK */}
          {entitySection === 'schema' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-paper-50 border border-line p-4 rounded-lg space-y-1">
                  <span className="label text-[10px] block">Entity graph quality</span>
                  <span className="font-serif text-3xl font-bold text-ink">
                    {typeof schemaCrosscheck?.quality_score === 'number' ? Math.round(schemaCrosscheck.quality_score) : '—'}
                    <span className="text-sm font-sans text-ink-400 font-normal">/100</span>
                  </span>
                  <span className="text-xs text-ink-500 block">
                    {schemaCrosscheck?.present_properties ?? 0} of {schemaCrosscheck?.applicable_properties ?? 0} applicable properties
                  </span>
                </div>

                <div className="bg-paper-50 border border-line p-4 rounded-lg space-y-1">
                  <span className="label text-[10px] block">Stated-property grounding</span>
                  <span className="font-serif text-3xl font-bold text-good">
                    {typeof schemaCrosscheck?.grounding_score === 'number' ? Math.round(schemaCrosscheck.grounding_score) : '—'}
                    <span className="text-sm font-sans text-ink-400 font-normal">/100</span>
                  </span>
                  <span className="text-xs text-ink-500 block">
                    {schemaCrosscheck?.verified_count ?? 0} of {schemaCrosscheck?.total_properties_checked ?? 0} stated properties
                  </span>
                </div>

                <div className="bg-paper-50 border border-line p-4 rounded-lg space-y-1">
                  <span className="label text-[10px] block">Identity contradictions</span>
                  <span className="font-serif text-3xl font-bold text-bad">
                    {schemaCrosscheck?.conflicts?.length ?? schemaCrosscheck?.unmatched_count ?? 0}
                  </span>
                  <span className="text-xs text-ink-500 block">Schema, Open Graph, and canonical disagree</span>
                </div>
              </div>

              {schemaCrosscheck?.summary && (
                <p className="text-xs text-ink-700 leading-relaxed">{schemaCrosscheck.summary}</p>
              )}

              {schemaCrosscheck?.conflicts?.length > 0 && (
                <div className="space-y-2">
                  {schemaCrosscheck.conflicts.map((conflict: any, idx: number) => (
                    <div key={idx} className="p-3 rounded border border-bad/30 bg-bad/5 text-xs text-ink-800">
                      {conflict.left_surface} says {conflict.left_value}. {conflict.right_surface} says {conflict.right_value}.
                    </div>
                  ))}
                </div>
              )}

              {/* Property Checks Table */}
              {schemaCrosscheck?.checks && schemaCrosscheck.checks.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-serif text-lg font-bold text-ink">Structured Property Cross-Audit</h4>
                  <div className="space-y-2">
                    {schemaCrosscheck.checks.map((chk: any, idx: number) => (
                      <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-paper-50 dark:bg-ink-900 border border-line rounded-lg gap-2 text-xs">
                        <div className="space-y-0.5">
                          <span className="font-mono text-ink-500 text-[10px] uppercase font-bold">
                            {chk.schema_type} • {chk.property_name}
                          </span>
                          <p className="text-ink font-medium">{chk.explanation}</p>
                        </div>
                        <span className={`text-[10px] font-mono px-2 py-1 rounded font-bold whitespace-nowrap self-start sm:self-auto ${
                          chk.status === 'VERIFIED' ? 'bg-good/15 text-good' :
                          chk.status === 'PARTIAL' ? 'bg-amber-100 text-amber-800' : 'bg-bad/15 text-bad'
                        }`}>
                          {chk.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </PillarShell>
  );
}
