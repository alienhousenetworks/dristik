import React, { useState } from 'react';
import { CompetitorBakeoffResult } from '../types';

interface CommercialBakeoffViewProps {
  analysisId: string;
  targetDomain: string;
  initialBakeoff?: CompetitorBakeoffResult;
  onBakeoffComplete?: (result: CompetitorBakeoffResult) => void;
}

export function CommercialBakeoffView({
  analysisId,
  targetDomain,
  initialBakeoff,
  onBakeoffComplete,
}: CommercialBakeoffViewProps) {
  const [bakeoff, setBakeoff] = useState<CompetitorBakeoffResult | undefined>(initialBakeoff);
  const [competitorUrl, setCompetitorUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunBakeoff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!competitorUrl.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/analyses/${analysisId}/competitor-bakeoff`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ competitor_url: competitorUrl.trim() }),
      });

      if (!res.ok) {
        throw new Error('Failed to run competitor bake-off');
      }

      const data: CompetitorBakeoffResult = await res.json();
      setBakeoff(data);
      if (onBakeoffComplete) onBakeoffComplete(data);
    } catch (err: any) {
      setError(err.message || 'Error running competitor bake-off');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'Answerable':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'Ambiguous':
        return 'text-amber-700 bg-amber-50 border-amber-200';
      default:
        return 'text-red-700 bg-red-50 border-red-200';
    }
  };

  return (
    <div className="sheet border border-line rounded-lg p-6 space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-pine"></span>
            <h3 className="font-serif text-xl text-ink">
              1-Competitor Bake-Off: Who Does the Model Answer For?
            </h3>
          </div>
          <p className="text-xs text-ink-500 mt-1">
            Head-to-head comparison on the exact 6 commercial inquiries SaaS buyers ask on sales calls.
          </p>
        </div>

        {/* Input Form to Run / Switch Competitor */}
        <form onSubmit={handleRunBakeoff} className="flex items-center gap-2">
          <input
            type="text"
            value={competitorUrl}
            onChange={(e) => setCompetitorUrl(e.target.value)}
            placeholder="competitor.com"
            className="text-xs px-3 py-1.5 border border-line rounded bg-paper-50 text-ink focus:outline-hidden focus:ring-1 focus:ring-pine w-44 md:w-56"
          />
          <button
            type="submit"
            disabled={isLoading || !competitorUrl.trim()}
            className="btn-primary font-semibold px-3 py-1.5 rounded text-xs transition-colors shadow-xs disabled:opacity-50"
          >
            {isLoading ? 'Benchmarking...' : 'Run Bake-Off'}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-3 rounded bg-red-50 border border-red-200 text-xs text-bad">
          {error}
        </div>
      )}

      {bakeoff ? (
        <div className="space-y-6">
          {/* Executive Score Summary */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-paper-50 border border-line p-4 rounded-lg">
            <div className="space-y-1">
              <span className="label text-pine block">
                Commercial Battlecard Summary
              </span>
              <p className="text-xs text-ink-700 leading-relaxed max-w-2xl font-medium">
                {bakeoff.executive_takeaway}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-center px-3 py-1 sheet rounded border border-line">
                <span className="label text-[10px] block">You Win</span>
                <span className="text-base font-bold text-good">{bakeoff.target_wins}</span>
              </div>
              <div className="text-center px-3 py-1 sheet rounded border border-line">
                <span className="label text-[10px] block">Rival Win</span>
                <span className="text-base font-bold text-warn">{bakeoff.competitor_wins}</span>
              </div>
              <div className="text-center px-3 py-1 sheet rounded border border-line">
                <span className="label text-[10px] block">Ties</span>
                <span className="text-base font-bold text-ink-500">{bakeoff.ties}</span>
              </div>
            </div>
          </div>

          {/* Side-by-Side Comparison Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-paper-50 text-ink-500 font-bold border-b border-line label text-[10px]">
                  <th className="p-3 w-1/5">Commercial Question</th>
                  <th className="p-3 w-2/5 border-l border-line">
                    <span className="text-pine font-extrabold">{targetDomain}</span> (You)
                  </th>
                  <th className="p-3 w-2/5 border-l border-line">
                    <span className="text-ink font-extrabold">{bakeoff.competitor_domain}</span> (Rival)
                  </th>
                  <th className="p-3 border-l border-line text-center">Advantage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {bakeoff.evaluations.map((item) => (
                  <tr key={item.question_key} className="hover:bg-paper-200/50 transition-colors">
                    <td className="p-3 align-top font-medium text-ink">
                      <div className="font-bold">{item.question_title}</div>
                      <div className="text-[10px] text-ink-500 mt-1 italic leading-tight">
                        {item.commercial_takeaway}
                      </div>
                    </td>

                    {/* Target Domain Column */}
                    <td className="p-3 align-top border-l border-line space-y-1.5 bg-emerald-50/20">
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getStatusClass(item.target_status)}`}>
                          {item.target_status}
                        </span>
                        <span className="font-bold text-ink-700 text-[11px]">
                          {item.target_score != null ? `${item.target_score}/10` : '—'}
                        </span>
                      </div>
                      <p className="text-ink-700 font-mono text-[11px] leading-relaxed">
                        "{item.target_answer}"
                      </p>
                    </td>

                    {/* Competitor Column */}
                    <td className="p-3 align-top border-l border-line space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getStatusClass(item.competitor_status)}`}>
                          {item.competitor_status}
                        </span>
                        <span className="font-bold text-ink-700 text-[11px]">
                          {item.competitor_score != null ? `${item.competitor_score}/10` : '—'}
                        </span>
                      </div>
                      <p className="text-ink-700 font-mono text-[11px] leading-relaxed">
                        "{item.competitor_answer}"
                      </p>
                    </td>

                    {/* Advantage Pill */}
                    <td className="p-3 align-top border-l border-line text-center whitespace-nowrap">
                      {item.winner === 'target' ? (
                        <span className="inline-block px-2 py-1 rounded bg-emerald-100 text-good font-bold text-[10px] border border-emerald-200">
                          ✓ You Win
                        </span>
                      ) : item.winner === 'competitor' ? (
                        <span className="inline-block px-2 py-1 rounded bg-amber-100 text-warn font-bold text-[10px] border border-amber-200">
                          Rival Ahead
                        </span>
                      ) : (
                        <span className="inline-block px-2 py-1 rounded bg-paper-200 text-ink-700 font-bold text-[10px] border border-line">
                          Parity
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="p-8 text-center bg-paper-50 border border-dashed border-line rounded-lg space-y-3">
          <div className="w-10 h-10 rounded-full bg-paper-200 text-pine flex items-center justify-center mx-auto text-lg font-bold">
            ⚔️
          </div>
          <div>
            <p className="text-sm font-semibold text-ink">No competitor benchmark loaded yet</p>
            <p className="text-xs text-ink-500 mt-1 max-w-md mx-auto">
              Enter a primary competitor's domain above to see how ChatGPT and Perplexity answer the 6 commercial questions for you versus them.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
