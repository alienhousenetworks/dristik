import { Category, Severity } from '../types';

export function display(value?: string | null, fallback = '—'): string {
  const text = (value ?? '').trim();
  if (!text) return fallback;
  const lowered = text.toLowerCase();
  if (
    lowered === 'unknown' ||
    lowered === 'unknown business' ||
    lowered === 'unspecified' ||
    lowered === 'n/a'
  ) {
    return fallback;
  }
  return text;
}

export function humanize(value?: string | null): string {
  if (!value) return '—';
  return value.replace(/_/g, ' ').toLowerCase();
}

export function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    TECHNICAL_SEO: 'Technical SEO',
    ON_PAGE_SEO: 'On-page SEO',
    CONTENT: 'Content',
    GEO: 'GEO',
    AI_SEARCH: 'AI search',
    SCHEMA: 'Schema',
    UX_CONVERSION: 'UX & conversion',
    TRUST_AUTHORITY: 'Trust',
    COMPETITIVE: 'Competitive',
  };
  return labels[category] || humanize(category);
}

export function severityTone(severity: Severity | string): string {
  switch (severity) {
    case 'CRITICAL':
    case 'HIGH':
      return 'text-bad';
    case 'MEDIUM':
      return 'text-warn';
    default:
      return 'text-ink-500';
  }
}

export function scoreTone(score: number): string {
  if (score >= 80) return 'text-good';
  if (score >= 60) return 'text-warn';
  return 'text-bad';
}

export function scoreBar(score: number): string {
  if (score >= 80) return 'bg-good';
  if (score >= 60) return 'bg-warn';
  return 'bg-bad';
}

export function formatPercent(value?: number | null): string {
  if (value === undefined || value === null || isNaN(value)) return '—';
  const n = value <= 1 ? value * 100 : value;
  return `${Math.round(n)}%`;
}

export function formatUsd(value: number): string {
  if (!value) return '$0.00';
  return `$${value.toFixed(4)}`;
}

export function formatAuditCost(telemetry?: {
  estimated_cost_usd?: number | null;
  cost_complete?: boolean;
  unpriced_calls?: number;
} | null): string {
  if (!telemetry) return '—';
  const unpriced = telemetry.unpriced_calls ?? 0;
  const known = telemetry.cost_complete !== false;
  const amount = telemetry.estimated_cost_usd ?? 0;
  if (!known && unpriced > 0 && !amount) return 'Unpriced';
  const formatted = formatUsd(amount);
  if (!known && unpriced > 0) {
    return `${formatted} · ${unpriced} call${unpriced === 1 ? '' : 's'} unpriced`;
  }
  return formatted;
}

export function costBasisCaption(basis?: string | null): string | null {
  if (basis === 'provider_billed') return 'Billed by the provider';
  if (basis === 'operator_rate') return 'Your configured rate';
  if (basis === 'list_price') return 'Published list price';
  if (basis === 'mixed') return 'Mixed rates';
  return null;
}

export function formatMs(value: number): string {
  if (!value) return '0s';
  if (value < 1000) return `${Math.round(value)}ms`;
  return `${(value / 1000).toFixed(1)}s`;
}

export function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback;
}

export function asString(value: unknown, fallback = '—'): string {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

export function isBlank(value?: string | null): boolean {
  return display(value, '') === '';
}

export const CATEGORY_FILTERS: Array<Category | 'ALL'> = [
  'ALL',
  'TECHNICAL_SEO',
  'ON_PAGE_SEO',
  'CONTENT',
  'GEO',
  'AI_SEARCH',
  'SCHEMA',
  'UX_CONVERSION',
  'TRUST_AUTHORITY',
];
