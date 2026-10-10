import { describe, expect, it } from 'vitest';
import { deriveRemediationClaim, patchStateLabel } from './remediationClaim';

describe('remediation claims', () => {
  it('does not call an unapplied patch verified', () => {
    const claim = deriveRemediationClaim([
      { release_status: 'PENDING_APPROVAL' },
      { release_status: 'APPROVED' },
    ]);
    expect(claim.state).toBe('GENERATED');
    expect(claim.detail).toMatch(/not verified in staging/);
    expect(patchStateLabel('PENDING_APPROVAL')).toBe('GENERATED — UNAPPLIED');
  });

  it('keeps applied and verified as separate states', () => {
    expect(deriveRemediationClaim([]).state).toBe('RECOMMENDATION');
    expect(deriveRemediationClaim([{ approval_status: 'APPLIED', verification_status: 'provisional' }]).state).toBe('APPLIED');
    expect(deriveRemediationClaim([{ verification_status: 'verified' }]).state).toBe('VERIFIED');
    expect(deriveRemediationClaim([
      { verification_status: 'verified' },
      { release_status: 'PENDING_APPROVAL' },
    ]).state).toBe('GENERATED');
  });
});
