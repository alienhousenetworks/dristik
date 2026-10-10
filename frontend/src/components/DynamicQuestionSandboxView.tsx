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
    pct >= 60 ? 'bg-good/10' : pct >= 30 ? 'bg-warn/10' : 'bg-bad/10';
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
    HIGH: 'bg-bad/10 text-bad border-bad/30',
    MEDIUM: 'bg-warn/10 text-warn border-warn/30',
    LOW: 'bg-good/10 text-good border-good/30',
  }[risk] ?? 'bg-paper-100 text-ink-600 border-line';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${config}`}>
      Answer Risk: {risk}
    </span>
  );
}

function ClaimDecompositionPanel({ claims }: { claims: KieClaimGroundingResult[] }) {
  if (!claims || claims.length === 0) return null;
  const statusConfig = {
    SUPPORTED: { color: 'text-good bg-good/10 border-good/30', icon: '✓' },
    PARTIALLY_SUPPORTED: { color: 'text-warn bg-warn/10 border-warn/30', icon: '◐' },
    UNSUPPORTED: { color: 'text-bad bg-bad/10 border-bad/30', icon: '✗' },
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
    <div className="rounded-lg border border-line bg-paper-100 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-ink-700" />
        <h4 className="font-semibold text-sm text-ink-700">
          5-Dimension AI Visibility Scorecard
        </h4>
        <span className="ml-auto text-[10px] font-mono text-ink-700 border border-line rounded px-1.5 py-0.5">
          {dims.weighting_profile}
        </span>
      </div>
      <p className="text-[11px] text-ink-700">
        Each dimension is measured independently. No arbitrary equal-weighting or composite rollup is applied.
        An aggregate index, if shown, is explicitly labelled with its weighting profile.
      </p>
      <div className="space-y-3">
        {dimensions.map((d) => (
          <div key={d.key}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-ink-700">
                {d.icon}
                {d.label}
              </div>
              <span className="font-mono text-xs font-bold text-ink-700">{d.value}%</span>
            </div>
            <GroundingBar ratio={d.value / 100} size="lg" />
            <p className="text-[10px] text-ink-700 mt-0.5">{d.description}</p>
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
    <div className="rounded-lg border border-line bg-paper-50 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Database className="w-4 h-4 text-ink-700" />
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
                ? 'bg-bad/10 border-bad/30 text-bad'
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
        <div className="text-[11px] text-bad bg-bad/10 border border-bad/30 rounded p-2 flex items-start gap-1.5">
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

  const isGap = (e: DynamicSandboxQuestionEvaluation) =>
    e.answerability_status === 'EVIDENCE_GAP' ||
    e.answerability_status === 'UNANSWERABLE' ||
    (!e.is_answerable && e.answerability_status !== 'PARTIAL');

  const totalCount = evaluations.length;
  const answerableCount = evaluations.filter((e) => e.answerability_status === 'ANSWERABLE' || (e.is_answerable && e.answerability_status !== 'PARTIAL')).length;
  const partialCount = evaluations.filter((e) => e.answerability_status === 'PARTIAL').length;
  const unanswerableCount = evaluations.filter(isGap).length;

  const validGroundings = evaluations.filter((e) => e.grounding_ratio != null);
  const avgGrounding =
    validGroundings.length > 0
      ? Math.round((validGroundings.reduce((acc, e) => acc + (e.grounding_ratio ?? 0), 0) / validGroundings.length) * 100)
      : null;
  const highRiskCount = evaluations.filter((e) => e.answer_risk === 'HIGH').length;

  const filteredEvaluations = useMemo(() => {
    return evaluations.filter((item) => {
      if (selectedFacet !== 'all' && item.facet !== selectedFacet) return false;
      if (statusFilter === 'answerable' && item.answerability_status !== 'ANSWERABLE' && !item.is_answerable) return false;
      if (statusFilter === 'partial' && item.answerability_status !== 'PARTIAL') return false;
      if (statusFilter === 'unanswerable' && !isGap(item)) return false;
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
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || `Server returned ${res.status}: ${res.statusText}`);
      }
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
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-good/10 text-good border border-good/30">
            <CheckCircle2 className="w-3 h-3 text-good" /> Answerable
          </span>
        );
      case 'PARTIAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-warn/10 text-warn border border-warn/30">
            <AlertTriangle className="w-3 h-3 text-warn" /> Partial Evidence
          </span>
        );
      case 'CONFLICTING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-paper-100 text-ink-700 border border-line">
            <AlertTriangle className="w-3 h-3 text-ink-700" /> Conflicting Evidence
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-bad/10 text-bad border border-bad/30">
            <XCircle className="w-3 h-3 text-bad" /> Evidence Gap
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
            <Sparkles className="w-5 h-5 text-ink-700" />
            <h3 className="font-sans text-xl text-ink">
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
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-ink-700' : ''}`} />
          {isLoading ? 'Building Knowledge Graph...' : totalCount > 0 ? 'Re-Evaluate Inquiries' : 'Synthesize 100 Questions'}
        </button>
      </div>

      {error && (
        <div className="p-3.5 bg-bad/10 border border-bad/30 text-bad text-xs rounded-md flex items-center justify-between gap-3">
          <span>{error}</span>
          <button
            onClick={handleGenerateOrRefresh}
            className="underline text-xs font-medium hover:opacity-80 shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── KIE Knowledge Graph Summary ── */}
      {kieGraphSummary && <KieGraphSummaryPanel summary={kieGraphSummary} />}

      {/* ── 5-Dimension Scorecard ── */}
      {fiveDimensions && (
        <div>
          <button
            className="text-xs font-semibold text-ink-700 hover:underline flex items-center gap-1.5 mb-2"
            onClick={() => setShowDimensions(!showDimensions)}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            {showDimensions ? 'Hide' : 'Show'} 5-Dimension AI Visibility Scorecard
          </button>
          {showDimensions && <FiveDimensionPanel dims={fiveDimensions} />}
        </div>
      )}

      {/* ── Uninitialized / Empty Sandbox: Readiness Card ── */}
      {totalCount === 0 ? (
        <div className="rounded-xl border border-line bg-paper-50 p-6 md:p-8 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-pine/10 text-pine border border-pine/30">
                <span className="w-1.5 h-1.5 rounded-full bg-pine animate-pulse" />
                Knowledge Graph Standby · Ready for Inquiry Synthesis
              </div>
              <h4 className="text-base font-semibold text-ink">
                100-Question Dynamic AI Sandbox & Grounding Check
              </h4>
              <p className="text-xs text-ink-600 max-w-2xl leading-relaxed">
                Synthesize 100 bespoke commercial buyer inquiries across 10 strategic facets (Identity, ICP, Pricing, Core Capabilities, Tech Stack, Competitive Moat, Enterprise Trust, Customer Proof, Onboarding, Purchase Flow). Each inquiry is evaluated using <strong>Hybrid Retrieval + Claim Grounding Verification</strong> to audit how AI engines (ChatGPT, Perplexity, Claude, Gemini) cite or hallucinate answers.
              </p>
            </div>
            <button
              onClick={handleGenerateOrRefresh}
              disabled={isLoading}
              className="btn-primary text-xs px-4 py-3 rounded-lg shadow-sm flex items-center justify-center gap-2 shrink-0 transition-transform active:scale-95"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              {isLoading ? 'Synthesizing 100 Questions...' : 'Synthesize 100 AI Inquiries & Check Grounding'}
            </button>
          </div>

          {/* 3-Pillar Readiness Inspection Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            <div className="p-3.5 rounded-lg border border-line bg-paper space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                <Database className="w-4 h-4 text-pine" />
                <span>1. Knowledge Graph Extraction</span>
              </div>
              <p className="text-[11px] text-ink-500 leading-normal">
                Maps entities, relationships, and first-party claims from crawled pages to construct the domain authority graph.
              </p>
            </div>
            <div className="p-3.5 rounded-lg border border-line bg-paper space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                <Search className="w-4 h-4 text-pine" />
                <span>2. Hybrid Evidence Retriever</span>
              </div>
              <p className="text-[11px] text-ink-500 leading-normal">
                Runs Query Planner to retrieve top-5 evidence chunks per inquiry using semantic vector + lexical BM25 matching.
              </p>
            </div>
            <div className="p-3.5 rounded-lg border border-line bg-paper space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                <GitBranch className="w-4 h-4 text-pine" />
                <span>3. Claim-Level Grounding Verifier</span>
              </div>
              <p className="text-[11px] text-ink-500 leading-normal">
                Decomposes candidate answers into atomic claims to audit citation accuracy, calculating Grounding Ratio and Answer Risk.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* ── Aggregate Scorecards ── */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-3 bg-paper-50 border border-line rounded-md text-center">
              <span className="label text-[10px] text-ink-400 block">Total Questions</span>
              <span className="text-xl font-bold font-mono text-ink">{totalCount}</span>
            </div>
            <div className="p-3 bg-good/10 border border-good/30 rounded-md text-center">
              <span className="label text-[10px] text-good block">Answerable</span>
              <span className="text-xl font-bold font-mono text-good">
                {answerableCount}{' '}
                <span className="text-xs font-normal">({Math.round((answerableCount / totalCount) * 100)}%)</span>
              </span>
            </div>
            <div className="p-3 bg-warn/10 border border-warn/30 rounded-md text-center">
              <span className="label text-[10px] text-warn block">Partial Evidence</span>
              <span className="text-xl font-bold font-mono text-warn">
                {partialCount}{' '}
                <span className="text-xs font-normal">({Math.round((partialCount / totalCount) * 100)}%)</span>
              </span>
            </div>
            <div className="p-3 bg-bad/10 border border-bad/30 rounded-md text-center">
              <span className="label text-[10px] text-bad block">Evidence Gaps</span>
              <span className="text-xl font-bold font-mono text-bad">
                {unanswerableCount}{' '}
                <span className="text-xs font-normal">({Math.round((unanswerableCount / totalCount) * 100)}%)</span>
              </span>
            </div>
            <div className="p-3 bg-paper-100 border border-line rounded-md text-center col-span-2 md:col-span-1">
              <span className="label text-[10px] text-ink-700 block">Avg Grounding</span>
              <span className="text-xl font-bold font-mono text-ink-700">
                {avgGrounding !== null ? `${avgGrounding}%` : '—'}
              </span>
            </div>
          </div>

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
                  ? 'border-b-2 border-line text-ink-700 bg-paper-50 font-semibold'
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
                      ? 'border-b-2 border-line text-ink-700 bg-paper-50 font-semibold'
                      : 'text-ink-500 hover:text-ink hover:bg-paper-50'
                  }`}
                >
                  {shortFacet} ({facetCount})
                </button>
              );
            })}
          </div>

          {/* ── Question Cards or Filter Empty State ── */}
          {filteredEvaluations.length === 0 ? (
            <div className="text-center py-10 bg-paper-50 rounded-md border border-line space-y-2">
              <HelpCircle className="w-8 h-8 text-ink-300 mx-auto" />
              <p className="text-sm font-medium text-ink-700">No questions match the current filters.</p>
              <p className="text-xs text-ink-500">
                {statusFilter !== 'all' ? `Status: ${statusFilter}. ` : ''}
                {selectedFacet !== 'all' ? `Facet: ${selectedFacet.split(',')[0]}. ` : ''}
                {searchQuery ? `Search: "${searchQuery}".` : ''}
              </p>
              <button
                onClick={() => {
                  setStatusFilter('all');
                  setSelectedFacet('all');
                  setSearchQuery('');
                }}
                className="text-xs text-pine font-medium underline hover:opacity-80 pt-1"
              >
                Reset all filters and clear search
              </button>
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
                      <span className="font-mono text-xs font-bold text-ink-700 bg-paper-200 px-2 py-0.5 rounded">
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
                            <Target className="w-3.5 h-3.5 text-ink-700" /> Grounding Ratio
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
                        <Quote className="w-3.5 h-3.5 text-ink-700" />
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

                    {/* Missing Inquiry Aspects for Partials or Gaps */}
                    {item.missing_aspects && item.missing_aspects.length > 0 && (
                      <div className="p-3 bg-warn/10 border border-warn/30 rounded-md space-y-1.5">
                        <div className="text-[11px] font-semibold text-warn flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-warn" />
                          <span>Missing Inquiry Aspects (Unsubstantiated by Crawled Copy)</span>
                        </div>
                        <ul className="list-disc list-inside text-[11px] text-warn space-y-0.5">
                          {item.missing_aspects.map((asp, idx) => (
                            <li key={idx} className="font-mono text-[10px]">{asp}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Evidence Source */}
                    {item.evidence_snippet && (
                      <div className="space-y-1 bg-paper/60 p-3 rounded-md border border-line/60">
                        <div className="flex items-center justify-between text-[11px] text-ink-500">
                          <span className="font-medium text-ink-600">Primary Evidence Snippet:</span>
                          {item.evidence_url && (
                            <a href={item.evidence_url} target="_blank" rel="noreferrer"
                              className="text-ink-700 hover:underline flex items-center gap-1 text-[11px]">
                              View Source <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                        <blockquote className="font-mono text-[11px] text-ink-600 border-l-2 border-line pl-2.5 py-0.5">
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
                          ? 'bg-bad/10 border-bad/30'
                          : item.answer_risk === 'MEDIUM'
                          ? 'bg-warn/10 border-warn/30'
                          : 'bg-warn/10 border-warn/30'
                      }`}>
                        <div className="flex items-center gap-1.5 font-semibold text-[11px] text-warn">
                          <AlertTriangle className="w-3.5 h-3.5 text-warn" />
                          <span>Evidence Gap & Answer Risk</span>
                        </div>
                        <p className="text-warn leading-relaxed">{item.gap_analysis}</p>
                      </div>
                    )}

                    {/* Recommended Answer */}
                    {item.recommended_answer && (
                      <div className="p-3 bg-good/10 border border-good/30 rounded-md space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-good text-[11px]">
                          <Zap className="w-3.5 h-3.5 text-good" />
                          <span>Recommended Content Action (Post-Remediation)</span>
                        </div>
                        <p className="text-good leading-relaxed">{item.recommended_answer}</p>
                      </div>
                    )}

                    {/* Score Bar & Gain */}
                    <div className="flex items-center justify-between pt-2 border-t border-line/50 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-ink">Citability Score:</span>
                        <div className="w-24 bg-paper-200 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.citability_score >= 7 ? 'bg-good/10' : item.citability_score >= 4 ? 'bg-warn/10' : 'bg-bad/10'}`}
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
        </>
      )}
    </div>
  );
}
