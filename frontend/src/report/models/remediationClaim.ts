/**
 * A generated diff, an applied change, and an independently verified
 * fix are different states. The report may claim only the state the
 * patch record actually has.
 */

export type RemediationState = 'RECOMMENDATION' | 'GENERATED' | 'APPLIED' | 'VERIFIED';

export interface RemediationClaim {
  state: RemediationState;
  label: string;
  detail: string;
}

export interface PatchLike {
  release_status?: string | null;
  approval_status?: string | null;
  verification_status?: string | null;
}

function normalizedStatus(status?: string | null): string {
  return (status || '').trim().toUpperCase().replace(/[\s-]+/g, '_');
}

function asPatch(patch?: PatchLike | string | null): PatchLike {
  if (typeof patch === 'string' || patch == null) return { release_status: patch };
  return patch;
}

export function patchState(patch?: PatchLike | string | null): RemediationState {
  const record = asPatch(patch);
  const fields = [
    normalizedStatus(record.verification_status),
    normalizedStatus(record.approval_status),
    normalizedStatus(record.release_status),
  ];
  if (fields.some((value) => value === 'VERIFIED' || value === 'INDEPENDENTLY_VERIFIED')) return 'VERIFIED';
  if (fields.some((value) => value === 'APPLIED')) return 'APPLIED';
  return 'GENERATED';
}

export function patchStateLabel(patch?: PatchLike | string | null): string {
  const state = patchState(patch);
  if (state === 'VERIFIED') return 'VERIFIED';
  if (state === 'APPLIED') return 'APPLIED — NOT VERIFIED';
  return 'GENERATED — UNAPPLIED';
}

/**
 * The section banner uses the weakest claim that is still true.
 * One unapplied patch keeps the set from being described as verified.
 */
export function deriveRemediationClaim(patches: PatchLike[]): RemediationClaim {
  if (patches.length === 0) {
    return {
      state: 'RECOMMENDATION',
      label: 'Recommendation only',
      detail: 'No code patch was generated. Items in the action plan are recommendations, not applied or verified fixes.',
    };
  }
  const states = patches.map((patch) => patchState(patch));
  if (states.every((state) => state === 'VERIFIED')) {
    return {
      state: 'VERIFIED',
      label: 'Independently verified',
      detail: 'Every listed patch is marked verified. Verification requires a recrawl after the change was applied.',
    };
  }
  if (states.some((state) => state === 'APPLIED' || state === 'VERIFIED') && states.every((state) => state !== 'GENERATED')) {
    return {
      state: 'APPLIED',
      label: 'Applied — not independently verified',
      detail: 'At least one patch is marked applied. Applied is not the same as a recrawl that confirmed the fix.',
    };
  }
  return {
    state: 'GENERATED',
    label: 'Patch generated (unapplied)',
    detail: 'Generated diffs have not been deployed. They are not a before-and-after result and they are not verified in staging.',
  };
}
