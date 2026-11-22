import { api } from './http';
import { ExecutiveReport } from '../types';

export interface GeoDimensionScore {
  dimension_key: string;
  dimension_name: string;
  scorecard_group: 'observed_performance' | 'readiness_optimization';
  proposed_weight_pct: number;
  score: number | null;
  grade: string;
  status: string;
  numerator?: number | null;
  denominator?: number | null;
  sample_size: number;
  evidence_ids: string[];
  notes: string[];
}

export interface GeoDualScorecard {
  audit_id: string;
  methodology_version: string;
  methodology_disclosure: string;
  observed_performance_score: number | null;
  observed_performance_grade: string;
  observed_performance_status: string;
  observed_metrics: Record<string, any>;
  readiness_score: number | null;
  readiness_grade: string;
  readiness_status: string;
  readiness_metrics: Record<string, any>;
  methodology_composite_score: number | null;
  methodology_composite_grade: string;
  active_weight_pct: number;
  dimensions: GeoDimensionScore[];
  coverage: {
    tested_platforms: string[];
    unconfigured_platforms: string[];
    successful_prompt_executions: number;
    failed_prompt_executions: number;
    total_planned_prompts: number;
    branded_prompts_tested: number;
    non_branded_prompts_tested: number;
    repeat_test_count: number;
    markets_covered: string[];
    languages_covered: string[];
    connector_availability: Record<string, string>;
    data_freshness: string;
    evidence_confidence: number | null;
    methodology_version: string;
  };
}

export interface GeoPlatformRecord {
  platform_id: string;
  display_name: string;
  active_model: string;
  testing_mode: string;
  capabilities?: Record<string, any>;
  prompts_attempted: number;
  prompts_succeeded: number;
  prompts_failed: number;
  mention_count: number;
  recommendation_count: number;
  citation_count: number;
  mention_rate_pct: number | null;
  recommendation_rate_pct: number | null;
  citation_rate_pct: number | null;
  sentiment_breakdown: Record<string, number>;
  accuracy_rate_pct: number | null;
  last_tested_at?: string | null;
  total_cost_usd: number;
  limitations: string[];
  data_quality_state: string;
}

export interface GeoTestPromptRecord {
  prompt_id: string;
  question: string;
  category: string;
  intent: string;
  is_branded: boolean;
  topic: string;
  target_brand: string;
  target_product?: string | null;
  relevant_competitors: string[];
  market: string;
  language: string;
  importance: string;
  testing_rationale: string;
  version: number;
  applicable_platforms: string[];
  repetitions: number;
  approval_status: string;
  quality_flags: string[];
}

export interface GeoResponseRecord {
  response_id: string;
  run_id: string;
  prompt_id: string;
  platform_id: string;
  model_version: string;
  testing_mode: string;
  response_text: string;
  response_hash: string;
  raw_citations: string[];
  extracted_claims: Array<{ sentence: string; sentiment: string; verified_status: string }>;
  sentiment: string;
  brand_positioning: string;
  is_shortlisted: boolean;
  is_comparative: boolean;
  brand_mentioned: boolean;
  brand_recommended: boolean;
  brand_cited: boolean;
  inaccurate_claims_count: number;
  analysis_confidence: number;
}

export interface GeoMentionRecord {
  mention_id: string;
  response_id: string;
  prompt_id: string;
  platform_id: string;
  entity_name: string;
  entity_kind: string;
  is_target_brand: boolean;
  mention_type: string;
  ordinal_position?: number | null;
  sentiment: string;
  context_snippet: string;
  inaccuracy_note?: string | null;
}

export interface GeoCitationRecord {
  citation_id: string;
  response_id: string;
  prompt_id: string;
  platform_id: string;
  cited_url: string;
  domain: string;
  publisher: string;
  source_ownership: string;
  source_category: string;
  associated_claim?: string | null;
  supports_claim: string;
  citation_position: number;
  freshness_status: string;
  competitors_associated: string[];
  url_valid: boolean;
}

export interface GeoEntityRecord {
  entity_id: string;
  entity_type: string;
  entity_name: string;
  attribute: string;
  value: any;
  source: string;
  source_url?: string | null;
  source_ownership: string;
  confidence: number;
  last_verified?: string | null;
  fact_status: string;
  approved_by?: string | null;
  approved_at?: string | null;
  locked_from_ai_overwrite: boolean;
}

export interface GeoExternalSourceRecord {
  source_id: string;
  domain: string;
  url?: string | null;
  publisher: string;
  title: string;
  subject: string;
  source_category: string;
  is_independent: boolean;
  cited_in_ai_responses: boolean;
  citation_count: number;
  cites_competitors: boolean;
  competitors_present: string[];
  brand_present: boolean;
  evidence_of_relevance: string;
  potential_contribution: string;
  outreach_strategy: string;
  restrictions_and_risks: string;
  opportunity_status: string;
  discovery_date: string;
}

export interface GeoPageRecord {
  page_id: string;
  url: string;
  page_type: string;
  http_status?: number | null;
  title: string;
  main_topic: string;
  relevant_audience: string;
  word_count: number;
  clarity_score?: number | null;
  completeness_score?: number | null;
  extractability_score?: number | null;
  freshness_score?: number | null;
  trust_score?: number | null;
  overall_readiness_score?: number | null;
  entity_coverage: string[];
  schema_types: string[];
  missing_questions: string[];
  content_issues: string[];
  recommendations: string[];
  extracted_text_preview: string;
}

export interface GeoFindingRecord {
  finding_id: string;
  category: string;
  department: string;
  agent_id: string;
  title: string;
  description: string;
  root_cause: string;
  root_cause_group: string;
  affected_entities: string[];
  affected_urls: string[];
  affected_prompts: string[];
  affected_platforms: string[];
  competitor_references: string[];
  evidence_ids: string[];
  severity: string;
  confidence?: number | null;
  business_impact?: string | null;
  recommendation: string;
  acceptance_criteria: string[];
  limitations: string[];
  is_hypothesis: boolean;
  status: string;
}

export interface GeoRemediationTaskRecord {
  task_id: string;
  finding_ids: string[];
  title: string;
  root_cause: string;
  deliverable_section: string;
  affected_pages: string[];
  affected_prompts: string[];
  affected_platforms: string[];
  affected_entities: string[];
  proposed_change: string;
  implementation_instructions: string;
  code_or_copy_patch?: string | null;
  owner: string;
  department: string;
  dependencies: string[];
  effort: string;
  priority: string;
  risk: string;
  approval_status: string;
  approved_by?: string | null;
  status: string;
  deployment_ref?: string | null;
  deployed_by?: string | null;
  acceptance_criteria: string[];
  before_evidence: Record<string, any>;
  after_evidence: Record<string, any>;
  verification_id?: string | null;
  implementation_verified?: boolean | null;
  outcome_improved?: string | null;
}

export interface GeoEnterpriseBundle {
  is_live_geo_audit: boolean;
  audit: {
    audit_id: string;
    domain: string;
    website_url: string;
    brand_name: string;
    mode: string;
    status: string;
    publication_status: string;
    current_stage: string;
    observed_performance_score: number | null;
    readiness_score: number | null;
    methodology_composite_score: number | null;
    qa_status: string;
    budget_usd: number;
    spent_usd: number;
    budget_paused: boolean;
    platforms_configured: string[];
    platforms_tested: string[];
    platforms_unconfigured: string[];
    prompts_planned: number;
    prompts_executed: number;
    prompts_succeeded: number;
    prompts_failed: number;
    limitations: string[];
    methodology_version: string;
    created_at: string;
    completed_at?: string | null;
  };
  scope: Record<string, any>;
  platforms: GeoPlatformRecord[];
  model_versions: Array<Record<string, any>>;
  prompts: GeoTestPromptRecord[];
  runs: Array<Record<string, any>>;
  responses: GeoResponseRecord[];
  mentions: GeoMentionRecord[];
  citations: GeoCitationRecord[];
  entities: GeoEntityRecord[];
  external_sources: GeoExternalSourceRecord[];
  pages: GeoPageRecord[];
  findings: GeoFindingRecord[];
  recommendations: Array<Record<string, any>>;
  remediation_pack: {
    pack_id?: string;
    executive_summary?: string;
    root_cause_groups?: Array<Record<string, any>>;
    deliverables?: Record<string, any>;
    department_packages?: Record<string, string[]>;
    dependency_edges?: Array<{ from: string; to: string; reason: string }>;
    conflict_notes?: Array<Record<string, any>>;
    tasks?: GeoRemediationTaskRecord[];
    remaining_risks?: Array<Record<string, any>>;
  };
  verifications: Array<Record<string, any>>;
  experiments: Array<Record<string, any>>;
  snapshots: Array<Record<string, any>>;
  scorecard: GeoDualScorecard;
  citation_graph: Record<string, any>;
  department_artifacts: Record<string, any>;
  qa_report: Record<string, any>;
  prompt_coverage: Record<string, any>;
  connector_statuses?: Array<Record<string, any>>;
  external_connectors?: Array<Record<string, any>>;
  capability_matrix?: Array<Record<string, any>>;
  report_profiles?: Record<string, { title: string; audience: string }>;
  monitoring_schedules?: Array<Record<string, any>>;
  monitoring_alerts?: Array<Record<string, any>>;
  monitoring_history?: Array<Record<string, any>>;
}

export const GEO_DEFAULT_REPORT_PROFILES: Record<string, { title: string; audience: string }> = {
  executive_brief: { title: 'GEO Executive Brief', audience: 'CEO, CMO, Leadership' },
  complete_audit_book: { title: 'Complete GEO Audit Book', audience: 'Enterprise Clients' },
  ai_visibility: { title: 'AI Visibility Report', audience: 'Brand and Marketing Teams' },
  citation_intelligence: { title: 'Citation Intelligence Report', audience: 'Content and Authority Teams' },
  brand_entity: { title: 'Brand Entity Report', audience: 'Brand and Communications Teams' },
  content_improvement: { title: 'GEO Content Improvement Plan', audience: 'Content Teams' },
  competitive_intelligence: { title: 'GEO Competitive Intelligence Report', audience: 'Strategy Teams' },
  remediation_pack: { title: 'GEO Remediation Pack', audience: 'Developers and Implementation Teams' },
  verification_report: { title: 'GEO Verification Report', audience: 'Project Owners and Management' },
  evidence_appendix: { title: 'GEO Evidence Appendix', audience: 'Technical and Compliance Reviewers' },
};

export const geoApi = {
  createAudit: (payload: Record<string, any>) =>
    api<{ audit: GeoEnterpriseBundle['audit']; scorecard: GeoDualScorecard }>('/api/v1/geo/audits', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listAudits: (domain?: string) =>
    api<{ audits: GeoEnterpriseBundle['audit'][] }>(
      `/api/v1/geo/audits${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
    ),
  getBundle: (auditId: string) =>
    api<GeoEnterpriseBundle>(`/api/v1/geo/audits/${encodeURIComponent(auditId)}/bundle`),
  generatePrompts: (payload: Record<string, any>) =>
    api<{ prompts: GeoTestPromptRecord[]; count: number }>('/api/v1/geo/prompts/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  validatePrompt: (payload: Record<string, any>) =>
    api<{ valid: boolean; quality_flags: string[] }>('/api/v1/geo/prompts/validate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  approvePrompt: (payload: Record<string, any>) =>
    api<{ prompt: GeoTestPromptRecord }>('/api/v1/geo/prompts/approve', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  runPromptLab: (payload: Record<string, any>) =>
    api<{ prompt: string; pii_redacted: string[]; results: Array<Record<string, any>> }>('/api/v1/geo/prompts/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  approveEntity: (payload: Record<string, any>) =>
    api<{ entity: GeoEntityRecord }>('/api/v1/geo/entities/approve', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  connectPlatform: (payload: Record<string, any>) =>
    api<{ connection: Record<string, any> }>('/api/v1/geo/platforms/connections', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  testPlatform: (platformId: string) =>
    api<Record<string, any>>('/api/v1/geo/platforms/test', {
      method: 'POST',
      body: JSON.stringify({ platform_id: platformId }),
    }),
  updateTaskStatus: (taskId: string, status: string, owner?: string) =>
    api<{ task: GeoRemediationTaskRecord }>(`/api/v1/geo/remediation/tasks/${encodeURIComponent(taskId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, owner }),
    }),
  approveTask: (taskId: string) =>
    api<{ task: GeoRemediationTaskRecord }>(`/api/v1/geo/remediation/tasks/${encodeURIComponent(taskId)}/approve`, {
      method: 'POST',
    }),
  deployTask: (taskId: string, deploymentRef: string) =>
    api<{ task: GeoRemediationTaskRecord }>(`/api/v1/geo/remediation/tasks/${encodeURIComponent(taskId)}/deploy`, {
      method: 'POST',
      body: JSON.stringify({ deployment_ref: deploymentRef }),
    }),
  verifyTask: (taskId: string, payload: Record<string, any>) =>
    api<{ task: GeoRemediationTaskRecord; verification: Record<string, any> }>(
      `/api/v1/geo/remediation/tasks/${encodeURIComponent(taskId)}/verify`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),
  createExperiment: (payload: Record<string, any>) =>
    api<{ experiment: Record<string, any> }>('/api/v1/geo/experiments/create', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  recordExperimentResults: (experimentId: string, payload: Record<string, any>) =>
    api<{ experiment: Record<string, any> }>(`/api/v1/geo/experiments/${encodeURIComponent(experimentId)}/results`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createSchedule: (payload: Record<string, any>) =>
    api<{ schedule: Record<string, any> }>('/api/v1/geo/monitoring/schedules', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  generateReport: (auditId: string, profile: string, format: 'html' | 'json' | 'pdf') =>
    api<{ report: Record<string, any>; byte_size: number }>('/api/v1/geo/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ audit_id: auditId, profile, format }),
    }),
  reportDownloadUrl: (reportId: string) => `/api/v1/geo/reports/${encodeURIComponent(reportId)}/download`,
};

/** Honest zero-fabrication adapter from saved ExecutiveReport when no standalone /api/v1/geo audit exists yet. */
export function buildGeoBundleFromExecutiveReport(report: ExecutiveReport, analysisId?: string): GeoEnterpriseBundle {
  const domain = (report.domain || report.website_url || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
  const brand = report.business_profile?.business_name || domain.split('.')[0] || 'Brand';
  const vCard = report.ai_visibility_scorecard;
  const measured = vCard?.status === 'MEASURED';
  const readinessVal = report.geo_readiness?.extractability_score ?? report.scores?.category_scores?.['GEO']?.score ?? null;
  const auditId = analysisId || report.analysis_id || report.report_id || 'saved_geo';
  const obsRecords = (vCard?.observatory_records || []) as Array<Record<string, any>>;

  const platforms: GeoPlatformRecord[] = [
    { id: 'chatgpt', name: 'ChatGPT (OpenAI)' },
    { id: 'gemini', name: 'Google Gemini' },
    { id: 'claude', name: 'Claude (Anthropic)' },
    { id: 'perplexity', name: 'Perplexity Pro' },
    { id: 'grok', name: 'Grok (xAI)' },
    { id: 'copilot', name: 'Microsoft Copilot' },
    { id: 'deepseek', name: 'DeepSeek' },
  ].map(({ id, name }) => {
    const recs = obsRecords.filter((r) => String(r.engine_id || r.engine || '').toLowerCase().includes(id));
    const n = recs.length;
    const mCount = recs.filter((r) => r.brand_mentioned).length;
    const cCount = recs.filter((r) => r.brand_cited).length;
    const recCount = recs.filter((r) => r.position_prominence === 'PRIMARY_RECOMMENDATION').length;
    return {
      platform_id: id,
      display_name: name,
      active_model: recs[0]?.model_version || 'Not configured',
      testing_mode: id === 'perplexity' ? 'API_WITH_SEARCH' : 'API_MODEL_ONLY',
      prompts_attempted: n,
      prompts_succeeded: n,
      prompts_failed: 0,
      mention_count: mCount,
      recommendation_count: recCount,
      citation_count: cCount,
      mention_rate_pct: n > 0 ? Math.round((mCount / n) * 1000) / 10 : null,
      recommendation_rate_pct: n > 0 ? Math.round((recCount / n) * 1000) / 10 : null,
      citation_rate_pct: n > 0 ? Math.round((cCount / n) * 1000) / 10 : null,
      sentiment_breakdown: {},
      accuracy_rate_pct: null,
      last_tested_at: recs[0]?.timestamp || null,
      total_cost_usd: 0,
      limitations: n === 0 ? ['Platform not queried in this saved audit; run Enterprise GEO Audit with credentials.'] : [],
      data_quality_state: n > 0 ? 'OBSERVED' : 'NOT_CONFIGURED',
    };
  });

  const findings: GeoFindingRecord[] = (report.findings || [])
    .filter((f) => ['GEO', 'AI_SEARCH', 'SCHEMA', 'CONTENT'].includes(String(f.category || '').toUpperCase()))
    .slice(0, 20)
    .map((f, idx) => ({
      finding_id: f.finding_id || `GEO-${String(idx + 1).padStart(3, '0')}`,
      category: String(f.category || 'content_quality').toLowerCase(),
      department: 'D',
      agent_id: 'saved_geo_audit',
      title: f.title,
      description: f.description,
      root_cause: f.why_it_matters || 'Observed in crawl audit.',
      root_cause_group: 'saved_audit_observation',
      affected_entities: [brand],
      affected_urls: (f.evidence || []).map((e) => e.url).filter(Boolean) as string[],
      affected_prompts: [],
      affected_platforms: [],
      competitor_references: [],
      evidence_ids: f.evidence_refs || [],
      severity: String(f.severity || 'medium').toLowerCase(),
      confidence: 0.8,
      business_impact: f.why_it_matters || '',
      recommendation: f.recommendation,
      acceptance_criteria: f.validation_criteria ? [f.validation_criteria] : [],
      limitations: [],
      is_hypothesis: false,
      status: 'open',
    }));

  const dimensions: GeoDimensionScore[] = [
    { dimension_key: 'measured_ai_visibility', dimension_name: 'Measured AI visibility', scorecard_group: 'observed_performance', proposed_weight_pct: 20, score: measured ? (vCard?.mention_rate_pct ?? null) : null, grade: measured ? 'B' : 'Unmeasured', status: measured ? 'OBSERVED' : 'NOT_CONFIGURED', sample_size: vCard?.successful_runs || 0, evidence_ids: [], notes: [] },
    { dimension_key: 'citation_visibility_quality', dimension_name: 'Citation visibility and quality', scorecard_group: 'observed_performance', proposed_weight_pct: 20, score: measured ? (vCard?.citation_rate_pct ?? null) : null, grade: measured ? 'C' : 'Unmeasured', status: measured ? 'OBSERVED' : 'NOT_CONFIGURED', sample_size: vCard?.successful_runs || 0, evidence_ids: [], notes: [] },
    { dimension_key: 'brand_entity_consistency', dimension_name: 'Brand entity consistency', scorecard_group: 'readiness_optimization', proposed_weight_pct: 15, score: readinessVal != null ? Math.round(readinessVal) : null, grade: readinessVal != null ? 'B' : 'Unmeasured', status: readinessVal != null ? 'OBSERVED' : 'NOT_TESTED', sample_size: (report.page_reports || []).length, evidence_ids: [], notes: [] },
    { dimension_key: 'content_information_quality', dimension_name: 'Content and information quality', scorecard_group: 'readiness_optimization', proposed_weight_pct: 15, score: readinessVal != null ? Math.round(readinessVal) : null, grade: readinessVal != null ? 'B' : 'Unmeasured', status: readinessVal != null ? 'OBSERVED' : 'NOT_TESTED', sample_size: (report.page_reports || []).length, evidence_ids: [], notes: [] },
    { dimension_key: 'external_reputation_coverage', dimension_name: 'External reputation and source coverage', scorecard_group: 'readiness_optimization', proposed_weight_pct: 15, score: null, grade: 'Unmeasured', status: 'NOT_TESTED', sample_size: 0, evidence_ids: [], notes: [] },
    { dimension_key: 'competitive_positioning_coverage', dimension_name: 'Competitive positioning and coverage', scorecard_group: 'observed_performance', proposed_weight_pct: 10, score: null, grade: 'Unmeasured', status: 'NOT_CONFIGURED', sample_size: 0, evidence_ids: [], notes: [] },
    { dimension_key: 'technical_retrieval_readiness', dimension_name: 'Technical and retrieval readiness', scorecard_group: 'readiness_optimization', proposed_weight_pct: 5, score: report.per_engine_geo?.ai_bot_directives?.robots_measured ? 85 : null, grade: report.per_engine_geo?.ai_bot_directives?.robots_measured ? 'A' : 'Unmeasured', status: report.per_engine_geo?.ai_bot_directives?.robots_measured ? 'OBSERVED' : 'NOT_TESTED', sample_size: (report.page_reports || []).length, evidence_ids: [], notes: [] },
  ];

  const responses: GeoResponseRecord[] = obsRecords.map((r, i) => ({
    response_id: r.record_id || `obs_${i}`,
    run_id: r.record_id || `run_${i}`,
    prompt_id: r.query_id || `q_${i}`,
    platform_id: r.engine_id || 'unknown',
    model_version: r.model_version || 'unknown',
    testing_mode: 'API_MODEL_ONLY',
    response_text: r.verbatim_answer || '',
    response_hash: '',
    raw_citations: r.cited_url ? [r.cited_url] : [],
    extracted_claims: [],
    sentiment: String(r.sentiment_framing || 'neutral').toLowerCase(),
    brand_positioning: r.position_prominence || 'ABSENT',
    is_shortlisted: r.position_prominence === 'LISTED_OPTION' || r.position_prominence === 'PRIMARY_RECOMMENDATION',
    is_comparative: false,
    brand_mentioned: Boolean(r.brand_mentioned),
    brand_recommended: r.position_prominence === 'PRIMARY_RECOMMENDATION',
    brand_cited: Boolean(r.brand_cited),
    inaccurate_claims_count: r.claim_accuracy === 'HALLUCINATED' ? 1 : 0,
    analysis_confidence: 0.85,
  }));

  const pages: GeoPageRecord[] = (report.page_reports || []).map((p: any, idx: number) => ({
    page_id: `pg_${idx + 1}`,
    url: p.url || `https://${domain}/`,
    page_type: p.page_type || (idx === 0 ? 'homepage' : 'general'),
    http_status: p.status_code ?? 200,
    title: p.title || '',
    main_topic: (Array.isArray(p.h1) ? p.h1[0] : p.h1) || p.title || '',
    relevant_audience: report.business_profile?.target_audience || 'Evaluators',
    word_count: p.word_count || 0,
    overall_readiness_score: readinessVal != null ? Math.round(readinessVal) : null,
    entity_coverage: [brand],
    schema_types: p.schema_types || [],
    missing_questions: [],
    content_issues: [],
    recommendations: [],
    extracted_text_preview: (p.body_text || '').slice(0, 350),
  }));

  return {
    is_live_geo_audit: false,
    audit: {
      audit_id: auditId,
      domain,
      website_url: report.website_url || `https://${domain}/`,
      brand_name: brand,
      mode: 'saved_snapshot',
      status: measured ? 'completed' : 'partial',
      publication_status: measured ? 'READY_TO_PUBLISH' : 'PARTIAL',
      current_stage: 'completed',
      observed_performance_score: measured ? (vCard?.mention_rate_pct ?? null) : null,
      readiness_score: readinessVal != null ? Math.round(readinessVal * 10) / 10 : null,
      methodology_composite_score: null,
      qa_status: measured ? 'passed' : 'partial',
      budget_usd: 5.0,
      spent_usd: 0,
      budget_paused: false,
      platforms_configured: vCard?.engines_queried || [],
      platforms_tested: vCard?.engines_queried || [],
      platforms_unconfigured: platforms.filter((p) => p.prompts_succeeded === 0).map((p) => p.platform_id),
      prompts_planned: (report.ai_search_matrix || []).length,
      prompts_executed: vCard?.successful_runs || 0,
      prompts_succeeded: vCard?.successful_runs || 0,
      prompts_failed: vCard?.failed_runs || 0,
      limitations: [
        'Viewing hydrated snapshot from saved ExecutiveReport. Launch an Enterprise GEO Audit to run the full 9-department DAG, consolidated remediation pack, and 10-profile PDF engine.',
      ],
      methodology_version: 'geo-enterprise-v1.0',
      created_at: report.generated_at || new Date().toISOString(),
    },
    scope: {
      domain,
      brand_name: brand,
      industry: report.business_profile?.industry || '',
      products: report.business_profile?.products || [],
      services: report.business_profile?.services || [],
      competitors: report.business_profile?.competitors || [],
      markets: ['US'],
      languages: ['en'],
    },
    platforms,
    model_versions: [],
    prompts: (report.ai_search_matrix || []).map((q, i) => ({
      prompt_id: `saved_p_${i + 1}`,
      question: q.query,
      category: String(q.question_type || 'category_discovery').toLowerCase(),
      intent: 'commercial',
      is_branded: q.query.toLowerCase().includes(brand.toLowerCase()),
      topic: String(q.question_type || 'general'),
      target_brand: brand,
      relevant_competitors: report.business_profile?.competitors || [],
      market: 'US',
      language: 'en',
      importance: 'medium',
      testing_rationale: 'Hydrated from saved query matrix.',
      version: 1,
      applicable_platforms: ['chatgpt', 'gemini', 'claude', 'perplexity'],
      repetitions: 1,
      approval_status: 'approved',
      quality_flags: [],
    })),
    runs: [],
    responses,
    mentions: [],
    citations: [],
    entities: [
      {
        entity_id: 'saved_ent_brand',
        entity_type: 'brand',
        entity_name: brand,
        attribute: 'official_name',
        value: brand,
        source: 'website_crawl',
        source_url: report.website_url,
        source_ownership: 'owned',
        confidence: 0.95,
        fact_status: 'confirmed',
        locked_from_ai_overwrite: true,
      },
    ],
    external_sources: [],
    pages,
    findings,
    recommendations: [],
    remediation_pack: { tasks: [], remaining_risks: [] },
    verifications: [],
    experiments: [],
    snapshots: [],
    scorecard: {
      audit_id: auditId,
      methodology_version: 'geo-enterprise-v1.0',
      methodology_disclosure:
        'Observed GEO Performance and GEO Readiness & Optimization are strictly separated. Missing provider credentials remain unmeasured (never 0%).',
      observed_performance_score: measured ? (vCard?.mention_rate_pct ?? null) : null,
      observed_performance_grade:
        measured && typeof vCard?.mention_rate_pct === 'number'
          ? (vCard.mention_rate_pct >= 93 ? 'A+' : vCard.mention_rate_pct >= 85 ? 'A' : vCard.mention_rate_pct >= 75 ? 'B' : vCard.mention_rate_pct >= 65 ? 'C' : vCard.mention_rate_pct >= 50 ? 'D' : 'F')
          : 'Unmeasured',
      observed_performance_status: measured ? 'OBSERVED' : 'NOT_CONFIGURED',
      observed_metrics: {
        brand_mention_rate_pct: measured ? vCard?.mention_rate_pct ?? null : null,
        recommendation_rate_pct: null,
        citation_observation_rate_pct: measured ? vCard?.citation_rate_pct ?? null : null,
        total_citations_observed: 0,
      },
      readiness_score: readinessVal != null ? Math.round(readinessVal * 10) / 10 : null,
      readiness_grade:
        readinessVal != null
          ? (readinessVal >= 93 ? 'A+' : readinessVal >= 85 ? 'A' : readinessVal >= 75 ? 'B' : readinessVal >= 65 ? 'C' : readinessVal >= 50 ? 'D' : 'F')
          : 'Unmeasured',
      readiness_status: readinessVal != null ? 'OBSERVED' : 'NOT_TESTED',
      readiness_metrics: { pages_analyzed: pages.length },
      methodology_composite_score: null,
      methodology_composite_grade: 'Unmeasured',
      active_weight_pct: readinessVal != null ? 35 : 0,
      dimensions,
      coverage: {
        tested_platforms: vCard?.engines_queried || [],
        unconfigured_platforms: platforms.filter((p) => p.prompts_succeeded === 0).map((p) => p.platform_id),
        successful_prompt_executions: vCard?.successful_runs || 0,
        failed_prompt_executions: vCard?.failed_runs || 0,
        total_planned_prompts: (report.ai_search_matrix || []).length,
        branded_prompts_tested: 0,
        non_branded_prompts_tested: 0,
        repeat_test_count: vCard?.repeats || 1,
        markets_covered: ['US'],
        languages_covered: ['en'],
        connector_availability: {},
        data_freshness: report.generated_at || new Date().toISOString(),
        evidence_confidence: measured ? 0.85 : 0.7,
        methodology_version: 'geo-enterprise-v1.0',
      },
    },
    citation_graph: { status: 'NOT_OBSERVED', nodes: [], edges: [], top_domains: [], opportunities: [] },
    department_artifacts: {},
    qa_report: { qa_status: measured ? 'passed' : 'partial', publication_status: measured ? 'READY_TO_PUBLISH' : 'PARTIAL', checks: [] },
    prompt_coverage: {},
    report_profiles: GEO_DEFAULT_REPORT_PROFILES,
  };
}
