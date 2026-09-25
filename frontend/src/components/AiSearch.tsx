import React, { useState } from 'react';
import { AiSearchQueryEvaluation, ExecutiveReport } from '../types';
import { display, formatPercent } from '../lib/format';

interface AiSearchProps {
  evaluations: AiSearchQueryEvaluation[];
  geoReadiness?: ExecutiveReport['geo_readiness'];
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: string) => void;
  onEvaluationsUpdated?: (evaluations: AiSearchQueryEvaluation[]) => void;
}

const CANONICAL_COMMERCIAL_QUESTIONS = [
  {
    key: 'identity',
    title: '1. Identity & Category',
    query: 'What does this company do, what is its primary offering, and what category does it belong to?',
    intent: 'Verify company name, core offering, and industry niche without marketing fluff.',
    risk: 'Without explicit WebSite and Organization Schema.org, LLMs hallucinate inaccurate adjacent categories.',
    remediation: 'Deploy schema.jsonld Organization graph and canonical llms.txt entity definitions.'
  },
  {
    key: 'icp',
    title: '2. Target Audience & ICP',
    query: 'Who is this product built for, what company sizes qualify, and who should NOT buy this?',
    intent: 'Verify explicit buyer personas, qualification criteria, and disqualifiers.',
    risk: 'Vague marketing jargon causes AI engines to omit your brand from specialized buyer vendor shortlists.',
    remediation: 'Publish character-safe ICP definitions with clear company-size bounds.'
  },
  {
    key: 'pricing',
    title: '3. Pricing & Commercial Model',
    query: 'How is this priced, what are the pricing tiers, and is self-serve or sales-led pricing available?',
    intent: 'Determine whether transparent pricing exists or if answer engines report "Contact Sales" / hallucinate.',
    risk: 'Perplexity and ChatGPT cite competitors with visible price points over sites that hide pricing behind sales demos.',
    remediation: 'Publish transparent pricing tiers or starting-at figures in FAQPage microdata.'
  },
  {
    key: 'alternatives',
    title: '4. Alternatives & Differentiation',
    query: 'How does this compare against primary market alternatives, and why choose it over competitors?',
    intent: 'Audit defensible competitive moats vs generic commodity claims.',
    risk: 'Competitors capture "alternatives to [Your Brand]" queries by publishing explicit comparison tables.',
    remediation: 'Deploy head-to-head comparison schemas and define unique architectural moats.'
  },
  {
    key: 'trust',
    title: '5. Trust & Enterprise Proof',
    query: 'What customer logos, case studies, security certifications, or social proof substantiate credibility?',
    intent: 'Verify third-party authority signals, SOC2/ISO/GDPR, and enterprise customer testimonials.',
    risk: 'Absence of verifiable customer proof leads answer engines to label your platform as unverified or high risk.',
    remediation: 'Include SOC2/GDPR compliance markers and verified customer case metrics in structured copy.'
  },
  {
    key: 'roi',
    title: '6. ROI & Time-to-Value',
    query: 'What is the concrete quantifiable business payoff, expected ROI, and time-to-value?',
    intent: 'Audit whether quantitative business outcomes (e.g. 3x faster, 40% reduction) are backed by evidence.',
    risk: 'Generative answer engines filter out non-quantified outcome claims as unsubstantiated marketing hyperbole.',
    remediation: 'Publish specific, evidence-grounded performance metrics with timeframes.'
  },
];

export function AiSearch({ evaluations, geoReadiness, analysisId, onOpenPatchPack, onNavigateToTab, onEvaluationsUpdated }: AiSearchProps) {
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = async () => {
    if (!analysisId) return;
    setIsSimulating(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/analyses/${analysisId}/simulate-ai-search`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Simulation failed: HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.ai_search_matrix && data.ai_search_matrix.length > 0) {
        if (onEvaluationsUpdated) {
          onEvaluationsUpdated(data.ai_search_matrix);
        }
      }
    } catch (err: any) {
      console.error('Simulation error:', err);
      setError(err?.message || 'Failed to simulate AI search queries.');
    } finally {
      setIsSimulating(false);
    }
  };

  const readinessBanner = geoReadiness ? (
    <div className="sheet border border-line rounded-lg p-5 space-y-2">
      <p className="label">GEO Readiness (on-page) vs Visibility (live engines)</p>
      <h3 className="font-serif text-2xl text-ink">{geoReadiness.headline}</h3>
      <p className="text-sm text-ink-600">{geoReadiness.visibility_message}</p>
      <ul className="text-sm text-ink-700 space-y-1">
        {geoReadiness.questions.map((q) => (
          <li key={q.question_key}>
            <span className="font-mono text-xs uppercase text-ink-500 mr-2">{q.status}</span>
            {q.question}
          </li>
        ))}
      </ul>
    </div>
  ) : null;

  if (!evaluations?.length) {
    return (
      <div className="space-y-6">
        {readinessBanner}
        {/* Diagnostic Explainer Banner */}
        <div className="sheet border border-line rounded-lg p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-warn animate-pulse"></span>
                <span className="label text-warn font-semibold">
                  Generative Answer Engine Evaluation Status
                </span>
              </div>
              <h3 className="font-serif text-2xl text-ink font-normal">
                Why Are AI Search Evaluations Pending?
              </h3>
              <p className="text-xs text-ink-500 max-w-2xl leading-relaxed">
                Dristik benchmarks your brand across the <strong>6 Canonical Commercial Buyer Queries</strong> in ChatGPT, Perplexity, Gemini, and Claude.
                Evaluations run against the crawled site evidence with the active LLM provider.
              </p>
              {error && (
                <div className="p-2.5 bg-red-50 dark:bg-red-950/20 border border-red-200 text-xs text-bad rounded">
                  {error}
                </div>
              )}
            </div>

            {/* Quick Action Buttons */}
            <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
              {analysisId && (
                <button
                  type="button"
                  disabled={isSimulating}
                  onClick={handleSimulate}
                  className="px-3.5 py-2 text-xs bg-ink text-paper rounded-md hover:bg-ink/90 font-medium transition-colors flex items-center gap-1.5 shadow-2xs disabled:opacity-50 cursor-pointer"
                >
                  {isSimulating ? (
                    <>
                      <span className="animate-spin">⏳</span>
                      <span>Evaluating 6 Queries with Live LLM...</span>
                    </>
                  ) : (
                    <>
                      <span>✨</span>
                      <span>Run Live Model Citability Evaluation</span>
                    </>
                  )}
                </button>
              )}
              {onNavigateToTab && (
                <button
                  type="button"
                  onClick={() => onNavigateToTab('ai_citations')}
                  className="px-3.5 py-2 text-xs bg-pine text-white rounded-md hover:bg-pine/90 font-medium transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
                >
                  <span>📡</span>
                  <span>View Real AI Citation Tracker</span>
                </button>
              )}
              {onOpenPatchPack && (
                <button
                  type="button"
                  onClick={onOpenPatchPack}
                  className="px-3.5 py-2 text-xs border border-line bg-paper-50 text-ink rounded-md hover:bg-paper-100 font-medium transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
                >
                  <span>📦</span>
                  <span>Open Developer Patch Pack</span>
                </button>
              )}
            </div>
          </div>

          {/* 3-Step Remediation Protocol */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-line text-xs">
            <div className="bg-paper-50 border border-line p-3.5 rounded-md space-y-1">
              <span className="label text-pine block font-mono text-[10px]">Step 1 · Ground Entity Facts</span>
              <p className="text-ink-700 leading-relaxed font-medium">
                Publish <code className="font-mono text-[11px]">/public/llms.txt</code> and Schema.org JSON-LD so LLM crawlers ingest unambiguous category, ICP, and pricing facts.
              </p>
            </div>
            <div className="bg-paper-50 border border-line p-3.5 rounded-md space-y-1">
              <span className="label text-pine block font-mono text-[10px]">Step 2 · Unblock Bot Crawlers</span>
              <p className="text-ink-700 leading-relaxed font-medium">
                Whitelist GPTBot, PerplexityBot, and ClaudeBot in <code className="font-mono text-[11px]">robots.txt</code> to permit real-time search indexation.
              </p>
            </div>
            <div className="bg-paper-50 border border-line p-3.5 rounded-md space-y-1">
              <span className="label text-pine block font-mono text-[10px]">Step 3 · Deploy FAQ Microdata</span>
              <p className="text-ink-700 leading-relaxed font-medium">
                Embed semantic HTML5 FAQ accordions with Schema microdata on high-intent solution pages to capture answer engine citations.
              </p>
            </div>
          </div>
        </div>

        {/* The 6 Canonical Commercial Questions Reference Matrix */}
        <div className="sheet border border-line rounded-lg p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
            <div>
              <span className="label text-pine">Empirical Commercial Evaluation Matrix &amp; Live Citations</span>
              <h4 className="font-serif text-xl text-ink font-normal mt-0.5">
                The 6 High-Intent Commercial Queries Evaluated by AI Search
              </h4>
            </div>
            <span className="text-xs font-mono bg-paper-50 border border-line px-2.5 py-1 rounded text-ink-600 self-start sm:self-auto">
              Perplexity · ChatGPT · Gemini · Claude
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CANONICAL_COMMERCIAL_QUESTIONS.map((item) => (
              <div
                key={item.key}
                className="bg-paper-50 border border-line rounded-lg p-4 space-y-2.5 hover:border-pine/40 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="label text-pine font-semibold text-[11px]">{item.title}</span>
                  <span className="text-[10px] font-mono bg-paper-100 dark:bg-ink-900 border border-line px-2 py-0.5 rounded text-ink-500">
                    Target Inquiry
                  </span>
                </div>

                <p className="font-serif text-base text-ink font-medium leading-snug">
                  "{item.query}"
                </p>

                <div className="text-xs space-y-1.5 pt-1 border-t border-line/60">
                  <p className="text-ink-600 leading-relaxed">
                    <strong className="text-ink font-semibold">Commercial Intent:</strong> {item.intent}
                  </p>
                  <p className="text-amber-800 dark:text-amber-300 leading-relaxed text-[11px]">
                    <strong>Answer Engine Risk:</strong> {item.risk}
                  </p>
                  <p className="text-good dark:text-emerald-400 leading-relaxed text-[11px]">
                    <strong>Remediation:</strong> {item.remediation}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {readinessBanner}
      <div className="sheet border border-line rounded-lg p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
          <div>
            <span className="label text-pine">Generative Answer Engine Retrieval Analysis</span>
            <h3 className="font-serif text-2xl text-ink font-normal mt-0.5">
              Simulated Commercial Search Evaluations
            </h3>
          </div>
          <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
            {analysisId && (
              <button
                type="button"
                disabled={isSimulating}
                onClick={handleSimulate}
                className="text-xs px-3 py-1.5 rounded border border-line bg-paper-50 hover:bg-paper-100 text-ink font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-2xs"
              >
                {isSimulating ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    <span>Re-simulating...</span>
                  </>
                ) : (
                  <>
                    <span>🔄</span>
                    <span>Re-simulate Queries</span>
                  </>
                )}
              </button>
            )}
            <span className="text-xs font-mono bg-good/10 text-good border border-good/20 px-3 py-1.5 rounded-full font-semibold">
              {evaluations.length} Commercial Queries Evaluated
            </span>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-2.5 bg-red-50 dark:bg-red-950/20 border border-red-200 text-xs text-bad rounded">
            {error}
          </div>
        )}

        <div className="divide-y divide-line">
          {evaluations.map((item, index) => (
            <article key={`${item.query}-${index}`} className="py-6 space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <span className="label text-pine font-semibold">{display(item.question_type)}</span>
                <span className="text-xs font-mono bg-paper-50 border border-line px-2.5 py-1 rounded text-ink-600">
                  Citability Score: <strong className="text-ink">{item.score}/10</strong> · Citation {formatPercent(item.citation_probability)} · {display(item.evidence_quality)}
                </span>
              </div>
              <h4 className="font-serif text-xl text-ink font-medium">"{display(item.query)}"</h4>
              <div className="bg-paper-50 border border-line p-3.5 rounded-md text-xs text-ink-700 leading-relaxed">
                <span className="label text-[10px] text-ink-500 block mb-1">Synthesized Answer Engine Response:</span>
                <p>{display(item.detected_answer)}</p>
              </div>
              {item.evidence_snippet && (
                <p className="text-xs text-ink-500 italic bg-paper-100/50 p-2.5 rounded border border-line/50">
                  <span className="font-semibold text-ink-700 not-italic">Crawled Evidence Anchor: </span>
                  "{item.evidence_snippet}"
                </p>
              )}
              <div className="text-xs text-ink-700 bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 p-3 rounded-md space-y-0.5">
                <span className="label text-[10px] text-warn block font-semibold">Strategic Citability Gap & Remediation:</span>
                <p className="text-ink leading-relaxed">{display(item.gap_analysis)}</p>
              </div>
              {item.after_answer && (
                <div className="bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 p-3.5 rounded-md text-xs text-ink-700 leading-relaxed space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="label text-[10px] text-good block font-semibold">Projected Grounded Response (Post-Patch Re-Query):</span>
                    {item.after_score != null && (
                      <span className="font-mono text-[11px] font-bold text-good">
                        Citability: {item.after_score}/10 {item.delta != null && `(+${item.delta} gain)`}
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-[11px]">{display(item.after_answer)}</p>
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
