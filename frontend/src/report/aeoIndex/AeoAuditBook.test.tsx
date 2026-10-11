import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ExecutiveReport } from '../../types';
import { AeoAuditBook } from './AeoAuditBook';

describe('AeoAuditBook', () => {
  it('keeps an empty report unmeasured', () => {
    render(<AeoAuditBook report={{} as ExecutiveReport} />);

    expect(screen.getByRole('heading', { name: /AEO opportunity and forecasting model/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Glossary/ })).toBeInTheDocument();
    expect(screen.getAllByText('Not tested').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Data unavailable').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No forecast is produced/).length).toBeGreaterThan(0);
    expect(screen.getByText(/not a zero and not a pass/)).toBeInTheDocument();
    expect(screen.queryByText(/0 of 0/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Citation rate is 0/)).not.toBeInTheDocument();
    expect(screen.queryByText(/score:\s*0/)).not.toBeInTheDocument();
  });

  it('quotes an assessed question and does not treat a mention as a recommendation', () => {
    const report = {
      domain: 'example.com',
      dynamic_sandbox_evaluations: [
        {
          question_id: 'Q-001',
          facet: 'Pricing',
          generated_question: 'What does Example Corp charge for onboarding?',
          buyer_intent: 'pricing',
          is_answerable: false,
          answerability_status: 'UNANSWERABLE',
          crawled_answer: 'The crawled pages do not state a price.',
          citability_score: 5,
          projected_patch_gain: 0.3,
        },
      ],
      ai_visibility_scorecard: {
        successful_runs: 4,
        engines_queried: ['chatgpt'],
        mention_rate_pct: 25,
        citation_rate_pct: null,
        surfaces_not_queried: ['Google AI Overviews', 'Google AI Mode', 'Bing Copilot'],
      },
    } as ExecutiveReport;

    render(<AeoAuditBook report={report} />);

    expect(screen.getAllByText(/What does Example Corp charge for onboarding\?/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0 of 1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Brand recommendation rate was not measured/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/25%/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/0\.30/)).not.toBeInTheDocument();
    expect(screen.queryByText(/0\.3%/)).not.toBeInTheDocument();
  });
});
