import { describe, expect, it } from 'vitest';
import { can } from './auth';
import { AuthUser } from '../types';

function user(partial: Partial<AuthUser>): AuthUser {
  return {
    user_id: 'u1',
    email: 'a@example.com',
    full_name: 'Ada Lovelace',
    org_id: 'o1',
    org_name: 'Analytical Engines',
    role: 'analyst',
    role_label: 'Analyst',
    is_system: false,
    permissions: [],
    ...partial,
  };
}

describe('permissions', () => {
  it('allows a listed permission', () => {
    expect(can(user({ permissions: ['mission:create'] }), 'mission:create')).toBe(true);
  });

  it('denies a missing permission', () => {
    expect(can(user({ permissions: ['report:read'] }), 'mission:create')).toBe(false);
    expect(can(null, 'mission:create')).toBe(false);
  });

  it('lets a system operator through', () => {
    expect(can(user({ is_system: true, permissions: [] }), 'staff:invite')).toBe(true);
  });
});
