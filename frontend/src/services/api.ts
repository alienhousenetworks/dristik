import { AnalysisRun, AnalysisSummary, PlansCatalog, PipelineGraphState } from '../types';

export async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
  } catch {
    /* ignore */
  }
  return `${fallback} (${response.status})`;
}

export async function listAnalyses(limit: number = 25): Promise<AnalysisSummary[]> {
  try {
    const response = await fetch(`/api/v1/analyses?limit=${limit}`, { credentials: 'include' });
    if (!response.ok) return [];
    return response.json();
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
  const response = await fetch('/api/v1/analyses', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      website_url: websiteUrl,
      max_crawl_pages: maxCrawlPages,
      site_type: siteType || undefined,
      industry: siteType || undefined,
      declared_site_type_notes: declaredNotes || undefined,
    }),
  });

  if (!response.ok) {
    throw new Error(await readError(response, 'Could not start the audit'));
  }

  return response.json();
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  const response = await fetch(`/api/v1/analyses/${analysisId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(await readError(response, 'Could not delete the audit'));
  }
}

export async function getAnalysis(analysisId: string): Promise<AnalysisRun> {
  const response = await fetch(`/api/v1/analyses/${analysisId}`, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(await readError(response, 'Could not load the audit'));
  }
  return response.json();
}

export async function getPlans(): Promise<PlansCatalog> {
  const response = await fetch('/api/v1/payments/plans', { credentials: 'include' });
  if (!response.ok) {
    throw new Error(await readError(response, 'Could not load plans'));
  }
  return response.json();
}

export function openAnalysisStream(analysisId: string): EventSource {
  return new EventSource(`/api/v1/analyses/${analysisId}/stream`);
}

export async function getExecutionGraph(analysisId: string): Promise<PipelineGraphState> {
  const response = await fetch(`/api/v1/analyses/${analysisId}/graph`, { credentials: 'include' });
  if (!response.ok) {
    throw new Error(await readError(response, 'Could not fetch execution graph'));
  }
  return response.json();
}

export async function pauseAnalysis(analysisId: string): Promise<{ status: string; analysis_id: string }> {
  const response = await fetch(`/api/v1/analyses/${analysisId}/pause`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(await readError(response, 'Could not pause the audit'));
  }
  return response.json();
}

export async function resumeAnalysis(analysisId: string): Promise<{ status: string; analysis_id: string }> {
  const response = await fetch(`/api/v1/analyses/${analysisId}/resume`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(await readError(response, 'Could not resume the audit'));
  }
  return response.json();
}

export async function runGraphNode(
  analysisId: string,
  nodeId: string
): Promise<{ success: boolean; node_id: string; status: string }> {
  const response = await fetch(`/api/v1/analyses/${analysisId}/nodes/${nodeId}/run`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error(await readError(response, `Could not execute step '${nodeId}'`));
  }
  return response.json();
}
