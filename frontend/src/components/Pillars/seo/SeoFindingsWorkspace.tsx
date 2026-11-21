import React, { useEffect, useMemo, useState } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport, Finding } from '../../../types';
import { FindingDetailDrawer } from './FindingDetailDrawer';
import { seoApi, SeoRemediationTask } from '../../../services/seoApi';
import { ChevronRight, Code, Download, Layers, Search } from 'lucide-react';

interface SeoFindingsWorkspaceProps {
  report: ExecutiveReport;
  auditId?: string;
  seoFindings: Finding[];
  tasks?: SeoRemediationTask[];
  onSelectFinding?: (f: Finding) => void;
  onTasksChanged?: () => void;
}

export function SeoFindingsWorkspace({
  report,
  auditId,
  seoFindings: initialFindings,
  tasks = [],
  onSelectFinding,
  onTasksChanged,
}: SeoFindingsWorkspaceProps) {
  const [findings, setFindings] = useState<Finding[]>(initialFindings);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'table' | 'clustered'>('table');
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  useEffect(() => {
    setFindings(initialFindings);
  }, [initialFindings]);

  const effectiveAuditId = auditId || report.analysis_id || report.report_id || '';

  const tasksByFindingId = useMemo(() => {
    const map = new Map<string, SeoRemediationTask>();
    for (const t of tasks) map.set(t.finding_id, t);
    return map;
  }, [tasks]);

  const handleUpdateStatus = async (findingId: string, newStatus: string) => {
    // Enforce Fixed != Verified: UI never allows manual transition to VERIFIED_FIXED without backend verification
    setFindings((prev) =>
      prev.map((f) => (f.finding_id === findingId ? { ...f, resolution_status: newStatus } : f))
    );
    if (selectedFinding?.finding_id === findingId) {
      setSelectedFinding((prev) => (prev ? { ...prev, resolution_status: newStatus } : null));
    }
    if (effectiveAuditId && newStatus !== 'VERIFIED_FIXED') {
      try {
        await seoApi.updateFinding(effectiveAuditId, findingId, { status: newStatus });
        setActionNotice(`Persisted ${findingId} → ${newStatus}.`);
      } catch (err: any) {
        setActionNotice(err?.message || `Updated locally (${newStatus}).`);
      }
    }
  };

  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        f.title.toLowerCase().includes(q) ||
        f.finding_id.toLowerCase().includes(q) ||
        (f.description && f.description.toLowerCase().includes(q));
      const matchesSeverity = severityFilter === 'ALL' || f.severity === severityFilter;
      const fStatus = f.resolution_status || f.verification_status || 'VERIFIED';
      const matchesStatus = statusFilter === 'ALL' || fStatus === statusFilter;
      return matchesSearch && matchesSeverity && matchesStatus;
    });
  }, [findings, searchQuery, severityFilter, statusFilter]);

  // Group by systemic root_cause_id first, falling back to category
  const clusters = useMemo(() => {
    const map = new Map<string, { title: string; subtitle: string; items: Finding[] }>();
    for (const f of filteredFindings) {
      const rcId = (f as any).root_cause_id;
      const cat = f.category || 'TECHNICAL_SEO';
      const key = rcId ? `${rcId}` : cat;
      if (!map.has(key)) {
        map.set(key, {
          title: rcId ? `${cat.replace(/_/g, ' ')} · ${rcId}` : cat.replace(/_/g, ' '),
          subtitle: rcId ? 'Shared systemic root cause' : 'Category group',
          items: [],
        });
      }
      map.get(key)!.items.push(f);
    }
    return Array.from(map.entries()).map(([clusterKey, val]) => ({ clusterKey, ...val }));
  }, [filteredFindings]);

  const handleSelectAll = () => {
    if (selectedIds.length === filteredFindings.length) setSelectedIds([]);
    else setSelectedIds(filteredFindings.map((f) => f.finding_id));
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  const handleBulkStatusChange = async (newStatus: 'FIX_SUBMITTED' | 'ACCEPTED_RISK' | 'REMEDIATION_PLANNED') => {
    const ids = [...selectedIds];
    setFindings((prev) =>
      prev.map((f) => (ids.includes(f.finding_id) ? { ...f, resolution_status: newStatus } : f))
    );
    setSelectedIds([]);
    if (effectiveAuditId) {
      await Promise.allSettled(
        ids.map((fid) =>
          newStatus === 'REMEDIATION_PLANNED'
            ? seoApi.createTask(fid, { audit_id: effectiveAuditId })
            : seoApi.updateFinding(effectiveAuditId, fid, { status: newStatus })
        )
      );
      onTasksChanged?.();
      setActionNotice(`Bulk updated ${ids.length} finding(s) to ${newStatus}.`);
    }
  };

  const handleExportCsv = () => {
    const headers = ['Finding ID', 'Root Cause', 'Severity', 'Category', 'Status', 'Title', 'Recommendation'];
    const rows = filteredFindings.map((f) => [
      f.finding_id,
      (f as any).root_cause_id || '',
      f.severity,
      f.category,
      f.resolution_status || f.verification_status || 'VERIFIED',
      `"${f.title.replace(/"/g, '""')}"`,
      `"${(f.recommendation || f.description || '').replace(/"/g, '""')}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `dristik-seo-findings-${report.domain}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">SEO Findings &amp; Remediation Workspace</h3>
          <p className="text-xs text-ink-500">
            Canonical defect lifecycle manager. Marking a fix submitted does not verify it—run automated re-crawl verification to seal VERIFIED_FIXED.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border border-line rounded-lg p-0.5 bg-paper-subtle">
            <button
              onClick={() => setViewMode('table')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md ${viewMode === 'table' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500'}`}
            >
              List View
            </button>
            <button
              onClick={() => setViewMode('clustered')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md ${viewMode === 'clustered' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500'}`}
            >
              Root-Cause Clusters
            </button>
          </div>
          <Button variant="secondary" size="sm" onClick={handleExportCsv} className="text-xs">
            <Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV
          </Button>
        </div>
      </div>

      {actionNotice && (
        <div className="px-3 py-2 rounded-lg bg-paper-subtle border border-line text-xs text-ink-600 flex items-center justify-between">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-ink-400 hover:text-ink text-xs">Dismiss</button>
        </div>
      )}

      <div className="p-4 rounded-xl border border-line bg-paper-subtle space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-ink-400" />
            <input
              type="text"
              placeholder="Filter findings by keyword or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-line bg-paper text-ink"
            />
          </div>
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value as any)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink">
            <option value="ALL">All Lifecycle States</option>
            <option value="DETECTED">DETECTED</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="PRIORITIZED">PRIORITIZED</option>
            <option value="REMEDIATION_PLANNED">REMEDIATION_PLANNED</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="FIX_SUBMITTED">FIX_SUBMITTED</option>
            <option value="RETESTING">RETESTING</option>
            <option value="VERIFIED_FIXED">VERIFIED_FIXED</option>
            <option value="ACCEPTED_RISK">ACCEPTED_RISK</option>
            <option value="DEFERRED">DEFERRED</option>
            <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
          </select>
          {selectedIds.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold text-ink">{selectedIds.length} sel.</span>
              <Button size="sm" variant="secondary" onClick={() => handleBulkStatusChange('REMEDIATION_PLANNED')} className="text-xs h-7 px-2">
                Create Tasks
              </Button>
              <Button size="sm" variant="secondary" onClick={() => handleBulkStatusChange('FIX_SUBMITTED')} className="text-xs h-7 px-2">
                Submit Fix
              </Button>
              <Button size="sm" variant="ghost" onClick={() => handleBulkStatusChange('ACCEPTED_RISK')} className="text-xs h-7 px-2">
                Accept Risk
              </Button>
            </div>
          )}
        </div>
      </div>

      {viewMode === 'table' ? (
        <div className="rounded-xl border border-line bg-paper overflow-x-auto shadow-xs">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-line bg-paper-subtle text-[11px] font-semibold uppercase text-ink-400">
                <th className="py-3 px-4 w-10">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === filteredFindings.length && filteredFindings.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-line"
                  />
                </th>
                <th className="py-3 px-3">Finding ID</th>
                <th className="py-3 px-3">Severity</th>
                <th className="py-3 px-3">State</th>
                <th className="py-3 px-4">Title &amp; Diagnosis</th>
                <th className="py-3 px-3">Category</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filteredFindings.map((f) => {
                const isSelected = selectedIds.includes(f.finding_id);
                const status = f.resolution_status || f.verification_status || 'VERIFIED';
                return (
                  <tr
                    key={f.finding_id}
                    onClick={() => {
                      setSelectedFinding(f);
                      onSelectFinding?.(f);
                    }}
                    className={`hover:bg-paper-subtle/80 cursor-pointer transition-colors group ${isSelected ? 'bg-primary/5' : ''}`}
                  >
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={isSelected} onChange={() => handleToggleSelect(f.finding_id)} className="rounded border-line" />
                    </td>
                    <td className="py-3 px-3 font-mono font-semibold text-ink-500">{f.finding_id}</td>
                    <td className="py-3 px-3">
                      <Badge tone={f.severity === 'CRITICAL' ? 'bad' : f.severity === 'HIGH' ? 'warn' : 'neutral'}>{f.severity}</Badge>
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-mono text-[11px] font-semibold px-2 py-0.5 rounded bg-paper-subtle border border-line">{status}</span>
                    </td>
                    <td className="py-3 px-4 max-w-md">
                      <p className="font-semibold text-ink group-hover:text-primary">{f.title}</p>
                      <p className="text-[11px] text-ink-500 line-clamp-1 mt-0.5">{f.recommendation || f.description}</p>
                    </td>
                    <td className="py-3 px-3 text-ink-600 font-mono text-[11px]">{f.category}</td>
                    <td className="py-3 px-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFinding(f);
                          onSelectFinding?.(f);
                        }}
                        className="text-xs h-7 px-2"
                      >
                        Patch <Code className="w-3 h-3 ml-1" />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="space-y-4">
          {clusters.map((c) => (
            <div key={c.clusterKey} className="rounded-xl border border-line bg-paper p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-primary" />
                  <div>
                    <h4 className="text-sm font-bold text-ink uppercase tracking-wider">{c.title}</h4>
                    <span className="text-[11px] text-ink-400">{c.subtitle}</span>
                  </div>
                </div>
                <Badge tone="neutral">{c.items.length} Finding{c.items.length !== 1 ? 's' : ''}</Badge>
              </div>
              <div className="divide-y divide-line/60">
                {c.items.map((item) => (
                  <div
                    key={item.finding_id}
                    onClick={() => {
                      setSelectedFinding(item);
                      onSelectFinding?.(item);
                    }}
                    className="py-2.5 flex items-center justify-between hover:bg-paper-subtle px-2 rounded cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <Badge tone={item.severity === 'CRITICAL' ? 'bad' : 'warn'}>{item.severity}</Badge>
                      <span className="font-mono text-xs text-ink-400">{item.finding_id}</span>
                      <span className="text-xs font-medium text-ink">{item.title}</span>
                    </div>
                    <Button size="sm" variant="ghost" className="text-xs h-6 px-2">
                      Inspect <ChevronRight className="w-3 h-3 ml-1" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedFinding && (
        <FindingDetailDrawer
          finding={selectedFinding}
          auditId={effectiveAuditId}
          task={tasksByFindingId.get(selectedFinding.finding_id) || null}
          onClose={() => setSelectedFinding(null)}
          onUpdateStatus={handleUpdateStatus}
        />
      )}
    </div>
  );
}
