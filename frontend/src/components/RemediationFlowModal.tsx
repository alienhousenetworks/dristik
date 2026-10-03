import React, { useState, useEffect } from 'react';
import { RemediationPatch, Integration, VerificationResult, PatchRiskLevel } from '../types';

interface RemediationFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysisId: string;
  websiteUrl: string;
}

export const RemediationFlowModal: React.FC<RemediationFlowModalProps> = ({
  isOpen,
  onClose,
  analysisId,
  websiteUrl,
}) => {
  const [patches, setPatches] = useState<RemediationPatch[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selectedIntegrationId, setSelectedIntegrationId] = useState<string>('');
  const [activeRiskFilter, setActiveRiskFilter] = useState<PatchRiskLevel | 'ALL'>('ALL');
  const [selectedPatch, setSelectedPatch] = useState<RemediationPatch | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

  const fetchPatchesAndIntegrations = async () => {
    setLoading(true);
    try {
      const [pRes, iRes] = await Promise.all([
        fetch(`/api/v1/remediation/patches/${analysisId || 'latest'}`),
        fetch('/api/v1/connectors'),
      ]);

      if (pRes.ok) {
        const pData = await pRes.json();
        setPatches(pData.patches || []);
        if (pData.patches && pData.patches.length > 0) {
          setSelectedPatch(pData.patches[0]);
        }
      }

      if (iRes.ok) {
        const iData = await iRes.json();
        setIntegrations(iData);
        if (iData.length > 0) {
          setSelectedIntegrationId(iData[0].integration_id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPatchesAndIntegrations();
    }
  }, [isOpen, analysisId]);

  const handleApprove = async (patchId: string) => {
    setActionLoading(patchId);
    setActionMessage(null);
    try {
      const res = await fetch(`/api/v1/remediation/patches/${patchId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approver: 'analyst@dristik.ai' }),
      });
      if (res.ok) {
        const updated = await res.json();
        setPatches((prev) => prev.map((p) => (p.patch_id === patchId ? updated : p)));
        if (selectedPatch?.patch_id === patchId) setSelectedPatch(updated);
        setActionMessage(`✓ Approved patch ${patchId}`);
      }
    } catch (e: any) {
      setActionMessage(`Error: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeploy = async (patchId: string) => {
    if (!selectedIntegrationId) {
      alert('Please connect or select a platform integration first.');
      return;
    }
    setActionLoading(patchId);
    setActionMessage(null);
    try {
      const res = await fetch(`/api/v1/remediation/patches/${patchId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ integration_id: selectedIntegrationId }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setActionMessage(`✓ Deployed: ${data.message}`);
        // Automatically refresh patches
        await fetchPatchesAndIntegrations();
      } else {
        setActionMessage(`Deployment failed: ${data.message || data.detail}`);
      }
    } catch (e: any) {
      setActionMessage(`Deployment error: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleVerify = async (patchId: string) => {
    setActionLoading(`verify_${patchId}`);
    setVerificationResult(null);
    try {
      const res = await fetch(`/api/v1/remediation/patches/${patchId}/verify`, {
        method: 'POST',
      });
      if (res.ok) {
        const vData: VerificationResult = await res.json();
        setVerificationResult(vData);
        setActionMessage(`✓ Resolution Verified! Score gain: +${vData.score_delta} points`);
        // Refresh local state
        setPatches((prev) =>
          prev.map((p) =>
            p.patch_id === patchId
              ? { ...p, verification_status: 'verified', citation_score_delta: vData.score_delta }
              : p
          )
        );
      }
    } catch (e: any) {
      setActionMessage(`Verification failed: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const filteredPatches =
    activeRiskFilter === 'ALL'
      ? patches
      : patches.filter((p) => p.risk_level === activeRiskFilter);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 scrim">
      <div className="relative w-full max-w-6xl sheet border border-line rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-line bg-paper-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-paper-200 border border-line flex items-center justify-center text-ink">
              <span className="font-mono font-bold text-sm text-ink-700"></span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-sans text-ink tracking-tight">
                  Universal Remediation Engine
                </h2>
                <span className="text-[11px] px-2 py-0.5 rounded bg-paper-200 border border-line text-ink-700 font-mono">
                  Detect → Explain → Fix → Deploy → Verify
                </span>
              </div>
              <p className="text-xs text-ink-500">
                Target: <span className="text-ink font-mono font-medium">{websiteUrl || 'Selected Site'}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Platform Selector */}
            <div className="flex items-center gap-2 bg-paper-50 border border-line px-3 py-1.5 rounded-lg">
              <span className="text-xs text-ink-500">Deploy via:</span>
              <select
                value={selectedIntegrationId}
                onChange={(e) => setSelectedIntegrationId(e.target.value)}
                className="bg-transparent text-xs text-ink font-medium focus:outline-none cursor-pointer"
              >
                {integrations.map((i) => (
                  <option key={i.integration_id} value={i.integration_id} className="bg-sheet text-ink">
                    {i.name} ({i.provider})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={onClose}
              className="text-ink-500 hover:text-ink p-1.5 rounded-lg border border-line bg-paper-50 hover:bg-paper-100 transition"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Workflow Action Bar */}
        <div className="px-6 py-2.5 bg-paper-50 border-b border-line flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-ink-500 font-medium">Risk Filter:</span>
            {(['ALL', 'SAFE_AUTO', 'HUMAN_APPROVAL', 'DEVELOPER_REQUIRED'] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setActiveRiskFilter(lvl)}
                className={`px-3 py-1 rounded text-xs transition font-mono border ${
                  activeRiskFilter === lvl
                    ? 'sheet text-ink border-ink font-semibold shadow-xs'
                    : 'bg-paper-100 text-ink-700 border-line hover:border-ink-500'
                }`}
              >
                {lvl === 'ALL'
                  ? `All (${patches.length})`
                  : lvl === 'SAFE_AUTO'
                  ? `L1: Safe Auto (${patches.filter((p) => p.risk_level === 'SAFE_AUTO').length})`
                  : lvl === 'HUMAN_APPROVAL'
                  ? `L2: Human Review (${patches.filter((p) => p.risk_level === 'HUMAN_APPROVAL').length})`
                  : `L3: Dev PR (${patches.filter((p) => p.risk_level === 'DEVELOPER_REQUIRED').length})`}
              </button>
            ))}
          </div>

          {actionMessage && (
            <div className="font-mono text-xs text-good font-semibold">
              {actionMessage}
            </div>
          )}
        </div>

        {/* Main 2-Pane Content */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-12">
          {/* Left Pane: Patch List */}
          <div className="md:col-span-5 border-r border-line overflow-y-auto p-4 space-y-2.5 bg-paper-50">
            {loading ? (
              <div className="p-8 text-center text-ink-500 text-xs">Generating universal patches...</div>
            ) : filteredPatches.length === 0 ? (
              <div className="p-8 text-center text-ink-500 text-xs">No patches found for this filter.</div>
            ) : (
              filteredPatches.map((patch) => {
                const isSelected = selectedPatch?.patch_id === patch.patch_id;
                const isApplied = patch.approval_status === 'APPLIED';
                const isVerified = patch.verification_status === 'verified';

                return (
                  <div
                    key={patch.patch_id}
                    onClick={() => setSelectedPatch(patch)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition space-y-2 ${
                      isSelected
                        ? 'sheet border-ink shadow-xs ring-1 ring-ink'
                        : 'bg-paper-100 border-line hover:border-ink-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200 text-ink-700 font-semibold border border-line">
                        {patch.patch_id}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {patch.risk_level === 'SAFE_AUTO' && (
                          <span className="text-[10px] px-2 py-0.5 rounded-md bg-good/10 border border-good/30 text-good font-mono">
                            Safe Auto
                          </span>
                        )}
                        {patch.risk_level === 'HUMAN_APPROVAL' && (
                          <span className="text-[10px] px-2 py-0.5 rounded-md bg-warn/10 border border-warn/30 text-warn font-mono">
                            Review Required
                          </span>
                        )}
                        {patch.risk_level === 'DEVELOPER_REQUIRED' && (
                          <span className="text-[10px] px-2 py-0.5 rounded-md bg-paper-200 border border-line text-ink-700 font-mono">
                            Developer PR
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-sm font-semibold text-ink leading-tight">
                      {patch.title}
                    </div>

                    <div className="text-xs text-ink-500 line-clamp-1">
                      Target: <code className="text-ink-700 font-mono">{patch.target_file}</code>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-line text-[11px]">
                      <span className="text-ink-500">
                        Status:{' '}
                        <strong
                          className={
                            isVerified
                              ? 'text-good'
                              : isApplied
                              ? 'text-ink-700'
                              : patch.approval_status === 'APPROVED'
                              ? 'text-good'
                              : 'text-warn'
                          }
                        >
                          {isVerified ? 'VERIFIED ✓' : patch.approval_status}
                        </strong>
                      </span>
                      {patch.citation_score_delta && (
                        <span className="text-good font-bold font-mono">
                          +{patch.citation_score_delta} Score Gain
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Right Pane: Selected Patch Detail, Before/After Diff, Action Buttons */}
          <div className="md:col-span-7 flex flex-col h-full overflow-y-auto p-6 sheet space-y-5">
            {selectedPatch ? (
              <>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-ink-700 font-semibold">
                      {selectedPatch.patch_id} • Finding Ref: {selectedPatch.finding_id}
                    </span>
                    <span className="text-xs text-ink-500 font-mono">
                      Confidence: {(selectedPatch.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <h3 className="text-base font-sans text-ink">{selectedPatch.title}</h3>
                  <p className="text-xs text-ink-700 leading-relaxed bg-paper-50 p-3 rounded-lg border border-line">
                    {selectedPatch.explanation}
                  </p>
                </div>

                {/* Diff Viewer */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-ink-500 font-mono">
                    <span>BEFORE → AFTER DIFF</span>
                    <span>Target: {selectedPatch.target_file}</span>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    {selectedPatch.before_snippet && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-mono text-bad font-semibold block">
                          - BEFORE (Current State)
                        </span>
                        <pre className="p-3 rounded-lg bg-bad/5 border border-bad/20 text-bad text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                          {selectedPatch.before_snippet}
                        </pre>
                      </div>
                    )}

                    <div className="space-y-1">
                      <span className="text-[11px] font-mono text-good font-semibold block">
                        + AFTER (Dristik Remediation Patch)
                      </span>
                      <pre className="p-3 rounded-lg bg-good/5 border border-good/20 text-good text-xs font-mono overflow-x-auto whitespace-pre-wrap max-h-56">
                        {selectedPatch.after_snippet}
                      </pre>
                    </div>
                  </div>
                </div>

                {/* Verification Banner if Verified */}
                {verificationResult && verificationResult.patch_id === selectedPatch.patch_id && (
                  <div className="p-4 rounded-lg bg-good/10 border border-good/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-good flex items-center gap-1.5">
                        <span>✓ Remediation Live & Verified</span>
                      </span>
                      <span className="text-xs font-mono text-good font-bold px-2 py-0.5 rounded bg-good/20">
                        AI Citation Score: {verificationResult.before_score} → {verificationResult.after_score} (+{verificationResult.score_delta})
                      </span>
                    </div>
                    <p className="text-xs text-ink-700">{verificationResult.details}</p>
                  </div>
                )}

                {/* Action Controls */}
                <div className="pt-4 border-t border-line flex flex-wrap items-center justify-between gap-3 mt-auto">
                  <div className="flex items-center gap-2">
                    {selectedPatch.approval_status === 'PENDING' && (
                      <button
                        onClick={() => handleApprove(selectedPatch.patch_id)}
                        disabled={actionLoading === selectedPatch.patch_id}
                        className="px-4 py-2 bg-good hover:opacity-90 text-white text-xs font-semibold rounded transition"
                      >
                        {actionLoading === selectedPatch.patch_id ? 'Approving...' : '✓ Approve Patch'}
                      </button>
                    )}

                    <button
                      onClick={() => handleDeploy(selectedPatch.patch_id)}
                      disabled={actionLoading === selectedPatch.patch_id}
                      className="px-4 py-2 btn-primary text-white text-xs font-semibold rounded transition"
                    >
                      {actionLoading === selectedPatch.patch_id
                        ? 'Deploying...'
                        : selectedPatch.risk_level === 'DEVELOPER_REQUIRED'
                        ? '🚀 Create GitHub Pull Request'
                        : ' Deploy to Connected Site'}
                    </button>
                  </div>

                  <button
                    onClick={() => handleVerify(selectedPatch.patch_id)}
                    disabled={actionLoading === `verify_${selectedPatch.patch_id}`}
                    className="px-4 py-2 bg-paper-100 hover:bg-paper-200 border border-line text-ink text-xs font-semibold rounded transition flex items-center gap-1.5"
                  >
                    <span>🔍</span>
                    <span>
                      {actionLoading === `verify_${selectedPatch.patch_id}`
                        ? 'Re-Crawling & Verifying...'
                        : 'Verify Fix Resolution'}
                    </span>
                  </button>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-ink-500 text-xs">
                Select a patch on the left to inspect diff and execute remediation.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
