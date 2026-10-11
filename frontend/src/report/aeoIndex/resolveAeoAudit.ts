import { ExecutiveReport } from '../../types';
import { AEO_SECTIONS } from './catalog';

export type AeoStatus =
  | 'ISSUE_SAMPLE'
  | 'CLEAN_SAMPLE'
  | 'VERIFIED'
  | 'INFERRED'
  | 'DATA_UNAVAILABLE'
  | 'NOT_TESTED'
  | 'NOT_APPLICABLE';

export const AEO_STATUS_LABEL: Record<AeoStatus, string> = {
  ISSUE_SAMPLE: 'Sample verified · issue',
  CLEAN_SAMPLE: 'Sample verified · no issue',
  VERIFIED: 'Verified',
  INFERRED: 'Inferred',
  DATA_UNAVAILABLE: 'Data unavailable',
  NOT_TESTED: 'Not tested',
  NOT_APPLICABLE: 'Not applicable',
};

export interface AeoCheckResult {
  label: string;
  status: AeoStatus;
  result: string;
}

export interface AeoSectionResult {
  number: string;
  part: string;
  title: string;
  status: AeoStatus;
  summary: string;
  checks: AeoCheckResult[];
}

export interface ResolvedAeoAudit {
  sampleNotice: string;
  sections: AeoSectionResult[];
  counts: Record<AeoStatus, number>;
}

const SEPARATION =
  'Content readiness describes the source. Observed answer visibility is a documented engine result. Business impact is measured separately. These three are not combined into one AEO grade.';

const LIMIT =
  ' Validation: review the updated page against the stored question and rerun that question under the same documented conditions. Success metrics are answer completeness, factual accuracy, and, when a live run exists, mention rate and citation rate. Limitation: a clearer page does not guarantee that an answer engine will select or cite it.';

const INTENT_RULES: Array<[string, string[]]> = [
  ['definition', ['what is', 'define', 'definition', 'meaning of']],
  ['explanatory', ['why ', 'explain', 'how does']],
  ['how-to', ['how to', 'how do i', 'step']],
  ['troubleshooting', ['error', 'not working', 'troubleshoot', 'fix ']],
  ['comparison', [' vs ', 'versus', 'compare', 'alternative', 'difference']],
  ['best', ['best ', 'top ']],
  ['recommendation', ['recommend', 'should i', 'which product']],
  ['pricing', ['price', 'pricing', 'cost', 'fee']],
  ['eligibility', ['eligib', 'qualif', 'who can']],
  ['location', ['where ', 'location', 'near me', 'available in']],
  ['transactional', ['buy', 'sign up', 'order', 'book ', 'subscribe']],
  ['navigational', ['login', 'official site', 'contact']],
  ['opinion', ['review', 'worth', 'opinion']],
];

type Result = [AeoStatus, string];

interface QuestionRow {
  qid: string;
  text: string;
  status: string;
  intent: string;
  url: string;
  gap: string;
  facet: string;
}

interface Facts {
  domain: string;
  generatedAt: string;
  pages: any[];
  crawled: number;
  discovered: number;
  sample: string;
  profile: any;
  questions: QuestionRow[];
  questionSource: string;
  assessed: number;
  usable: number;
  partial: number;
  unanswered: number;
  conflicting: number;
  card: any;
  runs: number;
  engines: string[];
  surfaces: string[];
  kind: string;
  rates: Record<string, number | null>;
  simulation: string;
  infoGain: number | null;
  robotsMeasured: boolean;
  bots: any;
  extractability: number | null;
  schemaTypes: string[];
  cross: any;
  entity: any;
  claims: any;
  passages: any;
  contradictions: any[];
  bakeoff: any;
  bakeItems: any[];
  gscState: string;
  ga4State: string;
  analytics: any;
  findings: any[];
  intl: any;
  manifest: any;
}

function num(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  return null;
}

function pct(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function has(label: string, ...needles: string[]): boolean {
  const low = label.toLowerCase();
  return needles.some((needle) => low.includes(needle));
}

function join(items: string[], limit = 6): string {
  const rows = items.map((item) => String(item || '').trim()).filter(Boolean);
  if (rows.length === 0) return 'none recorded';
  const shown = rows.slice(0, limit);
  const extra = rows.length - shown.length;
  return shown.join('; ') + (extra ? ` (+${extra} more)` : '');
}

function clip(value: unknown, limit = 180): string {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.length <= limit) return text;
  return text.slice(0, limit - 1).trimEnd() + '…';
}

function questionStatus(raw: unknown, isAnswerable: unknown): string {
  const status = String(raw || '').toUpperCase();
  if (status === 'ANSWERABLE' || status === 'SUPPORTED') {
    return isAnswerable === false ? 'UNANSWERABLE' : 'ANSWERABLE';
  }
  if (status === 'PARTIAL') return 'PARTIAL';
  if (['UNANSWERABLE', 'UNSUPPORTED', 'MISSING', 'BLIND'].includes(status)) return 'UNANSWERABLE';
  if (status === 'CONFLICTING' || status === 'CONFLICT') return 'CONFLICTING';
  if (isAnswerable === true) return 'ANSWERABLE';
  if (isAnswerable === false) return 'UNANSWERABLE';
  return 'UNASSESSED';
}

function intentBucket(text: string): string {
  const low = ` ${text.toLowerCase()} `;
  for (const [name, needles] of INTENT_RULES) {
    if (needles.some((needle) => low.includes(needle))) return name;
  }
  return 'unclassified';
}

function listOf(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

function buildFacts(report: ExecutiveReport): Facts {
  const anyReport = report || ({} as ExecutiveReport);
  const manifest = anyReport.crawl_manifest;
  const pages = listOf(manifest?.pages).length ? listOf(manifest?.pages) : listOf(anyReport.page_reports);
  const crawled = pages.length;
  const discovered = num(manifest?.total_pages_discovered) || 0;
  let sample = 'No page was crawled on this run. Dristik uses a representative sample.';
  if (crawled > 0 && discovered > crawled) {
    sample = `Representative sample: ${crawled} crawled page(s) of ${discovered} discovered URLs. This is not every URL on the site.`;
  } else if (crawled > 0) {
    sample = `Representative sample: ${crawled} crawled page(s). This is not every URL on the site.`;
  }
  const geo = anyReport.geo_readiness;
  const questions = loadQuestions(anyReport, geo);
  const card = anyReport.ai_visibility_scorecard;
  const runs = card ? num(card.successful_runs) || 0 : 0;
  const surfaces = listOf(card?.surfaces_not_queried).map(String).filter(Boolean);
  const matrix = anyReport.per_engine_geo as any;
  const gain = matrix?.information_gain;
  const bots = matrix?.ai_bot_directives;
  const performance = (anyReport.google_performance || {}) as any;
  const search = performance.search_console || {};
  const analytics = performance.analytics || {};
  const bake = anyReport.competitor_bakeoff as any;
  const bakeItems = listOf(bake?.evaluations);
  const schemaTypes: string[] = [];
  for (const name of listOf(geo?.schema_types)) {
    if (!schemaTypes.includes(String(name))) schemaTypes.push(String(name));
  }
  for (const page of pages) {
    for (const name of listOf(page?.schema_types)) {
      if (!schemaTypes.includes(String(name))) schemaTypes.push(String(name));
    }
  }
  const rate = (value: unknown) => (runs > 0 ? num(value) : null);
  return {
    domain: anyReport.domain || 'this site',
    generatedAt: anyReport.generated_at || 'the audit run',
    pages,
    crawled,
    discovered,
    sample,
    profile: anyReport.business_profile,
    questions: questions.rows,
    questionSource: questions.source,
    assessed: questions.rows.length,
    usable: questions.rows.filter((item) => item.status === 'ANSWERABLE').length,
    partial: questions.rows.filter((item) => item.status === 'PARTIAL').length,
    unanswered: questions.rows.filter((item) => item.status === 'UNANSWERABLE').length,
    conflicting: questions.rows.filter((item) => item.status === 'CONFLICTING').length,
    card,
    runs,
    engines: listOf(card?.engines_queried).map(String).filter(Boolean),
    surfaces: card && surfaces.length === 0 ? ['Google AI Overviews', 'Google AI Mode', 'Bing Copilot'] : surfaces,
    kind: String(card?.measurement_kind || ''),
    rates: {
      mention: rate(card?.mention_rate_pct),
      citation: rate(card?.citation_rate_pct),
      citation_accuracy: rate(card?.citation_accuracy_pct),
      entity_accuracy: rate(card?.entity_accuracy_pct),
      competitor: rate(card?.competitor_visibility_pct),
      hallucination: rate(card?.hallucination_rate_pct),
    },
    simulation: String(matrix?.measurement_mode || ''),
    infoGain: gain ? num(gain.score) : null,
    robotsMeasured: Boolean(bots?.robots_measured),
    bots: bots?.robots_measured ? bots : null,
    extractability: num(geo?.extractability_score),
    schemaTypes,
    cross: geo?.schema_crosscheck || {},
    entity: geo?.entity_consistency || {},
    claims: geo?.claims_analysis || {},
    passages: geo?.citation_passages || {},
    contradictions: listOf((anyReport as any).contradictions),
    bakeoff: bakeItems.length ? bake : null,
    bakeItems,
    gscState: String(search.state || 'NOT_CONNECTED'),
    ga4State: String(analytics.state || 'NOT_CONNECTED'),
    analytics,
    findings: listOf(anyReport.findings),
    intl: (anyReport as any).international_seo,
    manifest,
  };
}

function loadQuestions(report: ExecutiveReport, geo: ExecutiveReport['geo_readiness']): { rows: QuestionRow[]; source: string } {
  const sandbox = listOf(report.dynamic_sandbox_evaluations);
  if (sandbox.length) {
    return {
      source: 'the on-page answer sandbox',
      rows: sandbox.map((item) => {
        const text = item.generated_question || '';
        const aspects = listOf(item.missing_aspects).map(String);
        const gap = clip(item.gap_analysis || (aspects.length ? `Missing aspects: ${join(aspects, 4)}` : ''));
        return {
          qid: item.question_id || '',
          text,
          status: questionStatus(item.answerability_status, item.is_answerable),
          intent: intentBucket(`${text} ${item.buyer_intent || ''} ${item.facet || ''}`),
          url: item.evidence_url || item.target_update_page || '',
          gap,
          facet: item.facet || '',
        };
      }),
    };
  }
  const geoQuestions = listOf(geo?.questions);
  if (geoQuestions.length) {
    return { source: 'the stored geo question list', rows: geoQuestions.map(fromGeo) };
  }
  const graph = geo?.question_graph_50;
  const graphQuestions = listOf(graph?.questions);
  if (graphQuestions.length) {
    return { source: 'the stored question graph', rows: graphQuestions.map(fromGeo) };
  }
  return { source: '', rows: [] };
}

function fromGeo(item: any): QuestionRow {
  const text = String(item?.question || item?.generated_question || '');
  const facet = String(item?.category || item?.facet || '');
  return {
    qid: String(item?.question_key || item?.question_id || ''),
    text,
    status: questionStatus(item?.status || item?.answerability_status, item?.is_answerable),
    intent: intentBucket(`${text} ${facet}`),
    url: String(item?.evidence_url || ''),
    gap: clip(item?.why || item?.gap_analysis || ''),
    facet,
  };
}

function where(facts: Facts, status: string): QuestionRow[] {
  return facts.questions.filter((item) => item.status === status);
}

function quotes(rows: QuestionRow[], limit = 3): string {
  const shown = rows.slice(0, limit).map((item) => {
    let bit = `“${item.text || item.qid}” (${item.status}`;
    if (item.url) bit += `, ${item.url}`;
    if (item.gap) bit += `; ${clip(item.gap, 140)}`;
    return bit + ')';
  });
  if (shown.length === 0) return 'No question text was retained for this line.';
  const extra = rows.length - shown.length;
  return shown.join(' ') + (extra > 0 ? ` ${extra} more stay in the stored set.` : '');
}

function coverageSentence(facts: Facts): string {
  if (facts.assessed === 0) {
    return 'No question was assessed on this run. Question coverage has no denominator. A missing question set is not zero coverage.';
  }
  return (
    `Question coverage is ${facts.usable} of ${facts.assessed} assessed questions with a usable answer (status ANSWERABLE). ` +
    `Partial: ${facts.partial}. Unanswered: ${facts.unanswered}. Conflicting: ${facts.conflicting}. ` +
    `The denominator is ${facts.questionSource}. A completed evaluation is not, by itself, an answered question. ` +
    'This ratio is content readiness, not live visibility.'
  );
}

function liveSentence(facts: Facts): string {
  if (!facts.card) {
    return 'No live answer-engine scorecard was stored. Google AI Overviews, Google AI Mode, and Bing Copilot stay unqueried unless a run names them. An on-page writing exercise is not a live query.';
  }
  if (facts.runs <= 0) {
    return (
      'No successful live answer-engine run is stored, so mention rate, citation rate, recommendation rate, and citation share stay unmeasured. A missing rate is not zero. ' +
      `Surfaces left unqueried: ${join(facts.surfaces, 6)}. ChatGPT, Perplexity, Gemini, and Claude API answers are not those consumer surfaces.`
    );
  }
  return (
    `${facts.runs} successful live run(s). Measurement kind: ${facts.kind || 'unspecified'}. Engines queried: ${facts.engines.length ? join(facts.engines, 8) : 'the stored engine list is empty'}. ` +
    `Not queried: ${join(facts.surfaces, 6)}. An API answer can differ from the consumer product. These runs are not universal visibility across users, locations, or sessions.`
  );
}

function rate(facts: Facts, key: string, label: string, formula: string): Result {
  const value = facts.rates[key];
  if (!facts.card || facts.runs <= 0 || value == null) {
    const state: AeoStatus = facts.card && facts.runs > 0 ? 'DATA_UNAVAILABLE' : 'NOT_TESTED';
    return [state, `${label} was not measured. ${formula} ${liveSentence(facts)} A missing rate is not zero and not a pass.`];
  }
  return [
    'VERIFIED',
    `${label} is ${pct(value)}% on this run. ${formula} The denominator is the ${facts.runs} valid successful response(s). One response can mention several brands and cite several sources; those outcomes are not mutually exclusive. ${liveSentence(facts)}`,
  ];
}

function recommendation(facts: Facts): Result {
  const mention = facts.rates.mention;
  const mentionBit =
    mention != null
      ? `Mention rate on this run is ${pct(mention)}%, and a mention is not a recommendation.`
      : 'Mention rate was not measured either, and it would still not be a recommendation rate.';
  const state: AeoStatus = !facts.card || facts.runs <= 0 ? 'NOT_TESTED' : 'DATA_UNAVAILABLE';
  return [
    state,
    `Brand recommendation rate was not measured. The stored scorecard has mention and citation fields, not a recommendation flag. ${mentionBit} ${liveSentence(facts)}`,
  ];
}

function profileValue(facts: Facts, name: string): string {
  const value = facts.profile?.[name];
  if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) return '';
  if (Array.isArray(value)) return value.map(String).filter(Boolean).join(', ');
  return String(value).trim();
}

function profileLine(facts: Facts, label: string, names: string[]): Result {
  const filled = names.map((name) => [name, profileValue(facts, name)] as const).filter(([, value]) => value);
  if (filled.length === 0) {
    return ['DATA_UNAVAILABLE', `${label} is not in the stored business profile. An empty profile field is not a confirmed absence of the fact.`];
  }
  const status = String(facts.profile?.evidence_status || 'unspecified');
  return [
    'INFERRED',
    `The stored business profile records ${filled.map(([name, value]) => `${name}: ${value}`).join('; ')}. Profile evidence status: ${status}. This is the audit's business context, not a description returned by an answer engine.`,
  ];
}

function gapExamples(facts: Facts): string {
  const rows = [...where(facts, 'UNANSWERABLE'), ...where(facts, 'CONFLICTING'), ...where(facts, 'PARTIAL')];
  if (rows.length === 0) {
    return facts.assessed ? 'Every assessed question has a usable answer in the stored set.' : 'There is no assessed question to rank.';
  }
  return quotes(rows, 4);
}

function claimsSentence(facts: Facts): Result {
  const total = num(facts.claims?.total_claims_extracted) || 0;
  if (total <= 0) return ['NOT_TESTED', 'No claim inventory was extracted from the crawled pages.'];
  const fluff = num(facts.claims?.fluff_claims_count) || 0;
  const citable = num(facts.claims?.citable_claims_count) || 0;
  return [
    fluff ? 'ISSUE_SAMPLE' : 'CLEAN_SAMPLE',
    `The claim extract found ${total} claim(s), ${citable} marked citable and ${fluff} marked fluff. These are on-page claims. They are not answer-engine citations.`,
  ];
}

function passageSentence(facts: Facts): Result {
  const scanned = num(facts.passages?.total_passages_scanned) || 0;
  if (scanned <= 0) return ['NOT_TESTED', 'No passage extractability scan was stored.'];
  const ready = num(facts.passages?.citation_readiness_score);
  const scoreBit = ready != null ? ` The on-page citation-readiness figure is ${pct(ready)} / 100.` : '';
  return [
    'INFERRED',
    `${scanned} passage(s) were scanned.${scoreBit} That figure is extractability of the source. It is not a live citation rate.`,
  ];
}

function entitySentence(facts: Facts): Result {
  const surfaces = num(facts.entity?.surfaces_analyzed_count) || 0;
  if (surfaces <= 0) {
    return ['NOT_TESTED', 'Cross-page entity consistency was not measured. A brand name in the profile is not that test.'];
  }
  const discrepancies = listOf(facts.entity?.discrepancies);
  const score = num(facts.entity?.overall_consistency_score);
  return [
    discrepancies.length ? 'ISSUE_SAMPLE' : 'CLEAN_SAMPLE',
    `Entity consistency across ${surfaces} surface(s) is ${score != null ? `${pct(score)} / 100` : 'unspecified'}. ${discrepancies.length} discrepancy record(s). This is source consistency, not a live answer about the brand.`,
  ];
}

function schemaSentence(facts: Facts): string {
  if (facts.schemaTypes.length === 0) {
    if (facts.crawled === 0) return 'Structured data was not inspected because no page was crawled.';
    return 'No schema type was recorded on the crawled pages. Schema can clarify entities. It does not make an answer engine select or cite a page.';
  }
  const quality = num(facts.cross?.quality_score);
  const qualityBit = quality != null ? ` Schema cross-check quality is ${pct(quality)} of 100 stated properties.` : '';
  return `Schema types in the sample: ${join(facts.schemaTypes, 8)}.${qualityBit} Presence of a type, including FAQPage, does not guarantee a rich result or a citation.`;
}

function gscSentence(facts: Facts): Result {
  if (facts.gscState !== 'MEASURED') {
    return ['DATA_UNAVAILABLE', `Search Console state is ${facts.gscState}. Question queries, clicks, and impressions were not read. A disconnected connector is not zero clicks.`];
  }
  return ['VERIFIED', 'Search Console is MEASURED for this report. Clicks are not conversions, and query rows are not an answer-engine test.'];
}

function ga4Sentence(facts: Facts): Result {
  if (facts.ga4State !== 'MEASURED') {
    return ['DATA_UNAVAILABLE', `GA4 state is ${facts.ga4State}. Sessions, landing pages, and key events were not read. A missing key-event field is not zero conversions. Search Console clicks are not conversions.`];
  }
  if (facts.analytics?.key_events == null) {
    return ['DATA_UNAVAILABLE', 'GA4 is connected, and the key_events field is absent. Absent is not zero. Revenue was not attributed.'];
  }
  return ['VERIFIED', `GA4 key events are ${facts.analytics.key_events}. This is a key-event count, not revenue, and not an AI-referral conversion rate.`];
}

function bakeoffSentence(facts: Facts): string {
  if (!facts.bakeoff) return 'No competitor answer comparison with stored evaluations was attached.';
  return `On-page bake-off versus ${facts.bakeoff.competitor_domain || 'the named competitor'}: target wins ${facts.bakeoff.target_wins || 0}, competitor wins ${facts.bakeoff.competitor_wins || 0}, ties ${facts.bakeoff.ties || 0}, across ${facts.bakeItems.length} evaluation(s). This is a stored comparison of answers, not a live citation share.`;
}

function contradictionSentence(facts: Facts): string {
  if (facts.contradictions.length === 0) return 'No contradiction record was stored.';
  return `${facts.contradictions.length} contradiction record(s).`;
}

function robotsSentence(facts: Facts): Result {
  if (!facts.manifest || facts.crawled === 0) {
    return ['NOT_TESTED', 'robots.txt was not checked because no crawl manifest with pages was stored.'];
  }
  if (facts.manifest.robots_txt_found) return ['CLEAN_SAMPLE', 'robots.txt was found during the crawl. Bot-specific allow or deny still requires a measured robots parse.'];
  return ['ISSUE_SAMPLE', 'robots.txt was not found in the crawl. Answer engines that fetch this host have no robots file in the stored evidence.'];
}

function sitemapSentence(facts: Facts): Result {
  if (!facts.manifest || facts.crawled === 0) return ['NOT_TESTED', 'No crawl manifest was stored, so sitemap coverage was not checked.'];
  if (facts.manifest.sitemap_found) return ['CLEAN_SAMPLE', `An XML sitemap was recorded at ${facts.manifest.sitemap_url || 'the recorded sitemap'}.`];
  return ['ISSUE_SAMPLE', 'No XML sitemap was recorded for this crawl.'];
}

function indexableSentence(facts: Facts): string {
  if (facts.pages.length === 0) return 'No crawled page is available, so indexability was not judged.';
  const blocked = facts.pages.filter((page) => page?.is_indexable === false || String(page?.robots_meta || '').toLowerCase().includes('noindex'));
  if (blocked.length) return `${blocked.length} crawled page(s) are marked non-indexable.`;
  return `All ${facts.crawled} crawled page(s) are marked indexable in the crawl record. This is the sample, not the whole site.`;
}

function ttfbSentence(facts: Facts): string {
  const times = facts.pages.map((page) => num(page?.ttfb_ms)).filter((value): value is number => value != null && value > 0);
  if (times.length === 0) return 'Crawl response time was not recorded. Response time is not a Core Web Vital.';
  return `Crawl response time on the sample: ${times.slice(0, 5).map((value) => `${value} ms`).join(', ')}. This is server response timing, not Largest Contentful Paint, and not a field Core Web Vital.`;
}

function unt(label: string, because: string): Result {
  return ['NOT_TESTED', `${label} was not tested. ${because}`];
}

function gap(label: string, because: string): Result {
  return ['DATA_UNAVAILABLE', `${label} is data unavailable. ${because}`];
}

function needQuestions(facts: Facts, label: string): Result | null {
  if (facts.assessed) return null;
  return unt(label, `${coverageSentence(facts)} ${SEPARATION}`);
}

function fixFor(item: QuestionRow): string {
  if (item.gap) return `Add a fact-checked answer for “${clip(item.text, 80)}”. Stored gap: ${clip(item.gap, 160)}.`;
  return `Add a fact-checked answer, with conditions and a source, for “${clip(item.text, 80)}”.`;
}

function issue(scope: string, why: string, fix: string): string {
  return `Scope: ${scope}. Why it matters: ${why} Recommended fix: ${fix}${LIMIT}`;
}

function explicitAnswer(facts: Facts): Result {
  const blocked = needQuestions(facts, 'Direct answer');
  if (blocked) return blocked;
  const weak = [...where(facts, 'UNANSWERABLE'), ...where(facts, 'PARTIAL'), ...where(facts, 'CONFLICTING')];
  if (weak.length) {
    return ['ISSUE_SAMPLE', `${coverageSentence(facts)} ${quotes(weak, 3)}${issue('the named questions and their evidence URLs', 'A reader or an answer engine has to infer the answer.', fixFor(weak[0]))}`];
  }
  return ['CLEAN_SAMPLE', coverageSentence(facts)];
}

function platformAbsent(facts: Facts, label: string, surface: string): Result {
  return unt(label, `${surface} was not queried on this run. ${liveSentence(facts)} The on-page matrix does not stand in for this surface. ${facts.simulation ? `Matrix mode: ${facts.simulation}. ` : ''}`);
}

function line(facts: Facts, number: string, label: string): Result {
  const handler = HANDLERS[number];
  if (handler) return handler(facts, label);
  return appendix(facts, number, label);
}

const HANDLERS: Record<string, (facts: Facts, label: string) => Result> = {
  '01': (facts, label) => {
    if (has(label, 'overall')) {
      const code: AeoStatus = facts.assessed && facts.usable < facts.assessed ? 'ISSUE_SAMPLE' : facts.assessed === 0 ? 'NOT_TESTED' : 'CLEAN_SAMPLE';
      return [code, `${coverageSentence(facts)} ${liveSentence(facts)} ${facts.sample} ${SEPARATION}`];
    }
    if (has(label, 'brand presence')) return rate(facts, 'mention', 'Brand mention rate', 'Mentions divided by valid responses.');
    if (has(label, 'tested versus') || has(label, 'questions tested')) {
      return [facts.assessed ? 'VERIFIED' : 'NOT_TESTED', `${coverageSentence(facts)} Questions outside this stored set were not tested.`];
    }
    if (has(label, 'recommend')) return recommendation(facts);
    if (has(label, "cite the brand")) return rate(facts, 'citation', 'Citation rate', 'Responses with at least one qualifying citation to the brand domain, divided by valid responses.');
    if (has(label, 'competitors instead') || has(label, 'cite competitors')) return rate(facts, 'competitor', 'Competitor visibility', 'This is the stored competitor-visibility field, not citation share.');
    if (has(label, 'missing and inaccurate') || has(label, 'inaccurate')) {
      if (facts.conflicting || facts.contradictions.length) return ['ISSUE_SAMPLE', `${facts.conflicting} assessed question(s) are conflicting. ${contradictionSentence(facts)} ${gapExamples(facts)}`];
      if (facts.unanswered || facts.partial) return ['ISSUE_SAMPLE', `Missing answers in the assessed set. ${gapExamples(facts)}`];
      if (facts.assessed) return ['CLEAN_SAMPLE', coverageSentence(facts)];
      return unt(label, coverageSentence(facts));
    }
    if (has(label, 'highest-priority') || has(label, 'coverage gap')) {
      if (facts.assessed && (facts.unanswered || facts.partial || facts.conflicting)) return ['ISSUE_SAMPLE', `Priority gaps are the unanswered, partial, and conflicting questions. ${gapExamples(facts)}`];
      if (facts.assessed) return ['CLEAN_SAMPLE', `No coverage gap is stored inside the assessed set. ${coverageSentence(facts)}`];
      return unt(label, coverageSentence(facts));
    }
    if (has(label, 'commercial')) {
      const profile = profileLine(facts, 'Commercial context', ['business_model', 'value_proposition', 'primary_cta']);
      return [facts.assessed === 0 ? profile[0] : 'INFERRED', `${profile[1]} ${coverageSentence(facts)} No revenue figure is inferred from these gaps.`];
    }
    if (has(label, '30/60/90') || has(label, 'action plan')) return unt(label, `No 30/60/90 calendar is invented. The work queue is the stored gap list: ${gapExamples(facts)}`);
    return ['INFERRED', `${coverageSentence(facts)} ${liveSentence(facts)}`];
  },
  '02': (facts, label) => {
    if (has(label, 'question coverage')) {
      if (facts.assessed === 0) return unt(label, coverageSentence(facts));
      return [facts.usable === facts.assessed ? 'CLEAN_SAMPLE' : 'ISSUE_SAMPLE', `Formula: relevant questions with a usable, verified answer ÷ relevant questions assessed. ${coverageSentence(facts)}`];
    }
    if (has(label, 'completeness')) {
      if (facts.assessed === 0) return unt(label, 'Answer completeness needs assessed questions and required elements. Neither weighted element list was stored.');
      return ['INFERRED', `A weighted required-element score was not stored. What is stored: ${facts.usable} of ${facts.assessed} are complete enough to be ANSWERABLE, ${facts.partial} are partial, and a partial answer does not satisfy the completeness formula. ${gapExamples(facts)}`];
    }
    if (has(label, 'clarity') || has(label, 'extractability')) {
      const passage = passageSentence(facts);
      if (facts.extractability != null) return ['INFERRED', `On-page extractability is ${pct(facts.extractability)} / 100. ${passage[1]} ${SEPARATION}`];
      return [passage[0], `${passage[1]} ${SEPARATION}`];
    }
    if (has(label, 'factual accuracy')) {
      if (facts.rates.entity_accuracy != null) return rate(facts, 'entity_accuracy', 'Live entity accuracy', 'Verified correct brand claims in live responses ÷ brand claims assessed in those responses.');
      return claimsSentence(facts);
    }
    if (has(label, 'source attribution') || has(label, 'citation quality')) {
      if (facts.rates.citation_accuracy != null) return rate(facts, 'citation_accuracy', 'Citation accuracy', 'Verified relevant and correctly attributed citations ÷ citations assessed.');
      return ['NOT_TESTED', 'Citation accuracy stays blank until a span check on a live citation is stored. Passage extractability does not fill this score.'];
    }
    if (has(label, 'entity consistency')) return entitySentence(facts);
    if (has(label, 'accessibility') || has(label, 'answer-source')) {
      const robots = robotsSentence(facts);
      return [facts.crawled ? robots[0] : 'NOT_TESTED', `${facts.sample} ${indexableSentence(facts)} ${robots[1]}`];
    }
    if (has(label, 'structured data')) {
      if (facts.crawled === 0 && facts.schemaTypes.length === 0) return unt(label, schemaSentence(facts));
      return [facts.schemaTypes.length ? 'CLEAN_SAMPLE' : 'ISSUE_SAMPLE', schemaSentence(facts)];
    }
    if (has(label, 'search answer appearance')) return unt(label, `Featured snippets, People Also Ask, and other search-answer boxes were not collected. ${liveSentence(facts)}`);
    if (has(label, 'live answer visibility')) return rate(facts, 'mention', 'Live mention rate', 'Valid tested responses mentioning the brand ÷ valid responses. This is not a recommendation rate.');
    if (has(label, 'citation coverage')) return rate(facts, 'citation', 'Citation rate', 'Valid responses containing at least one qualifying citation to the brand domain ÷ valid responses.');
    if (has(label, 'competitive answer share')) {
      if (facts.rates.citation == null && facts.rates.competitor == null) {
        return ['NOT_TESTED', `Citation share was not calculated. It needs qualifying citations to the brand and to all tracked domains. ${bakeoffSentence(facts)} ${liveSentence(facts)}`];
      }
      return ['DATA_UNAVAILABLE', `Competitor visibility may be stored, and citation share still needs a denominator of qualifying citations to all tracked domains. Those inputs were not both stored. ${liveSentence(facts)}`];
    }
    return ['INFERRED', `${facts.sample} ${coverageSentence(facts)} ${liveSentence(facts)} Search Console: ${facts.gscState}. GA4: ${facts.ga4State}. ${SEPARATION}`];
  },
  '03': (facts, label) => {
    const mapping: Array<[string[], string[]]> = [
      [['business model', 'core offering'], ['business_model', 'industry', 'niche']],
      [['products'], ['products', 'services']],
      [['persona', 'audience'], ['target_audience']],
      [['countries', 'languages', 'regions'], ['geography']],
      [['positioning', 'differentiation'], ['value_proposition']],
      [['pricing', 'availability', 'eligibility'], ['primary_cta']],
      [['brand facts', 'approved claims'], ['business_name', 'value_proposition']],
    ];
    for (const [keys, names] of mapping) {
      if (has(label, ...keys)) return profileLine(facts, label, names);
    }
    if (has(label, 'high-value customer') || has(label, 'buyer journey') || has(label, 'support and troubleshooting')) {
      return needQuestions(facts, label) || ['INFERRED', `${facts.assessed} questions were generated for this business from ${facts.questionSource}. ${coverageSentence(facts)}`];
    }
    if (has(label, 'high-risk')) {
      return [facts.contradictions.length || facts.conflicting ? 'ISSUE_SAMPLE' : 'NOT_TESTED', `${contradictionSentence(facts)} ${claimsSentence(facts)[1]} No extra high-risk claim was inferred.`];
    }
    if (has(label, 'platform') || has(label, 'surface')) {
      return ['INFERRED', `${liveSentence(facts)} The on-page engine matrix mode is ${facts.simulation || 'not attached'}. SIMULATION_ONLY is a writing exercise, not a query of ChatGPT, Perplexity, Gemini, Copilot, or Google AI Overviews.`];
    }
    return profileLine(facts, label, ['business_name', 'industry']);
  },
  '04': (facts, label) => {
    if (has(label, 'no useful answer')) {
      const rows = where(facts, 'UNANSWERABLE');
      if (rows.length) return ['ISSUE_SAMPLE', `${rows.length} assessed question(s) have no usable answer. ${quotes(rows, 3)} ${issue('those questions', 'The source cannot satisfy them.', fixFor(rows[0]))}`];
      if (facts.assessed) return ['CLEAN_SAMPLE', `No assessed question is unanswered. ${coverageSentence(facts)}`];
      return unt(label, coverageSentence(facts));
    }
    if (has(label, 'incorrect') || has(label, 'outdated')) {
      if (facts.conflicting || facts.contradictions.length) return ['ISSUE_SAMPLE', `${contradictionSentence(facts)} ${quotes(where(facts, 'CONFLICTING'), 2)}`];
      return unt(label, 'No conflicting answer and no contradiction record were stored. Age of a statistic was not dated.');
    }
    if (has(label, 'recommendation')) return recommendation(facts);
    if (has(label, 'competitors repeatedly')) {
      const text = `${bakeoffSentence(facts)} ${liveSentence(facts)}`;
      return !facts.bakeoff && facts.rates.competitor == null ? unt(label, text) : ['INFERRED', text];
    }
    if (has(label, 'unsupported')) return claimsSentence(facts);
    if (has(label, 'contradict')) {
      if (facts.contradictions.length || facts.conflicting) return ['ISSUE_SAMPLE', contradictionSentence(facts)];
      return ['NOT_TESTED', `${contradictionSentence(facts)} An empty contradiction list is not a completed consistency audit.`];
    }
    if (has(label, 'specification') || has(label, 'evidence for factual')) return claimsSentence(facts);
    if (has(label, 'unavailable') || has(label, 'inaccessible')) return facts.crawled ? robotsSentence(facts) : unt(label, facts.sample);
    if (has(label, 'pricing') || has(label, 'policy')) {
      const priced = facts.questions.filter((item) => item.intent === 'pricing');
      if (priced.length === 0) return unt(label, 'No pricing question was in the assessed set, and no price date was checked. Stale pricing is not assumed.');
      const bad = priced.filter((item) => item.status !== 'ANSWERABLE');
      if (bad.length) return ['ISSUE_SAMPLE', `${bad.length} of ${priced.length} pricing question(s) lack a usable answer. ${quotes(bad, 2)}`];
      return ['CLEAN_SAMPLE', `All ${priced.length} assessed pricing question(s) have a usable answer. Currency freshness was not separately dated.`];
    }
    if (has(label, 'misleading') || has(label, 'generated')) return rate(facts, 'hallucination', 'Hallucination rate', 'This rate counts inaccurate generated answers in the live runs. It is blank when those runs do not exist.');
    if (has(label, 'sensitive') || has(label, 'regulated')) return unt(label, 'No regulated-claim review was run. Industry text in the profile is not that review.');
    return unt(label, coverageSentence(facts));
  },
  '05': (facts, label) => {
    if (!facts.bakeoff && facts.rates.competitor == null) return unt(label, `${bakeoffSentence(facts)} ${liveSentence(facts)} Competitor names are not invented.`);
    return ['INFERRED', `${bakeoffSentence(facts)} ${gapExamples(facts)} ${liveSentence(facts)}`];
  },
  '06': (facts, label) => {
    if (has(label, 'time to impact') || has(label, 'effort') || has(label, 'confidence in the recommendation')) return unt(label, `Effort, confidence intervals, and time to impact are not estimated. ${gapExamples(facts)}`);
    if (has(label, 'search demand')) return gscSentence(facts);
    if (facts.assessed === 0) return unt(label, coverageSentence(facts));
    return ['INFERRED', `Priority follows unanswered, then conflicting, then partial questions. Search demand is separate. ${gscSentence(facts)[1]} ${gapExamples(facts)} No traffic or revenue forecast is attached.`];
  },
  '07': (facts, label) => {
    if (has(label, 'search console')) return gscSentence(facts);
    if (has(label, 'collection date') || has(label, 'source and collection')) return ['INFERRED', `Question source: ${facts.questionSource || 'no question source'}. Report timestamp: ${facts.generatedAt}. Autocomplete, People Also Ask, and forums were not given their own collection dates.`];
    if (has(label, 'live answer')) return [facts.runs > 0 ? 'VERIFIED' : 'NOT_TESTED', `${liveSentence(facts)} The assessed question inventory is ${facts.questionSource || 'not stored'}.`];
    if (has(label, 'competitor question')) return facts.bakeItems.length ? ['INFERRED', bakeoffSentence(facts)] : unt(label, bakeoffSentence(facts));
    const blocked = needQuestions(facts, label);
    if (has(label, 'sandbox') || has(label, 'relevant search') || has(label, 'discovered from')) return blocked || ['INFERRED', coverageSentence(facts)];
    return unt(label, `This source was not collected. The assessed set, when present, is ${facts.questionSource || 'absent'}. That set is not People Also Ask, autocomplete, a support desk, or a forum export. ${coverageSentence(facts)}`);
  },
  '08': (facts, label) => {
    const blocked = needQuestions(facts, label);
    if (blocked) return blocked;
    if (has(label, 'follow-up') || has(label, 'clarification')) return unt(label, `Follow-up turns were not stored. The assessed set is single questions. ${coverageSentence(facts)}`);
    let bucket = 'unclassified';
    if (has(label, 'definition')) bucket = 'definition';
    else if (has(label, 'explanatory')) bucket = 'explanatory';
    else if (has(label, 'how-to') || has(label, 'how to')) bucket = 'how-to';
    else if (has(label, 'troubleshoot')) bucket = 'troubleshooting';
    else if (has(label, 'comparison')) bucket = 'comparison';
    else if (has(label, 'best')) bucket = 'best';
    else if (has(label, 'recommendation')) bucket = 'recommendation';
    else if (has(label, 'pricing')) bucket = 'pricing';
    else if (has(label, 'eligibility') || has(label, 'qualification')) bucket = 'eligibility';
    else if (has(label, 'location') || has(label, 'availability')) bucket = 'location';
    else if (has(label, 'transactional')) bucket = 'transactional';
    else if (has(label, 'navigational')) bucket = 'navigational';
    else if (has(label, 'opinion') || has(label, 'evaluation')) bucket = 'opinion';
    const rows = facts.questions.filter((item) => item.intent === bucket);
    return ['INFERRED', `${rows.length} of ${facts.assessed} assessed questions match “${bucket}” by wording. This is a classification of the stored set, not proof of customer demand. ${quotes(rows, 2)}`];
  },
  '09': (facts, label) => {
    if ((has(label, 'geographic') || has(label, 'language cluster')) && facts.assessed === 0 && facts.pages.length === 0) {
      return unt(label, coverageSentence(facts));
    }
    const blocked = needQuestions(facts, label);
    if (blocked && !has(label, 'geographic') && !has(label, 'language')) return blocked;
    const groups = new Map<string, QuestionRow[]>();
    for (const item of facts.questions) {
      const key = item.facet || item.intent || 'ungrouped';
      groups.set(key, [...(groups.get(key) || []), item]);
    }
    if (has(label, 'unanswered')) {
      const empty = [...groups.entries()].filter(([, rows]) => rows.length > 0 && rows.every((row) => row.status !== 'ANSWERABLE')).map(([name]) => name);
      if (!facts.assessed) return unt(label, coverageSentence(facts));
      if (empty.length) return ['ISSUE_SAMPLE', `Facets with no usable answer: ${join(empty, 8)}`];
      return ['CLEAN_SAMPLE', 'Every stored facet has at least one usable answer.'];
    }
    const names = [...groups.entries()].slice(0, 8).map(([name, rows]) => `${name} (${rows.length})`);
    return ['INFERRED', `${groups.size} group(s) by stored facet or intent, not by an embedding model. ${join(names, 8)} Duplicate wording was counted inside those groups.`];
  },
  '10': (facts, label) => {
    const blocked = needQuestions(facts, label);
    if (blocked) return blocked;
    const withUrl = facts.questions.filter((item) => item.url);
    const without = facts.questions.filter((item) => !item.url);
    if (has(label, 'no appropriate') || has(label, 'gap')) {
      if (without.length) return ['ISSUE_SAMPLE', `${without.length} of ${facts.assessed} assessed questions have no evidence URL. ${quotes(without, 3)}`];
      return ['CLEAN_SAMPLE', `All ${facts.assessed} assessed questions have an evidence URL.`];
    }
    if (without.length && has(label, 'existing page', 'destination', 'mapping')) {
      return ['ISSUE_SAMPLE', `${withUrl.length} questions map to a URL and ${without.length} do not. ${quotes(without, 2)}`];
    }
    return ['INFERRED', `${withUrl.length} of ${facts.assessed} questions have an evidence or target URL. ${quotes(withUrl.length ? withUrl : facts.questions, 3)}`];
  },
  '11': (facts, label) => {
    if (has(label, 'explicitly') || has(label, 'without requiring') || has(label, 'correct and complete') || has(label, 'actual user intent')) return explicitAnswer(facts);
    if (has(label, 'consistent')) {
      if (facts.contradictions.length || facts.conflicting) return ['ISSUE_SAMPLE', contradictionSentence(facts)];
      return ['NOT_TESTED', `No contradiction record is stored. That is not a completed consistency audit. ${contradictionSentence(facts)}`];
    }
    if (has(label, 'conditions') || has(label, 'limitations') || has(label, 'terms')) return ['INFERRED', `Conditions and limitations are only what the stored gaps say. ${gapExamples(facts)}`];
    if (has(label, 'facts from opinions')) return claimsSentence(facts);
    const blocked = needQuestions(facts, label);
    if (blocked) return blocked;
    return ['INFERRED', `${coverageSentence(facts)} Directness of the opening sentence was not separately scored.`];
  },
  '12': (facts, label) => {
    if (has(label, 'core answer')) return explicitAnswer(facts);
    if (has(label, 'evidence') || has(label, 'references')) return claimsSentence(facts);
    if (has(label, 'missing information')) {
      if (facts.partial || facts.unanswered) return ['ISSUE_SAMPLE', gapExamples(facts)];
      if (facts.assessed) return ['CLEAN_SAMPLE', `No partial or unanswered question is stored. ${coverageSentence(facts)}`];
      return unt(label, coverageSentence(facts));
    }
    const blocked = needQuestions(facts, label);
    if (blocked && facts.crawled === 0) return blocked;
    return ['INFERRED', `${label} was not scored as its own weighted element. The stored substitute is answer status. ${coverageSentence(facts)} A keyword missed in a representative sample is not a sitewide absence.`];
  },
  '13': (facts, label) => {
    if (has(label, 'initial')) return HANDLERS['02'](facts, 'Question coverage score');
    if (has(label, 'follow-up') || has(label, 'clarification') || has(label, 'multi-step') || has(label, 'multi-turn') || has(label, 'context-dependent')) {
      return unt(label, 'Multi-turn conversations were not run. Single stored questions do not prove a journey.');
    }
    if (has(label, 'purchase') || has(label, 'conversion') || has(label, 'next step') || has(label, 'decision')) {
      if (facts.assessed === 0) return unt(label, coverageSentence(facts));
      return ['INFERRED', `${coverageSentence(facts)} ${ga4Sentence(facts)[1]}`];
    }
    return unt(label, `This journey step was not executed as a conversation. ${coverageSentence(facts)}`);
  },
  '14': (facts, label) => {
    const faq = facts.schemaTypes.some((name) => name.toLowerCase() === 'faqpage');
    if (has(label, 'schema') || has(label, 'rich result') || has(label, 'eligibility')) {
      if (faq) return ['INFERRED', `FAQPage is present in the sample. That does not establish rich-result eligibility, and it does not mean an answer engine will cite the page. ${schemaSentence(facts)}`];
      if (facts.crawled === 0) return unt(label, schemaSentence(facts));
      return ['INFERRED', `FAQPage was not recorded. ${schemaSentence(facts)}`];
    }
    if (has(label, 'redundant') || has(label, 'duplication')) {
      if (facts.assessed === 0) return unt(label, coverageSentence(facts));
      const texts = facts.questions.map((item) => item.text.trim().toLowerCase()).filter(Boolean);
      const dupes = texts.length - new Set(texts).size;
      if (dupes) return ['ISSUE_SAMPLE', `${dupes} duplicate question text(s) inside the assessed set.`];
      return ['CLEAN_SAMPLE', 'No duplicate question text inside the assessed set. Duplication across unfetched pages was not checked.'];
    }
    if (has(label, 'accuracy') || has(label, 'genuine') || has(label, 'wording')) return explicitAnswer(facts);
    return [facts.assessed || facts.crawled ? 'INFERRED' : 'NOT_TESTED', `${schemaSentence(facts)} ${coverageSentence(facts)}`];
  },
  '15': (facts, label) => {
    if (has(label, 'search demand')) return gscSentence(facts);
    if (has(label, 'competitor')) return HANDLERS['05'](facts, label);
    if (has(label, 'inaccurate') || has(label, 'high-risk')) return HANDLERS['04'](facts, 'Incorrect or outdated answers');
    if (has(label, 'weak')) {
      const rows = where(facts, 'PARTIAL');
      if (rows.length) return ['ISSUE_SAMPLE', `${rows.length} partial answer(s). ${quotes(rows, 3)}`];
      if (facts.assessed) return ['CLEAN_SAMPLE', `No partial answer is stored. ${coverageSentence(facts)}`];
      return unt(label, coverageSentence(facts));
    }
    if (has(label, 'unanswered') || has(label, 'high-value') || has(label, 'brand relevance') || has(label, 'recommended question')) {
      if (facts.unanswered || facts.partial || facts.conflicting) return ['ISSUE_SAMPLE', `Coverage gaps, with business value left unmeasured: ${gapExamples(facts)}`];
      if (facts.assessed) return ['CLEAN_SAMPLE', coverageSentence(facts)];
      return unt(label, coverageSentence(facts));
    }
    if (has(label, 'conversion')) return HANDLERS['13'](facts, 'Purchase or conversion next steps');
    if (has(label, 'low-value') || has(label, 'redundant')) return HANDLERS['14'](facts, 'Redundant FAQ detection');
    return unt(label, coverageSentence(facts));
  },
  '16': (facts, label) => contentOrUntested(facts, label, 'Heading structure and opening answers use the crawled sample and the assessed questions. A heading that is not a question can still introduce an answer.'),
  '17': (facts, label) => {
    if (has(label, 'pronoun') || has(label, 'abbreviation') || has(label, 'units') || has(label, 'fragment')) {
      return unt(label, `That linguistic check was not run. ${passageSentence(facts)[1]}`);
    }
    const passage = passageSentence(facts);
    return [passage[0], `${passage[1]} ${coverageSentence(facts)}`];
  },
  '18': (facts, label) => {
    if (has(label, 'contradict')) {
      if (facts.contradictions.length || facts.conflicting) return ['ISSUE_SAMPLE', contradictionSentence(facts)];
      if (facts.assessed === 0) return ['NOT_TESTED', `${contradictionSentence(facts)} An empty list is not a completed cross-page fact check.`];
      return ['INFERRED', `No assessed question is marked CONFLICTING. ${contradictionSentence(facts)}`];
    }
    if (has(label, 'outdated') || has(label, 'dates') || has(label, 'figures')) return unt(label, 'Statistic dates were not checked. A missing date check is not a finding that the figure is wrong.');
    return claimsSentence(facts);
  },
  '19': (facts, label) => {
    if (has(label, 'author') || has(label, 'expertise')) {
      const people = facts.schemaTypes.filter((name) => ['person', 'author'].includes(name.toLowerCase()));
      if (people.length) return ['INFERRED', `Person or author schema is in the sample: ${join(people, 4)}. Schema is not proof of first-hand expertise.`];
      return unt(label, `No Person or author identity was recorded. ${schemaSentence(facts)}`);
    }
    if (facts.infoGain != null && has(label, 'original', 'testing', 'case', 'first-hand')) {
      return ['INFERRED', `The on-page information-gain figure is ${pct(facts.infoGain)} / 100. It is not a live citation result and not a research certificate.`];
    }
    if (has(label, 'original', 'testing', 'case', 'screenshot', 'first-hand')) return unt(label, 'First-hand evidence, original research, and screenshots were not inventoried.');
    return claimsSentence(facts);
  },
  '20': () => ['NOT_TESTED', 'Publication dates, offer expiry, and policy change dates were not compared with a current source. Freshness is not assumed from the crawl time.'],
  '21': (facts, label) => {
    if (facts.infoGain == null) return unt(label, 'Information gain was not measured. Repetition versus competitors is not assumed, and no uniqueness score is invented.');
    return ['INFERRED', `On-page information gain is ${pct(facts.infoGain)} / 100. That figure is a writing-exercise signal. It is not proof of proprietary research and not a citation rate.`];
  },
  '22': (facts, label) => {
    if (has(label, 'brand name') || has(label, 'organization') || has(label, 'alias')) {
      const entity = entitySentence(facts);
      const profile = profileLine(facts, label, ['business_name']);
      return [entity[0] === 'NOT_TESTED' ? profile[0] : entity[0], `${entity[1]} ${profile[1]}`];
    }
    if (has(label, 'product') || has(label, 'service') || has(label, 'terminology') || has(label, 'category')) return profileLine(facts, label, ['products', 'services', 'industry']);
    if (has(label, 'founder') || has(label, 'author')) return HANDLERS['19'](facts, 'Author identity');
    if (has(label, 'acronym')) return unt(label, 'Acronym expansion was not scanned.');
    return entitySentence(facts);
  },
  '23': (facts, label) => {
    const rows = facts.questions.filter((item) => ['comparison', 'best', 'recommendation'].includes(item.intent));
    if (has(label, 'disclosure') || has(label, 'conflict of interest')) return unt(label, 'Conflicts of interest and paid-placement disclosures were not reviewed.');
    if (rows.length === 0) return unt(label, `No comparison, best-of, or recommendation question is in the assessed set. ${bakeoffSentence(facts)}`);
    const bad = rows.filter((item) => item.status !== 'ANSWERABLE');
    if (bad.length) return ['ISSUE_SAMPLE', `${bad.length} of ${rows.length} comparison-style questions lack a usable answer. ${quotes(bad, 2)} ${bakeoffSentence(facts)}`];
    return ['CLEAN_SAMPLE', `All ${rows.length} comparison-style questions in the assessed set have a usable answer. ${quotes(rows, 2)}`];
  },
  '24': (facts, label) => {
    if (has(label, 'correction history') || has(label, 'version')) return ['INFERRED', `This document is the audit dated ${facts.generatedAt}. A content version-control history for the site was not read.`];
    return unt(label, 'Editorial workflow, fact-check ownership, and AI-assisted review policy were not collected from the site. This audit does not invent an editorial board.');
  },
  '25': (facts, label) => {
    if (has(label, 'crawler-specific')) {
      if (facts.robotsMeasured && facts.bots) {
        return ['VERIFIED', `Robots was parsed for AI crawlers. GPTBot allowed: ${facts.bots.gptbot_allowed}. PerplexityBot allowed: ${facts.bots.perplexitybot_allowed}. ClaudeBot allowed: ${facts.bots.claudebot_allowed}. Google-Extended allowed: ${facts.bots.google_extended_allowed}. An unmeasured robots file is not treated as allowed.`];
      }
      return gap(label, `AI crawler allow or deny was not measured. A missing parse is not allowed. ${robotsSentence(facts)[1]}`);
    }
    if (has(label, 'robots')) return robotsSentence(facts);
    if (has(label, 'http') || has(label, 'status') || has(label, 'important page')) {
      if (facts.pages.length === 0) return unt(label, facts.sample);
      const bad = facts.pages.filter((page) => (num(page?.status_code) || 0) >= 400);
      return [bad.length ? 'ISSUE_SAMPLE' : 'CLEAN_SAMPLE', `${facts.crawled} fetched page(s). Non-success pages in the sample: ${bad.length}.`];
    }
    if (has(label, 'authentication') || has(label, 'rate limit') || has(label, 'firewall') || has(label, 'region') || has(label, 'browser and crawler')) {
      return unt(label, `That access comparison was not run. ${facts.sample}`);
    }
    if (facts.crawled === 0) return unt(label, facts.sample);
    return ['INFERRED', `${facts.sample} ${indexableSentence(facts)}`];
  },
  '26': (facts, label) => {
    if (has(label, 'search console')) return gscSentence(facts);
    if (has(label, 'versus actual answer')) return ['NOT_TESTED', `${indexableSentence(facts)} ${liveSentence(facts)} Indexable HTML was not compared with a live answer appearance.`];
    if (facts.crawled === 0) return unt(label, facts.sample);
    if (has(label, 'canonical')) {
      const missing = facts.pages.filter((page) => !String(page?.canonical_url || '').trim());
      if (missing.length) return ['ISSUE_SAMPLE', `${missing.length} crawled page(s) have no canonical URL.`];
      return ['CLEAN_SAMPLE', 'Every crawled page has a canonical URL in the crawl record.'];
    }
    if (has(label, 'noindex') || has(label, 'robots meta') || has(label, 'indexable') || has(label, 'missing from the index')) {
      const blocked = facts.pages.filter((page) => page?.is_indexable === false || String(page?.robots_meta || '').toLowerCase().includes('noindex'));
      return [blocked.length ? 'ISSUE_SAMPLE' : 'CLEAN_SAMPLE', indexableSentence(facts)];
    }
    return ['INFERRED', `${indexableSentence(facts)} Search Console index coverage is separate. ${gscSentence(facts)[1]}`];
  },
  '27': (facts, label) => {
    if (facts.pages.length === 0) return unt(label, facts.sample);
    if (has(label, 'hydration') || has(label, 'lazy') || has(label, 'accordion') || has(label, 'hidden') || has(label, 'mobile')) {
      return unt(label, 'That render failure mode was not tested.');
    }
    if (has(label, 'structured data')) return ['INFERRED', schemaSentence(facts)];
    const modes = facts.pages.slice(0, 5).map((page) => `${page?.url || 'page'} ${page?.render_mode || 'unspecified'}`);
    return ['INFERRED', `Stored render modes: ${join(modes, 4)}. A static render mode is the crawl's record, not a second browser session.`];
  },
  '28': (facts, label) => {
    if (facts.pages.length === 0 && !facts.manifest) return unt(label, facts.sample);
    if (has(label, 'orphan')) {
      const orphans = listOf(facts.manifest?.orphan_urls).map(String);
      if (!facts.manifest) return unt(label, 'No crawl manifest, so orphan URLs were not listed.');
      if (orphans.length) return ['ISSUE_SAMPLE', `${orphans.length} orphan URL(s) recorded. ${join(orphans, 4)}`];
      return ['CLEAN_SAMPLE', 'The crawl manifest records no orphan URL. The sample can still miss links outside the fetched pages.'];
    }
    if (has(label, 'broken') || has(label, 'redirect')) return unt(label, 'A full broken-link crawl was not attached. HTTP status of fetched pages is in the technical appendix.');
    const total = facts.pages.reduce((sum, page) => sum + listOf(page?.internal_links).length, 0);
    return ['INFERRED', `Internal links recorded on crawled pages: ${total}. ${facts.sample}`];
  },
  '29': (facts, label) => {
    const wanted = ['Organization', 'Person', 'Article', 'BlogPosting', 'BreadcrumbList', 'Product', 'Offer', 'LocalBusiness', 'VideoObject', 'FAQ'].find((name) => label.toLowerCase().includes(name.toLowerCase()));
    if (wanted) {
      const present = facts.schemaTypes.filter((name) => name.toLowerCase().includes(wanted.toLowerCase()));
      if (present.length) return ['INFERRED', `${wanted} appears in the sample as ${join(present, 4)}. ${schemaSentence(facts)}`];
      if (facts.crawled === 0 && facts.schemaTypes.length === 0) return unt(label, schemaSentence(facts));
      return ['INFERRED', `${wanted} was not recorded in the sample. That absence is the sample, not a rich-result failure. ${schemaSentence(facts)}`];
    }
    if (has(label, 'eligibility') || has(label, 'limitation') || has(label, 'does not guarantee')) return ['INFERRED', schemaSentence(facts)];
    if (facts.schemaTypes.length) return ['INFERRED', schemaSentence(facts)];
    if (facts.crawled) return ['ISSUE_SAMPLE', schemaSentence(facts)];
    return unt(label, schemaSentence(facts));
  },
  '30': (facts, label) => contentOrUntested(facts, label, 'Titles and headings were read from the crawled sample. Table headers, landmarks, and accessible names were not extracted as their own test.'),
  '31': (facts, label) => {
    if (has(label, 'core web') || has(label, 'largest contentful') || has(label, 'layout stability')) {
      const field = facts.pages.some((page) => page?.field_performance?.has_field_data);
      const lab = facts.pages.some((page) => page?.lab_performance?.lighthouse_audit_version && num(page?.lab_performance?.lcp_ms) != null);
      if (field) return ['VERIFIED', `Field Core Web Vitals were stored. ${ttfbSentence(facts)}`];
      if (lab) return ['VERIFIED', `Lab Largest Contentful Paint was stored with a Lighthouse version. Lab data is not field CrUX data. ${ttfbSentence(facts)}`];
      return unt(label, `Field Core Web Vitals were not measured, and no Lighthouse version with LCP was stored. ${ttfbSentence(facts)}`);
    }
    if (has(label, 'latency') || has(label, 'resource') || has(label, 'performance of documentation')) {
      return facts.pages.length ? ['INFERRED', ttfbSentence(facts)] : unt(label, ttfbSentence(facts));
    }
    if (has(label, 'accessibility') || has(label, 'readability')) {
      if (facts.crawled === 0) return unt(label, 'No page was crawled. Automated screening is not a WCAG certificate.');
      const missingAlt = facts.pages.reduce((sum, page) => sum + (num(page?.images_without_alt) || 0), 0);
      return [missingAlt ? 'ISSUE_SAMPLE' : 'CLEAN_SAMPLE', `Images without alt text in the sample: ${missingAlt}. This is an automated screen, not a WCAG certificate, and not an answer-engine score.`];
    }
    return unt(label, ttfbSentence(facts));
  },
  '32': (facts, label) => {
    if (has(label, 'sitemap')) return sitemapSentence(facts);
    if (has(label, 'canonical')) return HANDLERS['26'](facts, 'Canonical URL correctness');
    if (has(label, 'international') || has(label, 'hreflang')) return HANDLERS['39'](facts, 'hreflang and canonical consistency');
    if (has(label, 'pagination') || has(label, 'versioned') || has(label, 'migration')) return unt(label, `That URL-architecture check was not run. ${facts.sample}`);
    if (facts.pages.length === 0) return unt(label, facts.sample);
    return ['INFERRED', `Fetched URLs: ${join(facts.pages.slice(0, 5).map((page) => String(page?.url || '')), 5)}. ${facts.sample}`];
  },
  '33': (facts, label) => platformAbsent(facts, label, 'Featured snippets'),
  '34': (facts, label) => platformAbsent(facts, label, 'People Also Ask'),
  '35': (facts, label) => platformAbsent(facts, label, 'Google AI Overviews, AI Mode, and featured snippets'),
  '36': (facts, label) => {
    if (facts.simulation === 'SIMULATION_ONLY' && facts.runs <= 0) {
      return ['NOT_TESTED', `${label} was not a live query. The per-engine matrix is SIMULATION_ONLY, an on-page writing exercise. ${liveSentence(facts)}`];
    }
    if (facts.runs <= 0) return platformAbsent(facts, label, 'ChatGPT, Perplexity, Gemini, Copilot, and Claude consumer surfaces');
    return ['INFERRED', `${liveSentence(facts)} Recommendation context was not a separate field. ${recommendation(facts)[1]}`];
  },
  '37': (facts, label) => unt(label, 'Voice assistants were not queried. No spoken-answer selection is assumed, and brand pronunciation was not tested.'),
  '38': (facts, label) => {
    if (has(label, 'public versus private')) return unt(label, `Authenticated help content was not compared with public pages. ${facts.sample}`);
    const docs = facts.pages.filter((page) => ['/help', '/docs', '/support', '/faq', 'knowledge'].some((token) => String(page?.url || '').toLowerCase().includes(token)));
    if (docs.length) return ['INFERRED', `URLs in the sample that look like help or docs: ${join(docs.map((page) => String(page.url)), 4)}. ${coverageSentence(facts)}`];
    if (facts.crawled === 0) return unt(label, facts.sample);
    return ['INFERRED', `No help, docs, support, or FAQ URL was in the crawled sample. ${facts.sample} ${coverageSentence(facts)}`];
  },
  '39': (facts, label) => {
    if (facts.intl && facts.intl.is_multilingual === false && has(label, 'hreflang', 'translation', 'localized', 'regional', 'country-specific', 'currency')) {
      return ['NOT_APPLICABLE', 'The international audit records this site as not multilingual. hreflang and regional-price checks do not apply.'];
    }
    const langs = facts.pages.map((page) => String(page?.html_lang || '')).filter(Boolean);
    if (has(label, 'hreflang') || has(label, 'canonical')) {
      if (new Set(langs).size <= 1) return ['NOT_APPLICABLE', `One or no language was recorded (${join([...new Set(langs)], 3)}). hreflang is not required by this sample alone.`];
    }
    if (langs.length === 0 && facts.crawled === 0) return unt(label, 'No page language was crawled.');
    return ['INFERRED', `Languages in the sample: ${join([...new Set(langs)], 6) || 'none recorded'}. Translation quality was not reviewed by a person. ${profileLine(facts, 'Market', ['geography'])[1]}`];
  },
  '40': (facts, label) => {
    if (has(label, 'confidence interval')) return unt(label, 'No confidence interval is calculated. Repeated runs, when stored, are still not universal visibility.');
    if (facts.runs <= 0) return unt(label, `A live benchmark was not stored. ${coverageSentence(facts)} ${liveSentence(facts)}`);
    return ['VERIFIED', `Successful runs: ${facts.runs}. Raw response retention is limited to what the scorecard stored. ${liveSentence(facts)}`];
  },
  '41': (facts) => claimsSentence(facts),
  '42': (facts, label) => {
    if (facts.runs <= 0) return unt(label, `Citation URLs were not captured because no successful live run is stored. ${liveSentence(facts)}`);
    if (facts.rates.citation == null) return gap(label, `A live run exists and the citation rate field is empty. Empty is not zero citations. ${liveSentence(facts)}`);
    if (has(label, 'share')) return HANDLERS['02'](facts, 'Competitive answer share');
    return rate(facts, 'citation', 'Citation rate', 'At least one qualifying citation to the brand domain ÷ valid responses.');
  },
  '43': (facts, label) => {
    if (has(label, 'knowledge panel')) return unt(label, 'Knowledge panel presence was not queried.');
    const entity = entitySentence(facts);
    if (entity[0] !== 'NOT_TESTED') return entity;
    return profileLine(facts, label, ['business_name', 'products', 'services', 'geography']);
  },
  '44': (facts, label) => {
    if (has(label, 'recommended') || has(label, 'superlative') || has(label, 'positive') || has(label, 'framing')) return recommendation(facts);
    if (has(label, 'mentioned') || has(label, 'omitted')) return rate(facts, 'mention', 'Brand mention rate', 'Valid responses mentioning the brand ÷ valid responses.');
    if (has(label, 'pricing')) return HANDLERS['04'](facts, 'Stale pricing and policy information');
    if (has(label, 'comparison')) return HANDLERS['23'](facts, 'Product comparison criteria');
    return ['NOT_TESTED', `How a live answer described the brand was not stored. ${liveSentence(facts)} ${profileLine(facts, label, ['value_proposition'])[1]}`];
  },
  '45': (facts, label) => {
    if (has(label, 'human verification') || has(label, 'correction prior')) {
      const rows = where(facts, 'CONFLICTING');
      if (rows.length || facts.contradictions.length) return ['ISSUE_SAMPLE', `Human review is required for the stored conflicts. ${contradictionSentence(facts)}`];
      return unt(label, `No conflicting answer was stored, so no correction queue was opened. ${liveSentence(facts)}`);
    }
    if (facts.rates.hallucination != null) return rate(facts, 'hallucination', 'Hallucination rate', 'Inaccurate generated answers ÷ valid live responses.');
    if (facts.conflicting || facts.contradictions.length) return ['ISSUE_SAMPLE', `On-page conflicts are stored. They are not, by themselves, a live hallucination. ${contradictionSentence(facts)}`];
    return unt(label, 'No live hallucination judgment and no on-page conflict were stored. Incorrect features, prices, and affiliations are not invented.');
  },
  '46': (facts, label) => unt(label, `Third-party reviews, directories, and independent articles were not collected. ${liveSentence(facts)}`),
  '47': (facts, label) => {
    if (!facts.bakeoff && facts.rates.competitor == null) return unt(label, `${bakeoffSentence(facts)} Defensible opportunities are the unanswered questions, without a competitor citation attached. ${gapExamples(facts)}`);
    return ['INFERRED', `${bakeoffSentence(facts)} ${gapExamples(facts)} ${liveSentence(facts)}`];
  },
  '48': (facts, label) => {
    if (has(label, 'search console') || has(label, 'question performance')) return gscSentence(facts);
    if (has(label, 'referral') || has(label, 'engine')) return gap(label, `AI referral sessions were not identified. GA4, when connected, is not automatically an answer-engine referral report. ${ga4Sentence(facts)[1]}`);
    return ga4Sentence(facts);
  },
  '49': (facts, label) => {
    if (has(label, 'revenue')) return gap(label, `Revenue was not attributed. GA4 key events are not revenue. ${ga4Sentence(facts)[1]}`);
    if (has(label, 'ai referral')) return gap(label, `AI referral conversions were not measured. ${ga4Sentence(facts)[1]}`);
    return ga4Sentence(facts);
  },
  '50': (facts, label) => unt(label, `No forecast is produced. Demand, addressable audience, citation opportunity, effort, cost, conversion assumptions, time to impact, and upside scenarios are not estimated. A visibility gap is not a traffic or revenue forecast. ${coverageSentence(facts)}`),
  '51': (facts, label) => {
    if (facts.assessed === 0 && facts.crawled === 0) return unt(label, `${facts.sample} ${coverageSentence(facts)}`);
    const target = facts.questions.find((item) => item.status !== 'ANSWERABLE' && item.url) || facts.questions[0];
    const page = target?.url || facts.pages[0]?.url || 'no URL';
    if (target && target.status !== 'ANSWERABLE' && has(label, 'missing', 'recommended', 'quality', 'questions', 'evidence', 'review')) {
      return ['ISSUE_SAMPLE', `Page in scope: ${page}. ${fixFor(target)}${issue(page, 'The stored question does not have a usable answer.', fixFor(target))}`];
    }
    return ['INFERRED', `Page in scope: ${page}. ${coverageSentence(facts)} ${schemaSentence(facts)} ${liveSentence(facts)} No improvement is claimed now.`];
  },
  '52': (facts, label) => {
    if (has(label, 'owner') || has(label, 'effort') || has(label, 'completion status')) return unt(label, 'Owners, effort, and completion status were not assigned. The question rows are the register.');
    if (has(label, 'retest')) return ['INFERRED', `Retest condition: the same question text, the same engine list, and a new timestamp. ${liveSentence(facts)}`];
    if (facts.assessed === 0) return unt(label, coverageSentence(facts));
    return ['INFERRED', `The register has ${facts.assessed} question row(s) from ${facts.questionSource}. ${coverageSentence(facts)} ${quotes(facts.questions, 2)}`];
  },
  '53': (facts, label) => unt(label, `No before-and-after implementation was stored, so nothing is marked improved. ${coverageSentence(facts)} ${liveSentence(facts)}`),
  '54': (facts, label) => unt(label, `No monitoring schedule was armed. A later run can compare question status, live mention rate, and live citation rate only when those values are stored again. ${coverageSentence(facts)} ${liveSentence(facts)}`),
  '55': (facts, label) => {
    if (has(label, 'sampling') || has(label, 'scope')) return ['INFERRED', `${facts.sample} The sample is not exhaustive sitewide coverage.`];
    if (has(label, 'engine') || has(label, 'model') || has(label, 'platform version') || has(label, 'test environment')) return ['INFERRED', liveSentence(facts)];
    if (has(label, 'scoring') || has(label, 'confidence') || has(label, 'uncertainty') || has(label, 'missing-data')) return ['INFERRED', `Rates keep their denominators. A missing input stays unmeasured. ${SEPARATION} ${coverageSentence(facts)}`];
    return ['INFERRED', `${SEPARATION} ${facts.sample} ${liveSentence(facts)} Report timestamp: ${facts.generatedAt}.`];
  },
};

function contentOrUntested(facts: Facts, label: string, detail: string): Result {
  if (facts.crawled === 0 && facts.assessed === 0) return unt(label, facts.sample);
  if (has(label, 'table') || has(label, 'landmark') || has(label, 'accessible name')) return unt(label, `${detail} ${facts.sample}`);
  return ['INFERRED', `${detail} ${coverageSentence(facts)} ${facts.sample}`];
}

function appendix(facts: Facts, number: string, label: string): Result {
  if (number === 'A') {
    if (has(label, 'domain')) return ['VERIFIED', `Audited domain: ${facts.domain}.`];
    if (has(label, 'business')) return profileLine(facts, label, ['business_name', 'business_model', 'industry']);
    if (has(label, 'product')) return profileLine(facts, label, ['products', 'services']);
    if (has(label, 'market')) return profileLine(facts, label, ['geography']);
    if (has(label, 'language')) return ['INFERRED', 'Languages observed come from the crawled sample. None are invented.'];
    if (has(label, 'platform')) return ['INFERRED', liveSentence(facts)];
    return ['INFERRED', `${facts.sample} Exclusions: surfaces and connectors named as not tested in the chapters above.`];
  }
  if (number === 'B') return facts.assessed ? ['INFERRED', coverageSentence(facts)] : unt(label, coverageSentence(facts));
  if (number === 'C') return HANDLERS['10'](facts, label);
  if (number === 'D') return HANDLERS['12'](facts, label === 'Evaluated answers' ? 'Core answer presence' : label);
  if (number === 'E') return HANDLERS['40'](facts, label);
  if (number === 'F') return HANDLERS['42'](facts, label);
  if (number === 'G') {
    if (has(label, 'price') || has(label, 'polic')) return HANDLERS['04'](facts, 'Stale pricing and policy information');
    if (has(label, 'claim') || has(label, 'source')) return claimsSentence(facts);
    return profileLine(facts, label, ['business_name', 'products', 'services']);
  }
  if (number === 'H') return HANDLERS['47'](facts, label);
  if (number === 'I') {
    if (has(label, 'crawl') || has(label, 'http')) return HANDLERS['25'](facts, 'HTTP response status');
    if (has(label, 'render')) return HANDLERS['27'](facts, 'Raw HTML versus rendered DOM');
    if (has(label, 'index')) return HANDLERS['26'](facts, 'Indexable answer pages');
    return HANDLERS['29'](facts, 'Structured data eligibility and limitations');
  }
  if (number === 'J') return has(label, 'owner') || has(label, 'status') ? HANDLERS['52'](facts, 'Owner and estimated effort') : HANDLERS['51'](facts, 'Recommended content changes');
  if (number === 'K') {
    if (has(label, 'weight')) return ['INFERRED', `The four dimensions are not weighted into one AEO grade. ${SEPARATION}`];
    if (has(label, 'exclusion')) return ['INFERRED', 'Excluded from rates: failed runs, unqueried surfaces, simulated writing exercises, and missing connectors. A missing value is not zero.'];
    if (has(label, 'denominator')) return ['INFERRED', 'Question coverage uses assessed questions. Mention, recommendation, and citation rates use valid responses. Citation share uses qualifying citations to all tracked domains. A response may both mention and cite.'];
    return ['INFERRED', `Question coverage = usable verified answers ÷ assessed questions. Brand mention rate = responses mentioning the brand ÷ valid responses. Brand recommendation rate was not stored as its own flag. Citation rate = responses with a qualifying brand-domain citation ÷ valid responses. AI referral conversion rate = attributed conversions ÷ eligible AI referral sessions. ${SEPARATION}`];
  }
  if (number === 'L') {
    if (has(label, 'revenue')) return HANDLERS['49'](facts, 'Revenue attribution');
    if (has(label, 'conversion')) return HANDLERS['49'](facts, 'Conversions from answer pages');
    if (has(label, 'referral')) return HANDLERS['48'](facts, 'Referral traffic from answer platforms');
    if (has(label, 'limitation') || has(label, 'attribution')) return ['INFERRED', `Clicks are not conversions. Key events are not revenue. AI referrals were not separated. ${ga4Sentence(facts)[1]}`];
    return HANDLERS['48'](facts, 'Organic search traffic to answer pages');
  }
  if (number === 'M') return ['INFERRED', `Findings stored: ${facts.findings.length}. Question rows stored: ${facts.assessed}. Live runs: ${facts.runs}. Report timestamp: ${facts.generatedAt}. Evidence states are verified, sample verified with or without an issue, inferred, not tested, data unavailable, and not applicable.`];
  if (number === 'N') {
    if (has(label, 'engine')) return ['INFERRED', liveSentence(facts)];
    if (has(label, 'integration')) return ['INFERRED', `Search Console: ${facts.gscState}. GA4: ${facts.ga4State}. Neither missing connector is a zero.`];
    if (has(label, 'sample')) return ['INFERRED', facts.sample];
    return ['INFERRED', `${gapExamples(facts)} ${coverageSentence(facts)}`];
  }
  if (has(label, 'scoring interpretation')) {
    return ['INFERRED', `Sample verified · issue means the checked sample contains the gap. Sample verified · no issue means that check was clean in the sample. Verified is a connected or live measurement. A chapter with no test is not a pass. ${SEPARATION}`];
  }
  if (has(label, 'metric')) return appendix(facts, 'K', 'Metric definitions');
  return ['INFERRED', `AEO asks whether a source can satisfy a question and be used in an answer. SEO asks whether the site can be discovered and perform in search. GEO asks how a brand is represented in generative answers. CRO asks whether visitors take a valuable action. A page can rank and still fail a question. A good answer can exist and still not be cited. ${SEPARATION}`];
}

function chapterStatus(codes: AeoStatus[]): AeoStatus {
  if (codes.includes('ISSUE_SAMPLE')) return 'ISSUE_SAMPLE';
  if (codes.includes('VERIFIED')) return 'VERIFIED';
  if (codes.includes('CLEAN_SAMPLE')) return 'CLEAN_SAMPLE';
  if (codes.includes('INFERRED')) return 'INFERRED';
  if (codes.includes('DATA_UNAVAILABLE')) return 'DATA_UNAVAILABLE';
  if (codes.includes('NOT_TESTED')) return 'NOT_TESTED';
  return 'NOT_APPLICABLE';
}

function blurb(facts: Facts, number: string): string {
  if (['01', '02', '11', '12', '15'].includes(number)) return `${coverageSentence(facts)} ${SEPARATION}`;
  if (['33', '34', '35', '36', '37', '40', '42', '44', '45'].includes(number)) return liveSentence(facts);
  if (['48', '49', '50', 'L'].includes(number)) return `${ga4Sentence(facts)[1]} No forecast is produced.`;
  if (['25', '26', '27', '31', '32', 'I'].includes(number)) return `${facts.sample} ${ttfbSentence(facts)}`;
  return `${facts.sample} ${coverageSentence(facts)}`;
}

export function resolveAeoAudit(report: ExecutiveReport): ResolvedAeoAudit {
  const facts = buildFacts(report);
  const counts: Record<AeoStatus, number> = {
    ISSUE_SAMPLE: 0,
    CLEAN_SAMPLE: 0,
    VERIFIED: 0,
    INFERRED: 0,
    DATA_UNAVAILABLE: 0,
    NOT_TESTED: 0,
    NOT_APPLICABLE: 0,
  };
  const sections = AEO_SECTIONS.map((section) => {
    const checks = section.checks.map((label) => {
      const [status, result] = line(facts, section.number, label);
      counts[status] += 1;
      return { label, status, result };
    });
    return {
      number: section.number,
      part: section.part,
      title: section.title,
      status: chapterStatus(checks.map((check) => check.status)),
      summary: blurb(facts, section.number),
      checks,
    };
  });
  return {
    sampleNotice: `${facts.sample} Every section below is a result from this run. A missing source is not a zero and not a pass. ${SEPARATION}`,
    sections,
    counts,
  };
}
