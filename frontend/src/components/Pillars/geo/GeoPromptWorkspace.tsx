import React, { useMemo, useState } from 'react';
import { Card } from '../../ui';
import { GeoEnterpriseBundle, GeoTestPromptRecord, geoApi } from '../../../services/geoApi';
import { CheckCircle2, Eye, FlaskConical, Plus, Search, ShieldCheck, XCircle } from 'lucide-react';

interface GeoPromptWorkspaceProps {
  bundle: GeoEnterpriseBundle;
  mode: 'prompts' | 'prompt_lab';
  onRefreshBundle: (auditId?: string) => Promise<void>;
}

function highlightBrandAndCompetitors(text: string, brand: string, competitors: string[]) {
  if (!text) return 'No response text captured.';
  const terms = [brand, ...competitors].filter((t) => t && t.length >= 2);
  if (terms.length === 0) return text;
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, idx) => {
    const low = part.toLowerCase();
    if (brand && low === brand.toLowerCase()) {
      return (
        <mark key={idx} className="bg-good/20 text-ink font-semibold px-0.5 rounded">
          {part}
        </mark>
      );
    }
    if (competitors.some((c) => c.toLowerCase() === low)) {
      return (
        <mark key={idx} className="bg-warn/20 text-ink font-semibold px-0.5 rounded">
          {part}
        </mark>
      );
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

export function GeoPromptWorkspace({ bundle, mode, onRefreshBundle }: GeoPromptWorkspaceProps) {
  const [filterScope, setFilterScope] = useState<'all' | 'non_branded' | 'branded'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [newQuestion, setNewQuestion] = useState('');
  const [newBranded, setNewBranded] = useState(false);
  const [newCategory, setNewCategory] = useState('category_discovery');
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const [selectedPromptId, setSelectedPromptId] = useState<string>(bundle.prompts[0]?.prompt_id || '');

  // Prompt Test Lab interactive execution state
  const [labPrompt, setLabPrompt] = useState(
    bundle.prompts[0]?.question || `What are the leading ${bundle.scope?.industry || 'software'} solutions?`,
  );
  const [labRunning, setLabRunning] = useState(false);
  const [labResults, setLabResults] = useState<Array<Record<string, any>>>([]);
  const [labError, setLabError] = useState<string | null>(null);

  const brand = bundle.audit.brand_name;
  const competitors: string[] = bundle.scope?.competitors || [];

  const filteredPrompts = useMemo(() => {
    return bundle.prompts.filter((p) => {
      if (filterScope === 'branded' && !p.is_branded) return false;
      if (filterScope === 'non_branded' && p.is_branded) return false;
      if (categoryFilter !== 'all' && p.category !== categoryFilter) return false;
      return true;
    });
  }, [bundle.prompts, filterScope, categoryFilter]);

  const categories = useMemo(
    () => Array.from(new Set(bundle.prompts.map((p) => p.category))).sort(),
    [bundle.prompts],
  );

  const handleCreatePrompt = async () => {
    if (!newQuestion.trim()) return;
    setValidationMsg(null);
    try {
      const val = await geoApi.validatePrompt({
        question: newQuestion.trim(),
        brand_name: brand,
        category: newCategory,
        is_branded: newBranded,
        existing_questions: bundle.prompts.map((p) => p.question),
      });
      if (!val.valid) {
        setValidationMsg(`Validation rejected: ${val.quality_flags.join('; ')}`);
        return;
      }
      await geoApi.approvePrompt({
        audit_id: bundle.audit.audit_id,
        question: newQuestion.trim(),
        category: newCategory,
        is_branded: newBranded,
        target_brand: brand,
        approval_status: 'approved',
      });
      setNewQuestion('');
      setValidationMsg('Prompt validated and added to approved test suite.');
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (err: any) {
      setValidationMsg(err?.message || 'Could not add prompt.');
    }
  };

  const handleToggleApproval = async (p: GeoTestPromptRecord, nextStatus: 'approved' | 'excluded') => {
    try {
      await geoApi.approvePrompt({
        prompt_id: p.prompt_id,
        category: p.category,
        is_branded: p.is_branded,
        approval_status: nextStatus,
      });
      await onRefreshBundle(bundle.audit.audit_id);
    } catch {
      /* handled silently when viewing offline snapshot */
    }
  };

  const handleRunLab = async () => {
    setLabRunning(true);
    setLabError(null);
    try {
      const res = await geoApi.runPromptLab({
        audit_id: bundle.audit.audit_id,
        prompt: labPrompt,
        brand_name: brand,
        domain: bundle.audit.domain,
        competitors,
        platforms: ['chatgpt', 'gemini', 'claude', 'perplexity'],
      });
      setLabResults(res.results || []);
    } catch (err: any) {
      setLabError(err?.message || 'Prompt Test Lab execution failed.');
    } finally {
      setLabRunning(false);
    }
  };

  const capturedForSelected = bundle.responses.filter((r) => !selectedPromptId || r.prompt_id === selectedPromptId);

  if (mode === 'prompt_lab') {
    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-pine" /> Side-by-Side Prompt Test Lab (Verbatim Response Inspector)
              </h3>
              <p className="text-xs text-ink-500">
                Inspect exact AI responses with highlighted brand mentions (green), competitor mentions (amber), cited URLs, model versions, and testing mode.
              </p>
            </div>
            <button
              type="button"
              onClick={handleRunLab}
              disabled={labRunning}
              className="px-4 py-2 bg-pine text-white text-xs font-semibold rounded hover:bg-pine/90 disabled:opacity-50"
            >
              {labRunning ? 'Testing Platforms…' : 'Execute Side-by-Side Test'}
            </button>
          </div>
          <textarea
            rows={2}
            value={labPrompt}
            onChange={(e) => setLabPrompt(e.target.value)}
            className="w-full p-3 border border-line rounded text-xs font-mono bg-white"
            placeholder="Enter a branded or non-branded test prompt..."
          />
          {labError && <p className="text-xs text-bad font-mono">{labError}</p>}

          {labResults.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {labResults.map((r, i) => (
                <div key={i} className="p-4 border border-line rounded bg-paper-50 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink">{r.display_name || r.platform_id}</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white border border-line">
                      {r.status} · {r.testing_mode}
                    </span>
                  </div>
                  {r.response ? (
                    <>
                      <div className="p-3 bg-white border border-line rounded whitespace-pre-wrap leading-relaxed text-[11px]">
                        {highlightBrandAndCompetitors(r.response.response_text, brand, competitors)}
                      </div>
                      <div className="flex flex-wrap gap-2 font-mono text-[10px] text-ink-600">
                        <span>Model: {r.model_version}</span>
                        <span>Mentioned: {r.response.brand_mentioned ? 'Yes' : 'No'}</span>
                        <span>Recommended: {r.response.brand_recommended ? 'Yes' : 'No'}</span>
                        <span>Cited: {r.response.brand_cited ? 'Yes' : 'No'}</span>
                        <span>Sentiment: {r.response.sentiment}</span>
                      </div>
                    </>
                  ) : (
                    <p className="text-ink-500 italic">{r.error || 'Platform not configured.'}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Captured Audit Responses Inspector */}
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-sans font-bold text-ink text-sm flex items-center gap-2">
              <Eye className="w-4 h-4 text-pine" /> Captured Audit Verbatim Responses ({bundle.responses.length})
            </h4>
            <select
              value={selectedPromptId}
              onChange={(e) => setSelectedPromptId(e.target.value)}
              className="text-xs border border-line rounded px-2.5 py-1.5 bg-white max-w-md"
            >
              <option value="">All prompts ({bundle.responses.length} responses)</option>
              {bundle.prompts.map((p) => (
                <option key={p.prompt_id} value={p.prompt_id}>
                  [{p.is_branded ? 'Branded' : 'Non-Branded'}] {p.question.slice(0, 75)}
                </option>
              ))}
            </select>
          </div>
          {capturedForSelected.length === 0 ? (
            <p className="text-xs text-ink-500">
              No live AI responses captured for this selection yet. Connect a provider or run the Prompt Test Lab above.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {capturedForSelected.slice(0, 12).map((resp) => (
                <div key={resp.response_id} className="p-4 border border-line rounded bg-paper-50 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink uppercase">{resp.platform_id}</span>
                    <span className="font-mono text-[10px] text-ink-500">
                      {resp.model_version} · {resp.testing_mode}
                    </span>
                  </div>
                  <div className="p-3 bg-white border border-line rounded whitespace-pre-wrap text-[11px] leading-relaxed max-h-56 overflow-y-auto">
                    {highlightBrandAndCompetitors(resp.response_text, brand, competitors)}
                  </div>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                    <span className={`px-1.5 py-0.5 rounded ${resp.brand_mentioned ? 'bg-good/10 text-good' : 'bg-paper-200 text-ink-500'}`}>
                      Mention: {resp.brand_mentioned ? 'Observed' : 'Not observed'}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded ${resp.brand_recommended ? 'bg-good/10 text-good' : 'bg-paper-200 text-ink-500'}`}>
                      Recommendation: {resp.brand_recommended ? 'Yes' : 'No'}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded ${resp.brand_cited ? 'bg-pine/10 text-pine' : 'bg-paper-200 text-ink-500'}`}>
                      Owned Citation: {resp.brand_cited ? 'Yes' : 'No'}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-paper-200 text-ink-600">
                      Positioning: {resp.brand_positioning}
                    </span>
                  </div>
                  {resp.raw_citations.length > 0 && (
                    <div className="text-[10px] font-mono text-ink-600 space-y-0.5 pt-1 border-t border-line/60">
                      <span className="font-bold">Cited URLs:</span>
                      {resp.raw_citations.slice(0, 4).map((u, ui) => (
                        <div key={ui} className="truncate text-pine">{u}</div>
                      ))}
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

  return (
    <div className="space-y-6">
      {/* Coverage Bar & Branded/Non-Branded Split */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <Search className="w-4 h-4 text-pine" /> Prompt Intelligence &amp; Versioned Test Suite ({bundle.prompts.length})
            </h3>
            <p className="text-xs text-ink-500">
              Branded prompts measure brand comprehension; non-branded prompts measure unprompted discovery &amp; recommendation share.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setFilterScope('all')}
              className={`px-2.5 py-1 rounded border font-mono ${filterScope === 'all' ? 'bg-ink text-white border-ink' : 'bg-white border-line'}`}
            >
              All ({bundle.prompts.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterScope('non_branded')}
              className={`px-2.5 py-1 rounded border font-mono ${filterScope === 'non_branded' ? 'bg-pine text-white border-pine' : 'bg-white border-line'}`}
            >
              Non-Branded ({bundle.prompts.filter((p) => !p.is_branded).length})
            </button>
            <button
              type="button"
              onClick={() => setFilterScope('branded')}
              className={`px-2.5 py-1 rounded border font-mono ${filterScope === 'branded' ? 'bg-ink text-white border-ink' : 'bg-white border-line'}`}
            >
              Branded ({bundle.prompts.filter((p) => p.is_branded).length})
            </button>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2 py-1 rounded border border-line bg-white font-mono text-xs"
            >
              <option value="all">All 12 Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Add Custom Prompt with Quality Validator */}
        <div className="p-3 rounded border border-line bg-paper-50 space-y-2">
          <div className="flex flex-wrap gap-2">
            <input
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              placeholder="Add custom evaluation prompt (automatically checked for neutrality & duplicates)..."
              className="flex-1 min-w-[240px] px-3 py-1.5 border border-line rounded bg-white text-xs"
            />
            <select value={newCategory} onChange={(e) => setNewCategory(e.target.value)} className="px-2 py-1.5 border border-line rounded bg-white text-xs">
              <option value="category_discovery">Category Discovery</option>
              <option value="brand_discovery">Brand Discovery</option>
              <option value="product_discovery">Product Discovery</option>
              <option value="comparison">Comparison</option>
              <option value="recommendation">Recommendation</option>
              <option value="alternative_discovery">Alternative Discovery</option>
              <option value="problem_solving">Problem Solving</option>
              <option value="purchase_research">Purchase Research</option>
              <option value="trust_and_reputation">Trust &amp; Reputation</option>
              <option value="feature_discovery">Feature Discovery</option>
              <option value="local_discovery">Local Discovery</option>
              <option value="expert_information">Expert Information</option>
            </select>
            <label className="inline-flex items-center gap-1.5 text-xs font-mono px-2">
              <input type="checkbox" checked={newBranded} onChange={(e) => setNewBranded(e.target.checked)} />
              Branded
            </label>
            <button
              type="button"
              onClick={handleCreatePrompt}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-pine text-white text-xs font-semibold rounded"
            >
              <Plus className="w-3.5 h-3.5" /> Validate &amp; Add
            </button>
          </div>
          {validationMsg && <p className="text-[11px] font-mono text-ink-700">{validationMsg}</p>}
        </div>

        {/* Prompt Suite Table */}
        <div className="overflow-x-auto border border-line rounded">
          <table className="w-full text-xs text-left">
            <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
              <tr>
                <th className="p-2.5">Prompt</th>
                <th className="p-2.5">Category / Intent</th>
                <th className="p-2.5">Type</th>
                <th className="p-2.5">Market / Lang</th>
                <th className="p-2.5">Status</th>
                <th className="p-2.5">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filteredPrompts.map((p) => (
                <tr key={p.prompt_id} className="hover:bg-paper-50">
                  <td className="p-2.5">
                    <div className="font-medium text-ink">{p.question}</div>
                    <div className="text-[10px] text-ink-500">{p.testing_rationale}</div>
                  </td>
                  <td className="p-2.5 font-mono text-[10px]">
                    <div>{p.category}</div>
                    <div className="text-ink-500">{p.intent} · v{p.version}</div>
                  </td>
                  <td className="p-2.5">
                    <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-bold ${p.is_branded ? 'bg-paper-200 text-ink-700' : 'bg-pine/10 text-pine'}`}>
                      {p.is_branded ? 'Branded' : 'Non-Branded'}
                    </span>
                  </td>
                  <td className="p-2.5 font-mono text-[10px]">{p.market} / {p.language}</td>
                  <td className="p-2.5 font-mono text-[10px] uppercase">{p.approval_status}</td>
                  <td className="p-2.5">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleToggleApproval(p, 'approved')}
                        title="Approve"
                        className="p-1 text-good hover:bg-good/10 rounded"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleToggleApproval(p, 'excluded')}
                        title="Exclude"
                        className="p-1 text-bad hover:bg-bad/10 rounded"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
