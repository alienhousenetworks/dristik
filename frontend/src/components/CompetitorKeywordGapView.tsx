import React, { useState } from 'react';
import {
  Swords,
  TrendingUp,
  FilePlus2,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Sparkles,
  Search,
  CheckCircle2,
} from 'lucide-react';
import { Card, Button, Badge } from './ui';

interface KeywordGapItem {
  keyword: string;
  search_volume: number;
  keyword_difficulty?: number;
  cpc_usd: number;
  competitor_domain: string;
  competitor_rank: number;
  target_rank?: number | null;
  gap_type: 'MISSING_OPPORTUNITY' | 'WEAK_PAGE_2' | string;
  estimated_monthly_visits_opportunity: number;
  recommended_action: string;
  recommended_page_slug: string;
}

interface KeywordGapReport {
  target_domain: string;
  competitor_domains: string[];
  total_missing_keywords: number;
  total_weak_keywords: number;
  total_opportunity_traffic: number;
  opportunities: KeywordGapItem[];
  summary: string;
}

interface CompetitorKeywordGapViewProps {
  targetDomain?: string;
  initialCompetitors?: string[];
  projectId?: string;
}

export function CompetitorKeywordGapView({
  targetDomain = '',
  initialCompetitors = [],
  projectId = 'default_project',
}: CompetitorKeywordGapViewProps) {
  const [competitorInput, setCompetitorInput] = useState(initialCompetitors.join(', '));
  const [report, setReport] = useState<KeywordGapReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cleanTarget = targetDomain || window.location.hostname.replace('www.', '');

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const comps = competitorInput
        .split(',')
        .map((c) => c.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/$/, ''))
        .filter((c) => c && c !== cleanTarget);

      const res = await fetch('/api/v1/intelligence/keywords/gap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_domain: cleanTarget,
          competitor_domains: comps,
          project_id: projectId,
        }),
      });

      if (!res.ok) {
        throw new Error(`Analysis failed with status ${res.status}`);
      }

      const data: KeywordGapReport = await res.json();
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Failed to evaluate competitor keyword gap.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="font-serif text-lg font-bold text-ink flex items-center gap-2">
              <Swords className="h-5 w-5 text-pine" />
              Competitor Keyword Gap Analysis
            </h3>
            <p className="text-xs text-ink-500">
              Discover high-value commercial search terms where rivals rank in the Top 10 but your website has zero presence.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <div className="w-full sm:w-1/3">
            <span className="text-[10px] text-ink-400 uppercase tracking-wider block mb-1">Target Website</span>
            <input
              type="text"
              readOnly
              value={cleanTarget}
              className="w-full px-3 py-1.5 text-xs bg-paper-100/50 dark:bg-ink-800 border border-line rounded text-ink font-mono"
            />
          </div>
          <div className="w-full sm:flex-1">
            <span className="text-[10px] text-ink-400 uppercase tracking-wider block mb-1">
              Rival Domains (Comma-separated)
            </span>
            <input
              type="text"
              placeholder="e.g. competitor1.com, competitor2.com"
              value={competitorInput}
              onChange={(e) => setCompetitorInput(e.target.value)}
              className="w-full px-3 py-1.5 text-xs bg-paper-50 dark:bg-ink-900 border border-line rounded text-ink focus:outline-none focus:border-pine font-mono"
            />
          </div>
          <div className="w-full sm:w-auto sm:self-end">
            <Button
              variant="primary"
              size="sm"
              onClick={runAnalysis}
              disabled={loading || !competitorInput.trim()}
              className="w-full sm:w-auto"
            >
              {loading ? 'Evaluating Gap...' : 'Evaluate Keyword Gap'}
            </Button>
          </div>
        </div>
        {error && <p className="text-xs text-rose-600 dark:text-rose-400">{error}</p>}
      </Card>

      {/* Results Section */}
      {report && (
        <div className="space-y-6">
          {/* Headline Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-4 space-y-1 bg-rose-50/40 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/40">
              <span className="text-[10px] text-rose-700 dark:text-rose-400 font-semibold uppercase tracking-wider block flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" /> Missing Opportunities
              </span>
              <span className="font-serif text-2xl font-bold text-rose-700 dark:text-rose-300 block">
                {report.total_missing_keywords}
              </span>
              <span className="text-[11px] text-ink-500">Rivals rank top 10 · You have 0 presence</span>
            </Card>

            <Card className="p-4 space-y-1 bg-amber-50/40 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/40">
              <span className="text-[10px] text-amber-700 dark:text-amber-400 font-semibold uppercase tracking-wider block">
                Weak Page 2 Terms
              </span>
              <span className="font-serif text-2xl font-bold text-amber-700 dark:text-amber-300 block">
                {report.total_weak_keywords}
              </span>
              <span className="text-[11px] text-ink-500">Ranks #11–#30 · Fast jump candidates</span>
            </Card>

            <Card className="p-4 space-y-1 bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/40">
              <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold uppercase tracking-wider block flex items-center gap-1">
                <TrendingUp className="h-3.5 w-3.5" /> Traffic Gain Potential
              </span>
              <span className="font-serif text-2xl font-bold text-emerald-700 dark:text-emerald-300 block">
                +{report.total_opportunity_traffic.toLocaleString()}
              </span>
              <span className="text-[11px] text-ink-500">Estimated monthly organic visits</span>
            </Card>
          </div>

          {/* Strategic Narrative */}
          <div className="bg-paper-100/60 dark:bg-ink-900/60 border border-line p-3 rounded text-xs text-ink-600 leading-relaxed">
            {report.summary}
          </div>

          {/* Gap Breakdown Table */}
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-line bg-paper-100/60 dark:bg-ink-900/60 text-ink-500 font-medium">
                    <th className="py-2.5 px-3">Keyword</th>
                    <th className="py-2.5 px-3 text-right">Volume</th>
                    <th className="py-2.5 px-3 text-right">KD</th>
                    <th className="py-2.5 px-3">Rival Rank</th>
                    <th className="py-2.5 px-3">Your Rank</th>
                    <th className="py-2.5 px-3 text-right">Potential Traffic</th>
                    <th className="py-2.5 px-3">Recommended Commercial Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {report.opportunities.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-ink-400">
                        No keyword gaps detected between these domains.
                      </td>
                    </tr>
                  ) : (
                    report.opportunities.map((opp, idx) => (
                      <tr key={idx} className="hover:bg-paper-100/40 dark:hover:bg-ink-800/30 transition-colors">
                        <td className="py-2.5 px-3 font-medium text-ink">
                          <div>{opp.keyword}</div>
                          <span className="text-[10px] text-ink-400 font-mono">
                            CPC: ${opp.cpc_usd.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-ink font-mono">
                          {opp.search_volume.toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          {opp.keyword_difficulty != null ? (
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                opp.keyword_difficulty > 65
                                  ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                                  : opp.keyword_difficulty > 35
                                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                                  : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                              }`}
                            >
                              {opp.keyword_difficulty}%
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="font-semibold text-emerald-600 font-mono">
                            #{opp.competitor_rank}
                          </span>{' '}
                          <span className="text-[10px] text-ink-400 truncate max-w-[100px] inline-block align-bottom">
                            ({opp.competitor_domain})
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          {opp.target_rank != null ? (
                            <span className="text-amber-600 font-semibold">#{opp.target_rank}</span>
                          ) : (
                            <Badge tone="bad" className="text-[10px]">
                              Unranked
                            </Badge>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-600">
                          +{opp.estimated_monthly_visits_opportunity.toLocaleString()} /mo
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-1.5">
                            <FilePlus2 className="h-3.5 w-3.5 text-pine shrink-0" />
                            <span className="text-[11px] text-ink font-medium">
                              {opp.recommended_action}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
