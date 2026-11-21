import React, { useMemo, useState } from 'react';
import { Badge, Button } from '../../ui';
import { ExecutiveReport, Finding } from '../../../types';
import { FindingDetailDrawer } from './FindingDetailDrawer';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Code,
  Download,
  Filter,
  Layers,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';

interface SeoFindingsWorkspaceProps {
  report: ExecutiveReport;
  seoFindings: Finding[];
  onSelectFinding?: (f: Finding) => void;
}

export function SeoFindingsWorkspace({
  report,
  seoFindings: initialFindings,
  onSelectFinding,
}: SeoFindingsWorkspaceProps) {
  const [findings, setFindings] = useState<Finding[]>(initialFindings);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'table' | 'clustered'>('table');
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Update status handler
  const handleUpdateStatus = (findingId: string, newStatus: string) => {
    setFindings((prev) =>
      prev.map((f) =>
        f.finding_id === findingId
          ? { ...f, resolution_status: newStatus, verification_status: newStatus }
          : f
      )
    );
    if (selectedFinding && selectedFinding.finding_id === findingId) {
      setSelectedFinding((prev) =>
        prev ? { ...prev, resolution_status: newStatus, verification_status: newStatus } : null
      );
    }
  };

  // Filtered findings
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

  // Root-cause clusters
  const clusters = useMemo(() => {
    const map = new Map<string, Finding[]>();
    for (const f of filteredFindings) {
      const clusterKey = f.category || 'TECHNICAL_SEO';
      if (!map.has(clusterKey)) map.set(clusterKey, []);
      map.get(clusterKey)!.push(f);
    }
    return Array.from(map.entries()).map(([key, items]) => ({
      clusterKey: key,
      title: key.replace(/_/g, ' '),
      items,
    }));
  }, [filteredFindings]);

  // Bulk actions
  const handleSelectAll = () => {
    if (selectedIds.length === filteredFindings.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredFindings.map((f) => f.finding_id));
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleBulkStatusChange = (newStatus: string) => {
    setFindings((prev) =>
      prev.map((f) =>
        selectedIds.includes(f.finding_id)
          ? { ...f, resolution_status: newStatus, verification_status: newStatus }
          : f
      )
    );
    setSelectedIds([]);
  };

  const handleExportCsv = () => {
    const headers = ['Finding ID', 'Severity', 'Category', 'Status', 'Title', 'Recommendation'];
    const rows = filteredFindings.map((f) => [
      f.finding_id,
      f.severity,
      f.category,
      f.resolution_status || f.verification_status || 'VERIFIED',
      `"${f.title.replace(/"/g, '""')}"`,
      `"${(f.recommendation || f.description || '').replace(/"/g, '""')}"`,
    ]);
    const csvContent =
      'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `dristik-seo-findings-${report.domain}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">SEO Findings &amp; Remediation Workspace</h3>
          <p className="text-xs text-ink-500">
            Enterprise defect lifecycle manager. Track, assign, inspect code patches, and run automated re-crawl verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border border-line rounded-lg p-0.5 bg-paper-subtle">
            <button
              onClick={() => setViewMode('table')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                viewMode === 'table' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500 hover:text-ink'
              }`}
            >
              List View
            </button>
            <button
              onClick={() => setViewMode('clustered')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                viewMode === 'clustered' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500 hover:text-ink'
              }`}
            >
              Root-Cause Clusters
            </button>
          </div>

          <Button variant="secondary" size="sm" onClick={handleExportCsv} className="text-xs">
            <Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Filter & Bulk Bar */}
      <div className="p-4 rounded-xl border border-line bg-paper-subtle space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-ink-400" />
            <input
              type="text"
              placeholder="Filter findings by keyword or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-line bg-paper text-ink focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-ink-400 uppercase">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as any)}
              className="flex-1 py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-ink-400 uppercase">Lifecycle:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="flex-1 py-1.5 px-2 text-xs rounded-lg border border-line bg-paper text-ink"
            >
              <option value="ALL">All States (15)</option>
              <option value="VERIFIED">VERIFIED</option>
              <option value="ASSIGNED">ASSIGNED</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="CODE_GENERATED">CODE_GENERATED</option>
              <option value="DEPLOYED_STAGING">DEPLOYED_STAGING</option>
              <option value="VERIFIED_FIXED">VERIFIED_FIXED</option>
              <option value="IGNORED">IGNORED</option>
            </select>
          </div>

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-ink">{selectedIds.length} selected</span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleBulkStatusChange('VERIFIED_FIXED')}
                className="text-xs h-7"
              >
                Mark Fixed
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Main Table View */}
      {viewMode === 'table' ? (
        <div className="rounded-xl border border-line bg-paper overflow-hidden shadow-xs">
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
                    className={`hover:bg-paper-subtle/80 cursor-pointer transition-colors group ${
                      isSelected ? 'bg-primary/5' : ''
                    }`}
                  >
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelect(f.finding_id)}
                        className="rounded border-line"
                      />
                    </td>
                    <td className="py-3 px-3 font-mono font-semibold text-ink-500">{f.finding_id}</td>
                    <td className="py-3 px-3">
                      <Badge tone={f.severity === 'CRITICAL' ? 'bad' : f.severity === 'HIGH' ? 'warn' : 'neutral'}>
                        {f.severity}
                      </Badge>
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-mono text-[11px] font-semibold px-2 py-0.5 rounded bg-paper-subtle border border-line">
                        {status}
                      </span>
                    </td>
                    <td className="py-3 px-4 max-w-md">
                      <p className="font-semibold text-ink group-hover:text-primary transition-colors">{f.title}</p>
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
        /* Root Cause Clustered View */
        <div className="space-y-4">
          {clusters.map((c) => (
            <div key={c.clusterKey} className="rounded-xl border border-line bg-paper p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-primary" />
                  <h4 className="text-sm font-bold text-ink uppercase tracking-wider">{c.title}</h4>
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
                    className="py-2.5 flex items-center justify-between hover:bg-paper-subtle px-2 rounded cursor-pointer transition-colors"
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

      {/* Finding Detail Slide-Over Drawer */}
      {selectedFinding && (
        <FindingDetailDrawer
          finding={selectedFinding}
          onClose={() => setSelectedFinding(null)}
          onUpdateStatus={handleUpdateStatus}
        />
      )}
    </div>
  );
}
