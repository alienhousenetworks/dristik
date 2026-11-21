import { api } from './http';

export interface SeoDimensionScore {
  dimension_id: string;
  name: string;
  configured_weight: number;
  effective_weight: number | null;
  is_applicable: boolean;
  is_measured: boolean;
  score: number | null;
  passed_checks_count: number;
  executed_checks_count: number;
  failed_checks_count?: number;
  interpretation: string | null;
  notes?: string[];
}

export interface SeoConfidenceVectors {
  audit_coverage_pct: number;
  evidence_confidence_pct: number;
  data_freshness_hours: number;
  connector_completeness_pct: number;
  sampling_status: string;
}

export interface SeoScorecardReport {
  audit_id?: string;
  methodology_version: string;
  overall_health_score: number | null;
  score_status?: 'MEASURED' | 'UNMEASURED';
  overall_interpretation: string;
  dimensions: SeoDimensionScore[];
  measured_dimensions_count: number;
  excluded_dimensions_count: number;
  active_weight_sum: number;
  confidence_vectors: SeoConfidenceVectors;
  disclosures: string[];
  sealed_at?: string;
}

export interface SeoRemediationTask {
  task_id: string;
  finding_id: string;
  root_cause_id?: string | null;
  fix_type: string;
  priority: string;
  problem: string;
  root_cause: string;
  affected_scope: {
    total_urls: number;
    template_pattern: string;
    sample_urls: string[];
  };
  seo_impact: string;
  business_impact: string;
  recommended_fix: string;
  implementation?: {
    platform: string;
    target_file_pattern: string;
    code_diff_snippet: string;
    instructions: string;
    stack_confidence: 'DETECTED' | 'GENERIC_FALLBACK' | string;
  };
  owner: string;
  department: string;
  dependencies: string[];
  effort: string;
  due_date?: string | null;
  acceptance_criteria: string;
  verification_protocol: string;
  evidence_refs?: string[];
  status: string;
  approval_status: string;
  verification_status: string;
  before_evidence?: Record<string, any>;
  after_evidence?: Record<string, any>;
  latest_verification?: Record<string, any> | null;
}

export interface SeoVerificationResult {
  task_id: string;
  finding_id: string;
  target_url: string;
  passed: boolean;
  verification_status: 'VERIFIED_FIXED' | 'STILL_OPEN' | 'FAILED';
  check_summary: string;
  before_snapshot: Record<string, any>;
  after_snapshot: Record<string, any>;
  comparison_rows: Array<{ dimension: string; before: string; after: string }>;
  verified_at: string;
}

export interface SeoConnectorStatus {
  provider_id: string;
  label: string;
  category: string;
  status: 'CONNECTED' | 'NOT_CONFIGURED' | 'ERROR' | 'QUOTA_EXCEEDED';
  scopes_granted: string[];
  scopes_required: string[];
  daily_quota_limit: number;
  daily_quota_used: number;
  last_sync_timestamp: string | null;
  data_freshness_hours: number | null;
  health_message: string;
  workspace_id?: string;
}

export interface SeoAuditHistory {
  audit_id: string;
  domain: string;
  has_history: boolean;
  baseline_audit_id: string | null;
  score_delta: number | null;
  historical_runs: Array<{
    audit_id: string;
    status: string;
    overall_score: number | null;
    completed_at: string;
  }>;
}

export const seoApi = {
  getOverview: (auditId: string) =>
    api<Record<string, any>>(`/api/v1/seo/audits/${encodeURIComponent(auditId)}`),

  getScores: (auditId: string) =>
    api<SeoScorecardReport>(`/api/v1/seo/audits/${encodeURIComponent(auditId)}/scores`),

  getFindings: (auditId: string) =>
    api<{ audit_id: string; count: number; findings: any[] }>(
      `/api/v1/seo/audits/${encodeURIComponent(auditId)}/findings`
    ),

  updateFinding: (auditId: string, findingId: string, payload: { status?: string; assigned_owner?: string; note?: string }) =>
    api<Record<string, any>>(
      `/api/v1/seo/findings/${encodeURIComponent(findingId)}?audit_id=${encodeURIComponent(auditId)}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    ),

  getTasks: (auditId: string) =>
    api<{ audit_id: string; count: number; tasks: SeoRemediationTask[]; recommendations: SeoRemediationTask[] }>(
      `/api/v1/seo/audits/${encodeURIComponent(auditId)}/tasks`
    ),

  createTask: (findingId: string, payload: { audit_id: string; assignee?: string; department?: string; priority?: string; due_date?: string }) =>
    api<Record<string, any>>(`/api/v1/seo/findings/${encodeURIComponent(findingId)}/tasks`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateTask: (auditId: string, taskId: string, payload: { status?: string; approval_status?: string; assigned_owner?: string; due_date?: string }) =>
    api<Record<string, any>>(
      `/api/v1/seo/tasks/${encodeURIComponent(taskId)}?audit_id=${encodeURIComponent(auditId)}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    ),

  verifyTask: (auditId: string, taskId: string, payload: { target_url?: string; rule_id?: string } = {}) =>
    api<SeoVerificationResult>(
      `/api/v1/seo/tasks/${encodeURIComponent(taskId)}/verify?audit_id=${encodeURIComponent(auditId)}`,
      { method: 'POST', body: JSON.stringify(payload) }
    ),

  getLinkGraph: (auditId: string) =>
    api<Record<string, any>>(`/api/v1/seo/orchestrator/audits/${encodeURIComponent(auditId)}/link-graph`),

  getHistory: (auditId: string) =>
    api<SeoAuditHistory>(`/api/v1/seo/audits/${encodeURIComponent(auditId)}/history`),

  listConnectors: (workspaceId?: string) =>
    api<SeoConnectorStatus[]>(
      workspaceId ? `/api/v1/seo/connectors?workspace_id=${encodeURIComponent(workspaceId)}` : '/api/v1/seo/connectors'
    ),

  connectProvider: (providerId: string, credentials: Record<string, any>, workspaceId?: string) =>
    api<SeoConnectorStatus>(
      `/api/v1/seo/connectors/${encodeURIComponent(providerId)}/connect${workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ''}`,
      { method: 'POST', body: JSON.stringify(credentials) }
    ),

  disconnectProvider: (providerId: string, workspaceId?: string) =>
    api<{ provider_id: string; disconnected: boolean }>(
      `/api/v1/seo/connectors/${encodeURIComponent(providerId)}/disconnect${workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ''}`,
      { method: 'POST' }
    ),

  generateReport: (auditId: string, payload: { profile: string; selected_chapters?: number[]; tone?: string; allow_draft_on_qa_block?: boolean }) =>
    api<{
      publication_id: string;
      audit_id: string;
      profile: string;
      status: string;
      qa_status: string;
      sha256_integrity_hash: string;
      download_pdf_url: string;
      download_html_url: string;
    }>(`/api/v1/seo/audits/${encodeURIComponent(auditId)}/reports`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
