import { AdminOrganization, AuthProvidersResponse, AuthUser, ContactRecord, OrgSummary, PlatformOverview } from '../types';
import { api } from './http';

function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  return api<T>(path, init);
}

export async function fetchMe(): Promise<AuthUser | null> {
  const data = await request<{ user: AuthUser | null }>('/api/v1/auth/me');
  return data.user;
}

export async function signup(body: {
  full_name: string;
  email: string;
  password: string;
  organization_name: string;
}): Promise<AuthUser> {
  const data = await request<{ user: AuthUser }>('/api/v1/auth/signup', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return data.user;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const data = await request<{ user: AuthUser }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return data.user;
}

export async function logout(): Promise<void> {
  await request('/api/v1/auth/logout', { method: 'POST' });
}

export async function forgotPassword(email: string): Promise<{ message: string; reset_path?: string }> {
  return request('/api/v1/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await request('/api/v1/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, password }),
  });
}

export async function deleteAccount(password: string): Promise<void> {
  await request('/api/v1/auth/delete-account', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function fetchOrg() {
  return request<{ org_id: string; org_name: string; is_system: boolean; members: AuthUser[] }>(
    '/api/v1/orgs/me',
  );
}

export async function inviteStaff(body: {
  full_name: string;
  email: string;
  password: string;
  role: string;
}): Promise<AuthUser> {
  const data = await request<{ user: AuthUser }>('/api/v1/orgs/me/members', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return data.user;
}

export async function changeStaffRole(userId: string, role: string): Promise<AuthUser> {
  const data = await request<{ user: AuthUser }>(`/api/v1/orgs/me/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
  return data.user;
}

export async function removeStaff(userId: string): Promise<void> {
  await request(`/api/v1/orgs/me/members/${userId}`, { method: 'DELETE' });
}

export async function submitContact(body: {
  name: string;
  email: string;
  phone: string;
  company: string;
  website: string;
  job_title: string;
  message: string;
}): Promise<{ message: string }> {
  return request('/api/v1/contact', { method: 'POST', body: JSON.stringify(body) });
}

export async function fetchContacts(): Promise<ContactRecord[]> {
  const data = await request<{ contacts: ContactRecord[] }>('/api/v1/contact');
  return data.contacts;
}

export async function fetchOrganizations(): Promise<OrgSummary[]> {
  const data = await request<{ organizations: OrgSummary[] }>('/api/v1/orgs');
  return data.organizations;
}

export function can(user: AuthUser | null, permission: string): boolean {
  return Boolean(user?.permissions?.includes(permission) || user?.is_system);
}

export async function fetchSystemOverview(): Promise<PlatformOverview> {
  return request('/api/v1/system/overview');
}

export async function fetchSystemOrganizations(): Promise<AdminOrganization[]> {
  const data = await request<{ organizations: AdminOrganization[] }>('/api/v1/system/organizations');
  return data.organizations;
}

export async function setOrgPlan(orgId: string, plan: string): Promise<AdminOrganization> {
  return request(`/api/v1/system/organizations/${orgId}/plan`, {
    method: 'PATCH',
    body: JSON.stringify({ plan }),
  });
}

export async function setOrgActive(orgId: string, isActive: boolean): Promise<AdminOrganization> {
  return request(`/api/v1/system/organizations/${orgId}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}

export async function deleteOrganization(orgId: string, purge = false): Promise<void> {
  await request(`/api/v1/system/organizations/${orgId}?purge=${purge ? 'true' : 'false'}`, {
    method: 'DELETE',
  });
}

export async function deactivateUser(userId: string): Promise<void> {
  await request(`/api/v1/system/users/${userId}/deactivate`, { method: 'POST' });
}

export async function restoreUser(userId: string): Promise<void> {
  await request(`/api/v1/system/users/${userId}/restore`, { method: 'POST' });
}

export async function setUserPassword(userId: string, password: string): Promise<void> {
  await request(`/api/v1/system/users/${userId}/password`, {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function runSessionExpiry(): Promise<{ expired_sessions: number }> {
  return request('/api/v1/system/maintenance/expire-sessions', { method: 'POST' });
}

export async function runDatabaseCleanup(): Promise<{
  expired_sessions: number;
  cleared_resets: number;
  database: PlatformOverview['database'];
}> {
  return request('/api/v1/system/maintenance/cleanup', { method: 'POST' });
}

export async function fetchAuthProviders(): Promise<AuthProvidersResponse> {
  return request<AuthProvidersResponse>('/api/v1/auth/providers');
}

export function startSSOAuth(
  provider: 'google' | 'github',
  onComplete: () => void,
  mode: 'popup' | 'redirect' = 'popup'
): () => void {
  const currentPath = window.location.pathname + window.location.search + window.location.hash;
  const redirectParam = encodeURIComponent(currentPath || '/');
  const authUrl = `/api/v1/auth/oauth/${provider}/authorize?redirect=${redirectParam}`;

  if (mode === 'redirect') {
    window.location.href = authUrl;
    return () => {};
  }

  const width = 540;
  const height = 660;
  const left = window.screenX + (window.outerWidth - width) / 2;
  const top = window.screenY + (window.outerHeight - height) / 2;

  const popup = window.open(
    authUrl,
    `oauth_${provider}_popup`,
    `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes`
  );

  // If popup was blocked or opened in tab that closed immediately, fallback to same-window redirect
  if (!popup) {
    window.location.href = authUrl;
    return () => {};
  }

  let cleaned = false;
  let timer: any = null;
  let bc: BroadcastChannel | null = null;

  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    if (timer) clearInterval(timer);
    window.removeEventListener('message', handleMessage);
    window.removeEventListener('storage', handleStorage);
    if (bc) {
      try {
        bc.close();
      } catch (_) {}
    }
  };

  const isAllowedOrigin = (origin: string) => {
    if (origin === window.location.origin) return true;
    try {
      const url = new URL(origin);
      return url.hostname === window.location.hostname && (url.port === '8000' || url.port === '5173' || !url.port);
    } catch (_) {
      return false;
    }
  };

  const handleMessage = (e: MessageEvent) => {
    if (!isAllowedOrigin(e.origin)) return;
    if (e.data && e.data.type === 'AUTH_SUCCESS') {
      cleanup();
      onComplete();
    }
  };

  const handleStorage = (e: StorageEvent) => {
    if (e.key === 'dristik_auth_sync' && e.newValue) {
      try {
        const payload = JSON.parse(e.newValue);
        if (payload?.type === 'AUTH_SUCCESS') {
          localStorage.removeItem('dristik_auth_sync');
          cleanup();
          onComplete();
        }
      } catch (_) {}
    }
  };

  try {
    bc = new BroadcastChannel('dristik_auth');
    bc.onmessage = (e) => {
      if (e.data && e.data.type === 'AUTH_SUCCESS') {
        cleanup();
        onComplete();
      }
    };
  } catch (_) {}

  const waitForSession = async () => {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      try {
        const user = await fetchMe();
        if (user) return true;
      } catch {
        /* session cookie may land a moment after the popup closes */
      }
      await new Promise((resolve) => window.setTimeout(resolve, 400));
    }
    return false;
  };

  timer = setInterval(() => {
    let closed = false;
    try {
      closed = Boolean(popup.closed);
    } catch {
      closed = false;
    }
    if (!closed) return;
    clearInterval(timer);
    timer = null;
    // Google often reports the popup closed before the callback finishes.
    // Keep BroadcastChannel and storage listeners until the session exists.
    void waitForSession().finally(() => {
      cleanup();
      onComplete();
    });
  }, 500);

  window.addEventListener('message', handleMessage);
  window.addEventListener('storage', handleStorage);
  return cleanup;
}
