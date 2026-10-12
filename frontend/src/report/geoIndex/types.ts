export type GeoStatus =
  | 'VERIFIED'
  | 'SAMPLE_VERIFIED'
  | 'INFERRED'
  | 'HYPOTHESIS'
  | 'DATA_UNAVAILABLE'
  | 'NOT_TESTED'
  | 'NOT_APPLICABLE';

export const GEO_STATUS_LABEL: Record<GeoStatus, string> = {
  VERIFIED: 'Verified',
  SAMPLE_VERIFIED: 'Sample verified',
  INFERRED: 'Inferred',
  HYPOTHESIS: 'Hypothesis',
  DATA_UNAVAILABLE: 'Data unavailable',
  NOT_TESTED: 'Not tested',
  NOT_APPLICABLE: 'Not applicable',
};

export interface GeoFindingRef {
  id: string;
  severity: string;
  title: string;
  scope: string;
  description?: string;
  action?: string;
  priority?: number;
}

export interface GeoCheck {
  label: string;
  status: GeoStatus;
  result: string;
  findings?: GeoFindingRef[];
}

export interface GeoAgentConsultation {
  agentId: string;
  agentName: string;
  agentRole: string;
  diagnosticOverview: string;
  architectureMechanics: string;
  rootCause: string;
  businessRisk: string;
  remediationRecipe: string;
  verificationProtocol: string;
}

export interface ResolvedGeoSection {
  number: string;
  part: string;
  title: string;
  status: GeoStatus;
  pageNumber: number;
  summary: string;
  checks: GeoCheck[];
  findings: GeoFindingRef[];
  agent: GeoAgentConsultation;
}

export interface ResolvedGeoAudit {
  sampleNotice: string;
  domain: string;
  extractabilityScore: number | null;
  visibilityStatus: string;
  citationRate: number | null;
  sections: ResolvedGeoSection[];
  counts: Record<GeoStatus, number>;
}
