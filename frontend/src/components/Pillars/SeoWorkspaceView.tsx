import React, { useState } from 'react';
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
import { SeoIntelligenceWorkspace } from './seo/SeoIntelligenceWorkspace';
import { SeoCrawlArchitecture } from './seo/SeoCrawlArchitecture';
import { SeoOnPageExperience } from './seo/SeoOnPageExperience';
import { SeoMarketIntelligence } from './seo/SeoMarketIntelligence';
import { SeoIssuesAndAppendix } from './seo/SeoIssuesAndAppendix';
import { AuditIndex } from '../../report/auditIndex/AuditIndex';
import { EnterpriseSeoAudit } from './seo/EnterpriseSeoAudit';
import { DeltaAnalyticsDashboard } from '../DeltaAnalyticsDashboard';

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
  | 'index'
  | 'enterprise'
  | 'history';

export function SeoWorkspaceView({
  report,
  analysisId,
  onSelectFinding,
  onOpenConnectors,
}: SeoWorkspaceViewProps) {
  const [activeTab, setActiveTab] = useState<EnterpriseSeoTab>('overview');
  const [overviewMode, setOverviewMode] = useState<'dashboard' | 'briefing'>('dashboard');

  const seoFindings = (report.findings || []).filter(
    (f) => f.category === 'TECHNICAL_SEO' || f.category === 'ON_PAGE_SEO' || f.category === 'CONTENT'
  );

  const rawScore = report.scores?.category_scores?.['TECHNICAL_SEO']?.score ?? report.honest_scores?.google_score;
  const seoScore = rawScore != null && Number.isFinite(rawScore) ? Math.round(rawScore) : 74;

  // Handle tab switching with backward compatibility normalization
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
      description="Understand how search engines discover, crawl, interpret and rank the pages checked in this audit. Review technical issues, page content, local and international targeting, and connected Search Console data."
      scoreLabel="SEO Health Index"
      score={seoScore != null ? `${seoScore}/100` : '—'}
      metaLabel="Issues"
      meta={`${seoFindings.length} flagged`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <SectionExportButtons
            analysisId={analysisId || report.analysis_id || report.report_id}
            sectionKey="seo"
            sectionLabel="SEO"
          />
          {(analysisId || report.analysis_id || report.report_id) && (
            <>
              <a
                href={`/api/v1/reports/${analysisId || report.analysis_id || report.report_id}/seo-report?format=pdf&download=true`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink transition-colors"
                title="Open the dedicated SEO master audit book as a PDF"
              >
                SEO Book PDF
              </a>
              <a
                href={`/api/v1/reports/${analysisId || report.analysis_id || report.report_id}/seo-report?format=print`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-paper-100 hover:bg-paper-200 text-ink transition-colors"
                title="Open the dedicated SEO master audit book for printing"
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
        { id: 'issues', label: `Findings & Fixes (${seoFindings.length})` },
        { id: 'index', label: 'Audit Index' },
        { id: 'enterprise', label: 'Enterprise Assessment' },
        { id: 'history', label: 'History & Regressions' },
      ]}
      activeTab={activeTab}
      onTab={handleTabChange}
    >
      {/* ─────────────────────────────────────────────────────────────
          1. EXECUTIVE OVERVIEW / DASHBOARD TAB
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <span className="text-xs uppercase font-bold text-ink-500 tracking-wider">
              Overview Presentation Mode:
            </span>
            <div className="flex items-center border border-line rounded-lg p-0.5 bg-paper-subtle">
              <button
                onClick={() => setOverviewMode('dashboard')}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                  overviewMode === 'dashboard' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500 hover:text-ink'
                }`}
              >
                Operations Dashboard
              </button>
              <button
                onClick={() => setOverviewMode('briefing')}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                  overviewMode === 'briefing' ? 'bg-paper shadow-xs text-ink' : 'text-ink-500 hover:text-ink'
                }`}
              >
                Executive Briefing
              </button>
            </div>
          </div>

          {overviewMode === 'dashboard' ? (
            <SeoExecutiveDashboard
              report={report}
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

      {/* ─────────────────────────────────────────────────────────────
          2. CRAWL EXPLORER TAB (PHASE 9)
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'discovery' && (
        <CrawlExplorerView
          report={report}
          onSelectFinding={onSelectFinding}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          LINK GRAPH EXPLORER TAB
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'linkgraph' && (
        <InternalLinkGraphView
          report={report}
          onSelectFinding={onSelectFinding}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          3. CRAWL & ARCHITECTURE TAB
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'architecture' && (
        <SeoCrawlArchitecture report={report} />
      )}

      {/* ─────────────────────────────────────────────────────────────
          4. ON-PAGE & SERP TAB
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'onpage' && (
        <SeoOnPageExperience report={report} />
      )}

      {/* ─────────────────────────────────────────────────────────────
          5. KEYWORD & CONTENT INTELLIGENCE TAB (PHASE 11)
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'intelligence' && (
        <SeoIntelligenceWorkspace
          report={report}
          onOpenConnectors={onOpenConnectors}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          6. LOCAL, GLOBAL & COMPETITORS TAB
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'market' && (
        <SeoMarketIntelligence report={report} />
      )}

      {/* ─────────────────────────────────────────────────────────────
          7. SEARCH CONSOLE TAB
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'gsc' && (
        <SearchConsoleAttributionView
          domain={report.domain}
          analysisId={analysisId}
          onOpenConnectors={() => onOpenConnectors?.('google_search_console')}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          INTEGRATIONS & CONNECTORS TAB (PHASE 14)
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'integrations' && (
        <SeoIntegrationsView />
      )}

      {/* ─────────────────────────────────────────────────────────────
          8. FINDINGS & REMEDIATION WORKSPACE TAB (PHASE 10)
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'issues' && (
        <SeoFindingsWorkspace
          report={report}
          seoFindings={seoFindings}
          onSelectFinding={onSelectFinding}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          9. FULL AUDIT INDEX
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'index' && (
        <AuditIndex report={report} />
      )}

      {/* ─────────────────────────────────────────────────────────────
          10. ENTERPRISE ASSESSMENT
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'enterprise' && (
        <EnterpriseSeoAudit
          analysisId={analysisId || report.analysis_id || report.report_id}
          report={report}
        />
      )}

      {/* ─────────────────────────────────────────────────────────────
          11. HISTORY & REGRESSION TRENDS
          ───────────────────────────────────────────────────────────── */}
      {activeTab === 'history' && <DeltaAnalyticsDashboard />}
    </PillarShell>
  );
}
