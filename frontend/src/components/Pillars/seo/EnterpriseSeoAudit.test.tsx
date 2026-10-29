import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { EnterpriseSeoAssessment, EnterpriseSeoPanel } from './EnterpriseSeoAudit';

const assessment: EnterpriseSeoAssessment = {
  report_stage: 'preliminary',
  coverage: {
    statement: 'Checked 2 of 100 discovered URLs. This is a sample. It is not a complete site audit.',
    sampling_status: 'SAMPLED_AUDIT',
    urls_discovered: 100,
    urls_crawled: 2,
  },
  scores: [
    {
      category: 'SEO',
      score: null,
      status: 'not_scored',
      note: 'This module does not calculate a score.',
    },
  ],
  chapters: [
    {
      chapter: 22,
      title: 'Organic search performance analytics',
      status: 'DATA_UNAVAILABLE',
      summary: 'Search Console is not connected.',
      subchapters: [
        {
          subchapter_id: '22.1',
          title: 'Search impressions, clicks, CTR, and position',
          status: 'DATA_UNAVAILABLE',
          note: 'No clicks were invented.',
        },
      ],
    },
  ],
  agents: [
    {
      agent_id: 'seo.search_console.v1',
      status: 'unavailable',
      coverage_note: 'Search Console is not connected.',
    },
  ],
  findings: [],
  cards: [],
  limitations: ['AEO, GEO, and CRO are separate modules and are not scored here.'],
};

describe('EnterpriseSeoPanel', () => {
  it('shows the sample and leaves a missing score unmeasured', () => {
    render(<EnterpriseSeoPanel assessment={assessment} />);

    expect(screen.getByText(/Checked 2 of 100 discovered URLs/)).toBeInTheDocument();
    expect(screen.getByText('Not scored')).toBeInTheDocument();
    expect(screen.getAllByText('Data unavailable').length).toBeGreaterThan(0);
    expect(screen.getByText(/No validated finding was published/)).toBeInTheDocument();
    expect(screen.queryByText(/^0$/)).not.toBeInTheDocument();
    expect(screen.queryByText('100')).not.toBeInTheDocument();
    expect(screen.getByText(/1 specialist is unavailable because its source was not stored/)).toBeInTheDocument();
    expect(screen.queryByText(/AI specialist loaded a versioned prompt/)).not.toBeInTheDocument();
  });

  it('does not describe an unloaded AI judgment as missing source data', () => {
    render(<EnterpriseSeoPanel assessment={{
      ...assessment,
      diagnostic_summary: 'SEO analysis only. No traffic figure was estimated.',
      deferred_modules: ['Content writing', 'Code remediation'],
      agents: [
        ...assessment.agents,
        {
          agent_id: 'seo.ai.content_completeness.v1',
          status: 'unavailable',
          coverage_note: 'The versioned prompt was loaded. No model completion ran.',
          error_code: 'MODEL_NOT_RUN',
          prompt_version: '1.0.0',
        },
      ],
    }} />);

    expect(screen.getByText(/1 AI specialist loaded a versioned prompt and did not publish a judgment/)).toBeInTheDocument();
    expect(screen.getByText(/Not executed in this phase: Content writing, Code remediation/)).toBeInTheDocument();
    expect(screen.getByText(/No traffic figure was estimated/)).toBeInTheDocument();
  });
});
