import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ExecutiveReport, Finding } from '../../types';
import { CroIntelligencePanel } from './CroIntelligencePanel';
import { CroAnalyticsDashboard } from './CroAnalyticsDashboard';
import { PillarShell } from '../ui';
import { AiNarrativePanel } from '../ui/AiNarrativePanel';
import { SectionExportButtons } from '../ui/SectionExportButtons';
import {
  CroEnterpriseBundle,
  CroEnterpriseFinding,
  CroWeightedDimension,
  croApi,
} from '../../services/croApi';
import { CroExecutiveDashboard } from './cro/CroExecutiveDashboard';
import { CroJourneyAndPageExplorer } from './cro/CroJourneyAndPageExplorer';
import { CroExperienceCopyFormsView } from './cro/CroExperienceCopyFormsView';
import { CroAnalyticsAndFunnelsView } from './cro/CroAnalyticsAndFunnelsView';
import { CroRemediationExperimentsView } from './cro/CroRemediationExperimentsView';
import { CroMonitoringReportsView } from './cro/CroMonitoringReportsView';

interface CroWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onDeployRemediation?: () => void;
  onSelectFinding?: (f: Finding) => void;
}

type EnterpriseCroTab =
  | 'overview'
  | 'journeys'
  | 'pages'
  | 'copy'
  | 'forms_cta'
  | 'ux_mobile_trust'
  | 'ecommerce'
  | 'analytics_funnels'
  | 'remediation'
  | 'experiments'
  | 'monitoring_reports'
  | 'history_method'
  | 'full_index';

const WEIGHTED_DIM_META: Array<[string, string, number]> = [
  ['conversion_journey', 'Conversion journey and funnel quality', 15],
  ['ux_usability', 'UX and usability', 15],
  ['ui_visual_hierarchy', 'UI and visual hierarchy', 10],
  ['landing_page_match', 'Landing page and message match', 10],
  ['copywriting_value_prop', 'Copywriting and value proposition', 10],
  ['forms_cta', 'Forms and CTA effectiveness', 10],
  ['trust_credibility', 'Trust and credibility', 10],
  ['mobile_accessibility', 'Mobile experience and accessibility', 10],
  ['performance_interaction', 'Performance and interaction quality', 5],
  ['analytics_measurement', 'Analytics and measurement readiness', 5],
];

/** Builds an honest, zero-fabrication canonical bundle from a saved ExecutiveReport before/without a live /api/v1/cro audit. */
export function buildBundleFromExecutiveReport(report: ExecutiveReport, analysisId?: string): CroEnterpriseBundle {
  const croAudit = report.cro_audit;
  const intel = (croAudit?.intelligence || {}) as Record<string, any>;
  const domain = (report.domain || report.website_url || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
  const url = report.website_url || (domain ? `https://${domain}/` : 'https://example.com/');
  const auditId = analysisId || report.analysis_id || report.report_id || 'saved_audit';

  const catCroScore = report.scores?.category_scores?.['UX_CONVERSION']?.score;
  const expScore =
    croAudit?.overall_cro_score != null
      ? Number(croAudit.overall_cro_score)
      : catCroScore != null
      ? Number(catCroScore)
      : null;

  const tenDims: any[] = intel?.ten_dimension_scorecard?.dimensions || [];
  const experienceDims: CroWeightedDimension[] = WEIGHTED_DIM_META.map(([id, name, weight], idx) => {
    const legacy = tenDims[idx];
    const score = typeof legacy?.score === 'number' ? legacy.score : null;
    return {
      dimension_id: id,
      name,
      configured_weight_pct: weight,
      applicable: true,
      executed_checks: score != null ? 1 : 0,
      total_checks: 1,
      score,
      status: score != null ? 'measured' : 'unmeasured',
      evidence_types: legacy?.evidence_class ? [String(legacy.evidence_class).toLowerCase()] : [],
      notes: legacy?.evidence_basis ? [legacy.evidence_basis] : [],
    };
  });

  const activeWeight = experienceDims.reduce((s, d) => s + (d.score != null ? d.configured_weight_pct : 0), 0);

  const findings: CroEnterpriseFinding[] = (report.findings || [])
    .filter((f) => f.category === 'UX_CONVERSION' || (f.category as any) === 'CRO')
    .map((f, idx) => ({
      finding_id: f.finding_id || `CRO-${String(idx + 1).padStart(3, '0')}`,
      category: 'ux_audit',
      subcategory: f.evidence_subtype || 'cro_observation',
      department: 'B',
      agent_id: (f as any).agent_id || 'cro_ai_specialist',
      title: f.title,
      description: (f as any).detailed_diagnosis || f.description,
      root_cause: (f as any).reasoning || f.why_it_matters || 'Observed during site crawl.',
      affected_urls: (f.evidence || []).map((e) => e.url).filter(Boolean) as string[],
      affected_elements: [],
      affected_journeys: [],
      affected_devices: Array.isArray((f as any).affected_devices) ? (f as any).affected_devices : [],
      evidence_ids: f.evidence_refs || [],
      source_type: (f as any).adversarial_reviewed ? 'ai_verified_finding' : 'ai_specialist_observation',
      claim_boundary: f.verification_notes || 'AI-analyzed CRO finding',
      severity: String(f.severity || 'medium').toLowerCase(),
      confidence: typeof f.confidence === 'number' ? f.confidence : null,
      recommendation: f.recommendation,
      implementation_instructions: f.recommendation,
      owner_role: 'Product / Engineering',
      effort: f.effort && f.effort <= 1 ? 'low' : 'medium',
      priority_score: typeof f.priority === 'number' ? Math.round(f.priority * 10) : 70,
      acceptance_criteria: f.validation_criteria ? [f.validation_criteria] : [],
      limitations: [],
      status: 'open',
    }));

  const pages = (report.page_reports || []).map((p: any, i: number) => ({
    page_id: `saved_pg_${i + 1}`,
    url: p.url || url,
    page_type: p.page_type || (i === 0 ? 'homepage' : 'general'),
    business_purpose: 'Audited page from saved crawl',
    conversion_objective: report.business_profile?.primary_cta || 'Primary conversion',
    target_audience: report.business_profile?.target_audience || 'unknown',
    journey_position: i === 0 ? 'entry' : 'evaluation',
    importance: i === 0 ? 'critical' : 'medium',
    http_status: p.status_code ?? null,
    title: p.title,
    h1: Array.isArray(p.h1) ? p.h1[0] : p.h1,
    subheadline: null,
    word_count: p.word_count || 0,
    rendered_dom_verified: !!p.rendered,
    device_coverage: Array.isArray(p.device_coverage) ? p.device_coverage : [],
    functional_test_status: 'not_tested',
    primary_cta: croAudit?.cta_analysis?.hero_cta_text || null,
    cta_count: Array.isArray(p.ctas) ? p.ctas.length : 0,
    forms_count: p.forms_count || 0,
    ux_findings_count: 0,
    ui_findings_count: 0,
    analytics_coverage: 'unmeasured',
    remediation_status: 'open',
    performance_metrics: {},
  }));

  const ctas = (croAudit?.cta_analysis?.ctas || []).map((c: any, idx: number) => ({
    element_id: `cta_${idx}`,
    url: c.page_url,
    text: c.cta_text,
    element_type: c.element_type,
    destination: c.target_url,
    cta_hierarchy: c.placement_zone === 'HERO' ? 'primary' : 'secondary',
    intent_category: c.intent_category.toLowerCase(),
    section: c.placement_zone.toLowerCase(),
    device: 'desktop',
    clickable: typeof c.interaction_test?.passed === 'boolean' ? c.interaction_test.passed : null,
    interaction_result: c.interaction_test?.status || 'not_tested',
  }));

  const formAudit = report.form_audit || croAudit?.form_friction;
  const formsRegistry = (formAudit?.forms || []).map((f: any) => ({
    form_id: f.form_id,
    element_id: f.form_id,
    url: f.page_url,
    field_count: f.input_count,
    required_fields: f.required_fields_count ?? 0,
    missing_labels: f.missing_labels_count,
    validation_state: 'not_tested',
    submission_test_state: 'not_tested',
    qualification_tradeoff_note: 'Review field necessity against sales qualification requirements.',
  }));

  const journeyStages = (intel?.journey_stages || []).map((st: any, idx: number) => ({
    step_id: `st_${idx}`,
    step_order: idx + 1,
    name: st.stage_name || `Step ${idx + 1}`,
    stage: st.stage_id || 'discovery',
    url: st.matched_urls?.[0] || null,
    expected_interaction: 'Progress toward primary conversion goal',
    technical_status: st.status === 'OBSERVED' ? 'observed' : 'not_tested',
    technical_notes: st.status === 'OBSERVED' ? 'Journey stage was observed in the crawl sample; functional success was not established.' : 'Journey stage was not observed in the crawl sample.',
    behavioral_status: 'unmeasured',
    behavioral_metrics: {},
  }));

  return {
    audit: {
      audit_id: auditId,
      domain,
      target_url: url,
      mode: 'standard',
      status: 'completed',
      current_stage: 'completed',
      safe_mode: true,
      analytics_connected: false,
      experience_score: expScore,
      measurement_score: null,
      pages_audited: pages.length,
      findings_count: findings.length,
      critical_findings_count: findings.filter((f) => f.severity === 'critical').length,
      qa_status: 'not_certified',
      methodology_version: 'dristik_cro_v2.0',
      limitations: ['Viewing saved multi-pillar report snapshot. Run Enterprise CRO Audit for full 11-stage DAG persistence and 14-profile PDF publishing.'],
      created_at: report.generated_at || new Date().toISOString(),
    },
    scorecard: {
      audit_id: auditId,
      methodology_version: 'dristik_cro_v2.0',
      experience_score: expScore,
      experience_grade: croAudit?.cro_grade || 'Not calibrated',
      experience_dimensions: experienceDims,
      experience_active_weight_pct: activeWeight,
      measurement_score: null,
      measurement_status: 'unmeasured',
      measurement_checks: [],
      business_performance_status: 'data_unavailable',
      business_performance_metrics: [
        { metric: 'Primary Conversion Rate', formula: 'Unique Converting Visitors / Eligible Unique Visitors * 100', value: null, status: 'data_unavailable' },
        { metric: 'Revenue Per Visitor (RPV)', formula: 'Attributed Revenue / Eligible Unique Visitors', value: null, status: 'data_unavailable' },
        { metric: 'Form Completion Rate', formula: 'Valid Form Submissions / Form Starts * 100', value: null, status: 'data_unavailable' },
      ],
      scope_coverage_pct: null,
      evidence_coverage_pct: null,
      confidence: null,
      analytics_completeness_pct: null,
      disclosures: [
        'CRO Experience Score, Conversion Measurement Score, and Measured Business Performance are kept strictly separate.',
        'Disconnected analytics metrics remain Unavailable (never coerced to zero).',
      ],
    },
    department_artifacts: {
      strategy_summary: {
        business_model: intel?.business_model || report.business_profile?.business_model || 'unknown',
        primary_conversion: report.business_profile?.primary_cta || 'unknown',
      },
      landing_copy_workspace: {
        message_match: { status: 'unmeasured', reason: 'Campaign/search query context not attached to saved audit.' },
        copy_proposals: croAudit?.value_prop?.hero_headline
          ? [
              {
                proposal_id: 'saved_hero_copy',
                page_url: url,
                section: 'hero_headline',
                original_copy: croAudit.value_prop.hero_headline,
                identified_problem: (croAudit.value_prop.observations || [])[0] || 'Evaluate above-the-fold clarity against target audience outcome.',
                recommended_copy: `Clarify your core outcome for ${report.business_profile?.target_audience || 'target customers'} above the fold.`,
                reason_for_change: 'Grounded recommendation awaiting user review and A/B validation.',
                supporting_source_facts: [`Observed headline: ${croAudit.value_prop.hero_headline}`],
                risks_and_assumptions: ['Requires user approval before production update.'],
              },
            ]
          : [],
      },
      forms_cta_workspace: { forms_registry: formsRegistry },
      ecommerce_audit: { applicable: !!intel?.commercial_intelligence?.ecommerce_audit?.is_ecommerce_site, ...(intel?.commercial_intelligence?.ecommerce_audit || {}) },
      ux_mobile_a11y: { wcag_summary: intel?.wcag_cro_accessibility || {} },
      trust_audit: {
        coverage_map: {
          privacy_policy: !!croAudit?.social_proof?.has_privacy_policy,
          terms_of_service: !!croAudit?.social_proof?.has_terms_of_service,
          testimonials_count: croAudit?.social_proof?.total_testimonials ?? 0,
          client_logos: croAudit?.social_proof?.client_logos_detected ?? 0,
        },
      },
      performance_tech: {},
      analytics_intelligence: { is_connected: false, connectors: [] },
    },
    pages,
    journeys: journeyStages.length
      ? [
          {
            journey_id: 'saved_jrn_1',
            name: 'Observed Conversion Journey',
            business_model: String(intel?.business_model || 'unknown'),
            entry_points: [url],
            steps: journeyStages,
            technical_health: 'healthy',
            behavioral_health: 'unmeasured',
            disclosure: 'Crawl identifies functional paths; actual visitor abandonment requires connected analytics.',
          },
        ]
      : [],
    findings,
    ctas,
    forms: formsRegistry,
    funnels: [],
    events: [],
    remediation_pack: {
      pack_id: 'saved_pack',
      executive_summary: `Consolidated view of ${findings.length} CRO finding(s) from saved report.`,
      root_cause_groups: [],
      deliverables: {},
      conflicts_detected: [],
      remaining_risks: [],
      tasks: findings.map((f, idx) => ({
        task_id: `CRO-TASK-${idx + 1}`,
        root_cause_group: f.category,
        title: f.title,
        linked_finding_ids: [f.finding_id],
        affected_urls: f.affected_urls,
        affected_components: [],
        affected_devices: f.affected_devices,
        business_objective: report.business_profile?.primary_cta || 'Primary conversion',
        deliverable_section: 'ux_remediation_plan',
        proposed_change: f.recommendation,
        implementation_instructions: f.implementation_instructions,
        owner: f.owner_role,
        department: 'Engineering',
        dependencies: [],
        conflicting_task_ids: [],
        effort_estimate: f.effort,
        priority: f.severity === 'critical' ? 'P0' : f.severity === 'high' ? 'P1' : 'P2',
        roadmap_window: f.severity === 'critical' || f.severity === 'high' ? 'days_30' : 'days_60',
        approval_status: 'pending',
        acceptance_criteria: f.acceptance_criteria,
        before_evidence: {},
        after_evidence: {},
        verification_status: 'unverified',
        status: 'backlog',
      })),
    },
    remediation_views: null,
    experiments: (intel?.experiment_proposals || []).map((e: any) => ({
      experiment_id: e.experiment_id,
      title: e.title,
      experiment_type: 'ab_test',
      hypothesis_statement: e.hypothesis,
      target_audience: e.target_audience || 'All eligible visitors',
      primary_metric: e.primary_metric,
      guardrail_metrics: e.guardrail_metrics || [],
      baseline_is_measured: false,
      minimum_detectable_effect: (e.minimum_detectable_effect_pct || 0) / 100,
      required_sample_per_variant: e.sample_size_per_variant || 0,
      total_required_sample: e.total_required_sample_size || 0,
      planned_duration_days: e.minimum_duration_days || 0,
      owner: 'Growth Lead',
      approval_status: 'pending',
      status: 'draft',
      variants: [],
      latest_result: null,
    })),
    connectors: [],
    alerts: [],
    schedules: [],
    reports: [],
  };
}

export function CroWorkspaceView({ report, analysisId }: CroWorkspaceViewProps) {
  const [activeTab, setActiveTab] = useState<EnterpriseCroTab>('overview');
  const [liveBundle, setLiveBundle] = useState<CroEnterpriseBundle | null>(null);

  const fallbackBundle = useMemo(
    () => buildBundleFromExecutiveReport(report, analysisId),
    [report, analysisId],
  );
  const bundle = liveBundle || fallbackBundle;
  const domain = bundle.audit.domain;
  const websiteUrl = bundle.audit.target_url;

  const hydrateFromApi = useCallback(
    async (explicitAuditId?: string) => {
      try {
        let targetId = explicitAuditId;
        if (!targetId) {
          const list = await croApi.listAudits(domain);
          targetId = list.items?.[0]?.audit_id;
        }
        const connectorsRes = await croApi.listConnectors().catch(() => ({ connectors: [] }));
        if (!targetId) {
          if (connectorsRes.connectors.length) {
            setLiveBundle((prev) => ({ ...(prev || fallbackBundle), connectors: connectorsRes.connectors }));
          }
          return;
        }
        const [detail, pagesR, journeysR, findingsR, ctasR, formsR, funnelsR, remR, expR, alertsR, schedR] =
          await Promise.all([
            croApi.getAuditDetail(targetId),
            croApi.getPages(targetId),
            croApi.getJourneys(targetId),
            croApi.getFindings(targetId),
            croApi.getCtas(targetId),
            croApi.getForms(targetId),
            croApi.getFunnels(targetId),
            croApi.getRemediation(targetId).catch(() => ({ pack: null, views: null })),
            croApi.listExperiments(targetId).catch(() => ({ items: [] })),
            croApi.listMonitoringAlerts(domain).catch(() => ({ items: [] })),
            croApi.listMonitoringSchedules(domain).catch(() => ({ items: [] })),
          ]);
        const storeFindings = findingsR.items || [];
        const seenFindingIds = new Set(storeFindings.map((f: any) => f.finding_id));
        const mergedFindings = [
          ...storeFindings,
          ...fallbackBundle.findings.filter((f) => !seenFindingIds.has(f.finding_id)),
        ];
        setLiveBundle({
          audit: detail.audit,
          scorecard: detail.scorecard || fallbackBundle.scorecard,
          qa_report: detail.qa_report,
          department_artifacts: detail.department_artifacts || {},
          pages: pagesR.items || [],
          journeys: journeysR.items || [],
          findings: mergedFindings,
          ctas: ctasR.items || [],
          forms: formsR.items || [],
          funnels: funnelsR.items || [],
          events: detail.department_artifacts?.analytics_intelligence?.events || [],
          remediation_pack: remR.pack,
          remediation_views: remR.views,
          experiments: expR.items || [],
          connectors: connectorsRes.connectors || [],
          alerts: alertsR.items || [],
          schedules: schedR.items || [],
          reports: [],
        });
      } catch {
        // Gracefully remain on saved ExecutiveReport bundle if backend CRO audit hasn't been created yet
      }
    },
    [domain, fallbackBundle],
  );

  useEffect(() => {
    hydrateFromApi();
  }, [hydrateFromApi]);

  const croScore = bundle.scorecard.experience_score;
  const croGrade = bundle.scorecard.experience_grade;

  return (
    <PillarShell
      kicker="Enterprise Conversion Intelligence"
      title="Conversion Rate Optimization (CRO)"
      description="Audit business goals, conversion journeys, UX/UI, forms, CTAs, checkout, analytics integrity, consolidated remediation, independent 4-outcome verification, and statistically valid A/B experiments."
      scoreLabel="CRO Experience"
      score={croScore == null ? 'Unmeasured' : `${croScore.toFixed(1)}`}
      metaLabel="Measurement"
      meta={bundle.scorecard.measurement_score == null ? `Grade ${croGrade}` : `${bundle.scorecard.measurement_score}/100`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <SectionExportButtons
            analysisId={analysisId || report.analysis_id || report.report_id}
            sectionKey="cro"
            sectionLabel="CRO"
          />
          {(analysisId || report.analysis_id || report.report_id) && (
            <a
              href={`/api/v1/reports/${analysisId || report.analysis_id || report.report_id}/cro-report?format=pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink"
            >
              CRO Book PDF
            </a>
          )}
        </div>
      }
      tabs={[
        { id: 'overview', label: 'Executive Dashboard' },
        { id: 'journeys', label: `Journeys (${bundle.journeys.length})` },
        { id: 'pages', label: `Page Inspector (${bundle.pages.length})` },
        { id: 'copy', label: 'Landing & Copy' },
        { id: 'forms_cta', label: `Forms & CTAs (${bundle.ctas.length})` },
        { id: 'ux_mobile_trust', label: 'UX · Mobile · Trust · CWV' },
        { id: 'ecommerce', label: 'Ecommerce & Checkout' },
        { id: 'analytics_funnels', label: 'Analytics · Funnels · Connectors' },
        { id: 'remediation', label: `Remediation & Verify (${bundle.remediation_pack?.tasks?.length ?? 0})` },
        { id: 'experiments', label: `Experiments (${bundle.experiments.length})` },
        { id: 'monitoring_reports', label: 'Monitoring & 14 Reports' },
        { id: 'history_method', label: 'History & Methodology' },
        { id: 'full_index', label: '55/65 Section Index' },
      ]}
      activeTab={activeTab}
      onTab={(id) => setActiveTab(id as EnterpriseCroTab)}
    >
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <AiNarrativePanel
            report={report}
            bundleKey="cro_pdf"
            title="CRO Enterprise AI Narrative & Verification"
          />
          <CroExecutiveDashboard
            bundle={bundle}
            domain={domain}
            websiteUrl={websiteUrl}
            onRefreshBundle={hydrateFromApi}
            onNavigateTab={(t) => setActiveTab(t as EnterpriseCroTab)}
          />
        </div>
      )}
      {activeTab === 'journeys' && <CroJourneyAndPageExplorer bundle={bundle} mode="journeys" />}
      {activeTab === 'pages' && <CroJourneyAndPageExplorer bundle={bundle} mode="pages" />}
      {activeTab === 'copy' && <CroExperienceCopyFormsView bundle={bundle} section="copy" />}
      {activeTab === 'forms_cta' && <CroExperienceCopyFormsView bundle={bundle} section="forms_cta" />}
      {activeTab === 'ux_mobile_trust' && <CroExperienceCopyFormsView bundle={bundle} section="ux_mobile_trust" />}
      {activeTab === 'ecommerce' && <CroExperienceCopyFormsView bundle={bundle} section="ecommerce" />}
      {activeTab === 'analytics_funnels' && (
        <CroAnalyticsAndFunnelsView bundle={bundle} onNavigateTab={(t) => setActiveTab(t as EnterpriseCroTab)} />
      )}
      {activeTab === 'remediation' && (
        <CroRemediationExperimentsView bundle={bundle} mode="remediation" onRefreshBundle={hydrateFromApi} />
      )}
      {activeTab === 'experiments' && (
        <CroRemediationExperimentsView bundle={bundle} mode="experiments" onRefreshBundle={hydrateFromApi} />
      )}
      {activeTab === 'monitoring_reports' && (
        <CroMonitoringReportsView
          bundle={bundle}
          domain={domain}
          websiteUrl={websiteUrl}
          onRefreshBundle={hydrateFromApi}
        />
      )}
      {activeTab === 'history_method' && <CroAnalyticsDashboard report={report} analysisId={analysisId} />}
      {activeTab === 'full_index' && <CroIntelligencePanel report={report} analysisId={analysisId} />}
    </PillarShell>
  );
}
