import { ExecutiveReport, Finding, PageEvidence } from '../../types';
import { AUDIT_SECTIONS } from './catalog';
import { ResolvedAuditIndex, ResolvedAuditSection, SectionStatus } from './types';
import {
  assignFindingsToChecks,
  buildSectionAnalysis,
  evaluateAuditCheck,
  toFindingRef,
} from './auditAnalysisEngine';

interface AuditContext {
  report: ExecutiveReport;
  pages: PageEvidence[];
  findings: Finding[];
  model: string;
}

interface SectionResult {
  status: SectionStatus;
  summary: string;
  coverage: string;
}

const EMPTY_COUNTS: Record<SectionStatus, number> = {
  NOT_APPLICABLE: 0,
  NOT_TESTED: 0,
  DATA_UNAVAILABLE: 0,
  NO_ISSUE: 0,
  ISSUE_VERIFIED: 0,
  INFERRED: 0,
  MEASURED: 0,
};

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function sampleLine(ctx: AuditContext): string {
  const crawled = ctx.pages.length;
  const discovered = finite(ctx.report.crawl_manifest?.total_pages_discovered);
  if (crawled === 0) return 'No page was crawled on this run.';
  if (discovered != null && discovered > crawled) {
    return `Checked on ${crawled} crawled page${crawled === 1 ? '' : 's'} of ${discovered} discovered URLs. This is not every URL on the site.`;
  }
  return `Checked on ${crawled} crawled page${crawled === 1 ? '' : 's'}. This is not every URL on the site.`;
}

function channelState(channel: { state?: string } | undefined): string {
  return channel?.state || 'NOT_CONNECTED';
}

function hasSchema(ctx: AuditContext, name: string): boolean {
  const needle = name.toLowerCase();
  return ctx.pages.some((page) => (page.schema_types || []).some((type) => type.toLowerCase().includes(needle)));
}

function siteMatches(ctx: AuditContext, words: string[]): boolean {
  return words.some((word) => ctx.model.includes(word));
}

function specialist(
  ctx: AuditContext,
  matched: boolean,
  evidence: boolean,
  label: string,
): SectionResult {
  if (evidence) {
    return {
      status: 'MEASURED',
      summary: `The crawl found evidence of ${label}. The rest of that specialist checklist was not run.`,
      coverage: sampleLine(ctx),
    };
  }
  if (!ctx.model.trim()) {
    return {
      status: 'NOT_TESTED',
      summary: `Site type was not established, so ${label} was not selected.`,
      coverage: 'Module not selected',
    };
  }
  if (!matched) {
    return {
      status: 'NOT_APPLICABLE',
      summary: `Not selected. The business profile does not describe ${label}.`,
      coverage: 'Not applicable',
    };
  }
  return {
    status: 'NOT_TESTED',
    summary: `${label} fits this business profile, and that module did not run.`,
    coverage: 'Not tested',
  };
}

function fieldVitals(ctx: AuditContext): boolean {
  return ctx.pages.some((page) => page.field_performance?.has_field_data === true);
}

function sectionForFinding(finding: Finding): string {
  const text = `${finding.title || ''} ${finding.description || ''}`.toLowerCase();
  const category = finding.category;
  if (/core web vital|largest contentful paint|\blcp\b|\binp\b|cumulative layout shift|\bcls\b/.test(text)) return '16';
  if (/hreflang|multilingual/.test(text)) return '36';
  if (/google business profile|\bnap\b|local business/.test(text)) return '35';
  if (/backlink|referring domain/.test(text)) return '31';
  if (/robots\.txt|crawl trap|orphan page/.test(text)) return '07';
  if (/noindex|soft 404|not indexed/.test(text)) return '08';
  if (/canonical/.test(text)) return '10';
  if (/redirect loop|redirect chain|\b404\b|\b410\b/.test(text)) return '11';
  if (/sitemap/.test(text)) return '12';
  if (/anchor text|click here/.test(text)) return '27';
  if (/click depth|internal link/.test(text)) return '13';
  if (/hsts|security header|mixed content|certificate/.test(text)) return '18';
  if (/javascript|hydration|rendered dom|client-side/.test(text)) return '15';
  if (/viewport|tap target|interstitial/.test(text)) return '17';
  if (/schema|structured data|json-ld/.test(text)) return '19';
  if (/meta description|title tag|title length/.test(text)) return '20';
  if (/\bh1\b|heading/.test(text)) return '21';
  if (/cannibal|duplicate title|near-duplicate/.test(text)) return '26';
  if (/alt text|image alt/.test(text)) return '28';
  if (/videoobject|\bvideo\b/.test(text)) return '29';
  if (/cloaking|doorway|keyword stuffing|hidden text|link spam/.test(text)) return '37';
  if (/merchant center|faceted|out of stock|product schema/.test(text)) return '38';
  if (/http 5\d\d|5xx|\b500\b|\b502\b|\b503\b|\b504\b|server error|server reliability|ttfb|response latency|latency spike/.test(text)) return '14';
  if (category === 'GEO') return '46';
  if (category === 'AI_SEARCH') return '45';
  if (category === 'CONTENT') return '23';
  if (category === 'ON_PAGE_SEO') return '20';
  if (category === 'UX_CONVERSION') return '50';
  if (category === 'SCHEMA') return '19';
  if (category === 'TRUST_AUTHORITY') return '18';
  if (category === 'COMPETITIVE') return '33';
  if (category === 'EXTERNAL_AUTHORITY') return '31';
  if (category === 'TECHNICAL_SEO') return '53';
  return '53';
}

function baseResult(ctx: AuditContext, number: string): SectionResult {
  const report = ctx.report;
  const pages = ctx.pages;
  const crawled = pages.length > 0;
  const http = report.http_status_breakdown;
  const gsc = channelState(report.google_performance?.search_console);
  const ga4 = channelState(report.google_performance?.analytics);
  const analytics = report.google_performance?.analytics;
  const search = report.google_performance?.search_console;
  const card = report.ai_visibility_scorecard;
  const live = Boolean(card && (card.status === 'MEASURED' || card.measurement_kind === 'LIVE_MODEL_API') && card.successful_runs > 0);

  switch (number) {
    case '01': {
      const story = (report.story_summary || '').trim();
      if (!story && !crawled) {
        return { status: 'NOT_TESTED', summary: 'No executive narrative was stored because this run has no crawl.', coverage: 'Not tested' };
      }
      return {
        status: 'INFERRED',
        summary: story
          ? 'The executive narrative interprets this audit. It is not a separate measurement of traffic, revenue, or AI citations.'
          : 'Findings and crawl evidence are available. A narrative summary was not stored.',
        coverage: sampleLine(ctx),
      };
    }
    case '02': {
      const scores = Object.entries(report.scores?.category_scores || {})
        .filter((entry) => finite(entry[1]?.score) != null)
        .map(([key]) => key.replace(/_/g, ' ').toLowerCase());
      if (scores.length === 0) {
        return { status: 'NOT_TESTED', summary: 'No category score was sealed on this report.', coverage: 'Not scored' };
      }
      return {
        status: 'MEASURED',
        summary: `Category scores on this report: ${scores.join(', ')}. Local SEO, international SEO, backlinks, and Core Web Vitals are not given a score here unless that module measured them. This index does not add a blended 0–100 across those modules.`,
        coverage: 'Category ledger',
      };
    }
    case '03': {
      const profile = report.business_profile;
      if (!profile || !(profile.business_name || profile.business_model || profile.industry)) {
        return { status: 'NOT_TESTED', summary: 'No business profile was stored.', coverage: 'Not tested' };
      }
      const bits = [profile.business_model, profile.industry, profile.geography].filter(Boolean);
      return {
        status: 'INFERRED',
        summary: `Profile recorded from the audit: ${bits.join(' · ') || profile.business_name}. This is not a customer interview.`,
        coverage: 'Business profile',
      };
    }
    case '04': {
      const serious = ctx.findings.filter((finding) => finding.severity === 'CRITICAL' || finding.severity === 'HIGH');
      if (!crawled && serious.length === 0) {
        return { status: 'NOT_TESTED', summary: 'No crawl and no findings were stored.', coverage: 'Not tested' };
      }
      if (serious.length === 0) {
        return { status: 'NO_ISSUE', summary: `No critical or high finding was recorded. ${sampleLine(ctx)}`, coverage: sampleLine(ctx) };
      }
      return {
        status: 'ISSUE_VERIFIED',
        summary: `${serious.length} critical or high finding${serious.length === 1 ? '' : 's'} recorded. Lower-severity items stay in the register.`,
        coverage: sampleLine(ctx),
      };
    }
    case '05':
    case '33': {
      const bakeoff = report.competitor_bakeoff?.evaluations?.length || 0;
      const named = report.business_profile?.competitors?.filter(Boolean) || [];
      const gap = report.external_authority?.competitor_gap?.length || 0;
      if (bakeoff === 0 && named.length === 0 && gap === 0) {
        return {
          status: 'DATA_UNAVAILABLE',
          summary: 'No competitor was measured. An uncrawled rival is left blank. Keyword and backlink gaps require the same provider on both domains.',
          coverage: 'Not measured',
        };
      }
      return {
        status: 'MEASURED',
        summary: `${named.length} named competitor${named.length === 1 ? '' : 's'}. ${bakeoff} bake-off row${bakeoff === 1 ? '' : 's'}. ${gap} authority gap statement${gap === 1 ? '' : 's'}. Gaps are included only when the same provider measured both sides.`,
        coverage: 'Measured competitors only',
      };
    }
    case '06': {
      const items = (report.roadmap_7_days?.length || 0) + (report.roadmap_30_days?.length || 0) + (report.roadmap_90_days?.length || 0);
      if (items === 0) {
        return { status: 'NOT_TESTED', summary: 'No roadmap items were stored.', coverage: 'Not stored' };
      }
      return {
        status: 'INFERRED',
        summary: `${items} roadmap item${items === 1 ? '' : 's'} stored across 7, 30, and 90 days. Effort and impact are planning notes, not measured outcomes.`,
        coverage: 'Roadmap',
      };
    }
    case '07': {
      if (!crawled && !report.crawl_manifest) {
        return { status: 'NOT_TESTED', summary: 'No crawl was stored.', coverage: 'Not tested' };
      }
      const robots = report.crawl_manifest?.robots_txt_found;
      const sitemap = report.crawl_manifest?.sitemap_found;
      return {
        status: 'MEASURED',
        summary: `Robots.txt ${robots ? 'was found' : 'was not found in the crawl record'}. Sitemap ${sitemap ? 'was found' : 'was not found in the crawl record'}. ${sampleLine(ctx)}`,
        coverage: sampleLine(ctx),
      };
    }
    case '08': {
      const rollup = report.indexation_intelligence || report.crawl_manifest?.indexation_rollup;
      if (!rollup) {
        return crawled
          ? { status: 'NOT_TESTED', summary: `Pages were crawled. An indexation classification was not stored. ${sampleLine(ctx)}`, coverage: sampleLine(ctx) }
          : { status: 'NOT_TESTED', summary: 'Indexation was not classified.', coverage: 'Not tested' };
      }
      const total = finite((rollup as { total_pages_evaluated?: number }).total_pages_evaluated)
        ?? finite((rollup as { total_pages_audited?: number }).total_pages_audited)
        ?? 0;
      const indexable = finite(rollup.indexable_count);
      return {
        status: 'MEASURED',
        summary: indexable == null
          ? 'An indexation rollup was stored.'
          : `${indexable} of ${total} classified URL${total === 1 ? '' : 's'} marked indexable. Search Console coverage is separate and only appears when a coverage state was stored.`,
        coverage: sampleLine(ctx),
      };
    }
    case '09': {
      if (!crawled) return { status: 'NOT_TESTED', summary: 'No URLs were crawled.', coverage: 'Not tested' };
      const https = pages.filter((page) => page.url.startsWith('https://')).length;
      const withQuery = pages.filter((page) => page.url.includes('?')).length;
      return {
        status: 'MEASURED',
        summary: `${https} of ${pages.length} crawled URL${pages.length === 1 ? '' : 's'} use HTTPS. ${withQuery} include a query string. Host, slash, and case variants were not probed unless a redirect audit stored them.`,
        coverage: sampleLine(ctx),
      };
    }
    case '10': {
      if (report.canonical_audit) {
        return { status: 'MEASURED', summary: 'A canonical audit was stored for this run.', coverage: sampleLine(ctx) };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Canonicals were not checked.', coverage: 'Not tested' };
      const declared = pages.filter((page) => (page.canonical_url || '').trim()).length;
      return {
        status: 'MEASURED',
        summary: `${declared} of ${pages.length} crawled pages declare a canonical. Chains, loops, and cross-domain targets were not tested unless a canonical audit stored them.`,
        coverage: sampleLine(ctx),
      };
    }
    case '11': {
      if (report.host_and_redirects) {
        return { status: 'MEASURED', summary: report.host_and_redirects.summary || 'Host and redirect probes were stored.', coverage: 'Host probe' };
      }
      const redirects = finite(http?.count_3xx);
      if (redirects == null && !crawled) return { status: 'NOT_TESTED', summary: 'Redirects were not inventoried.', coverage: 'Not tested' };
      return {
        status: 'MEASURED',
        summary: redirects != null
          ? `${redirects} redirect response${redirects === 1 ? '' : 's'} in the HTTP breakdown. Chains and loops are included only when the redirect audit stored them.`
          : 'Crawled status codes are available. A redirect-chain audit was not stored.',
        coverage: sampleLine(ctx),
      };
    }
    case '12': {
      if (!report.crawl_manifest) return { status: 'NOT_TESTED', summary: 'No crawl record was stored.', coverage: 'Not tested' };
      return {
        status: 'MEASURED',
        summary: report.crawl_manifest.sitemap_found
          ? `A sitemap URL was recorded${report.crawl_manifest.sitemap_url ? `: ${report.crawl_manifest.sitemap_url}` : ''}. Syntax, lastmod, and index coverage of every sitemap URL were not fully validated unless those fetches were stored.`
          : 'No sitemap was recorded on this crawl. Image, video, and news sitemaps were not separately validated.',
        coverage: 'Crawl record',
      };
    }
    case '13': {
      if (report.click_depth && report.click_depth.total_pages_analyzed > 0) {
        return {
          status: 'MEASURED',
          summary: `Click depth was calculated for ${report.click_depth.total_pages_analyzed} URLs. Maximum depth ${report.click_depth.max_click_depth}. The homepage is depth 1.`,
          coverage: sampleLine(ctx),
        };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Internal architecture was not measured.', coverage: 'Not tested' };
      return { status: 'NOT_TESTED', summary: `Pages were crawled. A click-depth graph was not stored. ${sampleLine(ctx)}`, coverage: sampleLine(ctx) };
    }
    case '14': {
      if (http && http.total_urls_checked > 0) {
        const bad = (http.count_4xx || 0) + (http.count_5xx || 0);
        return {
          status: bad > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
          summary: `${http.count_2xx || 0} 2xx, ${http.count_3xx || 0} 3xx, ${http.count_4xx || 0} 4xx, ${http.count_5xx || 0} 5xx. CDN and cache policy were not graded.`,
          coverage: `${http.total_urls_checked} URLs in the HTTP breakdown`,
        };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'No HTTP breakdown was stored.', coverage: 'Not tested' };
      return { status: 'MEASURED', summary: `Status codes were stored on crawled pages. ${sampleLine(ctx)}`, coverage: sampleLine(ctx) };
    }
    case '15': {
      const compared = (report.indexation_intelligence?.pages || []).filter((page) => page.render_delta).length;
      if (compared > 0) {
        return { status: 'MEASURED', summary: `A rendered-versus-raw comparison was stored for ${compared} URL${compared === 1 ? '' : 's'}.`, coverage: sampleLine(ctx) };
      }
      return {
        status: 'NOT_TESTED',
        summary: crawled
          ? 'Pages were fetched. A raw-HTML versus rendered-DOM comparison was not stored, so JavaScript-only content was not measured.'
          : 'Rendering was not compared.',
        coverage: 'Not tested',
      };
    }
    case '16': {
      if (fieldVitals(ctx)) {
        return { status: 'MEASURED', summary: 'Field Core Web Vitals were stored on at least one crawled page. Thresholds are LCP 2.5s, INP 200ms, and CLS 0.1 at the 75th percentile.', coverage: 'Field data' };
      }
      const lab = pages.some((page) => Boolean((page.lab_performance as { lighthouse_audit_version?: string } | undefined)?.lighthouse_audit_version));
      if (lab) {
        return { status: 'MEASURED', summary: 'A lab performance record was stored. It is not field Core Web Vitals and it is not a Google certification.', coverage: 'Lab data' };
      }
      return {
        status: 'NOT_TESTED',
        summary: crawled
          ? 'Crawl time to first byte may be shown elsewhere. LCP, INP, and CLS were not measured. Lab timing is not a substitute for field data.'
          : 'Core Web Vitals were not measured.',
        coverage: 'Not measured',
      };
    }
    case '17': {
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Mobile rendering was not checked.', coverage: 'Not tested' };
      const missing = pages.filter((page) => !(page.viewport || '').trim()).length;
      return {
        status: missing > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
        summary: missing > 0
          ? `${missing} crawled page${missing === 1 ? '' : 's'} have no viewport tag. Tap targets, interstitials, and mobile-desktop parity were not tested.`
          : `Every crawled page has a viewport tag. ${sampleLine(ctx)} Other mobile behavior was not tested.`,
        coverage: sampleLine(ctx),
      };
    }
    case '18': {
      if (!crawled) return { status: 'NOT_TESTED', summary: 'HTTPS and response headers were not checked.', coverage: 'Not tested' };
      const insecure = pages.filter((page) => page.url.startsWith('http://')).length;
      return {
        status: insecure > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
        summary: insecure > 0
          ? `${insecure} crawled URL${insecure === 1 ? '' : 's'} use HTTP. Header presence is a baseline, not a penetration test. A missing header is not reported as an SEO, conversion, or citation failure.`
          : `Crawled URLs use HTTPS. ${sampleLine(ctx)} Malware, injection, and certificate monitoring were not certified.`,
        coverage: sampleLine(ctx),
      };
    }
    case '19': {
      const schema = report.schema_validation;
      if (schema) {
        const errors = schema.entities_with_errors_count || 0;
        return {
          status: errors > 0 ? 'ISSUE_VERIFIED' : 'MEASURED',
          summary: `${schema.total_pages_with_schema} crawled pages with schema. ${schema.detected_types?.length || 0} types. ${errors} entities with errors. Valid syntax is not a rich result.`,
          coverage: sampleLine(ctx),
        };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Structured data was not read.', coverage: 'Not tested' };
      const types = new Set(pages.flatMap((page) => page.schema_types || []));
      return {
        status: 'MEASURED',
        summary: types.size > 0
          ? `Schema types in the sample: ${Array.from(types).slice(0, 8).join(', ')}. A full validator did not run. Syntax is not a rich result.`
          : 'No schema type was found on the crawled pages. A full validator did not run.',
        coverage: sampleLine(ctx),
      };
    }
    case '20': {
      const meta = report.meta_rollup;
      if (meta && meta.total_pages_evaluated > 0) {
        const issues = (meta.missing_titles?.length || 0) + (meta.duplicate_titles?.length || 0) + (meta.missing_descriptions?.length || 0);
        return {
          status: issues > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
          summary: `${meta.missing_titles?.length || 0} missing titles, ${meta.duplicate_titles?.length || 0} duplicate titles, ${meta.missing_descriptions?.length || 0} missing descriptions in the evaluated sample.`,
          coverage: `${meta.total_pages_evaluated} pages evaluated`,
        };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Titles and descriptions were not read.', coverage: 'Not tested' };
      const missingTitles = pages.filter((page) => !(page.title || '').trim()).length;
      const missingMeta = pages.filter((page) => !(page.meta_description || '').trim()).length;
      return {
        status: missingTitles + missingMeta > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
        summary: `${missingTitles} crawled pages lack a title. ${missingMeta} lack a meta description. Search-result rewrites were not measured.`,
        coverage: sampleLine(ctx),
      };
    }
    case '21': {
      if (report.heading_hierarchy && report.heading_hierarchy.total_pages_evaluated > 0) {
        const issues = report.heading_hierarchy.total_heading_issues || 0;
        return {
          status: issues > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
          summary: `${issues} heading issue${issues === 1 ? '' : 's'} in the heading rollup.`,
          coverage: `${report.heading_hierarchy.total_pages_evaluated} pages evaluated`,
        };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Headings were not read.', coverage: 'Not tested' };
      const missing = pages.filter((page) => !(page.h1 || []).some((item) => item.trim())).length;
      return {
        status: missing > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
        summary: `${missing} crawled pages have no H1. Hierarchy skips were not judged unless a heading rollup was stored.`,
        coverage: sampleLine(ctx),
      };
    }
    case '22':
    case '34':
    case '48':
    case 'E':
    case 'J': {
      if (gsc !== 'MEASURED') {
        return {
          status: 'DATA_UNAVAILABLE',
          summary: `Search Console is ${gsc.replace(/_/g, ' ').toLowerCase()}. Query, click, and position advice is skipped. Zeros are not shown for a disconnected property.`,
          coverage: gsc,
        };
      }
      const queries = search?.queries?.length || 0;
      return {
        status: 'MEASURED',
        summary: `Search Console measured${search?.property ? ` for ${search.property}` : ''}${search?.period ? ` (${search.period})` : ''}. ${queries} query row${queries === 1 ? '' : 's'} stored. Clicks ${finite(search?.clicks) ?? 'not stored'}. This is not a keyword-difficulty study.`,
        coverage: 'Google Search Console',
      };
    }
    case '23': {
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Page text was not extracted.', coverage: 'Not tested' };
      const words = pages.map((page) => finite(page.word_count)).filter((value): value is number => value != null && value > 0);
      if (words.length === 0) {
        return { status: 'NOT_TESTED', summary: 'No extractable word count was stored. Content quality was not judged from an empty extract.', coverage: sampleLine(ctx) };
      }
      const thin = words.filter((value) => value < 250).length;
      return {
        status: thin > 0 ? 'ISSUE_VERIFIED' : 'MEASURED',
        summary: `${thin} crawled page${thin === 1 ? '' : 's'} under 250 extracted words. Expertise, citations, and editorial review were not certified.`,
        coverage: sampleLine(ctx),
      };
    }
    case '24':
    case '45': {
      const questions = report.geo_readiness?.questions || [];
      if (questions.length === 0) {
        return { status: 'NOT_TESTED', summary: 'No on-page question assessment was stored. This is not a live answer-engine measurement.', coverage: 'Not tested' };
      }
      return {
        status: 'MEASURED',
        summary: `${questions.length} on-page buyer questions assessed. Supported ${report.geo_readiness?.questions_supported ?? 'not stored'}. This is answerability of the crawled pages, not a live citation.`,
        coverage: sampleLine(ctx),
      };
    }
    case '25': {
      const topical = report.topical_authority;
      if (!topical) return { status: 'NOT_TESTED', summary: 'The topical module did not run. No topical authority score is shown.', coverage: 'Not tested' };
      return {
        status: topical.status === 'PASS' ? 'NO_ISSUE' : 'INFERRED',
        summary: `${topical.summary || topical.status} This reading is limited to the crawled sample and is not a ranking.`,
        coverage: sampleLine(ctx),
      };
    }
    case '26': {
      const duplicateTitles = report.meta_rollup?.duplicate_titles?.length || 0;
      if (!crawled && duplicateTitles === 0 && gsc !== 'MEASURED') {
        return { status: 'NOT_TESTED', summary: 'Duplication and query cannibalization were not tested.', coverage: 'Not tested' };
      }
      return {
        status: duplicateTitles > 0 ? 'ISSUE_VERIFIED' : 'MEASURED',
        summary: `${duplicateTitles} duplicate title${duplicateTitles === 1 ? '' : 's'} in the sample. The same query on more than one URL is reported only when Search Console shows it. Search Console is ${gsc.replace(/_/g, ' ').toLowerCase()}.`,
        coverage: sampleLine(ctx),
      };
    }
    case '27': {
      if (report.anchor_text_audit && report.anchor_text_audit.total_links_analyzed > 0) {
        return {
          status: report.anchor_text_audit.generic_anchor_count > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
          summary: `${report.anchor_text_audit.generic_anchor_count} generic anchors in ${report.anchor_text_audit.total_links_analyzed} analyzed links.`,
          coverage: sampleLine(ctx),
        };
      }
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Internal links were not counted.', coverage: 'Not tested' };
      return { status: 'MEASURED', summary: 'Internal link fields exist on crawled pages. Anchor quality was not classified.', coverage: sampleLine(ctx) };
    }
    case '28': {
      if (!crawled) return { status: 'NOT_TESTED', summary: 'Images were not counted.', coverage: 'Not tested' };
      let total = 0;
      let missing = 0;
      for (const page of pages) {
        const images = finite(page.total_images);
        const without = finite(page.images_without_alt);
        if (images == null || images < 0 || without == null || without < 0 || without > images) continue;
        total += images;
        missing += without;
      }
      if (total === 0) return { status: 'NOT_TESTED', summary: 'No image count was stored on the crawled pages.', coverage: sampleLine(ctx) };
      return {
        status: missing > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
        summary: `${missing} of ${total} images are missing alt text. File names, formats, and image sitemaps were not fully audited.`,
        coverage: sampleLine(ctx),
      };
    }
    case '29': {
      if (hasSchema(ctx, 'video')) {
        return { status: 'MEASURED', summary: 'VideoObject schema appears in the crawled sample. Transcripts, video sitemaps, and watch-page indexing were not tested.', coverage: sampleLine(ctx) };
      }
      return {
        status: 'NOT_TESTED',
        summary: crawled
          ? 'No VideoObject schema was found in the crawled sample. A video-search audit was not run.'
          : 'Video SEO was not tested.',
        coverage: 'Not tested',
      };
    }
    case '30':
      return { status: 'NOT_TESTED', summary: 'Editorial ownership, calendars, and review workflow are not visible to this crawl.', coverage: 'Outside the crawl' };
    case '31':
    case 'G': {
      const authority = report.external_authority;
      const backlinks = authority?.sections?.backlink_profile;
      const connected = authority?.coverage?.some((row) => row.data_state === 'MEASURED' || row.connection_status === 'CONNECTED');
      if (!backlinks && !connected) {
        return { status: 'DATA_UNAVAILABLE', summary: 'No backlink provider was connected. Missing authority data is not a zero and not an SEO failure.', coverage: 'Not connected' };
      }
      return { status: 'MEASURED', summary: 'Backlink fields come from the connected provider named on the authority report. They are not Google ranking metrics.', coverage: 'Named provider' };
    }
    case '32': {
      const mentions = report.external_authority?.sections?.brand_mentions;
      if (!mentions) return { status: 'DATA_UNAVAILABLE', summary: 'Brand mentions and digital PR were not measured. They are not inferred from the crawled HTML.', coverage: 'Not connected' };
      return { status: 'MEASURED', summary: 'A brand-mention source was stored. Sentiment is included only when that source reported it.', coverage: 'Named provider' };
    }
    case '35': {
      const local = report.local_seo;
      if (local?.status === 'NOT_APPLICABLE') {
        return { status: 'NOT_APPLICABLE', summary: local.summary || 'The local module marked this site not applicable.', coverage: 'Not applicable' };
      }
      if (local) {
        const conflicts = (local.phone_conflicts?.length || 0) + (local.address_conflicts?.length || 0);
        return {
          status: conflicts > 0 || local.status === 'NEEDS_ATTENTION' || local.status === 'FAILED' ? 'ISSUE_VERIFIED' : 'MEASURED',
          summary: local.summary || `Local module status ${local.status}. ${conflicts} NAP conflict group${conflicts === 1 ? '' : 's'}. Map-pack rank was not invented.`,
          coverage: sampleLine(ctx),
        };
      }
      return specialist(ctx, siteMatches(ctx, ['local', 'clinic', 'restaurant', 'dentist', 'storefront', 'multi-location']), hasSchema(ctx, 'localbusiness'), 'a local business');
    }
    case '36': {
      const intl = report.international_seo;
      if (intl?.status === 'NOT_APPLICABLE') {
        return { status: 'NOT_APPLICABLE', summary: intl.summary || 'The international module marked this site not applicable.', coverage: 'Not applicable' };
      }
      if (intl) {
        const issues = intl.issues?.length || 0;
        return {
          status: issues > 0 || intl.status === 'FAILED' || intl.status === 'WARNING' ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
          summary: intl.summary || `${intl.total_pages_with_hreflang} pages with hreflang. ${issues} issue${issues === 1 ? '' : 's'}.`,
          coverage: sampleLine(ctx),
        };
      }
      const tagged = pages.filter((page) => page.hreflang_tags && Object.keys(page.hreflang_tags).length > 0).length;
      if (tagged > 0) {
        return { status: 'MEASURED', summary: `${tagged} crawled pages declare hreflang. Return tags and x-default were not validated by the international module.`, coverage: sampleLine(ctx) };
      }
      return specialist(ctx, siteMatches(ctx, ['international', 'multilingual', 'multi-country']), false, 'an international or multilingual site');
    }
    case '37':
      return {
        status: 'NOT_TESTED',
        summary: 'Spam and policy checks were not confirmed. A pattern finding is a review item, not a declared manual action. Search Essentials remain the baseline.',
        coverage: 'Not a compliance certification',
      };
    case '38':
      return specialist(ctx, siteMatches(ctx, ['ecommerce', 'e-commerce', 'retail', 'shop', 'catalog']), hasSchema(ctx, 'product'), 'an e-commerce catalog');
    case '39':
      return specialist(ctx, siteMatches(ctx, ['news', 'publisher', 'magazine', 'journal']), hasSchema(ctx, 'newsarticle'), 'a news publisher');
    case '40': {
      const discovered = finite(report.crawl_manifest?.total_pages_discovered) || 0;
      if (discovered >= 200) {
        return { status: 'NOT_TESTED', summary: `${discovered} URLs were discovered and ${pages.length} were crawled. A programmatic template audit was not run, so unfetched URLs are not judged.`, coverage: sampleLine(ctx) };
      }
      return { status: 'NOT_APPLICABLE', summary: 'No large generated URL space was discovered, so programmatic SEO was not selected.', coverage: 'Not applicable' };
    }
    case '41': {
      const fits = siteMatches(ctx, ['saas', 'b2b', 'software', 'lead gen', 'lead-gen', 'subscription']);
      if (!ctx.model.trim()) {
        return { status: 'NOT_TESTED', summary: 'Site type was not established, so SaaS and lead-generation SEO was not selected.', coverage: 'Module not selected' };
      }
      if (!fits) {
        return { status: 'NOT_APPLICABLE', summary: 'Not selected. The business profile does not describe a SaaS or lead-generation business.', coverage: 'Not applicable' };
      }
      if (!crawled) {
        return { status: 'NOT_TESTED', summary: 'The profile fits SaaS or lead generation, and no pages were crawled.', coverage: 'Not tested' };
      }
      return {
        status: 'MEASURED',
        summary: `The business profile matches SaaS or lead generation. ${sampleLine(ctx)} CRM pipeline and qualified leads were not measured.`,
        coverage: sampleLine(ctx),
      };
    }
    case '42': {
      const appLink = pages.some((page) => /apps\.apple\.com|play\.google\.com/.test(page.url) || (page.external_links || []).some((link) => /apps\.apple\.com|play\.google\.com/.test(link)));
      if (appLink) return { status: 'NOT_TESTED', summary: 'An app-store link was seen. Store listing text, ratings, and install measurement were not audited.', coverage: 'Not tested' };
      return { status: 'NOT_APPLICABLE', summary: 'No mobile-app listing was in scope.', coverage: 'Not applicable' };
    }
    case '43': {
      const wcag = report.wcag_audit;
      if (!wcag || !(wcag.total_checks_performed > 0)) {
        return { status: 'NOT_TESTED', summary: 'No automated accessibility screen was stored. This audit does not issue a WCAG certification.', coverage: 'Not tested' };
      }
      return {
        status: wcag.violations_count > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
        summary: `${wcag.violations_count} automated violation${wcag.violations_count === 1 ? '' : 's'} in ${wcag.total_checks_performed} checks. This is an automated screen, not a WCAG certification and not a ranking score.`,
        coverage: sampleLine(ctx),
      };
    }
    case '44':
      return { status: 'NOT_TESTED', summary: 'Voice, visual, and multimodal queries were not run.', coverage: 'Not queried' };
    case '46': {
      const extractability = finite(report.geo_readiness?.extractability_score);
      if (extractability == null && !crawled) {
        return { status: 'NOT_TESTED', summary: 'On-page extractability was not scored. It would not be a live citation rate.', coverage: 'Not tested' };
      }
      return {
        status: 'MEASURED',
        summary: extractability == null
          ? 'Crawl evidence exists. A separate extractability score was not stored. Live citations are a different section.'
          : `On-page extractability is ${extractability}. This is not a ChatGPT, Perplexity, or AI Overview citation rate.`,
        coverage: sampleLine(ctx),
      };
    }
    case '47':
    case 'K': {
      if (!live || !card) {
        return {
          status: 'NOT_TESTED',
          summary: 'Live engine responses were not measured. On-page extractability is not AI visibility. Google AI Overviews, Google AI Mode, and Bing Copilot were not queried.',
          coverage: 'Not a live query',
        };
      }
      const engines = card.engines_queried?.length ? card.engines_queried.join(', ') : `${card.engines_measured} engines`;
      const missing = card.surfaces_not_queried?.length
        ? card.surfaces_not_queried
        : ['Google AI Overviews', 'Google AI Mode', 'Bing Copilot'];
      const rates = [
        finite(card.mention_rate_pct) != null ? `mention rate ${card.mention_rate_pct}%` : '',
        finite(card.citation_rate_pct) != null ? `citation rate ${card.citation_rate_pct}%` : '',
        finite(card.competitor_visibility_pct) != null ? `competitor visibility ${card.competitor_visibility_pct}%` : '',
      ].filter(Boolean);
      return {
        status: 'MEASURED',
        summary: `Live model-API run for ${engines}. ${rates.join('; ') || 'Rates were not stored.'} Not queried: ${missing.join(', ')}. Model APIs are not those products. Citation accuracy was not span-checked.`,
        coverage: `${card.successful_runs} successful responses · ${card.queries} prompts · ${card.repeats} repeats`,
      };
    }
    case '49': {
      if (ga4 !== 'MEASURED') {
        return { status: 'DATA_UNAVAILABLE', summary: `Google Analytics 4 is ${ga4.replace(/_/g, ' ').toLowerCase()}. Sessions are not filled with an estimate.`, coverage: ga4 };
      }
      const landing = analytics?.landing_pages?.length || 0;
      return {
        status: 'MEASURED',
        summary: `GA4 measured${analytics?.property ? ` for ${analytics.property}` : ''}. Sessions ${finite(analytics?.sessions) ?? 'not stored'}. ${landing} landing page row${landing === 1 ? '' : 's'}.`,
        coverage: 'Google Analytics 4',
      };
    }
    case '50': {
      const sessions = finite(analytics?.sessions);
      const events = finite(analytics?.key_events);
      const landing = analytics?.landing_pages?.length || 0;
      if (ga4 === 'MEASURED' && sessions != null && sessions > 0 && events != null && landing > 0) {
        const rate = Math.round((events / sessions) * 1000) / 10;
        return {
          status: 'MEASURED',
          summary: `GA4 key-event rate is ${rate}% (${events} key events / ${sessions} sessions). This is not a 0–100 conversion grade.`,
          coverage: 'Google Analytics 4',
        };
      }
      if (!crawled) {
        return { status: 'DATA_UNAVAILABLE', summary: 'No crawl and no GA4 key-event rate. Conversion is not given a fallback score.', coverage: 'Not measured' };
      }
      return {
        status: 'INFERRED',
        summary: 'Heuristic notes come from the crawled pages. No conversion rate is shown because GA4 landing pages and key events were not both measured.',
        coverage: sampleLine(ctx),
      };
    }
    case '51': {
      const events = finite(analytics?.key_events);
      const sessions = finite(analytics?.sessions);
      if (ga4 === 'MEASURED' && events != null) {
        return {
          status: 'DATA_UNAVAILABLE',
          summary: `GA4 recorded ${events} key events${sessions != null ? ` and ${sessions} sessions` : ''}. Currency revenue, pipeline, and acquisition cost were not measured. Key events are not revenue.`,
          coverage: 'Revenue not measured',
        };
      }
      return { status: 'DATA_UNAVAILABLE', summary: 'Organic revenue was not measured. No revenue figure is shown.', coverage: 'Not connected' };
    }
    case '52':
      return { status: 'NOT_TESTED', summary: 'No traffic, ranking, or revenue forecast is produced. Nothing in this audit is a promised gain.', coverage: 'Not estimated' };
    case '53':
    case 'D':
    case 'L': {
      const recorded = ctx.findings.filter((finding) => finding.confidence_rubric !== 'GUESSING');
      if (recorded.length === 0 && ctx.findings.length === 0) {
        return {
          status: crawled ? 'MEASURED' : 'NOT_TESTED',
          summary: crawled
            ? 'No finding was recorded for this sample. That is not a claim that every possible check passed.'
            : 'No finding register was stored.',
          coverage: sampleLine(ctx),
        };
      }
      return {
        status: recorded.length > 0 ? 'ISSUE_VERIFIED' : 'INFERRED',
        summary: `${recorded.length} finding${recorded.length === 1 ? '' : 's'} in the register. ${ctx.findings.length - recorded.length} guessing note${ctx.findings.length - recorded.length === 1 ? '' : 's'} are excluded from the measured defect count.`,
        coverage: 'Finding register',
      };
    }
    case '54': {
      const checks = ctx.findings.filter((finding) => finding.remediation_verification);
      if (checks.length === 0) return { status: 'NOT_TESTED', summary: 'No post-fix retest was stored. A recommended patch is not a completed verification.', coverage: 'Not retested' };
      return { status: 'MEASURED', summary: `${checks.length} finding${checks.length === 1 ? '' : 's'} have a stored verification record.`, coverage: 'Retest records' };
    }
    case '55':
    case 'M': {
      if (!report.regression_report) return { status: 'NOT_TESTED', summary: 'No earlier audit was compared. Ongoing monitoring is not claimed from this single run.', coverage: 'Not monitored' };
      return {
        status: report.regression_report.has_regression ? 'ISSUE_VERIFIED' : 'MEASURED',
        summary: report.regression_report.summary || 'A comparison with an earlier audit was stored.',
        coverage: 'Prior audit',
      };
    }
    case 'A':
    case 'N':
      return {
        status: 'MEASURED',
        summary: `${sampleLine(ctx)} Sections marked not tested or data unavailable were not given a zero. A representative sample is a limit of this audit, not a failed check.`,
        coverage: report.domain || 'This audit',
      };
    case 'B':
    case 'O':
      return {
        status: 'MEASURED',
        summary: 'Status labels are Not applicable, Not tested, Data unavailable, No issue in the checked sample, Issue verified, Inferred, and Measured. A missing connector is never a score of zero.',
        coverage: 'This report',
      };
    case 'C': {
      if (!crawled) return { status: 'NOT_TESTED', summary: 'No URL inventory was crawled.', coverage: 'Not tested' };
      return { status: 'MEASURED', summary: sampleLine(ctx), coverage: 'Crawled URLs' };
    }
    case 'F': {
      const named = report.business_profile?.competitors?.filter(Boolean) || [];
      if (named.length === 0) return { status: 'DATA_UNAVAILABLE', summary: 'No competitor inventory was stored.', coverage: 'Not measured' };
      return { status: 'MEASURED', summary: named.slice(0, 8).join(', '), coverage: 'Named on this audit' };
    }
    case 'H':
      return baseResult(ctx, '19');
    case 'I':
      return baseResult(ctx, '16');
    default:
      return { status: 'NOT_TESTED', summary: 'This module was not run.', coverage: 'Not tested' };
  }
}

function applyFindings(result: SectionResult, findings: Finding[]): Pick<ResolvedAuditSection, 'status' | 'summary' | 'findings' | 'findingCount'> {
  const verified = findings.filter((finding) => finding.confidence_rubric !== 'GUESSING');
  let status = result.status;
  let summary = result.summary;
  if (verified.length > 0 && (status === 'NOT_TESTED' || status === 'DATA_UNAVAILABLE' || status === 'NO_ISSUE' || status === 'NOT_APPLICABLE' || status === 'MEASURED')) {
    status = 'ISSUE_VERIFIED';
    summary = `${verified.length} recorded finding${verified.length === 1 ? '' : 's'}. ${result.summary}`;
  }
  return {
    status,
    summary,
    findingCount: findings.length,
    findings: findings.slice(0, 10).map(toFindingRef),
  };
}

export function resolveAuditIndex(report: ExecutiveReport): ResolvedAuditIndex {
  const ctx: AuditContext = {
    report,
    pages: report.crawl_manifest?.pages || [],
    findings: report.findings || [],
    model: `${report.business_profile?.business_model || ''} ${report.business_profile?.industry || ''} ${report.business_profile?.niche || ''}`.toLowerCase(),
  };
  const grouped = new Map<string, Finding[]>();
  for (const finding of ctx.findings) {
    const number = sectionForFinding(finding);
    grouped.set(number, [...(grouped.get(number) || []), finding]);
  }
  const counts = { ...EMPTY_COUNTS };
  const sections = AUDIT_SECTIONS.map((definition) => {
    const base = baseResult(ctx, definition.number);
    const sectionFindings = grouped.get(definition.number) || [];
    const withFindings = applyFindings(base, sectionFindings);
    const assignedChecks = assignFindingsToChecks(sectionFindings, definition.checks);
    const auditedChecks = definition.checks.map((check) =>
      evaluateAuditCheck(ctx, definition.number, check, assignedChecks.get(check) || [])
    );
    const analysis = buildSectionAnalysis(
      ctx,
      definition.number,
      withFindings.status,
      withFindings.summary,
      sectionFindings
    );
    counts[withFindings.status] += 1;
    return { ...definition, ...base, ...withFindings, auditedChecks, analysis };
  });
  return {
    sampleNotice: sampleLine(ctx),
    sections,
    counts,
  };
}

export const STATUS_LABEL: Record<SectionStatus, string> = {
  NOT_APPLICABLE: 'Not applicable',
  NOT_TESTED: 'Not tested',
  DATA_UNAVAILABLE: 'Data unavailable',
  NO_ISSUE: 'No issue in the checked sample',
  ISSUE_VERIFIED: 'Issue verified',
  INFERRED: 'Inferred',
  MEASURED: 'Measured',
};
