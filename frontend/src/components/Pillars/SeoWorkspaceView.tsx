import React, { useEffect, useState } from 'react';
import { ExecutiveReport, Finding } from '../../types';
import { SearchConsoleAttributionView } from '../SearchConsoleAttributionView';
import { PillarShell } from '../ui';
import { SectionExportButtons } from '../ui/SectionExportButtons';
import { SeoExecutiveOverview } from './seo/SeoExecutiveOverview';
import { SeoExecutiveDashboard } from './seo/SeoExecutiveDashboard';
import { CrawlExplorerView } from './seo/CrawlExplorerView';
import { InternalLinkGraphView } from './seo/InternalLinkGraphView';
import { SeoIntegrationsView } from './seo/SeoIntegrationsView';
import { SeoFindingsWorkspace } from './seo/SeoFindingsWorkspace';
import { SeoRemediationCenter } from './seo/SeoRemediationCenter';
import { SeoIntelligenceWorkspace } from './seo/SeoIntelligenceWorkspace';
import { SeoCrawlArchitecture } from './seo/SeoCrawlArchitecture';
import { SeoOnPageExperience } from './seo/SeoOnPageExperience';
import { SeoMarketIntelligence } from './seo/SeoMarketIntelligence';
import { AuditIndex } from '../../report/auditIndex/AuditIndex';
import { EnterpriseSeoAssessment, EnterpriseSeoAudit } from './seo/EnterpriseSeoAudit';
import { DeltaAnalyticsDashboard } from '../DeltaAnalyticsDashboard';
import {
  seoApi,
  SeoAuditHistory,
  SeoConnectorStatus,
  SeoRemediationTask,
  SeoScorecardReport,
} from '../../services/seoApi';

interface SeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onSelectFinding?: (f: Finding) => void;
  onOpenConnectors?: (tabId?: string) => void;
}

export type EnterpriseSeoTab =
  | 'overview'
  | 'discovery'
  | 'linkgraph'
  | 'architecture'
  | 'onpage'
  | 'intelligence'
  | 'market'
  | 'gsc'
  | 'integrations'
  | 'issues'
  | 'remediation'
  | 'index'
  | 'enterprise'
  | 'history';

const SEO_CATEGORIES = new Set([
  'TECHNICAL_SEO',
  'ON_PAGE_SEO',
  'CONTENT',
  'STRUCTURED_DATA',
  'PERFORMANCE',
  'AUTHORITY',
  'LOCAL_SEO',
  'INTERNATIONAL_SEO',
  'ECOMMERCE_SEO',
]);

export function SeoWorkspaceView({
  report,
  analysisId,
  onSelectFinding,
  onOpenConnectors,
}: SeoWorkspaceViewProps) {
  const [activeTab, setActiveTab] = useState<EnterpriseSeoTab>('overview');
  const [overviewMode, setOverviewMode] = useState<'dashboard' | 'briefing'>('dashboard');
  const [selectedProfile, setSelectedProfile] = useState<string>('complete_book');
  const [scorecard, setScorecard] = useState<SeoScorecardReport | null>(null);
  const [assessment, setAssessment] = useState<EnterpriseSeoAssessment | null>(null);
  const [tasks, setTasks] = useState<SeoRemediationTask[]>([]);
  const [connectors, setConnectors] = useState<SeoConnectorStatus[]>([]);
  const [history, setHistory] = useState<SeoAuditHistory | null>(null);
  const [backendGraph, setBackendGraph] = useState<Record<string, any> | null>(null);

  const effectiveAuditId = analysisId || report.analysis_id || report.report_id || '';

  const refreshBackendData = () => {
    if (!effectiveAuditId) return;
    seoApi.getOverview(effectiveAuditId).then((ov) => {
      if (ov?.scorecard) setScorecard(ov.scorecard);
      if (ov?.coverage) setAssessment((prev) => ({ ...(prev || ({} as any)), coverage: ov.coverage }));
    }).catch(() => {});
    seoApi.getTasks(effectiveAuditId).then((res) => {
      if (Array.isArray(res?.tasks)) setTasks(res.tasks);
    }).catch(() => {});
    seoApi.listConnectors().then((res) => {
      if (Array.isArray(res)) setConnectors(res);
    }).catch(() => {});
    seoApi.getHistory(effectiveAuditId).then((res) => {
      if (res) setHistory(res);
    }).catch(() => {});
    seoApi.getLinkGraph(effectiveAuditId).then((res) => {
      if (res && Array.isArray(res.nodes)) setBackendGraph(res);
    }).catch(() => {});
  };

  useEffect(() => {
    refreshBackendData();
  }, [effectiveAuditId]);

  const seoFindings = (report.findings || []).filter(
    (f) => SEO_CATEGORIES.has(String(f.category || '').toUpperCase())
  );

  // Strictly canonical score — NEVER fall back to a hardcoded magic number like 74
  const rawScore =
    scorecard?.overall_health_score ??
    report.scores?.category_scores?.['TECHNICAL_SEO']?.score ??
    report.honest_scores?.google_score;
  const seoScore = rawScore != null && Number.isFinite(rawScore) ? Math.round(rawScore) : null;

  const handleTabChange = (rawId: string) => {
    switch (rawId) {
      case 'crawl':
        setActiveTab('discovery');
        break;
      case 'security':
        setActiveTab('architecture');
        break;
      case 'assets':
      case 'links':
        setActiveTab('onpage');
        break;
      case 'local':
      case 'international':
      case 'competitors':
        setActiveTab('market');
        break;
      case 'findings':
      case 'appendix':
        setActiveTab('issues');
        break;
      case 'overview':
      case 'discovery':
      case 'linkgraph':
      case 'architecture':
      case 'onpage':
      case 'intelligence':
      case 'market':
      case 'gsc':
      case 'integrations':
      case 'issues':
      case 'remediation':
      case 'index':
      case 'enterprise':
      case 'history':
        setActiveTab(rawId as EnterpriseSeoTab);
        break;
      default:
        setActiveTab('overview');
    }
  };

  return (
    <PillarShell
      kicker="Website search performance"
      title="Search Engine Optimization (SEO)"
      description="Canonical enterprise SEO operating system: 40 specialist diagnostics, reconciled 6-tier crawl inventory, 9-dimension mathematical scorecard, stack-aware remediation, live re-crawl verification, and multi-profile PDF publishing."
      scoreLabel="SEO Health Index"
      score={seoScore != null ? `${seoScore}/100` : 'Unmeasured'}
      metaLabel="Issues"
      meta={`${seoFindings.length} flagged`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <SectionExportButtons analysisId={effectiveAuditId} sectionKey="seo" sectionLabel="SEO" />
          {effectiveAuditId && (
            <>
              <select
                aria-label="SEO Report Publication Profile"
                value={selectedProfile}
                onChange={(e) => setSelectedProfile(e.target.value)}
                className="px-2 py-1.5 text-xs rounded-lg border border-line bg-paper text-ink"
              >
                <option value="complete_book">Complete SEO Audit Book</option>
                <option value="executive">Executive SEO Brief</option>
                <option value="technical">Technical SEO Report</option>
                <option value="content">Content SEO Report</option>
                <option value="remediation">Remediation Plan</option>
                <option value="verification">Verification Report</option>
                <option value="evidence">Evidence Appendix</option>
              </select>
              <a
                href={`/api/v1/reports/${effectiveAuditId}/seo-report?profile=${encodeURIComponent(selectedProfile)}&format=pdf&download=true`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink transition-colors"
                title="Download the canonical QA-gated SEO Audit Book PDF"
              >
                SEO Book PDF
              </a>
              <a
                href={`/api/v1/reports/${effectiveAuditId}/seo-report?profile=${encodeURIComponent(selectedProfile)}&format=print`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink transition-colors"
                title="Open the print-ready SEO Audit Book HTML"
              >
                SEO Book Print
              </a>
            </>
          )}
        </div>
      }
      tabs={[
        { id: 'overview', label: 'Executive Dashboard' },
        { id: 'discovery', label: 'Crawl Explorer' },
        { id: 'linkgraph', label: 'Internal Link Graph' },
        { id: 'architecture', label: 'Site Architecture' },
        { id: 'onpage', label: 'On-Page & SERP' },
        { id: 'intelligence', label: 'Keyword & Content' },
        { id: 'integrations', label: 'Connectors & Data' },
        { id: 'market', label: 'Local & Global' },
        { id: 'gsc', label: 'Search Console' },
        { id: 'issues', label: `Findings (${seoFindings.length})` },
        { id: 'remediation', label: `Remediation & Verify (${tasks.length})` },
        { id: 'index', label: 'Audit Index' },
        { id: 'enterprise', label: 'Enterprise Assessment' },
        { id: 'history', label: 'History & Regressions' },
      ]}
      activeTab={activeTab}
      onTab={handleTabChange}
    >
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <span className="text-xs uppercase font-bold text-ink-500 tracking-wider">Overview Presentation Mode:</span>
            <div className="flex items-center border border-line rounded-lg p-0.5 bg-paper-subtle">
              <button
                onClick={() => setOverviewMode('dashboard')}
                className={`px-3 py-1 text-xs font-semibold rounded-md ${overviewMode === 'dashboard' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500'}`}
              >
                Operations Dashboard
              </button>
              <button
                onClick={() => setOverviewMode('briefing')}
                className={`px-3 py-1 text-xs font-semibold rounded-md ${overviewMode === 'briefing' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500'}`}
              >
                Executive Briefing
              </button>
            </div>
          </div>

          {overviewMode === 'dashboard' ? (
            <SeoExecutiveDashboard
              report={report}
              assessment={assessment}
              scorecard={scorecard}
              connectors={connectors}
              history={history}
              seoFindings={seoFindings}
              onNavigateTab={handleTabChange}
              onSelectFinding={onSelectFinding}
            />
          ) : (
            <SeoExecutiveOverview
              report={report}
              seoFindings={seoFindings}
              onNavigateTab={handleTabChange}
              onSelectFinding={onSelectFinding}
            />
          )}
        </div>
      )}

      {activeTab === 'discovery' && <CrawlExplorerView report={report} onSelectFinding={onSelectFinding} />}
      {activeTab === 'linkgraph' && (
        <InternalLinkGraphView report={report} backendGraph={backendGraph} onSelectFinding={onSelectFinding} />
      )}
      {activeTab === 'architecture' && <SeoCrawlArchitecture report={report} />}
      {activeTab === 'onpage' && <SeoOnPageExperience report={report} />}
      {activeTab === 'intelligence' && (
        <SeoIntelligenceWorkspace report={report} onOpenConnectors={() => setActiveTab('integrations')} />
      )}
      {activeTab === 'market' && <SeoMarketIntelligence report={report} />}
      {activeTab === 'gsc' && (
        <SearchConsoleAttributionView
          domain={report.domain}
          analysisId={effectiveAuditId}
          onOpenConnectors={() => onOpenConnectors?.('google_search_console')}
        />
      )}
      {activeTab === 'integrations' && <SeoIntegrationsView onConnectorsUpdated={setConnectors} />}
      {activeTab === 'issues' && (
        <SeoFindingsWorkspace
          report={report}
          auditId={effectiveAuditId}
          seoFindings={seoFindings}
          tasks={tasks}
          onSelectFinding={onSelectFinding}
          onTasksChanged={refreshBackendData}
        />
      )}
      {activeTab === 'remediation' && (
        <SeoRemediationCenter auditId={effectiveAuditId} tasks={tasks} onTasksUpdated={refreshBackendData} />
      )}
      {activeTab === 'index' && <AuditIndex report={report} />}
      {activeTab === 'enterprise' && <EnterpriseSeoAudit analysisId={effectiveAuditId} report={report} />}
      {activeTab === 'history' && <DeltaAnalyticsDashboard />}
    </PillarShell>
  );
}
