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
      id: 'search_seo',
      name: 'Pillar 1: Search Intelligence (Technical & On-Page SEO)',
      weight_pct: 25,
      core_signals: [
        'HTTP Status Codes & Canonical URL integrity',
        'Robots.txt & XML Sitemap 200 OK indexing directive',
        'H1 Hierarchy & Title/Meta tag character bounds',
        'DOM-Validated Schema.org structured data scripts',
        'Mobile Viewport, TTFB latency (<500ms), and 4xx/5xx crawl rates',
      ],
      measurement_mode: 'Empirical AST & DOM Crawl Engine',
    },
    {
      id: 'ai_search_geo',
      name: 'Pillar 2: AI Search Intelligence (GEO & AEO)',
      weight_pct: 25,
      core_signals: [
        'Live Cross-Engine Citations (ChatGPT, Perplexity, Gemini, Claude)',
        'Direct Definition & Entity Clarity in First 200 Words',
        'Fact Extractability & Pricing Transparency for LLM synthesizers',
        '6-Prompt Canonical Commercial Buyer Inquiry Matrix coverage',
      ],
      measurement_mode: 'Live Multi-Model Querying + DOM Semantic Extraction',
    },
    {
      id: 'experience_sxo',
      name: 'Pillar 3: Experience Intelligence (SXO & Readability)',
      weight_pct: 20,
      core_signals: [
        'Flesch-Kincaid & Gunning-Fog Readability (Target: 60–80)',
        'Content scannability, proof-point density, and low fluff ratio',
        'Visual hierarchy, CTA button contrast & placement above the fold',
        'Cumulative Layout Shift (CLS) and viewport stabilization',
      ],
      measurement_mode: 'Empirical Heuristics & Text Complexity Algorithms',
    },
    {
      id: 'conversion_cro',
      name: 'Pillar 4: Conversion Intelligence (CRO & Funnels)',
      weight_pct: 20,
      core_signals: [
        '5-Second Value Proposition Clarity & ICP recognition',
        'High-contrast Action Verbs in primary call-to-action buttons',
        'Form Field Friction Count (< 4 input fields optimal)',
        'Commercial Bakeoff Delta against top 2 direct market peers',
      ],
      measurement_mode: 'Behavioral Heuristics + GA4 First-Party Connector',
    },
    {
      id: 'brand_trust',
      name: 'Pillar 5: Trust Intelligence (On-Page E-E-A-T Architecture)',
      weight_pct: 10,
      core_signals: [
        'Strict HTTPS encryption & valid SSL/TLS handshake',
        'Organization Schema with sameAs social profile verification',
        'Published Privacy Policy & Terms of Service URLs',
        'Direct Physical NAP (Name, Address, Phone) & Support Routing',
        'Executive & Author Byline Attribution',
      ],
      measurement_mode: 'Verified On-Page Governance (External Backlink Graph Optional via Majestic/DataForSEO)',
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
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-pine/10 text-pine font-bold border border-pine/30">
                METHODOLOGY SPECIFICATION
              </span>
              <span className="font-mono text-xs text-ink-500">v4.0 · September 2026</span>
            </div>
            <h2 className="font-serif text-2xl text-ink font-bold mt-1">
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
            { id: 'weights', label: '1. Five Pillar Weights' },
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
                  ? 'border-pine text-pine'
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
              <div className="p-4 rounded-xl bg-pine/5 border border-pine/20 space-y-1">
                <span className="font-semibold text-pine text-xs uppercase tracking-wider block">
                  Core Philosophical Principle
                </span>
                <p className="text-xs text-ink-600 dark:text-ink-400">
                  Scores are calculated strictly from empirically observed DOM nodes, HTTP telemetry, and live model queries. No invented CAC, synthetic TAM, or fabricated backlink authority.
                </p>
              </div>

              <div className="space-y-4">
                {pillars.map((pillar) => (
                  <div
                    key={pillar.id}
                    className="p-4 rounded-xl border border-line bg-paper-50 dark:bg-ink-900/40 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-serif font-bold text-ink text-base">{pillar.name}</h3>
                      <span className="font-mono text-xs px-2.5 py-1 rounded-full bg-ink text-paper-50 dark:bg-paper-100 dark:text-ink font-bold">
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
                      <span className="text-pine font-semibold">{pillar.measurement_mode}</span>
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
                <h3 className="font-serif text-lg font-bold text-ink">Diminishing Returns Deduction Formula</h3>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  In enterprise auditing, scoring must reflect true systemic impact. The first occurrence of an issue hits hardest because it introduces a new failure vector. Repeating instances of the same error category erode score at a calibrated diminishing rate to avoid score collapse on single taxonomies.
                </p>
                <div className="p-3 bg-paper-50 dark:bg-ink-950 rounded-lg border border-line font-mono text-xs text-pine font-semibold">
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
                      <td className="p-3 font-bold text-amber-600 dark:text-amber-400">HIGH</td>
                      <td className="p-3 font-semibold">-15.0 pts</td>
                      <td className="p-3">-9.0 pts</td>
                      <td className="p-3">-6.0 pts</td>
                      <td className="p-3">-4.0 pts</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-blue-600 dark:text-blue-400">MEDIUM</td>
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
              <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 space-y-2">
                <span className="font-semibold text-purple-700 dark:text-purple-300 text-xs uppercase tracking-wider block">
                  Strict Confidence Gating Architecture
                </span>
                <p className="text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
                  To prevent overclaiming during institutional and procurement due diligence, Dristik enforces an architectural gate between checkable DOM facts and cognitive AI inferences.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-5 rounded-xl border-2 border-emerald-500/50 bg-emerald-50/20 dark:bg-emerald-950/20 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🔬</span>
                    <h4 className="font-serif font-bold text-ink">Verified Empirical DOM Facts</h4>
                  </div>
                  <ul className="text-xs space-y-2 text-ink-600 dark:text-ink-400">
                    <li>✓ <strong>Grounding:</strong> Direct DOM element selector, HTTP status, or AST syntax tree.</li>
                    <li>✓ <strong>Executive Summary:</strong> Eligible to appear in primary blockers and headline constraints.</li>
                    <li>✓ <strong>Severity Allowed:</strong> Full severity impact (Up to CRITICAL -25 pts).</li>
                    <li>✓ <strong>Verification:</strong> 100% replicable via Chrome DevTools or cURL.</li>
                  </ul>
                </div>

                <div className="p-5 rounded-xl border-2 border-purple-500/50 bg-purple-50/20 dark:bg-purple-950/20 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">💡</span>
                    <h4 className="font-serif font-bold text-ink">Cognitive Model Inferences</h4>
                  </div>
                  <ul className="text-xs space-y-2 text-ink-600 dark:text-ink-400">
                    <li>⚠ <strong>Grounding:</strong> Multi-agent narrative reasoning or buyer psychology deduction.</li>
                    <li>✗ <strong>Executive Summary:</strong> Strictly barred from headlining executive blockers.</li>
                    <li>⚠ <strong>Severity Capped:</strong> Automatically capped at MEDIUM (max -4.0 pts deduction).</li>
                    <li>⚠ <strong>Isolation:</strong> Routed exclusively into dedicated "Exploratory Hypotheses".</li>
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
                  color: 'text-pine border-pine bg-pine/10',
                  desc: 'Strong discoverability with minor friction points. Capable of being cited by answer engines but has room for copy and CTA improvements.',
                },
                {
                  range: '50 – 74',
                  band: 'Fragile Presence',
                  color: 'text-amber-600 border-amber-500 bg-amber-50 dark:bg-amber-950/20',
                  desc: 'Multiple technical or content bottlenecks at risk of being filtered by Googlebot or ignored by multi-engine LLMs.',
                },
                {
                  range: '0 – 49',
                  band: 'Critical Vulnerability',
                  color: 'text-bad border-bad bg-bad/10',
                  desc: 'Severe accessibility, indexing, or positioning failure. Immediate engineering and editorial remediation required.',
                },
              ].map((b, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border ${b.color} space-y-1.5`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-serif font-bold text-ink text-base">{b.band}</span>
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
            <span className="font-mono text-pine">GSC & GA4 First-Party Connectors</span>
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
