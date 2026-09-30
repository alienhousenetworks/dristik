import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { CommercialBakeoffView } from '../CommercialBakeoffView';
import { CompetitorSideBySideBenchmark } from '../CompetitorSideBySideBenchmark';
import { CompetitorDiscoveryView } from '../CompetitorDiscoveryView';
import { Perspectives } from '../Perspectives';
import { PillarShell, Card } from '../ui';
import { Swords, BarChart3, Compass, GitCompare, ArrowRight } from 'lucide-react';

interface CompetitorWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  websiteUrl?: string;
}

type CompSubTab = 'bakeoff' | 'benchmark' | 'discovery' | 'perspectives';

export function CompetitorWorkspaceView({
  report,
  analysisId,
  websiteUrl,
}: CompetitorWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<CompSubTab>('bakeoff');

  const bakeoff = report.competitor_bakeoff;
  const totalBakeoff = (bakeoff?.target_wins || 0) + (bakeoff?.competitor_wins || 0) + (bakeoff?.ties || 0);
  const winRate = totalBakeoff > 0 ? Math.round(((bakeoff?.target_wins || 0) / totalBakeoff) * 100) : null;
  const compFindings = (report.findings || []).filter((f) => f.category === 'COMPETITIVE');

  return (
    <PillarShell
      kicker="Discipline 5 · Competitor Intelligence"
      title="Competitor Intelligence & Benchmarks"
      description="Head-to-head intent bake-offs, side-by-side metric benchmarks, market gap discovery, and 3-way perspective alignment."
      scoreLabel="Win Rate"
      score={winRate != null ? `${winRate}%` : '—'}
      metaLabel="Competitors"
      meta={bakeoff?.competitor_domain || 'Market rivals'}
      tabs={[
        { id: 'bakeoff', label: 'Commercial Query Bake-off' },
        { id: 'benchmark', label: 'Side-by-Side Benchmark' },
        { id: 'discovery', label: 'Market Gap Discovery' },
        { id: 'perspectives', label: 'Three-Way Perspective' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as CompSubTab)}
    >
      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: COMMERCIAL QUERY BAKE-OFF
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'bakeoff' && (
        <CommercialBakeoffView
          analysisId={analysisId || 'latest'}
          targetDomain={report.domain}
          initialBakeoff={report.competitor_bakeoff}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: SIDE-BY-SIDE BENCHMARK
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'benchmark' && (
        <CompetitorSideBySideBenchmark
          targetDomain={report.domain}
          analysisId={analysisId}
          niche={report.business_profile?.industry}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: MARKET GAP DISCOVERY
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'discovery' && (
        <CompetitorDiscoveryView
          websiteUrl={report.website_url}
          analysisId={analysisId}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: THREE-WAY PERSPECTIVE
          ───────────────────────────────────────────────────────────── */}
      {activeSubTab === 'perspectives' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <h3 className="font-serif text-lg text-ink font-semibold">
              Three-Way Alignment Matrix
            </h3>
            <p className="text-xs text-ink-600">
              Evaluates alignment between (1) What your website declares, (2) What search and AI engines perceive, and (3) What competitors communicate.
            </p>
            <Perspectives comparison={report.three_way_comparison} />
          </Card>
        </div>
      )}
    </PillarShell>
  );
}
