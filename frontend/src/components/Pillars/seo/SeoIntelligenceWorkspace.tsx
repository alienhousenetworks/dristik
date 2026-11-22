import React, { useMemo, useState } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport } from '../../../types';
import { ArrowRight, Check, Copy, Plug } from 'lucide-react';

interface SeoIntelligenceWorkspaceProps {
  report: ExecutiveReport;
  scorecard?: any;
  onOpenConnectors?: (tabId?: string) => void;
  onNavigateTab?: (tabId: string) => void;
}

interface KeywordRecord {
  keyword: string;
  volume: string;
  difficulty: string;
  intent: 'Informational' | 'Commercial' | 'Transactional' | 'Navigational' | 'Local';
  cpc: string;
  currentRank: string;
  rankingUrl: string;
  source: string;
}

function classifyIntent(text: string, url: string): KeywordRecord['intent'] {
  const blob = `${text} ${url}`.toLowerCase();
  if (/(pricing|buy|shop|checkout|cart|product|order|subscribe)/.test(blob)) return 'Transactional';
  if (/(compare|vs|best|review|alternative|solution|service|enterprise)/.test(blob)) return 'Commercial';
  if (/(how|what|why|guide|blog|docs|faq|tutorial|learn)/.test(blob)) return 'Informational';
  if (/(contact|location|store|near me|address)/.test(blob)) return 'Local';
  return 'Navigational';
}

export function SeoIntelligenceWorkspace({
  report,
  scorecard,
  onOpenConnectors,
  onNavigateTab,
}: SeoIntelligenceWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<'keywords' | 'intent' | 'gaps' | 'cannibalization' | 'brief'>('keywords');
  const [copiedBrief, setCopiedBrief] = useState(false);

  const contentDim = useMemo(() => {
    const dims = scorecard?.dimensions || (report as any)?.mathematical_scorecard?.dimensions || [];
    return dims.find((d: any) => d.dimension_id === 'content_quality_intent') || null;
  }, [scorecard, report]);

  const pages = useMemo(
    () => ((report.crawl_manifest?.pages || report.page_reports || []) as Array<Record<string, any>>),
    [report]
  );

  // Extract real connected GSC / keyword provider queries ONLY — never fabricate volumes/KD/CPC/ranks
  const { keywords, hasConnectedDemandProvider } = useMemo(() => {
    const gsc = (report as any).google_performance?.search_console;
    const gscRows: any[] = Array.isArray(gsc?.top_queries) ? gsc.top_queries : [];
    const demandRows: any[] = Array.isArray((report as any).search_demand?.keywords)
      ? (report as any).search_demand.keywords
      : [];

    if (demandRows.length > 0) {
      return {
        hasConnectedDemandProvider: true,
        keywords: demandRows.map((row: any): KeywordRecord => ({
          keyword: String(row.keyword || row.query || ''),
          volume: row.search_volume != null ? Number(row.search_volume).toLocaleString() : 'Unmeasured',
          difficulty: row.difficulty != null ? `${row.difficulty}/100` : 'Unmeasured',
          intent: classifyIntent(String(row.keyword || ''), String(row.url || '')),
          cpc: row.cpc != null ? `$${Number(row.cpc).toFixed(2)}` : 'Unmeasured',
          currentRank: row.position != null ? `Pos ${Number(row.position).toFixed(1)}` : 'Unmeasured',
          rankingUrl: String(row.url || report.website_url || ''),
          source: String(row.provider || 'Keyword Provider'),
        })),
      };
    }

    if (gscRows.length > 0) {
      return {
        hasConnectedDemandProvider: true,
        keywords: gscRows.map((row: any): KeywordRecord => ({
          keyword: String(row.query || row.keys?.[0] || ''),
          volume: row.impressions != null ? `${Number(row.impressions).toLocaleString()} impr.` : 'Unmeasured',
          difficulty: 'Unconnected',
          intent: classifyIntent(String(row.query || ''), String(row.page || '')),
          cpc: 'Unconnected',
          currentRank: row.position != null ? `Avg ${Number(row.position).toFixed(1)}` : 'Unmeasured',
          rankingUrl: String(row.page || report.website_url || ''),
          source: 'Google Search Console',
        })),
      };
    }

    // Unconnected fallback: derive strictly from actual crawled page titles & H1s, disclosing Unconnected metrics honestly
    const extracted: KeywordRecord[] = [];
    for (const p of pages) {
      const h1 = Array.isArray(p.h1) ? p.h1[0] : p.h1;
      const topic = String(h1 || p.title || '').trim();
      if (!topic) continue;
      extracted.push({
        keyword: topic,
        volume: 'Unconnected',
        difficulty: 'Unconnected',
        intent: classifyIntent(topic, String(p.url || '')),
        cpc: 'Unconnected',
        currentRank: 'Unconnected',
        rankingUrl: String(p.url || ''),
        source: 'Crawled DOM Topic',
      });
    }
    return { hasConnectedDemandProvider: false, keywords: extracted };
  }, [report, pages]);

  const [selectedKeywordForBrief, setSelectedKeywordForBrief] = useState<string>(
    () => keywords[0]?.keyword || report.domain || 'target topic'
  );

  // Detect real title/H1 cannibalization strictly from crawled pages
  const cannibalizationClusters = useMemo(() => {
    const groups = new Map<string, string[]>();
    for (const p of pages) {
      const key = String(p.title || '').trim().toLowerCase();
      if (!key) continue;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(String(p.url || ''));
    }
    return Array.from(groups.entries())
      .filter(([, urls]) => urls.length > 1)
      .map(([topic, urls]) => ({ topic, urls }));
  }, [pages]);

  // Competitor content gaps strictly from real competitor_seo_parity data (never fabricated SOC2/HIPAA)
  const competitorGaps: Array<{ topic: string; detail: string; status: string }> = useMemo(() => {
    const comp = (report as any).competitor_seo_parity;
    if (Array.isArray(comp?.content_gaps) && comp.content_gaps.length > 0) {
      return comp.content_gaps.map((g: any) => ({
        topic: String(g.topic || g.title || 'Content Gap'),
        detail: String(g.detail || g.reason || 'Observed in competitor crawl comparison.'),
        status: String(g.status || 'Gap Observed'),
      }));
    }
    return [];
  }, [report]);

  // Grounded editorial content brief using actual crawled headings & entities (zero fabricated demand numbers)
  const generatedBrief = useMemo(() => {
    const matchingPage =
      pages.find((p) => {
        const h1 = Array.isArray(p.h1) ? p.h1[0] : p.h1;
        return String(h1 || p.title || '').toLowerCase() === selectedKeywordForBrief.toLowerCase();
      }) || pages[0];
    const extractedH2s: string[] = Array.isArray(matchingPage?.h2) ? matchingPage.h2 : [];
    const entities = Array.from(
      new Set(pages.flatMap((p) => (Array.isArray(p.schema_types) ? p.schema_types : [])))
    );
    const intent = classifyIntent(selectedKeywordForBrief, String(matchingPage?.url || ''));
    const targetUrl = String(matchingPage?.url || report.website_url || `https://${report.domain}/`);

    return `# Content Optimization & Editorial Brief
Target Topic / Keyword: "${selectedKeywordForBrief}"
Domain Scope: ${report.domain}
Target URL: ${targetUrl}

## 1. Search Intent & Grounding Disclosure
- Classified Search Intent: ${intent}
- Search Volume & Difficulty: ${hasConnectedDemandProvider ? 'Sourced from connected provider' : 'Not measured (connect GSC or Keyword/SERP provider for verified search demand)'}

## 2. Recommended Metadata
- Proposed Title: "${selectedKeywordForBrief} | ${report.domain}"
- Proposed Meta Description: Write a unique 120–155 character summary directly answering ${intent.toLowerCase()} user intent for ${selectedKeywordForBrief}.

## 3. Observed & Recommended Heading Outline
- H1: ${selectedKeywordForBrief}
${extractedH2s.length > 0 ? extractedH2s.map((h) => `  - H2 (Observed): ${h}`).join('\n') : '  - H2: Core overview and direct answer\n  - H2: Evidence, specifications, and customer proof\n  - H2: Frequently asked questions & next steps'}

## 4. Entities, Internal Linking & Acceptance Criteria
- Observed Schema Entities on Site: ${entities.length > 0 ? entities.join(', ') : 'None detected (add appropriate Schema.org JSON-LD)'}
- Internal Links: Link contextually from homepage/category hub to ${targetUrl} using descriptive anchor text.
- Factual Validation: All product specs, pricing, and claims must be verified against source pages before publication.
`;
  }, [selectedKeywordForBrief, report, pages, hasConnectedDemandProvider]);

  const handleCopyBrief = () => {
    navigator.clipboard?.writeText(generatedBrief);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">SEO Intelligence &amp; Content Workspace</h3>
          <p className="text-xs text-ink-500">
            Source-grounded keyword discovery, search intent classification, cannibalization analysis, and editorial content briefs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-paper-subtle border border-line">
          {[
            { id: 'keywords', label: 'Keywords' },
            { id: 'intent', label: 'Intent Mapping' },
            { id: 'gaps', label: 'Content Gaps' },
            { id: 'cannibalization', label: `Cannibalization (${cannibalizationClusters.length})` },
            { id: 'brief', label: 'Content Briefs' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                activeTab === t.id ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:text-ink'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {contentDim && (
        <div className="rounded-xl border border-line bg-paper-subtle p-4 flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-ink">Content Quality &amp; Search Intent Audit Score</span>
              <Badge tone={contentDim.score != null && contentDim.score >= 70 ? 'good' : contentDim.score != null && contentDim.score >= 50 ? 'warn' : 'critical'}>
                {contentDim.score != null ? `${Math.round(contentDim.score)}/100` : 'Unmeasured'}
              </Badge>
              <span className="text-[11px] font-mono text-ink-500">
                Weight: {Math.round(contentDim.configured_weight * 100)}% · Eff: {contentDim.effective_weight != null ? `${Math.round(contentDim.effective_weight * 100)}%` : 'Excluded'}
              </span>
            </div>
            <p className="text-xs text-ink-500">
              {contentDim.passed_checks_count} passed · {contentDim.failed_checks_count ?? Math.max(0, contentDim.executed_checks_count - contentDim.passed_checks_count)} failed of {contentDim.executed_checks_count} executed checks.
            </p>
          </div>
          {onNavigateTab && (
            <Button size="sm" variant="secondary" onClick={() => onNavigateTab('issues')} className="text-xs">
              View All Content Issues <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          )}
        </div>
      )}

      {!hasConnectedDemandProvider && (
        <div className="p-3.5 rounded-xl border border-amber-300/60 bg-amber-50/40 dark:bg-amber-950/20 flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="text-ink-700 dark:text-ink-300">
            <strong>Demand Provider Unconnected:</strong> Showing topics extracted from crawled pages. Search volume, keyword difficulty, CPC, and live rank stay <code>Unconnected</code> rather than fabricated estimates.
          </span>
          {onOpenConnectors && (
            <Button size="sm" variant="secondary" onClick={() => onOpenConnectors('keyword_serp_provider')} className="text-xs h-7">
              <Plug className="w-3.5 h-3.5 mr-1" /> Connect GSC / Keyword Provider
            </Button>
          )}
        </div>
      )}

      {activeTab === 'keywords' && (
        <div className="rounded-xl border border-line bg-paper overflow-x-auto shadow-xs">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-subtle text-[11px] font-semibold uppercase text-ink-400">
                <th className="py-3 px-4">Keyword Query</th>
                <th className="py-3 px-3">Search Volume</th>
                <th className="py-3 px-3">Difficulty</th>
                <th className="py-3 px-3">Search Intent</th>
                <th className="py-3 px-3">CPC</th>
                <th className="py-3 px-3">Current Rank</th>
                <th className="py-3 px-4">Target URL</th>
                <th className="py-3 px-3">Source</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {keywords.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-ink-500">
                    No keywords or crawled page topics available yet.
                  </td>
                </tr>
              ) : (
                keywords.map((kw, i) => (
                  <tr key={i} className="hover:bg-paper-subtle">
                    <td className="py-3 px-4 font-semibold text-ink">{kw.keyword}</td>
                    <td className="py-3 px-3 font-mono text-ink-600">{kw.volume}</td>
                    <td className="py-3 px-3 font-mono text-ink-600">{kw.difficulty}</td>
                    <td className="py-3 px-3">
                      <Badge tone={kw.intent === 'Transactional' ? 'good' : kw.intent === 'Commercial' ? 'pine' : 'neutral'}>
                        {kw.intent}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 font-mono text-ink-600">{kw.cpc}</td>
                    <td className="py-3 px-3 font-mono text-ink-600">{kw.currentRank}</td>
                    <td className="py-3 px-4 font-mono text-xs text-ink-500 max-w-xs truncate">{kw.rankingUrl}</td>
                    <td className="py-3 px-3 text-[11px] text-ink-500">{kw.source}</td>
                    <td className="py-3 px-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setSelectedKeywordForBrief(kw.keyword);
                          setActiveTab('brief');
                        }}
                        className="text-xs h-7 px-2"
                      >
                        Create Brief <ArrowRight className="w-3 h-3 ml-1" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'intent' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(['Transactional', 'Commercial', 'Informational', 'Navigational', 'Local'] as const).map((intentName) => {
            const matching = keywords.filter((k) => k.intent === intentName);
            return (
              <div key={intentName} className="card p-4 space-y-2 border border-line bg-paper">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-ink">{intentName} Intent</h4>
                  <Badge tone="neutral">{matching.length} URL(s)</Badge>
                </div>
                {matching.length > 0 ? (
                  <div className="space-y-1.5 pt-1">
                    {matching.slice(0, 6).map((m, idx) => (
                      <div key={idx} className="p-2 rounded bg-paper-subtle border border-line text-xs">
                        <p className="font-semibold text-ink truncate">{m.keyword}</p>
                        <p className="font-mono text-[10px] text-ink-400 truncate">{m.rankingUrl}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-ink-500">No crawled pages classified under {intentName.toLowerCase()} intent.</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {activeTab === 'gaps' && (
        <div className="p-4 rounded-xl border border-line bg-paper space-y-3">
          <h4 className="text-sm font-bold text-ink">Competitive Content Gap Analysis</h4>
          {competitorGaps.length > 0 ? (
            <div className="space-y-2">
              {competitorGaps.map((g, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-line bg-paper-subtle flex items-center justify-between">
                  <div>
                    <h5 className="text-xs font-bold text-ink">{g.topic}</h5>
                    <p className="text-[11px] text-ink-500 mt-0.5">{g.detail}</p>
                  </div>
                  <Badge tone="warn">{g.status}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-5 rounded-lg border border-dashed border-line bg-paper-subtle text-xs text-ink-500 space-y-2">
              <p>
                <strong>Competitor Dataset Unavailable:</strong> No verified competitor SERP or crawl comparison was attached to this audit. Dristik does not fabricate competitor topic gaps without real source evidence.
              </p>
              {onOpenConnectors && (
                <Button size="sm" variant="secondary" onClick={() => onOpenConnectors('keyword_serp_provider')} className="text-xs">
                  Connect SERP / Competitor Provider
                </Button>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'cannibalization' && (
        <div className="p-4 rounded-xl border border-line bg-paper space-y-3">
          <h4 className="text-sm font-bold text-ink">Keyword &amp; Title Cannibalization Candidates</h4>
          {cannibalizationClusters.length > 0 ? (
            <div className="space-y-2">
              {cannibalizationClusters.map((c, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-line bg-paper-subtle space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <strong className="text-ink">Overlapping Topic: "{c.topic}"</strong>
                    <Badge tone="warn">{c.urls.length} Competing URLs</Badge>
                  </div>
                  {c.urls.map((u) => (
                    <div key={u} className="font-mono text-[11px] text-ink-500 truncate">• {u}</div>
                  ))}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-ink-500">No duplicate-title cannibalization conflicts detected across the {pages.length} crawled page(s).</p>
          )}
        </div>
      )}

      {activeTab === 'brief' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-ink">Grounded Editorial Content Brief</h4>
              <p className="text-xs text-ink-500">
                Targeting: <strong className="text-ink font-mono">{selectedKeywordForBrief}</strong>
              </p>
            </div>
            <Button size="sm" variant="secondary" onClick={handleCopyBrief} className="text-xs">
              {copiedBrief ? <><Check className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Copied</> : <><Copy className="w-3.5 h-3.5 mr-1" /> Copy Brief Markdown</>}
            </Button>
          </div>
          <div className="p-5 rounded-xl border border-line bg-paper-subtle font-mono text-xs text-ink overflow-x-auto">
            <pre className="whitespace-pre-wrap leading-relaxed">{generatedBrief}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
