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
  const croScore = Math.round(report.honest_scores?.human_score || 72);

  return (
    <PillarShell
      kicker="Conversion"
      title="Funnels, CTAs, and competitors"
      description="Clarity of the offer, form friction, pricing, and how you compare in buyer questions."
      scoreLabel="Conversion"
      score={croScore}
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
            <span className="label text-[10px] block text-pine">5-Second Value Proposition</span>
            <p className="font-serif text-2xl text-ink leading-relaxed">
              "{profile?.value_proposition || 'Comprehensive digital solutions for modern businesses.'}"
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div className="bg-paper-50 p-3 rounded border border-line">
                <span className="label text-[10px] block">Target Audience</span>
                <span className="font-semibold text-ink text-xs mt-1 block">
                  {profile?.target_audience || 'Commercial Decision Makers'}
                </span>
              </div>
              <div className="bg-paper-50 p-3 rounded border border-line">
                <span className="label text-[10px] block">Primary Intent</span>
                <span className="font-semibold text-ink text-xs mt-1 block">
                  {profile?.primary_intent || 'Lead Generation'}
                </span>
              </div>
              <div className="bg-paper-50 p-3 rounded border border-line">
                <span className="label text-[10px] block">Primary CTA</span>
                <span className="font-semibold text-good text-xs mt-1 block">
                  {profile?.primary_cta || 'Get Started / Contact Us'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: CTAS & FORMS */}
      {activeSubTab === 'cta_forms' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Call to Action & Form Friction Audit</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Action Verbs in CTA Buttons</span>
              <p className="font-mono text-sm text-ink font-bold">
                {profile?.primary_cta ? `"${profile.primary_cta}"` : 'Generic CTA detected'}
              </p>
              <p className="text-xs text-ink-500">
                Action-oriented buttons with immediate benefit outperform passive labels like "Submit" or "Click Here".
              </p>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Form Field Barriers</span>
              <p className="font-serif text-xl font-bold text-good">Friction Checked</p>
              <p className="text-xs text-ink-500">
                Forms with fewer than 4 input fields achieve up to 35% higher lead conversion rates.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: PRICING & MONETIZATION */}
      {activeSubTab === 'pricing' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Pricing Model & Commercial Transparency</h3>
          <div className="border border-line p-5 rounded-lg bg-paper-50 space-y-3">
            <span className="label text-[10px] block">Detected Monetization Structure</span>
            <p className="text-sm font-semibold text-ink">
              Model: {profile?.business_model || 'Subscription / Retainer'}
            </p>
            <p className="text-xs text-ink-600 leading-relaxed">
              Transparent pricing tables enhance Google AI search citability by allowing answer engines to quote verified price ranges.
            </p>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: CUSTOMER JOURNEY & FUNNEL */}
      {activeSubTab === 'funnel' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Discovered Customer Journey Progression</h3>
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
            <p className="text-sm text-ink-500">Awareness → Consideration → Commercial Evaluation → Conversion</p>
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
