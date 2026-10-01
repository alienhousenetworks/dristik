import { AnalysisRun, AnalysisSummary, PlansCatalog, PipelineGraphState } from '../types';
import { api, readError } from './http';

export { readError };

export async function listAnalyses(limit: number = 25): Promise<AnalysisSummary[]> {
  try {
    return await api<AnalysisSummary[]>(`/api/v1/analyses?limit=${limit}`, {}, 'Could not list audits');
  } catch {
    return [];
  }
}

export async function startAnalysis(
  websiteUrl: string,
  maxCrawlPages: number,
  siteType?: string,
  declaredNotes?: string
): Promise<AnalysisRun> {
  return api<AnalysisRun>(
    '/api/v1/analyses',
    {
      method: 'POST',
      body: JSON.stringify({
        website_url: websiteUrl,
        max_crawl_pages: maxCrawlPages,
        site_type: siteType || undefined,
        industry: siteType || undefined,
        declared_site_type_notes: declaredNotes || undefined,
      }),
    },
    'Could not start the audit',
  );
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  await api(`/api/v1/analyses/${analysisId}`, { method: 'DELETE' }, 'Could not delete the audit');
}

export async function getAnalysis(analysisId: string): Promise<AnalysisRun> {
  return api<AnalysisRun>(`/api/v1/analyses/${analysisId}`, {}, 'Could not load the audit');
}

export async function getPlans(): Promise<PlansCatalog> {
  return api<PlansCatalog>('/api/v1/payments/plans', {}, 'Could not load plans');
}

export function openAnalysisStream(analysisId: string): EventSource {
  return new EventSource(`/api/v1/analyses/${analysisId}/stream`);
}

export async function getExecutionGraph(analysisId: string): Promise<PipelineGraphState> {
  return api<PipelineGraphState>(`/api/v1/analyses/${analysisId}/graph`, {}, 'Could not fetch execution graph');
}

export async function pauseAnalysis(analysisId: string): Promise<{ status: string; analysis_id: string }> {
  return api(`/api/v1/analyses/${analysisId}/pause`, { method: 'POST' }, 'Could not pause the audit');
}

export async function resumeAnalysis(analysisId: string): Promise<{ status: string; analysis_id: string }> {
  return api(`/api/v1/analyses/${analysisId}/resume`, { method: 'POST' }, 'Could not resume the audit');
}

export async function runGraphNode(
  analysisId: string,
  nodeId: string
): Promise<{ success: boolean; node_id: string; status: string }> {
  return api(
    `/api/v1/analyses/${analysisId}/nodes/${nodeId}/run`,
    { method: 'POST' },
    `Could not execute step '${nodeId}'`,
  );
}
