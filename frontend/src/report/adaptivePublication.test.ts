import { describe, it, expect } from 'vitest';
import {
  detectReportFamily,
  buildPublicationManifest,
  ReportFamily,
} from './adaptivePublication';
import { computePublicationPagination, toRomanNumeral } from './paginationEngine';
import { normalizeExecutiveReport } from './models/normalizedReport';
import { ExecutiveReport } from '../types';

function mockMinimalReport(overrides: Partial<ExecutiveReport> = {}): ExecutiveReport {
  return {
    report_id: 'rep_001',
    analysis_id: 'analysis_001',
    website_url: 'https://testdomain.com',
    domain: 'testdomain.com',
    generated_at: '2026-10-12T12:00:00Z',
    business_profile: {
      business_name: 'Test Domain Corp',
    },
    scores: {
      overall_score: 82.5,
      overall_grade: 'B',
      grade: 'B',
      health_label: 'GOOD',
      seo_score: 85,
      geo_score: 80,
      aeo_score: 75,
      cro_score: 78,
      category_scores: {
        TECHNICAL_SEO: { score: 85, weight: 25 },
        GEO: { score: 80, weight: 25 },
        AEO: { score: 75, weight: 25 },
        UX_CONVERSION: { score: 78, weight: 25 },
      },
    },
    story_summary: 'Overall digital asset baseline is healthy with structured opportunities.',
    primary_strategic_opportunity: 'Consolidate canonical directives and enrich Schema.org organization markup.',
    consultant_advice_what_to_ignore: 'Do not spend engineering time on vanity subdomains.',
    three_way_comparison: {
      human_visitor_perspective: 'Clean layout and clear proposition.',
      search_engine_perspective: 'Standard crawl access and responsive HTTP 200 responses.',
      ai_answer_engine_perspective: 'Factual passages extractable with minor attribution gaps.',
    },
    findings: [
      {
        finding_id: 'f_seo_01',
        category: 'TECHNICAL_SEO',
        severity: 'HIGH',
        title: 'Missing canonical consolidation',
        description: 'Apex domain does not 301 redirect to www canonical target.',
        evidence_id: 'ev_001',
        evidence: [
          {
            evidence_id: 'ev_001',
            element: 'head',
            selector: 'link[rel="canonical"]',
            snippet: '<link rel="canonical" href="https://testdomain.com" />',
            source: 'crawl',
          },
        ],
        recommendation: 'Configure NGINX 301 rewrite rule.',
      },
      {
        finding_id: 'f_aeo_01',
        category: 'AI_SEARCH',
        severity: 'MEDIUM',
        title: 'Pricing query passage truncation',
        description: 'Pricing tier tables lack machine-readable text descriptions.',
        evidence_id: 'ev_002',
        evidence: [
          {
            evidence_id: 'ev_002',
            element: 'div',
            selector: '#pricing-matrix',
            snippet: '<div id="pricing-matrix">...</div>',
            source: 'crawl',
          },
        ],
        recommendation: 'Add structured pricing FAQ section.',
      },
    ],
    ...overrides,
  } as ExecutiveReport;
}

describe('Adaptive Publication Engine', () => {
  it('detects COMPLETE report family when multiple disciplines have telemetry', () => {
    const raw = mockMinimalReport({
      geo_readiness: { extractability_score: 80 } as any,
      dynamic_sandbox_evaluations: [{ question_key: 'q1' }] as any,
      cro_audit: { value_prop_found: true } as any,
      competitor_bakeoff: { competitors: [{ domain: 'comp1.com' }] } as any,
    });
    const normalized = normalizeExecutiveReport(raw);
    const family = detectReportFamily(normalized);
    expect(family).toBe('COMPLETE');
  });

  it('detects SEO report family when only SEO crawl telemetry is present', () => {
    const raw = mockMinimalReport({
      policy_pack: 'seo_only',
    });
    const normalized = normalizeExecutiveReport(raw);
    const family = detectReportFamily(normalized);
    expect(family).toBe('SEO');
  });

  it('detects GEO report family when policy pack is geo_only', () => {
    const raw = mockMinimalReport({
      policy_pack: 'geo_only',
    });
    const normalized = normalizeExecutiveReport(raw);
    const family = detectReportFamily(normalized);
    expect(family).toBe('GEO');
  });

  it('detects AEO report family when policy pack is aeo_only', () => {
    const raw = mockMinimalReport({
      policy_pack: 'aeo_only',
    });
    const normalized = normalizeExecutiveReport(raw);
    const family = detectReportFamily(normalized);
    expect(family).toBe('AEO');
  });

  it('detects CRO report family when policy pack is cro_only', () => {
    const raw = mockMinimalReport({
      policy_pack: 'cro_only',
    });
    const normalized = normalizeExecutiveReport(raw);
    const family = detectReportFamily(normalized);
    expect(family).toBe('CRO');
  });

  it('respects explicit user override over auto-detection', () => {
    const raw = mockMinimalReport();
    const normalized = normalizeExecutiveReport(raw);
    const family = detectReportFamily(normalized, 'CRO');
    expect(family).toBe('CRO');
  });

  it('builds type-specific publication manifests with adapted titles and badges', () => {
    const raw = mockMinimalReport();
    const normalized = normalizeExecutiveReport(raw);

    const seoManifest = buildPublicationManifest(normalized, 'SEO');
    expect(seoManifest.family).toBe('SEO');
    expect(seoManifest.title).toContain('Technical SEO');
    expect(seoManifest.reportTypeBadge).toContain('SEO');
    expect(seoManifest.chapters.some((c) => c.id === 'ch_seo')).toBe(true);
    expect(seoManifest.chapters.some((c) => c.id === 'ch_geo')).toBe(false);

    const aeoManifest = buildPublicationManifest(normalized, 'AEO');
    expect(aeoManifest.family).toBe('AEO');
    expect(aeoManifest.title).toContain('Answer Engine Optimization');
    expect(aeoManifest.chapters.some((c) => c.id === 'ch_aeo')).toBe(true);
    expect(aeoManifest.chapters.some((c) => c.id === 'ch_seo')).toBe(false);

    const completeManifest = buildPublicationManifest(normalized, 'COMPLETE');
    expect(completeManifest.family).toBe('COMPLETE');
    expect(completeManifest.chapters.some((c) => c.id === 'ch_seo')).toBe(true);
    expect(completeManifest.chapters.some((c) => c.id === 'ch_geo')).toBe(true);
    expect(completeManifest.chapters.some((c) => c.id === 'ch_aeo')).toBe(true);
  });

  it('supports custom title, subtitle, and confidentiality overrides', () => {
    const raw = mockMinimalReport();
    const normalized = normalizeExecutiveReport(raw);

    const manifest = buildPublicationManifest(normalized, 'COMPLETE', {
      titleOverride: 'Acme Strategic Q4 Digital Audit',
      subtitleOverride: 'Confidential Engineering Review',
      classificationOverride: 'RESTRICTED // BOARD DOSSIER',
    });

    expect(manifest.title).toBe('Acme Strategic Q4 Digital Audit');
    expect(manifest.subtitle).toBe('Confidential Engineering Review');
    expect(manifest.classification).toBe('RESTRICTED // BOARD DOSSIER');
  });
});

describe('Book Pagination & TOC Convergence Engine', () => {
  it('converts numbers to Roman numerals accurately for front matter', () => {
    expect(toRomanNumeral(1)).toBe('i');
    expect(toRomanNumeral(2)).toBe('ii');
    expect(toRomanNumeral(3)).toBe('iii');
    expect(toRomanNumeral(4)).toBe('iv');
    expect(toRomanNumeral(5)).toBe('v');
  });

  it('computes clean pagination starting body at Arabic 1 after Roman front matter', () => {
    const raw = mockMinimalReport();
    const normalized = normalizeExecutiveReport(raw);
    const manifest = buildPublicationManifest(normalized, 'COMPLETE');
    const pagination = computePublicationPagination(manifest, normalized);

    expect(pagination.status).toBe('STABLE_CONVERGED');
    // Front matter check
    expect(pagination.locations['front_matter_details'].logicalPageNumber).toBe('i');
    expect(pagination.locations['front_matter_toc'].logicalPageNumber).toBe('ii');

    // Body check (starts at Arabic 1!)
    expect(pagination.locations['ch_brief'].logicalPageNumber).toBe(1);

    // Later chapters increase monotonically
    const briefPage = pagination.locations['ch_brief'].logicalPageNumber as number;
    const seoPage = pagination.locations['ch_seo'].logicalPageNumber as number;
    expect(seoPage).toBeGreaterThan(briefPage);

    const roadmapPage = pagination.locations['ch_roadmap'].logicalPageNumber as number;
    expect(roadmapPage).toBeGreaterThan(seoPage);
  });

  it('adapts page counts when chapters are excluded in single-discipline profiles', () => {
    const raw = mockMinimalReport();
    const normalized = normalizeExecutiveReport(raw);

    const completeManifest = buildPublicationManifest(normalized, 'COMPLETE');
    const completePagination = computePublicationPagination(completeManifest, normalized);

    const seoManifest = buildPublicationManifest(normalized, 'SEO');
    const seoPagination = computePublicationPagination(seoManifest, normalized);

    expect(seoPagination.totalPhysicalPages).toBeLessThan(completePagination.totalPhysicalPages);
  });
});
