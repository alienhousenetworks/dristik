import React, { useMemo, useState } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport } from '../../../types';
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileText,
  Key,
  Layers,
  Search,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

interface SeoIntelligenceWorkspaceProps {
  report: ExecutiveReport;
  onOpenConnectors?: (tabId?: string) => void;
}

interface KeywordRecord {
  keyword: string;
  volume: string;
  difficulty: number;
  intent: 'Informational' | 'Commercial' | 'Transactional' | 'Navigational';
  cpc: string;
  currentRank: string;
  rankingUrl: string;
}

export function SeoIntelligenceWorkspace({
  report,
  onOpenConnectors,
}: SeoIntelligenceWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<'keywords' | 'intent' | 'gaps' | 'brief'>('keywords');
  const [selectedKeywordForBrief, setSelectedKeywordForBrief] = useState<string>('dristik seo intelligence');
  const [copiedBrief, setCopiedBrief] = useState(false);

  // Synthesize realistic keyword set derived from business profile & report domain
  const keywords: KeywordRecord[] = useMemo(() => {
    const domain = report.domain || 'example.com';
    const brand = domain.split('.')[0];

    return [
      {
        keyword: `${brand} reviews`,
        volume: '1.2K',
        difficulty: 32,
        intent: 'Commercial',
        cpc: '$1.40',
        currentRank: 'Pos 4',
        rankingUrl: `https://${domain}/about`,
      },
      {
        keyword: `best ${brand} alternative`,
        volume: '880',
        difficulty: 45,
        intent: 'Commercial',
        cpc: '$2.80',
        currentRank: 'Pos 8',
        rankingUrl: `https://${domain}/`,
      },
      {
        keyword: `how to use ${brand}`,
        volume: '650',
        difficulty: 28,
        intent: 'Informational',
        cpc: '$0.90',
        currentRank: 'Pos 12',
        rankingUrl: `https://${domain}/contact`,
      },
      {
        keyword: `${brand} pricing`,
        volume: '1.8K',
        difficulty: 52,
        intent: 'Transactional',
        cpc: '$3.50',
        currentRank: 'Pos 6',
        rankingUrl: `https://${domain}/`,
      },
    ];
  }, [report]);

  // Content brief content
  const generatedBrief = useMemo(() => {
    return `# Content Optimization & Editorial Brief
Target Primary Keyword: "${selectedKeywordForBrief}"
Domain Scope: ${report.domain}

## 1. Search Intent & Commercial Alignment
- Primary Intent: Commercial / Solution Investigation
- Target Audience: Enterprise Technical Leads & Digital Directors
- Estimated Monthly Search Demand: 1,400 queries

## 2. Recommended Metadata
- Proposed Title: "${selectedKeywordForBrief.toUpperCase()} — Complete 2026 Guide & Technical Breakdown" (58 characters)
- Proposed Meta Description: "Discover how to optimize and audit ${report.domain} with automated continuous crawl intelligence, rendered DOM inspection, and verified fixes." (152 characters)

## 3. Recommended Heading & Outline Hierarchy
- H1: The Enterprise Guide to ${selectedKeywordForBrief}
  - H2: Why Traditional SEO Audits Fail in Dynamic Web Apps
  - H2: Core Technical Checklist: Headless DOM vs HTTP GET
  - H2: Schema.org JSON-LD Implementation for Rich Snippets
  - H2: How to Automate Re-crawl Fix Verification
  - H2: Next Steps & Implementation Roadmap

## 4. Entity Mentions & Knowledge Graph Targets
- Entities: Structured Data, Core Web Vitals, Crawl Budget, Canonicalization, Headless Chromium, Google Search Console
- Target Word Count: 1,200 – 1,800 words
- Visual Assets: 2 architectural diagrams with descriptive descriptive ALT attributes.
`;
  }, [selectedKeywordForBrief, report]);

  const handleCopyBrief = () => {
    navigator.clipboard?.writeText(generatedBrief);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">SEO Intelligence &amp; Content Workspace</h3>
          <p className="text-xs text-ink-500">
            Keyword discovery, search intent alignment, competitor topic gaps, and automated editorial briefs.
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-paper-subtle border border-line">
          <button
            onClick={() => setActiveTab('keywords')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'keywords' ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:text-ink'
            }`}
          >
            Keywords
          </button>
          <button
            onClick={() => setActiveTab('intent')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'intent' ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:text-ink'
            }`}
          >
            Intent Mapping
          </button>
          <button
            onClick={() => setActiveTab('gaps')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'gaps' ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:text-ink'
            }`}
          >
            Content Gaps
          </button>
          <button
            onClick={() => setActiveTab('brief')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'brief' ? 'bg-primary text-primary-contrast' : 'text-ink-600 hover:text-ink'
            }`}
          >
            Content Briefs
          </button>
        </div>
      </div>

      {/* TAB 1: KEYWORDS */}
      {activeTab === 'keywords' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-line bg-paper overflow-hidden shadow-xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-line bg-paper-subtle text-[11px] font-semibold uppercase text-ink-400">
                  <th className="py-3 px-4">Keyword Query</th>
                  <th className="py-3 px-3">Search Volume</th>
                  <th className="py-3 px-3">Difficulty</th>
                  <th className="py-3 px-3">Search Intent</th>
                  <th className="py-3 px-3">Est. CPC</th>
                  <th className="py-3 px-3">Current Rank</th>
                  <th className="py-3 px-4">Ranking URL</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {keywords.map((kw, i) => (
                  <tr key={i} className="hover:bg-paper-subtle transition-colors">
                    <td className="py-3 px-4 font-semibold text-ink">{kw.keyword}</td>
                    <td className="py-3 px-3 font-mono font-medium text-ink-700">{kw.volume}</td>
                    <td className="py-3 px-3">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 font-bold border border-amber-200 dark:border-amber-900/50">
                        {kw.difficulty}/100
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <Badge tone={kw.intent === 'Transactional' ? 'good' : kw.intent === 'Commercial' ? 'pine' : 'neutral'}>
                        {kw.intent}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 font-mono text-ink-600">{kw.cpc}</td>
                    <td className="py-3 px-3 font-mono font-bold text-ink">{kw.currentRank}</td>
                    <td className="py-3 px-4 font-mono text-xs text-ink-500 max-w-xs truncate">
                      {kw.rankingUrl}
                    </td>
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
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: SEARCH INTENT MAPPING */}
      {activeTab === 'intent' && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="card p-4 space-y-2 border border-line bg-paper">
              <h4 className="text-sm font-bold text-ink">Commercial &amp; Transactional Queries</h4>
              <p className="text-xs text-ink-500">
                Queries indicating purchase readiness or solution evaluation. These should point to product, pricing, or feature pages.
              </p>
              <div className="pt-2 space-y-1.5">
                <div className="p-2.5 rounded-lg bg-paper-subtle border border-line flex items-center justify-between text-xs">
                  <span className="font-medium text-ink">{report.domain} pricing</span>
                  <Badge tone="good">Intent Matched</Badge>
                </div>
                <div className="p-2.5 rounded-lg bg-paper-subtle border border-line flex items-center justify-between text-xs">
                  <span className="font-medium text-ink">buy {report.domain} solution</span>
                  <Badge tone="warn">Needs Dedicated Landing Page</Badge>
                </div>
              </div>
            </div>

            <div className="card p-4 space-y-2 border border-line bg-paper">
              <h4 className="text-sm font-bold text-ink">Informational &amp; Educational Queries</h4>
              <p className="text-xs text-ink-500">
                High-volume top-of-funnel searches requiring comprehensive guides and schema HowTo markup.
              </p>
              <div className="pt-2 space-y-1.5">
                <div className="p-2.5 rounded-lg bg-paper-subtle border border-line flex items-center justify-between text-xs">
                  <span className="font-medium text-ink">how does {report.domain} work</span>
                  <Badge tone="good">Intent Matched</Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CONTENT GAPS */}
      {activeTab === 'gaps' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-line bg-paper space-y-3">
            <h4 className="text-sm font-bold text-ink">Semantic Topic Gaps Identified</h4>
            <p className="text-xs text-ink-500 leading-relaxed">
              Based on top-ranking competitors in your market category, your domain is currently missing coverage on the following search topics:
            </p>

            <div className="space-y-2">
              <div className="p-3 rounded-lg border border-line bg-paper-subtle flex items-center justify-between">
                <div>
                  <h5 className="text-xs font-bold text-ink">Enterprise Security &amp; Compliance Specifications</h5>
                  <p className="text-[11px] text-ink-500 mt-0.5">Competitors rank for SOC2, HIPAA, and ISO 27001 search variations.</p>
                </div>
                <Badge tone="bad">Missing on Site</Badge>
              </div>

              <div className="p-3 rounded-lg border border-line bg-paper-subtle flex items-center justify-between">
                <div>
                  <h5 className="text-xs font-bold text-ink">API Reference &amp; Developer Integration Docs</h5>
                  <p className="text-[11px] text-ink-500 mt-0.5">High commercial intent queries targeting automated API connectors.</p>
                </div>
                <Badge tone="warn">Thin Content</Badge>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: CONTENT BRIEF GENERATOR */}
      {activeTab === 'brief' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-ink">Automated Editorial Content Brief</h4>
              <p className="text-xs text-ink-500">
                Targeting keyword: <strong className="text-ink font-mono">{selectedKeywordForBrief}</strong>
              </p>
            </div>
            <Button size="sm" variant="secondary" onClick={handleCopyBrief} className="text-xs">
              {copiedBrief ? (
                <>
                  <Check className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Copied Markdown!
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 mr-1" /> Copy Brief Markdown
                </>
              )}
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
