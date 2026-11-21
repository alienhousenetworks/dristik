import React from 'react';
import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { CroWorkspaceView } from '../CroWorkspaceView';

vi.mock('../../../services/croApi', async () => {
  const actual = await vi.importActual<any>('../../../services/croApi');
  return {
    ...actual,
    croApi: {
      ...actual.croApi,
      listAudits: vi.fn().mockResolvedValue({ items: [], count: 0 }),
      listConnectors: vi.fn().mockResolvedValue({
        connectors: [
          {
            connector_id: 'ga4',
            provider: 'Google Analytics 4',
            category: 'analytics',
            priority_tier: 1,
            connection_status: 'not_connected',
            supported_data: ['events', 'funnels'],
            available_capabilities: [],
            unsupported_or_limited: ['No raw session video'],
            auth_status: 'unauthenticated',
          },
        ],
      }),
    },
  };
});

const mockReport: any = {
  report_id: 'rep_cro_1',
  analysis_id: 'anl_cro_1',
  domain: 'acme-saas.com',
  website_url: 'https://acme-saas.com/',
  generated_at: '2026-11-21T12:00:00Z',
  business_profile: {
    business_model: 'saas',
    primary_cta: 'Start Free Trial',
    target_audience: 'B2B Operations Teams',
  },
  cro_audit: {
    overall_cro_score: 76.5,
    cro_grade: 'B',
    value_prop: {
      hero_headline: 'Automate Finance Operations',
      clarity_grade: 'B',
      observations: ['Clear category'],
    },
    cta_analysis: {
      total_ctas_detected: 4,
      high_intent_count: 2,
      exploratory_count: 1,
      passive_generic_count: 1,
      hero_cta_text: 'Start Free Trial',
      ctas: [
        {
          page_url: 'https://acme-saas.com/',
          cta_text: 'Submit',
          element_type: 'button',
          intent_category: 'PASSIVE_GENERIC',
          placement_zone: 'HERO',
        },
      ],
    },
    social_proof: { has_privacy_policy: true, has_terms_of_service: true, total_testimonials: 2, client_logos_detected: 4 },
    intelligence: {
      business_model: 'saas',
      journey_stages: [
        { stage_id: 'landing', stage_name: 'Landing & Value Hook', status: 'OBSERVED', matched_urls: ['https://acme-saas.com/'] },
      ],
      experiment_proposals: [
        {
          experiment_id: 'EXP-ACME-01',
          title: 'CTA Action Microcopy Test',
          hypothesis: 'If we replace Submit with Start Free Trial, qualified signups improve.',
          primary_metric: 'Primary Conversion Rate',
          guardrail_metrics: ['Qualified Lead Rate'],
          sample_size_per_variant: 4200,
          total_required_sample_size: 8400,
          minimum_duration_days: 14,
        },
      ],
    },
  },
  findings: [
    {
      finding_id: 'CRO-001',
      title: 'Passive CTA Copy on Hero',
      description: 'Button uses generic Submit label.',
      category: 'UX_CONVERSION',
      severity: 'HIGH',
      recommendation: 'Use Start Free Trial instead of Submit.',
      evidence: [{ url: 'https://acme-saas.com/' }],
      evidence_refs: ['ev_001'],
    },
  ],
  page_reports: [
    { url: 'https://acme-saas.com/', status_code: 200, title: 'Acme SaaS', h1: ['Automate Finance Operations'], word_count: 650, forms_count: 1 },
  ],
};

describe('CroWorkspaceView Enterprise Workspace', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders the 3 separated scorecards and keeps disconnected business performance Unavailable', () => {
    render(<CroWorkspaceView report={mockReport} analysisId="anl_cro_1" />);
    expect(screen.getByText('1. CRO Experience Score')).toBeTruthy();
    expect(screen.getByText('2. Conversion Measurement Score')).toBeTruthy();
    expect(screen.getByText('3. Measured Business Performance')).toBeTruthy();
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
  });

  it('displays dual Technical vs Behavioral status badges in Journey Explorer', () => {
    render(<CroWorkspaceView report={mockReport} analysisId="anl_cro_1" />);
    fireEvent.click(screen.getByRole('tab', { name: /Journeys/i }));
    expect(screen.getAllByText(/Technical status/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Behavioral status/i).length).toBeGreaterThan(0);
  });

  it('requires user approval in Landing & Copy Studio and separates 4 verification outcomes in Remediation', () => {
    render(<CroWorkspaceView report={mockReport} analysisId="anl_cro_1" />);
    fireEvent.click(screen.getByRole('tab', { name: /Landing & Copy/i }));
    const approveBtn = screen.getByRole('button', { name: /Approve Copy Proposal/i });
    fireEvent.click(approveBtn);
    expect(screen.getByRole('button', { name: /Approved for Implementation/i })).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Remediation & Verify/i }));
    fireEvent.click(screen.getByRole('button', { name: /Verification Queue/i }));
    expect(screen.getByText(/1\. Implementation/i)).toBeTruthy();
    expect(screen.getByText(/2\. Functional/i)).toBeTruthy();
    expect(screen.getByText(/3\. Analytics Event/i)).toBeTruthy();
    expect(screen.getByText(/4\. Business Outcome/i)).toBeTruthy();
  });

  it('exposes all 14 report profiles in Monitoring & 14 Reports', () => {
    render(<CroWorkspaceView report={mockReport} analysisId="anl_cro_1" />);
    fireEvent.click(screen.getByRole('tab', { name: /Monitoring & 14 Reports/i }));
    expect(screen.getByText(/14 Profiles · 65-Section Book/i)).toBeTruthy();
  });
});
