export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return String(body.detail[0].msg);
  } catch {
    /* non-JSON error body */
  }
  return `${fallback} (${response.status})`;
}

const anonymousPaths = ['/api/v1/auth/login', '/api/v1/auth/signup', '/api/v1/auth/me', '/api/v1/auth/forgot-password'];

export async function api<T>(path: string, init: RequestInit = {}, fallback = 'Request failed'): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, {
    credentials: 'include',
    ...init,
    headers,
  });
  if (!response.ok) {
    if (response.status === 401 && !anonymousPaths.some((item) => path.startsWith(item))) {
      window.dispatchEvent(new CustomEvent('dristik:unauthorized'));
    }
    throw new ApiError(await readError(response, fallback), response.status);
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}
