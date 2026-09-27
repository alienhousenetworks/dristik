import { AdminOrganization, AuthProvidersResponse, AuthUser, ContactRecord, OrgSummary, PlatformOverview } from '../types';
import { readError } from './api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await readError(response, 'Request failed'));
  }
  return response.json();
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

export function startSSOAuth(provider: 'google' | 'github', onComplete: () => void): () => void {
  const width = 540;
  const height = 660;
  const left = window.screenX + (window.outerWidth - width) / 2;
  const top = window.screenY + (window.outerHeight - height) / 2;
  const authUrl = `/api/v1/auth/oauth/${provider}/authorize`;

  const popup = window.open(
    authUrl,
    `oauth_${provider}_popup`,
    `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes`
  );

  let cleaned = false;
  let timer: any = null;

  const handleMessage = (e: MessageEvent) => {
    if (e.data && e.data.type === 'AUTH_SUCCESS') {
      cleanup();
      onComplete();
    }
  };

  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    if (timer) clearInterval(timer);
    window.removeEventListener('message', handleMessage);
  };

  timer = setInterval(() => {
    if (!popup || popup.closed) {
      cleanup();
      onComplete();
    }
  }, 800);

  window.addEventListener('message', handleMessage);
  return cleanup;
}
