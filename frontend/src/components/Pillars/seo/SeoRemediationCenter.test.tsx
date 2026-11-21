import React from 'react';
import { afterEach, describe, expect, it, vi, beforeEach } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { SeoRemediationCenter } from './SeoRemediationCenter';
import { seoApi, SeoRemediationTask } from '../../../services/seoApi';

const sampleTasks: SeoRemediationTask[] = [
  {
    task_id: 'REM_001',
    finding_id: 'FND_001',
    root_cause_id: 'RC_TITLE',
    fix_type: 'CODE_LEVEL',
    priority: 'P0',
    problem: 'Missing <title> tag on product template',
    root_cause: 'Shared layout omits dynamic title metadata',
    affected_scope: { total_urls: 3, sample_urls: ['https://example.com/p/1'], template_pattern: '/p/*' },
    seo_impact: 'Poor SERP click-through rate',
    business_impact: 'Lower organic conversions',
    recommended_fix: 'Render unique <title> per route',
    implementation: {
      platform: 'NEXTJS_REACT',
      target_file_pattern: 'app/**/page.tsx',
      code_diff_snippet: '+ export const metadata = { title: "Product" };',
      instructions: 'Add metadata export.',
      stack_confidence: 'DETECTED',
    },
    owner: 'Frontend Developer',
    department: 'Engineering',
    dependencies: ['Deploy to staging'],
    effort: '30 minutes',
    acceptance_criteria: 'Document renders non-empty <title>.',
    verification_protocol: 'Re-crawl target URL and inspect <title>.',
    evidence_refs: ['EV_001'],
    status: 'REMEDIATION_PLANNED',
    approval_status: 'PENDING_APPROVAL',
    verification_status: 'UNVERIFIED',
  },
];

describe('SeoRemediationCenter', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders views and runs real backend live verification without fake timers', async () => {
    const verifySpy = vi.spyOn(seoApi, 'verifyTask').mockResolvedValue({
      task_id: 'REM_001',
      finding_id: 'FND_001',
      target_url: 'https://example.com/p/1',
      passed: true,
      verification_status: 'VERIFIED_FIXED',
      check_summary: 'Live title check passed (34 chars).',
      comparison_rows: [
        { dimension: 'Title', before: '(missing)', after: 'Product | Example' },
      ],
      verified_at: '2026-11-22T00:00:00Z',
    });

    const onUpdated = vi.fn();
    render(<SeoRemediationCenter auditId="audit_123" tasks={sampleTasks} onTasksUpdated={onUpdated} />);

    expect(screen.getByText('SEO Remediation & Verification Center')).toBeInTheDocument();
    expect(screen.getByText('Missing <title> tag on product template')).toBeInTheDocument();

    // Switch to Verification Queue
    fireEvent.click(screen.getByText('Verification Queue (1)'));
    const verifyBtn = screen.getByRole('button', { name: /Run Live Retest/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(verifySpy).toHaveBeenCalledWith('audit_123', 'REM_001', {
        target_url: 'https://example.com/p/1',
        rule_id: 'Missing <title> tag on product template',
      });
      expect(screen.getByText(/VERIFIED_FIXED/)).toBeInTheDocument();
      expect(screen.getByText('Product | Example')).toBeInTheDocument();
      expect(onUpdated).toHaveBeenCalled();
    });
  });

  it('displays roadmap and priority matrix views cleanly', () => {
    render(<SeoRemediationCenter auditId="audit_123" tasks={sampleTasks} />);

    fireEvent.click(screen.getByText('Priority Matrix'));
    expect(screen.getByText('Quick Wins & Critical (P0 / P1)')).toBeInTheDocument();

    fireEvent.click(screen.getByText('7/30/60/90 Roadmap'));
    expect(screen.getByText('7 Days (P0 Blockers)')).toBeInTheDocument();
  });
});
