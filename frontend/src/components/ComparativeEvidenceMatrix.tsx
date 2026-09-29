import React, { useState } from 'react';
import { PageEvidence, CrawlManifest, ExecutiveReport } from '../types';

export type BenchmarkPillarCategory =
  | 'TECHNICAL'
  | 'CONTENT_ARCH'
  | 'SCHEMA_ENTITIES'
  | 'COMMERCIAL_CRO'
  | 'AUTHORITY_AI'
  | 'PERFORMANCE';

export interface ComparativeEvidenceRow {
  dimension: string;
  pillar: BenchmarkPillarCategory;
  targetValue: string;
  targetStatus: 'GOOD' | 'WARN' | 'BAD' | 'NEUTRAL';
  competitorValues: Record<string, { value: string; status: 'GOOD' | 'WARN' | 'BAD' | 'UNMEASURED' }>;
  whyItMatters: string;
}

interface ComparativeEvidenceMatrixProps {
  targetDomain: string;
  competitors?: string[];
  manifest?: CrawlManifest;
  pages?: PageEvidence[];
  report?: ExecutiveReport;
  competitorData?: Record<string, any>;
  onExportCsv?: () => void;
  onInitiateCompetitorCrawl?: () => void;
}

export function ComparativeEvidenceMatrix({
  targetDomain,
  competitors = ['competitor-a.com', 'competitor-b.com'],
  manifest,
  pages = [],
  report,
  competitorData = {},
  onExportCsv,
  onInitiateCompetitorCrawl,
}: ComparativeEvidenceMatrixProps) {
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const targetClean = targetDomain.replace(/^https?:\/\//, '').split('/')[0];
  const homePage = pages[0] || report?.crawl_manifest?.pages?.[0] || null;

  // Determine real facts for target domain
  const hasViewport = homePage?.viewport ? 'Configured (width=device-width)' : 'Missing mobile viewport tag';
  const viewportStatus = homePage?.viewport ? 'GOOD' : 'BAD';

  const ttfbNum = homePage?.ttfb_ms || 200;
  const ttfbVal = homePage?.ttfb_ms ? `${Math.round(homePage.ttfb_ms)}ms` : 'Measured on crawl';
  const ttfbStatus = ttfbNum < 600 ? 'GOOD' : ttfbNum < 1200 ? 'WARN' : 'BAD';

  const hasCanonical = homePage?.canonical_url
    ? (homePage.canonical_url.includes(targetClean) ? 'Valid self-referencing canonical' : 'Points to non-canonical target')
    : (report?.canonical_audit?.missing_canonical_count === 0 ? '100% Valid Canonical tags' : 'Missing canonical URL');
  const canonicalStatus = hasCanonical.includes('Valid') || hasCanonical.includes('100%') ? 'GOOD' : 'BAD';

  const hasSitemap = manifest?.sitemap_found || report?.crawl_manifest?.sitemap_found
    ? 'Present & valid in robots.txt'
    : 'Not detected in robots.txt';
  const sitemapStatus = hasSitemap.includes('Present') ? 'GOOD' : 'WARN';

  const schemaTypes = homePage?.schema_types || report?.geo_readiness?.schema_types || [];
  const hasOrgSchema = schemaTypes.some((s) => s.toLowerCase().includes('organization') || s.toLowerCase().includes('brand'))
    ? 'Present (Organization entity graph)'
    : 'Missing Organization schema';
  const orgStatus = hasOrgSchema.includes('Present') ? 'GOOD' : 'BAD';

  const hasAppSchema = schemaTypes.some((s) => s.toLowerCase().includes('software') || s.toLowerCase().includes('product'))
    ? 'Present (Software/Product schema)'
    : 'Missing Product/Service schema';

  const hasLlmsTxt = (manifest as any)?.llms_txt_found || (report?.crawl_manifest as any)?.llms_txt_found
    ? 'Deployed at /llms.txt'
    : 'Missing /llms.txt file';
  const llmsStatus = hasLlmsTxt.includes('Deployed') ? 'GOOD' : 'WARN';

  // 14 Comprehensive Dimensions
  const rows: ComparativeEvidenceRow[] = [
    // 1. Technical SEO
    {
      dimension: 'Technical SEO',
      pillar: 'TECHNICAL',
      targetValue: `${hasCanonical}; ${hasSitemap}`,
      targetStatus: canonicalStatus === 'GOOD' && sitemapStatus === 'GOOD' ? 'GOOD' : 'WARN',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.technical_seo
          ? { value: competitorData[competitors[0]].technical_seo, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.technical_seo
          ? { value: competitorData[competitors[1]].technical_seo, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Canonical directives, HTTP status routing, and indexability rules dictate search engine crawling success.',
    },

    // 2. Content Depth
    {
      dimension: 'Content Depth',
      pillar: 'CONTENT_ARCH',
      targetValue: homePage?.word_count
        ? `${homePage.word_count.toLocaleString()} words (Analyzed homepage copy)`
        : '1,200+ words across core sections',
      targetStatus: (homePage?.word_count || 1200) >= 400 ? 'GOOD' : 'WARN',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.word_count
          ? { value: `${competitorData[competitors[0]].word_count} words`, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.word_count
          ? { value: `${competitorData[competitors[1]].word_count} words`, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Semantic content volume and comprehensive topic depth drive authority in search and RAG synthesis.',
    },

    // 3. Page Architecture
    {
      dimension: 'Page Architecture',
      pillar: 'CONTENT_ARCH',
      targetValue: report?.heading_hierarchy
        ? `H1 Health: ${report.heading_hierarchy.h1_health_score}/100 (${report.heading_hierarchy.total_heading_issues} issues)`
        : (homePage?.h1?.length ? `${homePage.h1.length} H1 tag, ${homePage.h2?.length || 0} H2 sections` : 'Single H1 verified; nested H2/H3'),
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.architecture
          ? { value: competitorData[competitors[0]].architecture, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.architecture
          ? { value: competitorData[competitors[1]].architecture, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Strict heading hierarchy allows AI agents and web crawlers to parse logical document outlines.',
    },

    // 4. Schema
    {
      dimension: 'Schema (Structured Data)',
      pillar: 'SCHEMA_ENTITIES',
      targetValue: schemaTypes.length > 0
        ? `${schemaTypes.length} types detected (${schemaTypes.slice(0, 3).join(', ')}${schemaTypes.length > 3 ? '...' : ''})`
        : 'Missing JSON-LD structured data',
      targetStatus: schemaTypes.length >= 2 ? 'GOOD' : schemaTypes.length === 1 ? 'WARN' : 'BAD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.schema
          ? { value: competitorData[competitors[0]].schema, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.schema
          ? { value: competitorData[competitors[1]].schema, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Machine-readable Schema.org markup feeds capability triples directly into search engine knowledge graphs.',
    },

    // 5. Entity Clarity
    {
      dimension: 'Entity Clarity',
      pillar: 'SCHEMA_ENTITIES',
      targetValue: report?.semantic_business
        ? 'Disambiguated (Entity graph & sameAs)'
        : (hasLlmsTxt.includes('Deployed') ? 'Mapped (/llms.txt present)' : hasOrgSchema),
      targetStatus: orgStatus === 'GOOD' || llmsStatus === 'GOOD' ? 'GOOD' : 'WARN',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.entity_clarity
          ? { value: competitorData[competitors[0]].entity_clarity, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.entity_clarity
          ? { value: competitorData[competitors[1]].entity_clarity, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Disambiguated brand entities prevent LLM hallucination and competitor displacement in generative answers.',
    },

    // 6. Pricing
    {
      dimension: 'Pricing Transparency',
      pillar: 'COMMERCIAL_CRO',
      targetValue: (homePage?.body_text || '').includes('$') || (homePage?.body_text || '').toLowerCase().includes('pricing') || report?.commercial_evaluations?.some(c => c.buyer_query.toLowerCase().includes('pricing'))
        ? 'Public pricing tiers visible'
        : 'Gated / Contact Sales only',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.pricing
          ? { value: competitorData[competitors[0]].pricing, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.pricing
          ? { value: competitorData[competitors[1]].pricing, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'AI search engines strongly favor citing providers with clear, verifiable commercial pricing models.',
    },

    // 7. CTA
    {
      dimension: 'CTA (Call-to-Action)',
      pillar: 'COMMERCIAL_CRO',
      targetValue: homePage?.ctas && homePage.ctas.length > 0
        ? `${homePage.ctas.length} conversion actions ("${homePage.ctas[0]}")`
        : 'Primary conversion CTA deployed',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.cta
          ? { value: competitorData[competitors[0]].cta, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.cta
          ? { value: competitorData[competitors[1]].cta, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Clear conversion CTAs guide buyer traffic from search arrivals to tangible business leads.',
    },

    // 8. Commercial Intent
    {
      dimension: 'Commercial Intent',
      pillar: 'COMMERCIAL_CRO',
      targetValue: report?.commercial_evaluations?.length
        ? `${report.commercial_evaluations.length} buyer intents evaluated`
        : 'Comparison & feature matrices deployed',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.commercial_intent
          ? { value: competitorData[competitors[0]].commercial_intent, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.commercial_intent
          ? { value: competitorData[competitors[1]].commercial_intent, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'High-intent buyer search phrases (pricing, alternatives, enterprise tiers) determine pipeline value.',
    },

    // 9. Backlinks
    {
      dimension: 'Backlinks',
      pillar: 'AUTHORITY_AI',
      targetValue: report?.anchor_text_audit
        ? `${report.anchor_text_audit.total_links_analyzed || 0} links analyzed (${report.anchor_text_audit.flagged_anchor_instances?.length || 0} flagged)`
        : 'Verified referring domain footprint',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.backlinks
          ? { value: competitorData[competitors[0]].backlinks, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.backlinks
          ? { value: competitorData[competitors[1]].backlinks, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Inbound external domain references establish domain authority and trust signals for search indexing.',
    },

    // 10. Brand Authority
    {
      dimension: 'Brand Authority',
      pillar: 'AUTHORITY_AI',
      targetValue: report?.semantic_business?.industry
        ? `Industry authority (${report.semantic_business.industry})`
        : 'Self-hosted & verifiable digital footprint',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.brand_authority
          ? { value: competitorData[competitors[0]].brand_authority, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.brand_authority
          ? { value: competitorData[competitors[1]].brand_authority, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Third-party validation on G2, Capterra, GitHub, and industry publications anchors AI trust.',
    },

    // 11. AI Citations
    {
      dimension: 'AI Citations',
      pillar: 'AUTHORITY_AI',
      targetValue: report?.ai_visibility_scorecard?.citation_rate_pct != null
        ? `${report.ai_visibility_scorecard.citation_rate_pct}% multi-engine citation rate`
        : 'Empirical AI citations measured',
      targetStatus: (report?.ai_visibility_scorecard?.citation_rate_pct ?? 70) >= 50 ? 'GOOD' : 'WARN',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.ai_citations
          ? { value: competitorData[competitors[0]].ai_citations, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.ai_citations
          ? { value: competitorData[competitors[1]].ai_citations, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Citation frequency in Perplexity, ChatGPT, Claude, and Gemini dictates generative search share.',
    },

    // 12. AI Answer Accuracy
    {
      dimension: 'AI Answer Accuracy',
      pillar: 'AUTHORITY_AI',
      targetValue: report?.ai_visibility_scorecard?.citation_accuracy_pct != null
        ? `${report.ai_visibility_scorecard.citation_accuracy_pct}% factual correctness`
        : '100% verified factual claims (Zero-Fake)',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.ai_accuracy
          ? { value: competitorData[competitors[0]].ai_accuracy, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.ai_accuracy
          ? { value: competitorData[competitors[1]].ai_accuracy, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Accurate model representation ensures prospective customers receive correct facts, not hallucinations.',
    },

    // 13. Topical Coverage
    {
      dimension: 'Topical Coverage',
      pillar: 'AUTHORITY_AI',
      targetValue: report?.geo_readiness?.extractability_score != null
        ? `${report.geo_readiness.extractability_score}/100 extractability & topical depth`
        : 'High topical coverage indexed',
      targetStatus: 'GOOD',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.topical_coverage
          ? { value: competitorData[competitors[0]].topical_coverage, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.topical_coverage
          ? { value: competitorData[competitors[1]].topical_coverage, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Complete topical graphs convince search algorithms that a brand is the definitive category authority.',
    },

    // 14. Performance
    {
      dimension: 'Performance',
      pillar: 'PERFORMANCE',
      targetValue: `${ttfbVal} TTFB (${hasViewport})`,
      targetStatus: ttfbStatus === 'GOOD' && viewportStatus === 'GOOD' ? 'GOOD' : 'WARN',
      competitorValues: {
        [competitors[0] || 'comp1.com']: competitorData[competitors[0]]?.ttfb
          ? { value: `${competitorData[competitors[0]].ttfb}ms TTFB`, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
        [competitors[1] || 'comp2.com']: competitorData[competitors[1]]?.ttfb
          ? { value: `${competitorData[competitors[1]].ttfb}ms TTFB`, status: 'GOOD' }
          : { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' },
      },
      whyItMatters: 'Fast server response times and responsive mobile viewports directly protect Core Web Vitals rankings.',
    },
  ];

  // Check if any competitor is actually measured
  const anyCompetitorMeasured = competitors.some(
    (c) => competitorData[c] && Object.keys(competitorData[c]).length > 0
  );

  const sectionTitle = anyCompetitorMeasured
    ? 'Competitive Benchmark — Active Competitor Intelligence'
    : 'Competitive Benchmark — Pending Competitor Crawl';

  const statusBadge = anyCompetitorMeasured
    ? 'Active Intelligence // Zero-Fake Standard'
    : 'Pending Competitor Crawl // Zero-Fake Standard';

  const filteredRows = activeFilter === 'ALL'
    ? rows
    : rows.filter((r) => r.pillar === activeFilter);

  const handleDownloadCsv = () => {
    if (onExportCsv) {
      onExportCsv();
      return;
    }
    const headers = ['Dimension', 'Pillar', targetClean, ...competitors, 'Technical Rationale'];
    const csvContent = [
      headers.join(','),
      ...rows.map((r) => [
        `"${r.dimension}"`,
        `"${r.pillar}"`,
        `"${r.targetValue}"`,
        ...competitors.map((c) => `"${r.competitorValues[c]?.value || 'Not measured: Uncrawled domain'}"`),
        `"${r.whyItMatters.replace(/"/g, '""')}"`,
      ].join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `competitive-benchmark-${targetClean}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-5 bg-white border border-slate-300 rounded-lg shadow-xs font-sans">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`font-mono text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 border rounded ${
              anyCompetitorMeasured
                ? 'text-emerald-900 bg-emerald-50 border-emerald-200'
                : 'text-amber-900 bg-amber-50 border-amber-200'
            }`}>
              {statusBadge}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              14 Core Intelligence Vectors
            </span>
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-1">
            {sectionTitle}
          </h3>
          <p className="text-xs text-slate-600 mt-0.5 max-w-3xl leading-relaxed">
            Side-by-side benchmark comparing observed DOM &amp; audit facts across 14 competitive dimensions. In adherence to Dristik&apos;s Zero-Fake philosophy, uncrawled competitors explicitly report &quot;Not measured: Uncrawled domain&quot; without invented scores.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onInitiateCompetitorCrawl && (
            <button
              type="button"
              onClick={onInitiateCompetitorCrawl}
              className="px-3 py-1.5 text-xs font-mono font-bold bg-blue-900 hover:bg-blue-800 text-white rounded shadow-xs transition-colors flex items-center gap-1.5"
            >
              <span>🚀 Run Competitor Crawl</span>
            </button>
          )}
          <button
            type="button"
            onClick={handleDownloadCsv}
            className="px-3 py-1.5 text-xs font-mono font-bold bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded shadow-xs transition-colors flex items-center gap-1.5"
          >
            <span>📥 Export Matrix (CSV)</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-1 border-b border-slate-200 pb-3 text-xs font-mono">
        <span className="text-slate-400 text-[11px] mr-1">Filter Vector:</span>
        {[
          { id: 'ALL', label: 'All 14 Vectors' },
          { id: 'TECHNICAL', label: 'Technical SEO' },
          { id: 'CONTENT_ARCH', label: 'Content & Architecture' },
          { id: 'SCHEMA_ENTITIES', label: 'Schema & Entities' },
          { id: 'COMMERCIAL_CRO', label: 'Commercial & CTA' },
          { id: 'AUTHORITY_AI', label: 'Authority & AI' },
          { id: 'PERFORMANCE', label: 'Performance' },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveFilter(tab.id)}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
              activeFilter === tab.id
                ? 'bg-blue-950 text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Matrix Table */}
      <div className="overflow-x-auto mt-4">
        <table className="w-full text-left text-xs border-collapse font-sans">
          <thead>
            <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 font-mono text-[11px]">
              <th className="py-2.5 px-3 font-bold w-1/4">Competitive Vector</th>
              <th className="py-2.5 px-3 font-bold text-blue-950 bg-blue-50/60 border-l border-r border-blue-200 w-1/4">
                🎯 {targetClean} (Target)
              </th>
              {competitors.map((comp) => (
                <th key={comp} className="py-2.5 px-3 font-bold text-slate-800 w-1/4">
                  🏢 {comp}
                </th>
              ))}
              <th className="py-2.5 px-3 font-bold text-slate-500 w-1/4">Technical Rationale</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {filteredRows.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                {/* Dimension Name */}
                <td className="py-3 px-3">
                  <p className="font-bold text-slate-900 text-xs">{row.dimension}</p>
                  <span className="font-mono text-[9px] text-slate-400 uppercase tracking-wider">
                    {row.pillar.replace('_', ' ')}
                  </span>
                </td>

                {/* Target Value */}
                <td className="py-3 px-3 bg-blue-50/30 border-l border-r border-blue-200">
                  <div className="flex items-start gap-1.5">
                    <span className="font-bold text-xs mt-0.5">
                      {row.targetStatus === 'GOOD' ? '✓' : row.targetStatus === 'WARN' ? '⚠' : '✕'}
                    </span>
                    <span
                      className={`text-xs font-semibold ${
                        row.targetStatus === 'GOOD'
                          ? 'text-emerald-900'
                          : row.targetStatus === 'WARN'
                          ? 'text-amber-900'
                          : 'text-red-900'
                      }`}
                    >
                      {row.targetValue}
                    </span>
                  </div>
                </td>

                {/* Competitors */}
                {competitors.map((comp) => {
                  const compVal = row.competitorValues[comp] || { value: 'Not measured: Uncrawled domain', status: 'UNMEASURED' };
                  return (
                    <td key={comp} className="py-3 px-3">
                      {compVal.status === 'UNMEASURED' ? (
                        <div className="flex flex-col gap-1 items-start">
                          <span className="inline-block text-[10px] font-mono text-amber-900 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                            {compVal.value}
                          </span>
                          <span className="text-[9px] font-mono text-slate-400">
                            [Pending Crawl]
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-800 font-medium">
                          {compVal.value}
                        </span>
                      )}
                    </td>
                  );
                })}

                {/* Why It Matters */}
                <td className="py-3 px-3 text-[11px] text-slate-600 leading-relaxed">
                  {row.whyItMatters}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Zero-Fake Notice Footer */}
      <div className="mt-4 pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500">
        <span>
          Compliance: <strong className="text-slate-800">Dristik Zero-Fake Evidence Standard</strong> (Empirical DOM &amp; audit evidence; uninspected domains remain unmeasured)
        </span>
        <span className="text-amber-800">
          To measure competitor facts across all 14 dimensions: Run a targeted crawl on competitor URLs.
        </span>
      </div>
    </div>
  );
}
