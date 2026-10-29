import { describe, expect, it } from 'vitest';
import { ExecutiveReport, PageEvidence } from '../types';
import { measuredBreakdowns } from './measuredBreakdowns';

function report(partial: Partial<ExecutiveReport>): ExecutiveReport {
  return partial as ExecutiveReport;
}

function page(partial: Partial<PageEvidence>): PageEvidence {
  return partial as PageEvidence;
}

function ids(partial: Partial<ExecutiveReport>): string[] {
  return measuredBreakdowns(report(partial)).map((chart) => chart.id);
}

describe('measured breakdown charts', () => {
  it('adds nothing when the audit has no split to show', () => {
    expect(ids({})).toEqual([]);
    expect(ids({
      http_status_breakdown: {
        total_urls_checked: 4,
        count_2xx: 4,
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
      click_depth: {
        homepage_url: 'https://example.com/',
        total_pages_analyzed: 4,
        depth_1_count: 4,
        depth_2_count: 0,
        depth_3_count: 0,
        depth_4_plus_count: 0,
        max_click_depth: 1,
        pages_by_depth: {},
        depth_distribution_pct: {},
        high_depth_warning_count: 0,
      },
      crawl_manifest: {
        domain: 'example.com',
        base_url: 'https://example.com',
        total_pages_discovered: 2,
        sitemap_found: false,
        robots_txt_found: false,
        crawl_health: {},
        pages: [
          page({ url: 'https://example.com/', title: 'x'.repeat(55), meta_description: 'x'.repeat(155), h1: ['Home'], word_count: 800, schema_types: ['Organization'], total_images: 2, images_without_alt: 0 }),
          page({ url: 'https://example.com/about', title: 'y'.repeat(55), meta_description: 'y'.repeat(155), h1: ['About'], word_count: 900, schema_types: ['Organization'], total_images: 1, images_without_alt: 0 }),
        ],
      },
      ai_visibility_scorecard: {
        status: 'NOT_MEASURED',
        engines_measured: 0,
        engines_requested: 0,
        queries: 0,
        repeats: 0,
        successful_runs: 0,
        failed_runs: 0,
        citation_accuracy_pct: 88,
        mention_rate_pct: 40,
        citation_rate_pct: 10,
      },
      google_performance: {
        analytics: { state: 'NOT_CONNECTED', sessions: 100, landing_pages: [{ page: '/', sessions: 100 }] },
        search_console: { state: 'NOT_CONNECTED', queries: [{ query: 'crm', clicks: 10 }] },
      },
    })).toEqual([]);
  });

  it('charts response classes, indexation, depth, coverage, length, schema, and alt text when they split', () => {
    const charts = measuredBreakdowns(report({
      http_status_breakdown: {
        total_urls_checked: 5,
        count_2xx: 3,
        count_3xx: 1,
        count_4xx: 1,
        count_5xx: 0,
        status_health_score: 60,
        pages_2xx: [],
        pages_3xx: [],
        pages_4xx: [],
        pages_5xx: [],
        broken_links: [],
        summary: '',
      },
      click_depth: {
        homepage_url: 'https://example.com/',
        total_pages_analyzed: 4,
        depth_1_count: 1,
        depth_2_count: 2,
        depth_3_count: 1,
        depth_4_plus_count: 0,
        max_click_depth: 3,
        pages_by_depth: {},
        depth_distribution_pct: {},
        high_depth_warning_count: 0,
      },
      indexation_intelligence: {
        total_pages_audited: 3,
        crawlable_count: 3,
        indexable_count: 1,
        noindex_count: 1,
        x_robots_blocked_count: 0,
        robots_blocked_count: 1,
        soft_404_count: 0,
        duplicate_count: 0,
        canonical_mismatch_count: 0,
        redirect_count: 0,
        js_only_count: 0,
        high_js_risk_count: 0,
        pages: [
          { url: 'https://example.com/', status_code: 200, crawlable: true, indexable: true, indexed_state: 'INDEXED', canonical_match: true, has_noindex: false, robots_blocked: false, is_soft_404: false, is_duplicate: false, is_redirect: false, is_js_only_content: false, blocked_resources: [], gsc_coverage_state: 'Submitted and indexed' },
          { url: 'https://example.com/old', status_code: 200, crawlable: true, indexable: false, indexed_state: 'UNKNOWN', canonical_match: true, has_noindex: true, robots_blocked: false, is_soft_404: false, is_duplicate: false, is_redirect: false, is_js_only_content: false, blocked_resources: [], gsc_coverage_state: 'Excluded by noindex' },
          { url: 'https://example.com/secret', status_code: 200, crawlable: false, indexable: false, indexed_state: 'UNKNOWN', canonical_match: true, has_noindex: false, robots_blocked: true, is_soft_404: false, is_duplicate: false, is_redirect: false, is_js_only_content: false, blocked_resources: [] },
        ],
        summary: '',
      },
      crawl_manifest: {
        domain: 'example.com',
        base_url: 'https://example.com',
        total_pages_discovered: 3,
        sitemap_found: true,
        robots_txt_found: true,
        crawl_health: {},
        pages: [
          page({ url: 'https://example.com/', title: 'Short', meta_description: 'Tiny', h1: ['Home'], word_count: 120, schema_types: ['Organization', 'WebSite'], total_images: 4, images_without_alt: 1 }),
          page({ url: 'https://example.com/pricing', title: 'Pricing for the platform this year', meta_description: 'z'.repeat(155), h1: [], word_count: 700, schema_types: [], total_images: 2, images_without_alt: 2 }),
          page({ url: 'https://example.com/guide', title: '', meta_description: '', h1: ['Guide', 'Second'], word_count: 0, schema_types: ['Article'], total_images: 0, images_without_alt: 0 }),
        ],
      },
    }));
    const byId = Object.fromEntries(charts.map((chart) => [chart.id, chart]));

    expect(byId.chart_http_status.bars.map((bar) => bar.label)).toEqual(['2xx', '3xx', '4xx']);
    expect(byId.chart_indexation.bars.map((bar) => bar.label)).toEqual(['Indexable', 'Noindex', 'Blocked by robots.txt']);
    expect(byId.chart_search_console_coverage.bars).toHaveLength(2);
    expect(byId.chart_click_depth.bars.map((bar) => bar.label)).toEqual(['1 click', '2 clicks', '3 clicks']);
    expect(byId.chart_onpage_coverage.bars.map((bar) => bar.label)).toEqual([
      'Title present',
      'Title missing',
      'Meta description present',
      'Meta description missing',
      'Schema present',
      'Schema missing',
    ]);
    expect(byId.chart_title_length.bars.length).toBeGreaterThanOrEqual(2);
    expect(byId.chart_title_length.bars.some((bar) => bar.label === 'Under 30 characters')).toBe(true);
    expect(byId.chart_meta_length.bars.map((bar) => bar.value).reduce((sum, value) => sum + value, 0)).toBe(2);
    expect(byId.chart_h1_count.bars.map((bar) => bar.label)).toEqual(['No H1', 'One H1', 'More than one H1']);
    expect(byId.chart_content_length.bars.some((bar) => bar.label === 'No extractable text')).toBe(true);
    expect(byId.chart_schema_types.note).toMatch(/two types/);
    expect(byId.chart_schema_types.bars.map((bar) => bar.label)).toContain('No schema');
    expect(byId.chart_image_alt.bars).toEqual([
      { label: 'Alt text present', value: 3 },
      { label: 'Alt text missing', value: 3 },
    ]);
    expect(ids({ crawl_manifest: report({}).crawl_manifest })).not.toContain('chart_ai_engine_matrix');
  });

  it('charts live rates and connected analytics without inventing accuracy or a grade', () => {
    const charts = measuredBreakdowns(report({
      ai_visibility_scorecard: {
        status: 'MEASURED',
        measurement_kind: 'LIVE_MODEL_API',
        engines_measured: 2,
        engines_requested: 2,
        queries: 6,
        repeats: 2,
        successful_runs: 4,
        failed_runs: 0,
        mention_rate_pct: 50,
        citation_rate_pct: 0,
        citation_accuracy_pct: 99,
        competitor_visibility_pct: 25,
      },
      google_performance: {
        analytics: {
          state: 'MEASURED',
          sessions: 30,
          key_events: 4,
          landing_pages: [
            { page: 'https://example.com/', sessions: 20, key_events: 3 },
            { page: 'https://example.com/pricing', sessions: 10, key_events: 1 },
            { page: 'https://example.com/empty', sessions: 0, key_events: 0 },
          ],
        },
        search_console: {
          state: 'MEASURED',
          queries: [
            { query: 'best crm', clicks: 12, impressions: 100 },
            { query: 'crm pricing', clicks: 4, impressions: 80 },
            { query: 'unused', clicks: 0, impressions: 5 },
          ],
        },
      },
    }));
    const byId = Object.fromEntries(charts.map((chart) => [chart.id, chart]));
    expect(byId.chart_live_visibility_rates.bars).toEqual([
      { label: 'Mention rate', value: 50 },
      { label: 'Citation rate', value: 0 },
      { label: 'Competitor visibility', value: 25 },
    ]);
    expect(byId.chart_live_visibility_rates.unit).toBe('%');
    expect(byId.chart_live_visibility_rates.bars.map((bar) => bar.label).join(' ')).not.toMatch(/accuracy/i);
    expect(byId.chart_ga4_landing_sessions.bars.map((bar) => bar.value)).toEqual([20, 10]);
    expect(byId.chart_ga4_landing_key_events.bars.map((bar) => bar.value)).toEqual([3, 1, 0]);
    expect(byId.chart_gsc_queries.title).toMatch(/clicks/);
    expect(byId.chart_gsc_queries.bars.map((bar) => bar.label)).toEqual(['best crm', 'crm pricing']);
  });

  it('splits a rollup into indexable and not indexable when page rows are absent', () => {
    const chart = measuredBreakdowns(report({
      indexation_intelligence: {
        total_pages_evaluated: 4,
        indexable_count: 3,
      } as ExecutiveReport['indexation_intelligence'],
    })).find((item) => item.id === 'chart_indexation');
    expect(chart?.bars).toEqual([
      { label: 'Indexable', value: 3 },
      { label: 'Not indexable', value: 1 },
    ]);
  });

  it('uses impressions when clicks do not form a comparison', () => {
    const charts = measuredBreakdowns(report({
      google_performance: {
        search_console: {
          state: 'MEASURED',
          queries: [
            { query: 'alpha', clicks: 3, impressions: 40 },
            { query: 'beta', clicks: 0, impressions: 25 },
          ],
        },
      },
    }));
    expect(charts.find((chart) => chart.id === 'chart_gsc_queries')?.title).toMatch(/impressions/);
  });

  it('keeps an unmeasured live run and a key-event-free property off the chart list', () => {
    expect(ids({
      ai_visibility_scorecard: {
        status: 'MEASURED',
        measurement_kind: 'LIVE_MODEL_API',
        engines_measured: 1,
        engines_requested: 1,
        queries: 2,
        repeats: 1,
        successful_runs: 0,
        failed_runs: 2,
        mention_rate_pct: 100,
        citation_rate_pct: 100,
      },
      google_performance: {
        analytics: {
          state: 'MEASURED',
          sessions: 8,
          landing_pages: [
            { page: '/', sessions: 8, key_events: null },
            { page: '/pricing', sessions: 2, key_events: null },
          ],
        },
      },
    }).filter((id) => id.startsWith('chart_live') || id.startsWith('chart_ga4'))).toEqual([
      'chart_ga4_landing_sessions',
    ]);
  });
});
