import { describe, expect, it } from 'vitest';
import { ExecutiveReport, PageEvidence } from '../../types';
import { AUDIT_SECTIONS } from './catalog';
import { resolveAuditIndex } from './resolveAuditIndex';

function report(partial: Partial<ExecutiveReport>): ExecutiveReport {
  return partial as ExecutiveReport;
}

function page(partial: Partial<PageEvidence>): PageEvidence {
  return partial as PageEvidence;
}

function section(partial: Partial<ExecutiveReport>, number: string) {
  return resolveAuditIndex(report(partial)).sections.find((item) => item.number === number);
}

describe('audit index', () => {
  it('lists every section and appendix once', () => {
    const numbers = AUDIT_SECTIONS.map((item) => item.number);
    expect(numbers.slice(0, 55)).toEqual(Array.from({ length: 55 }, (_, index) => String(index + 1).padStart(2, '0')));
    expect(numbers.slice(55)).toEqual(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']);
    expect(new Set(numbers).size).toBe(numbers.length);
  });

  it('does not turn a missing crawl or connector into a pass or a zero', () => {
    const index = resolveAuditIndex(report({}));
    const byNumber = Object.fromEntries(index.sections.map((item) => [item.number, item]));
    expect(byNumber['14'].status).toBe('NOT_TESTED');
    expect(byNumber['16'].status).toBe('NOT_TESTED');
    expect(byNumber['16'].summary).toMatch(/not measured/i);
    expect(byNumber['22'].status).toBe('DATA_UNAVAILABLE');
    expect(byNumber['48'].summary).not.toMatch(/0 clicks/);
    expect(byNumber['49'].status).toBe('DATA_UNAVAILABLE');
    expect(byNumber['50'].summary).not.toMatch(/grade/i);
    expect(byNumber['51'].status).toBe('DATA_UNAVAILABLE');
    expect(byNumber['52'].status).toBe('NOT_TESTED');
    expect(byNumber['47'].summary).toMatch(/not queried/i);
    expect(byNumber['47'].summary).not.toMatch(/citation accuracy is \d/i);
    expect(byNumber['42'].status).toBe('NOT_APPLICABLE');
    expect(index.sections.some((item) => /score:\s*0\b/.test(item.summary))).toBe(false);
  });

  it('keeps a clean response sample from standing in for Core Web Vitals', () => {
    const http = section({
      crawl_manifest: {
        domain: 'example.com',
        base_url: 'https://example.com',
        total_pages_discovered: 20,
        sitemap_found: true,
        robots_txt_found: true,
        crawl_health: {},
        pages: [
          page({ url: 'https://example.com/', status_code: 200, title: 'Home', meta_description: 'A description of the home page for buyers.', h1: ['Home'], word_count: 400, viewport: 'width=device-width', schema_types: [], total_images: 1, images_without_alt: 0 }),
          page({ url: 'https://example.com/pricing', status_code: 200, title: 'Pricing', meta_description: 'A description of the pricing page for buyers.', h1: ['Pricing'], word_count: 500, viewport: 'width=device-width', schema_types: [], total_images: 0, images_without_alt: 0 }),
        ],
      },
      http_status_breakdown: {
        total_urls_checked: 2,
        count_2xx: 2,
        count_3xx: 0,
        count_4xx: 0,
        count_5xx: 0,
        status_health_score: 100,
        pages_2xx: [],
        pages_3xx: [],
        pages_4xx: [],
        pages_5xx: [],
        broken_links: [],
        summary: '',
      },
    }, '16');
    expect(section({
      http_status_breakdown: {
        total_urls_checked: 2,
        count_2xx: 2,
        count_3xx: 0,
        count_4xx: 0,
        count_5xx: 0,
        status_health_score: 100,
        pages_2xx: [],
        pages_3xx: [],
        pages_4xx: [],
        pages_5xx: [],
        broken_links: [],
        summary: '',
      },
    }, '14')?.status).toBe('NO_ISSUE');
    expect(http?.status).toBe('NOT_TESTED');
    expect(http?.summary).toMatch(/LCP, INP, and CLS/);
  });

  it('selects specialist modules from the business profile and live measurement', () => {
    const saas = resolveAuditIndex(report({
      business_profile: {
        business_name: 'Acme',
        industry: 'Software',
        niche: 'CRM',
        products: [],
        services: [],
        target_audience: 'Ops teams',
        geography: 'US',
        business_model: 'B2B SaaS',
        value_proposition: 'Pipeline',
        primary_intent: 'commercial',
        confidence: 0.8,
      },
      crawl_manifest: {
        domain: 'acme.test',
        base_url: 'https://acme.test',
        total_pages_discovered: 4,
        sitemap_found: false,
        robots_txt_found: true,
        crawl_health: {},
        pages: [page({ url: 'https://acme.test/', title: 'Acme', h1: ['Acme'], word_count: 300, schema_types: ['Organization'] })],
      },
      ai_visibility_scorecard: {
        status: 'MEASURED',
        measurement_kind: 'LIVE_MODEL_API',
        engines_measured: 2,
        engines_requested: 2,
        engines_queried: ['ChatGPT', 'Perplexity'],
        surfaces_not_queried: ['Google AI Overviews', 'Google AI Mode', 'Bing Copilot'],
        queries: 6,
        repeats: 2,
        successful_runs: 4,
        failed_runs: 0,
        mention_rate_pct: 25,
        citation_rate_pct: 0,
        citation_accuracy_pct: 90,
      },
      google_performance: {
        analytics: {
          state: 'MEASURED',
          sessions: 40,
          key_events: 4,
          landing_pages: [{ page: '/', sessions: 40, key_events: 4 }],
        },
      },
      local_seo: { status: 'NOT_APPLICABLE', summary: 'Not a local business.', nap_consistency_score: 0, phone_conflicts: [], address_conflicts: [], has_google_business_profile: false, gbp_urls: [], has_google_maps_embed: false, local_citations_found: [], local_business_schema_found: false, local_schema_completeness_pct: 0, schema_missing_fields: [], local_landing_pages: [], nap_records: [] },
    }));
    const byNumber = Object.fromEntries(saas.sections.map((item) => [item.number, item]));
    expect(byNumber['38'].status).toBe('NOT_APPLICABLE');
    expect(byNumber['41'].status).toBe('MEASURED');
    expect(byNumber['41'].summary).toMatch(/CRM pipeline/);
    expect(byNumber['35'].status).toBe('NOT_APPLICABLE');
    expect(byNumber['47'].summary).toMatch(/Google AI Overviews/);
    expect(byNumber['47'].summary).toMatch(/Citation accuracy was not span-checked/);
    expect(byNumber['47'].summary).not.toMatch(/90%/);
    expect(byNumber['50'].summary).toMatch(/10%/);
    expect(byNumber['50'].summary).toMatch(/not a 0–100/);
    expect(byNumber['51'].summary).toMatch(/not revenue/i);
  });

  it('attaches a verified technical finding without treating a guess as a defect', () => {
    const verified = section({
      findings: [
        { finding_id: 'f1', category: 'TECHNICAL_SEO', severity: 'HIGH', title: 'Pricing URL returns HTTP 500', description: 'Status 500', evidence: [], evidence_refs: [], confidence: 0.9, confidence_label: 'High', impact: 8, effort: 2, priority: 1, recommendation: 'Fix the origin.', verification_status: 'verified', confidence_rubric: 'CERTAIN', evidence_scope: 'PAGE_VERIFIED' },
        { finding_id: 'f2', category: 'TECHNICAL_SEO', severity: 'LOW', title: 'Possible cloaking', description: 'Guess', evidence: [], evidence_refs: [], confidence: 0.2, confidence_label: 'Low', impact: 1, effort: 1, priority: 9, recommendation: 'Review.', verification_status: 'unverified', confidence_rubric: 'GUESSING' },
      ],
    }, '14');
    expect(verified?.status).toBe('ISSUE_VERIFIED');
    expect(verified?.findings.map((finding) => finding.id)).toContain('f1');
    expect(section({
      findings: [
        { finding_id: 'f2', category: 'TECHNICAL_SEO', severity: 'LOW', title: 'Possible header gap', description: 'Guess', evidence: [], evidence_refs: [], confidence: 0.2, confidence_label: 'Low', impact: 1, effort: 1, priority: 9, recommendation: 'Review.', verification_status: 'unverified', confidence_rubric: 'GUESSING' },
      ],
    }, '14')?.status).not.toBe('ISSUE_VERIFIED');
  });
});
