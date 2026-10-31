import React, { useState, useEffect } from 'react';

interface ScoringRubricModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PillarDetail {
  id: string;
  name: string;
  weight_pct: number;
  core_signals: string[];
  measurement_mode: string;
}

export function ScoringRubricModal({ isOpen, onClose }: ScoringRubricModalProps) {
  const [activeTab, setActiveTab] = useState<'weights' | 'formula' | 'gating' | 'bands'>('weights');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const pillars: PillarDetail[] = [
    {
      id: 'technical_seo',
      name: '1. Technical SEO',
      weight_pct: 15,
      core_signals: [
        'HTTP Status Codes & Canonical URL integrity',
        'Robots.txt & XML Sitemap 200 OK indexing directive',
        'TTFB latency (<500ms), DNS resolution, TLS handshake',
        'Crawl health, orphan page avoidance, and 4xx/5xx error rates',
      ],
      measurement_mode: 'Deterministic AST & DOM Crawl Engine',
    },
    {
      id: 'on_page_seo',
      name: '2. On-Page SEO',
      weight_pct: 10,
      core_signals: [
        'H1 Hierarchy & Title/Meta tag character bounds',
        'Semantic HTML structure & internal anchor link clarity',
        'Open Graph tags & social sharing cards',
        'Image alt text coverage & media accessibility',
      ],
      measurement_mode: 'HTML & Semantic DOM Analysis',
    },
    {
      id: 'content',
      name: '3. Content & Semantics',
      weight_pct: 15,
      core_signals: [
        'Flesch-Kincaid & Gunning-Fog readability bounds (60–80 target)',
        'Topic depth, semantic keyword cannibalization analysis',
        'Proof-point density and low fluff ratio',
        'Authoritative entity naming and terminology consistency',
      ],
      measurement_mode: 'Natural Language & Linguistic Heuristics',
    },
    {
      id: 'geo',
      name: '4. GEO & AI Readiness',
      weight_pct: 15,
      core_signals: [
        'Direct definition and entity clarity in top 200 words',
        'Fact extractability and pricing transparency for LLMs',
        'Quotable claims, statistical citations, and clear headings',
        '6-Prompt commercial buyer inquiry matrix coverage',
      ],
      measurement_mode: 'On-Page Extractability & Semantic Grounding',
    },
    {
      id: 'ai_search',
      name: '5. AI Search Visibility',
      weight_pct: 15,
      core_signals: [
        'Live cross-engine citations (ChatGPT, Perplexity, Gemini, Claude)',
        'Brand mention rate and synthesized share of voice',
        'Citation accuracy against source page ground truth',
        'Zero synthetic guesses: remains blank unless live engines ran',
      ],
      measurement_mode: 'Live Multi-Engine Monitor (Blank when unmeasured)',
    },
    {
      id: 'schema',
      name: '6. Schema Architecture',
      weight_pct: 10,
      core_signals: [
        'DOM-validated Schema.org JSON-LD scripts and microdata',
        'Organization schema with verified sameAs profiles',
        'Product, FAQPage, Article, and BreadcrumbList syntax',
        'Google Rich Results eligibility validation',
      ],
      measurement_mode: 'AST Structured Data Parser',
    },
    {
      id: 'ux_conversion',
      name: '7. UX & Conversion (CRO)',
      weight_pct: 10,
      core_signals: [
        '5-second value proposition clarity above the fold',
        'High-contrast action verbs in primary CTAs',
        'Form field count stored on audited forms',
        'Mobile viewport responsiveness & layout shift (CLS)',
      ],
      measurement_mode: 'Behavioral Heuristics + GA4 First-Party Connector',
    },
    {
      id: 'trust_authority',
      name: '8. Trust & Authority (E-E-A-T)',
      weight_pct: 10,
      core_signals: [
        'Strict HTTPS encryption and modern TLS protocols',
        'Published Privacy Policy, Terms, and physical NAP',
        'Leadership & author byline attribution with verifiable experience',
        'Connected external vendor authority (GSC, Ahrefs, Semrush, Moz)',
      ],
      measurement_mode: 'Verified On-Page Governance & External Providers',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm animate-fade-in">
      <div
        className="sheet border border-line rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden bg-paper-50 dark:bg-ink-950"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-line flex items-center justify-between bg-paper-100/50 dark:bg-ink-900/50">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-bold border border-line">
                METHODOLOGY SPECIFICATION
              </span>
              <span className="font-mono text-xs text-ink-500">v4.0 · September 2026</span>
            </div>
            <h2 className="font-sans text-2xl text-ink font-bold mt-1">
              Dristik Enterprise Web Intelligence & Scoring Rubric
            </h2>
            <p className="text-xs text-ink-500 mt-0.5">
              Transparent, deterministic mathematical weighting, diminishing returns curves, and confidence gating rules.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-paper-200 dark:hover:bg-ink-800 text-ink-500 hover:text-ink transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-line px-6 gap-3 bg-paper-50 dark:bg-ink-900/30">
          {[
            { id: 'weights', label: '1. Eight Engine Categories' },
            { id: 'formula', label: '2. Diminishing Returns Math' },
            { id: 'gating', label: '3. Confidence Gating Rules' },
            { id: 'bands', label: '4. Calibrated Score Bands' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-2 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-line text-ink-700'
                  : 'border-transparent text-ink-500 hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-ink-700 dark:text-ink-300">
          {/* TAB 1: WEIGHTS */}
          {activeTab === 'weights' && (
            <div className="space-y-6">
              <div className="p-4 rounded-xl bg-paper-100 border border-line space-y-1">
                <span className="font-semibold text-ink-700 text-xs uppercase tracking-[0.04em] block">
                  Core Philosophical Principle
                </span>
                <p className="text-xs text-ink-600 dark:text-ink-400">
                  Scores are calculated strictly from empirically observed DOM nodes, HTTP telemetry, and live model queries. No invented CAC, synthetic TAM, or fabricated backlink authority. Missing external providers stay unmeasured.
                </p>
              </div>

              {/* Three Honesty Perspective Views */}
              <div className="p-4 rounded-xl border border-line bg-paper-100/60 dark:bg-ink-900/30 space-y-3">
                <span className="font-semibold text-ink text-xs uppercase tracking-[0.04em] block">
                  3 Honest Perspective Views (Composite Blends)
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-paper-50 dark:bg-ink-950 border border-line space-y-1">
                    <span className="font-bold text-ink block">Google Discoverability</span>
                    <p className="text-[11px] text-ink-500">45% Technical + 35% On-Page + 20% Schema. Evaluates organic crawling and indexing posture.</p>
                  </div>
                  <div className="p-3 rounded-lg bg-paper-50 dark:bg-ink-950 border border-line space-y-1">
                    <span className="font-bold text-ink block">Human Experience</span>
                    <p className="text-[11px] text-ink-500">40% UX/CRO + 35% Content Readability + 25% Trust. Evaluates engagement and conversion friction.</p>
                  </div>
                  <div className="p-3 rounded-lg bg-paper-50 dark:bg-ink-950 border border-line space-y-1">
                    <span className="font-bold text-ink block">AI Search Readiness</span>
                    <p className="text-[11px] text-ink-500">50% GEO Extractability + 50% AI Search Visibility (stays blank if live engine monitor was not run).</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {pillars.map((pillar) => (
                  <div
                    key={pillar.id}
                    className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-sans font-bold text-ink text-base">{pillar.name}</h3>
                      <span className="font-mono text-xs px-2.5 py-1 rounded-md bg-ink text-paper-50 dark:bg-paper-100 dark:text-ink font-bold">
                        Weight: {pillar.weight_pct}%
                      </span>
                    </div>

                    <div className="space-y-1">
                      <span className="label text-[10px] block text-ink-500">Signals Evaluated:</span>
                      <ul className="list-disc pl-5 text-xs space-y-1 text-ink-600 dark:text-ink-400">
                        {pillar.core_signals.map((sig, idx) => (
                          <li key={idx}>{sig}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="pt-2 border-t border-line/60 flex items-center justify-between text-[11px] font-mono text-ink-500">
                      <span>Inspection Method:</span>
                      <span className="text-ink-700 font-semibold">{pillar.measurement_mode}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: FORMULA */}
          {activeTab === 'formula' && (
            <div className="space-y-6">
              <div className="sheet border border-line p-5 rounded-xl space-y-3 bg-paper-100/40 dark:bg-ink-900/40">
                <h3 className="font-sans text-lg font-bold text-ink">Diminishing Returns Deduction Formula</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  In enterprise auditing, scoring must reflect true systemic impact. The first occurrence of an issue hits hardest because it introduces a new failure vector. Repeating instances of the same error category erode score at a calibrated diminishing rate to avoid score collapse on single taxonomies.
                </p>
                <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded-lg border border-line font-mono text-xs text-ink-700 font-semibold">
                  Deduction(Severity, Occurrence) = SeverityStepTable[OccurrenceIndex]
                </div>
              </div>

              <div className="sheet border border-line rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-paper-100/70 dark:bg-ink-900/70 border-b border-line">
                      <th className="p-3 font-semibold text-ink">Defect Severity</th>
                      <th className="p-3 font-semibold text-ink">1st Occurrence</th>
                      <th className="p-3 font-semibold text-ink">2nd Occurrence</th>
                      <th className="p-3 font-semibold text-ink">3rd Occurrence</th>
                      <th className="p-3 font-semibold text-ink">4th+ Occurrence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line font-mono text-xs">
                    <tr>
                      <td className="p-3 font-bold text-bad">CRITICAL</td>
                      <td className="p-3 font-semibold">-25.0 pts</td>
                      <td className="p-3">-12.0 pts</td>
                      <td className="p-3">-8.0 pts</td>
                      <td className="p-3">-5.0 pts</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-warn dark:text-warn">HIGH</td>
                      <td className="p-3 font-semibold">-15.0 pts</td>
                      <td className="p-3">-9.0 pts</td>
                      <td className="p-3">-6.0 pts</td>
                      <td className="p-3">-4.0 pts</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-ink-700 dark:text-ink-700">MEDIUM</td>
                      <td className="p-3 font-semibold">-8.0 pts</td>
                      <td className="p-3">-5.0 pts</td>
                      <td className="p-3">-3.0 pts</td>
                      <td className="p-3">-2.0 pts</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-ink-500">LOW</td>
                      <td className="p-3 font-semibold">-3.0 pts</td>
                      <td className="p-3">-2.0 pts</td>
                      <td className="p-3">-1.0 pts</td>
                      <td className="p-3">-1.0 pts</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: GATING */}
          {activeTab === 'gating' && (
            <div className="space-y-6">
              <div className="p-4 rounded-xl bg-paper-100 border border-line space-y-2">
                <span className="font-semibold text-ink-700 dark:text-ink-700 text-xs uppercase tracking-[0.04em] block">
                  Strict Confidence Gating Architecture
                </span>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  To prevent overclaiming during institutional and procurement due diligence, Dristik enforces an architectural gate between checkable DOM facts and cognitive AI inferences.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-5 rounded-xl border-2 border-good/30 bg-good/10 dark:bg-good/10 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg"></span>
                    <h4 className="font-sans font-bold text-ink">Verified Empirical DOM Facts</h4>
                  </div>
                  <ul className="text-xs space-y-2 text-ink-600 dark:text-ink-400">
                    <li>✓ <strong>Grounding:</strong> Direct DOM element selector, HTTP status, or AST syntax tree.</li>
                    <li>✓ <strong>Executive Summary:</strong> Eligible to appear in primary blockers and headline constraints.</li>
                    <li>✓ <strong>Severity Allowed:</strong> Full severity impact (Up to CRITICAL -25 pts).</li>
                    <li>✓ <strong>Verification:</strong> 100% replicable via Chrome DevTools or cURL.</li>
                  </ul>
                </div>

                <div className="p-5 rounded-xl border-2 border-line bg-paper-100 dark:bg-paper-100 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg"></span>
                    <h4 className="font-sans font-bold text-ink">Cognitive Model Inferences</h4>
                  </div>
                  <ul className="text-xs space-y-2 text-ink-600 dark:text-ink-400">
                    <li> <strong>Grounding:</strong> Multi-agent narrative reasoning or buyer psychology deduction.</li>
                    <li>✗ <strong>Executive Summary:</strong> Strictly barred from headlining executive blockers.</li>
                    <li> <strong>Severity Capped:</strong> Automatically capped at MEDIUM (max -4.0 pts deduction).</li>
                    <li> <strong>Isolation:</strong> Routed exclusively into dedicated "Exploratory Hypotheses".</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: BANDS */}
          {activeTab === 'bands' && (
            <div className="space-y-4">
              {[
                {
                  range: '90 – 100',
                  band: 'Category Benchmark',
                  color: 'text-good border-good bg-good/10',
                  desc: 'Exceptional architectural health. Schema, mobile viewport, direct answer definition, and crawlability meet institutional standards.',
                },
                {
                  range: '75 – 89',
                  band: 'Citation Ready',
                  color: 'text-ink-700 border-line bg-paper-200',
                  desc: 'Strong discoverability with minor friction points. Capable of being cited by answer engines but has room for copy and CTA improvements.',
                },
                {
                  range: '50 – 74',
                  band: 'Fragile Presence',
                  color: 'text-warn border-warn/30 bg-warn/10 dark:bg-warn/10',
                  desc: 'Multiple technical or content bottlenecks at risk of being filtered by Googlebot or ignored by multi-engine LLMs.',
                },
                {
                  range: '0 – 49',
                  band: 'Low readiness',
                  color: 'text-bad border-bad bg-bad/10',
                  desc: 'Severe accessibility, indexing, or positioning failure. Immediate engineering and editorial remediation required.',
                },
              ].map((b, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border ${b.color} space-y-1.5`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-sans font-bold text-ink text-base">{b.band}</span>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-paper-50 dark:bg-ink-900 border border-line">
                      Score: {b.range}
                    </span>
                  </div>
                  <p className="text-xs text-ink-600 dark:text-ink-400">{b.desc}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-line flex items-center justify-between bg-paper-100/50 dark:bg-ink-900/50">
          <div className="flex items-center gap-3 text-xs text-ink-500">
            <span>External Providers:</span>
            <span className="font-mono text-ink-700">GSC & GA4 First-Party Connectors</span>
            <span>•</span>
            <span className="font-mono text-ink-600">Backlink Index: Majestic / DataForSEO (Optional)</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-ink text-paper-50 dark:bg-paper-100 dark:text-ink font-semibold text-xs hover:opacity-90 transition-opacity"
          >
            Close Specification
          </button>
        </div>
      </div>
    </div>
  );
}
