import React, { useState } from 'react';
import { ExecutiveReport, Finding } from '../../types';
import { Pages } from '../Pages';
import { SearchConsoleAttributionView } from '../SearchConsoleAttributionView';
import { IndexationIntelligenceView } from '../IndexationIntelligenceView';
import { KeywordTrackingView } from '../KeywordTrackingView';
import { PillarShell } from '../ui';

interface SearchIntelligenceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onSelectFinding?: (f: Finding) => void;
  onOpenConnectors?: (tabId?: string) => void;
}

type SearchSubTab = 'overview' | 'keywords' | 'indexation' | 'technical' | 'onpage' | 'content' | 'links' | 'gsc' | 'pages';

export function SearchIntelligenceView({
  report,
  analysisId,
  onSelectFinding,
  onOpenConnectors,
}: SearchIntelligenceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<SearchSubTab>('overview');

  const crawl = report.crawl_manifest;
  const pages = crawl?.pages || [];
  const homePage = pages[0];
  const findings = (report.findings || []).filter(
    (f) => f.category === 'TECHNICAL_SEO' || f.category === 'ON_PAGE_SEO' || f.category === 'CONTENT'
  );

  return (
    <PillarShell
      kicker="Search"
      title="Organic search and crawl"
      description="Indexation, HTML structure, internal links, and Search Console attribution."
      scoreLabel="Search"
      score={(() => {
        const measured = report.scores?.category_scores?.['TECHNICAL_SEO']?.score ?? report.honest_scores?.google_score;
        return typeof measured === 'number' ? Math.round(measured) : '—';
      })()}
      metaLabel="Findings"
      meta={`${findings.length}`}
      tabs={[
        { id: 'overview', label: 'Overview' },
        { id: 'keywords', label: 'Keywords & SERP' },
        { id: 'indexation', label: 'Indexation' },
        { id: 'technical', label: 'Technical' },
        { id: 'onpage', label: 'On-page' },
        { id: 'content', label: 'Content' },
        { id: 'links', label: 'Links' },
        { id: 'gsc', label: 'Search Console' },
        { id: 'pages', label: `Pages (${pages.length})` },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as SearchSubTab)}
    >

      {/* SUB-VIEW: KEYWORDS & SERP TRACKING */}
      {activeSubTab === 'keywords' && (
        <KeywordTrackingView
          projectId={report.project_id || 'default_project'}
          domain={report.domain}
          competitors={report.business_profile?.competitors || []}
        />
      )}

      {/* SUB-VIEW 1: OVERVIEW & HIGH-LEVEL DIAGNOSTICS */}
      {activeSubTab === 'overview' && (
        <div className="space-y-8">
          {/* Key Vitals Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-4 rounded-lg space-y-1">
              <span className="label text-[10px] text-ink-500 block">XML Sitemap</span>
              <span className="font-semibold text-ink text-base block">
                {crawl?.sitemap_found ? ' Detected & Valid' : ' Not Discovered'}
              </span>
              <span className="text-xs text-ink-500 font-mono truncate block">
                {crawl?.sitemap_url || 'No sitemap link in robots.txt'}
              </span>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-4 rounded-lg space-y-1">
              <span className="label text-[10px] text-ink-500 block">Robots.txt Health</span>
              <span className="font-semibold text-ink text-base block">
                {crawl?.robots_txt_found ? ' Accessible' : crawl ? 'Not found' : '—'}
              </span>
              <span className="text-xs text-ink-500 block">
                {crawl?.robots_txt_found ? 'Standard crawl rules active' : 'Crawl directives absent'}
              </span>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-4 rounded-lg space-y-1">
              <span className="label text-[10px] text-ink-500 block">Crawl Footprint</span>
              <span className="font-semibold text-ink text-base block">
                {crawl?.total_pages_discovered || pages.length} Pages Crawled
              </span>
              <span className="text-xs text-ink-500 block">
                {pages.length ? `${pages.filter((p) => p.status_code === 200).length} returned HTTP 200` : 'No pages crawled'}
              </span>
            </div>

            <div className="bg-paper-50 dark:bg-ink-900/40 border border-line p-4 rounded-lg space-y-1">
              <span className="label text-[10px] text-ink-500 block">Server TTFB (Latency)</span>
              <span className="font-semibold text-ink text-base block">
                {homePage?.ttfb_ms ? `${homePage.ttfb_ms} ms` : '—'}
              </span>
              <span className="text-xs text-ink-500 block">
                {homePage?.ttfb_ms ? 'Measured on the homepage fetch' : 'Not measured'}
              </span>
            </div>
          </div>

          {/* Critical Findings Section */}
          <div className="sheet border border-line rounded-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-sans text-xl text-ink font-bold">
                Verified Search & SEO Deficiencies ({findings.length})
              </h3>
              <span className="text-xs font-mono text-ink-500">Backed by Cryptographic DOM Evidence</span>
            </div>

            {findings.length === 0 ? (
              <p className="text-sm text-good">No critical technical or on-page SEO defects detected.</p>
            ) : (
              <div className="space-y-3">
                {findings.slice(0, 6).map((item) => (
                  <div
                    key={item.finding_id}
                    onClick={() => onSelectFinding?.(item)}
                    className="p-3.5 bg-paper-50 dark:bg-ink-900/40 border border-line rounded-md hover:border-ink cursor-pointer transition-colors flex items-start justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                          item.severity === 'CRITICAL' ? 'bg-bad/10 text-bad' :
                          item.severity === 'HIGH' ? 'bg-warn/10 text-warn' : 'bg-paper-200 text-ink-700'
                        }`}>
                          {item.severity}
                        </span>
                        <span className="font-semibold text-ink text-sm">{item.title}</span>
                      </div>
                      <p className="text-xs text-ink-600 line-clamp-1">{item.description}</p>
                    </div>

                    <span className="text-xs text-ink-700 font-mono font-bold shrink-0 self-center">
                      Inspect Evidence →
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW: INDEXATION INTELLIGENCE */}
      {activeSubTab === 'indexation' && (
        <IndexationIntelligenceView
          manifest={crawl}
          pages={pages}
          domain={report.domain}
        />
      )}

      {/* SUB-VIEW 2: TECHNICAL SEO */}
      {activeSubTab === 'technical' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Technical Crawl & Indexability Directives</h3>
          <p className="text-xs text-ink-500">Audits canonical tags, noindex tags, sitemap entries, and HTTP status codes.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="border border-line rounded-lg p-4 bg-paper-50 space-y-3">
              <span className="label text-[10px] block">Robots.txt Content</span>
              <pre className="text-xs font-mono bg-paper-100 dark:bg-ink-950 p-3 rounded overflow-x-auto max-h-48 border border-line">
                {crawl?.robots_txt_content || 'robots.txt was not fetched.'}
              </pre>
            </div>

            <div className="border border-line rounded-lg p-4 bg-paper-50 space-y-3">
              <span className="label text-[10px] block">Canonical & Indexability Audit</span>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between border-b border-line pb-1.5">
                  <span className="text-ink-600">Canonical Tag Declared:</span>
                  <span className="font-mono font-bold text-ink">{homePage?.canonical_url || '—'}</span>
                </div>
                <div className="flex items-center justify-between border-b border-line pb-1.5">
                  <span className="text-ink-600">Robots Meta Tag:</span>
                  <span className="font-mono font-bold text-ink">{homePage?.robots_meta || '—'}</span>
                </div>
                <div className="flex items-center justify-between border-b border-line pb-1.5">
                  <span className="text-ink-600">HTTP Status:</span>
                  <span className="font-mono font-bold text-ink">{homePage?.status_code ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between pb-1">
                  <span className="text-ink-600">DOM Elements Count:</span>
                  <span className="font-mono text-ink">{homePage?.dom_elements_count ?? '—'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: ON-PAGE & HTML */}
      {activeSubTab === 'onpage' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">On-Page Tags & HTML5 Semantic Architecture</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Homepage Title Tag</span>
              <p className="font-semibold text-ink text-sm">{homePage?.title || 'No Title Detected'}</p>
              <span className="text-ink-500 font-mono">Length: {homePage?.title ? homePage.title.length : 0} characters. A character count is not a required band.</span>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-2">
              <span className="label text-[10px] block">Meta Description</span>
              <p className="text-ink text-sm">{homePage?.meta_description || 'No Meta Description Found'}</p>
              <span className="text-ink-500 font-mono">Length: {homePage?.meta_description ? homePage.meta_description.length : 0} characters. A character count is not a required band.</span>
            </div>

            <div className="col-span-full border border-line p-4 rounded-lg bg-paper-50 space-y-3">
              <span className="label text-[10px] block">H1 - H3 Heading Structure</span>
              <div className="space-y-1.5 font-mono text-xs">
                {homePage?.h1?.map((h, i) => (
                  <div key={i} className="bg-paper-100 p-2 rounded border border-line">
                    <span className="text-ink-700 font-bold mr-2">H1:</span> {h}
                  </div>
                ))}
                {homePage?.h2?.slice(0, 5).map((h, i) => (
                  <div key={i} className="bg-paper-100/60 p-1.5 rounded border border-line/60 ml-4">
                    <span className="text-ink-500 font-bold mr-2">H2:</span> {h}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: CONTENT DEPTH, INFORMATION GAIN & EEAT */}
      {activeSubTab === 'content' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-sans text-2xl text-ink font-bold">Topical Authority, Information Gain & Non-Commodity Value</h3>
              <p className="text-xs text-ink-500 mt-1">
                Aligned with Google AI-search guidance: rewarding unique first-party data, expert signals, and empirical proof over commodity word counts.
              </p>
            </div>
            {report.topical_authority && (
              <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded ${
                report.topical_authority.status === 'PASS' ? 'bg-good/10 text-good' :
                report.topical_authority.status === 'NEEDS_IMPROVEMENT' ? 'bg-warn/10 text-warn' :
                'bg-bad/10 text-bad'
              }`}>
                {report.topical_authority.status.replace('_', ' ')}
              </span>
            )}
          </div>

          {/* Vitals Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block text-ink-500 uppercase font-mono font-semibold">Information Gain</span>
              <span className="font-sans text-3xl font-bold text-ink">
                {report.topical_authority ? `${report.topical_authority.avg_information_gain}/100` : '50/100'}
              </span>
              <span className="text-xs text-ink-500 block">Unique data vs commodity copy</span>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block text-ink-500 uppercase font-mono font-semibold">Original Data Points</span>
              <span className="font-sans text-3xl font-bold text-ink">
                {report.topical_authority?.total_original_data_points ?? 0}
              </span>
              <span className="text-xs text-ink-500 block">Metrics, percentages, currencies</span>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block text-ink-500 uppercase font-mono font-semibold">Unbacked Claims</span>
              <span className={`font-sans text-3xl font-bold ${(report.topical_authority?.unbacked_claims_total ?? 0) > 0 ? 'text-warn' : 'text-good'}`}>
                {report.topical_authority?.unbacked_claims_total ?? 0}
              </span>
              <span className="text-xs text-ink-500 block">Superlatives without proof</span>
            </div>

            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block text-ink-500 uppercase font-mono font-semibold">Readability & Length</span>
              <span className="font-sans text-3xl font-bold text-ink">
                {homePage?.word_count || 0} <span className="text-sm font-sans font-normal text-ink-500">words</span>
              </span>
              <span className="text-xs text-ink-500 block">
                Flesch: {homePage?.readability_score ?? '—'} / 100
              </span>
            </div>
          </div>

          {/* Diagnostic Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-xs">
            {/* Left: First-party Evidence & Expert Signals */}
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-3">
              <span className="label text-[10px] block uppercase font-mono font-semibold text-ink-700">
                First-Party Evidence & E-E-A-T Signals
              </span>
              <div className="space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-line/60">
                  <span className="text-ink-600">Pages with Expert / Author Bylines:</span>
                  <span className="font-mono font-bold text-ink">
                    {report.topical_authority?.pages_with_expert_signals ?? 0} of {pages.length}
                  </span>
                </div>
                <div className="flex items-center justify-between pb-1.5 border-b border-line/60">
                  <span className="text-ink-600">First-Party Evidence Density:</span>
                  <span className="font-mono font-bold text-ink">
                    {report.topical_authority?.first_party_evidence_density ?? 0} points/page
                  </span>
                </div>
                <div className="flex items-center justify-between pb-1.5 border-b border-line/60">
                  <span className="text-ink-600">Topical Concept Breadth:</span>
                  <span className="font-mono font-bold text-ink">
                    {report.topical_authority?.topical_coverage_score ?? 0} / 100
                  </span>
                </div>
                <div className="pt-2">
                  <span className="label text-[10px] block text-ink-500 mb-1">Search Intent Distribution</span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(report.topical_authority?.search_intent_distribution || {}).map(([intent, cnt]) => (
                      <span key={intent} className="px-2 py-0.5 rounded font-mono font-semibold bg-paper-100 border border-line text-ink">
                        {intent}: {cnt}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Synthesis & Cannibalization Alerts */}
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-3">
              <span className="label text-[10px] block uppercase font-mono font-semibold text-ink-700">
                Topical Authority Synthesis
              </span>
              <p className="text-ink-700 leading-relaxed">
                {report.topical_authority?.summary || 'Topical authority evaluation complete.'}
              </p>

              {report.topical_authority?.cannibalization_clusters && report.topical_authority.cannibalization_clusters.length > 0 && (
                <div className="p-3 rounded border border-bad/30 bg-bad/10 dark:bg-bad/10 space-y-1.5">
                  <span className="text-[10px] font-bold text-bad uppercase block">
                    Content Cannibalization Warning ({report.topical_authority.cannibalization_clusters.length} clusters)
                  </span>
                  {report.topical_authority.cannibalization_clusters.map((c, i) => (
                    <div key={i} className="text-ink-700 text-[11px] space-y-0.5">
                      <span className="font-semibold text-bad dark:text-bad block">Topic: {c.primary_topic} ({Math.round(c.similarity_score * 100)}% text similarity)</span>
                      <span className="font-mono text-ink-500 truncate block">{c.urls.join(' ↔ ')}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 5: INTERNAL LINKING GRAPH */}
      {activeSubTab === 'links' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-sans text-2xl text-ink font-bold">Internal Linking Architecture & Discovery</h3>
          <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-3">
            <span className="label text-[10px] block">Internal Links Mapped</span>
            <div className="max-h-60 overflow-y-auto space-y-1.5 font-mono text-xs">
              {(homePage?.internal_links || []).slice(0, 15).map((l, i) => (
                <div key={i} className="p-1.5 bg-paper-100 rounded border border-line truncate">
                  🔗 {l}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 6: SEARCH CONSOLE ATTRIBUTION */}
      {activeSubTab === 'gsc' && (
        <SearchConsoleAttributionView
          domain={report.domain}
          analysisId={analysisId}
          onOpenConnectors={onOpenConnectors}
        />
      )}

      {/* SUB-VIEW 7: PAGES EXPLORER */}
      {activeSubTab === 'pages' && (
        <Pages
          manifest={report.crawl_manifest}
          summary={report.crawl_summary}
          pageReports={report.page_reports || []}
        />
      )}
    </PillarShell>
  );
}
