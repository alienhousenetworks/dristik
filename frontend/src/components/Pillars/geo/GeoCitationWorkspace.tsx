import React, { useMemo, useState } from 'react';
import { Card } from '../../ui';
import { GeoEnterpriseBundle } from '../../../services/geoApi';
import { ExternalLink, Globe, Link2, Network, Target } from 'lucide-react';

interface GeoCitationWorkspaceProps {
  bundle: GeoEnterpriseBundle;
}

export function GeoCitationWorkspace({ bundle }: GeoCitationWorkspaceProps) {
  const [view, setView] = useState<'explorer' | 'graph' | 'opportunities'>('explorer');
  const [ownershipFilter, setOwnershipFilter] = useState<string>('all');
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  const graph = bundle.citation_graph || {};
  const summary = graph.summary || {};
  const opportunities: Array<Record<string, any>> = graph.opportunities || [];
  const topDomains: Array<Record<string, any>> = graph.top_domains || [];

  const filteredCitations = useMemo(() => {
    return bundle.citations.filter((c) => {
      if (ownershipFilter !== 'all' && c.source_ownership !== ownershipFilter) return false;
      if (platformFilter !== 'all' && c.platform_id !== platformFilter) return false;
      if (search.trim() && !`${c.domain} ${c.cited_url} ${c.publisher}`.toLowerCase().includes(search.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [bundle.citations, ownershipFilter, platformFilter, search]);

  const platformsSeen = useMemo(
    () => Array.from(new Set(bundle.citations.map((c) => c.platform_id))).sort(),
    [bundle.citations],
  );

  return (
    <div className="space-y-6">
      {/* Citation Summary Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-4">
          <span className="font-mono text-[10px] uppercase text-ink-500">Total Citations Observed</span>
          <div className="text-2xl font-bold text-ink mt-1">{summary.total_citations ?? bundle.citations.length}</div>
        </Card>
        <Card className="p-4">
          <span className="font-mono text-[10px] uppercase text-ink-500">Owned Citations</span>
          <div className="text-2xl font-bold text-good mt-1">{summary.owned_citations ?? 0}</div>
        </Card>
        <Card className="p-4">
          <span className="font-mono text-[10px] uppercase text-ink-500">Independent Sources</span>
          <div className="text-2xl font-bold text-pine mt-1">{summary.independent_citations ?? 0}</div>
        </Card>
        <Card className="p-4">
          <span className="font-mono text-[10px] uppercase text-ink-500">Competitor Citations</span>
          <div className="text-2xl font-bold text-warn mt-1">{summary.competitor_citations ?? 0}</div>
        </Card>
      </div>

      {/* View Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          {[
            { id: 'explorer', label: '1. Citation Explorer', icon: Link2 },
            { id: 'graph', label: '2. Citation Source Graph', icon: Network },
            { id: 'opportunities', label: `3. Source Opportunities (${opportunities.length})`, icon: Target },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setView(id as any)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold border ${
                view === id ? 'bg-ink text-white border-ink' : 'bg-white text-ink-700 border-line'
              }`}
            >
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>
        <span className="text-[11px] font-mono text-ink-500">
          Citation frequency != authority; ownership, independence &amp; claim support tracked separately.
        </span>
      </div>

      {view === 'explorer' && (
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap gap-2 text-xs">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter domain, URL, or publisher..."
              className="px-3 py-1.5 border border-line rounded bg-white flex-1 min-w-[200px]"
            />
            <select value={ownershipFilter} onChange={(e) => setOwnershipFilter(e.target.value)} className="px-2.5 py-1.5 border border-line rounded bg-white font-mono">
              <option value="all">All Ownership</option>
              <option value="owned">Owned</option>
              <option value="independent">Independent</option>
              <option value="earned">Earned</option>
              <option value="competitor">Competitor</option>
            </select>
            <select value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)} className="px-2.5 py-1.5 border border-line rounded bg-white font-mono">
              <option value="all">All Platforms</option>
              {platformsSeen.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          {filteredCitations.length === 0 ? (
            <p className="text-xs text-ink-500">
              No citations captured for the active filter. Connect a search-grounded provider (e.g. Perplexity Sonar or Gemini Search Grounding) to capture live source citations.
            </p>
          ) : (
            <div className="overflow-x-auto border border-line rounded">
              <table className="w-full text-xs text-left">
                <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
                  <tr>
                    <th className="p-2.5">Domain / Publisher</th>
                    <th className="p-2.5">Cited URL</th>
                    <th className="p-2.5">Ownership</th>
                    <th className="p-2.5">Category</th>
                    <th className="p-2.5">Platform</th>
                    <th className="p-2.5">Competitors</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {filteredCitations.map((c) => (
                    <tr key={c.citation_id} className="hover:bg-paper-50">
                      <td className="p-2.5 font-semibold text-ink">{c.domain}</td>
                      <td className="p-2.5 max-w-xs truncate font-mono text-[10px]">
                        <a href={c.cited_url} target="_blank" rel="noreferrer" className="text-pine hover:underline inline-flex items-center gap-1">
                          {c.cited_url} <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      </td>
                      <td className="p-2.5 font-mono text-[10px] uppercase">{c.source_ownership}</td>
                      <td className="p-2.5 font-mono text-[10px]">{c.source_category}</td>
                      <td className="p-2.5 font-mono text-[10px]">{c.platform_id}</td>
                      <td className="p-2.5 text-[11px] text-ink-600">{c.competitors_associated.join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {view === 'graph' && (
        <Card className="p-5 space-y-4">
          <h4 className="font-sans font-bold text-ink text-sm flex items-center gap-2">
            <Globe className="w-4 h-4 text-pine" /> Multi-Entity Citation Source Graph ({(graph.nodes || []).length} Nodes · {(graph.edges || []).length} Edges)
          </h4>
          {topDomains.length === 0 ? (
            <p className="text-xs text-ink-500">Citation graph populates once live cited URLs are observed.</p>
          ) : (
            <svg viewBox="0 0 760 280" className="w-full h-auto border border-line rounded bg-paper-50">
              {/* Brand central hub */}
              <rect x="20" y="110" width="140" height="48" rx="8" fill="#0f766e" />
              <text x="90" y="138" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="700">
                {bundle.audit.brand_name.slice(0, 18)}
              </text>
              {topDomains.slice(0, 6).map((d, idx) => {
                const y = 24 + idx * 42;
                const col = d.ownership === 'owned' ? '#15803d' : d.ownership === 'competitor' ? '#b91c1c' : '#1d4ed8';
                return (
                  <g key={d.domain}>
                    <line x1="160" y1="134" x2="290" y2={y + 14} stroke={col} strokeWidth="1.5" strokeDasharray={d.brand_present ? '' : '4 3'} />
                    <rect x="290" y={y} width="240" height="28" rx="5" fill="#fff" stroke={col} strokeWidth="1.2" />
                    <text x="300" y={y + 18} fill="#0f172a" fontSize="10" fontWeight="600">
                      {d.domain.slice(0, 28)} ({d.citation_count}x)
                    </text>
                    <text x="545" y={y + 18} fill={col} fontSize="9.5" fontFamily="monospace">
                      {d.ownership.toUpperCase()} · {d.brand_present ? 'Brand present' : 'Gap'}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </Card>
      )}

      {view === 'opportunities' && (
        <Card className="p-5 space-y-3">
          <h4 className="font-sans font-bold text-ink text-sm">Ethical Citation Source Opportunities</h4>
          <p className="text-xs text-ink-500">
            Independent publications and review domains repeatedly cited in AI answers without verified brand coverage. Recommendations strictly exclude paid or fabricated mentions.
          </p>
          {opportunities.length === 0 ? (
            <p className="text-xs text-ink-500">No independent citation gaps identified yet.</p>
          ) : (
            <div className="space-y-2.5">
              {opportunities.map((opp, idx) => (
                <div key={idx} className="p-3.5 rounded border border-line bg-paper-50 space-y-1 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-ink">{opp.domain}</span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white border border-line">
                      {opp.citation_count}x cited · {opp.category}
                    </span>
                  </div>
                  <p className="text-ink-700">{opp.why_it_matters}</p>
                  <p className="text-pine text-[11px]"><strong>Action:</strong> {opp.recommended_action}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
