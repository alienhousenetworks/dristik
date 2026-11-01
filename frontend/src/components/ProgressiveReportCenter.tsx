import React, { useState, useEffect } from 'react';
import {
  getProgressiveReportCatalog,
  ProgressiveReportCatalog,
  ProgressiveReportItem,
  getSubphasePdfUrl,
  getSubphaseJsonUrl,
  getPhasePdfUrl,
} from '../services/api';
import { FileText, Download, CheckCircle, Clock, AlertTriangle, ShieldCheck, Database, RefreshCw, ExternalLink } from 'lucide-react';

interface ProgressiveReportCenterProps {
  analysisId: string;
  isLive?: boolean;
}

const CANONICAL_PHASES = [
  { id: 'phase_01_ingestion', name: 'Phase 1 — Ingestion & Multi-Page Crawl', subphases: ['1.1', '1.2', '1.3', '1.4', '1.5', '1.6'] },
  { id: 'phase_02_business', name: 'Phase 2 — Business Understanding & Grounding', subphases: ['2.1', '2.2', '2.3', '2.4'] },
  { id: 'phase_03_pillars', name: 'Phase 3 — Four Strategic Pillars (SEO, GEO, AEO, CRO)', subphases: ['3.1', '3.2', '3.3', '3.4'] },
  { id: 'phase_04_copywriting', name: 'Phase 4 — Copywriting & Page Intelligence', subphases: ['4.1', '4.2', '4.3', '4.4', '4.5', '4.6'] },
  { id: 'phase_05_remediation', name: 'Phase 5 — Engineering Remediation & Roadmaps', subphases: ['5.1', '5.2', '5.3', '5.4', '5.5', '5.6'] },
  { id: 'phase_06_reporting', name: 'Phase 6 — Reporting, Verification & Sealing', subphases: ['6.1', '6.2', '6.3', '6.4', '6.5', '6.6'] },
];

export const ProgressiveReportCenter: React.FC<ProgressiveReportCenterProps> = ({ analysisId, isLive }) => {
  const [catalog, setCatalog] = useState<ProgressiveReportCatalog | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [selectedJsonSubphase, setSelectedJsonSubphase] = useState<{ phaseId: string; subphaseId: string } | null>(null);
  const [jsonData, setJsonData] = useState<string | null>(null);

  const fetchCatalog = async () => {
    try {
      const data = await getProgressiveReportCatalog(analysisId);
      setCatalog(data);
    } catch (e) {
      // Catalog may still be initializing
    }
  };

  useEffect(() => {
    fetchCatalog();
    if (isLive) {
      const interval = setInterval(fetchCatalog, 4000);
      return () => clearInterval(interval);
    }
  }, [analysisId, isLive]);

  const viewJson = async (phaseId: string, subphaseId: string) => {
    setSelectedJsonSubphase({ phaseId, subphaseId });
    setJsonData('Loading raw JSON contract...');
    try {
      const url = getSubphaseJsonUrl(analysisId, phaseId, subphaseId);
      const res = await fetch(url);
      const data = await res.json();
      setJsonData(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setJsonData(`Error loading JSON: ${err.message}`);
    }
  };

  const getSubphaseItem = (phaseId: string, subId: string): ProgressiveReportItem | undefined => {
    if (!catalog) return undefined;
    return catalog.subphases.find((s) => s.phase_id === phaseId && s.subphase_id === subId);
  };

  const getPhaseItem = (phaseId: string): ProgressiveReportItem | undefined => {
    if (!catalog) return undefined;
    return catalog.phases.find((p) => p.phase_id === phaseId);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5 mb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-teal-400 uppercase tracking-widest">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            Progressive Evidence Reporting System
          </div>
          <h2 className="text-xl font-extrabold text-white mt-1">Analysis Report Center</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Run ID: <code className="text-sky-300 font-mono bg-slate-800/80 px-1.5 py-0.5 rounded">{analysisId}</code>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right text-xs">
            <span className="text-slate-400">PDFs Ready: </span>
            <strong className="text-emerald-400 font-bold">{catalog?.ready_subphase_pdfs || 0}</strong>
            <span className="text-slate-500"> / {catalog?.total_subphase_reports || 0}</span>
          </div>
          <button
            onClick={() => {
              setLoading(true);
              fetchCatalog().finally(() => setLoading(false));
            }}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-teal-400' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Phase Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-3 mb-6 scrollbar-thin">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition ${
            activeTab === 'all' ? 'bg-teal-600 text-white font-bold' : 'bg-slate-800/70 text-slate-400 hover:text-slate-200'
          }`}
        >
          All 6 Phases
        </button>
        {CANONICAL_PHASES.map((p, idx) => {
          const phItem = getPhaseItem(p.id);
          const isComplete = phItem && phItem.status === 'COMPLETED';
          return (
            <button
              key={p.id}
              onClick={() => setActiveTab(p.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition ${
                activeTab === p.id ? 'bg-teal-600 text-white font-bold' : 'bg-slate-800/70 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>Phase {idx + 1}</span>
              {isComplete && <CheckCircle className="w-3 h-3 text-emerald-400 inline" />}
            </button>
          );
        })}
      </div>

      {/* Phases Grid */}
      <div className="space-y-6">
        {CANONICAL_PHASES.filter((p) => activeTab === 'all' || activeTab === p.id).map((phase) => {
          const phaseEntry = getPhaseItem(phase.id);
          const isPhaseDone = phaseEntry && phaseEntry.status === 'COMPLETED';

          return (
            <div key={phase.id} className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5">
              {/* Phase Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/60 gap-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${isPhaseDone ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">{phase.name}</h3>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400">
                      <span>Status:</span>
                      <span className={`font-semibold ${isPhaseDone ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {phaseEntry ? phaseEntry.status : 'IN PROGRESS / PENDING'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Phase Consolidated Action */}
                <div>
                  {isPhaseDone ? (
                    <a
                      href={getPhasePdfUrl(analysisId, phase.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold bg-teal-600 hover:bg-teal-500 text-white rounded-lg transition shadow-sm"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Consolidated PDF
                    </a>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-500 bg-slate-900 border border-slate-800 rounded-lg cursor-not-allowed">
                      <Clock className="w-3.5 h-3.5 text-slate-600" />
                      Consolidated PDF Awaiting Completion
                    </span>
                  )}
                </div>
              </div>

              {/* Sub-Phases List */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
                {phase.subphases.map((subId) => {
                  const subItem = getSubphaseItem(phase.id, subId);
                  const isReady = subItem && (subItem.pdf_ready || subItem.status === 'COMPLETED');

                  return (
                    <div
                      key={subId}
                      className="bg-slate-900/90 border border-slate-800 rounded-lg p-3.5 flex flex-col justify-between hover:border-slate-700 transition"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-mono font-bold text-sky-400 bg-sky-950/60 border border-sky-800/50 px-1.5 py-0.5 rounded">
                            {subId}
                          </span>
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                              isReady
                                ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {isReady ? 'PDF READY' : 'PENDING'}
                          </span>
                        </div>
                        <h4 className="text-xs font-semibold text-slate-200 line-clamp-1">
                          {subItem?.title || `Sub-Phase ${subId}`}
                        </h4>
                        {subItem?.content_hash && (
                          <div className="text-[10px] font-mono text-slate-500 mt-1 truncate">
                            SHA: {subItem.content_hash.slice(0, 10)}...
                          </div>
                        )}
                      </div>

                      {/* Sub-phase Actions */}
                      <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-slate-800/70">
                        {isReady ? (
                          <>
                            <a
                              href={getSubphasePdfUrl(analysisId, phase.id, subId)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex-1 flex items-center justify-center gap-1 text-[11px] font-semibold text-teal-300 bg-teal-950/60 hover:bg-teal-900/60 border border-teal-800/50 py-1 rounded transition"
                            >
                              <Download className="w-3 h-3" />
                              PDF
                            </a>
                            <button
                              onClick={() => viewJson(phase.id, subId)}
                              className="px-2 py-1 text-[11px] font-mono text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded transition"
                              title="Inspect JSON Contract"
                            >
                              JSON
                            </button>
                          </>
                        ) : (
                          <span className="text-[11px] text-slate-500 italic py-1">Executing in pipeline...</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* JSON Viewer Modal */}
      {selectedJsonSubphase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[80vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div className="flex items-center gap-2 text-xs font-bold text-teal-400">
                <Database className="w-4 h-4" />
                Raw Sub-Phase Contract JSON: {selectedJsonSubphase.subphaseId}
              </div>
              <button
                onClick={() => setSelectedJsonSubphase(null)}
                className="text-slate-400 hover:text-white text-sm font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-auto font-mono text-xs text-sky-300 bg-slate-950 flex-1">
              <pre>{jsonData}</pre>
            </div>
            <div className="p-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedJsonSubphase(null)}
                className="px-4 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
