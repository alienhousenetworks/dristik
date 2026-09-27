import React, { useState } from 'react';
import { ExecutiveReport, Finding } from '../../types';
import { PillarShell } from '../ui';

interface WebsiteExperienceViewProps {
  report: ExecutiveReport;
  onSelectFinding?: (f: Finding) => void;
}

type ExpSubTab = 'sxo' | 'cwv' | 'mobile' | 'accessibility' | 'ia';

export function WebsiteExperienceView({
  report,
  onSelectFinding,
}: WebsiteExperienceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<ExpSubTab>('sxo');

  const crawl = report.crawl_manifest;
  const homePage = crawl?.pages?.[0];
  const ttfb = typeof homePage?.ttfb_ms === 'number' && homePage.ttfb_ms > 0 ? homePage.ttfb_ms : null;
  const ctas = homePage?.ctas || [];
  const measuredUx = report.scores?.category_scores?.['UX_CONVERSION']?.score ?? report.honest_scores?.human_score;
  const uxScore = typeof measuredUx === 'number' ? Math.round(measuredUx) : null;

  const findings = (report.findings || []).filter(
    (f) => f.category === 'UX_CONVERSION'
  );

  return (
    <PillarShell
      kicker="Experience"
      title="Speed, mobile, and usability"
      description="How quickly the site loads, how it behaves on mobile, and whether visitors can complete the job they came for."
      scoreLabel="Experience"
      score={uxScore ?? '—'}
      metaLabel="TTFB"
      meta={ttfb == null ? '—' : `${ttfb} ms`}
      tabs={[
        { id: 'sxo', label: 'Experience' },
        { id: 'cwv', label: 'Speed' },
        { id: 'mobile', label: 'Mobile' },
        { id: 'accessibility', label: 'Accessibility' },
        { id: 'ia', label: 'Structure' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as ExpSubTab)}
    >

      {/* SUB-VIEW 1: SXO SEARCH EXPERIENCE */}
      {activeSubTab === 'sxo' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-5 rounded-lg space-y-2">
              <span className="label text-[10px] block">3-Second Hook Test</span>
              <span className="font-serif text-2xl font-bold text-ink">
                {homePage?.title ? 'Title present' : 'No title'}
              </span>
              <p className="text-xs text-ink-500 leading-relaxed">
                Whether a visitor arriving from Google or ChatGPT immediately grasps what the company does within 3 seconds.
              </p>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-5 rounded-lg space-y-2">
              <span className="label text-[10px] block">Bounce Risk Mitigation</span>
              <span className="font-serif text-2xl font-bold text-ink">
                Not measured
              </span>
              <p className="text-xs text-ink-500 leading-relaxed">
                Bounce rate needs analytics. This crawl does not record it.
              </p>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-5 rounded-lg space-y-2">
              <span className="label text-[10px] block">Intent Resolution</span>
              <span className="font-serif text-2xl font-bold text-ink">
                {report.business_profile?.primary_intent || '—'}
              </span>
              <p className="text-xs text-ink-500 leading-relaxed">
                Matching search queries directly to specific on-page actions.
              </p>
            </div>
          </div>

          {/* UX & SXO Findings */}
          <div className="sheet border border-line rounded-lg p-6 space-y-4">
            <h3 className="font-serif text-xl text-ink font-bold">
              User Experience & Intent Obstacles ({findings.length})
            </h3>
            {findings.length === 0 ? (
              <p className="text-sm text-good">No critical experience bottlenecks identified.</p>
            ) : (
              <div className="space-y-3">
                {findings.map((f) => (
                  <div
                    key={f.finding_id}
                    onClick={() => onSelectFinding?.(f)}
                    className="p-3.5 bg-paper-50 dark:bg-ink-900/40 border border-line rounded-md hover:border-pine cursor-pointer transition-colors flex items-start justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-paper-200 text-ink-700">
                          {f.severity}
                        </span>
                        <span className="font-semibold text-ink text-sm">{f.title}</span>
                      </div>
                      <p className="text-xs text-ink-600 line-clamp-1">{f.description}</p>
                    </div>
                    <span className="text-xs text-pine font-mono font-bold shrink-0 self-center">
                      Inspect →
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: CORE WEB VITALS & PERFORMANCE */}
      {activeSubTab === 'cwv' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Core Web Vitals & Server Performance</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">TTFB (Time to First Byte)</span>
              <span className="font-serif text-3xl font-bold text-ink">{ttfb == null ? '—' : `${ttfb} ms`}</span>
              <span className="text-xs text-ink-500 block">{ttfb == null ? 'Not measured on this crawl' : 'From this crawl'}</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">DOM Tree Depth</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {homePage?.dom_elements_count ?? '—'}
              </span>
              <span className="text-xs text-ink-500 block">{homePage?.dom_elements_count ? 'Elements counted' : 'Not counted'}</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">External Scripts</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {homePage?.scripts_count ?? '—'}
              </span>
              <span className="text-xs text-ink-500 block">JavaScript payload</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Stylesheets</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {homePage?.stylesheets_count ?? '—'}
              </span>
              <span className="text-xs text-ink-500 block">{homePage?.stylesheets_count == null ? 'Not counted' : 'Stylesheets counted'}</span>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: MOBILE USABILITY */}
      {activeSubTab === 'mobile' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Mobile Viewport & Responsiveness</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Viewport Meta Tag</span>
              <p className="font-mono text-xs text-ink bg-paper-100 p-2 rounded border border-line">
                {homePage?.viewport || 'Not found'}
              </p>
              <span className="text-xs text-ink-500 block">{homePage?.viewport ? 'Viewport tag present' : 'No viewport tag in the crawl'}</span>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Tap Target Safety</span>
              <p className="font-serif text-xl font-bold text-ink">Not measured</p>
              <span className="text-xs text-ink-500 block">Tap-target size was not rendered.</span>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: ACCESSIBILITY */}
      {activeSubTab === 'accessibility' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Accessibility (WCAG 2.1 AA) Compliance</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Image Alt Text</span>
              <span className="font-serif text-3xl font-bold text-ink">
                {homePage?.images_without_alt === 0 ? '100%' : `${homePage?.images_without_alt || 0} missing`}
              </span>
              <span className="text-xs text-ink-500 block">Screen reader image descriptions</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Heading Hierarchy</span>
              <span className="font-serif text-3xl font-bold text-ink">—</span>
              <span className="text-xs text-ink-500 block">Heading order was not scored as a pass.</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Semantic HTML5</span>
              <span className="font-serif text-3xl font-bold text-ink">—</span>
              <span className="text-xs text-ink-500 block">Landmark tags were not scored.</span>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 5: INFORMATION ARCHITECTURE */}
      {activeSubTab === 'ia' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Information Architecture & Navigation Flow</h3>
          <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-3">
            <span className="label text-[10px] block">Detected Calls to Action & Navigation Triggers</span>
            <div className="flex flex-wrap gap-2">
              {ctas.length > 0 ? (
                ctas.map((cta, i) => (
                  <span key={i} className="px-3 py-1 bg-paper-100 border border-line rounded-full text-xs font-medium text-ink">
                    🔘 {cta}
                  </span>
                ))
              ) : (
                <span className="text-xs text-ink-500">No CTA strings were extracted.</span>
              )}
            </div>
          </div>
        </div>
      )}
    </PillarShell>
  );
}
