/**
 * Normalized Report Model for Dristik Editorial Publication.
 * 
 * Separates raw audit engine data from visual templates.
 * Enforces the Zero-Fake rule (no synthetic competitors, no manufactured metrics).
 * Guarantees traceability of all claims back to evidence IDs.
 */

import {
  ExecutiveReport,
  Finding,
  PageEvidence,
  PageReport,
  CodePatch,
  CommercialQueryEvaluation,
  DynamicSandboxQuestionEvaluation,
  CompetitorBakeoffResult,
  CharacterSafeCopy,
  RoadmapItem,
} from '../../types';
import { formatPercentPoints, formatRatioPercent, joinMetricValue } from '../../lib/format';
import { answerabilityConfidence, buildLiveObservation, questionDenominators } from './aiMeasurement';
import { evidenceSupportsFinding } from './evidenceIntegrity';
import { assignEvidenceHashes, EvidenceHashStatus } from './evidenceIntegrity';
import { deriveRemediationClaim, RemediationClaim } from './remediationClaim';
import { finiteNumber } from './scoreLedger';
import { alignDisplayedStory, buildDisplayedScore } from '../../lib/displayedAuditScore';
import { effectiveAfterScore } from '../../lib/patchAnswerDelta';
import { GoogleChannelPayload } from '../../types';

export interface NormalizedEvidenceItem {
  id: string;
  sourceType: string;
  url?: string;
  selector?: string;
  snippet?: string;
  sha256?: string;
  sourceSnapshotSha256?: string;
  hashStatus: EvidenceHashStatus;
  timestamp?: string;
  confidence?: number;
}

export interface NormalizedFinding {
  id: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  category: string;
  confidence?: number;
  observation: string;
  evidenceItems: NormalizedEvidenceItem[];
  businessImpact?: string;
  recommendation?: string;
  verificationNotes?: string;
  codePatch?: CodePatch;
  subObservations?: string[];
}

export interface ScoreLedgerRow {
  pillar: string;
  categoryKey: string;
  rawScore: number | null;
  weightPct: number;
  nominalWeightPct: number;
  contribution: number;
  status: string;
  included: boolean;
}

export interface NormalizedQuestionRecord {
  questionId: string;
  facet: string;
  question: string;
  evidenceRef: string;
  answerabilityPct: number;
  citationReadiness: 'High' | 'Medium' | 'Low';
  confidencePct: number | null;
  confidenceBasis: string;
}

export interface NormalizedFacetSummary {
  facetId: string;
  facetTitle: string;
  questionCount: number;
  answerableCount: number;
  partialCount: number;
  gapCount: number;
  averageCitability: number; // 0-10
  sampleQuestions: DynamicSandboxQuestionEvaluation[];
}

export type GoogleDataState = 'NOT_CONNECTED' | 'NOT_AUTHORIZED' | 'NO_DATA' | 'FETCH_FAILED' | 'MEASURED';

export interface GoogleChannelView {
  state: GoogleDataState;
  notice: string;
  property: string | null;
  period: string | null;
  metrics: Array<{ label: string; value: string }>;
  rows: Array<{ label: string; detail: string }>;
}

const GOOGLE_NOTICES: Record<'search_console' | 'analytics', Record<GoogleDataState, string>> = {
  search_console: {
    NOT_CONNECTED: 'Google Search Console was not connected for this audit. Clicks, impressions, CTR, average position, queries, pages, and indexing coverage were not retrieved.',
    NOT_AUTHORIZED: 'Google Search Console authorization expired or was refused. Search performance was not retrieved.',
    NO_DATA: 'Google Search Console is connected, and the property returned no rows for this period.',
    FETCH_FAILED: 'The Search Console request failed. No clicks or impressions are shown.',
    MEASURED: 'Retrieved from Google Search Console for this audit.',
  },
  analytics: {
    NOT_CONNECTED: 'Google Analytics 4 was not connected for this audit. Sessions, landing pages, engagement, and conversions were not retrieved.',
    NOT_AUTHORIZED: 'Google Analytics authorization expired or was refused. Session data was not retrieved.',
    NO_DATA: 'Google Analytics is connected, and the property returned no sessions metric for this period.',
    FETCH_FAILED: 'The Google Analytics request failed. No sessions are shown.',
    MEASURED: 'Retrieved from Google Analytics 4 for this audit.',
  },
};

function googleState(value: unknown): GoogleDataState {
  if (value === 'MEASURED' || value === 'NOT_AUTHORIZED' || value === 'NO_DATA' || value === 'FETCH_FAILED' || value === 'NOT_CONNECTED') {
    return value;
  }
  return 'NOT_CONNECTED';
}

function formatCount(value: unknown): string | null {
  return typeof value === 'number' && Number.isFinite(value) ? Math.round(value).toLocaleString('en-US') : null;
}

function formatDecimal(value: unknown, digits = 1): string | null {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : null;
}

export function googleChannelView(
  source: 'search_console' | 'analytics',
  raw?: GoogleChannelPayload | null,
): GoogleChannelView {
  const state = googleState(raw?.state);
  const view: GoogleChannelView = {
    state,
    notice: raw?.notice || GOOGLE_NOTICES[source][state],
    property: raw?.property || null,
    period: raw?.period || null,
    metrics: [],
    rows: [],
  };
  if (state !== 'MEASURED') return view;
  if (source === 'search_console') {
    const clicks = formatCount(raw?.clicks);
    const impressions = formatCount(raw?.impressions);
    const ctr = formatDecimal(raw?.average_ctr, 2);
    const position = formatDecimal(raw?.average_position, 1);
    if (clicks != null) view.metrics.push({ label: 'Clicks', value: clicks });
    if (impressions != null) view.metrics.push({ label: 'Impressions', value: impressions });
    if (ctr != null) view.metrics.push({ label: 'Average CTR', value: `${ctr}%` });
    if (position != null) view.metrics.push({ label: 'Average position', value: position });
    (raw?.queries || []).slice(0, 8).forEach((row) => {
      if (!row.query) return;
      const bits = [
        row.page,
        formatCount(row.clicks) != null ? `${formatCount(row.clicks)} clicks` : '',
        formatCount(row.impressions) != null ? `${formatCount(row.impressions)} impressions` : '',
        formatDecimal(row.position, 1) != null ? `position ${formatDecimal(row.position, 1)}` : '',
      ].filter(Boolean);
      view.rows.push({ label: row.query, detail: bits.join(' · ') });
    });
    return view;
  }
  const sessions = formatCount(raw?.sessions);
  const engagement = formatDecimal(raw?.engagement_rate_pct, 1);
  const conversions = formatCount(raw?.conversions);
  if (sessions != null) view.metrics.push({ label: 'Sessions', value: sessions });
  if (engagement != null) view.metrics.push({ label: 'Engagement rate', value: `${engagement}%` });
  if (conversions != null) view.metrics.push({ label: 'Conversions', value: conversions });
  return view;
}

function ttfbQualifier(sampleCount: number): string {
  if (sampleCount <= 0) return 'No server-response sample was recorded.';
  return `Mean of ${sampleCount} sampled URL${sampleCount === 1 ? '' : 's'}, one server-response measurement each. Not a full page load, not Core Web Vitals field data, and not a site-wide performance score.`;
}

function externalAuthorityLabel(authority: ExecutiveReport['external_authority']): string {
  const coverage = (authority as { coverage?: Array<{ data_state?: string }> } | null | undefined)?.coverage;
  const measured = Array.isArray(coverage) && coverage.some((item) => item?.data_state === 'MEASURED' || item?.data_state === 'PARTIALLY_MEASURED');
  return measured ? 'Connected' : 'Not connected';
}

export interface NormalizedReport {
  // Metadata & Identity
  meta: {
    reportId: string;
    analysisId: string;
    domain: string;
    brandName: string;
    websiteUrl: string;
    generatedAt: string;
    policyPack: string;
    certifiedZeroFake: boolean;
    pagesAnalyzed: number;
    discoveredUrlsCount: number | null;
    sampleCoveragePct: number | null;
    evidenceCount: number;
    rawBrandColor?: string;
  };

  // Explicit Evidence & Crawl Coverage Confidence
  coverageConfidence: {
    pagesAudited: number;
    pagesDiscovered: number | null;
    pageCoveragePct: number | null;
    evidenceCoveragePct: number | null;
    answerabilityQuestions: number;
    questionCoverage: { numerator: number; denominator: number };
    answerability: { numerator: number; denominator: number };
    claimGrounding: { numerator: number; denominator: number } | null;
    liveQueriesExecuted: number;
    liveQueriesAttempted: number;
    liveQueriesFailed: number;
    externalAuthorityLabel: string;
    performancePagesCount: number;
    overallEvidenceConfidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'NOT_SCORED';
    scopeLimitationNotice: string;
  };

  // Executive Brief
  brief: {
    leadThesis: string;
    keySignals: {
      overallScore: number | null;
      overallGrade: string;
      technicalScore: number | null;
      geoScore: number | null;
      aeoScore: number | null;
      croScore: number | null;
    };
    whatIsWorking: string[];
    whatNeedsAttention: string[];
    whatMattersNext: string;
    consultantIgnoreAdvice?: string;
  };

  googlePerformance: {
    searchConsole: GoogleChannelView;
    analytics: GoogleChannelView;
  };

  // 5-Pillar Scorecard & Tri-Perspective
  scorecard: {
    overallScore: number | null;
    grade: string;
    confidencePercent: string;
    evidenceCoveragePercent: string;
    calculatedComposite: number | null;
    compositeFormula: string;
    partialCoverage: boolean;
    coverageLabel: string;
    excludedPillars: string[];
    ledger: ScoreLedgerRow[];
    perspectives: {
      human: string;
      searchSpider: string;
      answerEngine: string;
    };
  };

  // Visual Diagnostic Charts & Metrics
  visual: {
    hasRadarData: boolean;
    hasDonutData: boolean;
    hasLatencyData: boolean;
    hasEngineBarData: boolean;
    spotlightMetrics: Array<{ label: string; value: string; significance: string }>;
  };

  // Chapter 01: Discoverability & Technical SEO
  technicalSeo: {
    canonicalDestination: string;
    is301Consolidated: boolean | null;
    redirectChainsCount: number;
    robotsTxtStatus: string;
    sitemapStatus: string;
    http200RateText: string;
    pages: PageEvidence[];
  };

  // Chapter 02: Generative Engine Optimization (GEO)
  geo: {
    dimensions: Array<{ key: string; label: string; band: string; summary: string }>;
    llmsTxtFound: boolean;
    botDirectives: {
      gptBot: string;
      claudeBot: string;
      perplexityBot: string;
    };
    attributionRewrites: Array<{
      currentPassage: string;
      recommendedRewrite: string;
      why?: string;
    }>;
    questions: Array<{
      key: string;
      question: string;
      status: string;
      answer?: string;
      recommendedAnswer?: string;
    }>;
  };

  // Chapter 03: Answer Engine Visibility (AEO)
  aeo: {
    // Explicit Distinction: Live Citation Telemetry vs DOM Extractability & Readiness
    liveObservation: {
      isMeasured: boolean;
      engineCount: number;
      queriesExecuted: number;
      queriesAttempted: number;
      queriesFailed: number;
      brandMentionedCount: number;
      brandMentionRatePct: number | null;
      brandCitedCount: number;
      liveCitationRatePct: number | null;
      status: string;
      engineDetails: Array<{
        engine: string;
        queriesExecuted: number;
        brandMentioned: number;
        brandCited: number;
        citationRatePct: number | null;
        status: string;
      }>;
    };
    readiness: {
      domExtractabilityScore: number | null;
      readinessBand: string;
      citationReadiness: string;
      groundingCoveragePct: number | null;
      answerabilityRatePct: number | null;
    };
    engines: Array<{
      name: string;
      score: number | null;
      status: string;
      retrievalSource: string;
    }>;
    commercialInquiries: CommercialQueryEvaluation[];
    requeryGainPct: number | null;
    sandboxFacets: NormalizedFacetSummary[];
    totalSandboxQuestions: number;
    allSandboxEvaluations: DynamicSandboxQuestionEvaluation[];
    auditedQuestions: NormalizedQuestionRecord[];
  };

  // Chapter 04: Competitive Intelligence & Entity Knowledge Graph
  competitive: {
    chapterTitle: string;
    chapterSubtitle: string;
    chapterDescription: string;
    isRealCompetitorDataAvailable: boolean;
    executionStatus: 'EXECUTED' | 'NOT_EXECUTED';
    notExecutedReason?: string;
    competitorName?: string;
    bakeoffResults?: CompetitorBakeoffResult;
    entitySummary: string;
    schemaTypes: string[];
    schemaAssessmentSummary: string;
    socialMetaStatus: string;
  };

  // Chapter 05: Conversion & Production Copy
  conversion: {
    fiveSecondHook?: string;
    fiveSecondStatus: 'NOT_DETERMINABLE' | 'OBSERVED_COPY';
    fiveSecondNotice: string;
    croBoundary: string;
    formCount: number | null;
    formAccessibilityStatus: string;
    characterSafeCopy?: CharacterSafeCopy;
    contradictions: Array<{ statementA: string; statementB: string; conflict: string }>;
    leadGenOpportunity?: {
      route: string;
      title: string;
      cta: string;
      schemaType: string;
    };
  };

  // Chapter 06: Page-by-Page Audit
  pages: {
    inventory: Array<{
      url: string;
      path: string;
      pageType: string;
      statusCode: number | null;
      wordCount: number;
      ttfbMs: number | null;
      seoScore: number | null;
      copyScore: number | null;
      hook?: string;
      geoSnippet?: string;
      suggestedTitle?: string;
      suggestedH1?: string;
      hero?: string;
      primaryCta?: string;
      bodyRewrite?: string;
      analysis?: string;
      sections?: Array<{ name: string; copy: string }>;
      faqs?: Array<{ question: string; answer: string }>;
      currentTitle?: string;
      suggestedDescription?: string;
      currentDescription?: string;
    }>;
  };

  // Chapter 07: Strategic Priorities & Roadmap
  priorities: {
    top10Actions: Array<{
      rank: number;
      action: string;
      priority: string;
      impact: string;
      effort: string;
      engineerHours: number | null;
      outcome: string;
      validation: string;
      findingId?: string;
      evidenceId?: string;
      affectedRoutes?: string[];
      observed?: string;
      remediationSteps?: string[];
      verificationRule?: string;
      expectedEffect?: string;
    }>;
    roadmapNow: RoadmapItem[];
    roadmapNext: RoadmapItem[];
    roadmapOngoing: RoadmapItem[];
  };

  remediation: RemediationClaim;

  // Methodology
  methodology: {
    auditScope: string;
    crawlDepth: number;
    sampledPagesCount: number;
    verifiedFactCount: number;
    knownLimitations: string[];
  };

  // Appendix: Findings & Ledger
  appendices: {
    findings: NormalizedFinding[];
    patches: CodePatch[];
    evidenceLedger: NormalizedEvidenceItem[];
  };
}

/**
 * Normalizes raw ExecutiveReport into the strictly typed NormalizedReport.
 * Strictly enforces Zero-Fake guarantees.
 */
export function normalizeExecutiveReport(report: ExecutiveReport): NormalizedReport {
  const profile = report.business_profile || ({} as any);
  const resolved = report.resolved_entity;
  const scores = report.scores || ({} as any);
  const rawFindings = report.findings || [];
  const rawPages = report.crawl_manifest?.pages || [];
  const rawPageReports = report.page_reports || [];
  const commEvals = report.commercial_evaluations || [];
  const sandboxEvals = report.dynamic_sandbox_evaluations || [];
  const bakeoff = report.competitor_bakeoff;
  const geoReadiness = report.geo_readiness;
  const perEngine = (report as any).per_engine_geo;

  const domain = report.domain || 'Target Digital Property';
  const brandName = resolved?.name || profile.business_name || domain.replace(/^www\./i, '');

  // 1. Evidence Ledger Normalization
  // `hash` is the per-record payload digest. `content_sha256` is the page
  // snapshot and is shared by every extract from that fetch.
  const evidenceDrafts: Array<NormalizedEvidenceItem & { payloadHash?: string; snapshotHash?: string }> = [];
  const seenEvidenceIds = new Set<string>();
  if (report.evidence_ledger) {
    Object.entries(report.evidence_ledger).forEach(([id, item]: [string, any]) => {
      seenEvidenceIds.add(id);
      evidenceDrafts.push({
        id,
        sourceType: item.source_type || 'html_dom_ast',
        url: item.url,
        selector: item.selector || item.element,
        snippet: item.text || item.snippet,
        payloadHash: item.hash,
        snapshotHash: item.content_sha256,
        hashStatus: 'NOT_SEALED',
        timestamp: item.fetched_at || report.generated_at,
        confidence: item.confidence,
      });
    });
  }

  rawFindings.forEach((f) => {
    (f.evidence || []).forEach((ev) => {
      const evId = ev.evidence_id || `ev_${evidenceDrafts.length + 1}`;
      if (seenEvidenceIds.has(evId)) return;
      seenEvidenceIds.add(evId);
      evidenceDrafts.push({
        id: evId,
        sourceType: ev.source || 'DOM Element Inspection',
        url: ev.url || report.website_url,
        selector: ev.selector || (ev as any).element,
        snippet: ev.snippet || (ev as any).excerpt || (ev as any).value,
        payloadHash: (ev as any).hash,
        snapshotHash: (ev as any).content_sha256,
        hashStatus: 'NOT_SEALED',
        timestamp: report.generated_at,
      });
    });
  });

  const hashDecisions = assignEvidenceHashes(evidenceDrafts.map((item) => ({
    id: item.id,
    payloadHash: item.payloadHash,
    snapshotHash: item.snapshotHash,
  })));
  const evidenceMap = new Map<string, NormalizedEvidenceItem>();
  evidenceDrafts.forEach((item, index) => {
    const decision = hashDecisions[index];
    evidenceMap.set(item.id, {
      id: item.id,
      sourceType: item.sourceType,
      url: item.url,
      selector: item.selector,
      snippet: item.snippet,
      sha256: decision.sha256,
      sourceSnapshotSha256: decision.sourceSnapshotSha256,
      hashStatus: decision.hashStatus,
      timestamp: item.timestamp,
      confidence: item.confidence,
    });
  });

  const evidenceList = Array.from(evidenceMap.values());

  // 2. Findings Normalization
  const normalizedFindings: NormalizedFinding[] = rawFindings.map((f, idx) => {
    const matchedEvidence = (f.evidence_refs || [])
      .map((ref) => evidenceMap.get(ref))
      .filter((item): item is NormalizedEvidenceItem => item !== undefined);

    const claimText = `${f.title || ''} ${f.description || ''}`;
    const inlineEvidence = (f.evidence || []).map((e, i) => ({
      id: e.evidence_id || `ev_inline_${i + 1}`,
      sourceType: e.source || 'DOM Ast',
      url: e.url,
      selector: e.selector,
      snippet: e.snippet,
      sha256: (e as { hash?: string }).hash,
      hashStatus: (e as { hash?: string }).hash ? 'SEALED' as const : 'NOT_SEALED' as const,
    }));
    const citedEvidence = (matchedEvidence.length > 0 ? matchedEvidence : inlineEvidence)
      .filter((item) => evidenceSupportsFinding(claimText, item));

    return {
      id: f.finding_id || `F-${String(idx + 1).padStart(3, '0')}`,
      title: f.title || 'Technical Discrepancy',
      severity: (f.severity?.toUpperCase() as any) || 'MEDIUM',
      category: f.category || 'TECHNICAL_SEO',
      confidence: f.confidence,
      observation: f.description || '',
      evidenceItems: citedEvidence,
      businessImpact: f.business_impact,
      recommendation: f.recommendation,
      verificationNotes: f.verification_notes,
      codePatch: f.code_patch || (report.code_patches || []).find((p) => p.patch_id === (f as any).patch_id),
      subObservations: f.sub_observations,
    };
  });

  // 3. Dynamic Sandbox Facet Grouping
  const facetMap = new Map<string, DynamicSandboxQuestionEvaluation[]>();
  sandboxEvals.forEach((q) => {
    const fId = q.facet || 'General Capabilities';
    if (!facetMap.has(fId)) facetMap.set(fId, []);
    facetMap.get(fId)!.push(q);
  });

  const normalizedFacets: NormalizedFacetSummary[] = Array.from(facetMap.entries()).map(
    ([facetId, qList]) => {
      const answerable = qList.filter((q) => q.answerability_status === 'ANSWERABLE').length;
      const partial = qList.filter((q) => q.answerability_status === 'PARTIAL').length;
      const gap = qList.filter((q) => q.answerability_status === 'UNANSWERABLE').length;
      const avgCit = Math.round(
        qList.reduce((acc, q) => acc + (q.citability_score || 0), 0) / (qList.length || 1)
      );

      return {
        facetId,
        facetTitle: facetId,
        questionCount: qList.length,
        answerableCount: answerable,
        partialCount: partial,
        gapCount: gap,
        averageCitability: avgCit,
        sampleQuestions: qList.slice(0, 3),
      };
    }
  );

  // 4. Re-Query Uplift Delta Calculation
  let requeryGainPct: number | null = null;
  if (commEvals.length > 0) {
    const beforeAvg = commEvals.reduce((acc, e) => acc + e.before_score, 0) / commEvals.length;
    const afterList = commEvals.filter((e) => e.after_score != null);
    if (afterList.length > 0) {
      const afterAvg = afterList.reduce((acc, e) => acc + (effectiveAfterScore(e) ?? e.before_score), 0) / afterList.length;
      const deltaPoints = Math.round((afterAvg - beforeAvg) * 10);
      requeryGainPct = deltaPoints === 0 ? null : deltaPoints;
    }
  }

  // 5. Zero-Fake Competitive Verification
  // Rule: If bakeoff is present and has real competitor names (not competitor-a.com / placeholder), allow it.
  const hasLegitCompetitor = Boolean(
    bakeoff &&
    bakeoff.competitor_domain &&
    !bakeoff.competitor_domain.includes('competitor-a') &&
    !bakeoff.competitor_domain.includes('placeholder')
  );

  // 6. One score for the cover, the grade, and the ledger.
  // Live citation is never copied from the on-page GEO score. A missing
  // pillar is excluded. A measured zero stays a zero.
  const authoritative = buildDisplayedScore(report);
  const scoreLedger: ScoreLedgerRow[] = authoritative.rows;
  const calculatedComposite = authoritative.composite;
  const technicalScore = scoreLedger.find((row) => row.categoryKey === 'TECHNICAL_SEO')?.rawScore ?? null;
  const geoScore = scoreLedger.find((row) => row.categoryKey === 'GEO')?.rawScore ?? null;
  const aeoScore = scoreLedger.find((row) => row.categoryKey === 'AEO')?.rawScore ?? null;
  const croScore = scoreLedger.find((row) => row.categoryKey === 'UX_CONVERSION')?.rawScore ?? null;

  const auditedQuestions: NormalizedQuestionRecord[] = sandboxEvals.map((q, idx) => {
    const matchedEvidence = q.evidence_url
      ? Array.from(evidenceMap.values()).find((item) => item.url === q.evidence_url || item.id === q.evidence_url)
      : undefined;
    const hasPassage = Boolean(q.evidence_url || q.evidence_snippet);
    const judged = answerabilityConfidence({
      evidenceUrl: q.evidence_url,
      evidenceSnippet: q.evidence_snippet,
      answerabilityStatus: q.answerability_status,
      citabilityScore: q.citability_score,
      groundingRatio: q.grounding_ratio,
    });
    return {
      questionId: q.question_id || `Q-${String(idx + 1).padStart(3, '0')}`,
      facet: q.facet || 'General Capabilities',
      question: q.generated_question,
      evidenceRef: matchedEvidence?.id || (hasPassage ? 'Passage recorded' : 'No evidence'),
      answerabilityPct: judged.answerabilityPct,
      citationReadiness: judged.citationReadiness,
      confidencePct: judged.confidencePct,
      confidenceBasis: judged.confidenceBasis,
    };
  });

  const liveObservation = buildLiveObservation(report.ai_visibility_scorecard);
  const questionMetrics = questionDenominators(sandboxEvals);

  const competitiveChapterTitle = hasLegitCompetitor
    ? 'Competitive Intelligence & Knowledge Graph'
    : 'Knowledge Graph & Entity Readiness';
  const competitiveChapterSubtitle = hasLegitCompetitor
    ? 'PEER-SET BENCHMARK & SCHEMA ENTITY MAPPING'
    : 'SEMANTIC SCHEMA & MACHINE-READABLE ENTITY MAPPING';
  const competitiveChapterDesc = hasLegitCompetitor
    ? 'Machine-readable entity graph crosscheck, structured data verification, and head-to-head evaluation on commercial buyer queries against verified industry peers.'
    : 'Machine-readable entity graph crosscheck, structured data verification, and first-party semantic knowledge extraction.';

  const manifest = report.crawl_manifest as (typeof report.crawl_manifest & {
    total_discovered_urls?: number;
    crawl_budget?: { discovery_truncated?: boolean };
  }) | undefined;
  const discoveredRaw = finiteNumber(manifest?.total_pages_discovered) ?? finiteNumber(manifest?.total_discovered_urls);
  const totalDiscovered = discoveredRaw != null && discoveredRaw > 0 ? Math.max(discoveredRaw, rawPages.length) : null;
  const discoveryTruncated = Boolean(
    (manifest?.crawl_health as { discovery_truncated?: boolean } | undefined)?.discovery_truncated
    || manifest?.crawl_budget?.discovery_truncated,
  );
  const sampleCoverage = totalDiscovered
    ? Math.round((rawPages.length / totalDiscovered) * 1000) / 10
    : null;
  const evidenceCoverageRatio = finiteNumber(scores.evidence_coverage);
  const evidenceCoveragePct = evidenceCoverageRatio == null
    ? null
    : (evidenceCoverageRatio <= 1 ? Math.round(evidenceCoverageRatio * 1000) / 10 : evidenceCoverageRatio);
  const evidenceConfidence: NormalizedReport['coverageConfidence']['overallEvidenceConfidence'] = evidenceCoveragePct == null
    ? 'NOT_SCORED'
    : evidenceCoveragePct >= 80 ? 'HIGH' : evidenceCoveragePct >= 50 ? 'MEDIUM' : 'LOW';
  const remediation = deriveRemediationClaim(report.code_patches || []);
  const ttfbSamples = rawPages.filter((page) => typeof page.ttfb_ms === 'number' && Number.isFinite(page.ttfb_ms));
  const ttfbMean = ttfbSamples.length
    ? Math.round(ttfbSamples.reduce((sum, page) => sum + (page.ttfb_ms || 0), 0) / ttfbSamples.length)
    : null;

  return {
    meta: {
      reportId: report.report_id || `rpt_${Date.now()}`,
      analysisId: report.analysis_id || report.report_id || 'unspecified_run',
      domain,
      brandName,
      websiteUrl: report.website_url,
      generatedAt: report.generated_at || new Date().toISOString(),
      policyPack: report.policy_pack || 'enterprise_web_intel_v4',
      certifiedZeroFake: report.certification_status === 'CERTIFIED',
      pagesAnalyzed: rawPages.length,
      discoveredUrlsCount: totalDiscovered,
      sampleCoveragePct: sampleCoverage,
      evidenceCount: evidenceList.length,
      rawBrandColor: (report as any).theme_color || (report as any).brand_color,
    },

    coverageConfidence: {
      pagesAudited: rawPages.length,
      pagesDiscovered: totalDiscovered,
      pageCoveragePct: sampleCoverage,
      evidenceCoveragePct,
      answerabilityQuestions: sandboxEvals.length,
      questionCoverage: questionMetrics.coverage,
      answerability: questionMetrics.answerability,
      claimGrounding: questionMetrics.claimGrounding,
      liveQueriesExecuted: liveObservation.queriesExecuted,
      liveQueriesAttempted: liveObservation.queriesAttempted,
      liveQueriesFailed: liveObservation.queriesFailed,
      externalAuthorityLabel: externalAuthorityLabel(report.external_authority),
      performancePagesCount: rawPages.filter((page) => page.ttfb_ms != null).length,
      overallEvidenceConfidence: evidenceConfidence,
      scopeLimitationNotice: totalDiscovered
        ? `The score applies only to the ${rawPages.length} analyzed URL${rawPages.length === 1 ? '' : 's'} out of ${totalDiscovered} discovered. Uncrawled URLs are not in the score.${discoveryTruncated ? ' The sitemap listing stopped at the discovery cap, so the discovered count is a floor, not the size of the site.' : ''}`
        : `The score applies only to the ${rawPages.length} analyzed URL${rawPages.length === 1 ? '' : 's'}. The crawl did not record how many URLs were discovered.`,
    },

    googlePerformance: {
      searchConsole: googleChannelView('search_console', report.google_performance?.search_console),
      analytics: googleChannelView('analytics', report.google_performance?.analytics),
    },

    brief: {
      leadThesis: alignDisplayedStory(
        report.story_summary ||
        `Audit of ${rawPages.length} sampled URL${rawPages.length === 1 ? '' : 's'} for ${brandName}. No executive narrative was sealed for this run.`,
        scores.overall_score,
        authoritative,
      ),
      keySignals: {
        overallScore: calculatedComposite,
        overallGrade: authoritative.grade,
        technicalScore,
        geoScore,
        aeoScore,
        croScore,
      },
      whatIsWorking: (report.what_site_gets_right || []).slice(0, 4),
      whatNeedsAttention: (report.what_is_holding_it_back || []).slice(0, 4),
      whatMattersNext:
        report.primary_strategic_opportunity ||
        'No next action was sealed for this run.',
      consultantIgnoreAdvice: report.consultant_advice_what_to_ignore,
    },

    scorecard: {
      overallScore: calculatedComposite,
      grade: authoritative.grade,
      confidencePercent: formatRatioPercent(finiteNumber(scores.overall_confidence)),
      evidenceCoveragePercent: evidenceCoveragePct == null ? '—' : formatPercentPoints(evidenceCoveragePct),
      calculatedComposite,
      compositeFormula: authoritative.formula,
      partialCoverage: authoritative.partialCoverage,
      coverageLabel: authoritative.coverageLabel,
      excludedPillars: authoritative.excludedPillars,
      ledger: scoreLedger,
      perspectives: {
        human:
          report.three_way_comparison?.human_visitor_perspective ||
          'No visitor-perspective note was sealed for this run.',
        searchSpider:
          report.three_way_comparison?.search_engine_perspective ||
          'No search-engine perspective was sealed for this run.',
        answerEngine:
          report.three_way_comparison?.ai_answer_engine_perspective ||
          'No answer-engine perspective was sealed for this run.',
      },
    },

    visual: {
      hasRadarData: Boolean(report.visual_intelligence?.selected_visualizations?.some((c) => c.chart_type === 'radar')),
      hasDonutData: Boolean(report.findings && report.findings.length > 0),
      hasLatencyData: Boolean(rawPages.some((p) => p.ttfb_ms != null)),
      hasEngineBarData: Boolean(perEngine != null),
      spotlightMetrics: (report.visual_intelligence?.spotlight_metrics
        ? report.visual_intelligence.spotlight_metrics.map((m) => ({
            label: m.label,
            value: joinMetricValue(m.value, m.unit),
            significance: /ttfb|time-to-first-byte|server response/i.test(`${m.label} ${m.significance}`)
              ? `${m.significance} ${ttfbQualifier(ttfbSamples.length)}`
              : m.significance,
          }))
        : [
            { label: 'Sampled Pages', value: String(rawPages.length), significance: 'Crawl depth across critical routes' },
            { label: 'Verified Findings', value: String(rawFindings.length), significance: 'Deterministic issues detected' },
            {
              label: 'Sampled server TTFB',
              value: ttfbMean == null ? 'Not measured' : `${ttfbMean} ms`,
              significance: ttfbQualifier(ttfbSamples.length),
            },
            { label: 'Evidence Ledger', value: `${evidenceList.length} items`, significance: 'Source-linked audit facts. A content hash checks integrity, not correctness.' },
          ]
      ).slice(0, 4),
    },

    technicalSeo: {
      canonicalDestination: report.host_and_redirects?.canonical_destination || report.website_url,
      is301Consolidated: report.host_and_redirects?.proper_301_consolidation ?? null,
      redirectChainsCount: report.host_and_redirects?.chains_recorded?.length ?? 0,
      robotsTxtStatus: report.crawl_manifest?.robots_txt_found ? 'Accessible (Crawl Directives Active)' : 'Missing robots.txt directives',
      sitemapStatus: report.crawl_manifest?.sitemap_found ? `Discovered: ${report.crawl_manifest?.sitemap_url || 'Active'}` : 'Missing XML sitemap declaration in robots.txt',
      http200RateText: `${rawPages.filter((p) => p.status_code === 200).length} of ${rawPages.length} sampled URLs returned HTTP 200 OK`,
      pages: rawPages,
    },

    geo: {
      dimensions: geoReadiness?.dimensions || [],
      llmsTxtFound: rawPages.some((p) => p.url.endsWith('llms.txt')),
      botDirectives: {
        gptBot: (report.crawl_manifest?.robots_txt_content || '').includes('GPTBot') ? 'Explicit Directive Declared' : 'Default Permitted (No Block)',
        claudeBot: (report.crawl_manifest?.robots_txt_content || '').includes('ClaudeBot') ? 'Explicit Directive Declared' : 'Default Permitted',
        perplexityBot: (report.crawl_manifest?.robots_txt_content || '').includes('PerplexityBot') ? 'Explicit Directive Declared' : 'Default Permitted',
      },
      attributionRewrites: ((geoReadiness?.citation_passages?.rewrite_recommendations || []) as any[]).map((rw) => ({
        currentPassage: rw.current_passage || '',
        recommendedRewrite: rw.recommended_rewrite || '',
        why: rw.why,
      })).filter((rw) => rw.recommendedRewrite && rw.recommendedRewrite !== rw.currentPassage),
      questions: ((geoReadiness?.questions || []) as any[]).map((q) => ({
        key: q.question_key || '',
        question: q.question || '',
        status: (q.status || 'UNSUPPORTED').toUpperCase(),
        answer: q.answer_snippet || q.answer || '',
        recommendedAnswer: q.recommended_answer || '',
      })),
    },

    aeo: {
      liveObservation,
      readiness: {
        domExtractabilityScore: geoScore,
        readinessBand: geoScore == null ? 'Not measured' : geoScore >= 75 ? 'High' : (geoScore >= 50 ? 'Medium' : 'Low'),
        citationReadiness: geoScore == null ? 'Not measured' : geoScore >= 75 ? 'High' : 'Medium',
        groundingCoveragePct: questionMetrics.claimGrounding && questionMetrics.claimGrounding.denominator > 0
          ? Math.round((questionMetrics.claimGrounding.numerator / questionMetrics.claimGrounding.denominator) * 1000) / 10
          : null,
        answerabilityRatePct: sandboxEvals.length > 0
          ? Math.round((sandboxEvals.filter((q) => q.answerability_status === 'ANSWERABLE').length / sandboxEvals.length) * 100)
          : null,
      },
      engines: (['chatgpt', 'perplexity', 'google_aio', 'claude', 'gemini'] as const).flatMap((key) => {
        const row = perEngine?.[key];
        const score = finiteNumber(row?.score);
        if (score == null) return [];
        const names: Record<string, string> = {
          chatgpt: 'ChatGPT Search (OpenAI)',
          perplexity: 'Perplexity AI',
          google_aio: 'Google AI Overviews',
          claude: 'Claude (Anthropic)',
          gemini: 'Gemini (Google)',
        };
        return [{
          name: names[key],
          score,
          status: row?.readiness_band || 'Measured',
          retrievalSource: 'On-page extractability for this engine profile. Not a live citation count.',
        }];
      }),
      commercialInquiries: commEvals,
      requeryGainPct,
      sandboxFacets: normalizedFacets,
      totalSandboxQuestions: sandboxEvals.length,
      allSandboxEvaluations: sandboxEvals,
      auditedQuestions,
    },

    competitive: {
      chapterTitle: competitiveChapterTitle,
      chapterSubtitle: competitiveChapterSubtitle,
      chapterDescription: competitiveChapterDesc,
      isRealCompetitorDataAvailable: hasLegitCompetitor,
      executionStatus: hasLegitCompetitor ? 'EXECUTED' : 'NOT_EXECUTED',
      notExecutedReason: hasLegitCompetitor ? undefined : 'Competitor crawl connector unavailable or unprovisioned for this audit execution run.',
      competitorName: hasLegitCompetitor ? bakeoff?.competitor_domain : undefined,
      bakeoffResults: hasLegitCompetitor ? bakeoff : undefined,
      entitySummary: (report.geo_readiness?.schema_crosscheck as any)?.summary || 'No schema cross-check summary was recorded.',
      schemaTypes: report.geo_readiness?.schema_types || [],
      schemaAssessmentSummary: finiteNumber((report.geo_readiness?.schema_crosscheck as any)?.quality_score) == null
        ? 'Schema quality was not scored'
        : `${finiteNumber((report.geo_readiness?.schema_crosscheck as any)?.quality_score)}/100 Schema Integrity`,
      socialMetaStatus: rawPages.some((p) => p.og_tags && Object.keys(p.og_tags).length > 0)
        ? 'Open Graph tags present on at least one sampled page'
        : 'No Open Graph tags recorded on the sampled pages',
    },

    conversion: {
      fiveSecondHook: Array.isArray(rawPages[0]?.h1) ? rawPages[0]?.h1?.[0] : undefined,
      fiveSecondStatus: 'NOT_DETERMINABLE',
      fiveSecondNotice: Array.isArray(rawPages[0]?.h1) && rawPages[0]?.h1?.[0]
        ? 'The line above is the crawled H1. A timed five-second comprehension test was not run, so comprehension was not scored.'
        : 'A five-second value-proposition test was not determinable from the crawled evidence. No timed comprehension result is reported.',
      croBoundary: [
        'This CRO figure covers observable copy and DOM checks on the analyzed pages.',
        (report as any).form_audit ? 'A form screen ran. It is an automated label check, not a WCAG certification.' : 'No form audit ran.',
        report.google_performance?.analytics?.state === 'MEASURED'
          ? 'Analytics supplied visitor numbers for this run.'
          : 'GA4 was not connected, so conversion rate, funnel abandonment, and revenue were not measured.',
      ].join(' '),
      formCount: (report as any).form_audit
        ? finiteNumber((report as any).form_audit.total_forms_detected ?? (report as any).form_audit.total_forms_found)
        : (report as any).cro_audit?.form_friction
          ? finiteNumber((report as any).cro_audit.form_friction.total_forms_detected)
          : null,
      formAccessibilityStatus: !(report as any).form_audit && !(report as any).cro_audit?.form_friction
        ? 'Not measured'
        : (((report as any).form_audit?.forms_with_missing_labels === 0) || ((report as any).cro_audit?.form_friction?.forms_with_missing_labels === 0) || (report as any).form_audit?.wcag_accessible)
          ? 'Automated screening: labels present'
          : 'Automated screening: unlabeled inputs',
      characterSafeCopy: report.character_safe_copy,
      contradictions: (report.contradictions || []).map((c) => ({
        statementA: c.declared_type || c.contradiction_type,
        statementB: c.detected_type || 'Observed DOM Value',
        conflict: c.reason,
      })),
    },

    pages: {
      inventory: rawPages.map((page) => {
        const pageKey = (page.url || '').trim().replace(/\/+$/, '').toLowerCase();
        const rep = rawPageReports.find((r) => {
          const reportKey = (r.url || '').trim().replace(/\/+$/, '').toLowerCase();
          return r.url === page.url || reportKey === pageKey;
        });
        const routePath = page.url.replace(/^https?:\/\/[^/]+/, '') || '/';
        const sug = rep?.copywriting?.suggested as any;
        const text = (...values: unknown[]) => {
          const found = values.find((value) => typeof value === 'string' && value.trim());
          return typeof found === 'string' ? found.trim() : undefined;
        };
        const written = rep?.copywriting?.llm_status === 'ok';
        const sections = Array.isArray(sug?.sections)
          ? sug.sections
              .map((section: any) => ({
                name: text(section?.section_name, section?.name) || 'Section',
                copy: text(section?.suggested_copy, section?.rewrite, section?.copy) || '',
              }))
              .filter((section: { copy: string }) => section.copy)
          : [];
        const faqs = Array.isArray(sug?.faq_items)
          ? sug.faq_items
              .map((faq: any) => ({
                question: text(faq?.question) || '',
                answer: text(faq?.answer) || '',
              }))
              .filter((faq: { question: string; answer: string }) => faq.question || faq.answer)
          : [];

        return {
          url: page.url,
          path: routePath,
          pageType: page.page_type || 'General Page',
          statusCode: page.status_code,
          wordCount: page.word_count || 0,
          ttfbMs: page.ttfb_ms,
          seoScore: rep?.seo?.score != null ? Math.round(rep.seo.score) : null,
          copyScore: written && rep?.copywriting?.score != null ? Math.round(rep.copywriting.score) : null,
          hook: text(sug?.hook_3sec, sug?.hook),
          geoSnippet: text(sug?.geo_snippet, sug?.snippet),
          suggestedTitle: text(sug?.title, sug?.title_tag, sug?.proposed_title, sug?.recommended_title),
          suggestedH1: text(sug?.h1, sug?.headline),
          hero: text(sug?.hero, sug?.hero_subhead),
          primaryCta: text(sug?.primary_cta, sug?.cta),
          bodyRewrite: text(sug?.body_rewrite, sug?.full_rewrite),
          analysis: written ? text(rep?.copywriting?.analysis) : undefined,
          sections,
          faqs,
          currentTitle: page.title,
          suggestedDescription: text(sug?.meta_description, sug?.description, sug?.meta),
          currentDescription: page.meta_description,
        };
      }),
    },

    priorities: {
      top10Actions: (report.top_10_actions?.actions || []).slice(0, 10).map((act, i) => ({
        rank: act.rank || i + 1,
        action: act.action,
        priority: act.priority || '',
        impact: act.impact || '',
        effort: act.effort || '',
        engineerHours: finiteNumber(act.estimated_engineer_hours),
        outcome: act.expected_outcome || '',
        validation: act.validation || '',
        findingId: act.related_finding_id,
      })),
      roadmapNow: report.roadmap_7_days || [],
      roadmapNext: report.roadmap_30_days || [],
      roadmapOngoing: report.roadmap_90_days || [],
    },

    remediation,

    methodology: {
      auditScope: liveObservation.queriesAttempted > 0
        ? `DOM analysis of ${rawPages.length} URL${rawPages.length === 1 ? '' : 's'}. Live AI queries: ${liveObservation.queriesAttempted} attempted, ${liveObservation.queriesExecuted} completed, ${liveObservation.queriesFailed} failed.`
        : `DOM analysis of ${rawPages.length} URL${rawPages.length === 1 ? '' : 's'}. Live AI engines were not queried on this run.`,
      crawlDepth: 0,
      sampledPagesCount: rawPages.length,
      verifiedFactCount: evidenceList.length,
      knownLimitations: [
        'Chrome User Experience Report (CrUX) publishes real-user 28-day Core Web Vitals only for origins with sufficient Chrome traffic volume.',
        liveObservation.isMeasured
          ? 'Citation figures count only the engine responses that completed on this run. On-page extractability is a separate measurement.'
          : 'Live answer-engine citations were not measured on this run. On-page extractability is not a citation rate.',
        'Zero-Fake enforcement: Unmeasured dimensions are explicitly labeled as unmeasured rather than estimated.',
      ],
    },

    appendices: {
      findings: normalizedFindings,
      patches: report.code_patches || [],
      evidenceLedger: evidenceList,
    },
  };
}
