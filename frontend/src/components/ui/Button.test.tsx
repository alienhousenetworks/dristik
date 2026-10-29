import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { Button } from './primitives';

describe('Button', () => {
  it('exposes the accessible name and a loading state', () => {
    render(<Button loading>Save audit</Button>);
    const button = screen.getByRole('button', { name: 'Save audit' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });
});