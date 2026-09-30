import React, { useState, useMemo } from 'react';
import { DynamicSandboxQuestionEvaluation } from '../types';
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
} from 'lucide-react';

interface DynamicQuestionSandboxViewProps {
  analysisId: string;
  initialEvaluations?: DynamicSandboxQuestionEvaluation[];
  onEvaluationsUpdate?: (updated: DynamicSandboxQuestionEvaluation[]) => void;
}

export function DynamicQuestionSandboxView({
  analysisId,
  initialEvaluations = [],
  onEvaluationsUpdate,
}: DynamicQuestionSandboxViewProps) {
  const [evaluations, setEvaluations] = useState<DynamicSandboxQuestionEvaluation[]>(initialEvaluations);
  const [selectedFacet, setSelectedFacet] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Facet catalog derived from evaluations or defaults
  const facets = useMemo(() => {
    const list = Array.from(new Set(evaluations.map((e) => e.facet))).filter(Boolean);
    return list.length > 0
      ? list
      : [
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

  // Aggregate metrics
  const totalCount = evaluations.length;
  const answerableCount = evaluations.filter((e) => e.answerability_status === 'ANSWERABLE' || e.is_answerable).length;
  const partialCount = evaluations.filter((e) => e.answerability_status === 'PARTIAL').length;
  const unanswerableCount = evaluations.filter(
    (e) => e.answerability_status === 'UNANSWERABLE' || (!e.is_answerable && e.answerability_status !== 'PARTIAL')
  ).length;
  const avgCitabilityScore =
    totalCount > 0
      ? Math.round((evaluations.reduce((acc, e) => acc + (e.citability_score || 0), 0) / totalCount) * 10) / 10
      : 0;

  // Filtered evaluations
  const filteredEvaluations = useMemo(() => {
    return evaluations.filter((item) => {
      // Facet filter
      if (selectedFacet !== 'all' && item.facet !== selectedFacet) {
        return false;
      }
      // Status filter
      if (statusFilter === 'answerable' && item.answerability_status !== 'ANSWERABLE') return false;
      if (statusFilter === 'partial' && item.answerability_status !== 'PARTIAL') return false;
      if (statusFilter === 'unanswerable' && item.answerability_status !== 'UNANSWERABLE') return false;

      // Text search
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesQ = item.generated_question.toLowerCase().includes(query);
        const matchesA = (item.crawled_answer || '').toLowerCase().includes(query);
        const matchesIntent = (item.buyer_intent || '').toLowerCase().includes(query);
        const matchesId = item.question_id.toLowerCase().includes(query);
        if (!matchesQ && !matchesA && !matchesIntent && !matchesId) {
          return false;
        }
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
        throw new Error(`Failed to generate dynamic sandbox: ${res.statusText}`);
      }
      const data = await res.json();
      if (data.evaluations && Array.isArray(data.evaluations)) {
        setEvaluations(data.evaluations);
        if (onEvaluationsUpdate) {
          onEvaluationsUpdate(data.evaluations);
        }
      }
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
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Answerable on Site
          </span>
        );
      case 'PARTIAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-300">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Partial Evidence
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 border border-rose-300">
            <XCircle className="w-3 h-3 text-rose-600" />
            Unanswerable Gap
          </span>
        );
    }
  };

  return (
    <div className="sheet border border-line rounded-lg p-6 space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-pine" />
            <h3 className="font-serif text-xl text-ink">
              Dynamic 100-Question AI Sandbox & Grounded Answer Check
            </h3>
          </div>
          <p className="text-xs text-ink-500 max-w-3xl">
            100 bespoke commercial & technical inquiries synthesized by AI tailored to this specific website and industry category.
            Every question executes an automated <strong>Answer Check</strong> against crawled DOM evidence to identify extractable answers, citability scores, and citation gaps.
          </p>
        </div>

        <button
          onClick={handleGenerateOrRefresh}
          disabled={isLoading}
          className="btn-secondary text-xs flex items-center gap-2 px-3 py-2 rounded-md transition-colors"
          title="Synthesize & re-evaluate 100 dynamic inquiries with active AI"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-pine' : ''}`} />
          {isLoading ? 'Synthesizing with AI...' : totalCount > 0 ? 'Re-Evaluate 100 Questions' : 'Generate 100 Questions'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-md">
          {error}
        </div>
      )}

      {/* Aggregate Scorecards */}
      {totalCount > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="p-3 bg-paper-50 border border-line rounded-md text-center">
            <span className="label text-[10px] text-ink-400 block">Total Inquiries</span>
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
            <span className="label text-[10px] text-rose-800 block">Unanswerable Gaps</span>
            <span className="text-xl font-bold font-mono text-rose-700">
              {unanswerableCount}{' '}
              <span className="text-xs font-normal">({Math.round((unanswerableCount / totalCount) * 100)}%)</span>
            </span>
          </div>
          <div className="p-3 bg-indigo-50/60 border border-indigo-200 rounded-md text-center col-span-2 md:col-span-1">
            <span className="label text-[10px] text-indigo-800 block">Avg Citability Score</span>
            <span className="text-xl font-bold font-mono text-indigo-700">
              {avgCitabilityScore} <span className="text-xs font-normal">/ 10</span>
            </span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-paper-50 p-3 rounded-md border border-line">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-ink-600">Status:</span>
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-2.5 py-1 text-xs rounded-md font-mono transition-colors ${
              statusFilter === 'all' ? 'bg-pine text-white font-semibold' : 'bg-paper text-ink-600 hover:bg-paper-100 border border-line'
            }`}
          >
            All ({evaluations.length})
          </button>
          <button
            onClick={() => setStatusFilter('answerable')}
            className={`px-2.5 py-1 text-xs rounded-md font-mono transition-colors ${
              statusFilter === 'answerable'
                ? 'bg-emerald-700 text-white font-semibold'
                : 'bg-paper text-emerald-800 hover:bg-emerald-50 border border-emerald-200'
            }`}
          >
            Answerable ({answerableCount})
          </button>
          <button
            onClick={() => setStatusFilter('partial')}
            className={`px-2.5 py-1 text-xs rounded-md font-mono transition-colors ${
              statusFilter === 'partial'
                ? 'bg-amber-700 text-white font-semibold'
                : 'bg-paper text-amber-800 hover:bg-amber-50 border border-amber-200'
            }`}
          >
            Partial ({partialCount})
          </button>
          <button
            onClick={() => setStatusFilter('unanswerable')}
            className={`px-2.5 py-1 text-xs rounded-md font-mono transition-colors ${
              statusFilter === 'unanswerable'
                ? 'bg-rose-700 text-white font-semibold'
                : 'bg-paper text-rose-800 hover:bg-rose-50 border border-rose-200'
            }`}
          >
            Gaps ({unanswerableCount})
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-ink-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search questions or answers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-paper border border-line rounded-md focus:outline-none focus:border-pine"
          />
        </div>
      </div>

      {/* Facet Tabs */}
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

      {/* Questions List */}
      {filteredEvaluations.length === 0 ? (
        <div className="text-center py-10 bg-paper-50 rounded-md border border-line">
          <HelpCircle className="w-8 h-8 text-ink-300 mx-auto mb-2" />
          <p className="text-sm font-medium text-ink-700">No questions match the current filters.</p>
          <p className="text-xs text-ink-500 mt-1">Try resetting the status filter or searching for another keyword.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEvaluations.map((item) => {
            const isExpanded = expandedId === item.question_id;
            return (
              <div
                key={item.question_id}
                className="border border-line rounded-md bg-paper transition-shadow hover:shadow-sm"
              >
                {/* Collapsed Header Summary */}
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
                        {item.facet}
                      </span>
                      {getStatusBadge(item.answerability_status)}
                      <span className="text-xs font-mono text-ink-500 ml-auto flex items-center gap-1">
                        Citability: <strong className="text-ink">{item.citability_score}/10</strong>
                      </span>
                    </div>

                    <h4 className="text-sm font-semibold text-ink leading-snug">
                      {item.generated_question}
                    </h4>

                    <p className="text-xs text-ink-500 italic line-clamp-1">
                      Intent: {item.buyer_intent}
                    </p>
                  </div>

                  <button className="text-ink-400 hover:text-ink pt-1">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>

                {/* Expanded Answer Check Details */}
                {isExpanded && (
                  <div className="border-t border-line bg-paper-50 p-4 space-y-4 text-xs">
                    {/* The Answer Check Box */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-ink font-semibold">
                        <Quote className="w-3.5 h-3.5 text-pine" />
                        <span>Answer Check: Detected Content on Crawled Site</span>
                      </div>
                      <div className="p-3 bg-paper border border-line rounded-md text-ink-700 leading-relaxed font-sans">
                        {item.crawled_answer}
                      </div>
                    </div>

                    {/* Evidence Snippet & URL */}
                    {item.evidence_snippet && (
                      <div className="space-y-1 bg-paper/60 p-3 rounded-md border border-line/60">
                        <div className="flex items-center justify-between text-[11px] text-ink-500">
                          <span className="font-medium text-ink-600">DOM Evidence Snippet:</span>
                          {item.evidence_url && (
                            <a
                              href={item.evidence_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-pine hover:underline flex items-center gap-1 text-[11px]"
                            >
                              <span>View Source URL</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                        <blockquote className="font-mono text-[11px] text-ink-600 border-l-2 border-pine pl-2.5 py-0.5">
                          "{item.evidence_snippet}"
                        </blockquote>
                      </div>
                    )}

                    {/* Citability Gap Analysis */}
                    {item.gap_analysis && (
                      <div className="p-3 bg-amber-50/50 border border-amber-200/60 rounded-md space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-amber-900 text-[11px]">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                          <span>Citability Gap Analysis</span>
                        </div>
                        <p className="text-amber-800/90 leading-relaxed">
                          {item.gap_analysis}
                        </p>
                      </div>
                    )}

                    {/* Recommended Authoritative Answer */}
                    {item.recommended_answer && (
                      <div className="p-3 bg-emerald-50/50 border border-emerald-200/60 rounded-md space-y-1">
                        <div className="flex items-center gap-1.5 font-semibold text-emerald-900 text-[11px]">
                          <Zap className="w-3.5 h-3.5 text-emerald-700" />
                          <span>Recommended Authoritative Answer (Post-Remediation)</span>
                        </div>
                        <p className="text-emerald-800/90 leading-relaxed">
                          {item.recommended_answer}
                        </p>
                      </div>
                    )}

                    {/* Score Bar & Gain */}
                    <div className="flex items-center justify-between pt-2 border-t border-line/50 text-[11px]">
                      <div className="flex items-center gap-2">
                        <Target className="w-3.5 h-3.5 text-pine" />
                        <span className="font-medium text-ink">Citability Readiness:</span>
                        <div className="w-24 bg-paper-200 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              item.citability_score >= 7
                                ? 'bg-emerald-500'
                                : item.citability_score >= 4
                                ? 'bg-amber-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${item.citability_score * 10}%` }}
                          />
                        </div>
                        <span className="font-mono font-bold text-ink">{item.citability_score}/10</span>
                      </div>

                      {item.projected_patch_gain && (
                        <div className="text-good font-mono font-medium">
                          Expected Patch Boost: +{Math.round(item.projected_patch_gain * 100)}%
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
