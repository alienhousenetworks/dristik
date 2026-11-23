import { api } from './http';

export interface CroWeightedDimension {
  dimension_id: string;
  name: string;
  configured_weight_pct: number;
  effective_weight_pct?: number | null;
  applicable: boolean;
  executed_checks: number;
  total_checks: number;
  score: number | null;
  status: string;
  evidence_types: string[];
  notes: string[];
}

export interface CroThreeScorecard {
  audit_id: string;
  methodology_version: string;
  experience_score: number | null;
  experience_grade: string;
  experience_dimensions: CroWeightedDimension[];
  experience_active_weight_pct: number;
  measurement_score: number | null;
  measurement_status: string;
  measurement_checks: Array<{ check: string; status: string; detail: string }>;
  business_performance_status: string;
  business_performance_metrics: Array<{
    metric: string;
    formula: string;
    counting_unit?: string;
    value: number | null;
    unit?: string;
    status: string;
    source?: string;
    date_range?: string | null;
  }>;
  scope_coverage_pct?: number | null;
  test_coverage_pct?: number | null;
  evidence_coverage_pct?: number | null;
  confidence?: number | null;
  data_freshness?: string;
  analytics_completeness_pct?: number | null;
  disclosures: string[];
}

export interface CroAuditRecord {
  audit_id: string;
  domain: string;
  target_url: string;
  profile_id?: string | null;
  mode: string;
  status: string;
  current_stage: string;
  safe_mode: boolean;
  analytics_connected: boolean;
  experience_score: number | null;
  measurement_score: number | null;
  pages_audited: number;
  findings_count: number;
  critical_findings_count: number;
  qa_status: string;
  methodology_version: string;
  limitations: string[];
  created_at: string;
  completed_at?: string | null;
}

export interface CroEnterpriseFinding {
  finding_id: string;
  category: string;
  subcategory: string;
  department: string;
  agent_id: string;
  title: string;
  description: string;
  root_cause: string;
  root_cause_group_id?: string | null;
  affected_urls: string[];
  affected_elements: string[];
  affected_journeys: string[];
  affected_devices: string[];
  evidence_ids: string[];
  source_type: string;
  claim_boundary: string;
  severity: string;
  confidence?: number | null;
  recommendation: string;
  implementation_instructions: string;
  owner_role: string;
  effort: string;
  priority_score: number;
  acceptance_criteria: string[];
  limitations: string[];
  status: string;
}

export interface CroJourneyStepRecord {
  step_id: string;
  step_order: number;
  name: string;
  stage: string;
  url?: string | null;
  expected_interaction: string;
  analytics_event_name?: string | null;
  technical_status: string;
  technical_notes: string;
  behavioral_status: string;
  behavioral_metrics: Record<string, any>;
}

export interface CroJourneyRecord {
  journey_id: string;
  name: string;
  business_model: string;
  entry_points: string[];
  steps: CroJourneyStepRecord[];
  technical_health: string;
  behavioral_health: string;
  measured_completion_rate?: number | null;
  disclosure: string;
}

export interface CroPageRecord {
  page_id: string;
  url: string;
  page_type: string;
  business_purpose: string;
  conversion_objective: string;
  target_audience: string;
  journey_position: string;
  importance: string;
  http_status?: number | null;
  title?: string | null;
  h1?: string | null;
  subheadline?: string | null;
  word_count: number;
  rendered_dom_verified: boolean;
  device_coverage: string[];
  functional_test_status: string;
  primary_cta?: string | null;
  cta_count: number;
  forms_count: number;
  ux_findings_count: number;
  ui_findings_count: number;
  analytics_coverage: string;
  remediation_status: string;
  performance_metrics: Record<string, any>;
}

export interface CroRemediationTaskRecord {
  task_id: string;
  root_cause_group: string;
  title: string;
  linked_finding_ids: string[];
  affected_urls: string[];
  affected_components: string[];
  affected_devices: string[];
  business_objective: string;
  deliverable_section: string;
  proposed_change: string;
  original_copy_or_design?: string | null;
  updated_copy_or_design?: string | null;
  implementation_instructions: string;
  owner: string;
  department: string;
  dependencies: string[];
  conflicting_task_ids: string[];
  effort_estimate: string;
  priority: string;
  roadmap_window: string;
  due_date?: string | null;
  approval_status: string;
  deployment_ref?: string | null;
  acceptance_criteria: string[];
  before_evidence: Record<string, any>;
  after_evidence: Record<string, any>;
  verification_status: string;
  status: string;
}

export interface CroExperimentRecord {
  experiment_id: string;
  title: string;
  experiment_type: string;
  hypothesis_statement: string;
  target_audience: string;
  primary_metric: string;
  guardrail_metrics: string[];
  baseline_rate_input?: number | null;
  baseline_is_measured: boolean;
  minimum_detectable_effect: number;
  required_sample_per_variant: number;
  total_required_sample: number;
  planned_duration_days: number;
  owner: string;
  approval_status: string;
  status: string;
  variants: Array<{ variant_id: string; name: string; is_control: boolean; traffic_allocation_pct: number; description: string }>;
  latest_result?: {
    decision: string;
    decision_rationale: string;
    control_rate?: number | null;
    variant_rate?: number | null;
    relative_lift?: number | null;
    p_value?: number | null;
    adjusted_p_value?: number | null;
    srm_p_value?: number | null;
    srm_detected: boolean;
    peeking_warning: boolean;
    guardrail_breached: boolean;
    confidence_interval_95?: number[] | null;
  } | null;
}

export interface CroConnectorRecord {
  connector_id: string;
  provider: string;
  category: string;
  priority_tier: number;
  connection_status: string;
  supported_data: string[];
  available_capabilities: string[];
  unsupported_or_limited: string[];
  auth_status: string;
}

export interface CroEnterpriseBundle {
  audit: CroAuditRecord;
  scorecard: CroThreeScorecard;
  qa_report?: Record<string, any> | null;
  department_artifacts: Record<string, any>;
  pages: CroPageRecord[];
  journeys: CroJourneyRecord[];
  findings: CroEnterpriseFinding[];
  ctas: any[];
  forms: any[];
  funnels: any[];
  events: any[];
  remediation_pack?: {
    pack_id: string;
    executive_summary: string;
    root_cause_groups: any[];
    deliverables: Record<string, any>;
    conflicts_detected: any[];
    remaining_risks: any[];
    tasks: CroRemediationTaskRecord[];
  } | null;
  remediation_views?: Record<string, any> | null;
  experiments: CroExperimentRecord[];
  connectors: CroConnectorRecord[];
  alerts: any[];
  schedules: any[];
  reports: any[];
}

export const croApi = {
  listAudits: (domain?: string) =>
    api<{ items: CroAuditRecord[]; count: number }>(
      `/api/v1/cro/audits${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
      {},
      'Failed to list CRO audits',
    ),

  createAudit: (payload: {
    target_url: string;
    mode?: string;
    business_config?: Record<string, any>;
    safe_mode?: boolean;
    use_live_browser?: boolean;
  }) =>
    api<{ audit: CroAuditRecord; scorecard: CroThreeScorecard }>(
      '/api/v1/cro/audits',
      { method: 'POST', body: JSON.stringify(payload) },
      'Failed to start CRO audit',
    ),

  getAuditDetail: (auditId: string) =>
    api<any>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}`, {}, 'Failed to load CRO audit'),

  getPages: (auditId: string) =>
    api<{ items: CroPageRecord[] }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/pages`, {}, 'Failed to load CRO pages'),

  getJourneys: (auditId: string) =>
    api<{ items: CroJourneyRecord[] }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/journeys`, {}, 'Failed to load CRO journeys'),

  getFindings: (auditId: string) =>
    api<{ items: CroEnterpriseFinding[] }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/findings`, {}, 'Failed to load CRO findings'),

  getCtas: (auditId: string) =>
    api<{ items: any[] }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/ctas`, {}, 'Failed to load CRO CTAs'),

  getForms: (auditId: string) =>
    api<{ items: any[]; registry: any[] }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/forms`, {}, 'Failed to load CRO forms'),

  getFunnels: (auditId: string) =>
    api<{ items: any[] }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/funnels`, {}, 'Failed to load CRO funnels'),

  getRemediation: (auditId: string) =>
    api<{ pack: any; views: any }>(`/api/v1/cro/audits/${encodeURIComponent(auditId)}/remediation`, {}, 'Failed to load CRO remediation'),

  approveTask: (taskId: string) =>
    api<CroRemediationTaskRecord>(`/api/v1/cro/remediation/tasks/${encodeURIComponent(taskId)}/approve`, { method: 'POST' }, 'Failed to approve task'),

  deployTask: (taskId: string, deployment_ref: string) =>
    api<CroRemediationTaskRecord>(
      `/api/v1/cro/remediation/tasks/${encodeURIComponent(taskId)}/deploy`,
      { method: 'POST', body: JSON.stringify({ deployment_ref }) },
      'Failed to mark task deployed',
    ),

  verifyTask: (taskId: string, payload: Record<string, any>) =>
    api<any>(
      `/api/v1/cro/remediation/tasks/${encodeURIComponent(taskId)}/verify`,
      { method: 'POST', body: JSON.stringify(payload) },
      'Failed to verify task',
    ),

  listExperiments: (auditId?: string) =>
    api<{ items: CroExperimentRecord[] }>(
      `/api/v1/cro/experiments${auditId ? `?audit_id=${encodeURIComponent(auditId)}` : ''}`,
      {},
      'Failed to load CRO experiments',
    ),

  approveExperiment: (expId: string) =>
    api<CroExperimentRecord>(`/api/v1/cro/experiments/${encodeURIComponent(expId)}/approve`, { method: 'POST' }, 'Failed to approve experiment'),

  startExperiment: (expId: string) =>
    api<CroExperimentRecord>(`/api/v1/cro/experiments/${encodeURIComponent(expId)}/start`, { method: 'POST' }, 'Failed to start experiment'),

  evaluateExperiment: (expId: string, payload: Record<string, any>) =>
    api<any>(
      `/api/v1/cro/experiments/${encodeURIComponent(expId)}/results`,
      { method: 'POST', body: JSON.stringify(payload) },
      'Failed to evaluate experiment',
    ),

  listConnectors: () =>
    api<{ connectors: CroConnectorRecord[] }>('/api/v1/cro/analytics/connectors', {}, 'Failed to load CRO connectors'),

  listMonitoringAlerts: (domain?: string) =>
    api<{ items: any[] }>(
      `/api/v1/cro/monitoring/alerts${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
      {},
      'Failed to load monitoring alerts',
    ),

  listMonitoringSchedules: (domain?: string) =>
    api<{ items: any[] }>(
      `/api/v1/cro/monitoring/schedules${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
      {},
      'Failed to load monitoring schedules',
    ),

  createSchedule: (payload: { domain: string; target_urls: string[]; cadence: string }) =>
    api<any>('/api/v1/cro/monitoring/schedules', { method: 'POST', body: JSON.stringify(payload) }, 'Failed to create schedule'),

  createReport: (payload: { audit_id: string; profile: string; format: 'html' | 'json' | 'pdf' }) =>
    api<{ report: any; download_url: string }>(
      '/api/v1/cro/reports/create',
      { method: 'POST', body: JSON.stringify(payload) },
      'Failed to publish CRO report',
    ),

  updateBusinessProfile: (payload: Record<string, any>) =>
    api<any>('/api/v1/cro/business-profiles/create', { method: 'POST', body: JSON.stringify(payload) }, 'Failed to save business profile'),
};

export const CRO_REPORT_PROFILE_LIST = [
  { id: 'executive_brief', title: 'CRO Executive Brief', audience: 'CEO and Leadership' },
  { id: 'complete_audit_book', title: 'Complete CRO Audit Book (65 Sections)', audience: 'Enterprise Clients' },
  { id: 'ux_ui_audit', title: 'UX/UI Audit', audience: 'Design and Product Teams' },
  { id: 'landing_page_report', title: 'Landing Page Optimization Report', audience: 'Marketing Teams' },
  { id: 'copywriting_report', title: 'Copywriting Improvement Report', audience: 'Content and Marketing' },
  { id: 'forms_leadgen_report', title: 'Forms and Lead Generation Report', audience: 'Sales and Marketing' },
  { id: 'ecommerce_cro_report', title: 'Ecommerce CRO Report', audience: 'Ecommerce Operators' },
  { id: 'checkout_report', title: 'Checkout Optimization Report', audience: 'Product and Engineering' },
  { id: 'analytics_funnel_report', title: 'Analytics and Funnel Report', audience: 'Analytics Teams' },
  { id: 'mobile_cro_report', title: 'Mobile CRO Report', audience: 'Product and Design' },
  { id: 'remediation_pack', title: 'CRO Remediation Pack', audience: 'Developers & Implementation' },
  { id: 'experimentation_report', title: 'Experimentation Report', audience: 'Growth & Experimentation' },
  { id: 'verification_report', title: 'Independent Verification Report', audience: 'Management & Reviewers' },
  { id: 'evidence_appendix', title: 'Technical & Compliance Evidence Appendix', audience: 'Compliance & Technical QA' },
] as const;

export const CRO_BUSINESS_MODELS = [
  { value: 'ecommerce', label: 'Ecommerce' },
  { value: 'saas', label: 'SaaS' },
  { value: 'b2b_lead_gen', label: 'B2B Lead Generation' },
  { value: 'b2c_lead_gen', label: 'B2C Lead Generation' },
  { value: 'professional_services', label: 'Professional Services' },
  { value: 'local_services', label: 'Local Services' },
  { value: 'marketplace', label: 'Marketplace' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'publisher_content', label: 'Publisher / Content' },
  { value: 'booking_reservation', label: 'Booking & Reservation' },
  { value: 'education_courses', label: 'Education & Courses' },
  { value: 'financial_services', label: 'Financial Services' },
] as const;
