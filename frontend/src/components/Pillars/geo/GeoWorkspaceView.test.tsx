import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { GeoWorkspaceView } from '../GeoWorkspaceView';
import { ExecutiveReport } from '../../../types';

const mockReport: ExecutiveReport = {
  report_id: 'rep_geo_1',
  analysis_id: 'anl_geo_1',
  domain: 'acmeflow.io',
  website_url: 'https://acmeflow.io/',
  generated_at: '2026-11-22T00:00:00Z',
  story_summary: 'AcmeFlow GEO baseline.',
  findings: [
    {
      finding_id: 'GEO-001',
      title: 'Missing Organization schema on homepage',
      description: 'Homepage does not declare Organization JSON-LD.',
      category: 'GEO',
      severity: 'HIGH',
      recommendation: 'Publish verified Organization JSON-LD.',
      evidence: [{ url: 'https://acmeflow.io/', snippet: 'No JSON-LD found' }],
      evidence_refs: ['ev_1'],
    } as any,
  ],
  page_reports: [
    {
      url: 'https://acmeflow.io/',
      title: 'AcmeFlow — Workflow Automation',
      status_code: 200,
      word_count: 420,
      h1: ['AcmeFlow Automation'],
      schema_types: [],
      body_text: 'AcmeFlow automates lead routing and billing workflows for B2B teams.',
    } as any,
  ],
  business_profile: {
    business_name: 'AcmeFlow',
    industry: 'workflow automation',
    products: ['AcmeFlow Core'],
    competitors: ['Zapier'],
  } as any,
  geo_readiness: {
    extractability_score: 74,
    questions: [],
    dimensions: [],
  } as any,
  ai_visibility_scorecard: {
    status: 'NOT_MEASURED',
    not_measured_reason: 'No AI API credentials configured.',
    engines_queried: [],
    surfaces_not_queried: ['ChatGPT', 'Perplexity'],
    observatory_records: [],
  } as any,
  ai_search_matrix: [
    { query: 'What are the best workflow automation tools?', question_type: 'category_discovery' } as any,
    { query: 'What does AcmeFlow offer?', question_type: 'brand_discovery' } as any,
  ],
} as any;

describe('Enterprise GeoWorkspaceView', () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' }),
        text: async () => '',
      }),
    );
  });

  it('renders separated Dual GEO Scorecards and marks unconfigured Observed Visibility honestly (never 0%)', () => {
    render(<GeoWorkspaceView report={mockReport} analysisId="anl_geo_1" />);
    expect(screen.getByText(/1\. Observed GEO Performance/i)).toBeTruthy();
    expect(screen.getByText(/2\. GEO Readiness & Optimization/i)).toBeTruthy();
    expect(screen.getAllByText(/Unmeasured/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/NOT_CONFIGURED/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Platform-Specific GEO Scorecards/i)).toBeTruthy();
  });

  it('navigates across Prompt Intelligence, Prompt Test Lab, Citations, Brand & Entities, Verification, and 10 Report Profiles', () => {
    render(<GeoWorkspaceView report={mockReport} analysisId="anl_geo_1" />);

    fireEvent.click(screen.getByRole('tab', { name: /Prompts \(2\)/i }));
    expect(screen.getByText(/Prompt Intelligence & Versioned Test Suite/i)).toBeTruthy();
    expect(screen.getByText(/^Non-Branded \(1\)$/i)).toBeTruthy();
    expect(screen.getByText(/^Branded \(1\)$/i)).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Prompt Test Lab/i }));
    expect(screen.getByText(/Side-by-Side Prompt Test Lab/i)).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Citations \(0\)/i }));
    expect(screen.getByText(/1\. Citation Explorer/i)).toBeTruthy();
    expect(screen.getByText(/2\. Citation Source Graph/i)).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Brand & Entities/i }));
    expect(screen.getByText(/Brand Knowledge Profile & Entity Consistency/i)).toBeTruthy();
    expect(screen.getByText(/Approve Official Fact/i)).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Verification/i }));
    expect(screen.getByText(/Independent GEO Verification Queue/i)).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Reports \(10 Profiles\)/i }));
    expect(screen.getByText(/GEO Executive Brief/i)).toBeTruthy();
    expect(screen.getByText(/Complete GEO Audit Book/i)).toBeTruthy();
    expect(screen.getByText(/GEO Evidence Appendix/i)).toBeTruthy();
  });
});
