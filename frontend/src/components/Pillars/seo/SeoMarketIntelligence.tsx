import React, { useState } from 'react';
import { ExecutiveReport } from '../../../types';
import { Card } from '../../ui';
import {
  MapPin,
  Globe,
  Users,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Languages,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';

interface SeoMarketIntelligenceProps {
  report: ExecutiveReport;
}

export function SeoMarketIntelligence({ report }: SeoMarketIntelligenceProps) {
  const [activeMarketSection, setActiveMarketSection] = useState<'local' | 'intl' | 'competitors'>('local');

  const localSeo = report.local_seo;
  const intlSeo = report.international_seo;
  const compParity = report.competitor_seo_parity;

  return (
    <div className="space-y-6">
      {/* ─────────────────────────────────────────────────────────────
          SECTION SUB-NAV: LOCAL vs INTERNATIONAL vs COMPETITORS
          ───────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-b border-line pb-3">
        {[
          { id: 'local' as const, label: 'Local SEO & NAP Footprint', icon: MapPin },
          { id: 'intl' as const, label: 'International & Hreflang', icon: Languages },
          { id: 'competitors' as const, label: 'Competitor Technical Parity', icon: Users },
        ].map((sec) => {
          const Icon = sec.icon;
          const isActive = activeMarketSection === sec.id;
          return (
            <button
              key={sec.id}
              type="button"
              onClick={() => setActiveMarketSection(sec.id)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-paper-100 text-ink shadow-sm border border-line font-semibold'
                  : 'text-ink-500 hover:text-ink hover:bg-paper-100/50'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {sec.label}
            </button>
          );
        })}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          SUB-VIEW 1: LOCAL SEO & NAP CONSISTENCY
          ───────────────────────────────────────────────────────────── */}
      {activeMarketSection === 'local' && (
        <div className="space-y-6">
          {/* Top Vitals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-1.5 bg-paper-50 border-line">
              <span className="text-[10px] font-mono uppercase tracking-[0.04em] text-ink-500 font-semibold block">
                NAP Consistency
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold font-mono text-ink">
                  {localSeo ? `${localSeo.nap_consistency_score}%` : '100%'}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                  (localSeo?.nap_consistency_score ?? 100) >= 80 ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'
                }`}>
                  {(localSeo?.nap_consistency_score ?? 100) >= 80 ? 'Consistent' : 'Conflicts'}
                </span>
              </div>
              <span className="text-[11px] text-ink-500 block">Name, Address, Phone alignment</span>
            </Card>

            <Card className="p-4 space-y-1.5 bg-paper-50 border-line">
              <span className="text-[10px] font-mono uppercase tracking-[0.04em] text-ink-500 font-semibold block">
                Google Business Profile
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold font-sans text-ink">
                  {localSeo?.has_google_business_profile ? 'Linked' : 'Not Linked'}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                  localSeo?.has_google_business_profile ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'
                }`}>
                  {localSeo?.has_google_business_profile ? 'Verified' : 'Missing Link'}
                </span>
              </div>
              <span className="text-[11px] text-ink-500 block">Google Maps co-reference</span>
            </Card>

            <Card className="p-4 space-y-1.5 bg-paper-50 border-line">
              <span className="text-[10px] font-mono uppercase tracking-[0.04em] text-ink-500 font-semibold block">
                Google Maps Embed
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold font-sans text-ink">
                  {localSeo?.has_google_maps_embed ? 'Embedded' : 'Missing'}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                  localSeo?.has_google_maps_embed ? 'bg-good/10 text-good' : 'bg-ink-500/10 text-ink-500'
                }`}>
                  {localSeo?.has_google_maps_embed ? 'Interactive' : 'No iframe'}
                </span>
              </div>
              <span className="text-[11px] text-ink-500 block">Contact landing verification</span>
            </Card>

            <Card className="p-4 space-y-1.5 bg-paper-50 border-line">
              <span className="text-[10px] font-mono uppercase tracking-[0.04em] text-ink-500 font-semibold block">
                LocalBusiness Schema
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold font-mono text-ink">
                  {localSeo?.local_business_schema_found ? `${localSeo.local_schema_completeness_pct}%` : 'Absent'}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                  localSeo?.local_business_schema_found ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'
                }`}>
                  {localSeo?.local_business_schema_found ? 'JSON-LD Valid' : 'Missing'}
                </span>
              </div>
              <span className="text-[11px] text-ink-500 block">Structured local entities</span>
            </Card>
          </div>

          {/* Diagnostic Details Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card className="p-6 space-y-4 border-line bg-paper-50">
              <div className="flex items-center gap-2 border-b border-line pb-3">
                <MapPin className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-base font-semibold text-ink">
                  NAP Footprint & Authoritative Contact
                </h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase font-bold block">Authoritative Phone Detected</span>
                  <span className="font-mono font-bold text-ink text-sm">
                    {localSeo?.consistent_phone || 'No phone number declared in main text'}
                  </span>
                </div>

                <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
                  <span className="text-[10px] font-mono text-ink-500 uppercase font-bold block">Authoritative Physical Address</span>
                  <span className="text-ink-700 leading-relaxed block">
                    {localSeo?.consistent_address || 'No physical address block detected on crawled pages'}
                  </span>
                </div>

                {/* Phone Conflicts Resolver */}
                {localSeo?.phone_conflicts && localSeo.phone_conflicts.length > 1 && (
                  <div className="p-3.5 rounded border border-bad/30 bg-bad/5 space-y-2">
                    <span className="text-[10px] font-bold text-bad uppercase block">Conflicting Phone Numbers Detected:</span>
                    <div className="space-y-1 font-mono text-xs">
                      {localSeo.phone_conflicts.map((c, i) => (
                        <div key={i} className="flex justify-between text-bad">
                          <span>{c.phone}</span>
                          <span>({c.occurrences} pages)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Schema Missing Fields */}
                {localSeo?.schema_missing_fields && localSeo.schema_missing_fields.length > 0 && (
                  <div className="p-3.5 rounded border border-warn/30 bg-warn/5 space-y-1">
                    <span className="text-[10px] font-bold text-warn uppercase block">Missing LocalBusiness JSON-LD Fields:</span>
                    <span className="text-xs text-ink-700 block">
                      {localSeo.schema_missing_fields.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            </Card>

            <Card className="p-6 space-y-4 border-line bg-paper-50">
              <div className="flex items-center gap-2 border-b border-line pb-3">
                <Globe className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-base font-semibold text-ink">
                  Google Business Profile & Directory Signals
                </h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-2">
                  <span className="text-[10px] font-mono text-ink-500 uppercase font-bold block">Google Business Profile Links</span>
                  {localSeo?.gbp_urls && localSeo.gbp_urls.length > 0 ? (
                    <div className="space-y-1 font-mono">
                      {localSeo.gbp_urls.map((url, i) => (
                        <a
                          key={i}
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-pine-600 hover:underline flex items-center gap-1 truncate"
                        >
                          {url} <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      ))}
                    </div>
                  ) : (
                    <p className="text-ink-500">
                      No direct link to Google Business Profile detected in footer or header. Adding this strengthens entity trust.
                    </p>
                  )}
                </div>

                <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-2">
                  <span className="text-[10px] font-mono text-ink-500 uppercase font-bold block">Local Landing Pages Discovered</span>
                  {localSeo?.local_landing_pages && localSeo.local_landing_pages.length > 0 ? (
                    <div className="space-y-1 font-mono">
                      {localSeo.local_landing_pages.map((lp, i) => (
                        <div key={i} className="flex justify-between text-ink-700">
                          <span className="truncate">{lp.url}</span>
                          <span className="text-ink-500 font-sans">{lp.target_location || 'Local'}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-ink-500">
                      No location-specific landing pages discovered. Ideal for multi-location enterprise footprints.
                    </p>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-VIEW 2: INTERNATIONAL SEO & HREFLANG
          ───────────────────────────────────────────────────────────── */}
      {activeMarketSection === 'intl' && (
        <div className="space-y-6">
          <Card className="p-6 space-y-4 border-line bg-paper-50">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Languages className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-base font-semibold text-ink">
                  Internationalization & Hreflang Architecture
                </h3>
              </div>
              <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded ${
                intlSeo?.is_multilingual ? 'bg-pine-500/10 text-pine-600 dark:text-pine-400' : 'bg-paper-200 text-ink-600'
              }`}>
                {intlSeo?.is_multilingual ? 'Multilingual Site' : 'Single Locale'}
              </span>
            </div>

            <p className="text-xs text-ink-600 leading-relaxed">
              Validates that multi-regional and multi-language URLs declare reciprocal hreflang alternate tags, include an `x-default` global fallback, and prevent language targeting errors.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">Detected Locales</span>
                <span className="text-xl font-mono font-bold text-ink">
                  {intlSeo?.locales_detected?.length || 1}
                </span>
                <p className="text-[10px] text-ink-500 font-mono truncate">
                  {intlSeo?.locales_detected?.join(', ') || 'en (default)'}
                </p>
              </div>

              <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">x-default Fallback</span>
                <span className={`text-xl font-mono font-bold ${
                  intlSeo?.has_x_default ? 'text-good' : 'text-ink-400'
                }`}>
                  {intlSeo?.has_x_default ? 'Declared' : 'Not Set'}
                </span>
                <p className="text-[10px] text-ink-500">Global fallback targeting</p>
              </div>

              <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">Reciprocal Return Tags</span>
                <span className={`text-xl font-mono font-bold ${
                  intlSeo?.return_tags_healthy ? 'text-good' : 'text-warn'
                }`}>
                  {intlSeo?.return_tags_healthy ? 'Valid' : 'Discrepancy'}
                </span>
                <p className="text-[10px] text-ink-500">Two-way cross reference</p>
              </div>

              <div className="p-3.5 rounded border border-line bg-paper-100/60 space-y-1">
                <span className="text-[10px] font-mono text-ink-400 block uppercase font-bold">Flagged Issues</span>
                <span className={`text-xl font-mono font-bold ${
                  (intlSeo?.issues?.length || 0) > 0 ? 'text-warn' : 'text-good'
                }`}>
                  {intlSeo?.issues?.length || 0}
                </span>
                <p className="text-[10px] text-ink-500">Invalid ISO language tags</p>
              </div>
            </div>

            {/* Hreflang Issues Table */}
            {intlSeo?.issues && intlSeo.issues.length > 0 && (
              <div className="mt-4 pt-3 border-t border-line space-y-2">
                <span className="text-xs font-semibold text-bad block">
                  Flagged Hreflang Validation Errors:
                </span>
                <div className="space-y-1.5 font-mono text-xs max-h-40 overflow-y-auto">
                  {intlSeo.issues.map((iss, idx) => (
                    <div key={idx} className="p-2.5 rounded bg-bad/5 border border-bad/20 flex items-center justify-between gap-3 text-ink-700">
                      <span className="truncate">{iss.url}: {iss.message}</span>
                      <span className="text-bad font-bold shrink-0">{iss.severity}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-VIEW 3: COMPETITOR TECHNICAL SEO PARITY
          ───────────────────────────────────────────────────────────── */}
      {activeMarketSection === 'competitors' && (
        <div className="space-y-6">
          <Card className="p-6 space-y-4 border-line bg-paper-50">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-ink-700" />
                <h3 className="font-sans text-base font-semibold text-ink">
                  Competitor Technical SEO Parity Matrix
                </h3>
              </div>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-paper-200 text-ink-700">
                {compParity?.target_rank != null
                  ? `Rank #${compParity.target_rank} of ${compParity?.competitors?.length ?? 1}`
                  : 'Target Baseline Active'}
              </span>
            </div>

            <p className="text-xs text-ink-600 leading-relaxed">
              {compParity?.strategic_takeaway || 'Side-by-side technical SEO benchmark comparing target domain against direct competitors in the same vertical.'}
            </p>

            {/* Side-by-side Table */}
            <div className="overflow-x-auto border border-line rounded-lg">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-paper-100 border-b border-line text-ink-700">
                    <th className="p-3 font-semibold">Technical Metric</th>
                    {compParity?.competitors.map((c, idx) => (
                      <th key={idx} className="p-3 font-semibold font-mono">
                        {c.brand_name} {c.is_target && <span className="text-pine-600 font-bold ml-1">(Target)</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">Overall SEO Score</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono font-bold text-ink">
                        {c.overall_seo_score != null ? `${c.overall_seo_score}/100` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">Technical Health</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono text-ink-700">
                        {c.technical_health_score != null ? `${c.technical_health_score}/100` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">On-Page Optimization</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono text-ink-700">
                        {c.onpage_score != null ? `${c.onpage_score}/100` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">Average Word Count</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono text-ink-700">
                        {c.avg_word_count != null ? `${c.avg_word_count} words` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">Schema Types Count</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono text-ink-700">
                        {c.schema_types_count != null ? `${c.schema_types_count} types` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">Server Latency (TTFB)</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono text-ink-700">
                        {c.avg_ttfb_ms != null ? `${c.avg_ttfb_ms} ms` : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-paper-100/50">
                    <td className="p-3 font-medium text-ink-600">HTTP 200 Pass Rate</td>
                    {compParity?.competitors.map((c, idx) => (
                      <td key={idx} className="p-3 font-mono text-good font-semibold">
                        {c.http_200_rate_pct != null ? `${c.http_200_rate_pct}%` : '—'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Strategic Strengths and Deficits */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
              <div className="p-4 rounded-lg border border-good/20 bg-good/5 space-y-1.5">
                <span className="font-semibold text-good block">Key Competitive Advantages</span>
                {compParity?.top_advantages && compParity.top_advantages.length > 0 ? (
                  <ul className="list-disc list-inside space-y-1 text-ink-700">
                    {compParity.top_advantages.map((adv, idx) => (
                      <li key={idx}>{adv}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-ink-500">Parity with competitor baseline.</p>
                )}
              </div>

              <div className="p-4 rounded-lg border border-bad/20 bg-bad/5 space-y-1.5">
                <span className="font-semibold text-bad block">Competitive Deficits to Close</span>
                {compParity?.critical_deficits && compParity.critical_deficits.length > 0 ? (
                  <ul className="list-disc list-inside space-y-1 text-ink-700">
                    {compParity.critical_deficits.map((def, idx) => (
                      <li key={idx}>{def}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-ink-500">No major technical deficits vs peers.</p>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
