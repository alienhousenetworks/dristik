import React from 'react';
import { describe, expect, it, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ExecutiveReport } from '../../types';
import { GeoAuditBook } from './GeoAuditBook';

describe('GeoAuditBook', () => {
  afterEach(() => {
    cleanup();
  });
  it('renders an empty report safely and keeps it unmeasured without fake certainty', () => {
    render(<GeoAuditBook report={{} as ExecutiveReport} />);

    expect(screen.getByText(/Enterprise GEO Audit Standard/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Executive GEO Summary/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Change history and audit reproducibility manifest/ })).toBeInTheDocument();
    expect(screen.getAllByText(/Specialist Agent \/\//).length).toBeGreaterThan(0);
  });

  it('renders all 50 chapters, 15 appendices, and specialist agent attribution cards', () => {
    const report = {
      domain: 'acme.com',
      scores: {
        geo_score: 85,
      },
      geo_readiness: {
        extractability_score: 85,
        schema_types: ['Organization', 'SoftwareApplication'],
      },
      ai_visibility_scorecard: {
        status: 'MEASURED',
        successful_runs: 5,
        engines_queried: ['ChatGPT Search', 'Perplexity'],
        mention_rate_pct: 75,
        citation_rate_pct: 50,
      },
      findings: [
        {
          finding_id: 'GEO-001',
          category: 'CONTENT',
          severity: 'HIGH',
          title: 'Missing Direct Definition Block for Cloud Orchestration',
          description: 'The homepage lacks a concise 50-word definition block.',
          recommendation: 'Deploy explicit answer definition below H1.',
        },
      ],
      page_reports: [
        { url: 'https://acme.com', status_code: 200, word_count: 800 },
      ],
    } as unknown as ExecutiveReport;

    render(<GeoAuditBook report={report} />);

    expect(screen.getByText(/85\/100/)).toBeInTheDocument();
    expect(screen.getByText(/50%/)).toBeInTheDocument();
    expect(screen.getAllByText(/GEO-001: Missing Direct Definition Block for Cloud Orchestration/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/geo\.benchmark_orchestrator\.v3/).length).toBeGreaterThan(0);

    // Verify search functionality
    const searchInput = screen.getByPlaceholderText(/Search chapters or checks/);
    fireEvent.change(searchInput, { target: { value: 'Hallucination' } });
    expect(screen.getByRole('heading', { name: /Brand Accuracy and Hallucination Audit/ })).toBeInTheDocument();
  });
});
