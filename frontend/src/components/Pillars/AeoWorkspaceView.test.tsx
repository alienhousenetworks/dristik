import React from 'react';
import { describe, expect, it, afterEach } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ExecutiveReport } from '../../types';
import { AeoWorkspaceView } from './AeoWorkspaceView';

const stored = {
  domain: 'acme.example',
  analysis_id: 'a1',
  dynamic_sandbox_evaluations: [
    {
      question_id: 'Q-1',
      facet: 'Pricing, Packaging & Commercial Model',
      generated_question: 'What does Acme charge per cluster?',
      buyer_intent: 'pricing',
      is_answerable: true,
      answerability_status: 'ANSWERABLE',
      crawled_answer: 'Pricing starts at $99 per cluster per month.',
      rag_answer: 'Pricing starts at $99 per cluster per month.',
      source_section: 'Pricing Plans',
      citability_score: 8,
      projected_patch_gain: 0,
      grounding_ratio: 0.91,
    },
    {
      question_id: 'Q-2',
      facet: 'Trust',
      generated_question: 'Where is Acme headquartered?',
      buyer_intent: 'location',
      is_answerable: false,
      answerability_status: 'UNANSWERABLE',
      crawled_answer: 'The crawled pages do not state a headquarters.',
      rag_answer: 'The crawled pages do not state a headquarters.',
      citability_score: 2,
      projected_patch_gain: 0,
    },
  ],
} as ExecutiveReport;

describe('AeoWorkspaceView questions', () => {
  afterEach(() => cleanup());

  it('shows every stored question with its segment and RAG answer', () => {
    render(<AeoWorkspaceView report={stored} />);

    fireEvent.click(screen.getByRole('tab', { name: 'Questions (2)' }));

    expect(screen.getAllByText('What does Acme charge per cluster?').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Where is Acme headquartered?').length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/Pricing, Packaging & Commercial Model · Pricing Plans/).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/Segment not stored|Trust/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Pricing starts at \$99 per cluster per month\./).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/do not state a headquarters/).length).toBeGreaterThan(0);
    expect(screen.queryByText('Identity, Category & Core Mission')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Answerability Lab' }));

    expect(screen.getAllByText('What does Acme charge per cluster?').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/91% grounding/).length).toBeGreaterThan(0);
    expect(screen.getByText('Grounding not measured')).toBeInTheDocument();
    expect(screen.queryByText(/sonic pulse/)).not.toBeInTheDocument();
    expect(screen.queryByText(/₹499/)).not.toBeInTheDocument();
  });

  it('does not invent questions, segments, or RAG answers when none were stored', () => {
    render(<AeoWorkspaceView report={{ domain: 'acme.example' } as ExecutiveReport} />);

    fireEvent.click(screen.getByRole('tab', { name: 'Questions (0)' }));
    expect(screen.getByText(/No questions were stored on this audit/)).toBeInTheDocument();
    expect(screen.queryByText('Identity, Category & Core Mission')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Answerability Lab' }));
    expect(screen.getByText(/No RAG answers were stored/)).toBeInTheDocument();
    expect(screen.queryByText(/sonic pulse/)).not.toBeInTheDocument();
    expect(screen.queryByText(/₹499/)).not.toBeInTheDocument();
  });
});
