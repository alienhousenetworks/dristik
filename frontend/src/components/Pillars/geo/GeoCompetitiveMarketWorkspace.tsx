import React, { useState } from 'react';
import { Card } from '../../ui';
import { GeoEnterpriseBundle } from '../../../services/geoApi';
import { Crosshair, Globe2, Trophy } from 'lucide-react';

interface GeoCompetitiveMarketWorkspaceProps {
  bundle: GeoEnterpriseBundle;
  mode: 'competitors' | 'markets';
}

export function GeoCompetitiveMarketWorkspace({ bundle, mode }: GeoCompetitiveMarketWorkspaceProps) {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [battlecards, setBattlecards] = useState<Array<Record<string, any>>>([]);
  const [bcLoading, setBcLoading] = useState(false);
  const [bcError, setBcError] = useState<string | null>(null);
  const comp = bundle.department_artifacts?.department_g || {};
  const market = bundle.department_artifacts?.department_h || {};
  const rows: Array<Record<string, any>> = comp.comparison_table || [];

  const handleGenerateBattlecards = async () => {
    setBcLoading(true);
    setBcError(null);
    try {
      const comps = rows.filter((r) => !r.is_target_brand).map((r) => r.entity_name);
      const res = await fetch('/api/v1/geo-pipeline/battlecards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_name: bundle.audit.brand_name,
          competitors: comps.length > 0 ? comps : (bundle.scope?.competitors || []),
          responses: (bundle.responses || []).map((r) => ({
            prompt: r.prompt_id,
            answer: r.response_text,
            sources: [],
          })),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setBattlecards(data.battlecards || []);
    } catch (err: any) {
      setBcError(err?.message || 'Could not generate battlecards.');
    } finally {
      setBcLoading(false);
    }
  };

  if (mode === 'markets') {
    const byMarket = market.by_market || {};
    const byLang = market.by_language || {};
    const byIntent = market.by_intent || {};
    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-4">
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <Globe2 className="w-4 h-4 text-pine" /> Market, Language &amp; Intent Visibility
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {[
              { title: 'By Geographic Market', data: byMarket },
              { title: 'By Language', data: byLang },
              { title: 'By Search / Buyer Intent', data: byIntent },
            ].map((sec) => (
              <div key={sec.title} className="p-4 rounded border border-line bg-paper-50 space-y-2">
                <h4 className="font-mono text-[11px] uppercase font-bold text-ink-700">{sec.title}</h4>
                {Object.keys(sec.data).length === 0 ? (
                  <p className="text-ink-500">No live responses captured for this breakdown yet.</p>
                ) : (
                  Object.entries(sec.data).map(([k, v]: [string, any]) => (
                    <div key={k} className="p-2 bg-white rounded border border-line flex justify-between">
                      <span className="font-semibold text-ink">{k}</span>
                      <span className="font-mono text-[10px]">
                        M:{v.mention_rate_pct ?? '—'}% · R:{v.recommendation_rate_pct ?? '—'}% (n={v.runs})
                      </span>
                    </div>
                  ))
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  const evidenceResponses = selectedEntity
    ? bundle.responses.filter((r) => {
        const row = rows.find((x) => x.entity_name === selectedEntity);
        return row?.evidence_response_ids?.includes(r.response_id);
      })
    : [];

  return (
    <div className="space-y-6">
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <Crosshair className="w-4 h-4 text-pine" /> Brand vs Competitor GEO Comparison
            </h3>
            <p className="text-xs text-ink-500">
              {comp.disclaimer || 'All entities evaluated on the identical shared prompt suite. Click any row to inspect original captured responses.'}
            </p>
          </div>
          {comp.leader_entity && (
            <span className="inline-flex items-center gap-1.5 font-mono text-xs px-2.5 py-1 rounded bg-paper-100 border border-line">
              <Trophy className="w-3.5 h-3.5 text-warn" /> Leader: {comp.leader_entity} (Your rank #{comp.target_rank})
            </span>
          )}
        </div>

        {rows.length === 0 ? (
          <p className="text-xs text-ink-500">
            No live comparative prompt responses captured yet. Configure competitors and AI providers to evaluate shared-prompt competitive share.
          </p>
        ) : (
          <div className="overflow-x-auto border border-line rounded">
            <table className="w-full text-xs text-left">
              <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
                <tr>
                  <th className="p-2.5">Brand / Competitor</th>
                  <th className="p-2.5">Tested</th>
                  <th className="p-2.5">Mentions</th>
                  <th className="p-2.5">Recommendations</th>
                  <th className="p-2.5">Citations</th>
                  <th className="p-2.5">Independent Sources</th>
                  <th className="p-2.5">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <tr
                    key={r.entity_name}
                    onClick={() => setSelectedEntity(r.entity_name)}
                    className={`cursor-pointer hover:bg-paper-50 ${r.is_target_brand ? 'bg-pine/5 font-semibold' : ''}`}
                  >
                    <td className="p-2.5 text-ink">
                      {r.entity_name} {r.is_target_brand && <span className="font-mono text-[9px] text-pine">(YOUR BRAND)</span>}
                    </td>
                    <td className="p-2.5 font-mono">{r.tested_responses}</td>
                    <td className="p-2.5 font-mono">{r.mentioned_responses} ({r.mention_rate_pct}%)</td>
                    <td className="p-2.5 font-mono">{r.recommendations} ({r.recommendation_rate_pct}%)</td>
                    <td className="p-2.5 font-mono">{r.cited_responses} ({r.citation_rate_pct}%)</td>
                    <td className="p-2.5 font-mono">{r.independent_sources_cited}</td>
                    <td className="p-2.5 font-mono text-[10px] text-pine underline">Inspect</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selectedEntity && (
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-sans font-bold text-ink text-sm">Original Response Evidence for {selectedEntity} ({evidenceResponses.length})</h4>
            <button type="button" onClick={() => setSelectedEntity(null)} className="text-xs font-mono text-ink-500 hover:underline">
              Close
            </button>
          </div>
          {evidenceResponses.length === 0 ? (
            <p className="text-xs text-ink-500">No captured mentions for {selectedEntity} in this run.</p>
          ) : (
            <div className="space-y-2">
              {evidenceResponses.map((er) => (
                <div key={er.response_id} className="p-3 rounded border border-line bg-paper-50 text-xs space-y-1">
                  <div className="font-mono text-[10px] text-ink-500">{er.platform_id} · {er.model_version} · {er.testing_mode}</div>
                  <p className="whitespace-pre-wrap text-[11px] text-ink-800">{er.response_text}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h4 className="font-sans font-bold text-ink text-sm">AI Competitor Battlecards</h4>
            <p className="text-xs text-ink-500">
              Synthesizes side-by-side strengths, weaknesses, and winning prompts strictly from observed AI answers.
            </p>
          </div>
          <button
            type="button"
            disabled={bcLoading}
            onClick={handleGenerateBattlecards}
            className="px-3 py-1.5 rounded bg-ink text-white font-mono text-xs disabled:opacity-50"
          >
            {bcLoading ? 'Synthesizing...' : 'Build Battlecards'}
          </button>
        </div>
        {bcError && <p className="text-xs text-bad font-mono">{bcError}</p>}
        {battlecards.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {battlecards.map((bc) => (
              <div key={bc.competitor} className="p-4 rounded border border-line bg-paper-50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-ink">{bc.competitor}</span>
                  <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-white border border-line">
                    {bc.sentiment} · {bc.mention_count} mentions
                  </span>
                </div>
                <p className="text-ink-700">{bc.summary}</p>
                {bc.strengths?.length > 0 && (
                  <div>
                    <div className="font-mono text-[10px] uppercase text-pine font-bold">Observed Strengths</div>
                    <ul className="list-disc pl-4 text-ink-700">
                      {bc.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
                {bc.weaknesses?.length > 0 && (
                  <div>
                    <div className="font-mono text-[10px] uppercase text-bad font-bold">Observed Weaknesses</div>
                    <ul className="list-disc pl-4 text-ink-700">
                      {bc.weaknesses.map((w: string, i: number) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
