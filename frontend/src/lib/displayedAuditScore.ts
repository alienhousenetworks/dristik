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
 */
export function buildDisplayedScore(report: ExecutiveReport): AuthoritativeScore {
  const scores = report.scores;
  const honest = report.honest_scores;
  const categoryScore = (key: string): number | null => {
    const category = scores?.category_scores?.[key] as { score?: number; status?: string } | undefined;
    if (!category || category.status === 'NOT_MEASURED') return null;
    return finiteNumber(category.score);
  };
  const liveCitation = finiteNumber(honest?.live_ai_citation_score)
    ?? (honest?.ai_visibility_status === 'MEASURED' ? finiteNumber(honest?.ai_visibility_score) : null);
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
