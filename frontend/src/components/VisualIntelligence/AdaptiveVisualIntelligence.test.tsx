import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ExecutiveReport } from '../../types';
import { AdaptiveVisualIntelligence } from './AdaptiveVisualIntelligence';

describe('AdaptiveVisualIntelligence extra charts', () => {
  it('renders a measured response-class chart and prints percents for live rates', () => {
    const report = {
      domain: 'example.com',
      visual_intelligence: {
        ai_rationale: 'Charts from this audit only.',
        audit_case_profile: 'Measured sample',
        selected_visualizations: [],
        spotlight_metrics: [],
        generated_at: '2026-10-11',
      },
      http_status_breakdown: {
        total_urls_checked: 3,
        count_2xx: 2,
        count_3xx: 0,
        count_4xx: 1,
        count_5xx: 0,
        status_health_score: 70,
        pages_2xx: [],
        pages_3xx: [],
        pages_4xx: [],
        pages_5xx: [],
        broken_links: [],
        summary: '',
      },
      ai_visibility_scorecard: {
        status: 'MEASURED',
        measurement_kind: 'LIVE_MODEL_API',
        engines_measured: 2,
        engines_requested: 2,
        queries: 4,
        repeats: 1,
        successful_runs: 2,
        failed_runs: 0,
        mention_rate_pct: 40,
        citation_rate_pct: 10,
        citation_accuracy_pct: 99,
      },
    } as unknown as ExecutiveReport;

    render(<AdaptiveVisualIntelligence report={report} />);

    expect(screen.getByRole('heading', { name: 'Response classes' })).toBeInTheDocument();
    expect(screen.getByText('2xx')).toBeInTheDocument();
    expect(screen.getByText('4xx')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Live answer rates' })).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText('10%')).toBeInTheDocument();
    expect(screen.queryByText('99%')).not.toBeInTheDocument();
    expect(screen.getAllByText(/Citation accuracy is omitted/).length).toBeGreaterThan(0);
  });
});
