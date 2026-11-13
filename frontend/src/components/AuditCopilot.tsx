import React, { useState } from 'react';
import { askAuditCopilot, CopilotResponse } from '../services/api';
import { Card } from './ui';
import { Sparkles, Send, ShieldCheck, AlertTriangle } from 'lucide-react';

interface AuditCopilotProps {
  analysisId: string;
  domain: string;
}

const QUICK_PROMPTS = [
  'What are the highest-impact critical defects holding back conversions?',
  'Why is our AI Search / GEO citation readiness low, and what should we ship first?',
  'Summarize canonical, indexability, and schema issues on our pricing or commercial pages.',
];

export function AuditCopilot({ analysisId, domain }: AuditCopilotProps) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{ q: string; res: CopilotResponse }>>([]);

  const submitQuestion = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await askAuditCopilot(analysisId, trimmed);
      setHistory((prev) => [...prev, { q: trimmed, res }]);
      setQuestion('');
    } catch (err: any) {
      setError(err?.message || 'Failed to query Audit Copilot.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-line pb-4">
        <span className="text-[10px] font-mono uppercase tracking-[0.04em] text-ink-700 font-bold block">
          Evidence-Grounded Agentic Assistant
        </span>
        <h2 className="font-sans text-3xl text-ink font-semibold flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-teal-600" />
          Audit Copilot — {domain}
        </h2>
        <p className="text-xs text-ink-500 mt-1">
          Ask follow-up questions about findings, affected URLs, or remediation steps. Every answer cites verified evidence IDs.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => submitQuestion(p)}
            disabled={loading}
            className="text-xs px-3 py-1.5 rounded-full border border-line bg-surface hover:bg-slate-100 text-ink-700 transition"
          >
            {p}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submitQuestion(question);
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about a page, defect, score, or engineering fix..."
          className="flex-1 px-4 py-2.5 text-sm rounded-lg border border-line bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-700 text-white text-sm font-medium hover:bg-teal-800 disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          {loading ? 'Analyzing...' : 'Ask Copilot'}
        </button>
      </form>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="space-y-4">
        {history.map((item, idx) => (
          <Card key={idx} className="p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-line pb-2">
              <div className="text-sm font-semibold text-ink">{item.q}</div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                {item.res.mode}
              </span>
            </div>
            <div className="text-sm text-ink-700 whitespace-pre-wrap leading-relaxed">
              {item.res.answer}
            </div>
            {item.res.cited_evidence_ids.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-line">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span className="text-[11px] font-mono text-ink-500 mr-1">Cited Evidence:</span>
                {item.res.cited_evidence_ids.map((id) => (
                  <span
                    key={id}
                    className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200"
                  >
                    {id}
                  </span>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

