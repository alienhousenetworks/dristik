/**
 * One report score. Cover, grade, charts, and the calculation ledger
 * all read this result. A measured zero stays in the total. A pillar
 * with no measurement is left out and the remaining weights are scaled
 * so they still sum to 100.
 */

export type PillarMeasurement = 'MEASURED' | 'LIVE_MEASURED' | 'NOT_MEASURED';

export interface PillarInput {
  pillar: string;
  categoryKey: string;
  /** Null means the pillar was not measured. Zero is a real measurement. */
  rawScore: number | null;
  /** Nominal share of the composite, such as 0.30. */
  nominalWeight: number;
  status: PillarMeasurement;
}

export interface LedgerRow {
  pillar: string;
  categoryKey: string;
  rawScore: number | null;
  /** Effective share of this composite. Zero when the pillar is excluded. */
  weightPct: number;
  /** Stated share before missing pillars are removed, such as 30. */
  nominalWeightPct: number;
  contribution: number;
  status: PillarMeasurement;
  included: boolean;
}

export interface AuthoritativeScore {
  rows: LedgerRow[];
  composite: number | null;
  grade: string;
  formula: string;
  /** True when at least one pillar was left out and at least one remains. */
  partialCoverage: boolean;
  coverageLabel: string;
  excludedPillars: string[];
}

export const REPORT_PILLARS = {
  technical: { pillar: 'Technical Discoverability (SEO)', categoryKey: 'TECHNICAL_SEO', nominalWeight: 0.3 },
  geo: { pillar: 'Generative Extractability (GEO)', categoryKey: 'GEO', nominalWeight: 0.25 },
  aeo: { pillar: 'Live Answer-Engine Citations (AEO)', categoryKey: 'AEO', nominalWeight: 0.25 },
  cro: { pillar: 'Conversion & UX Friction (CRO)', categoryKey: 'UX_CONVERSION', nominalWeight: 0.2 },
} as const;

export function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function gradeForScore(score: number | null): string {
  if (score == null) return '—';
  if (score >= 93) return 'A+';
  if (score >= 85) return 'A';
  if (score >= 75) return 'B';
  if (score >= 65) return 'C';
  if (score >= 50) return 'D';
  return 'F';
}

function roundTo(value: number, digits: number): number {
  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

export function buildAuthoritativeScore(pillars: PillarInput[]): AuthoritativeScore {
  const measured = pillars.filter((pillar) => pillar.status !== 'NOT_MEASURED' && pillar.rawScore != null);
  const weightSum = measured.reduce((sum, pillar) => sum + pillar.nominalWeight, 0);

  const rows: LedgerRow[] = pillars.map((pillar) => {
    const included = pillar.status !== 'NOT_MEASURED' && pillar.rawScore != null && weightSum > 0;
    const nominalWeightPct = roundTo(pillar.nominalWeight * 100, 1);
    if (!included || pillar.rawScore == null) {
      return {
        pillar: pillar.pillar,
        categoryKey: pillar.categoryKey,
        rawScore: null,
        weightPct: 0,
        nominalWeightPct,
        contribution: 0,
        status: 'NOT_MEASURED',
        included: false,
      };
    }
    const share = pillar.nominalWeight / weightSum;
    return {
      pillar: pillar.pillar,
      categoryKey: pillar.categoryKey,
      rawScore: roundTo(pillar.rawScore, 1),
      weightPct: roundTo(share * 100, 1),
      nominalWeightPct,
      contribution: roundTo(pillar.rawScore * share, 2),
      status: pillar.status,
      included: true,
    };
  });

  const includedRows = rows.filter((row) => row.included);
  if (includedRows.length > 0) {
    const displayed = includedRows.reduce((sum, row) => sum + row.weightPct, 0);
    const drift = roundTo(100 - displayed, 1);
    if (drift !== 0) {
      const last = includedRows[includedRows.length - 1];
      last.weightPct = roundTo(last.weightPct + drift, 1);
    }
  }

  const composite = measured.length > 0 && weightSum > 0
    ? roundTo(
        measured.reduce((sum, pillar) => sum + (pillar.rawScore as number) * (pillar.nominalWeight / weightSum), 0),
        1,
      )
    : null;

  const formula = rows
    .map((row) => (
      row.included
        ? `${row.categoryKey} ${row.rawScore}×${row.weightPct}%`
        : `${row.categoryKey} not measured`
    ))
    .join(' + ');

  const excludedPillars = rows.filter((row) => !row.included).map((row) => row.pillar);
  const partialCoverage = excludedPillars.length > 0 && rows.some((row) => row.included);
  const coverageLabel = composite == null
    ? 'Not scored'
    : partialCoverage
      ? 'Partial-coverage composite'
      : 'Full composite';

  return {
    rows,
    composite,
    grade: gradeForScore(composite),
    formula: composite == null ? formula : `${formula} = ${composite.toFixed(1)}`,
    partialCoverage,
    coverageLabel,
    excludedPillars,
  };
}

export function shortPillarLabel(categoryKey: string): string {
  switch (categoryKey) {
    case 'TECHNICAL_SEO':
      return 'SEO';
    case 'GEO':
      return 'GEO';
    case 'AEO':
      return 'AEO';
    case 'UX_CONVERSION':
      return 'CRO';
    default:
      return categoryKey;
  }
}
