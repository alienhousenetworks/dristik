import { ExecutiveReport, PageEvidence } from '../types';
import { categoryLabel } from './format';

export interface MeasuredBar {
  label: string;
  value: number;
}

export interface MeasuredBreakdown {
  id: string;
  title: string;
  note: string;
  bars: MeasuredBar[];
  category?: 'OVERALL' | 'TECHNICAL_SEO' | 'GEO' | 'UX_CONVERSION';
  /** Appended to the printed value. `%` is printed as `42%`. */
  unit?: string;
  /** Bar width is value / scaleMax. Use 100 for rates. */
  scaleMax?: number;
}

function counts(items: string[]): MeasuredBar[] {
  const tally = new Map<string, number>();
  for (const item of items) {
    tally.set(item, (tally.get(item) || 0) + 1);
  }
  return Array.from(tally.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);
}

function positive(rows: Array<[string, number]>): MeasuredBar[] {
  return rows
    .filter((row) => Number.isFinite(row[1]) && row[1] > 0)
    .map(([label, value]) => ({ label, value }));
}

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function clip(text: string, max = 42): string {
  const clean = text.trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

function uniqueLabels(bars: MeasuredBar[]): MeasuredBar[] {
  const seen = new Map<string, number>();
  return bars.map((bar) => {
    const count = (seen.get(bar.label) || 0) + 1;
    seen.set(bar.label, count);
    if (count === 1) return bar;
    return { ...bar, label: `${bar.label} (${count})` };
  });
}

function pagePath(raw: string): string {
  try {
    const url = new URL(raw);
    const path = `${url.pathname || '/'}${url.search}`;
    return path === '' ? '/' : path;
  } catch {
    return raw;
  }
}

function pagesOf(report: ExecutiveReport): PageEvidence[] {
  return report.crawl_manifest?.pages || [];
}

function add(charts: MeasuredBreakdown[], chart: MeasuredBreakdown | null) {
  if (!chart || chart.bars.length < 2) return;
  charts.push(chart);
}

function httpStatusChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const http = report.http_status_breakdown;
  if (!http || !(http.total_urls_checked > 0)) return null;
  const bars = positive([
    ['2xx', http.count_2xx || 0],
    ['3xx', http.count_3xx || 0],
    ['4xx', http.count_4xx || 0],
    ['5xx', http.count_5xx || 0],
  ]);
  if (bars.length < 2) return null;
  return {
    id: 'chart_http_status',
    title: 'Response classes',
    note: 'HTTP classes recorded on this audit. A single class is not charted.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

type IndexPage = {
  is_redirect?: boolean;
  robots_blocked?: boolean;
  has_noindex?: boolean;
  is_soft_404?: boolean;
  is_duplicate?: boolean;
  canonical_declared?: string | null;
  canonical_match?: boolean;
  indexable?: boolean;
  gsc_coverage_state?: string | null;
};

type IndexRollup = {
  total_pages_evaluated?: number;
  total_pages_audited?: number;
  indexable_count?: number;
  pages?: IndexPage[];
};

function indexRollup(report: ExecutiveReport): IndexRollup | null {
  return (report.indexation_intelligence as IndexRollup | undefined)
    || (report.crawl_manifest?.indexation_rollup as IndexRollup | undefined)
    || null;
}

function indexOutcome(page: IndexPage): string {
  if (page.is_redirect) return 'Redirect';
  if (page.robots_blocked) return 'Blocked by robots.txt';
  if (page.has_noindex) return 'Noindex';
  if (page.is_soft_404) return 'Soft 404';
  if (page.is_duplicate) return 'Duplicate';
  if (page.canonical_declared && page.canonical_match === false) return 'Canonical mismatch';
  if (page.indexable) return 'Indexable';
  return 'Not indexable';
}

const INDEX_ORDER = [
  'Indexable',
  'Noindex',
  'Blocked by robots.txt',
  'Canonical mismatch',
  'Duplicate',
  'Soft 404',
  'Redirect',
  'Not indexable',
];

function indexationChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const rollup = indexRollup(report);
  if (!rollup) return null;
  const pages = Array.isArray(rollup.pages) ? rollup.pages : [];
  if (pages.length >= 2) {
    const tally = new Map<string, number>();
    for (const page of pages) {
      const outcome = indexOutcome(page);
      tally.set(outcome, (tally.get(outcome) || 0) + 1);
    }
    const bars = positive(INDEX_ORDER.map((label) => [label, tally.get(label) || 0]));
    if (bars.length < 2) return null;
    return {
      id: 'chart_indexation',
      title: 'Indexation outcomes',
      note: 'One outcome per crawled URL. A redirect, robots block, or noindex is counted ahead of indexable.',
      category: 'TECHNICAL_SEO',
      bars,
    };
  }
  const total = finite(rollup.total_pages_evaluated) ?? finite(rollup.total_pages_audited);
  const indexable = finite(rollup.indexable_count);
  if (total == null || indexable == null || total < 2 || indexable < 0 || indexable > total) return null;
  const hidden = total - indexable;
  if (indexable === 0 || hidden === 0) return null;
  return {
    id: 'chart_indexation',
    title: 'Indexation outcomes',
    note: 'Indexable versus not indexable from the rollup. Page-level reasons were not stored, so they are not split.',
    category: 'TECHNICAL_SEO',
    bars: [
      { label: 'Indexable', value: indexable },
      { label: 'Not indexable', value: hidden },
    ],
  };
}

function searchConsoleCoverageChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const pages = indexRollup(report)?.pages || [];
  const states = pages
    .map((page) => (page.gsc_coverage_state || '').trim())
    .filter((state) => state.length > 0);
  const bars = counts(states);
  if (states.length < 2 || bars.length < 2) return null;
  return {
    id: 'chart_search_console_coverage',
    title: 'Search Console coverage',
    note: 'Only URLs that already have a Search Console coverage state. HTML indexation is a separate chart.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

function clickDepthChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const depth = report.click_depth;
  if (!depth || !(depth.total_pages_analyzed >= 2)) return null;
  const bars = positive([
    ['1 click', depth.depth_1_count || 0],
    ['2 clicks', depth.depth_2_count || 0],
    ['3 clicks', depth.depth_3_count || 0],
    ['4 or more clicks', depth.depth_4_plus_count || 0],
  ]);
  if (bars.length < 2) return null;
  return {
    id: 'chart_click_depth',
    title: 'Click depth',
    note: 'Clicks from the homepage through crawled links. The homepage is depth 1. This is not a ranking.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

function onPageCoverageChart(pages: PageEvidence[]): MeasuredBreakdown | null {
  if (pages.length < 2) return null;
  const bars: MeasuredBar[] = [];
  const signals: Array<[string, (page: PageEvidence) => boolean]> = [
    ['Title', (page) => Boolean((page.title || '').trim())],
    ['Meta description', (page) => Boolean((page.meta_description || '').trim())],
    ['Schema', (page) => Array.isArray(page.schema_types) && page.schema_types.some((type) => type.trim())],
  ];
  for (const [name, present] of signals) {
    let yes = 0;
    for (const page of pages) if (present(page)) yes += 1;
    const no = pages.length - yes;
    if (yes > 0 && no > 0) {
      bars.push({ label: `${name} present`, value: yes }, { label: `${name} missing`, value: no });
    }
  }
  if (bars.length < 2) return null;
  return {
    id: 'chart_onpage_coverage',
    title: 'On-page coverage',
    note: 'Crawled pages in this sample. A signal is omitted when every page agrees. A page can miss more than one item.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

const TITLE_BANDS = [
  'Under 30 characters',
  '30–49 characters',
  '50–60 characters',
  'Over 60 characters',
];

function titleBand(length: number): string {
  if (length < 30) return TITLE_BANDS[0];
  if (length < 50) return TITLE_BANDS[1];
  if (length <= 60) return TITLE_BANDS[2];
  return TITLE_BANDS[3];
}

const DESCRIPTION_BANDS = [
  'Under 70 characters',
  '70–149 characters',
  '150–160 characters',
  'Over 160 characters',
];

function descriptionBand(length: number): string {
  if (length < 70) return DESCRIPTION_BANDS[0];
  if (length < 150) return DESCRIPTION_BANDS[1];
  if (length <= 160) return DESCRIPTION_BANDS[2];
  return DESCRIPTION_BANDS[3];
}

function lengthChart(
  id: string,
  title: string,
  texts: string[],
  bands: string[],
  bandOf: (length: number) => string,
): MeasuredBreakdown | null {
  if (texts.length < 2) return null;
  const tally = new Map(bands.map((label) => [label, 0]));
  for (const text of texts) {
    const label = bandOf(text.length);
    tally.set(label, (tally.get(label) || 0) + 1);
  }
  const bars = positive(bands.map((label) => [label, tally.get(label) || 0]));
  if (bars.length < 2) return null;
  return {
    id,
    title,
    note: 'Character counts for tags that are present on the crawled pages. Missing tags stay in the coverage chart.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

function h1Chart(pages: PageEvidence[]): MeasuredBreakdown | null {
  if (pages.length < 2) return null;
  let none = 0;
  let one = 0;
  let many = 0;
  for (const page of pages) {
    const count = Array.isArray(page.h1) ? page.h1.filter((item) => item.trim()).length : 0;
    if (count === 0) none += 1;
    else if (count === 1) one += 1;
    else many += 1;
  }
  const bars = positive([
    ['No H1', none],
    ['One H1', one],
    ['More than one H1', many],
  ]);
  if (bars.length < 2) return null;
  return {
    id: 'chart_h1_count',
    title: 'H1 count',
    note: 'One row per crawled page. This is the heading on the page, not a keyword cannibalization result.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

function contentLengthChart(pages: PageEvidence[]): MeasuredBreakdown | null {
  let none = 0;
  let thin = 0;
  let mid = 0;
  let deep = 0;
  let measured = 0;
  for (const page of pages) {
    const words = finite(page.word_count);
    if (words == null || words < 0) continue;
    measured += 1;
    if (words === 0) none += 1;
    else if (words < 250) thin += 1;
    else if (words < 600) mid += 1;
    else deep += 1;
  }
  if (measured < 2 || none === measured) return null;
  const bars = positive([
    ['No extractable text', none],
    ['Under 250 words', thin],
    ['250–599 words', mid],
    ['600 or more words', deep],
  ]);
  if (bars.length < 2) return null;
  return {
    id: 'chart_content_length',
    title: 'Extracted word count',
    note: 'Words extracted from the crawled pages. Pages with no extracted text are shown only when other pages did yield text.',
    category: 'TECHNICAL_SEO',
    bars,
  };
}

function schemaTypeChart(pages: PageEvidence[]): MeasuredBreakdown | null {
  if (pages.length < 2) return null;
  const tally = new Map<string, number>();
  let none = 0;
  for (const page of pages) {
    const types = Array.isArray(page.schema_types)
      ? Array.from(new Set(page.schema_types.map((type) => type.trim()).filter(Boolean)))
      : [];
    if (types.length === 0) {
      none += 1;
      continue;
    }
    for (const type of types) tally.set(type, (tally.get(type) || 0) + 1);
  }
  const typed = Array.from(tally.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 8)
    .map(([label, value]) => ({ label: clip(label), value }));
  const bars = none > 0 ? [...typed, { label: 'No schema', value: none }] : typed;
  if (bars.length < 2) return null;
  return {
    id: 'chart_schema_types',
    title: 'Schema types on crawled pages',
    note: 'A page with two types is counted in both bars. This is presence in the crawl, not a rich-result test.',
    category: 'GEO',
    bars,
  };
}

function imageAltChart(pages: PageEvidence[]): MeasuredBreakdown | null {
  let total = 0;
  let missing = 0;
  for (const page of pages) {
    const images = finite(page.total_images);
    const withoutAlt = finite(page.images_without_alt);
    if (images == null || images <= 0 || withoutAlt == null || withoutAlt < 0 || withoutAlt > images) continue;
    total += images;
    missing += withoutAlt;
  }
  const withAlt = total - missing;
  if (withAlt <= 0 || missing <= 0) return null;
  return {
    id: 'chart_image_alt',
    title: 'Image alt text',
    note: 'Images on the crawled pages. Pages with an inconsistent image count are left out.',
    category: 'TECHNICAL_SEO',
    bars: [
      { label: 'Alt text present', value: withAlt },
      { label: 'Alt text missing', value: missing },
    ],
  };
}

function liveVisibilityChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const card = report.ai_visibility_scorecard;
  if (!card) return null;
  const measured = card.status === 'MEASURED' || card.measurement_kind === 'LIVE_MODEL_API';
  if (!measured || !(card.successful_runs > 0)) return null;
  const rows: Array<[string, number | null]> = [
    ['Mention rate', finite(card.mention_rate_pct)],
    ['Citation rate', finite(card.citation_rate_pct)],
    ['Competitor visibility', finite(card.competitor_visibility_pct)],
  ];
  const bars = rows
    .filter((row): row is [string, number] => row[1] != null)
    .map(([label, value]) => ({ label, value }));
  if (bars.length < 2) return null;
  return {
    id: 'chart_live_visibility_rates',
    title: 'Live answer rates',
    note: 'Rates from engines queried on this run. Citation accuracy is omitted until a span check exists. Model APIs are not Google AI Overviews, AI Mode, or Bing Copilot.',
    category: 'GEO',
    unit: '%',
    scaleMax: 100,
    bars,
  };
}

function landingLabel(page: string, index: number): string {
  const path = page.startsWith('http') ? pagePath(page) : page;
  return clip(path || `Page ${index + 1}`);
}

function ga4SessionsChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const analytics = report.google_performance?.analytics;
  if (analytics?.state !== 'MEASURED' || !Array.isArray(analytics.landing_pages)) return null;
  const rows = analytics.landing_pages
    .map((row, index) => {
      const sessions = finite(row?.sessions);
      const page = (row?.page || '').trim();
      if (sessions == null || sessions < 0 || !page) return null;
      return { label: landingLabel(page, index), value: sessions };
    })
    .filter((row): row is MeasuredBar => row != null && row.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
  if (rows.length < 2) return null;
  return {
    id: 'chart_ga4_landing_sessions',
    title: 'GA4 landing-page sessions',
    note: 'Sessions from the connected Google Analytics 4 property. Estimated traffic is not included.',
    category: 'UX_CONVERSION',
    unit: 'sessions',
    bars: uniqueLabels(rows),
  };
}

function ga4KeyEventsChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const analytics = report.google_performance?.analytics;
  if (analytics?.state !== 'MEASURED' || !Array.isArray(analytics.landing_pages)) return null;
  const rows = analytics.landing_pages
    .map((row, index) => {
      const events = finite(row?.key_events);
      const page = (row?.page || '').trim();
      if (events == null || events < 0 || !page) return null;
      return { label: landingLabel(page, index), value: events };
    })
    .filter((row): row is MeasuredBar => row != null)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
  if (rows.length < 2 || !rows.some((row) => row.value > 0)) return null;
  return {
    id: 'chart_ga4_landing_key_events',
    title: 'GA4 key events by landing page',
    note: 'Key events from the connected Google Analytics 4 property. A rate is not turned into a 0–100 grade.',
    category: 'UX_CONVERSION',
    unit: 'events',
    bars: uniqueLabels(rows),
  };
}

function searchConsoleQueryChart(report: ExecutiveReport): MeasuredBreakdown | null {
  const search = report.google_performance?.search_console;
  if (search?.state !== 'MEASURED' || !Array.isArray(search.queries)) return null;
  const queries = search.queries.filter((row) => (row?.query || '').trim());
  if (queries.length < 2) return null;
  const ranked = (metric: 'clicks' | 'impressions') => uniqueLabels(
    queries
      .map((row) => ({
        label: clip(row.query || ''),
        value: finite(row[metric]) || 0,
      }))
      .filter((row) => row.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8),
  );
  const clickBars = ranked('clicks');
  const impressionBars = ranked('impressions');
  const bars = clickBars.length >= 2 ? clickBars : impressionBars;
  const metric = clickBars.length >= 2 ? 'clicks' : 'impressions';
  if (bars.length < 2) return null;
  return {
    id: 'chart_gsc_queries',
    title: metric === 'clicks' ? 'Search Console queries by clicks' : 'Search Console queries by impressions',
    note: 'Queries from the connected Search Console property. This is not a keyword gap and not a rank forecast.',
    category: 'TECHNICAL_SEO',
    unit: metric,
    bars,
  };
}

/**
 * Breakdowns the score radar and severity donut do not already show.
 * A chart is returned only when the split itself is informative and the
 * numbers come from this audit.
 */
export function measuredBreakdowns(report: ExecutiveReport): MeasuredBreakdown[] {
  const charts: MeasuredBreakdown[] = [];
  const findings = report.findings || [];
  const pages = pagesOf(report);

  const categoryBars = counts(
    findings.map((finding) => categoryLabel(String(finding.category || 'Other')))
  ).filter((bar) => bar.value > 0);
  if (categoryBars.length >= 2) {
    charts.push({
      id: 'chart_findings_by_category',
      title: 'Findings by category',
      note: 'Where the recorded findings sit. Severity is a separate chart.',
      bars: categoryBars,
    });
  }

  const questions = report.geo_readiness?.questions || [];
  const questionBars = counts(questions.map((question) => question.status || 'Unspecified'));
  if (questions.length >= 3 && questionBars.length >= 2) {
    charts.push({
      id: 'chart_geo_answer_status',
      title: 'Buyer questions by answer status',
      note: 'On-page answerability from the crawled pages. This is not a live citation count.',
      bars: questionBars,
    });
  }

  const rubricBars = counts(
    findings
      .map((finding) => finding.confidence_rubric)
      .filter((band): band is 'CERTAIN' | 'LIKELY' | 'GUESSING' =>
        band === 'CERTAIN' || band === 'LIKELY' || band === 'GUESSING')
  );
  if (rubricBars.length >= 2) {
    charts.push({
      id: 'chart_confidence_rubric',
      title: 'Finding confidence',
      note: 'Certain means two sources agree. Guessing is not treated as a measured defect.',
      bars: rubricBars,
    });
  }

  add(charts, httpStatusChart(report));
  add(charts, indexationChart(report));
  add(charts, searchConsoleCoverageChart(report));
  add(charts, clickDepthChart(report));
  add(charts, onPageCoverageChart(pages));
  add(charts, lengthChart(
    'chart_title_length',
    'Title length',
    pages.map((page) => (page.title || '').trim()).filter(Boolean),
    TITLE_BANDS,
    titleBand,
  ));
  add(charts, lengthChart(
    'chart_meta_length',
    'Meta description length',
    pages.map((page) => (page.meta_description || '').trim()).filter(Boolean),
    DESCRIPTION_BANDS,
    descriptionBand,
  ));
  add(charts, h1Chart(pages));
  add(charts, contentLengthChart(pages));
  add(charts, schemaTypeChart(pages));
  add(charts, imageAltChart(pages));
  add(charts, liveVisibilityChart(report));
  add(charts, ga4SessionsChart(report));
  add(charts, ga4KeyEventsChart(report));
  add(charts, searchConsoleQueryChart(report));

  return charts;
}
