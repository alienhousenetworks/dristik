import React, { useEffect, useState } from 'react';
import { CodePatch, ExecutiveReport, RemediationPatch } from '../types';
import { fetchPatchPackFiles } from '../services/api';
import { Card, Section } from './ui';
import { FileCode2, Copy, Check, Download, Layers, CheckCircle2, ShieldCheck, Package } from 'lucide-react';

interface DevPatchPackViewProps {
  report: ExecutiveReport;
  analysisId?: string;
}

export function DevPatchPackView({ report, analysisId }: DevPatchPackViewProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [packFiles, setPackFiles] = useState<Record<string, string>>({});
  const [activeArtifact, setActiveArtifact] = useState<string>('patches/unified.diff');

  useEffect(() => {
    if (!analysisId) return;
    fetchPatchPackFiles(analysisId)
      .then((res) => {
        if (res?.files) {
          setPackFiles(res.files);
          if (res.files['patches/unified.diff']) {
            setActiveArtifact('patches/unified.diff');
          } else if (res.file_names?.length) {
            setActiveArtifact(res.file_names[0]);
          }
        }
      })
      .catch(() => {
        /* fallback to inline patches */
      });
  }, [analysisId]);

  let verificationStatus: string | null = null;
  try {
    if (packFiles['VERIFICATION_REPORT.json']) {
      verificationStatus = JSON.parse(packFiles['VERIFICATION_REPORT.json'])?.overall_status || null;
    }
  } catch {
    verificationStatus = null;
  }

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
          <span className="text-[10px] font-mono uppercase tracking-[0.04em] text-ink-700 font-bold block">
            Engineering & Remediation
          </span>
          <h2 className="font-sans text-3xl text-ink font-semibold">Developer Patch Pack</h2>
          <p className="text-xs text-ink-500 mt-1">
            Engineered code diffs ready for review and deployment to resolve identified SEO, Schema, and CRO issues.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {verificationStatus && (
            <span
              className={`inline-flex items-center gap-1 text-[11px] font-mono px-2.5 py-1 rounded border ${
                verificationStatus === 'VERIFIED_SYNTAX_PASS'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              {verificationStatus}
            </span>
          )}
          {analysisId && (
            <a
              href={`/api/v1/analyses/${analysisId}/patch-pack/zip`}
              className="btn-primary text-xs px-3 py-2 flex items-center gap-1.5"
            >
              <Package className="w-4 h-4" />
              <span>Download Enterprise ZIP</span>
            </a>
          )}
          <button
            type="button"
            onClick={handleDownloadPatchFile}
            className="text-xs px-3 py-2 rounded border border-line bg-paper-100 hover:bg-paper-200 flex items-center gap-1.5"
          >
            <Download className="w-4 h-4" />
            <span>Download .patch</span>
          </button>
        </div>
      </div>

      {/* Enterprise Remediation Bundle Workbench */}
      {Object.keys(packFiles).length > 0 && (
        <Card className="p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2">
            <div className="text-xs font-mono font-bold text-ink uppercase tracking-wider flex items-center gap-1.5">
              <FileCode2 className="w-4 h-4 text-teal-700" />
              Enterprise Remediation Artifacts ({Object.keys(packFiles).length})
            </div>
            <button
              type="button"
              onClick={() => handleCopy(`artifact_${activeArtifact}`, packFiles[activeArtifact] || '')}
              className="text-xs px-2.5 py-1 rounded border border-line hover:bg-paper-100 flex items-center gap-1"
            >
              {copiedId === `artifact_${activeArtifact}` ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedId === `artifact_${activeArtifact}` ? 'Copied' : 'Copy Artifact'}</span>
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {Object.keys(packFiles).map((fname) => (
              <button
                key={fname}
                type="button"
                onClick={() => setActiveArtifact(fname)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                  activeArtifact === fname
                    ? 'bg-teal-700 text-white font-bold'
                    : 'bg-paper-100 text-ink-600 hover:bg-paper-200 border border-line'
                }`}
              >
                {fname}
              </button>
            ))}
          </div>
          <pre className="p-3 rounded bg-slate-950 text-slate-100 text-xs font-mono overflow-x-auto max-h-80 leading-relaxed">
            {(packFiles[activeArtifact] || '').split('\n').map((line, i) => {
              const cls = line.startsWith('+') && !line.startsWith('+++')
                ? 'text-emerald-400'
                : line.startsWith('-') && !line.startsWith('---')
                ? 'text-rose-400'
                : line.startsWith('@@')
                ? 'text-cyan-300'
                : 'text-slate-200';
              return <div key={i} className={cls}>{line || ' '}</div>;
            })}
          </pre>
        </Card>
      )}

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
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-bold">
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
                    <pre className="text-ink-700 text-[11px] whitespace-pre-wrap">{p.before_snippet}</pre>
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
