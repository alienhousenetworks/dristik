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
  { keys: ['gemini'], label: 'Gemini (Google)' },
  { keys: ['qwen'], label: 'Qwen (Alibaba)' },
  { keys: ['deepseek'], label: 'DeepSeek' },
  { keys: ['perplexity'], label: 'Perplexity AI' },
  { keys: ['google_aio', 'aio', 'ai_overviews', 'google_ai'], label: 'Google AI Overviews' },
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
export interface QuestionRatio {
  numerator: number;
  denominator: number;
}

export interface QuestionDenominators {
  /** Questions with a completed assessment, over questions in scope. */
  coverage: QuestionRatio;
  /** Questions with a supporting passage and an answerable status, over questions assessed. */
  answerability: QuestionRatio;
  /** Supported claims over claims evaluated. Null when no claim check was recorded. */
  claimGrounding: QuestionRatio | null;
}

const COMPLETED_QUESTION = new Set(['ANSWERABLE', 'PARTIAL', 'UNANSWERABLE', 'CONFLICTING']);

export interface QuestionMetricInput {
  answerability_status?: string | null;
  evidence_url?: string | null;
  evidence_snippet?: string | null;
  grounding_ratio?: number | null;
  claim_decomposition?: Array<{ status?: string | null; evidence_url?: string | null; evidence_snippet?: string | null }> | null;
}

function hasPassage(question: QuestionMetricInput): boolean {
  return Boolean((question.evidence_url || '').trim() || (question.evidence_snippet || '').trim());
}

/**
 * Coverage, answerability, and claim grounding use different denominators.
 * A finished question check is not an answered question, and evidence
 * coverage of the score is not claim grounding.
 */
export function questionDenominators(questions: QuestionMetricInput[]): QuestionDenominators {
  const completed = questions.filter((question) => COMPLETED_QUESTION.has((question.answerability_status || '').toUpperCase()));
  const answerable = completed.filter((question) => (
    (question.answerability_status || '').toUpperCase() === 'ANSWERABLE' && hasPassage(question)
  ));
  let claimsEvaluated = 0;
  let claimsGrounded = 0;
  let sawClaimCheck = false;
  questions.forEach((question) => {
    const claims = question.claim_decomposition || [];
    if (claims.length > 0) {
      sawClaimCheck = true;
      claimsEvaluated += claims.length;
      claimsGrounded += claims.filter((claim) => (
        (claim.status || '').toUpperCase() === 'SUPPORTED'
        && Boolean((claim.evidence_url || '').trim() || (claim.evidence_snippet || '').trim())
      )).length;
      return;
    }
    if (typeof question.grounding_ratio === 'number' && Number.isFinite(question.grounding_ratio)) {
      sawClaimCheck = true;
      claimsEvaluated += 1;
      const points = question.grounding_ratio <= 1 ? question.grounding_ratio : question.grounding_ratio / 100;
      if (points >= 1 && hasPassage(question)) claimsGrounded += 1;
    }
  });
  return {
    coverage: { numerator: completed.length, denominator: questions.length },
    answerability: { numerator: answerable.length, denominator: completed.length },
    claimGrounding: sawClaimCheck ? { numerator: claimsGrounded, denominator: claimsEvaluated } : null,
  };
}

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
