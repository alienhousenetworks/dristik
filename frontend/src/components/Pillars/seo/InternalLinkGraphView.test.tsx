import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InternalLinkGraphView } from './InternalLinkGraphView';
import { ExecutiveReport } from '../../../types';

const mockReport: ExecutiveReport = {
  report_id: 'rep_graph_01',
  website_url: 'https://example.com/',
  domain: 'example.com',
  generated_at: '2026-11-21T10:00:00Z',
  business_profile: {
    company_name: 'Example Graph Corp',
    domain: 'example.com',
  } as any,
  scores: { overall_score: 80 } as any,
  story_summary: 'Internal linking test report',
  what_site_gets_right: [],
  what_is_holding_it_back: [],
  primary_strategic_opportunity: '',
  consultant_advice_what_to_ignore: '',
  three_way_comparison: {} as any,
  ai_search_matrix: [],
  findings: [],
  code_patches: [],
  roadmap_7_days: [],
  roadmap_30_days: [],
  roadmap_90_days: [],
  telemetry: {} as any,
  crawl_summary: {},
  agent_execution_trace: [],
  crawl_manifest: {
    manifest_id: 'cm_002',
    pages: [
      {
        url: 'https://example.com/',
        title: 'Example Homepage',
        status_code: 200,
        internal_links: ['https://example.com/products', 'https://example.com/blog'],
        word_count: 700,
      },
      {
        url: 'https://example.com/products',
        title: 'Product Catalog',
        status_code: 200,
        internal_links: ['https://example.com/'],
        word_count: 500,
      },
      {
        url: 'https://example.com/blog',
        title: 'Blog Resource Hub',
        status_code: 200,
        internal_links: ['https://example.com/'],
        word_count: 900,
      },
      {
        url: 'https://example.com/orphan-guide',
        title: 'Orphan Guide Page',
        status_code: 200,
        internal_links: [],
        word_count: 350,
      },
    ],
  } as any,
};

describe('InternalLinkGraphView', () => {
  it('renders graph visualization, rings, and summary bar', () => {
    render(<InternalLinkGraphView report={mockReport} />);

    expect(screen.getByText('Internal Linking Visual Explorer')).toBeDefined();
    expect(screen.getByText('Architecture Overview')).toBeDefined();
    expect(screen.getByText('Depth 1')).toBeDefined();
    expect(screen.getByText('Depth 2')).toBeDefined();
  });

  it('allows clicking a node to inspect its link dossier drawer', () => {
    render(<InternalLinkGraphView report={mockReport} />);

    // Click on Homepage node text
    const nodeText = screen.getAllByText('Example Homepage')[0];
    fireEvent.click(nodeText);

    // The Link Dossier drawer opens showing inlinks/outlinks tabs
    expect(screen.getByText(/All Discovered Inbound References/i)).toBeDefined();
    expect(screen.getByText(/Open Full 12-Tab URL Inspection/i)).toBeDefined();

    // Switch to Link Suggestions tab
    const sugTab = screen.getByText(/Link Suggestions/i);
    fireEvent.click(sugTab);
    expect(screen.getByText(/Recommended Links to Add/i)).toBeDefined();
  });
});
