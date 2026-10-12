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

export function buildSectionAnalysis(
  _ctx: AuditContext,
  _sectionNumber: string,
  _status: SectionStatus,
  summary: string,
  findings: Finding[]
): SectionAnalysis {
  const storedCause = findings.find((finding) => finding.confidence_rubric !== 'GUESSING')?.description;
  return {
    agentId: 'stored-evidence',
    agentName: 'Stored evidence',
    executiveSummary: summary,
    technicalMechanics: 'Charts count stored measurements. A missing source is not drawn as zero.',
    rootCause: storedCause
      ? 'The recorded finding is the evidence. A root cause is shown only when that finding stored one.'
      : 'No root cause was established beyond the stored evidence.',
    businessImpact: 'Traffic, revenue, and rankings are not estimated from this chapter.',
    remediation: 'A change is named only when a finding stored one.',
    verificationMethod: 'Re-fetch the same URL sample and compare the stored evidence.',
  };
}
