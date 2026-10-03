import React from 'react';
import { Sparkles, Zap, AlertCircle, Info } from 'lucide-react';
import { ControlledRetrievalReport, AnalyzedChunk } from '../../types';

export interface RagChunkVisualizerProps {
  report: ControlledRetrievalReport | null;
  loading?: boolean;
  error?: string | null;
  query: string;
  onQueryChange: (q: string) => void;
  onRunAnalysis: () => void;
}

export const ControlledRetrievalVisualizer: React.FC<RagChunkVisualizerProps> = ({
  report,
  loading = false,
  error = null,
  query,
  onQueryChange,
  onRunAnalysis,
}) => {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
          <Zap className="w-4 h-4 text-ink-700" /> Controlled Semantic Retrieval Analysis
        </h3>
        <p className="text-xs text-ink-500 mt-1">
          Dristik's controlled semantic retrieval methodology evaluates how well crawled page content aligns with buyer queries under deterministic chunking and cosine similarity.
        </p>
      </div>

      {/* Methodology & Scope Disclosure Card */}
      <div className="p-3.5 bg-ink-50 rounded-lg border border-ink/10 text-xs space-y-2">
        <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-ink-700">
          <Info className="w-3.5 h-3.5 text-ink-700 shrink-0" />
          <span>Methodology & Configuration Disclosure</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[11px] text-ink-600">
          <div className="bg-paper-50/80 p-2 rounded border border-ink/5">
            <span className="text-ink-400 block text-[9px] uppercase tracking-[0.04em]">Embedding Model</span>
            <span className="font-bold text-ink">{report?.methodology?.embedding_model || 'E5-small-v2'}</span>
          </div>
          <div className="bg-paper-50/80 p-2 rounded border border-ink/5">
            <span className="text-ink-400 block text-[9px] uppercase tracking-[0.04em]">Chunking Strategy</span>
            <span className="font-bold text-ink">{report?.methodology?.chunk_size || 250} words / {report?.methodology?.chunk_overlap || 40} overlap</span>
          </div>
          <div className="bg-paper-50/80 p-2 rounded border border-ink/5">
            <span className="text-ink-400 block text-[9px] uppercase tracking-[0.04em]">Similarity Metric</span>
            <span className="font-bold text-ink">Cosine Similarity</span>
          </div>
          <div className="bg-paper-50/80 p-2 rounded border border-ink/5">
            <span className="text-ink-400 block text-[9px] uppercase tracking-[0.04em]">Threshold Criterion</span>
            <span className="font-bold text-ink">{report?.methodology?.similarity_threshold || 0.72}</span>
          </div>
        </div>
        <p className="text-[10px] text-ink-500 italic pt-1 border-t border-ink/5">
          <strong>Important:</strong> These measurements represent Dristik's controlled semantic retrieval methodology.
          They are not measurements or predictions of proprietary retrieval systems used by ChatGPT,
          Perplexity, Gemini, Claude, or other external AI engines.
        </p>
      </div>

      {/* Query Bar */}
      <div className="space-y-2 pt-1">
        <label className="text-xs font-semibold text-ink-700 block">Target Inquiry / Query Prompt:</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            className="flex-1 px-3 py-2 text-xs border border-ink/20 rounded-md focus:outline-none focus:ring-2 focus:ring-pine/30 bg-paper-50"
            placeholder="Enter target inquiry to measure semantic retrieval similarity..."
          />
          <button
            type="button"
            onClick={onRunAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-pine hover:bg-pine-700 text-white rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            {loading ? <Sparkles className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            <span>{loading ? 'Analyzing...' : 'Run Analysis'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-bad/10 text-bad rounded-md text-xs font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Visualizer Chunks */}
      {report && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between text-xs">
            <h4 className="font-mono text-xs font-bold text-ink-600 uppercase tracking-[0.04em]">
              Evaluated Chunks ({report.total_chunks} Total · {report.qualifying_chunks_count} Passing Dristik Threshold)
            </h4>
            <span className="font-mono text-ink-500">
              Pass Rate: {report.threshold_pass_rate_pct}% · Top Similarity: {report.top_chunk_similarity}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {report.chunks.map((c: AnalyzedChunk, i: number) => (
              <div
                key={i}
                className={`p-3.5 rounded-lg border text-xs space-y-2 ${
                  c.passes_threshold ? 'bg-good/5 border-good/30' : 'bg-ink-50/60 border-ink/10'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-ink flex items-center gap-2">
                    <span>{c.chunk_id}</span>
                    <span className="text-[10px] text-ink-400 font-normal">({c.word_count} words)</span>
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-mono text-[11px] px-2 py-0.5 rounded font-bold ${
                        c.passes_threshold ? 'bg-good/10 text-good' : 'bg-ink-100 text-ink-600'
                      }`}
                    >
                      Cosine: {c.similarity_score}
                    </span>
                    <span
                      className={`font-mono text-[10px] px-1.5 py-0.5 rounded uppercase font-bold ${
                        c.passes_threshold ? 'bg-good text-white' : 'bg-ink-200 text-ink-700'
                      }`}
                    >
                      {c.passes_threshold ? `Passes Threshold (Rank #${c.retrieval_rank})` : 'Below Dristik Threshold'}
                    </span>
                  </div>
                </div>
                <p className="font-mono text-[11px] text-ink-700 leading-relaxed bg-paper-50/70 p-2.5 rounded border border-ink/5">
                  {c.content}
                </p>
                {c.evaluation_notes && c.evaluation_notes.length > 0 && (
                  <div className="text-[10px] text-ink-500 font-mono flex items-center gap-1">
                    <Info className="w-3 h-3 shrink-0 text-ink-700" />
                    <span>{c.evaluation_notes.join(' · ')}</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {report.content_structure_recommendations && report.content_structure_recommendations.length > 0 && (
            <div className="p-3 bg-paper-100 border border-line rounded-md text-xs space-y-1">
              <span className="font-semibold text-ink block">Dristik Content Structure Observations:</span>
              <ul className="list-disc list-inside text-ink-700 space-y-0.5 text-[11px]">
                {report.content_structure_recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Backward-compatible alias
export const RagChunkVisualizer = ControlledRetrievalVisualizer;
export default ControlledRetrievalVisualizer;
