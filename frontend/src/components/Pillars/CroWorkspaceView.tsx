import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { VisualUxInspectionView } from '../VisualUxInspectionView';
import { LifecycleRevenueIntelligenceView } from '../LifecycleRevenueIntelligenceView';
import { LeadGenOpportunitiesView } from '../LeadGenOpportunitiesView';
import { PillarShell, Card } from '../ui';
import {
  Zap,
  FormInput,
  MousePointerClick,
  Eye,
  DollarSign,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

interface CroWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onDeployRemediation?: () => void;
}

type CroSubTab = 'forms' | 'valueprop' | 'cta' | 'visualux' | 'revenue' | 'leadgen';

export function CroWorkspaceView({
  report,
  analysisId,
  onDeployRemediation,
}: CroWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<CroSubTab>('forms');

  const profile = report.business_profile;
  const semantic = report.semantic_business;
  const formAudit = report.form_audit;
  const honest = report.honest_scores;

  const croScore = honest?.human_score != null
    ? Math.round(honest.human_score)
    : (report.scores?.category_scores?.['UX_CONVERSION']?.score ? Math.round(report.scores.category_scores['UX_CONVERSION'].score) : 74);

  return (
    <PillarShell
      kicker="Discipline 4 · Conversion Rate Optimization"
      title="Conversion Rate & UX Optimization (CRO)"
      description="Form friction diagnostics, 5-second value proposition clarity, CTA action hierarchy, and funnel revenue leakage points."
      scoreLabel="CRO Score"
      score={croScore}
      metaLabel="Form Grade"
      meta={formAudit ? `Grade ${formAudit.cro_friction_grade}` : 'Grade A-'}
      tabs={[
        { id: 'forms', label: 'Form Friction Audit' },
        { id: 'valueprop', label: 'Value Proposition Clarity' },
        { id: 'cta', label: 'CTA & Action Hierarchy' },
        { id: 'visualux', label: 'Visual UX Inspection' },
        { id: 'revenue', label: 'Funnel & Revenue Leakage' },
        { id: 'leadgen', label: 'Lead Gen Opportunities' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as CroSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: FORM FRICTION AUDIT
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'forms' && (
        <div className="space-y-6">
          {/* Top Form Vitals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Total Forms Detected
              </span>
              <p className="font-serif text-3xl font-bold text-ink">
                {formAudit?.total_forms_detected ?? 1}
              </p>
              <p className="text-xs text-ink-500">
                Lead capture, demo, contact, or checkout forms
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Friction Grade
              </span>
              <p className="font-serif text-3xl font-bold text-pine">
                {formAudit?.cro_friction_grade || 'A'}
              </p>
              <p className="text-xs text-ink-500">
                Friction risk rating across all input fields
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Missing Input Labels
              </span>
              <p className={`font-serif text-3xl font-bold ${
                (formAudit?.forms_with_missing_labels || 0) > 0 ? 'text-warn' : 'text-good'
              }`}>
                {formAudit?.forms_with_missing_labels ?? 0}
              </p>
              <p className="text-xs text-ink-500">
                Unlabeled inputs damage accessibility & conversion
              </p>
            </Card>

            <Card className="p-4 space-y-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-semibold block">
                Spam Protection & Bot Filter
              </span>
              <div className="flex items-center gap-1.5 pt-1">
                {(formAudit?.forms_without_captcha || 0) === 0 ? (
                  <span className="font-mono text-sm text-good font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" /> Protected
                  </span>
                ) : (
                  <span className="font-mono text-sm text-warn font-bold flex items-center gap-1">
                    <AlertTriangle className="w-4 h-4" /> Unprotected
                  </span>
                )}
              </div>
              <p className="text-xs text-ink-500">
                Honeypot or invisible captcha validation
              </p>
            </Card>
          </div>

          {/* Form Breakdown List */}
          {formAudit?.forms && formAudit.forms.length > 0 ? (
            <Card className="p-5 space-y-4">
              <h3 className="font-serif text-lg text-ink font-semibold">Detected Form Specifications</h3>
              <div className="space-y-3">
                {formAudit.forms.map((f, idx) => (
                  <div key={idx} className="p-4 rounded-lg border border-line bg-paper-50 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-ink-700">Form #{idx + 1} ({f.input_count} inputs)</span>
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-pine/10 text-pine font-semibold">
                        Submit: &quot;{f.submit_button_text || 'Submit'}&quot;
                      </span>
                    </div>
                    <p className="font-mono text-[11px] text-ink-500 truncate">Page: {f.page_url}</p>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {f.input_types?.map((t, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-paper-100 border border-line text-ink-600 font-mono text-[10px]">
                          type=&quot;{t}&quot;
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <Card className="p-5 space-y-2">
              <h3 className="font-serif text-lg text-ink font-semibold">Form Analysis Summary</h3>
              <p className="text-xs text-ink-600">
                Primary conversion relies on direct links or modal triggers. Keep submission forms under 4 fields to maximize completion rate.
              </p>
            </Card>
          )}

          {/* Actionable Remedies */}
          {formAudit?.actionable_remedies && formAudit.actionable_remedies.length > 0 && (
            <Card className="p-5 space-y-3 border-l-4 border-l-pine">
              <h4 className="text-xs font-bold text-pine uppercase tracking-wider">
                Recommended CRO Form Remedies
              </h4>
              <ul className="text-xs text-ink-700 space-y-1.5 list-disc pl-5">
                {formAudit.actionable_remedies.map((rem, i) => (
                  <li key={i}>{rem}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: 5-SECOND VALUE PROPOSITION CLARITY
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'valueprop' && (
        <div className="space-y-6">
          <Card className="p-6 space-y-4">
            <span className="text-[10px] font-mono uppercase tracking-widest text-pine font-bold block">
              5-Second Value Proposition Test
            </span>
            <blockquote className="font-serif text-2xl text-ink leading-relaxed italic border-l-2 border-pine pl-4">
              &quot;{profile?.value_proposition || 'No explicit value proposition extracted from the homepage.'}&quot;
            </blockquote>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-line text-xs">
              <div className="p-3 rounded bg-paper-50 border border-line space-y-1">
                <span className="label text-[10px] text-ink-500 block">Target Audience</span>
                <p className="font-semibold text-ink text-sm">{profile?.target_audience || 'Commercial Buyers'}</p>
              </div>
              <div className="p-3 rounded bg-paper-50 border border-line space-y-1">
                <span className="label text-[10px] text-ink-500 block">Primary Intent</span>
                <p className="font-semibold text-ink text-sm">{profile?.primary_intent || 'Commercial Consideration'}</p>
              </div>
              <div className="p-3 rounded bg-paper-50 border border-line space-y-1">
                <span className="label text-[10px] text-ink-500 block">Business Model</span>
                <p className="font-semibold text-ink text-sm">{profile?.business_model || 'Enterprise B2B'}</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: CTA & ACTION HIERARCHY
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'cta' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <h3 className="font-serif text-lg text-ink font-semibold">Call to Action (CTA) Audit</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-lg bg-good/5 border border-good/20 space-y-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-good font-bold block">
                  Primary Call to Action
                </span>
                <p className="font-mono text-base font-bold text-ink">
                  &quot;{profile?.primary_cta || 'Get Started'}&quot;
                </p>
                <p className="text-ink-600">
                  Primary high-intent action button above the fold.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-paper-50 border border-line space-y-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 font-bold block">
                  Secondary Call to Action
                </span>
                <p className="font-mono text-base font-bold text-ink">
                  &quot;{profile?.secondary_cta || 'Learn More / Book Demo'}&quot;
                </p>
                <p className="text-ink-600">
                  Low-friction nurture step for uncommitted visitors.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: VISUAL UX INSPECTION
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'visualux' && (
        <VisualUxInspectionView visualUx={report.visual_ux} />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 5: REVENUE & FUNNEL LEAKAGE
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'revenue' && (
        <LifecycleRevenueIntelligenceView
          lifecycleData={report.lifecycle_revenue}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 6: LEAD GEN OPPORTUNITIES
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'leadgen' && (
        <LeadGenOpportunitiesView
          domain={report.domain}
          bizName={profile?.business_name}
          niche={profile?.industry}
          analysisId={analysisId}
        />
      )}
    </PillarShell>
  );
}
