import { AnalysisRun, AnalysisSummary, PlansCatalog } from '../types';

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
