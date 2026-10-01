import { describe, expect, it } from 'vitest';
import { parseNavigation, tabMatches } from './navigation';

describe('navigation', () => {
  it('reads the view, token, and audit id from the hash', () => {
    const parsed = parseNavigation({ hash: '#/reset?token=abc', search: '' }, null);
    expect(parsed.view).toBe('reset');
    expect(parsed.token).toBe('abc');
  });

  it('falls back to home for an unknown hash and keeps a stored audit', () => {
    const parsed = parseNavigation({ hash: '#/nope', search: '' }, 'audit-1');
    expect(parsed.view).toBe('home');
    expect(parsed.analysisId).toBe('audit-1');
  });

  it('prefers the query audit id', () => {
    const parsed = parseNavigation({ hash: '', search: '?analysis_id=from-query' }, 'stored');
    expect(parsed.view).toBe('home');
    expect(parsed.analysisId).toBe('from-query');
  });

  it('treats legacy tab ids as their current section', () => {
    expect(tabMatches('ai_citations', 'geo')).toBe(true);
    expect(tabMatches('website_experience', 'cro')).toBe(true);
    expect(tabMatches('seo', 'geo')).toBe(false);
  });
});
