import React from 'react';
import { describe, expect, it } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { SeoExecutiveDashboard } from './SeoExecutiveDashboard';
import { CrawlExplorerView } from './CrawlExplorerView';
import { UrlInspectionDrawer } from './UrlInspectionDrawer';
import { SeoFindingsWorkspace } from './SeoFindingsWorkspace';
import { SeoIntelligenceWorkspace } from './SeoIntelligenceWorkspace';
import { ExecutiveReport, Finding } from '../../../types';

const mockReport: ExecutiveReport = {
  report_id: 'rep_001',
  analysis_id: 'an_001',
  website_url: 'https://example.com/',
  domain: 'example.com',
  generated_at: '2026-11-21T10:00:00Z',
  business_profile: {
    company_name: 'Example Corp',
    domain: 'example.com',
    industry: 'Technology',
  } as any,
  scores: {
    overall_score: 74,
    category_scores: {
      TECHNICAL_SEO: { score: 74, label: 'Good' },
    },
  } as any,
  story_summary: 'Comprehensive SEO analysis for Example Corp.',
  what_site_gets_right: ['Fast server response'],
  what_is_holding_it_back: ['Missing canonical tags'],
  primary_strategic_opportunity: 'Implement schema markup across all pages.',
  consultant_advice_what_to_ignore: 'Avoid micro-optimizing image compression further.',
  three_way_comparison: {} as any,
  ai_search_matrix: [],
  findings: [
    {
      finding_id: 'SEO_FND_001',
      category: 'TECHNICAL_SEO',
      severity: 'CRITICAL',
      title: 'Canonical URL Tag Mismatch',
      description: 'Canonical tag points to non-existent URL.',
      recommendation: 'Update canonical link tag to self-reference.',
      confidence: 0.95,
      confidence_label: 'Certain',
      impact: 9,
      effort: 2,
      priority: 1,
      verification_status: 'VERIFIED',
      evidence: [],
      evidence_refs: [],
    } as Finding,
    {
      finding_id: 'SEO_FND_002',
      category: 'ON_PAGE_SEO',
      severity: 'HIGH',
      title: 'Missing Primary H1 Tag',
      description: 'Homepage has no H1 element in rendered DOM.',
      recommendation: 'Add descriptive H1 tag.',
      confidence: 0.9,
      confidence_label: 'Certain',
      impact: 7,
      effort: 1,
      priority: 2,
      verification_status: 'VERIFIED',
      evidence: [],
      evidence_refs: [],
    } as Finding,
  ],
  code_patches: [],
  roadmap_7_days: [],
  roadmap_30_days: [],
  roadmap_90_days: [],
  telemetry: {} as any,
  crawl_summary: {},
  agent_execution_trace: [],
  crawl_manifest: {
    manifest_id: 'cm_001',
    pages: [
      {
        url: 'https://example.com/',
        title: 'Example Homepage',
        meta_description: 'Welcome to Example Corp.',
        status_code: 200,
        canonical_url: 'https://example.com/',
        h1: ['Welcome to Example'],
        h2: ['Products', 'Services'],
        schema_types: ['Organization'],
        word_count: 500,
        internal_links_count: 10,
        external_links_count: 2,
      },
    ],
  } as any,
};

describe('SeoExecutiveDashboard', () => {
  it('renders overall score, trust vectors, and reconciled taxonomy', () => {
    render(
      <SeoExecutiveDashboard
        report={mockReport}
        seoFindings={mockReport.findings}
        onNavigateTab={() => {}}
      />
    );

    expect(screen.getByText('Canonical SEO Health Score')).toBeDefined();
    expect(screen.getByText('Audit Coverage')).toBeDefined();
    expect(screen.getByText('Evidence Quality')).toBeDefined();
    expect(screen.getByText('Technical & Crawlability')).toBeDefined();
    expect(screen.getByText('Top Strategic Remediations')).toBeDefined();
  });
});

describe('CrawlExplorerView', () => {
  it('renders URL table and allows filtering', () => {
    render(<CrawlExplorerView report={mockReport} />);

    expect(screen.getByText('Crawl Explorer')).toBeDefined();
    expect(screen.getByText('https://example.com/')).toBeDefined();
    expect(screen.getByText('Example Homepage')).toBeDefined();
  });

  it('shows stored image and video URLs on the images tab', () => {
    cleanup();
    render(
      <UrlInspectionDrawer
        page={{
          url: 'https://example.com/',
          status_code: 200,
          total_images: 2,
          h1: ['Welcome to Example'],
          h2: [],
          schema_types: [],
          image_assets: [
            { url: 'https://cdn.example.com/hero.webp', has_alt: true, alt_text: 'Hero', is_empty_alt: false },
          ],
          video_assets: [
            { url: 'https://www.youtube.com/embed/abc', kind: 'iframe', has_source: true },
          ],
        }}
        report={mockReport}
        onClose={() => {}}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /Images/ }));
    expect(screen.getByText('https://cdn.example.com/hero.webp')).toBeDefined();
    expect(screen.getByText('https://www.youtube.com/embed/abc')).toBeDefined();
    expect(screen.getByText('Has ALT')).toBeDefined();
    expect(screen.queryByText('No image asset records stored for this URL.')).toBeNull();
  });
});

describe('SeoFindingsWorkspace', () => {
  it('renders findings list and toggles to clustered view', () => {
    render(
      <SeoFindingsWorkspace
        report={mockReport}
        seoFindings={mockReport.findings}
      />
    );

    expect(screen.getByText('SEO Findings & Remediation Workspace')).toBeDefined();
    expect(screen.getAllByText('Canonical URL Tag Mismatch').length).toBeGreaterThan(0);

    // Toggle to clustered view
    const clusterBtn = screen.getByText('Root-Cause Clusters');
    fireEvent.click(clusterBtn);
    expect(screen.getByText('TECHNICAL SEO')).toBeDefined();
  });
});

describe('SeoIntelligenceWorkspace', () => {
  it('renders keyword table and generates content brief', () => {
    render(<SeoIntelligenceWorkspace report={mockReport} />);

    expect(screen.getByText('SEO Intelligence & Content Workspace')).toBeDefined();
    expect(screen.getByText('Keyword Query')).toBeDefined();

    // Switch to brief
    const briefTab = screen.getByText('Content Briefs');
    fireEvent.click(briefTab);
    expect(screen.getByText(/Content Optimization & Editorial Brief/i)).toBeDefined();
  });
});
