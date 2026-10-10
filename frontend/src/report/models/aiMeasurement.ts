/**
 * Live engine queries and on-page answerability are different measurements.
 * This module never fills in query counts, mention counts, or per-engine scores.
 */

export interface LiveEngineRow {
  engine: string;
  queriesExecuted: number;
  brandMentioned: number;
  brandCited: number;
  citationRatePct: number | null;
  status: string;
}

export interface LiveObservation {
  isMeasured: boolean;
  engineCount: number;
  /** Completed responses. An attempted budget is not a completed query. */
  queriesExecuted: number;
  queriesAttempted: number;
  queriesFailed: number;
  brandMentionedCount: number;
  brandMentionRatePct: number | null;
  brandCitedCount: number;
  liveCitationRatePct: number | null;
  status: string;
  engineDetails: LiveEngineRow[];
}

export interface ObservatoryRecord {
  engine_id?: string;
  engine_name?: string;
  brand_mentioned?: boolean;
  brand_cited?: boolean;
}

export interface VisibilityScorecard {
  status?: string;
  queries?: number;
  engines_measured?: number;
  engines_requested?: number;
  mention_rate_pct?: number | null;
  citation_rate_pct?: number | null;
  not_measured_reason?: string | null;
  successful_runs?: number;
  failed_runs?: number;
  observatory_records?: ObservatoryRecord[];
}

const NAMED_ENGINES: Array<{ keys: string[]; label: string }> = [
  { keys: ['claude', 'anthropic'], label: 'Claude (Anthropic)' },
  { keys: ['chatgpt', 'openai', 'gpt'], label: 'ChatGPT Search (OpenAI)' },
  { keys: ['perplexity'], label: 'Perplexity AI' },
  { keys: ['google_aio', 'aio', 'ai_overviews', 'google_ai'], label: 'Google AI Overviews' },
  { keys: ['gemini'], label: 'Gemini (Google)' },
];

function engineLabel(record: ObservatoryRecord): string | null {
  const raw = `${record.engine_id || ''} ${record.engine_name || ''}`.toLowerCase();
  if (!raw.trim()) return null;
  const match = NAMED_ENGINES.find((engine) => engine.keys.some((key) => raw.includes(key)));
  return match?.label || record.engine_name || record.engine_id || null;
}

function positiveCount(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? Math.round(value) : 0;
}

function measuredRow(label: string, rows: ObservatoryRecord[]): LiveEngineRow {
  if (rows.length === 0) return notExecuted(label);
  const mentioned = rows.filter((row) => row.brand_mentioned).length;
  const cited = rows.filter((row) => row.brand_cited).length;
  return {
    engine: label,
    queriesExecuted: rows.length,
    brandMentioned: mentioned,
    brandCited: cited,
    citationRatePct: Math.round((cited / rows.length) * 1000) / 10,
    status: 'MEASURED',
  };
}

function notExecuted(label: string): LiveEngineRow {
  return {
    engine: label,
    queriesExecuted: 0,
    brandMentioned: 0,
    brandCited: 0,
    citationRatePct: null,
    status: 'NOT_EXECUTED',
  };
}

export function buildLiveObservation(scorecard?: VisibilityScorecard | null): LiveObservation {
  const records = scorecard?.observatory_records || [];
  const grouped = new Map<string, ObservatoryRecord[]>();
  records.forEach((record) => {
    const label = engineLabel(record);
    if (!label) return;
    const bucket = grouped.get(label) || [];
    bucket.push(record);
    grouped.set(label, bucket);
  });

  const namedLabels = new Set(NAMED_ENGINES.map((engine) => engine.label));
  const engineDetails = [
    ...NAMED_ENGINES.map((engine) => measuredRow(engine.label, grouped.get(engine.label) || [])),
    ...[...grouped.keys()]
      .filter((label) => !namedLabels.has(label))
      .map((label) => measuredRow(label, grouped.get(label) || [])),
  ];

  const executed = engineDetails.filter((row) => row.status === 'MEASURED');
  const queriesFromRecords = executed.reduce((sum, row) => sum + row.queriesExecuted, 0);
  const mentionedFromRecords = executed.reduce((sum, row) => sum + row.brandMentioned, 0);
  const citedFromRecords = executed.reduce((sum, row) => sum + row.brandCited, 0);
  const status = (scorecard?.status || '').toUpperCase();
  const declaredQueries = positiveCount(scorecard?.queries);
  const successfulRuns = positiveCount(scorecard?.successful_runs);
  const failedRuns = positiveCount(scorecard?.failed_runs);
  const enginesMeasured = positiveCount(scorecard?.engines_measured);
  const provenByRuns = status === 'MEASURED' && successfulRuns > 0 && enginesMeasured > 0;
  const queriesCompleted = queriesFromRecords > 0 ? queriesFromRecords : (provenByRuns ? successfulRuns : 0);
  const isMeasured = queriesFromRecords > 0 || provenByRuns;
  const queriesAttempted = declaredQueries > 0 ? declaredQueries : queriesCompleted;

  if (!isMeasured) {
    return {
      isMeasured: false,
      engineCount: 0,
      queriesExecuted: 0,
      queriesAttempted,
      queriesFailed: failedRuns,
      brandMentionedCount: 0,
      brandMentionRatePct: null,
      brandCitedCount: 0,
      liveCitationRatePct: null,
      status: 'NOT_EXECUTED',
      engineDetails,
    };
  }

  return {
    isMeasured: true,
    engineCount: executed.length || enginesMeasured,
    queriesExecuted: queriesCompleted,
    queriesAttempted,
    queriesFailed: failedRuns,
    brandMentionedCount: queriesFromRecords > 0 ? mentionedFromRecords : 0,
    brandMentionRatePct: queriesFromRecords > 0
      ? Math.round((mentionedFromRecords / queriesFromRecords) * 1000) / 10
      : finiteOrNull(scorecard?.mention_rate_pct),
    brandCitedCount: queriesFromRecords > 0 ? citedFromRecords : 0,
    liveCitationRatePct: queriesFromRecords > 0
      ? Math.round((citedFromRecords / queriesFromRecords) * 1000) / 10
      : finiteOrNull(scorecard?.citation_rate_pct),
    status: 'MEASURED',
    engineDetails,
  };
}

function finiteOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export interface AnswerabilityInput {
  evidenceUrl?: string | null;
  evidenceSnippet?: string | null;
  answerabilityStatus?: string | null;
  citabilityScore?: number | null;
  groundingRatio?: number | null;
}

export interface AnswerabilityConfidence {
  confidencePct: number | null;
  confidenceBasis: string;
  answerabilityPct: number;
  citationReadiness: 'High' | 'Medium' | 'Low';
}

/**
 * A missing passage is a gap, not a 100% confident answer.
 * Confidence is omitted unless the check recorded grounding or citability
 * against a passage that was actually found.
 */
export function answerabilityConfidence(input: AnswerabilityInput): AnswerabilityConfidence {
  const status = (input.answerabilityStatus || '').toUpperCase();
  const answerabilityPct = status === 'ANSWERABLE' ? 100 : status === 'PARTIAL' ? 50 : 0;
  const citability = typeof input.citabilityScore === 'number' ? input.citabilityScore : 0;
  const citationReadiness: 'High' | 'Medium' | 'Low' = citability >= 7 ? 'High' : citability >= 4 ? 'Medium' : 'Low';
  const hasEvidence = Boolean((input.evidenceUrl || '').trim() || (input.evidenceSnippet || '').trim());

  if (!hasEvidence) {
    return {
      confidencePct: null,
      confidenceBasis: 'No supporting passage in the audited sample',
      answerabilityPct,
      citationReadiness,
    };
  }
  if (typeof input.groundingRatio === 'number' && Number.isFinite(input.groundingRatio)) {
    const points = input.groundingRatio <= 1 ? input.groundingRatio * 100 : input.groundingRatio;
    return {
      confidencePct: Math.round(points),
      confidenceBasis: 'Share of claims grounded in a crawled passage',
      answerabilityPct,
      citationReadiness,
    };
  }
  if (citability > 0) {
    return {
      confidencePct: Math.round(citability * 10),
      confidenceBasis: 'Citability recorded against a crawled passage',
      answerabilityPct,
      citationReadiness,
    };
  }
  return {
    confidencePct: null,
    confidenceBasis: 'A passage was found, but no confidence was recorded',
    answerabilityPct,
    citationReadiness,
  };
}
