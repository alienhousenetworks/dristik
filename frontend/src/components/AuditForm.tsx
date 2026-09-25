import React from 'react';

export const SITE_TYPES = [
  { value: '', label: 'Detect automatically' },
  { value: 'business_corporate', label: 'Business / Corporate' },
  { value: 'saas', label: 'SaaS' },
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'marketplace', label: 'Marketplace' },
  { value: 'agency_services', label: 'Agency / Services' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'publisher_media', label: 'Publisher / Media' },
  { value: 'blog', label: 'Blog' },
  { value: 'community', label: 'Community' },
  { value: 'non_profit', label: 'Non-profit' },
  { value: 'educational', label: 'Educational' },
  { value: 'government', label: 'Government' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'financial', label: 'Financial' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'travel_hospitality', label: 'Travel / Hospitality' },
  { value: 'local_business', label: 'Local Business' },
  { value: 'other', label: 'Other' },
];

interface AuditFormProps {
  url: string;
  maxPages: number;
  siteType: string;
  declaredNotes?: string;
  isLoading: boolean;
  error: string | null;
  onUrlChange: (value: string) => void;
  onMaxPagesChange: (value: number) => void;
  onSiteTypeChange: (value: string) => void;
  onDeclaredNotesChange?: (value: string) => void;
  onSubmit: () => void;
}

export function AuditForm({
  url,
  maxPages,
  siteType,
  declaredNotes = '',
  isLoading,
  error,
  onUrlChange,
  onMaxPagesChange,
  onSiteTypeChange,
  onDeclaredNotesChange,
  onSubmit,
}: AuditFormProps) {
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex flex-col lg:flex-row lg:items-end gap-3">
        <label className="flex-1 min-w-0">
          <span className="label block mb-1.5">Website URL</span>
          <input
            type="text"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="https://example.com"
            disabled={isLoading}
            autoComplete="url"
            spellCheck={false}
            className="field"
          />
        </label>

        <label className="lg:w-52">
          <span className="label block mb-1.5">Site type</span>
          <select
            value={siteType}
            onChange={(e) => onSiteTypeChange(e.target.value)}
            disabled={isLoading}
            className="field"
          >
            {SITE_TYPES.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>
        </label>

        <label className="lg:w-24">
          <span className="label block mb-1.5">Pages</span>
          <select
            value={maxPages}
            onChange={(e) => onMaxPagesChange(Number(e.target.value))}
            disabled={isLoading}
            className="field"
          >
            <option value={3}>3</option>
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={25}>25</option>
          </select>
        </label>

        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary px-5 py-2.5 disabled:opacity-50 lg:mb-px"
        >
          {isLoading ? 'Running…' : 'Run audit'}
        </button>
      </div>

      {siteType === 'other' && onDeclaredNotesChange && (
        <label className="block">
          <span className="label block mb-1.5">Describe the business</span>
          <input
            type="text"
            value={declaredNotes}
            onChange={(e) => onDeclaredNotesChange(e.target.value)}
            placeholder="e.g. B2B wholesale marketplace"
            disabled={isLoading}
            className="field"
          />
        </label>
      )}

      <p className="text-xs text-ink-400">
        Site type is treated as context, not truth. Dristik verifies the live pages independently.
      </p>

      {error && <p className="text-sm text-bad">{error}</p>}
    </form>
  );
}
