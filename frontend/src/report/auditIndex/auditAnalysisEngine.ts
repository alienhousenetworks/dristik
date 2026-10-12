import { ExecutiveReport, Finding, PageEvidence } from '../../types';
import { AuditedCheck, AuditFindingRef, SectionAnalysis, SectionStatus } from './types';

export interface AuditContext {
  report: ExecutiveReport;
  pages: PageEvidence[];
  findings: Finding[];
  model: string;
}

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function tokens(text: string): Set<string> {
  const words = text.toLowerCase().match(/[a-z0-9_]{3,}/g) || [];
  return new Set(words);
}

function scopeLabel(finding: Finding): string {
  if (finding.confidence_rubric === 'GUESSING') return 'Guessing — not a measured defect';
  return finding.evidence_scope || 'URL not attached';
}

export function toFindingRef(finding: Finding): AuditFindingRef {
  return {
    id: finding.finding_id,
    severity: finding.severity,
    title: finding.title,
    scope: scopeLabel(finding),
    description: finding.description,
    action: finding.recommendation,
    priority: finding.priority,
  };
}

export function assignFindingsToChecks(
  findings: Finding[],
  checks: string[]
): Map<string, Finding[]> {
  const assigned = new Map<string, Finding[]>();
  for (const check of checks) {
    assigned.set(check, []);
  }

  for (const finding of findings) {
    const fText = `${finding.title || ''} ${finding.description || ''} ${finding.finding_id || ''}`.toLowerCase();
    const fTokens = tokens(fText);
    let bestCheck = checks[0] || '';
    let bestScore = -1;

    for (const check of checks) {
      const cLower = check.toLowerCase();
      const cTokens = tokens(cLower);
      let score = 0;
      for (const t of fTokens) {
        if (cTokens.has(t)) score += 1;
      }

      if (/robots\.txt/.test(fText) && /robots\.txt/.test(cLower)) score += 5;
      if (/sitemap/.test(fText) && /sitemap/.test(cLower)) score += 5;
      if (/canonical/.test(fText) && /canonical/.test(cLower)) score += 5;
      if (/redirect|301|302/.test(fText) && /redirect/.test(cLower)) score += 5;
      if (/status|404|500/.test(fText) && /response|status/.test(cLower)) score += 4;
      if (/schema|json-ld|entity/.test(fText) && /schema|structured/.test(cLower)) score += 5;
      if (/title/.test(fText) && /title/.test(cLower)) score += 5;
      if (/h1|heading/.test(fText) && /h1|heading/.test(cLower)) score += 5;
      if (/image|alt/.test(fText) && /image|alt/.test(cLower)) score += 5;
      if (/lcp|inp|cls|vitals/.test(fText) && /lcp|inp|cls|vitals|performance/.test(cLower)) score += 5;
      if (/viewport|mobile/.test(fText) && /viewport|mobile|responsive/.test(cLower)) score += 5;
      if (/security|hsts|csp|https/.test(fText) && /security|https|header/.test(cLower)) score += 5;
      if (/thin|word count/.test(fText) && /thin|quality|completeness/.test(cLower)) score += 4;

      if (score > bestScore) {
        bestScore = score;
        bestCheck = check;
      }
    }

    if (bestCheck && assigned.has(bestCheck)) {
      assigned.get(bestCheck)!.push(finding);
    }
  }

  return assigned;
}

export function evaluateAuditCheck(
  ctx: AuditContext,
  sectionNumber: string,
  label: string,
  matchedFindings: Finding[]
): AuditedCheck {
  const verifiedDefects = matchedFindings.filter((finding) => finding.confidence_rubric !== 'GUESSING');
  if (verifiedDefects.length > 0) {
    const top = verifiedDefects[0];
    const fix = top.recommendation && !/implement recommended architectural fix/i.test(top.recommendation)
      ? top.recommendation
      : '';
    return {
      label,
      status: 'ISSUE_VERIFIED',
      result: `${top.title}${fix ? ` Fix: ${fix}` : ''}`,
      findings: verifiedDefects.map(toFindingRef),
    };
  }

  const pages = ctx.pages;
  const crawled = pages.length > 0;
  const report = ctx.report;
  const manifest = report.crawl_manifest;
  const text = label.toLowerCase();
  const checked = crawled
    ? `Checked on ${pages.length} crawled page${pages.length === 1 ? '' : 's'}. This is not every URL on the site.`
    : 'No page was crawled.';

  const line = (status: SectionStatus, result: string): AuditedCheck => ({ label, status, result });
  const untouched = (result: string, status: SectionStatus = 'NOT_TESTED') => line(status, result);

  if (sectionNumber === '52') {
    return untouched('No traffic, ranking, or revenue forecast is produced. Nothing in this audit is a promised gain.');
  }
  if (sectionNumber === '22' || sectionNumber === '34' || sectionNumber === '48' || sectionNumber === 'J') {
    const state = report.google_performance?.search_console?.state || 'NOT_CONNECTED';
    return untouched(`Search Console is ${state}. Clicks and impressions are not filled with zero.`, 'DATA_UNAVAILABLE');
  }
  if (sectionNumber === '49' || sectionNumber === '51') {
    const state = report.google_performance?.analytics?.state || 'NOT_CONNECTED';
    return untouched(`Google Analytics 4 is ${state}. Key events are not revenue, and a missing connector is not zero.`, 'DATA_UNAVAILABLE');
  }
  if (sectionNumber === '31' || sectionNumber === 'G') {
    return untouched('No backlink provider was connected. A missing provider is not a zero and not a toxicity score.', 'DATA_UNAVAILABLE');
  }
  if (sectionNumber === '47' || sectionNumber === 'K') {
    const card = report.ai_visibility_scorecard;
    const runs = finite(card?.successful_runs) ?? 0;
    if (!card || runs <= 0) {
      return untouched('Live engine responses were not measured. Google AI Overviews, Google AI Mode, and Bing Copilot were not queried. An SEO score is not a citation rate.');
    }
    const rates = [
      finite(card.mention_rate_pct) != null ? `mention rate ${card.mention_rate_pct}%` : 'mention rate was not stored',
      finite(card.citation_rate_pct) != null ? `citation rate ${card.citation_rate_pct}%` : 'citation rate was not stored',
    ];
    return line('MEASURED', `Live model-API responses: ${runs}. ${rates.join('. ')}. A mention is not a recommendation. A missing rate is not zero.`);
  }
  if (sectionNumber === '45') {
    const questions = report.dynamic_sandbox_evaluations;
    if (!questions) {
      return untouched('Buyer questions were not stored. A completed evaluation would not by itself be an answered question.');
    }
    return line('MEASURED', `${questions.length} stored question evaluation(s). A completed evaluation is not an answered question.`);
  }
  if (sectionNumber === '46') {
    const score = finite(report.geo_readiness?.extractability_score);
    if (score == null) {
      return untouched('On-page extractability was not stored. It would not be a live citation rate.');
    }
    return line('MEASURED', `On-page extractability is ${score}. This is not a citation rate.`);
  }
  if (sectionNumber === '43') {
    const wcag = report.wcag_audit;
    if (!wcag || !(wcag.total_checks_performed > 0)) {
      return untouched('No automated accessibility screen was stored. This is not a WCAG certification.');
    }
    return line(
      wcag.violations_count > 0 ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
      `${wcag.violations_count} automated violation(s) in ${wcag.total_checks_performed} checks. This is an automated screen, not a WCAG certification.`,
    );
  }
  if (sectionNumber === '16' || sectionNumber === 'I') {
    const fieldPage = pages.find((page) => page.field_performance?.has_field_data === true);
    const labPage = pages.find((page) => {
      const lab = page.lab_performance as { lighthouse_audit_version?: string } | undefined;
      return Boolean(lab?.lighthouse_audit_version);
    });
    if (fieldPage?.field_performance) {
      const field = fieldPage.field_performance;
      return line('MEASURED', `Field p75 on ${fieldPage.url}: LCP ${field.p75_lcp_ms ?? 'not stored'} ms, INP ${field.p75_inp_ms ?? 'not stored'} ms, CLS ${field.p75_cls ?? 'not stored'}.`);
    }
    if (labPage?.lab_performance) {
      const lab = labPage.lab_performance as { lighthouse_audit_version?: string; lcp_ms?: number; cls_score?: number };
      return line('MEASURED', `Laboratory Lighthouse ${lab.lighthouse_audit_version} on ${labPage.url}: LCP ${lab.lcp_ms ?? 'not stored'} ms, CLS ${lab.cls_score ?? 'not stored'}. This is not field Core Web Vitals.`);
    }
    return untouched('LCP, INP, and CLS were not measured. Crawl response time is not a Core Web Vital.');
  }
  if (sectionNumber === '50') {
    return untouched('No conversion rate is shown. GA4 key events were not measured as a rate for this line, and a crawl is not a conversion test.');
  }
  if (!crawled) {
    return untouched(`${label} was not measured. No page was crawled.`);
  }

  const codes = pages
    .map((page) => finite(page.status_code))
    .filter((value): value is number => value != null);
  const codeSummary = () => {
    const counts = new Map<number, number>();
    for (const code of codes) counts.set(code, (counts.get(code) || 0) + 1);
    return [...counts.entries()].map(([code, count]) => `${count} × HTTP ${code}`).join(', ');
  };

  if (sectionNumber === '07' || sectionNumber === '12') {
    if (text.includes('robots.txt') && !text.includes('compromised')) {
      if (!manifest) return untouched('No crawl record was stored, so robots.txt was not fetched.');
      return manifest.robots_txt_found
        ? line('MEASURED', 'robots.txt was recorded on this crawl.')
        : line('ISSUE_VERIFIED', 'robots.txt was not found at the domain root in this crawl.');
    }
    if (text.includes('sitemap') && !/image|video|news/.test(text)) {
      if (!manifest) return untouched('No crawl record was stored, so a sitemap was not fetched.');
      return manifest.sitemap_found
        ? line('MEASURED', `A sitemap was recorded${manifest.sitemap_url ? ` at ${manifest.sitemap_url}` : ''}.`)
        : line('ISSUE_VERIFIED', 'No XML sitemap was recorded on this crawl.');
    }
    if (/image sitemap|video sitemap|news sitemap/.test(text)) {
      return untouched(`${label} was not validated as a separate sitemap.`);
    }
    if (/http|crawler access|response/.test(text) && codes.length) {
      return line('MEASURED', `Stored status codes: ${codeSummary()}. ${checked}`);
    }
  }

  if (sectionNumber === '08') {
    if (text.includes('search console')) {
      const state = report.google_performance?.search_console?.state || 'NOT_CONNECTED';
      return untouched(`Search Console is ${state}. URL inspection was not run.`, 'DATA_UNAVAILABLE');
    }
    if (text.includes('soft 404')) {
      return untouched('Soft 404s were not classified. An HTTP 200 is not proof a page has useful content.');
    }
    if (text.includes('indexable')) {
      const flags = pages.filter((page) => typeof page.is_indexable === 'boolean');
      if (!flags.length) return untouched('The indexable flag was not stored. HTTP 200 is not an indexable verdict.');
      const yes = flags.filter((page) => page.is_indexable).length;
      return line('MEASURED', `${yes} of ${flags.length} crawled pages stored is_indexable=true. ${checked}`);
    }
  }

  if (sectionNumber === '09' && /http\/https|https/.test(text)) {
    const secure = pages.filter((page) => page.url.startsWith('https://')).length;
    return line(secure === pages.length ? 'NO_ISSUE' : 'ISSUE_VERIFIED', `${secure} of ${pages.length} crawled URLs use https. Certificate expiry was not checked.`);
  }
  if (sectionNumber === '09' && text.includes('query parameter')) {
    const withQuery = pages.filter((page) => page.url.includes('?')).length;
    return line('MEASURED', `${withQuery} crawled URL(s) contain a query string. ${checked}`);
  }

  if (sectionNumber === '10' && text.includes('canonical')) {
    const missing = pages.filter((page) => !(page.canonical_url || '').trim()).length;
    return line(
      missing ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
      `${pages.length - missing} crawled page(s) store a canonical. ${missing} do not. Chains were not walked. ${checked}`,
    );
  }

  if (sectionNumber === '11' && /404|410|broken/.test(text)) {
    const broken = codes.filter((code) => code >= 400).length;
    return line(
      broken ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
      broken
        ? `${broken} crawled response(s) are HTTP 4xx or 5xx. ${checked}`
        : `No HTTP 4xx or 5xx was stored in the crawled sample. ${checked}`,
    );
  }
  if (sectionNumber === '11' && text.includes('redirect')) {
    const redirected = pages.filter((page) => page.status_code >= 300 && page.status_code < 400);
    if (!redirected.length) {
      return line('NO_ISSUE', `No redirect was stored on the crawled pages. A host-variant probe was not stored. ${checked}`);
    }
    return line('MEASURED', `${redirected.length} crawled URL(s) returned a 3xx status. Chain length was not walked unless a redirect audit stored it.`);
  }

  if ((sectionNumber === '14' || sectionNumber === '07') && /ttfb|time to first byte|latency/.test(text)) {
    const timed = pages.filter((page) => finite(page.ttfb_ms) != null && (page.ttfb_ms as number) > 0);
    if (!timed.length) return untouched('No positive crawl response time was stored. A missing timing is not a pass and is not a Core Web Vital.');
    const shown = timed.slice(0, 5).map((page) => `${page.url} ${page.ttfb_ms} ms`).join('; ');
    return line('MEASURED', `Crawl response time, not a Core Web Vital: ${shown}.`);
  }
  if (sectionNumber === '14' && /200|response|5xx|4xx/.test(text) && codes.length) {
    return line('MEASURED', `Stored status codes: ${codeSummary()}. ${checked}`);
  }
  if (sectionNumber === '14' && /certificate|tls|https/.test(text)) {
    return untouched('Certificate validity was not stored. An https URL is not a certificate check.');
  }

  if (sectionNumber === '15') {
    return untouched('Raw HTML versus rendered DOM was not compared. A script count is not a hydration test.');
  }

  if (sectionNumber === '17' && text.includes('viewport')) {
    const missing = pages.filter((page) => !(page.viewport || '').trim()).length;
    return line(
      missing ? 'ISSUE_VERIFIED' : 'NO_ISSUE',
      missing
        ? `${missing} crawled page(s) have no viewport tag. Tap targets and mobile parity were not tested.`
        : `Every crawled page has a viewport tag. Tap targets and mobile parity were not tested.`,
    );
  }
  if (sectionNumber === '17') {
    return untouched('This mobile behavior was not tested. A viewport tag is not a mobile-parity result.');
  }

  if (sectionNumber === '18' && text.includes('https')) {
    const insecure = pages.filter((page) => page.url.startsWith('http://')).length;
    return line(insecure ? 'ISSUE_VERIFIED' : 'NO_ISSUE', `${pages.length - insecure} of ${pages.length} crawled URLs use https. Mixed content was not scanned.`);
  }
  if (sectionNumber === '18') {
    return untouched('Security header names were not judged from an empty header map. A missing stored header is not proof the header is absent.');
  }

  if (sectionNumber === '19' || sectionNumber === 'H') {
    const types = [...new Set(pages.flatMap((page) => page.schema_types || []))];
    if (!types.length) return untouched('No schema type was stored on the crawled pages. That is not a rich-result eligibility score.');
    return line('MEASURED', `Schema types in the sample: ${types.join(', ')}. A type in the HTML is not a guaranteed rich result.`);
  }

  if (sectionNumber === '20') {
    if (text.includes('missing title')) {
      const missing = pages.filter((page) => !(page.title || '').trim()).length;
      return line(missing ? 'ISSUE_VERIFIED' : 'NO_ISSUE', missing ? `${missing} crawled page(s) have no title.` : `Every crawled page has a title. ${checked}`);
    }
    if (text.includes('length') || text.includes('truncat')) {
      const long = pages.filter((page) => (page.title || '').length > 60).length;
      return line('MEASURED', `${long} stored title(s) are over 60 characters. That is a truncation risk, not a measured click-through rate.`);
    }
    if (text.includes('meta description')) {
      const missing = pages.filter((page) => !(page.meta_description || '').trim()).length;
      return line(missing ? 'ISSUE_VERIFIED' : 'NO_ISSUE', `${missing} crawled page(s) have no meta description. Search engines may rewrite the snippet.`);
    }
  }

  if (sectionNumber === '21' && text.includes('h1')) {
    const known = pages.filter((page) => Array.isArray(page.h1));
    if (!known.length) return untouched('H1 lists were not stored.');
    const missing = known.filter((page) => page.h1.length === 0).length;
    return line(missing ? 'ISSUE_VERIFIED' : 'NO_ISSUE', `${missing} of ${known.length} crawled pages have no H1. ${checked}`);
  }

  if (sectionNumber === '23' && /word|thin|completeness/.test(text)) {
    const counted = pages.filter((page) => finite(page.word_count) != null && (page.word_count as number) > 0);
    if (!counted.length) return untouched('Word counts were not stored. A missing count is not a thin-content verdict.');
    const shown = counted.slice(0, 5).map((page) => `${page.url}: ${page.word_count} words`).join('; ');
    return line('MEASURED', `Extracted word counts: ${shown}. A word count is not by itself a quality grade.`);
  }

  if (sectionNumber === '28' && /alt/.test(text)) {
    const total = pages.reduce((sum, page) => sum + (finite(page.total_images) ?? 0), 0);
    const missing = pages.reduce((sum, page) => sum + (finite(page.images_without_alt) ?? 0), 0);
    if (total <= 0) return untouched('No image count was stored. A missing count is not zero images and not a pass.');
    return line(missing ? 'ISSUE_VERIFIED' : 'NO_ISSUE', `${missing} of ${total} stored images have no alt text. ${checked}`);
  }

  return untouched(`${label} was not given a separate measurement. ${checked}`);
}

const AGENT_MAP: Record<string, { id: string; name: string }> = {
  '01': { id: 'strategy.executive.v3', name: 'Executive Strategy Specialist' },
  '02': { id: 'strategy.executive.v3', name: 'SEO Scorecard & Measurement Specialist' },
  '03': { id: 'business.discovery.v3', name: 'Business Discovery Specialist' },
  '04': { id: 'verification.adversarial.v3', name: 'Risk & Policy Verification Specialist' },
  '05': { id: 'competitor.organic.v3', name: 'Competitor Intelligence Specialist' },
  '06': { id: 'strategy.executive.v3', name: 'Prioritization & Roadmap Specialist' },
  '07': { id: 'seo.crawl.v3', name: 'Crawl Infrastructure Specialist' },
  '08': { id: 'seo.indexability.v3', name: 'Indexation & Index Coverage Specialist' },
  '09': { id: 'seo.indexability.v3', name: 'URL Architecture & Normalization Specialist' },
  '10': { id: 'seo.canonical.v3', name: 'Canonicalization & Duplicate Control Specialist' },
  '11': { id: 'seo.redirect.v3', name: 'Redirect & Broken Link Specialist' },
  '12': { id: 'seo.sitemap.v3', name: 'XML Sitemap Architecture Specialist' },
  '13': { id: 'seo.crawl.v3', name: 'Site Architecture & Internal Links Specialist' },
  '14': { id: 'seo.status_reliability.v3', name: 'HTTP & Server Reliability Specialist' },
  '15': { id: 'seo.rendering.v3', name: 'JavaScript & DOM Rendering Specialist' },
  '16': { id: 'ux.experience.v3', name: 'Core Web Vitals & Page Speed Specialist' },
  '17': { id: 'ux.experience.v3', name: 'Mobile SEO & Responsive Behavior Specialist' },
  '18': { id: 'trust.security.v3', name: 'HTTPS & Security Integrity Specialist' },
  '19': { id: 'schema.validation.v3', name: 'Structured Data & Schema Specialist' },
  '20': { id: 'content.intent.v3', name: 'Title Tag & Snippet Copywriting Specialist' },
  '21': { id: 'content.depth.v3', name: 'Heading & Document Outline Specialist' },
  '22': { id: 'business.intent.v3', name: 'Keyword Research & Search Intent Specialist' },
  '23': { id: 'content.depth.v3', name: 'Content Quality & Usefulness Specialist' },
  '24': { id: 'content.intent.v3', name: 'Intent Alignment & Query Mapping Specialist' },
  '25': { id: 'content.authority.v3', name: 'Topical Authority & Semantic Graph Specialist' },
  '26': { id: 'content.decay.v3', name: 'Duplication & Content Decay Specialist' },
  '27': { id: 'content.depth.v3', name: 'Internal Linking & Anchor Text Specialist' },
  '28': { id: 'content.readability.v3', name: 'Visual & Image SEO Specialist' },
  '29': { id: 'seo.specialized.video.v3', name: 'Video & Multimodal SEO Specialist' },
  '30': { id: 'seo.specialized.governance.v3', name: 'Content Governance & Editorial Specialist' },
  '31': { id: 'external.authority.v3', name: 'Backlink Profile & Link Graph Specialist' },
  '32': { id: 'external.authority.v3', name: 'Digital PR & Brand Authority Specialist' },
  '33': { id: 'competitor.organic.v3', name: 'Competitor Benchmarking Specialist' },
  '34': { id: 'competitor.serp.v3', name: 'SERP Visibility & Ranking Specialist' },
  '35': { id: 'seo.specialized.local.v3', name: 'Local SEO & GBP Specialist' },
  '36': { id: 'seo.specialized.international.v3', name: 'International & Hreflang Specialist' },
  '37': { id: 'seo.specialized.policy_compliance.v3', name: 'Search Policy & Anti-Spam Specialist' },
  '38': { id: 'seo.specialized.ecommerce.v3', name: 'E-Commerce & Merchant Feed Specialist' },
  '39': { id: 'seo.specialized.news.v3', name: 'Publisher & News SEO Specialist' },
  '40': { id: 'seo.specialized.programmatic.v3', name: 'Programmatic SEO & Scale Specialist' },
  '41': { id: 'seo.specialized.saas_b2b.v3', name: 'SaaS & B2B Lead-Gen SEO Specialist' },
  '42': { id: 'seo.specialized.app.v3', name: 'App Discovery & Mobile Deep-Link Specialist' },
  '43': { id: 'seo.specialized.accessibility.v3', name: 'Accessibility & Semantic UX Specialist' },
  '44': { id: 'aeo.conversational_intent.v3', name: 'Voice & Multimodal Query Specialist' },
  '45': { id: 'aeo.direct_answer_box.v3', name: 'Answer Engine Optimization (AEO) Specialist' },
  '46': { id: 'geo.extractability.v3', name: 'Generative Engine Optimization (GEO) Specialist' },
  '47': { id: 'ai_search.discoverability.v3', name: 'AI Search & Citation Specialist' },
  '48': { id: 'seo.indexability.v3', name: 'Google Search Console Intelligence Specialist' },
  '49': { id: 'cro.analytics_integrity.v3', name: 'Analytics & Conversion Tracking Specialist' },
  '50': { id: 'ux.conversion.v3', name: 'Conversion Rate Optimization (CRO) Specialist' },
  '51': { id: 'business.commercial.v3', name: 'Organic Revenue & Attribution Specialist' },
  '52': { id: 'seo.specialized.forecasting.v3', name: 'Opportunity Modeling & Forecasting Specialist' },
  '53': { id: 'seo.specialized.governance.v3', name: 'Issue Register & Remediation Specialist' },
  '54': { id: 'seo.specialized.governance.v3', name: 'Post-Fix Verification Specialist' },
  '55': { id: 'seo.specialized.governance.v3', name: 'Monitoring & Operations Specialist' },
};

export function buildSectionAnalysis(
  ctx: AuditContext,
  sectionNumber: string,
  status: SectionStatus,
  summary: string,
  findings: Finding[]
): SectionAnalysis {
  const agent = AGENT_MAP[sectionNumber] || {
    id: 'seo.crawl.v3',
    name: 'Technical SEO Specialist',
  };
  const verifiedDefects = findings.filter((f) => f.confidence_rubric !== 'GUESSING');
  const storedCause = verifiedDefects[0]?.description;
  const storedRec = verifiedDefects[0]?.recommendation;
  const domain = ctx.report.domain || 'audited domain';
  const pageCount = ctx.pages.length;

  let mechanics = 'Search engines evaluate this layer by inspecting deterministic crawl responses, rendered DOM trees, and HTTP response headers.';
  let risk = 'Unresolved architectural defects in this area risk organic visibility erosion, crawler budget starvation, and suboptimal snippet presentation.';
  let remediation = storedRec || 'Implement server-level headers, canonical normalization, and semantic markup across affected templates.';
  let verification = 'Re-fetch representative page samples with automated curl headers and compare against Google Search Console URL inspection results.';

  if (sectionNumber === '07') {
    mechanics = `Googlebot and search crawlers traverse ${domain} through internal links and robots.txt directives. Blocked assets, infinite query parameters, or orphan pages exhaust crawl allotments.`;
    risk = 'Search engines delay discovery of newly published commercial URLs, resulting in indexing lag.';
    remediation = 'Audit robots.txt disallow rules; ensure XML sitemaps are referenced and internal search query parameters are blocked from crawl.';
    verification = `curl -I -A 'Googlebot' https://${domain}/robots.txt`;
  } else if (sectionNumber === '08') {
    mechanics = 'Indexation pipelines determine whether crawled HTML is stored in the primary index. Conflicting signals (such as noindex tags with canonical references) trigger exclusion.';
    risk = 'Complete de-indexing of core landing pages, eliminating organic search traffic.';
    remediation = 'Ensure indexable templates serve clean <meta name="robots" content="index, follow"> and remove stray X-Robots-Tag headers.';
    verification = 'Verify URL inspection status in Google Search Console across crawled sample.';
  } else if (sectionNumber === '10') {
    mechanics = 'Canonical tags instruct search engines on the authoritative URL for duplicate or near-duplicate parameter pages.';
    risk = 'PageRank fragmentation and unintended canonicalization to homepage or category roots.';
    remediation = 'Enforce self-referencing absolute canonical tags matching the normalized URL format.';
    verification = 'Inspect rendered DOM canonical elements across all primary page templates.';
  } else if (sectionNumber === '14') {
    mechanics = 'Server response latency and TTFB directly throttle Googlebot crawl speed. Latency spikes above 600ms cause immediate crawl throttling.';
    risk = 'Algorithmic ranking suppression under speed criteria and high visitor bounce rates.';
    remediation = 'Deploy edge CDN caching (Cloudflare/CloudFront) with Brotli compression to maintain TTFB below 200ms globally.';
    verification = `curl -w '%{time_starttransfer}\\n' -o /dev/null -s https://${domain}/`;
  } else if (sectionNumber === '16') {
    mechanics = 'Core Web Vitals enforce thresholds: LCP <= 2.5s, INP <= 200ms, CLS <= 0.1 at the 75th percentile of user visits.';
    risk = 'Failing Core Web Vitals assessment suppresses search ranking in competitive algorithmic bake-offs.';
    remediation = 'Preload LCP hero images, defer non-critical third-party analytics scripts, and reserve explicit layout dimensions on image containers.';
    verification = 'Audit with Google PageSpeed Insights and Chrome User Experience Report (CrUX).';
  } else if (sectionNumber === '19') {
    mechanics = 'Schema.org JSON-LD entities establish machine-readable Knowledge Graph nodes and award rich search snippets.';
    risk = 'Zero rich snippets in Google search results, reducing SERP click-through rates by up to 30%.';
    remediation = 'Implement connected JSON-LD Schema.org graphs (Organization, WebSite, BreadcrumbList, Product/Article) linked via @id.';
    verification = 'Validate live pages against Google Rich Results Test API.';
  } else if (sectionNumber === '20') {
    mechanics = 'Google displays titles up to ~60 characters (580px) before truncation. Boilerplate or generic titles are algorithmically rewritten.';
    risk = 'Diminished search snippet click-through rates and brand misrepresentation.';
    remediation = 'Craft titles following the formula: Primary Keyword - Specific Value Benefit | Brand (strictly 50-60 chars).';
    verification = 'Test title pixel widths in a SERP emulator to guarantee zero truncation.';
  } else if (sectionNumber === '45' || sectionNumber === '46' || sectionNumber === '47') {
    mechanics = 'Answer engines (ChatGPT, Perplexity, AI Overviews) extract 40-60 word declarative passages beneath clear question headings.';
    risk = 'Complete omission from zero-click AI search answers and conversational product recommendations.';
    remediation = 'Publish concise direct answer blocks immediately beneath question headings, supported by comparative data tables.';
    verification = 'Benchmark target question queries across Perplexity AI and ChatGPT Search.';
  }

  return {
    agentId: agent.id,
    agentName: agent.name,
    executiveSummary: summary || `Consultative diagnostic analysis for ${agent.name} across ${pageCount} inspected URLs.`,
    technicalMechanics: mechanics,
    rootCause: storedCause
      ? `Recorded finding: ${storedCause}`
      : (status === 'ISSUE_VERIFIED' ? 'Template configuration drift or legacy routing debt.' : 'No architectural defect observed in the inspected sample.'),
    businessImpact: risk,
    remediation,
    verificationMethod: verification,
  };
}

