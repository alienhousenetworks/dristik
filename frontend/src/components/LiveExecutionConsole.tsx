import React, { useState, useEffect, useRef } from 'react';
import { AnalysisRun, PipelineGraphState, GraphNode, ActivityEvent } from '../types';
import { getExecutionGraph, pauseAnalysis, resumeAnalysis, runGraphNode } from '../services/api';
import { formatMs } from '../lib/format';

interface LiveExecutionConsoleProps {
  run: AnalysisRun;
  onRefreshRun?: () => void;
}

export function LiveExecutionConsole({ run, onRefreshRun }: LiveExecutionConsoleProps) {
  const [graphState, setGraphState] = useState<PipelineGraphState | null>(run.graph || null);
  const [activeTab, setActiveTab] = useState<'terminal' | 'dag'>('terminal');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSectionFilter, setSelectedSectionFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [runningNodeId, setRunningNodeId] = useState<string | null>(null);
  const [nodeActionError, setNodeActionError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isPausing, setIsPausing] = useState(false);
  const [isResuming, setIsResuming] = useState(false);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Poll graph state if missing or active
  useEffect(() => {
    let isMounted = true;
    const fetchGraph = async () => {
      try {
        const data = await getExecutionGraph(run.analysis_id);
        if (isMounted) {
          setGraphState(data);
        }
      } catch {
        /* ignore polling error */
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 2500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [run.analysis_id]);

  // Sync if run prop changes with embedded graph
  useEffect(() => {
    if (run.graph) {
      setGraphState(run.graph);
    }
  }, [run.graph]);

  // Auto-scroll terminal log
  useEffect(() => {
    if (autoScroll && activeTab === 'terminal' && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [graphState?.activity_events, autoScroll, activeTab]);

  const handlePause = async () => {
    setIsPausing(true);
    setNodeActionError(null);
    try {
      await pauseAnalysis(run.analysis_id);
      if (onRefreshRun) onRefreshRun();
    } catch (err: any) {
      setNodeActionError(err.message || 'Failed to pause audit');
    } finally {
      setIsPausing(false);
    }
  };

  const handleResume = async () => {
    setIsResuming(true);
    setNodeActionError(null);
    try {
      await resumeAnalysis(run.analysis_id);
      if (onRefreshRun) onRefreshRun();
    } catch (err: any) {
      setNodeActionError(err.message || 'Failed to resume audit');
    } finally {
      setIsResuming(false);
    }
  };

  const handleRunNode = async (nodeId: string) => {
    setRunningNodeId(nodeId);
    setNodeActionError(null);
    try {
      await runGraphNode(run.analysis_id, nodeId);
      const updated = await getExecutionGraph(run.analysis_id);
      setGraphState(updated);
      if (onRefreshRun) onRefreshRun();
    } catch (err: any) {
      setNodeActionError(err.message || `Failed to run step ${nodeId}`);
    } finally {
      setRunningNodeId(null);
    }
  };

  const isPaused = run.status === 'paused' || graphState?.is_paused;
  const isFailed = run.status === 'failed';
  const isCompleted = run.status === 'completed';
  const isRunning = !isPaused && !isFailed && !isCompleted;

  const totalCost = run.telemetry?.estimated_cost_usd ?? 0;
  const totalTokens = run.telemetry?.total_tokens ?? 0;

  // Filter activities
  const events = graphState?.activity_events || [];
  const filteredEvents = events.filter((ev) => {
    const matchesSection = selectedSectionFilter === 'all' || ev.section_id === selectedSectionFilter;
    const matchesSearch =
      !searchQuery ||
      ev.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.agent_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSection && matchesSearch;
  });

  return (
    <div className="rounded-xl border border-line bg-card shadow-sm overflow-hidden text-ink">
      {/* 1. TOP COMMAND BAR */}
      <div className="p-4 sm:p-5 border-b border-line bg-sand-50/60 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-xs uppercase tracking-wider text-ink-500 font-semibold">
              Mission Orchestrator
            </span>
            {isRunning && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-pine/10 text-pine border border-pine/20">
                <span className="w-2 h-2 rounded-full bg-pine animate-ping" />
                Live Executing
              </span>
            )}
            {isPaused && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600 border border-amber-500/20">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                Audit Paused
              </span>
            )}
            {isFailed && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-bad/10 text-bad border border-bad/20">
                <span className="w-2 h-2 rounded-full bg-bad" />
                Halted on Error
              </span>
            )}
            {isCompleted && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Mission Complete
              </span>
            )}
          </div>
          <h3 className="text-base sm:text-lg font-serif font-semibold text-ink mt-1 truncate max-w-md sm:max-w-xl">
            {run.website_url.replace(/^https?:\/\//, '')}
          </h3>
          <p className="text-xs text-ink-600 font-mono mt-0.5">
            {run.current_step || 'Processing workflow steps...'}
          </p>
        </div>

        {/* Action Controls & Metrics */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-xs font-mono text-ink-500">
              AI Cost: <span className="font-bold text-pine font-sans">${totalCost.toFixed(4)}</span> •{' '}
              <span className="font-bold text-ink-700">{totalTokens.toLocaleString()} tokens</span>
            </div>
            <div className="text-xs font-mono text-ink-400 mt-0.5">
              Nodes: {graphState?.completed_nodes ?? 0} / {graphState?.total_nodes ?? 18} Completed
            </div>
          </div>

          {/* Pause / Resume Buttons */}
          {isRunning && (
            <button
              type="button"
              onClick={handlePause}
              disabled={isPausing}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-sand-200/80 hover:bg-sand-300 text-ink border border-line flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs"
            >
              <svg className="w-3.5 h-3.5 text-ink-600" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16" rx="1" />
                <rect x="14" y="4" width="4" height="16" rx="1" />
              </svg>
              <span>{isPausing ? 'Pausing...' : 'Stop / Pause'}</span>
            </button>
          )}

          {(isPaused || isFailed) && (
            <button
              type="button"
              onClick={handleResume}
              disabled={isResuming}
              className="px-4 py-1.5 rounded-lg text-xs font-medium bg-pine hover:bg-pine/90 text-sand-50 flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs"
            >
              <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              <span>{isResuming ? 'Resuming...' : 'Resume Audit'}</span>
            </button>
          )}

          {/* View Tab Switcher */}
          <div className="inline-flex rounded-lg p-0.5 bg-sand-200/60 border border-line">
            <button
              type="button"
              onClick={() => setActiveTab('terminal')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
                activeTab === 'terminal'
                  ? 'bg-card text-ink shadow-xs font-semibold'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              Terminal Telemetry
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('dag')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
                activeTab === 'dag'
                  ? 'bg-card text-ink shadow-xs font-semibold'
                  : 'text-ink-600 hover:text-ink'
              }`}
            >
              Sections & DAG
            </button>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-1.5 bg-sand-200/80 w-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            isFailed ? 'bg-bad' : isPaused ? 'bg-amber-500' : 'bg-pine'
          }`}
          style={{ width: `${Math.max(4, run.progress_percentage || graphState?.progress_percentage || 5)}%` }}
        />
      </div>

      {nodeActionError && (
        <div className="px-5 py-2.5 bg-bad/10 border-b border-bad/20 text-xs text-bad flex items-center justify-between">
          <span>{nodeActionError}</span>
          <button
            type="button"
            onClick={() => setNodeActionError(null)}
            className="text-bad hover:underline font-bold text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. TAB CONTENT */}
      {activeTab === 'terminal' ? (
        /* TERMINAL-STYLE LIVE ACTIVITY STREAM */
        <div className="bg-[#0b0f17] text-slate-200 p-4 font-mono text-xs select-text">
          {/* Terminal Console Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-3 border-b border-slate-800 text-[11px] text-slate-400">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
              </div>
              <span className="font-semibold text-slate-300 ml-1">dristik-telemetry-engine</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400">Semantic Activity Stream (Not Raw Shell Dumps)</span>
            </div>

            <div className="flex items-center gap-2.5">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter logs..."
                className="bg-slate-900 border border-slate-700/80 rounded px-2 py-0.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-slate-500"
              />

              <select
                value={selectedSectionFilter}
                onChange={(e) => setSelectedSectionFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700/80 rounded px-2 py-0.5 text-xs text-slate-300 focus:outline-hidden"
              >
                <option value="all">All Sections</option>
                {graphState?.sections.map((s) => (
                  <option key={s.section_id} value={s.section_id}>
                    {s.title}
                  </option>
                ))}
              </select>

              <label className="flex items-center gap-1 text-[11px] text-slate-400 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="rounded text-pine"
                />
                <span>Auto-scroll</span>
              </label>
            </div>
          </div>

          {/* Stream Log Entries */}
          <div className="h-[380px] overflow-y-auto space-y-1.5 pr-2 scrollbar-thin">
            {filteredEvents.length === 0 ? (
              <div className="text-slate-500 italic py-8 text-center">
                Waiting for pipeline execution events...
              </div>
            ) : (
              filteredEvents.map((ev) => {
                const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '';
                let statusBadgeColor = 'bg-slate-800 text-slate-300';
                if (ev.status === 'success') statusBadgeColor = 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40';
                else if (ev.status === 'running') statusBadgeColor = 'bg-blue-950/80 text-blue-400 border border-blue-800/40 animate-pulse';
                else if (ev.status === 'warning') statusBadgeColor = 'bg-amber-950/80 text-amber-400 border border-amber-800/40';
                else if (ev.status === 'error') statusBadgeColor = 'bg-rose-950/80 text-rose-400 border border-rose-800/40';
                else if (ev.status === 'info') statusBadgeColor = 'bg-slate-800/80 text-cyan-300 border border-slate-700/50';

                return (
                  <div
                    key={ev.id}
                    className="p-1.5 rounded hover:bg-slate-900/60 transition-colors flex items-start gap-2.5 leading-relaxed"
                  >
                    <span className="text-slate-500 text-[10px] shrink-0 font-mono mt-0.5">{timeStr}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold shrink-0 ${statusBadgeColor}`}
                    >
                      {ev.status}
                    </span>
                    <span className="text-cyan-400 font-semibold shrink-0 text-[11px]">
                      [{ev.agent_name || ev.node_title}]
                    </span>
                    <span className="text-slate-200 flex-1 break-words">{ev.summary}</span>
                  </div>
                );
              })
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>
      ) : (
        /* SECTIONS & DAG BREAKDOWN WITH SEPARATE NODE RUNNERS */
        <div className="p-5 space-y-5 bg-sand-50/40">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-serif font-bold text-ink">Modular Execution Graph (DAG)</h4>
              <p className="text-xs text-ink-500">
                Each section and sub-section is a modular node. You can run or retry any sub-section separately as long as prerequisite inputs have been completed.
              </p>
            </div>
            {isPaused && (
              <span className="text-xs font-mono font-medium text-amber-600 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20">
                Paused at step: click Resume to continue
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4">
            {graphState?.sections.map((section) => {
              const sectionNodes = section.node_ids
                .map((nid) => graphState.nodes[nid])
                .filter(Boolean) as GraphNode[];

              const completedNodesCount = sectionNodes.filter((n) => n.status === 'completed').length;
              const allDone = sectionNodes.length > 0 && completedNodesCount === sectionNodes.length;

              return (
                <div
                  key={section.section_id}
                  className={`rounded-lg border transition-all ${
                    allDone ? 'border-pine/30 bg-card' : 'border-line bg-card'
                  }`}
                >
                  {/* Section Title Header */}
                  <div className="px-4 py-3 border-b border-line/60 bg-sand-100/40 flex items-center justify-between">
                    <div>
                      <span className="font-serif font-semibold text-sm text-ink">{section.title}</span>
                      <p className="text-[11px] text-ink-500">{section.description}</p>
                    </div>
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded font-medium ${
                        allDone
                          ? 'bg-pine/10 text-pine border border-pine/20'
                          : 'bg-sand-200 text-ink-600'
                      }`}
                    >
                      {completedNodesCount} / {sectionNodes.length} Done
                    </span>
                  </div>

                  {/* Sub-sections / Nodes inside this Section */}
                  <div className="divide-y divide-line/40">
                    {sectionNodes.map((node) => {
                      const isNodeRunning = runningNodeId === node.node_id || node.status === 'running';
                      const isNodeCompleted = node.status === 'completed';
                      const isNodeFailed = node.status === 'failed';
                      const canRun = node.can_run_separately && !isNodeRunning;

                      let statusBadge = (
                        <span className="text-[11px] font-mono text-ink-400 bg-sand-200/60 px-2 py-0.5 rounded">
                          Waiting
                        </span>
                      );
                      if (isNodeRunning) {
                        statusBadge = (
                          <span className="text-[11px] font-mono text-blue-600 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping" />
                            Running...
                          </span>
                        );
                      } else if (isNodeCompleted) {
                        statusBadge = (
                          <span className="text-[11px] font-mono text-pine bg-pine/10 px-2 py-0.5 rounded border border-pine/20 font-semibold">
                            ✓ Completed
                          </span>
                        );
                      } else if (isNodeFailed) {
                        statusBadge = (
                          <span className="text-[11px] font-mono text-bad bg-bad/10 px-2 py-0.5 rounded border border-bad/20 font-semibold">
                            ✕ Failed
                          </span>
                        );
                      } else if (canRun) {
                        statusBadge = (
                          <span className="text-[11px] font-mono text-cyan-600 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                            Ready to Run
                          </span>
                        );
                      }

                      return (
                        <div
                          key={node.node_id}
                          className="px-4 py-3 flex flex-wrap items-center justify-between gap-3 hover:bg-sand-50/50 transition-colors"
                        >
                          <div className="flex-1 min-w-[240px]">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-ink">{node.title}</span>
                              {statusBadge}
                              <span className="text-[10px] font-mono text-ink-400">
                                [{node.agent_name}]
                              </span>
                            </div>
                            <p className="text-xs text-ink-500 mt-0.5">{node.description}</p>

                            {/* Node Error details */}
                            {node.error_message && (
                              <div className="mt-1.5 text-xs text-bad bg-bad/5 p-2 rounded border border-bad/20">
                                Error: {node.error_message}
                              </div>
                            )}

                            {/* Node Output counts */}
                            {(node.evidence_count || node.claims_count || node.duration_ms) ? (
                              <div className="mt-1 flex items-center gap-3 text-[11px] font-mono text-ink-400">
                                {node.duration_ms ? <span>⏱ {formatMs(node.duration_ms)}</span> : null}
                                {node.evidence_count ? (
                                  <span>🔎 {node.evidence_count} evidence items</span>
                                ) : null}
                                {node.claims_count ? <span>📝 {node.claims_count} claims</span> : null}
                                {node.output_summary ? (
                                  <span className="text-ink-600 font-sans italic">{node.output_summary}</span>
                                ) : null}
                              </div>
                            ) : null}
                          </div>

                          {/* Action Button: Run Separately / Retry */}
                          <div className="shrink-0 flex items-center gap-2">
                            {canRun ? (
                              <button
                                type="button"
                                onClick={() => handleRunNode(node.node_id)}
                                disabled={isNodeRunning}
                                className="px-3 py-1 text-xs font-medium bg-sand-200 hover:bg-sand-300 text-ink rounded-md transition-colors cursor-pointer flex items-center gap-1.5 shadow-2xs"
                              >
                                <svg className="w-3 h-3 text-pine" fill="currentColor" viewBox="0 0 24 24">
                                  <path d="M8 5v14l11-7z" />
                                </svg>
                                <span>{isNodeCompleted ? 'Re-run step' : 'Run this step'}</span>
                              </button>
                            ) : (
                              <button
                                type="button"
                                disabled
                                title={`Prerequisites pending: ${node.missing_dependencies.join(', ')}`}
                                className="px-3 py-1 text-xs font-medium bg-sand-100 text-ink-300 rounded-md cursor-not-allowed border border-line/40"
                              >
                                {isNodeRunning ? 'Executing...' : 'Blocked'}
                              </button>
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
        </div>
      )}
    </div>
  );
}
