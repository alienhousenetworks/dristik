import React, { useState, useEffect } from 'react';

interface GeneratedLandingPageSpec {
  page_slug: string;
  target_intent: string;
  page_title: string;
  meta_description: string;
  h1_headline: string;
  hero_subhead: string;
  value_pillars: string[];
  faq_microdata: Array<{ question: string; answer: string }>;
  primary_cta: string;
  estimated_monthly_lead_potential: number;
  schema_markup: string;
}

interface CommercialOpportunity {
  opportunity_id: string;
  title: string;
  category: string;
  market_rationale: string;
  competitor_signal: string;
  content_void: string;
  impact_level: string;
  estimated_annual_pipeline_inr: number;
  generated_spec: GeneratedLandingPageSpec;
}

interface LeadGenOpportunitiesViewProps {
  domain: string;
  bizName?: string;
  niche?: string;
  analysisId?: string;
  onDeployRequested?: (spec: GeneratedLandingPageSpec) => void;
}

export function LeadGenOpportunitiesView({
  domain,
  bizName = 'Target Brand',
  niche = 'Enterprise Solutions',
  analysisId,
  onDeployRequested
}: LeadGenOpportunitiesViewProps) {
  const [opportunities, setOpportunities] = useState<CommercialOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeSpecModal, setActiveSpecModal] = useState<CommercialOpportunity | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchOpportunities = async () => {
      setLoading(true);
      try {
        const queryParams = new URLSearchParams({
          domain,
          biz_name: bizName,
          niche
        });
        if (analysisId) queryParams.append('analysis_id', analysisId);

        const res = await fetch(`/api/v1/intelligence/lead-gen?${queryParams.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setOpportunities(data);
        }
      } catch (err) {
        console.error('Failed to load lead gen opportunities:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchOpportunities();
  }, [domain, bizName, niche, analysisId]);

  if (loading) {
    return (
      <div className="p-8 sheet border border-line rounded-lg flex items-center justify-center gap-3 text-ink-500">
        <div className="w-5 h-5 border-2 border-pine border-t-transparent rounded-full animate-spin"></div>
        <span>Detecting commercial voids & lead generation opportunities...</span>
      </div>
    );
  }

  if (opportunities.length === 0) {
    return (
      <div className="p-6 sheet border border-line rounded-lg space-y-2">
        <span className="label text-ink">Lead gen: no crawl-backed voids</span>
        <p className="text-sm text-ink-800">
          No landing-page blueprints were invented. Lead gen only reports URL gaps from a completed crawl
          (missing /pricing, /compare, or /solutions). Re-run the audit, then open this tab with that analysis id.
        </p>
      </div>
    );
  }

  const formatINR = (val?: number | null) => {
    if (val == null) return 'Unestimated (Input Required)';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  const totalPipeline = opportunities.reduce((acc, o) => acc + (o.estimated_annual_pipeline_inr || 0), 0);
  const hasPipelineEstimates = opportunities.some(o => o.estimated_annual_pipeline_inr != null);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="sheet border border-line rounded-lg p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="label text-pine">
                Commercial Void Detection & 1-Click Page Generation
              </span>
            </div>
            <h3 className="font-serif text-2xl md:text-3xl text-ink font-normal">
              High-Intent Lead Opportunities Captured by Competitors
            </h3>
            <p className="text-xs text-ink-500 mt-1 max-w-xl">
              Dristik crawls competitor citations to detect where buyers ask commercial questions that your site has no page for.
              Click any opportunity to inspect and generate an instant landing page blueprint with Schema.org JSON-LD.
            </p>
          </div>

          {hasPipelineEstimates && (
            <div className="bg-paper-50 border border-line rounded-md p-3 text-right shrink-0">
              <span className="label block text-[10px]">Total Pipeline In Jeopardy</span>
              <span className="text-2xl font-serif font-bold text-good">
                {formatINR(totalPipeline)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Opportunities List */}
      {opportunities.length === 0 ? (
        <div className="p-8 text-center bg-paper-50 rounded-lg border border-line text-ink-500 text-xs">
          No commercial opportunity voids detected for this domain.
        </div>
      ) : (
      <div className="space-y-4">
        {opportunities.map((opp) => (
          <div
            key={opp.opportunity_id}
            className="sheet border border-line hover:border-ink-400 rounded-lg p-5 transition-all space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                  opp.impact_level === 'CRITICAL'
                    ? 'bg-red-100 text-bad border-red-200'
                    : 'bg-amber-100 text-warn border-amber-200'
                }`}>
                  {opp.impact_level} IMPACT
                </span>
                <span className="text-[11px] font-mono text-ink-500">{opp.category}</span>
              </div>
              <div className="text-sm font-mono font-bold text-good">
                Est. Pipeline: {opp.estimated_annual_pipeline_inr != null ? formatINR(opp.estimated_annual_pipeline_inr) : 'Qualitative Void'}
              </div>
            </div>

            <div>
              <h4 className="text-base font-bold text-ink">{opp.title}</h4>
              <p className="text-xs text-ink-700 mt-1 leading-relaxed">{opp.market_rationale}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-paper-50 p-3.5 rounded-md border border-line">
              <div>
                <span className="label text-[10px] text-warn block">Competitor Signal:</span>
                <p className="text-ink-700 mt-0.5">{opp.competitor_signal}</p>
              </div>
              <div>
                <span className="label text-[10px] text-bad block">Your Content Void:</span>
                <p className="text-ink-700 mt-0.5">{opp.content_void}</p>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-line">
              <div className="text-xs text-ink-500">
                Target Slug: <span className="font-mono text-ink font-semibold">{opp.generated_spec.page_slug}</span> · Lead Potential: <span className="text-good font-bold">{opp.generated_spec.estimated_monthly_lead_potential != null ? `${opp.generated_spec.estimated_monthly_lead_potential} qualified demos/mo` : 'High-Intent Void'}</span>
              </div>
              <button
                type="button"
                onClick={() => setActiveSpecModal(opp)}
                className="btn-primary text-xs px-3.5 py-1.5 rounded-md font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <span>🚀</span>
                <span>Inspect Landing Page Blueprint</span>
              </button>
            </div>
          </div>
        ))}
      </div>
      )}

      {/* Landing Page Spec Modal */}
      {activeSpecModal && (
        <div className="scrim fixed inset-0 z-50 overflow-y-auto p-4 flex flex-col items-center justify-center">
          <div className="sheet border border-line rounded-lg max-w-3xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div>
                <span className="label text-pine">
                  Ready-to-Deploy Landing Page Blueprint
                </span>
                <h3 className="text-lg font-serif text-ink mt-0.5">{activeSpecModal.title}</h3>
              </div>
              <button
                type="button"
                onClick={() => setActiveSpecModal(null)}
                className="text-ink-400 hover:text-ink text-lg font-bold px-2"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-paper-50 p-3 rounded-md border border-line">
                <div>
                  <span className="label text-[10px] block">Slug</span>
                  <span className="font-mono text-ink font-semibold">{activeSpecModal.generated_spec.page_slug}</span>
                </div>
                <div>
                  <span className="label text-[10px] block">Target Intent</span>
                  <span className="text-ink-700">{activeSpecModal.generated_spec.target_intent}</span>
                </div>
              </div>

              <div>
                <span className="label text-[10px] block mb-1">Page Title & Meta Description</span>
                <p className="font-bold text-ink text-sm">{activeSpecModal.generated_spec.page_title}</p>
                <p className="text-ink-500 mt-1">{activeSpecModal.generated_spec.meta_description}</p>
              </div>

              <div className="border border-line bg-paper-50 p-4 rounded-md space-y-2">
                <span className="label text-pine text-[10px] block">Hero Section Architecture</span>
                <h4 className="text-base font-bold text-ink font-serif">{activeSpecModal.generated_spec.h1_headline}</h4>
                <p className="text-ink-700 leading-relaxed">{activeSpecModal.generated_spec.hero_subhead}</p>
                <div className="pt-2">
                  <span className="inline-block bg-pine-100 text-pine border border-pine/20 px-3 py-1 rounded text-xs font-bold">
                    CTA: {activeSpecModal.generated_spec.primary_cta}
                  </span>
                </div>
              </div>

              <div>
                <span className="label text-[10px] block mb-2">Value Pillars</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {activeSpecModal.generated_spec.value_pillars.map((pillar, i) => (
                    <div key={i} className="bg-paper-50 border border-line p-2.5 rounded text-ink-700 text-[11px]">
                      {pillar}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="label text-[10px]">Schema.org JSON-LD (FAQPage + Service)</span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(activeSpecModal.generated_spec.schema_markup);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="text-[10px] text-pine hover:underline font-mono font-semibold"
                  >
                    {copied ? '✓ Copied!' : 'Copy JSON-LD'}
                  </button>
                </div>
                <pre className="bg-paper-200/70 p-3 rounded border border-line font-mono text-[10px] text-ink overflow-x-auto max-h-40">
                  {activeSpecModal.generated_spec.schema_markup}
                </pre>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-line">
              <button
                type="button"
                onClick={() => setActiveSpecModal(null)}
                className="px-4 py-2 border border-line hover:border-ink-400 rounded-md text-xs font-medium text-ink-700 transition-colors"
              >
                Close
              </button>
              {onDeployRequested && (
                <button
                  type="button"
                  onClick={() => {
                    onDeployRequested(activeSpecModal.generated_spec);
                    setActiveSpecModal(null);
                  }}
                  className="btn-primary px-4 py-2 rounded-md text-xs font-semibold shadow-xs"
                >
                  Deploy Page via Connector (WordPress / Webflow / Git)
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
