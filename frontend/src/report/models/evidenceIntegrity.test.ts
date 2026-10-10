import { describe, expect, it } from 'vitest';
import { assignEvidenceHashes, formatEvidenceHash } from './evidenceIntegrity';

const snapshot = 'sha256:abcdef1234567890abcdef1234567890';

describe('evidence hashes', () => {
  it('keeps a unique page snapshot as the seal for one row', () => {
    const [row] = assignEvidenceHashes([{ id: 'ev_dom_1', snapshotHash: snapshot }]);
    expect(row.hashStatus).toBe('SEALED');
    expect(row.sha256).toBe(snapshot);
  });

  it('does not print one page snapshot as the seal for every extract', () => {
    const rows = assignEvidenceHashes([
      { id: 'h1', snapshotHash: snapshot },
      { id: 'title', snapshotHash: snapshot },
    ]);
    expect(rows.every((row) => row.hashStatus === 'SHARED_SNAPSHOT')).toBe(true);
    expect(rows.every((row) => row.sha256 == null)).toBe(true);
    expect(formatEvidenceHash(snapshot, 'SHARED_SNAPSHOT')).toBe('Shared page snapshot — not a per-record seal');
  });

  it('prefers each row payload hash', () => {
    const rows = assignEvidenceHashes([
      { id: 'h1', payloadHash: 'sha256:' + 'a'.repeat(64), snapshotHash: snapshot },
      { id: 'title', payloadHash: 'sha256:' + 'b'.repeat(64), snapshotHash: snapshot },
    ]);
    expect(rows[0].sha256).not.toBe(rows[1].sha256);
    expect(rows[0].hashStatus).toBe('SEALED');
    expect(formatEvidenceHash(rows[0].sha256, rows[0].hashStatus)).toMatch(/^sha256:a{16}…$/);
  });
});
