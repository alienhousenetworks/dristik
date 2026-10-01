import { api } from './http';

function send<T>(path: string, init?: RequestInit): Promise<T> {
  return api<T>(path, init, 'External authority request failed');
}

export function fetchExternalProviders() {
  return send<{ providers: Array<Record<string, unknown>> }>('/api/v1/external-authority/providers');
}

export function fetchExternalHealth() {
  return send<{ connectors: Array<Record<string, unknown>> }>('/api/v1/external-authority/health');
}

export function fetchExternalCoverage(domain: string) {
  const params = new URLSearchParams({ domain, period_days: '28' });
  return send<{ matrix: Array<Record<string, unknown>>; sources: Array<{ source: string; state: string }> }>(
    `/api/v1/external-authority/coverage?${params.toString()}`,
  );
}

export function startExternalOAuth(provider: string, domain: string) {
  return send<{ authorize_url: string }>('/api/v1/external-authority/oauth/start', {
    method: 'POST',
    body: JSON.stringify({ provider, domain }),
  });
}

export function connectExternalApiKey(provider: string, domain: string, secret: { api_key?: string; login?: string; password?: string }) {
  return send<{ status: string }>('/api/v1/external-authority/connect', {
    method: 'POST',
    body: JSON.stringify({ provider, domain, ...secret }),
  });
}

export function disconnectExternal(provider: string) {
  return send<{ status: string }>('/api/v1/external-authority/disconnect', {
    method: 'POST',
    body: JSON.stringify({ provider }),
  });
}

export function saveExternalBrand(name: string, aliases: string[]) {
  return send('/api/v1/external-authority/brand', {
    method: 'PUT',
    body: JSON.stringify({ name, aliases }),
  });
}

export function saveExternalCompetitors(competitors: Array<{ name: string; domain: string }>) {
  return send('/api/v1/external-authority/competitors', {
    method: 'PUT',
    body: JSON.stringify({ competitors }),
  });
}

export function saveExternalLocal(profile: Record<string, unknown>) {
  return send('/api/v1/external-authority/local-business', {
    method: 'PUT',
    body: JSON.stringify(profile),
  });
}

export function syncExternal(domain: string) {
  return send<{ results: Array<Record<string, unknown>> }>('/api/v1/external-authority/sync', {
    method: 'POST',
    body: JSON.stringify({ domain, periods: [28], run: true }),
  });
}
