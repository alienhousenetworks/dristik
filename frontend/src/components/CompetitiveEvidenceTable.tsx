import React, { useState } from 'react';
import {
  CompetitiveEvidenceTableRow,
  CompetitiveGapDimension,
  CausalAdvantageExplanation,
  CompetitorProfile,
} from '../types';
import { Card, Badge } from './ui';
import {
  Table,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  TrendingUp,
  TrendingDown,
  Layers,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ExternalLink,
} from 'lucide-react';

interface CompetitiveEvidenceTableProps {
  targetDomain: string;
  targetBrand: string;
  competitors: CompetitorProfile[];
  evidenceRows: CompetitiveEvidenceTableRow[];
  gapMatrix: CompetitiveGapDimension[];
  causalExplanations: CausalAdvantageExplanation[];
}

export function CompetitiveEvidenceTable({
  targetDomain,
  targetBrand,
  competitors,
  evidenceRows,
  gapMatrix,
  causalExplanations,
}: CompetitiveEvidenceTableProps) {
  const [selectedCompDomain, setSelectedCompDomain] = useState<string>(
    competitors[0]?.canonical_domain || ''
  );
  const [showCausalDetails, setShowCausalDetails] = useState<boolean>(true);

  const selectedComp = competitors.find((c) => c.canonical_domain === selectedCompDomain) || competitors[0];
  const selectedCausal = causalExplanations.find(
    (c) => c.competitor_domain === selectedCompDomain
  );

  return (
    <div className="space-y-6">
      {/* ─────────────────────────────────────────────────────────────
          SECTION 1: COMPETITIVE EVIDENCE TABLE
          ───────────────────────────────────────────────────────────── */}
      <Card className="p-6 space-y-4 bg-card border border-border/70 rounded-xl shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Table className="w-5 h-5 text-ink-700" />
              <h3 className="font-sans text-lg font-semibold text-ink">
                Competitive Evidence Matrix
              </h3>
              <Badge tone="pine" className="text-xs">
                Zero-Fake Verified
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Side-by-side empirical observations across all audited dimensions. Uncrawled metrics fail closed with explicit Unmeasured markers.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm divide-y divide-border">
            <thead className="bg-muted/50 text-xs font-semibold text-muted-foreground uppercase tracking-[0.04em]">
              <tr>
                <th className="py-3 px-4">Audit Dimension</th>
                <th className="py-3 px-4 text-good dark:text-good bg-good/10 dark:bg-good/10">
                  {targetBrand} (Target)
                </th>
                {competitors.map((c) => (
                  <th key={c.id} className="py-3 px-4">
                    <div className="flex items-center gap-1.5">
                      <span>{c.company_name}</span>
                      <div className="flex gap-0.5">
                        {c.competitor_types.slice(0, 2).map((t) => (
                          <span
                            key={t}
                            className="text-[9px] px-1 py-0.2 rounded bg-paper-200 dark:bg-ink-800 text-ink-600 dark:text-ink-300 font-mono"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </th>
                ))}
                <th className="py-3 px-4 text-muted-foreground">Provenance Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-xs">
              {evidenceRows.map((row) => (
                <tr key={row.dimension_key} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 font-medium text-ink flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-muted-foreground" />
                    {row.dimension}
                  </td>
                  <td className="py-3 px-4 font-semibold text-good dark:text-good bg-good/10 dark:bg-good/10">
                    {row.target_value || 'Unmeasured'}
                  </td>
                  {competitors.map((c) => {
                    const val = row.competitor_values[c.canonical_domain];
                    const isUnmeasured = !val || val === 'Unmeasured';

                    return (
                      <td key={c.id} className="py-3 px-4">
                        {isUnmeasured ? (
                          <span className="inline-flex items-center gap-1 text-ink-400 dark:text-ink-500 italic text-[11px]">
                            <HelpCircle className="w-3 h-3" /> Unmeasured
                          </span>
                        ) : (
                          <span className="font-semibold text-ink">{val}</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="py-3 px-4 text-muted-foreground text-[11px] max-w-xs truncate">
                    {row.provenance_note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ─────────────────────────────────────────────────────────────
          SECTION 2: WHY COMPETITORS OUTPERFORM (CAUSAL REASONER)
          ───────────────────────────────────────────────────────────── */}
      {competitors.length > 0 && (
        <Card className="p-6 space-y-4 bg-card border border-border/70 rounded-xl shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-warn" />
                <h3 className="font-sans text-lg font-semibold text-ink">
                  Causal Explainability: Why Rivals Outperform
                </h3>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Observable, evidence-backed architectural reasons explaining ranking and citation advantages.
              </p>
            </div>

            {/* Competitor Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Select Rival:</span>
              <div className="flex gap-1.5">
                {competitors.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSelectedCompDomain(c.canonical_domain)}
                    className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                      selectedCompDomain === c.canonical_domain
                        ? 'bg-paper-100 text-white shadow-xs'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                  >
                    {c.company_name}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {selectedCausal && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {/* Advantages / Why They Outperform */}
              <div className="p-4 rounded-xl bg-warn/10 border border-warn/30 space-y-2.5">
                <div className="flex items-center gap-2 text-warn dark:text-warn font-semibold text-xs uppercase tracking-wide">
                  <TrendingUp className="w-4 h-4" />
                  Why {selectedCausal.competitor_name} Outperforms {targetBrand}
                </div>
                <ul className="space-y-2 text-xs text-ink/90">
                  {selectedCausal.reasons_they_outperform.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-warn/10 mt-1.5 shrink-0" />
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Where Target Wins / Moats */}
              <div className="p-4 rounded-xl bg-good/10 border border-good/30 space-y-2.5">
                <div className="flex items-center gap-2 text-good dark:text-good font-semibold text-xs uppercase tracking-wide">
                  <CheckCircle2 className="w-4 h-4" />
                  Where {targetBrand} Holds Competitive Advantage
                </div>
                <ul className="space-y-2 text-xs text-ink/90">
                  {selectedCausal.areas_target_wins.map((win, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-good/10 mt-1.5 shrink-0" />
                      <span>{win}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
