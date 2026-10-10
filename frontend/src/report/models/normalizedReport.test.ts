import { describe, it, expect } from 'vitest';
import { normalizeExecutiveReport } from './normalizedReport';
import { ExecutiveReport } from '../../types';

describe('NormalizedReport Model & Zero-Fake Enforcer', () => {
  const mockReport: Partial<ExecutiveReport> = {
    report_id: 'rpt_test_123',
    analysis_id: 'analysis_456',
    domain: 'enterprise-analytics.io',
    website_url: 'https://enterprise-analytics.io',
    generated_at: '2026-10-03T10:00:00Z',
    certification_status: 'CERTIFIED',
    business_profile: {
      business_name: 'Enterprise Analytics Inc',
      industry: 'Enterprise SaaS',
      value_proposition: 'AI-driven commercial intelligence for Fortune 500 teams',
      target_audience: 'B2B C-Suite & Engineering Leadership',
    } as any,
    scores: {
      overall_score: 82.4,
      grade: 'A',
      overall_confidence: 0.94,
      evidence_coverage: 0.96,
      category_scores: {
        TECHNICAL_SEO: { score: 88, weight: 0.3 } as any,
        GEO: { score: 78, weight: 0.25 } as any,
        UX_CONVERSION: { score: 80, weight: 0.25 } as any,
      },
    } as any,
    findings: [
      {
        finding_id: 'F-001',
        title: 'Missing canonical redirect consolidation',
        severity: 'CRITICAL',
        category: 'TECHNICAL_SEO',
        confidence: 0.98,
        description: 'Apex domain does not 301 permanently to www host.',
        evidence_refs: ['ev_dom_1'],
        business_impact: 'Divides PageRank authority across two hosts.',
        recommendation: 'Deploy server 301 redirect rule.',
      } as any,
    ],
    evidence_ledger: {
      ev_dom_1: {
        source_type: 'html_dom_ast',
        url: 'https://enterprise-analytics.io',
        selector: 'head > link[rel="canonical"]',
        text: '<link rel="canonical" href="https://enterprise-analytics.io" />',
        content_sha256: 'sha256:abcdef1234567890',
        fetched_at: '2026-10-03T10:00:00Z',
      },
    } as any,
    crawl_manifest: {
      pages: [
        { url: 'https://enterprise-analytics.io/', status_code: 200, ttfb_ms: 142, word_count: 850 } as any,
        { url: 'https://enterprise-analytics.io/solutions', status_code: 200, ttfb_ms: 185, word_count: 1200 } as any,
      ],
    } as any,
    commercial_evaluations: [
      {
        question_key: 'q1',
        question_title: 'Enterprise Pricing Model',
        buyer_query: 'How much does enterprise analytics platform cost?',
        before_score: 4,
        after_score: 9,
        before_evidence_status: 'PARTIAL',
      } as any,
    ],
    dynamic_sandbox_evaluations: [
      {
        question_id: 'd1',
        facet: 'Pricing & Commercial Terms',
        generated_question: 'What is the entry price for enterprise tier?',
        answerability_status: 'ANSWERABLE',
        citability_score: 8,
        projected_patch_gain: 0.35,
      } as any,
    ],
    competitor_bakeoff: {
      competitor_domain: 'competitor-a.com', // Synthetic placeholder name!
      evaluations: [],
      target_wins: 0,
      competitor_wins: 0,
      ties: 0,
      executive_takeaway: 'Placeholder competitor',
    } as any,
  };

  it('normalizes core metadata, brand name, and certification status', () => {
    const normalized = normalizeExecutiveReport(mockReport as ExecutiveReport);

    expect(normalized.meta.domain).toBe('enterprise-analytics.io');
    expect(normalized.meta.brandName).toBe('Enterprise Analytics Inc');
    expect(normalized.meta.certifiedZeroFake).toBe(true);
    expect(normalized.meta.pagesAnalyzed).toBe(2);
  });

  it('enforces Zero-Fake rule by rejecting synthetic competitor placeholder names', () => {
    const normalized = normalizeExecutiveReport(mockReport as ExecutiveReport);

    // Because competitor_domain is "competitor-a.com", it MUST be rejected as unprovisioned
    expect(normalized.competitive.isRealCompetitorDataAvailable).toBe(false);
    expect(normalized.competitive.competitorName).toBeUndefined();
  });

  it('accepts legitimate, real competitors in the bake-off model', () => {
    const realCompetitorReport = {
      ...mockReport,
      competitor_bakeoff: {
        competitor_domain: 'realmarketpeer.com',
        evaluations: [
          {
            question_key: 'q1',
            question_title: 'Global SOC2 Certification',
            winner: 'Target Site',
            commercial_takeaway: 'Target site explicitly displays SOC2 Type II compliance.',
          },
        ],
      },
    };

    const normalized = normalizeExecutiveReport(realCompetitorReport as any);
    expect(normalized.competitive.isRealCompetitorDataAvailable).toBe(true);
    expect(normalized.competitive.competitorName).toBe('realmarketpeer.com');
  });

  it('calculates Re-Query citation uplift delta correctly', () => {
    const normalized = normalizeExecutiveReport(mockReport as ExecutiveReport);

    // before_score = 4, after_score = 9 -> delta = (9 - 4) * 10 = +50%
    expect(normalized.aeo.requeryGainPct).toBe(50);
  });

  it('preserves cryptographic evidence ledger and links findings to evidence IDs', () => {
    const normalized = normalizeExecutiveReport(mockReport as ExecutiveReport);

    expect(normalized.appendices.evidenceLedger.length).toBeGreaterThanOrEqual(1);
    const ev = normalized.appendices.evidenceLedger[0];
    expect(ev.id).toBe('ev_dom_1');
    expect(ev.sha256).toBe('sha256:abcdef1234567890');

    expect(normalized.appendices.findings[0].evidenceItems[0].id).toBe('ev_dom_1');
  });

  it('prints the ledger composite instead of a second overall score', () => {
    const normalized = normalizeExecutiveReport({
      ...mockReport,
      scores: {
        ...mockReport.scores,
        overall_score: 83,
        grade: 'A',
      },
      honest_scores: {
        google_score: 79.6,
        ai_readiness_score: 80,
        human_score: 76.6,
        live_ai_citation_score: 0,
        ai_visibility_status: 'MEASURED',
        ai_citation_score: 80,
      },
    } as ExecutiveReport);

    expect(normalized.scorecard.overallScore).toBe(78.9);
    expect(normalized.scorecard.grade).toBe('B');
    expect(normalized.brief.keySignals.overallScore).toBe(78.9);
    expect(normalized.brief.keySignals.overallGrade).toBe('B');
    expect(normalized.scorecard.ledger.find((row) => row.categoryKey === 'AEO')?.included).toBe(false);
    expect(normalized.googlePerformance.searchConsole.state).toBe('NOT_CONNECTED');
    expect(normalized.googlePerformance.analytics.state).toBe('NOT_CONNECTED');
    expect(normalized.googlePerformance.searchConsole.metrics).toEqual([]);
  });

  it('uses measured extractability instead of a GEO category score of 100', () => {
    const normalized = normalizeExecutiveReport({
      ...mockReport,
      story_summary: 'Acme scores 83/100 (B, Good). This figure is the weighted rollup of pillar scores.',
      scores: {
        ...mockReport.scores,
        overall_score: 83,
        grade: 'B',
        category_scores: {
          ...mockReport.scores.category_scores,
          GEO: { score: 100, weight: 0.2, weighted_score: 20, status: 'MEASURED', summary: 'rubric pass' },
        },
      },
      honest_scores: {
        google_score: 79.6,
        ai_readiness_score: 80,
        human_score: 76.6,
        live_ai_citation_score: 0,
        ai_visibility_status: 'MEASURED',
        ai_citation_score: 0,
      },
      geo_readiness: {
        extractability_score: 52.7,
      },
    } as ExecutiveReport);

    expect(normalized.scorecard.overallScore).toBe(69.8);
    expect(normalized.scorecard.grade).toBe('C');
    expect(normalized.brief.keySignals.geoScore).toBe(52.7);
    expect(normalized.scorecard.ledger.find((row) => row.categoryKey === 'GEO')?.rawScore).toBe(52.7);
    expect(normalized.brief.leadThesis).toContain('69.8/100 (grade C)');
    expect(normalized.brief.leadThesis).not.toContain('83/100');
  });

  it('keeps a measured citation zero when this run has engine responses', () => {
    const normalized = normalizeExecutiveReport({
      ...mockReport,
      story_summary: 'Acme scores 83/100 (B, Good). This figure is the weighted rollup of pillar scores.',
      honest_scores: {
        google_score: 79.6,
        ai_readiness_score: 80,
        human_score: 76.6,
        live_ai_citation_score: 0,
        ai_visibility_status: 'MEASURED',
      },
      geo_readiness: { extractability_score: 52.7 },
      ai_visibility_scorecard: {
        status: 'MEASURED',
        queries: 18,
        successful_runs: 3,
        failed_runs: 0,
        engines_measured: 1,
        engines_requested: 5,
        repeats: 1,
        citation_rate_pct: 0,
        observatory_records: [{ engine_id: 'claude', brand_cited: false, brand_mentioned: false }],
      },
      google_performance: {
        search_console: {
          state: 'MEASURED',
          property: 'sc-domain:enterprise-analytics.io',
          period: '28d',
          clicks: 120,
          impressions: 4000,
          average_ctr: 3,
          average_position: 8.2,
          queries: [{ query: 'enterprise analytics', page: '/', clicks: 40, impressions: 900, position: 6.1 }],
        },
        analytics: { state: 'NOT_AUTHORIZED' },
      },
    } as ExecutiveReport);

    expect(normalized.scorecard.overallScore).toBe(52.4);
    expect(normalized.scorecard.grade).toBe('D');
    expect(normalized.aeo.liveObservation.queriesExecuted).toBe(1);
    expect(normalized.aeo.liveObservation.queriesAttempted).toBe(18);
    expect(normalized.googlePerformance.searchConsole.state).toBe('MEASURED');
    expect(normalized.googlePerformance.searchConsole.metrics.find((metric) => metric.label === 'Clicks')?.value).toBe('120');
    expect(normalized.googlePerformance.analytics.state).toBe('NOT_AUTHORIZED');
    expect(normalized.googlePerformance.analytics.metrics).toEqual([]);
  });

  it('does not copy on-page GEO into live citations', () => {
    const normalized = normalizeExecutiveReport({
      ...mockReport,
      honest_scores: {
        google_score: 79.6,
        ai_readiness_score: 80,
        human_score: 76.6,
        ai_visibility_status: 'NOT_MEASURED',
        ai_citation_score: 80,
      },
    } as ExecutiveReport);

    expect(normalized.scorecard.ledger.find((row) => row.categoryKey === 'AEO')?.included).toBe(false);
    expect(normalized.scorecard.overallScore).toBe(78.9);
    expect(normalized.aeo.liveObservation.queriesExecuted).toBe(0);
    expect(normalized.meta.discoveredUrlsCount).toBeNull();
    expect(normalized.conversion.formCount).toBeNull();
  });

  it('does not reuse one page snapshot as every evidence seal', () => {
    const shared = 'sha256:abcdef1234567890abcdef1234567890';
    const normalized = normalizeExecutiveReport({
      ...mockReport,
      evidence_ledger: {
        h1: { source_type: 'dom', url: 'https://enterprise-analytics.io', text: 'One', content_sha256: shared },
        title: { source_type: 'dom', url: 'https://enterprise-analytics.io', text: 'Two', content_sha256: shared },
      },
    } as ExecutiveReport);

    expect(normalized.appendices.evidenceLedger.map((item) => item.hashStatus)).toEqual(['SHARED_SNAPSHOT', 'SHARED_SNAPSHOT']);
    expect(normalized.appendices.evidenceLedger.every((item) => item.sha256 == null)).toBe(true);
  });
});
