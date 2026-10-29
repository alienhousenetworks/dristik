import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { LeadGenOpportunitiesView } from '../LeadGenOpportunitiesView';
import { CompetitorDiscoveryView } from '../CompetitorDiscoveryView';
import { CommercialBakeoffView } from '../CommercialBakeoffView';
import { CompetitorSideBySideBenchmark } from '../CompetitorSideBySideBenchmark';
import { PillarShell } from '../ui';

interface ConversionIntelligenceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  websiteUrl?: string;
  onDeployRemediation?: () => void;
}

type CroSubTab = 'cro' | 'cta_forms' | 'pricing' | 'funnel' | 'lead_gen' | 'bakeoff';

export function ConversionIntelligenceView({
  report,
  analysisId,
  websiteUrl,
  onDeployRemediation,
}: ConversionIntelligenceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<CroSubTab>('cro');

  const profile = report.business_profile;
  const semantic = report.semantic_business;
  const humanScore = report.honest_scores?.human_score;
  const croScore = typeof humanScore === 'number' ? Math.round(humanScore) : null;

  return (
    <PillarShell
      kicker="Conversion"
      title="Funnels, CTAs, and competitors"
      description="Clarity of the offer, form friction, pricing, and how you compare in buyer questions."
      scoreLabel="Conversion"
      score={croScore ?? '—'}
      metaLabel="Model"
      meta={profile?.business_model || '—'}
      tabs={[
        { id: 'cro', label: 'Clarity' },
        { id: 'cta_forms', label: 'CTAs & forms' },
        { id: 'pricing', label: 'Pricing' },
        { id: 'funnel', label: 'Journey' },
        { id: 'lead_gen', label: 'Lead gen' },
        { id: 'bakeoff', label: 'Competitors' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as CroSubTab)}
    >

      {/* SUB-VIEW 1: CRO HEURISTICS */}
      {activeSubTab === 'cro' && (
        <div className="space-y-6">
          <div className="sheet border border-line rounded-lg p-6 space-y-4">
            <span className="label text-[10px] block text-ink-700">5-Second Value Proposition</span>
            <p className="font-sans text-2xl text-ink leading-relaxed">
              {profile?.value_proposition ? `"${profile.value_proposition}"` : 'No value proposition was extracted from the crawl.'}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div className="bg-paper-50 p-3 rounded border border-line">
                <span className="label text-[10px] block">Target Audience</span>
                <span className="font-semibold text-ink text-xs mt-1 block">
                  {profile?.target_audience || '—'}
                </span>
              </div>
              <div className="bg-paper-50 p-3 rounded border border-line">
                <span className="label text-[10px] block">Primary Intent</span>
                <span className="font-semibold text-ink text-xs mt-1 block">
                  {profile?.primary_intent || '—'}
                </span>
              </div>
              <div className="bg-paper-50 p-3 rounded border border-line">
                <span className="label text-[10px] block">Primary CTA</span>
                <span className="font-semibold text-good text-xs mt-1 block">
                  {profile?.primary_cta || '—'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: CTAS & FORMS */}
      {activeSubTab === 'cta_forms' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Call to Action & Form Friction Audit</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Action Verbs in CTA Buttons</span>
              <p className="font-mono text-sm text-ink font-bold">
                {profile?.primary_cta ? `"${profile.primary_cta}"` : 'No CTA string was extracted.'}
              </p>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Form fields</span>
              <p className="font-sans text-xl font-bold text-ink">Not measured</p>
              <p className="text-xs text-ink-500">
                Field count and completion rate are blank until the crawl records the form or a CRM returns submissions.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: PRICING & MONETIZATION */}
      {activeSubTab === 'pricing' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Pricing Model & Commercial Transparency</h3>
          <div className="border border-line p-5 rounded-lg bg-paper-50 space-y-3">
            <span className="label text-[10px] block">Detected Monetization Structure</span>
            <p className="text-sm font-semibold text-ink">
              {profile?.business_model ? `Model: ${profile.business_model}` : 'No business model was stated on the crawled pages.'}
            </p>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: CUSTOMER JOURNEY & FUNNEL */}
      {activeSubTab === 'funnel' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Discovered Customer Journey Progression</h3>
          {semantic?.journey_stages && semantic.journey_stages.length > 0 ? (
            <div className="flex flex-wrap items-center gap-3">
              {semantic.journey_stages.map((stage, idx) => (
                <React.Fragment key={idx}>
                  <span className="text-xs font-mono bg-paper-100 border border-line px-3.5 py-2 rounded-lg text-ink font-medium">
                    {idx + 1}. {stage}
                  </span>
                  {idx < semantic.journey_stages.length - 1 && (
                    <span className="text-ink-400 text-sm">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          ) : (
            <p className="text-sm text-ink-500">No journey stages were extracted from this crawl.</p>
          )}
        </div>
      )}

      {/* SUB-VIEW 5: LEAD GEN OPPORTUNITIES */}
      {activeSubTab === 'lead_gen' && (
        <LeadGenOpportunitiesView
          domain={report.domain}
          bizName={profile?.business_name}
          niche={profile?.industry}
          analysisId={analysisId}
          onDeployRequested={onDeployRemediation}
        />
      )}

      {/* SUB-VIEW 6: COMPETITOR BAKEOFF */}
      {activeSubTab === 'bakeoff' && (
        <div className="space-y-8">
          <CompetitorSideBySideBenchmark
            targetDomain={report.domain}
            analysisId={analysisId || report.analysis_id}
            niche={profile?.industry}
          />
          {report.competitor_bakeoff && (
            <CommercialBakeoffView
              analysisId={analysisId || report.analysis_id || 'latest'}
              targetDomain={report.domain}
              initialBakeoff={report.competitor_bakeoff}
            />
          )}
          <CompetitorDiscoveryView
            websiteUrl={websiteUrl || report.website_url}
            analysisId={analysisId}
          />
        </div>
      )}
    </PillarShell>
  );
}
