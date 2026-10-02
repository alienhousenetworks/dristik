import React, { useState, useEffect } from 'react';
import {
  Search,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Sparkles,
  RefreshCw,
  Trash2,
  TrendingUp,
  Award,
  Globe,
  Tag,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Layers,
} from 'lucide-react';
import { Card, Button, Badge, ScorePill } from './ui';

interface TrackedKeyword {
  keyword_id: string;
  project_id: string;
  domain: string;
  keyword: string;
  target_url?: string;
  intent: string;
  search_volume: number;
  cpc_usd: number;
  competition: number;
  keyword_difficulty?: number;
  current_position?: number | null;
  previous_position?: number | null;
  best_position?: number | null;
  position_delta: number;
  serp_features: string[];
  has_ai_overview: boolean;
  has_featured_snippet: boolean;
  tags: string[];
}

interface MovementSummary {
  total_tracked: number;
  improved_count: number;
  declined_count: number;
  stable_count: number;
  top_3_count: number;
  top_10_count: number;
  ai_overview_count: number;
}

interface KeywordTrackingViewProps {
  projectId?: string;
  domain?: string;
  competitors?: string[];
}

export function KeywordTrackingView({
  projectId = 'default_project',
  domain = '',
  competitors = [],
}: KeywordTrackingViewProps) {
  const [keywords, setKeywords] = useState<TrackedKeyword[]>([]);
  const [summary, setSummary] = useState<MovementSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newIntent, setNewIntent] = useState('Commercial');
  const [newTargetUrl, setNewTargetUrl] = useState('');
  const [searchFilter, setSearchFilter] = useState('');

  const targetDomain = domain || window.location.hostname.replace('www.', '');

  const fetchKeywords = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/intelligence/keywords?project_id=${encodeURIComponent(projectId)}`);
      if (res.ok) {
        const data = await res.json();
        setKeywords(data);
      }
      const sumRes = await fetch(`/api/v1/intelligence/keywords/movement-summary?project_id=${encodeURIComponent(projectId)}`);
      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSummary(sumData);
      }
    } catch (e) {
      console.warn('Failed to load tracked keywords', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeywords();
  }, [projectId]);

  const handleAddKeyword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;

    try {
      const res = await fetch('/api/v1/intelligence/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          domain: targetDomain,
          keyword: newKeyword.trim(),
          intent: newIntent,
          target_url: newTargetUrl || undefined,
        }),
      });
      if (res.ok) {
        setNewKeyword('');
        setNewTargetUrl('');
        setShowAddModal(false);
        fetchKeywords();
      }
    } catch (e) {
      console.error('Failed to add keyword', e);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await fetch('/api/v1/intelligence/keywords/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          domain: targetDomain,
          competitor_domains: competitors,
        }),
      });
      await fetchKeywords();
    } catch (e) {
      console.error('Sync failed', e);
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = async (kwId: string) => {
    if (!confirm('Stop tracking this keyword?')) return;
    try {
      await fetch(`/api/v1/intelligence/keywords/${kwId}?project_id=${encodeURIComponent(projectId)}`, {
        method: 'DELETE',
      });
      fetchKeywords();
    } catch (e) {
      console.error('Delete failed', e);
    }
  };

  const filtered = keywords.filter((k) =>
    k.keyword.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-xl font-bold text-ink">Continuous Keyword & SERP Tracking</h2>
          <p className="text-xs text-ink-500">
            Daily Google rank positions, AI Overview coverage, SERP features, and competitor movement.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing SERP...' : 'Sync Live SERP'}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            Track Keyword
          </Button>
        </div>
      </div>

      {/* Movement Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="p-3 space-y-1">
          <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Tracked</span>
          <span className="font-serif text-xl font-bold text-ink block">{summary?.total_tracked || keywords.length}</span>
          <span className="text-[11px] text-ink-400">Total terms</span>
        </Card>
        <Card className="p-3 space-y-1">
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block flex items-center gap-1">
            <TrendingUp className="h-3 w-3" /> Improved
          </span>
          <span className="font-serif text-xl font-bold text-emerald-600 block">+{summary?.improved_count || 0}</span>
          <span className="text-[11px] text-ink-400">Past 24 hours</span>
        </Card>
        <Card className="p-3 space-y-1">
          <span className="text-[10px] text-rose-600 dark:text-rose-400 uppercase tracking-wider block flex items-center gap-1">
            <ArrowDownRight className="h-3 w-3" /> Declined
          </span>
          <span className="font-serif text-xl font-bold text-rose-600 block">-{summary?.declined_count || 0}</span>
          <span className="text-[11px] text-ink-400">Past 24 hours</span>
        </Card>
        <Card className="p-3 space-y-1">
          <span className="text-[10px] text-amber-600 uppercase tracking-wider block flex items-center gap-1">
            <Award className="h-3 w-3" /> Top 3
          </span>
          <span className="font-serif text-xl font-bold text-ink block">{summary?.top_3_count || 0}</span>
          <span className="text-[11px] text-ink-400">Prime positions</span>
        </Card>
        <Card className="p-3 space-y-1">
          <span className="text-[10px] text-blue-600 uppercase tracking-wider block">Top 10</span>
          <span className="font-serif text-xl font-bold text-ink block">{summary?.top_10_count || 0}</span>
          <span className="text-[11px] text-ink-400">Page 1 share</span>
        </Card>
        <Card className="p-3 space-y-1">
          <span className="text-[10px] text-purple-600 uppercase tracking-wider block flex items-center gap-1">
            <Sparkles className="h-3 w-3" /> AI Overview
          </span>
          <span className="font-serif text-xl font-bold text-purple-600 block">{summary?.ai_overview_count || 0}</span>
          <span className="text-[11px] text-ink-400">Generative results</span>
        </Card>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-ink-400" />
          <input
            type="text"
            placeholder="Search tracked keywords..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-paper-50 dark:bg-ink-900 border border-line rounded-md text-ink placeholder:text-ink-400 focus:outline-none focus:border-pine"
          />
        </div>
      </div>

      {/* Keywords Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-100/60 dark:bg-ink-900/60 text-ink-500 font-medium">
                <th className="py-2.5 px-3">Keyword</th>
                <th className="py-2.5 px-3">Intent</th>
                <th className="py-2.5 px-3 text-right">Volume</th>
                <th className="py-2.5 px-3 text-right">Rank</th>
                <th className="py-2.5 px-3 text-center">Movement</th>
                <th className="py-2.5 px-3 text-right">Best</th>
                <th className="py-2.5 px-3">SERP Features</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-ink-400">
                    {loading ? (
                      'Loading tracked keywords...'
                    ) : (
                      <div className="space-y-2">
                        <p>No keywords tracked yet for this domain.</p>
                        <Button size="sm" variant="secondary" onClick={() => setShowAddModal(true)}>
                          Track Your First Keyword
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ) : (
                filtered.map((kw) => {
                  const delta = kw.position_delta;
                  return (
                    <tr key={kw.keyword_id} className="hover:bg-paper-100/40 dark:hover:bg-ink-800/30 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-ink">
                        <div>{kw.keyword}</div>
                        {kw.target_url && (
                          <span className="text-[10px] text-ink-400 truncate max-w-[200px] block">
                            {kw.target_url}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge tone="neutral" className="text-[10px] capitalize">
                          {kw.intent}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right text-ink font-mono">
                        {kw.search_volume > 0 ? kw.search_volume.toLocaleString() : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {kw.current_position != null ? (
                          <span
                            className={`font-semibold font-mono ${
                              kw.current_position <= 3
                                ? 'text-amber-600 dark:text-amber-400'
                                : kw.current_position <= 10
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-ink'
                            }`}
                          >
                            #{kw.current_position}
                          </span>
                        ) : (
                          <span className="text-ink-400">&gt; 100</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {delta > 0 ? (
                          <span className="inline-flex items-center text-emerald-600 font-semibold text-[11px]">
                            <ArrowUpRight className="h-3 w-3" /> +{delta}
                          </span>
                        ) : delta < 0 ? (
                          <span className="inline-flex items-center text-rose-600 font-semibold text-[11px]">
                            <ArrowDownRight className="h-3 w-3" /> {delta}
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-ink-400 text-[11px]">
                            <Minus className="h-3 w-3" />
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-ink-400 font-mono">
                        {kw.best_position ? `#${kw.best_position}` : '—'}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {kw.has_ai_overview && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 font-medium inline-flex items-center gap-0.5">
                              <Sparkles className="h-2.5 w-2.5" /> AI
                            </span>
                          )}
                          {kw.has_featured_snippet && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 font-medium">
                              Snippet
                            </span>
                          )}
                          {kw.serp_features?.includes('people_also_ask') && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 font-medium">
                              PAA
                            </span>
                          )}
                          {kw.serp_features?.includes('local_pack') && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 font-medium">
                              Map
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleDelete(kw.keyword_id)}
                          className="text-ink-400 hover:text-rose-600 p-1 transition-colors"
                          title="Stop Tracking"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add Keyword Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-md p-6 space-y-4 bg-paper dark:bg-ink-950">
            <h3 className="font-serif text-lg font-bold text-ink">Add Tracked Keyword</h3>
            <form onSubmit={handleAddKeyword} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-ink block mb-1">Search Keyword *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AI automation software"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-paper-50 dark:bg-ink-900 border border-line rounded text-ink focus:outline-none focus:border-pine"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-ink block mb-1">Intent</label>
                <select
                  value={newIntent}
                  onChange={(e) => setNewIntent(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-paper-50 dark:bg-ink-900 border border-line rounded text-ink focus:outline-none focus:border-pine"
                >
                  <option value="Commercial">Commercial (Buyer Search)</option>
                  <option value="Informational">Informational</option>
                  <option value="Transactional">Transactional</option>
                  <option value="Navigational">Navigational</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-ink block mb-1">Target URL (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. /solutions/ai-automation"
                  value={newTargetUrl}
                  onChange={(e) => setNewTargetUrl(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-paper-50 dark:bg-ink-900 border border-line rounded text-ink focus:outline-none focus:border-pine"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" size="sm" onClick={() => setShowAddModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm">
                  Add Keyword
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
