import React, { useState, useMemo } from 'react';
import {
  DynamicSandboxQuestionEvaluation,
  FiveDimensionAiVisibility,
  KieGraphSummary,
  KieClaimGroundingResult,
  KieAnswerRisk,
} from '../types';
import {
  Sparkles,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Quote,
  Target,
  Zap,
  Database,
  GitBranch,
  ShieldCheck,
  BarChart3,
  BookOpen,
  Link2,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function GroundingBar({ ratio, size = 'sm' }: { ratio: number; size?: 'sm' | 'lg' }) {
  const pct = Math.round(ratio * 100);
  const color =
    pct >= 60 ? 'bg-emerald-500' : pct >= 30 ? 'bg-amber-500' : 'bg-rose-500';
  const h = size === 'lg' ? 'h-2.5' : 'h-1.5';
  return (
    <div className={`flex items-center gap-2`}>
      <div className={`flex-1 bg-paper-200 ${h} rounded-full overflow-hidden`}>
        <div className={`${h} ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[11px] font-bold text-ink w-9 text-right">{pct}%</span>
    </div>
  );
}

function AnswerRiskBadge({ risk }: { risk?: KieAnswerRisk | string | null }) {
  if (!risk) return null;
  const config = {
    HIGH: 'bg-rose-100 text-rose-800 border-rose-300',
    MEDIUM: 'bg-amber-100 text-amber-800 border-amber-300',
    LOW: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  }[risk] ?? 'bg-paper-100 text-ink-600 border-line';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${config}`}>
      Answer Risk: {risk}
    </span>
  );
}

function ClaimDecompositionPanel({ claims }: { claims: KieClaimGroundingResult[] }) {
  if (!claims || claims.length === 0) return null;
  const statusConfig = {
    SUPPORTED: { color: 'text-emerald-700 bg-emerald-50 border-emerald-200', icon: '✓' },
    PARTIALLY_SUPPORTED: { color: 'text-amber-700 bg-amber-50 border-amber-200', icon: '◐' },
    UNSUPPORTED: { color: 'text-rose-700 bg-rose-50 border-rose-200', icon: '✗' },
  } as Record<string, { color: string; icon: string }>;
  return (
    <div className="space-y-1.5">
      <div className="text-[11px] font-semibold text-ink-600 flex items-center gap-1.5">
        <GitBranch className="w-3 h-3" />
        Claim-Level Grounding Verification
      </div>
      {claims.map((c, i) => {
        const cfg = statusConfig[c.status] ?? statusConfig.UNSUPPORTED;
        return (
          <div key={i} className={`p-2.5 rounded border text-[11px] ${cfg.color}`}>
            <div className="flex items-start gap-2">
              <span className="font-mono font-bold mt-0.5 text-xs">{cfg.icon}</span>
              <div className="flex-1 space-y-1">
                <p className="leading-relaxed">{c.claim_text}</p>
                {c.evidence_snippet && (
                  <blockquote className="border-l-2 border-current pl-2 opacity-80 font-mono text-[10px]">
                    "{c.evidence_snippet.slice(0, 120)}"
                  </blockquote>
                )}
                {c.evidence_url && (
                  <a
                    href={c.evidence_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] underline opacity-70 hover:opacity-100"
                  >
                    <Link2 className="w-2.5 h-2.5" /> Source
                  </a>
                )}
              </div>
              <span className="font-mono text-[10px] opacity-70 shrink-0">
                {Math.round(c.confidence * 100)}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 5-Dimension Scorecard Panel
// ─────────────────────────────────────────────────────────────────────────────

function FiveDimensionPanel({ dims }: { dims: FiveDimensionAiVisibility }) {
  const dimensions = [
    {
      key: 'knowledge_coverage',
      label: 'Knowledge Coverage',
      value: dims.knowledge_coverage,
      icon: <BookOpen className="w-3.5 h-3.5" />,
      description: 'Proportion of the 10-facet taxonomy with ≥2 supporting atomic claims',
    },
    {
      key: 'retrieval_coverage',
      label: 'Retrieval Coverage',
      value: dims.retrieval_coverage,
      icon: <Search className="w-3.5 h-3.5" />,
      description: 'Share of questions where the Hybrid Retriever found at least one evidence chunk',
    },
    {
      key: 'evidence_quality',
      label: 'Evidence Quality',
      value: dims.evidence_quality,
      icon: <ShieldCheck className="w-3.5 h-3.5" />,
      description: 'Share of claims backed by HIGH-strength FACT or CAPABILITY evidence from authoritative pages',
    },
    {
      key: 'answer_grounding',
      label: 'Answer Grounding',
      value: dims.answer_grounding,
      icon: <Target className="w-3.5 h-3.5" />,
      description: 'Average grounding ratio across all simulated answers (supported / total claims)',
    },
    {
      key: 'citation_quality',
      label: 'Citation Quality',
      value: dims.citation_quality,
      icon: <Link2 className="w-3.5 h-3.5" />,
      description: 'Share of supported claims with a canonical source URL for disambiguation',
    },
  ] as const;

  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50/40 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-indigo-600" />
        <h4 className="font-semibold text-sm text-indigo-900">
          5-Dimension AI Visibility Scorecard
        </h4>
        <span className="ml-auto text-[10px] font-mono text-indigo-500 border border-indigo-200 rounded px-1.5 py-0.5">
          {dims.weighting_profile}
        </span>
      </div>
      <p className="text-[11px] text-indigo-700/80">
        Each dimension is measured independently. No arbitrary equal-weighting or composite rollup is applied.
        An aggregate index, if shown, is explicitly labelled with its weighting profile.
      </p>
      <div className="space-y-3">
        {dimensions.map((d) => (
          <div key={d.key}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-indigo-800">
                {d.icon}
                {d.label}
              </div>
              <span className="font-mono text-xs font-bold text-indigo-900">{d.value}%</span>
            </div>
            <GroundingBar ratio={d.value / 100} size="lg" />
            <p className="text-[10px] text-indigo-600/70 mt-0.5">{d.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Knowledge Graph Summary Panel
// ─────────────────────────────────────────────────────────────────────────────

function KieGraphSummaryPanel({ summary }: { summary: KieGraphSummary }) {
  return (
    <div className="rounded-lg border border-pine/20 bg-paper-50 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Database className="w-4 h-4 text-pine" />
        <h4 className="font-semibold text-sm text-ink">Website Knowledge Graph</h4>
        <span className="text-[10px] text-ink-400 ml-1">— {summary.domain}</span>
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center">
        {[
          { label: 'Pages', value: summary.total_pages_classified },
          { label: 'Claims', value: summary.total_claims_extracted },
          { label: 'Entities', value: summary.total_entities },
          { label: 'Relations', value: summary.total_relationships },
          {
            label: 'Contradictions',
            value: summary.total_contradictions,
            alert: summary.total_contradictions > 0,
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className={`p-2 rounded border ${
              stat.alert
                ? 'bg-rose-50 border-rose-200 text-rose-800'
                : 'bg-paper border-line text-ink'
            }`}
          >
            <div className="text-lg font-bold font-mono">{stat.value}</div>
            <div className="text-[10px] font-medium opacity-70">{stat.label}</div>
          </div>
        ))}
        {Object.entries(summary.entity_categories || {}).slice(0, 1).map(([cat, count]) => (
          <div key={cat} className="p-2 rounded border bg-paper border-line text-ink">
            <div className="text-lg font-bold font-mono">{count}</div>
            <div className="text-[10px] font-medium opacity-70">{cat}</div>
          </div>
        ))}
      </div>
      {summary.total_contradictions > 0 && (
        <div className="text-[11px] text-rose-700 bg-rose-50 border border-rose-200 rounded p-2 flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>
            {summary.total_contradictions} cross-page knowledge conflict{summary.total_contradictions > 1 ? 's' : ''} detected
            (ICP, pricing, or headcount inconsistency). AI answer engines may hallucinate
            from conflicting signals.
          </span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

interface DynamicQuestionSandboxViewProps {
  analysisId: string;
  initialEvaluations?: DynamicSandboxQuestionEvaluation[];
  initialKieGraphSummary?: KieGraphSummary | null;
  initialFiveDimensions?: FiveDimensionAiVisibility | null;
  onEvaluationsUpdate?: (updated: DynamicSandboxQuestionEvaluation[]) => void;
}

export function DynamicQuestionSandboxView({
  analysisId,
  initialEvaluations = [],
  initialKieGraphSummary = null,
  initialFiveDimensions = null,
  onEvaluationsUpdate,
}: DynamicQuestionSandboxViewProps) {
  const [evaluations, setEvaluations] = useState<DynamicSandboxQuestionEvaluation[]>(initialEvaluations);
  const [kieGraphSummary, setKieGraphSummary] = useState<KieGraphSummary | null>(initialKieGraphSummary);
  const [fiveDimensions, setFiveDimensions] = useState<FiveDimensionAiVisibility | null>(initialFiveDimensions);
  const [selectedFacet, setSelectedFacet] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showDimensions, setShowDimensions] = useState<boolean>(true);

  const facets = useMemo(() => {
    const list = Array.from(new Set(evaluations.map((e) => e.facet))).filter(Boolean);
    return list.length > 0 ? list : [
      'Identity, Category & Core Mission',
      'Target Audience, ICP & Disqualifiers',
      'Pricing, Packaging & Commercial Model',
      'Core Capabilities, Features & Product Mechanics',
      'Technology Stack, Architecture & Integrations',
      'Competitive Moat, Differentiation & Alternatives',
      'Trust, Enterprise Security & Regulatory Compliance',
      'Customer Proof, Case Studies & Quantified ROI',
      'Implementation, Support & Customer Success',
      'High-Intent Purchase & Conversion Paths',
    ];
  }, [evaluations]);

  const totalCount = evaluations.length;
  const answerableCount = evaluations.filter((e) => e.answerability_status === 'ANSWERABLE' || e.is_answerable).length;
  const partialCount = evaluations.filter((e) => e.answerability_status === 'PARTIAL').length;
  const unanswerableCount = evaluations.filter(
    (e) => e.answerability_status === 'UNANSWERABLE' || (!e.is_answerable && e.answerability_status !== 'PARTIAL')
  ).length;
  const avgGrounding =
    totalCount > 0
      ? Math.round((evaluations.reduce((acc, e) => acc + (e.grounding_ratio ?? 0), 0) / totalCount) * 100)
      : 0;
  const highRiskCount = evaluations.filter((e) => e.answer_risk === 'HIGH').length;

  const filteredEvaluations = useMemo(() => {
    return evaluations.filter((item) => {
      if (selectedFacet !== 'all' && item.facet !== selectedFacet) return false;
      if (statusFilter === 'answerable' && item.answerability_status !== 'ANSWERABLE') return false;
      if (statusFilter === 'partial' && item.answerability_status !== 'PARTIAL') return false;
      if (statusFilter === 'unanswerable' && item.answerability_status !== 'UNANSWERABLE') return false;
      if (statusFilter === 'high_risk' && item.answer_risk !== 'HIGH') return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        if (
          !item.generated_question.toLowerCase().includes(q) &&
          !(item.crawled_answer || '').toLowerCase().includes(q) &&
          !(item.buyer_intent || '').toLowerCase().includes(q) &&
          !item.question_id.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [evaluations, selectedFacet, statusFilter, searchQuery]);

  const handleGenerateOrRefresh = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/analyses/${analysisId}/dynamic-sandbox`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`Failed: ${res.statusText}`);
      const data = await res.json();
      if (data.evaluations && Array.isArray(data.evaluations)) {
        setEvaluations(data.evaluations);
        if (onEvaluationsUpdate) onEvaluationsUpdate(data.evaluations);
      }
      if (data.kie_graph_summary) setKieGraphSummary(data.kie_graph_summary);
      if (data.five_dimension_ai_visibility) setFiveDimensions(data.five_dimension_ai_visibility);
    } catch (err: any) {
      setError(err.message || 'Error executing dynamic sandbox evaluation');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ANSWERABLE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Answerable
          </span>
        );
      case 'PARTIAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3 h-3 text-amber-600" /> Partial Evidence
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 border border-rose-300">
            <XCircle className="w-3 h-3 text-rose-600" /> Evidence Gap
          </span>
        );
    }
  };

  return (
    <div className="sheet border border-line rounded-lg p-6 space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-pine" />
            <h3 className="font-serif text-xl text-ink">
              Dynamic AI Question Sandbox — KIE Grounded Answer Check
            </h3>
          </div>
          <p className="text-xs text-ink-500 max-w-3xl">
            {totalCount > 0 ? totalCount : '100'} bespoke buyer inquiries synthesized from the{' '}
            <strong>Website Knowledge Graph</strong>, evaluated via{' '}
            <strong>Hybrid Retrieval + Claim-Level Grounding Verification</strong>.
            Each question reports a <strong>Grounding Ratio</strong> (supported claims / total claims)
            and an <strong>Answer Risk</strong> label (HIGH / MEDIUM / LOW) indicating whether
            an AI answer engine would hallucinate or cite competitors to fill this gap.
          </p>
        </div>
        <button
          id="sandbox-generate-btn"
          onClick={handleGenerateOrRefresh}
          disabled={isLoading}
          className="btn-secondary text-xs flex items-center gap-2 px-3 py-2 rounded-md transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-pine' : ''}`} />
          {isLoading ? 'Building Knowledge Graph...' : totalCount > 0 ? 'Re-Evaluate' : 'Generate Questions'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-md">
          {error}
        </div>
      )}

      {/* ── KIE Knowledge Graph Summary ── */}
      {kieGraphSummary && <KieGraphSummaryPanel summary={kieGraphSummary} />}

      {/* ── 5-Dimension Scorecard ── */}
      {fiveDimensions && (
        <div>
          <button
            className="text-xs font-semibold text-indigo-700 hover:underline flex items-center gap-1.5 mb-2"
            onClick={() => setShowDimensions(!showDimensions)}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            {showDimensions ? 'Hide' : 'Show'} 5-Dimension AI Visibility Scorecard
          </button>
          {showDimensions && <FiveDimensionPanel dims={fiveDimensions} />}
        </div>
      )}

      {/* ── Aggregate Scorecards ── */}
      {totalCount > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="p-3 bg-paper-50 border border-line rounded-md text-center">
            <span className="label text-[10px] text-ink-400 block">Total Questions</span>
            <span className="text-xl font-bold font-mono text-ink">{totalCount}</span>
          </div>
          <div className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-md text-center">
            <span className="label text-[10px] text-emerald-800 block">Answerable</span>
            <span className="text-xl font-bold font-mono text-emerald-700">
              {answerableCount}{' '}
              <span className="text-xs font-normal">({Math.round((answerableCount / totalCount) * 100)}%)</span>
            </span>
          </div>
          <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-md text-center">
            <span className="label text-[10px] text-amber-800 block">Partial Evidence</span>
            <span className="text-xl font-bold font-mono text-amber-700">
              {partialCount}{' '}
              <span className="text-xs font-normal">({Math.round((partialCount / totalCount) * 100)}%)</span>
            </span>
          </div>
          <div className="p-3 bg-rose-50/60 border border-rose-200 rounded-md text-center">
            <span className="label text-[10px] text-rose-800 block">Evidence Gaps</span>
            <span className="text-xl font-bold font-mono text-rose-700">
              {unanswerableCount}{' '}
              <span className="text-xs font-normal">({Math.round((unanswerableCount / totalCount) * 100)}%)</span>
            </span>
          </div>
          <div className="p-3 bg-indigo-50/60 border border-indigo-200 rounded-md text-center col-span-2 md:col-span-1">
            <span className="label text-[10px] text-indigo-800 block">Avg Grounding</span>
            <span className="text-xl font-bold font-mono text-indigo-700">
              {avgGrounding}%
            </span>
          </div>
        </div>
      )}

      {/* ── Filters ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-paper-50 p-3 rounded-md border border-line">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-ink-600">Filter:</span>
          {[
            { key: 'all', label: `All (${evaluations.length})` },
            { key: 'answerable', label: `Answerable (${answerableCount})`, color: 'emerald' },
            { key: 'partial', label: `Partial (${partialCount})`, color: 'amber' },
            { key: 'unanswerable', label: `Gaps (${unanswerableCount})`, color: 'rose' },
            ...(highRiskCount > 0 ? [{ key: 'high_risk', label: `High Risk (${highRiskCount})`, color: 'rose' }] : []),
          ].map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key)}
              className={`px-2.5 py-1 text-xs rounded-md font-mono transition-colors ${
                statusFilter === key
                  ? color ? `bg-${color}-700 text-white font-semibold` : 'bg-pine text-white font-semibold'
                  : color ? `bg-paper text-${color}-800 hover:bg-${color}-50 border border-${color}-200` : 'bg-paper text-ink-600 hover:bg-paper-100 border border-line'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-ink-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search questions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-paper border border-line rounded-md focus:outline-none focus:border-pine"
          />
        </div>
      </div>

      {/* ── Facet Tabs ── */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1 text-xs border-b border-line scrollbar-thin">
        <button
          onClick={() => setSelectedFacet('all')}
          className={`px-3 py-1.5 whitespace-nowrap rounded-t-md font-medium transition-colors ${
            selectedFacet === 'all'
              ? 'border-b-2 border-pine text-pine bg-paper-50 font-semibold'
              : 'text-ink-500 hover:text-ink hover:bg-paper-50'
          }`}
        >
          All Facets ({totalCount})
        </button>
        {facets.map((facet) => {
          const facetCount = evaluations.filter((e) => e.facet === facet).length;
          const shortFacet = facet.split(',')[0].split('&')[0].trim();
          return (
            <button
              key={facet}
              onClick={() => setSelectedFacet(facet)}
              className={`px-3 py-1.5 whitespace-nowrap rounded-t-md font-medium transition-colors ${
                selectedFacet === facet
                  ? 'border-b-2 border-pine text-pine bg-paper-50 font-semibold'
                  : 'text-ink-500 hover:text-ink hover:bg-paper-50'
              }`}
            >
              {shortFacet} ({facetCount})
            </button>
          );
        })}
      </div>

      {/* ── Question Cards ── */}
      {filteredEvaluations.length === 0 ? (
        <div className="text-center py-10 bg-paper-50 rounded-md border border-line">
          <HelpCircle className="w-8 h-8 text-ink-300 mx-auto mb-2" />
          <p className="text-sm font-medium text-ink-700">No questions match the current filters.</p>
          <p className="text-xs text-ink-500 mt-1">Reset the status filter or clear the search.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEvaluations.map((item) => {
            const isExpanded = expandedId === item.question_id;
            const grounding = item.grounding_ratio ?? null;
            return (
              <div key={item.question_id} className="border border-line rounded-md bg-paper transition-shadow hover:shadow-sm">
                {/* ── Collapsed Header ── */}
                <div
                  onClick={() => setExpandedId(isExpanded ? null : item.question_id)}
                  className="p-4 flex items-start justify-between gap-3 cursor-pointer select-none"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-pine bg-pine/10 px-2 py-0.5 rounded">
                        {item.question_id}
                      </span>
                      <span className="text-[11px] font-medium text-ink-500 bg-paper-100 px-2 py-0.5 rounded">
                        {item.facet.split(',')[0].trim()}
                      </span>
                      {getStatusBadge(item.answerability_status)}
                      <AnswerRiskBadge risk={item.answer_risk} />
                    </div>
                    <h4 className="text-sm font-semibold text-ink leading-snug">{item.generated_question}</h4>
                    <p className="text-xs text-ink-500 italic line-clamp-1">Intent: {item.buyer_intent}</p>
                    {/* Inline grounding bar in collapsed view */}
                    {grounding !== null && (
                      <div className="pt-1 max-w-xs">
                        <GroundingBar ratio={grounding} />
                      </div>
                    )}
                  </div>
                  <button className="text-ink-400 hover:text-ink pt-1">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>

                {/* ── Expanded Details ── */}
                {isExpanded && (
                  <div className="border-t border-line bg-paper-50 p-4 space-y-4 text-xs">
                    {/* Grounding Ratio (prominent) */}
                    {grounding !== null && (
                      <div className="p-3 bg-paper border border-line rounded-md space-y-2">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-ink flex items-center gap-1.5">
                            <Target className="w-3.5 h-3.5 text-pine" /> Grounding Ratio
                          </span>
                          <span className="font-mono font-bold text-ink">{Math.round(grounding * 100)}%</span>
                        </div>
                        <GroundingBar ratio={grounding} size="lg" />
                        <p className="text-[10px] text-ink-500">
                          Proportion of synthesized answer claims supported by first-party crawled evidence.
                          A ratio below 35% signals HIGH hallucination risk for AI answer engines.
                        </p>
                      </div>
                    )}

                    {/* Retrieved Answer */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-ink font-semibold">
                        <Quote className="w-3.5 h-3.5 text-pine" />
                        <span>KIE Retrieved Answer (from first-party evidence)</span>
                        {item.retrieval_evidence_count != null && (
                          <span className="ml-auto font-mono text-[10px] text-ink-500">
                            {item.retrieval_evidence_count} evidence chunks retrieved
                          </span>
                        )}
                      </div>
                      <div className="p-3 bg-paper border border-line rounded-md text-ink-700 leading-relaxed font-sans">
                        {item.crawled_answer || 'No sufficient first-party evidence found.'}
                      </div>
                    </div>

                    {/* Evidence Source */}
                    {item.evidence_snippet && (
                      <div className="space-y-1 bg-paper/60 p-3 rounded-md border border-line/60">
                        <div className="flex items-center justify-between text-[11px] text-ink-500">
                          <span className="font-medium text-ink-600">Primary Evidence Snippet:</span>
                          {item.evidence_url && (
                            <a href={item.evidence_url} target="_blank" rel="noreferrer"
                              className="text-pine hover:underline flex items-center gap-1 text-[11px]">
                              View Source <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                        <blockquote className="font-mono text-[11px] text-ink-600 border-l-2 border-pine pl-2.5 py-0.5">
                          "{item.evidence_snippet}"
                        </blockquote>
                      </div>
                    )}

                    {/* Claim-Level Decomposition */}
                    {item.claim_decomposition && item.claim_decomposition.length > 0 && (
                      <ClaimDecompositionPanel claims={item.claim_decomposition} />
                    )}

                    {/* Gap Analysis */}
                    {item.gap_analysis && (
                      <div className={`p-3 rounded-md border space-y-1 ${
                        item.answer_risk === 'HIGH'
                          ? 'bg-rose-50/60 border-rose-200'
                          : item.answer_risk === 'MEDIUM'
                          ? 'bg-amber-50/60 border-amber-200'
                          : 'bg-amber-50/40 border-amber-200/60'
                      }`}>
                        <div className="flex items-center gap-1.5 font-semibold text-[11px] text-amber-900">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                          <span>Evidence Gap & Answer Risk</span>
                        </div>
                        <p className="text-amber-800/90 leading-relaxed">{item.gap_analysis}</p>
                      </div>
                    )}

                    {/* Recommended Answer */}
                    {item.recommended_answer && (
                      <div className="p-3 bg-emerald-50/50 border border-emerald-200/60 rounded-md space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-emerald-900 text-[11px]">
                          <Zap className="w-3.5 h-3.5 text-emerald-700" />
                          <span>Recommended Content Action (Post-Remediation)</span>
                        </div>
                        <p className="text-emerald-800/90 leading-relaxed">{item.recommended_answer}</p>
                      </div>
                    )}

                    {/* Score Bar & Gain */}
                    <div className="flex items-center justify-between pt-2 border-t border-line/50 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-ink">Citability Score:</span>
                        <div className="w-24 bg-paper-200 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.citability_score >= 7 ? 'bg-emerald-500' : item.citability_score >= 4 ? 'bg-amber-500' : 'bg-rose-500'}`}
                            style={{ width: `${item.citability_score * 10}%` }}
                          />
                        </div>
                        <span className="font-mono font-bold text-ink">{item.citability_score}/10</span>
                      </div>
                      {item.projected_patch_gain > 0 && (
                        <div className="text-good font-mono font-medium">
                          Expected Gain: +{Math.round(item.projected_patch_gain * 100)}%
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
