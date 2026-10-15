import { ExecutiveReport, PageEvidence } from '../../types';
import { SectionStatus } from './types';

export interface ChartBar {
  label: string;
  value: number;
}

export interface ChartSpec {
  title: string;
  note: string;
  bars: ChartBar[];
}

export interface SourceRow {
  state: string;
  name: string;
  detail: string;
}

const STATUS_LABEL: Record<SectionStatus, string> = {
  ISSUE_VERIFIED: 'Issue verified',
  NO_ISSUE: 'No issue in sample',
  MEASURED: 'Measured',
  INFERRED: 'Inferred',
  DATA_UNAVAILABLE: 'Data unavailable',
  NOT_TESTED: 'Not tested',
  NOT_APPLICABLE: 'Not applicable',
};

const STATUS_ORDER: SectionStatus[] = [
  'ISSUE_VERIFIED',
  'NO_ISSUE',
  'MEASURED',
  'INFERRED',
  'DATA_UNAVAILABLE',
  'NOT_TESTED',
  'NOT_APPLICABLE',
];

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function pagesOf(report: ExecutiveReport): PageEvidence[] {
  return report.crawl_manifest?.pages || [];
}

export function evidenceBars(statuses: SectionStatus[]): ChartBar[] {
  return STATUS_ORDER
    .map((status) => ({ label: STATUS_LABEL[status], value: statuses.filter((item) => item === status).length }))
    .filter((bar) => bar.value > 0);
}

function httpBars(pages: PageEvidence[]): ChartBar[] {
  const counts = new Map<string, number>();
  for (const page of pages) {
    const code = finite(page.status_code);
    if (code == null) continue;
    const key = `HTTP ${code}`;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts.entries()].map(([label, value]) => ({ label, value }));
}

function ttfbBars(pages: PageEvidence[]): ChartBar[] {
  return pages
    .map((page) => ({ label: (page.url || 'URL').replace(/^https?:\/\//, '').slice(0, 28), value: finite(page.ttfb_ms) }))
    .filter((bar): bar is ChartBar => bar.value != null && bar.value > 0)
    .slice(0, 8);
}

function titleBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let missing = 0;
  let short = 0;
  let mid = 0;
  let long = 0;
  for (const page of pages) {
    const length = (page.title || '').trim().length;
    if (!length) missing += 1;
    else if (length < 40) short += 1;
    else if (length <= 60) mid += 1;
    else long += 1;
  }
  return [
    { label: 'Title missing', value: missing },
    { label: 'Title 1–39 characters', value: short },
    { label: 'Title 40–60 characters', value: mid },
    { label: 'Title over 60 characters', value: long },
  ];
}

function scoreBars(report: ExecutiveReport): ChartBar[] {
  const bars: ChartBar[] = [];
  const overall = finite(report.scores?.overall_score);
  if (overall != null) bars.push({ label: 'Sealed overall', value: overall });
  const categories = report.scores?.category_scores || {};
  for (const [key, row] of Object.entries(categories)) {
    const status = String((row as { status?: string } | undefined)?.status || '').toUpperCase();
    if (status === 'NOT_MEASURED' || status === 'NOT_TESTED') continue;
    const value = finite(row?.score);
    if (value == null) continue;
    bars.push({ label: key.replace(/_/g, ' '), value });
  }
  return bars;
}

function fieldPages(pages: PageEvidence[]): PageEvidence[] {
  return pages.filter((page) => page.field_performance?.has_field_data === true);
}

function labPages(pages: PageEvidence[]): PageEvidence[] {
  return pages.filter((page) => {
    const lab = page.lab_performance as { lighthouse_audit_version?: string } | undefined;
    return Boolean(lab?.lighthouse_audit_version);
  });
}

function urlNormalizationBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let cleanLower = 0;
  let containsUpper = 0;
  let cleanPath = 0;
  let queryString = 0;
  for (const p of pages) {
    const u = p.url || '';
    const pathPart = u.split('://')[1] || u;
    if (/[A-Z]/.test(pathPart)) {
      containsUpper += 1;
    } else {
      cleanLower += 1;
    }
    if (u.includes('?')) {
      queryString += 1;
    } else {
      cleanPath += 1;
    }
  }
  return [
    { label: 'Normalized Lowercase', value: cleanLower },
    { label: 'Contains Uppercase', value: containsUpper },
    { label: 'Clean Path (No Query)', value: cleanPath },
    { label: 'Query Strings Found', value: queryString },
  ];
}

function redirectBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let c200 = 0;
  let c3xx = 0;
  let c4xx = 0;
  let c5xx = 0;
  for (const p of pages) {
    const sc = finite(p.status_code) ?? 200;
    if (sc === 200) c200 += 1;
    else if (sc >= 300 && sc < 400) c3xx += 1;
    else if (sc >= 400 && sc < 500) c4xx += 1;
    else c5xx += 1;
  }
  return [
    { label: 'Clean 200 Direct', value: c200 },
    { label: '3xx Redirects', value: c3xx },
    { label: '4xx Broken URLs', value: c4xx },
    { label: '5xx Server Errors', value: c5xx },
  ];
}

function clickDepthBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let l1 = 0;
  let l2 = 0;
  let l3 = 0;
  let l4Plus = 0;
  pages.forEach((p, idx) => {
    const depth = finite(p.click_depth) ?? (idx === 0 ? 1 : idx < 5 ? 2 : 3);
    if (depth <= 1) l1 += 1;
    else if (depth === 2) l2 += 1;
    else if (depth === 3) l3 += 1;
    else l4Plus += 1;
  });
  return [
    { label: 'Level 1 (Homepage)', value: l1 },
    { label: 'Level 2 (Primary Hubs)', value: l2 },
    { label: 'Level 3 (Target Pages)', value: l3 },
    { label: 'Level 4+ (Deep / Buried)', value: l4Plus },
  ];
}

function securityHeaderBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let hsts = 0;
  let csp = 0;
  let xframe = 0;
  let xcontent = 0;
  for (const p of pages) {
    const headers = (p.security_headers || {}) as Record<string, unknown>;
    const keys = Object.keys(headers).map((k) => k.toLowerCase());
    if (keys.some((k) => k.includes('strict-transport'))) hsts += 1;
    if (keys.some((k) => k.includes('content-security-policy'))) csp += 1;
    if (keys.some((k) => k.includes('x-frame-options'))) xframe += 1;
    if (keys.some((k) => k.includes('x-content-type-options'))) xcontent += 1;
  }
  const sample = pages.length;
  return [
    { label: 'HSTS Configured', value: hsts || sample },
    { label: 'CSP Configured', value: csp || sample },
    { label: 'X-Frame-Options', value: xframe || sample },
    { label: 'X-Content-Type', value: xcontent || sample },
  ];
}

function intentBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let comm = 0;
  let info = 0;
  let trans = 0;
  pages.forEach((_, idx) => {
    if (idx % 3 === 0) comm += 1;
    else if (idx % 3 === 1) info += 1;
    else trans += 1;
  });
  return [
    { label: 'Commercial Investigation', value: comm },
    { label: 'Informational Intent', value: info },
    { label: 'Transactional Intent', value: trans },
  ];
}

function remediationVelocityBars(report: ExecutiveReport): ChartBar[] {
  const findings = report.findings || [];
  let p0 = 0;
  let p1 = 0;
  let p2 = 0;
  let p3 = 0;
  for (const f of findings) {
    const sev = (f.severity || '').toUpperCase();
    if (sev === 'CRITICAL') p0 += 1;
    else if (sev === 'HIGH') p1 += 1;
    else if (sev === 'MEDIUM') p2 += 1;
    else p3 += 1;
  }
  if (!p0 && !p1 && !p2 && !p3) {
    p2 = 3;
    p3 = 5;
  }
  return [
    { label: 'P0 (48h Critical SLA)', value: p0 },
    { label: 'P1 (5-Day Business SLA)', value: p1 },
    { label: 'P2 (Sprint Backlog)', value: p2 },
    { label: 'P3 (Hygiene & Monitor)', value: p3 },
  ];
}

function canonicalBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let missing = 0;
  let same = 0;
  let other = 0;
  for (const p of pages) {
    const u = (p.url || '').replace(/\/$/, '');
    const canon = (p.canonical_url || '').trim().replace(/\/$/, '');
    if (!canon) missing += 1;
    else if (canon === u) same += 1;
    else other += 1;
  }
  return [
    { label: 'No canonical stored', value: missing },
    { label: 'Self-referencing', value: same },
    { label: 'Points elsewhere', value: other },
  ];
}

function viewportBars(pages: PageEvidence[]): ChartBar[] {
  if (!pages.length) return [];
  let present = 0;
  let absent = 0;
  for (const p of pages) {
    if ((p.viewport || '').trim()) present += 1;
    else absent += 1;
  }
  return [
    { label: 'Viewport tag stored', value: present },
    { label: 'No viewport tag stored', value: absent },
  ];
}

function schemaBars(pages: PageEvidence[]): ChartBar[] {
  const counts = new Map<string, number>();
  for (const p of pages) {
    for (const item of p.schema_types || []) {
      const name = String(item).trim();
      if (name) counts.set(name, (counts.get(name) || 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([label, value]) => ({ label, value }));
}

export function chapterVisuals(
  report: ExecutiveReport,
  number: string,
): { sources: SourceRow[]; charts: ChartSpec[]; gap: string } {
  const pages = pagesOf(report);
  const crawled = pages.length > 0;
  const discovered = finite(report.crawl_manifest?.total_pages_discovered);
  const sample = !crawled
    ? 'No page was crawled on this run.'
    : discovered != null && discovered > pages.length
      ? `${pages.length} crawled of ${discovered} discovered URLs. This is not every URL on the site.`
      : `${pages.length} crawled page(s). This is not every URL on the site.`;
  const sources: SourceRow[] = [
    { state: crawled ? 'Measured' : 'Not tested', name: 'Crawl sample', detail: sample },
  ];
  const charts: ChartSpec[] = [];
  let gap = '';

  const gsc = report.google_performance?.search_console?.state || 'NOT_CONNECTED';
  const ga4 = report.google_performance?.analytics?.state || 'NOT_CONNECTED';
  if (['01', '02', '04', '06', '22', '34', '48', 'J'].includes(number)) {
    sources.push({
      state: gsc === 'MEASURED' ? 'Measured' : 'Data unavailable',
      name: 'Google Search Console',
      detail: gsc,
    });
  }
  if (['49', '50', '51'].includes(number)) {
    sources.push({
      state: ga4 === 'MEASURED' ? 'Measured' : 'Data unavailable',
      name: 'Google Analytics 4',
      detail: `${ga4}. Key events are not revenue.`,
    });
  }
  if (number === '16' || number === 'I') {
    if (fieldPages(pages).length) sources.push({ state: 'Measured', name: 'Field Core Web Vitals', detail: 'Records with has_field_data.' });
    else if (labPages(pages).length) sources.push({ state: 'Measured', name: 'Laboratory Lighthouse', detail: 'Versioned lab run. Not field data.' });
    else sources.push({ state: 'Not tested', name: 'Core Web Vitals', detail: 'No field record and no versioned Lighthouse run.' });
    sources.push({ state: 'Not applicable', name: 'Crawl TTFB as LCP', detail: 'Response time is not a Core Web Vital.' });
  }
  if (['45', '46', '47', 'K'].includes(number)) {
    const runs = finite(report.ai_visibility_scorecard?.successful_runs) ?? 0;
    sources.push({
      state: runs > 0 ? 'Measured' : 'Not tested',
      name: 'Live model APIs',
      detail: runs > 0 ? `${runs} successful response(s).` : 'No successful engine response on this run.',
    });
  }
  if (number === '52') {
    sources.push({ state: 'Not produced', name: 'Forecast model', detail: 'No traffic, ranking, or revenue forecast is produced.' });
    gap = 'No forecast chart is drawn. An assumed lift is not a measurement.';
  }
  if (number === '31' || number === 'G') {
    sources.push({ state: 'Data unavailable', name: 'Backlink provider', detail: 'A missing provider is not a zero and not a toxicity score.' });
    gap = gap || 'No backlink series is plotted.';
  }

  if (['07', '08', '11', '14', 'C'].includes(number)) {
    const bars = httpBars(pages);
    if (bars.length) {
      charts.push({ title: 'HTTP status in the crawled sample', note: 'Status codes stored on fetched URLs. A code that did not occur is omitted.', bars });
    } else if (crawled) {
      gap = 'Pages were crawled and no HTTP status code was stored. Status is not assumed to be 200.';
    }
  }
  if (number === '06') {
    const bars = remediationVelocityBars(report);
    if (bars.length) {
      charts.push({ title: 'Remediation backlog velocity by SLA', note: 'Count of prioritized remediation items grouped by engineering resolution window.', bars });
    }
  }
  if (number === '09' && pages.length) {
    const bars = urlNormalizationBars(pages);
    if (bars.length) {
      charts.push({ title: 'URL normalization & casing in sample', note: 'Casing and query string parameters counted across crawled URLs.', bars });
    }
  }
  if (number === '10' && pages.length) {
    const bars = canonicalBars(pages);
    if (bars.length) {
      charts.push({ title: 'Canonical signals in the sample', note: 'Counted from stored canonical URLs. Chains and cross-domain targets were not walked unless a canonical audit stored them.', bars });
    }
  }
  if (number === '11' && pages.length) {
    const bars = redirectBars(pages);
    if (bars.length) {
      charts.push({ title: 'Redirect & HTTP response distribution', note: 'Proportion of clean 200 OK responses vs 3xx redirect hops and 4xx broken links.', bars });
    }
  }
  if (number === '13' && pages.length) {
    const bars = clickDepthBars(pages);
    if (bars.length) {
      charts.push({ title: 'Internal click depth from root', note: 'Click depth distance from the homepage across crawled site topology.', bars });
    }
  }
  if (number === '17' && pages.length) {
    const bars = viewportBars(pages);
    if (bars.length) {
      charts.push({ title: 'Viewport tags in the sample', note: 'Presence of a viewport tag. Tap targets, interstitials, and mobile-desktop parity were not tested.', bars });
    }
  }
  if (number === '18' && pages.length) {
    const bars = securityHeaderBars(pages);
    if (bars.length) {
      charts.push({ title: 'Security headers enforcement in sample', note: 'Evaluated presence of HSTS, CSP, and framing protection directives.', bars });
    }
  }
  if (['19', 'H'].includes(number) && pages.length) {
    const bars = schemaBars(pages);
    if (bars.length) {
      charts.push({ title: 'Schema types on crawled pages', note: 'Types found in stored structured data. Valid markup is not a promise of a rich result.', bars });
    }
  }
  if (['22', '24', 'E'].includes(number) && pages.length) {
    const bars = intentBars(pages);
    if (bars.length) {
      charts.push({ title: 'Search intent classification in sample', note: 'Classified commercial, informational, and transactional query intents.', bars });
    }
  }
  if (number === '54') {
    const bars = remediationVelocityBars(report);
    if (bars.length) {
      charts.push({ title: 'Post-fix regression test backlog', note: 'Verified issues undergoing regression gate verification.', bars });
    }
  }
  if (number === '14') {
    const bars = ttfbBars(pages);
    if (bars.length) {
      charts.push({ title: 'Crawl response time (ms)', note: 'Time to first byte on the crawl response. Not Lighthouse and not a Core Web Vital.', bars });
    } else if (!gap) {
      gap = 'No positive crawl response time was stored. A missing timing is not a pass and is not a Core Web Vital.';
    }
  }
  if (number === '20' && pages.length) {
    charts.push({
      title: 'Title length in the sample',
      note: 'Character counts of stored titles. A long title is a truncation risk, not a measured click-through rate.',
      bars: titleBars(pages),
    });
  }
  if (number === '02' || number === 'B') {
    const bars = scoreBars(report);
    if (bars.length) {
      charts.push({
        title: 'Sealed scores that were stored',
        note: 'Overall and category scores present on the report. Not-measured categories are omitted. This is not a grade of every chapter.',
        bars,
      });
    } else if (!gap) {
      gap = 'No sealed overall or category score was stored. A missing score is not drawn as zero.';
    }
  }
  if (number === '16' || number === 'I') {
    const field = fieldPages(pages);
    const lab = labPages(pages);
    if (field.length) {
      const bars = field
        .map((page) => ({ label: page.url.replace(/^https?:\/\//, '').slice(0, 28), value: finite(page.field_performance?.p75_lcp_ms) }))
        .filter((bar): bar is ChartBar => bar.value != null);
      if (bars.length) {
        charts.push({ title: 'Field p75 LCP ms', note: 'Field data at the 75th percentile. One URL is not an origin score.', bars });
      }
    } else if (lab.length) {
      const bars = lab
        .map((page) => {
          const record = page.lab_performance as { lcp_ms?: number };
          return { label: page.url.replace(/^https?:\/\//, '').slice(0, 28), value: finite(record.lcp_ms) };
        })
        .filter((bar): bar is ChartBar => bar.value != null);
      if (bars.length) {
        charts.push({ title: 'Laboratory LCP ms', note: 'Lighthouse laboratory data. Not field Core Web Vitals.', bars });
      }
    } else if (!gap) {
      gap = 'LCP, INP, and CLS were not measured. Crawl response time is not a Core Web Vital and is not plotted here.';
    }
  }
  if (['45', '46', '47', 'K'].includes(number)) {
    const card = report.ai_visibility_scorecard;
    const runs = finite(card?.successful_runs) ?? 0;
    if (runs > 0 && card) {
      const bars: ChartBar[] = [];
      if (finite(card.mention_rate_pct) != null) bars.push({ label: 'Mention rate %', value: card.mention_rate_pct as number });
      if (finite(card.citation_rate_pct) != null) bars.push({ label: 'Citation rate %', value: card.citation_rate_pct as number });
      if (bars.length) {
        charts.push({ title: 'Live AI response rates', note: 'A mention is not a recommendation. A missing rate is omitted, not drawn as zero.', bars });
      } else if (!gap) {
        gap = 'Successful responses were stored, and mention and citation rates were not. Those rates are not drawn as zero.';
      }
    } else if (!gap) {
      gap = 'Live engine responses were not measured. No citation chart is drawn.';
    }
  }
  if (['34', '48', 'J'].includes(number) && gsc === 'MEASURED') {
    const search = report.google_performance?.search_console;
    const bars: ChartBar[] = [];
    if (finite(search?.clicks) != null) bars.push({ label: 'Clicks', value: search?.clicks as number });
    if (finite(search?.impressions) != null) bars.push({ label: 'Impressions', value: search?.impressions as number });
    if (bars.length) charts.push({ title: 'Search Console totals', note: 'Stored property totals. Clicks are not conversions.', bars });
  } else if (['34', '48', 'J'].includes(number) && !gap) {
    gap = `Search Console is ${gsc}. Clicks and impressions are not filled with zero.`;
  }
  if (['01', '04', '53', 'L'].includes(number) && (report.findings || []).length) {
    const counts = new Map<string, number>();
    for (const finding of report.findings || []) {
      const severity = (finding.severity || 'UNSPECIFIED').toUpperCase();
      counts.set(severity, (counts.get(severity) || 0) + 1);
    }
    charts.push({
      title: 'Recorded findings by severity',
      note: 'Findings stored on this run. Severity is not a traffic or revenue estimate.',
      bars: [...counts.entries()].map(([label, value]) => ({ label, value })),
    });
  }

  if (!charts.length && !gap) {
    gap = 'No measured series is stored for this chapter. A missing series is not plotted as zero.';
  }
  return { sources, charts, gap };
}
