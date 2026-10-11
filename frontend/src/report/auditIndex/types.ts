export type SectionStatus =
  | 'NOT_APPLICABLE'
  | 'NOT_TESTED'
  | 'DATA_UNAVAILABLE'
  | 'NO_ISSUE'
  | 'ISSUE_VERIFIED'
  | 'INFERRED'
  | 'MEASURED';

export interface AuditSectionDefinition {
  number: string;
  part: string;
  title: string;
  checks: string[];
}

export interface AuditFindingRef {
  id: string;
  severity: string;
  title: string;
  scope: string;
}

export interface ResolvedAuditSection extends AuditSectionDefinition {
  status: SectionStatus;
  summary: string;
  coverage: string;
  findings: AuditFindingRef[];
  findingCount: number;
}

export interface ResolvedAuditIndex {
  sampleNotice: string;
  sections: ResolvedAuditSection[];
  counts: Record<SectionStatus, number>;
}
