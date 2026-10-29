/**
 * The page snapshot hash is one digest for the whole document.
 * Each evidence row needs its own payload digest. A shared snapshot
 * hash must not be printed as if it sealed every row.
 */

export type EvidenceHashStatus = 'SEALED' | 'SHARED_SNAPSHOT' | 'NOT_SEALED';

export interface EvidenceHashInput {
  id: string;
  payloadHash?: string | null;
  snapshotHash?: string | null;
}

export interface EvidenceHashDecision {
  id: string;
  sha256?: string;
  sourceSnapshotSha256?: string;
  hashStatus: EvidenceHashStatus;
}

function cleanDigest(value?: string | null): string {
  return (value || '').trim();
}

export function assignEvidenceHashes(items: EvidenceHashInput[]): EvidenceHashDecision[] {
  const snapshotCounts = new Map<string, number>();
  items.forEach((item) => {
    const snapshot = cleanDigest(item.snapshotHash);
    const payload = cleanDigest(item.payloadHash);
    if (!payload && snapshot) {
      snapshotCounts.set(snapshot, (snapshotCounts.get(snapshot) || 0) + 1);
    }
  });

  return items.map((item) => {
    const payload = cleanDigest(item.payloadHash);
    const snapshot = cleanDigest(item.snapshotHash);
    if (payload) {
      return {
        id: item.id,
        sha256: payload,
        sourceSnapshotSha256: snapshot || undefined,
        hashStatus: 'SEALED' as const,
      };
    }
    if (snapshot && (snapshotCounts.get(snapshot) || 0) === 1) {
      return {
        id: item.id,
        sha256: snapshot,
        sourceSnapshotSha256: snapshot,
        hashStatus: 'SEALED' as const,
      };
    }
    if (snapshot) {
      return {
        id: item.id,
        sourceSnapshotSha256: snapshot,
        hashStatus: 'SHARED_SNAPSHOT' as const,
      };
    }
    return { id: item.id, hashStatus: 'NOT_SEALED' as const };
  });
}

const IMAGE_CLAIM = /alt text|alt attribute|image accessibility|images lack|missing alt|without alt/i;
const HEADER_CLAIM = /hsts|strict-transport|content-security-policy|\bcsp\b|security header|x-frame-options|x-content-type|clickjacking/i;
const TITLE_SELECTOR = /^(title|h1|h2|h3)$|meta\[name=["']?description/i;

export interface EvidenceSupportInput {
  selector?: string | null;
  sourceType?: string | null;
  id?: string | null;
}

/**
 * A finding may cite only the record that observed the same surface.
 * An image-alt finding does not inherit a title node, and a header
 * finding does not inherit one either.
 */
export function evidenceSupportsFinding(claim: string, item: EvidenceSupportInput): boolean {
  const text = claim || '';
  const selector = (item.selector || '').trim();
  const external = (item.sourceType || '').toLowerCase() === 'external'
    || (item.id || '').toLowerCase().startsWith('ext_');
  if (IMAGE_CLAIM.test(text) && (TITLE_SELECTOR.test(selector) || (external && selector.toLowerCase() !== 'img'))) {
    return false;
  }
  if (HEADER_CLAIM.test(text) && (TITLE_SELECTOR.test(selector) || selector.toLowerCase() === 'img')) {
    return false;
  }
  if (HEADER_CLAIM.test(text) && external && !/strict-transport|content-security|x-frame|x-content-type|response.header|header/i.test(selector)) {
    return false;
  }
  return true;
}

/** One visible prefix, long enough that neighboring rows do not look identical. */
export function formatEvidenceHash(hash?: string | null, status: EvidenceHashStatus = 'SEALED'): string {
  if (status === 'SHARED_SNAPSHOT') return 'Shared page snapshot — not a per-record seal';
  if (status === 'NOT_SEALED' || !hash) return 'Not sealed';
  const digest = hash.replace(/^sha256:/i, '').replace(/%+$/g, '').trim();
  if (digest.length < 12) return 'Not sealed';
  return `sha256:${digest.slice(0, 16)}…`;
}
