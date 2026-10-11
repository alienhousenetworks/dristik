import { ExecutiveReport } from '../types';
import {
  AuthoritativeScore,
  buildAuthoritativeScore,
  finiteNumber,
  PillarInput,
  REPORT_PILLARS,
} from '../report/models/scoreLedger';

/**
 * One score for the dashboard and the PDF.
 * GEO uses the measured extractability composite. A category score of 100
 * from checks that were never run is not used in its place.
 * A live citation of zero stays in the total only when an engine on this
 * run returned a response. An attempted query budget is not that response.
 */
function positiveCount(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0;
}

function recordNamesEngine(record: { engine_id?: string; engine_name?: string } | null | undefined): boolean {
  return Boolean(`${record?.engine_id || ''} ${record?.engine_name || ''}`.trim());
}

export function liveExecutionProven(report: ExecutiveReport): boolean {
  const card = report.ai_visibility_scorecard;
  if (positiveCount(card?.successful_runs)) return true;
  const records = [
    ...(card?.observatory_records || []),
    ...(report.observatory_records || []),
  ];
  return records.some((record) => recordNamesEngine(record));
}

function scoreClaimPattern(token?: string): RegExp {
  const number = token ? `${token}(?:\\.0)?` : '\\d+(?:\\.\\d+)?';
  return new RegExp(`${number}/100(?:\\s*\\([^)]*\\))?(?:,?\\s*grade\\s+[A-F]\\+?)?`, 'i');
}

export function alignDisplayedStory(
  story: string | null | undefined,
  sealedScore: unknown,
  score: AuthoritativeScore,
): string {
  const text = story || '';
  if (score.composite == null) return text;
  const replacement = `${score.composite.toFixed(1)}/100 (grade ${score.grade})`;
  const sealed = finiteNumber(sealedScore);
  if (sealed != null) {
    const sealedClaim = scoreClaimPattern(String(Math.round(sealed)));
    if (sealedClaim.test(text)) return text.replace(sealedClaim, replacement);
  }
  return text.replace(scoreClaimPattern(), replacement);
}

export function buildDisplayedScore(report: ExecutiveReport): AuthoritativeScore {
  const scores = report.scores;
  const honest = report.honest_scores;
  const categoryScore = (key: string): number | null => {
    const category = scores?.category_scores?.[key] as { score?: number; status?: string } | undefined;
    if (!category || category.status === 'NOT_MEASURED') return null;
    return finiteNumber(category.score);
  };
  const proven = liveExecutionProven(report);
  const liveCitation = proven
    ? (
      finiteNumber(honest?.live_ai_citation_score)
      ?? (honest?.ai_visibility_status === 'MEASURED' ? finiteNumber(honest?.ai_visibility_score) : null)
      ?? finiteNumber(report.ai_visibility_scorecard?.citation_rate_pct)
    )
    : null;
  const geoMeasured = finiteNumber(report.geo_readiness?.extractability_score);
  const technical = finiteNumber(honest?.google_score) ?? categoryScore('TECHNICAL_SEO');
  const geo = geoMeasured ?? finiteNumber(honest?.ai_readiness_score) ?? categoryScore('GEO');
  const cro = finiteNumber(honest?.human_score) ?? categoryScore('UX_CONVERSION');
  const pillars: PillarInput[] = [
    {
      ...REPORT_PILLARS.technical,
      rawScore: technical,
      status: technical == null ? 'NOT_MEASURED' : 'MEASURED',
    },
    {
      ...REPORT_PILLARS.geo,
      rawScore: geo,
      status: geo == null ? 'NOT_MEASURED' : 'MEASURED',
    },
    {
      ...REPORT_PILLARS.aeo,
      rawScore: liveCitation,
      status: liveCitation == null ? 'NOT_MEASURED' : 'LIVE_MEASURED',
    },
    {
      ...REPORT_PILLARS.cro,
      rawScore: cro,
      status: cro == null ? 'NOT_MEASURED' : 'MEASURED',
    },
  ];
  return buildAuthoritativeScore(pillars);
}
