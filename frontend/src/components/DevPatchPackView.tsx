import React, { useState } from 'react';
import { CodePatch, ExecutiveReport, RemediationPatch } from '../types';
import { Card, Section } from './ui';
import { FileCode2, Copy, Check, Download, Layers, CheckCircle2 } from 'lucide-react';

interface DevPatchPackViewProps {
  report: ExecutiveReport;
  analysisId?: string;
}

export function DevPatchPackView({ report, analysisId }: DevPatchPackViewProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  const patches: CodePatch[] = report.code_patches || [];
  const remediationPatches: RemediationPatch[] = report.remediation_patches || [];

  const allPatches = [
    ...patches,
    ...remediationPatches.map((rp) => ({
      patch_id: rp.patch_id,
      title: rp.title,
      category: rp.category as any,
      target_file: rp.target_file,
      before_snippet: rp.before_snippet,
      after_snippet: rp.after_snippet,
      explanation: rp.explanation,
      release_status: rp.approval_status || 'READY_TO_DEPLOY',
    })),
  ];

  const categories = ['ALL', ...Array.from(new Set(allPatches.map((p) => p.category)))];

  const filteredPatches = selectedCategory === 'ALL'
    ? allPatches
    : allPatches.filter((p) => p.category === selectedCategory);

  const handleCopy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      /* fallback */
    }
  };

  const handleDownloadPatchFile = () => {
    const patchContent = allPatches.map((p) => (
      `# ================================================================\n` +
      `# Patch: ${p.patch_id} - ${p.title}\n` +
      `# Target File: ${p.target_file}\n` +
      `# Category: ${p.category}\n` +
      `# Explanation: ${p.explanation}\n` +
      `# ================================================================\n` +
      (p.before_snippet ? `--- BEFORE\n${p.before_snippet}\n` : '') +
      `+++ AFTER\n${p.after_snippet}\n\n`
    )).join('\n');

    const blob = new Blob([patchContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dristik-patch-pack-${report.domain || 'site'}.patch`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-line pb-4">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-pine font-bold block">
            Engineering & Remediation
          </span>
          <h2 className="font-serif text-3xl text-ink font-semibold">Developer Patch Pack</h2>
          <p className="text-xs text-ink-500 mt-1">
            Engineered code diffs ready for review and deployment to resolve identified SEO, Schema, and CRO issues.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleDownloadPatchFile}
            className="btn-primary text-xs px-3 py-2 flex items-center gap-1.5"
          >
            <Download className="w-4 h-4" />
            <span>Download .patch Pack</span>
          </button>
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
              selectedCategory === cat
                ? 'bg-pine text-paper-100 font-bold'
                : 'bg-paper-100 text-ink-600 hover:bg-paper-200 border border-line'
            }`}
          >
            {cat}
          </button>
        ))}
        <span className="text-xs text-ink-400 font-mono ml-auto">
          {filteredPatches.length} patches available
        </span>
      </div>

      {/* Patches List */}
      {filteredPatches.length > 0 ? (
        <div className="space-y-6">
          {filteredPatches.map((p) => (
            <Card key={p.patch_id} className="p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-pine/10 text-pine font-bold">
                      {p.category}
                    </span>
                    <span className="text-xs font-mono text-ink-400">{p.patch_id}</span>
                  </div>
                  <h3 className="text-base font-bold text-ink">{p.title}</h3>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-good/10 text-good font-semibold">
                    {p.release_status || 'READY_TO_DEPLOY'}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopy(p.patch_id, p.after_snippet)}
                    className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1"
                  >
                    {copiedId === p.patch_id ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-good" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Code</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Target File & Explanation */}
              <div className="text-xs space-y-1">
                <p className="font-mono text-ink-500">
                  <strong className="text-ink-700">Target File: </strong> {p.target_file}
                </p>
                <p className="text-ink-600 leading-relaxed">{p.explanation}</p>
              </div>

              {/* Code Diffs */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 text-xs font-mono">
                {p.before_snippet && (
                  <div className="p-3 rounded bg-bad/5 border border-bad/20 space-y-1 overflow-x-auto">
                    <span className="text-[10px] font-bold text-bad uppercase block">Existing State (Before)</span>
                    <pre className="text-ink-800 text-[11px] whitespace-pre-wrap">{p.before_snippet}</pre>
                  </div>
                )}
                <div className={`p-3 rounded bg-good/5 border border-good/20 space-y-1 overflow-x-auto ${
                  !p.before_snippet ? 'lg:col-span-2' : ''
                }`}>
                  <span className="text-[10px] font-bold text-good uppercase block">Proposed Patch (After)</span>
                  <pre className="text-ink-900 text-[11px] font-semibold whitespace-pre-wrap">{p.after_snippet}</pre>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center space-y-2">
          <FileCode2 className="w-8 h-8 text-ink-300 mx-auto" />
          <h4 className="text-sm font-semibold text-ink">No Code Patches for this Category</h4>
          <p className="text-xs text-ink-500">All audit recommendations have clean release statuses.</p>
        </Card>
      )}
    </div>
  );
}
