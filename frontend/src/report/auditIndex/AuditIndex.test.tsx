import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ExecutiveReport } from '../../types';
import { AuditIndex } from './AuditIndex';

describe('AuditIndex', () => {
  it('renders every part and keeps an unconnected audit from looking complete', () => {
    render(<AuditIndex report={{} as ExecutiveReport} />);

    expect(screen.getByRole('heading', { name: /Forecasting and opportunity modeling/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /AI search visibility and citation intelligence/ })).toBeInTheDocument();
    expect(screen.getByText('No traffic, ranking, or revenue forecast is produced. Nothing in this audit is a promised gain.')).toBeInTheDocument();
    expect(screen.getAllByText('Data unavailable').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Not tested').length).toBeGreaterThan(0);
    expect(screen.queryByText(/score:\s*0/)).not.toBeInTheDocument();
  });
});
