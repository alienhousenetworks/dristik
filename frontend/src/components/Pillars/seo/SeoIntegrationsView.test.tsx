import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SeoIntegrationsView } from './SeoIntegrationsView';

describe('SeoIntegrationsView', () => {
  it('renders Google Search Console and analytics connector cards', () => {
    render(<SeoIntegrationsView />);

    expect(screen.getByText('SEO Integrations & Connectors Hub')).toBeDefined();
    expect(screen.getByText('Google Search Console')).toBeDefined();
    expect(screen.getByText('Google Analytics 4')).toBeDefined();
    expect(screen.getByText('PageSpeed Insights & CrUX')).toBeDefined();
    expect(screen.getByText('DataForSEO Backlink Intelligence')).toBeDefined();
  });

  it('allows connecting an unconfigured integration', async () => {
    render(<SeoIntegrationsView />);

    const connectButtons = screen.getAllByText('Connect Integration');
    expect(connectButtons.length).toBeGreaterThan(0);

    fireEvent.click(connectButtons[0]);
    expect(screen.getByText('Connecting...')).toBeDefined();
  });
});
