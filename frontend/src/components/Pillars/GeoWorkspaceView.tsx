import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ExecutiveReport, AiSearchQueryEvaluation, TabId, ControlledRetrievalReport } from '../../types';
import { RealAiCitationTracker } from '../RealAiCitationTracker';
import { GeoAeoTrendTracker } from '../GeoAeoTrendTracker';
import { GeoKpiAnalytics } from './GeoKpiAnalytics';
import { PillarShell, Card } from '../ui';
import { SectionExportButtons } from '../ui/SectionExportButtons';
import { ControlledRetrievalVisualizer } from './RagChunkVisualizer';
import { GeoAuditBook } from '../../report/geoIndex/GeoAuditBook';
import {
  GeoEnterpriseBundle,
  buildGeoBundleFromExecutiveReport,
  geoApi,
} from '../../services/geoApi';
import { GeoExecutiveDashboard } from './geo/GeoExecutiveDashboard';
import { GeoPromptWorkspace } from './geo/GeoPromptWorkspace';
import { GeoCitationWorkspace } from './geo/GeoCitationWorkspace';
import { GeoBrandContentWorkspace } from './geo/GeoBrandContentWorkspace';
import { GeoCompetitiveMarketWorkspace } from './geo/GeoCompetitiveMarketWorkspace';
import { GeoRemediationVerificationWorkspace } from './geo/GeoRemediationVerificationWorkspace';
import { GeoOpsReportsWorkspace } from './geo/GeoOpsReportsWorkspace';

interface GeoWorkspaceViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onOpenPatchPack?: () => void;
  onNavigateToTab?: (tab: TabId) => void;
  onEvaluationsUpdated?: (evals: AiSearchQueryEvaluation[]) => void;
}

type EnterpriseGeoTab =
  | 'overview'
  | 'platforms'
  | 'prompts'
  | 'prompt_lab'
  | 'visibility'
  | 'citations'
  | 'brand'
  | 'products'
  | 'content'
  | 'external_authority'
  | 'competitors'
  | 'markets'
  | 'findings'
  | 'recommendations'
  | 'remediation'
  | 'verification'
  | 'experiments'
  | 'monitoring'
  | 'history'
  | 'reports'
  | 'methodology'
  | 'connectors'
  | 'retrieval_lab'
  | 'audit_book';

export function GeoWorkspaceView({
  report,
  analysisId,
}: GeoWorkspaceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<EnterpriseGeoTab>('overview');
  const [liveBundle, setLiveBundle] = useState<GeoEnterpriseBundle | null>(null);

  // Controlled Retrieval Visualizer state (preserved legacy interactive tool)
  const [retrievalQuery, setRetrievalQuery] = useState(
    'What are the core capabilities, technical architecture, and pricing for this platform?',
  );
  const [retrievalLoading, setRetrievalLoading] = useState(false);
  const [retrievalReport, setRetrievalReport] = useState<ControlledRetrievalReport | null>(null);
  const [retrievalError, setRetrievalError] = useState<string | null>(null);

  const fallbackBundle = useMemo(
    () => buildGeoBundleFromExecutiveReport(report, analysisId),
    [report, analysisId],
  );
  const bundle = liveBundle || fallbackBundle;
  const domain = bundle.audit.domain;
  const brandName = bundle.audit.brand_name;

  const refreshBundle = useCallback(
    async (targetAuditId?: string) => {
      try {
        let aid = targetAuditId;
        if (!aid) {
          const listRes = await geoApi.listAudits(domain);
          aid = listRes.audits?.[0]?.audit_id;
        }
        if (aid) {
          const b = await geoApi.getBundle(aid);
          setLiveBundle({ ...b, is_live_geo_audit: true });
        }
      } catch {
        /* stay gracefully on zero-fabrication fallback bundle when unauthenticated or no GEO audit exists */
      }
    },
    [domain],
  );

  useEffect(() => {
    refreshBundle();
  }, [refreshBundle]);

  const handleRunControlledRetrieval = async () => {
    setRetrievalLoading(true);
    setRetrievalError(null);
    try {
      const pageText =
        report.crawl_manifest?.pages?.[0]?.body_text ||
        report.business_profile?.value_proposition ||
        '';
      if (!pageText.trim()) {
        setRetrievalError('No crawled page content available to analyze for this domain.');
        setRetrievalReport(null);
        return;
      }
      const res = await fetch('/api/v1/geo-pipeline/controlled-retrieval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page_text: pageText,
          query: retrievalQuery,
          source_url: `https://${domain}/`,
          chunk_size: 250,
          chunk_overlap: 40,
          similarity_threshold: 0.72,
          top_k: 3,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setRetrievalReport(await res.json());
    } catch (err: any) {
      setRetrievalError(err?.message || 'Failed to execute controlled retrieval analysis.');
    } finally {
      setRetrievalLoading(false);
    }
  };

  const readinessDisplay =
    bundle.scorecard.readiness_score != null ? Math.round(bundle.scorecard.readiness_score) : '—';
  const observedMeta =
    bundle.scorecard.observed_performance_score != null
      ? `${bundle.scorecard.observed_performance_score}/100`
      : bundle.scorecard.observed_performance_status;

  return (
    <PillarShell
      kicker="Enterprise Generative Engine Optimization"
      title="Generative Engine Optimization (GEO)"
      description="Measures observed AI mentions, recommendations, and citations separately from website readiness, entity consistency, and third-party authority—backed by consolidated remediation and independent verification."
      scoreLabel="GEO Readiness"
      score={readinessDisplay}
      metaLabel="Observed AI Visibility"
      meta={observedMeta}
      actions={
        <SectionExportButtons
          analysisId={analysisId || report.analysis_id || report.report_id}
          sectionKey="geo"
          sectionLabel="GEO"
        />
      }
      tabs={[
        { id: 'overview', label: 'Overview' },
        { id: 'platforms', label: 'AI Platforms' },
        { id: 'prompts', label: `Prompts (${bundle.prompts.length})` },
        { id: 'prompt_lab', label: 'Prompt Test Lab' },
        { id: 'visibility', label: 'Visibility Explorer' },
        { id: 'citations', label: `Citations (${bundle.citations.length})` },
        { id: 'brand', label: 'Brand & Entities' },
        { id: 'products', label: 'Products' },
        { id: 'content', label: 'Content Readiness' },
        { id: 'external_authority', label: 'External Authority' },
        { id: 'competitors', label: 'Competitors' },
        { id: 'markets', label: 'Markets & Lang' },
        { id: 'findings', label: `Findings (${bundle.findings.length})` },
        { id: 'recommendations', label: 'Recommendations' },
        { id: 'remediation', label: `Remediation (${bundle.remediation_pack?.tasks?.length || 0})` },
        { id: 'verification', label: 'Verification' },
        { id: 'experiments', label: 'Experiments' },
        { id: 'monitoring', label: 'Monitoring' },
        { id: 'history', label: 'History' },
        { id: 'reports', label: 'Reports (10 Profiles)' },
        { id: 'methodology', label: 'Methodology' },
        { id: 'connectors', label: 'Connectors' },
        { id: 'retrieval_lab', label: 'Retrieval Lab' },
        { id: 'audit_book', label: 'Full Audit Index' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as EnterpriseGeoTab)}
    >
      {(activeSubTab === 'overview' || activeSubTab === 'platforms') && (
        <GeoExecutiveDashboard
          bundle={bundle}
          domain={domain}
          websiteUrl={bundle.audit.website_url}
          onRefreshBundle={refreshBundle}
          onNavigateTab={(t) => setActiveSubTab(t as EnterpriseGeoTab)}
        />
      )}

      {(activeSubTab === 'prompts' || activeSubTab === 'prompt_lab') && (
        <GeoPromptWorkspace
          bundle={bundle}
          mode={activeSubTab}
          onRefreshBundle={refreshBundle}
        />
      )}

      {activeSubTab === 'visibility' && (
        <div className="space-y-6">
          <RealAiCitationTracker
            domain={domain}
            bizName={brandName}
            analysisId={analysisId}
            initialData={(report as any).ai_citation_dashboard}
          />
          <GeoAeoTrendTracker domain={domain} />
          <GeoKpiAnalytics domain={domain} />
        </div>
      )}

      {activeSubTab === 'citations' && <GeoCitationWorkspace bundle={bundle} />}

      {(activeSubTab === 'brand' || activeSubTab === 'products' || activeSubTab === 'content' || activeSubTab === 'external_authority') && (
        <GeoBrandContentWorkspace
          bundle={bundle}
          section={activeSubTab}
          onRefreshBundle={refreshBundle}
        />
      )}

      {(activeSubTab === 'competitors' || activeSubTab === 'markets') && (
        <GeoCompetitiveMarketWorkspace bundle={bundle} mode={activeSubTab} />
      )}

      {(activeSubTab === 'findings' || activeSubTab === 'recommendations' || activeSubTab === 'remediation' || activeSubTab === 'verification') && (
        <GeoRemediationVerificationWorkspace
          bundle={bundle}
          mode={activeSubTab}
          onRefreshBundle={refreshBundle}
        />
      )}

      {(activeSubTab === 'experiments' || activeSubTab === 'monitoring' || activeSubTab === 'history' || activeSubTab === 'reports' || activeSubTab === 'methodology' || activeSubTab === 'connectors') && (
        <GeoOpsReportsWorkspace
          bundle={bundle}
          mode={activeSubTab}
          onRefreshBundle={refreshBundle}
        />
      )}

      {activeSubTab === 'retrieval_lab' && (
        <Card className="p-5">
          <ControlledRetrievalVisualizer
            report={retrievalReport}
            loading={retrievalLoading}
            error={retrievalError}
            query={retrievalQuery}
            onQueryChange={setRetrievalQuery}
            onRunAnalysis={handleRunControlledRetrieval}
          />
        </Card>
      )}

      {activeSubTab === 'audit_book' && <GeoAuditBook report={report} />}
    </PillarShell>
  );
}
