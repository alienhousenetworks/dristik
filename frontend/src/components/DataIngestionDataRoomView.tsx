import React, { useMemo, useState } from 'react';
import {
  ConnectorType,
  ExecutiveReport,
  Finding,
  HypothesisMatrixItem,
  PageEvidence,
  TabId,
} from '../types';
import { PageHeader } from './ui';
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  FileCheck2,
  FlaskConical,
  Globe,
  Link2,
  Lock,
  Network,
  PlugZap,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react';

interface DataIngestionDataRoomViewProps {
  report: ExecutiveReport;
  analysisId?: string;
  onSelectTab: (tab: TabId) => void;
  onSelectFinding?: (finding: Finding) => void;
  onOpenConnectors?: (connectorTab?: ConnectorType) => void;
}

type DataRoomSubTab = 'corpus' | 'connectors' | 'provenance';

function buildFallbackHypothesesMatrix(report: ExecutiveReport): HypothesisMatrixItem[] {
  const items: HypothesisMatrixItem[] = [];
  const seen = new Set<string>();
  const gscState = report.google_performance?.search_console?.state;
  const ga4State = report.google_performance?.analytics?.state;

  const missingTel: string[] = [];
  if (gscState !== 'CONNECTED') missingTel.push('Google Search Console');
  if (ga4State !== 'CONNECTED') missingTel.push('Google Analytics 4');

  const addFindingAsHypothesis = (f: Finding, source: string) => {
    const id = f.finding_id || (f as any).audit_id || `hyp_${items.length + 1}`;
    if (seen.has(id)) return;
    seen.add(id);
    const conf = Math.round(((typeof f.confidence === 'number' ? f.confidence : 0.45) + Number.EPSILON) * 100) / 100;
    const domain = String(f.category || 'GENERAL').toUpperCase();
    items.push({
      id,
      statement: f.title || f.description || 'Exploratory hypothesis',
      domain,
      source,
      prior_probability: 0.5,
      posterior_confidence: conf,
      confidence_delta: Math.round((conf - 0.5) * 100) / 100,
      status: conf >= 0.7 ? 'validated' : conf <= 0.3 ? 'falsified' : 'inconclusive',
      supporting_evidence_refs: f.evidence_refs || [],
      contradicting_evidence_refs: [],
      supporting_summaries: f.description ? [f.description] : [],
      contradicting_summaries: [],
      required_telemetry: missingTel.length > 0 ? missingTel : ['SME Verification'],
      recommended_action: f.recommendation || (f as any).verification_method || null,
    });
  };

  for (const f of report.exploratory_hypotheses || []) {
    addFindingAsHypothesis(f, 'exploratory_finding');
  }

  for (const f of report.findings || []) {
    const isHyp =
      f.evidence_class === 'HYPOTHESIS' ||
      f.confidence_label === 'GUESSING' ||
      (f as any).root_cause_status === 'hypothesized';
    if (isHyp) addFindingAsHypothesis(f, 'exploratory_finding');
  }

  for (const c of report.contradictions || []) {
    const id = c.id || `contra_${items.length + 1}`;
    if (seen.has(id)) continue;
    seen.add(id);
    const conf = Math.round(((typeof c.confidence === 'number' ? c.confidence : 0.5) + Number.EPSILON) * 100) / 100;
    items.push({
      id,
      statement: c.reason || `Declared (${c.declared_type || 'unknown'}) vs detected (${c.detected_type || 'unknown'})`,
      domain: 'ENTITY_TRUST',
      source: 'contradiction',
      prior_probability: 0.5,
      posterior_confidence: conf,
      confidence_delta: Math.round((conf - 0.5) * 100) / 100,
      status: conf >= 0.7 ? 'validated' : conf <= 0.3 ? 'falsified' : 'inconclusive',
      supporting_evidence_refs: (c.evidence || []).map((e) => e.url).filter((u): u is string => Boolean(u)),
      contradicting_evidence_refs: [],
      supporting_summaries: c.reason ? [c.reason] : [],
      contradicting_summaries: [],
      required_telemetry: ['Canonical Entity Schema', 'Declared Business Profile'],
      recommended_action: 'Reconcile declared business identity with on-page Schema.org and copy.',
    });
  }

  return items;
}

function statusPillClass(status: string): string {
  switch (status.toLowerCase()) {
    case 'validated':
      return 'bg-good/10 text-good border-good/30';
    case 'falsified':
      return 'bg-bad/10 text-bad border-bad/30';
    case 'inconclusive':
      return 'bg-warn/10 text-warn border-warn/30';
    default:
      return 'bg-paper-200 text-ink-600 border-line';
  }
}

function connectorBadge(state?: string): { label: string; cls: string; ok: boolean } {
  const normalized = (state || 'NOT_CONNECTED').toUpperCase();
  if (normalized === 'CONNECTED' || normalized === 'ATTACHED' || normalized === 'VERIFIED') {
    return { label: normalized, cls: 'bg-good/10 text-good border-good/30', ok: true };
  }
  if (normalized === 'DEGRADED' || normalized === 'PARTIAL') {
    return { label: normalized, cls: 'bg-warn/10 text-warn border-warn/30', ok: false };
  }
  return { label: normalized.replace(/_/g, ' '), cls: 'bg-paper-200 text-ink-500 border-line', ok: false };
}

export function DataIngestionDataRoomView({
  report,
  onSelectTab,
  onOpenConnectors,
}: DataIngestionDataRoomViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<DataRoomSubTab>('corpus');
  const [urlSearch, setUrlSearch] = useState('');
  const [showRobotsRaw, setShowRobotsRaw] = useState(false);

  // Hypotheses Matrix filters
  const [hypSearch, setHypSearch] = useState('');
  const [hypDomainFilter, setHypDomainFilter] = useState<string>('ALL');
  const [hypStatusFilter, setHypStatusFilter] = useState<string>('ALL');
  const [expandedHypId, setExpandedHypId] = useState<string | null>(null);

  const manifest = report.crawl_manifest;
  const pages: PageEvidence[] = (manifest?.pages && manifest.pages.length > 0)
    ? manifest.pages
    : ((report.page_reports as unknown as PageEvidence[]) || []);
  const crawlSummary = (report.crawl_summary || {}) as Record<string, unknown>;
  const crawlHealth = (manifest?.crawl_health || {}) as Record<string, unknown>;

  const totalDomElements = useMemo(
    () => pages.reduce((acc, p) => acc + (Number(p.dom_elements_count) || 0), 0),
    [pages]
  );
  const totalWords = useMemo(() => {
    const fromSummary = Number(crawlSummary.total_words);
    if (Number.isFinite(fromSummary) && fromSummary > 0) return fromSummary;
    return pages.reduce((acc, p) => acc + (Number(p.word_count) || 0), 0);
  }, [crawlSummary.total_words, pages]);

  const uniqueSchemas = useMemo(() => {
    const set = new Set<string>();
    pages.forEach((p) => (p.schema_types || []).forEach((s) => set.add(s)));
    return Array.from(set).sort();
  }, [pages]);

  const gscState = report.google_performance?.search_console?.state || 'NOT_CONNECTED';
  const ga4State = report.google_performance?.analytics?.state || 'NOT_CONNECTED';
  const extAttached = Boolean(report.external_authority);
  const crmAttached = Boolean(report.lifecycle_revenue);
  const connectedCount =
    (gscState === 'CONNECTED' ? 1 : 0) +
    (ga4State === 'CONNECTED' ? 1 : 0) +
    (extAttached ? 1 : 0) +
    (crmAttached ? 1 : 0);

  const evidenceNodes = Number(crawlSummary.evidence_graph_nodes ?? 0);
  const evidenceEdges = Number(crawlSummary.evidence_graph_edges ?? 0);
  const shaVerifiedNodes = Number(crawlSummary.sha256_verified_nodes ?? 0);
  const domSelectorsCount = Number(crawlSummary.dom_selectors_count ?? 0);
  const claimsCount = (report.claims || []).length;

  const ledgerBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    const ledger = report.evidence_ledger || {};
    Object.values(ledger).forEach((item) => {
      const cls = String((item as any)?.evidence_class || (item as any)?.classification || 'UNCLASSIFIED');
      counts[cls] = (counts[cls] || 0) + 1;
    });
    return counts;
  }, [report.evidence_ledger]);

  const filteredPages = useMemo(() => {
    const q = urlSearch.trim().toLowerCase();
    if (!q) return pages;
    return pages.filter(
      (p) =>
        (p.url || '').toLowerCase().includes(q) ||
        (p.title || '').toLowerCase().includes(q) ||
        (p.page_type || '').toLowerCase().includes(q)
    );
  }, [pages, urlSearch]);

  // Hypotheses Matrix data
  const matrixItems = useMemo<HypothesisMatrixItem[]>(() => {
    if (report.hypotheses_matrix && report.hypotheses_matrix.length > 0) {
      return report.hypotheses_matrix;
    }
    return buildFallbackHypothesesMatrix(report);
  }, [report]);

  const hypDomains = useMemo(() => {
    const set = new Set<string>(['ALL']);
    matrixItems.forEach((h) => set.add(h.domain.toUpperCase()));
    return Array.from(set);
  }, [matrixItems]);

  const hypCounts = useMemo(() => {
    const summary = { total: matrixItems.length, validated: 0, inconclusive: 0, falsified: 0, untested: 0 };
    matrixItems.forEach((h) => {
      const st = h.status.toLowerCase();
      if (st === 'validated') summary.validated += 1;
      else if (st === 'falsified') summary.falsified += 1;
      else if (st === 'inconclusive') summary.inconclusive += 1;
      else summary.untested += 1;
    });
    return summary;
  }, [matrixItems]);

  const filteredHypotheses = useMemo(() => {
    const q = hypSearch.trim().toLowerCase();
    return matrixItems.filter((h) => {
      if (hypDomainFilter !== 'ALL' && h.domain.toUpperCase() !== hypDomainFilter) return false;
      if (hypStatusFilter !== 'ALL' && h.status.toLowerCase() !== hypStatusFilter) return false;
      if (q && !h.statement.toLowerCase().includes(q) && !h.id.toLowerCase().includes(q) && !h.domain.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [matrixItems, hypSearch, hypDomainFilter, hypStatusFilter]);

  const avgTtfb = typeof crawlHealth.avg_ttfb_ms === 'number'
    ? Math.round(crawlHealth.avg_ttfb_ms)
    : typeof crawlSummary.avg_ttfb_ms === 'number'
      ? Math.round(Number(crawlSummary.avg_ttfb_ms))
      : null;

  const llmsTxtFound = typeof (manifest as any)?.llms_txt_found === 'boolean'
    ? Boolean((manifest as any).llms_txt_found)
    : null;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Data Ingestion & Provenance"
        title="Enterprise Data Room & Hypotheses Matrix"
        description="Complete audit inventory of ingested crawl corpus, external telemetry connectors, cryptographic evidence provenance, and falsifiable hypotheses evaluated against accumulated evidence."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {report.certification_status && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold border border-line bg-paper-100 text-ink-700">
                <Lock className="w-3.5 h-3.5 text-pine" />
                {report.certification_status}
              </span>
            )}
            <button
              type="button"
              onClick={() => onSelectTab('pages')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-line bg-paper-50 hover:bg-paper-100 text-ink transition-colors"
            >
              <Globe className="w-3.5 h-3.5 text-pine" />
              Page Inspector
            </button>
            <button
              type="button"
              onClick={() => onSelectTab('findings')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-line bg-paper-50 hover:bg-paper-100 text-ink transition-colors"
            >
              <FileCheck2 className="w-3.5 h-3.5 text-pine" />
              Evidence Ledger
            </button>
          </div>
        }
      />

      {/* Section 1: Data Room KPI & Provenance Strip */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="card p-4">
          <div className="text-[11px] font-mono uppercase text-ink-500">Pages Ingested</div>
          <div className="text-2xl font-bold text-ink mt-1">{pages.length}</div>
          <div className="text-[11px] text-ink-400 mt-0.5">
            {manifest?.total_pages_discovered ? `of ${manifest.total_pages_discovered} discovered` : 'Crawl manifest'}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-[11px] font-mono uppercase text-ink-500">Words & DOM</div>
          <div className="text-2xl font-bold text-ink mt-1">{totalWords.toLocaleString()}</div>
          <div className="text-[11px] text-ink-400 mt-0.5">
            {totalDomElements > 0 ? `${totalDomElements.toLocaleString()} DOM nodes` : `${uniqueSchemas.length} schema types`}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-[11px] font-mono uppercase text-ink-500">SHA-256 Verified</div>
          <div className="text-2xl font-bold text-pine mt-1">{shaVerifiedNodes}</div>
          <div className="text-[11px] text-ink-400 mt-0.5">{evidenceNodes} evidence nodes</div>
        </div>
        <div className="card p-4">
          <div className="text-[11px] font-mono uppercase text-ink-500">External Sources</div>
          <div className="text-2xl font-bold text-ink mt-1">{connectedCount} / 4</div>
          <div className="text-[11px] text-ink-400 mt-0.5">GSC, GA4, Authority, CRM</div>
        </div>
        <div className="card p-4">
          <div className="text-[11px] font-mono uppercase text-ink-500">Verified Claims</div>
          <div className="text-2xl font-bold text-ink mt-1">{claimsCount}</div>
          <div className="text-[11px] text-ink-400 mt-0.5">{(report.findings || []).length} synthesized findings</div>
        </div>
        <div className="card p-4">
          <div className="text-[11px] font-mono uppercase text-ink-500">Snapshot Seal</div>
          <div className="text-xs font-mono font-semibold text-ink mt-1.5 truncate" title={report.sealed_evidence_snapshot_id || report.manifest_id || 'Unsealed'}>
            {report.sealed_evidence_snapshot_id || report.manifest_id || 'Not sealed'}
          </div>
          <div className="text-[11px] text-ink-400 mt-1">Policy: {report.policy_pack || 'enterprise_v4'}</div>
        </div>
      </section>

      {/* Section 2: Ingested Data Room Inventory */}
      <section className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-line flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-paper-50">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-pine font-semibold">
              <Database className="w-3.5 h-3.5" />
              Ingested Data Room
            </div>
            <h3 className="text-base font-bold text-ink mt-0.5">
              Source-by-source ingestion ledger
            </h3>
          </div>

          <div className="inline-flex rounded-lg border border-line bg-paper-100 p-1">
            {([
              { id: 'corpus', label: `Crawled Corpus (${pages.length})` },
              { id: 'connectors', label: `Connectors (${connectedCount}/4)` },
              { id: 'provenance', label: `Evidence Graph (${evidenceNodes})` },
            ] as Array<{ id: DataRoomSubTab; label: string }>).map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveSubTab(item.id)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                  activeSubTab === item.id
                    ? 'bg-paper-50 text-ink shadow-xs border border-line'
                    : 'text-ink-500 hover:text-ink'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sub-tab A: Crawled Corpus & Technical Manifest */}
        {activeSubTab === 'corpus' && (
          <div className="p-5 space-y-5">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono text-ink-500 uppercase">robots.txt</div>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-xs font-bold text-ink flex items-center gap-1">
                    {manifest?.robots_txt_found ? (
                      <><CheckCircle2 className="w-3.5 h-3.5 text-good" /> Ingested</>
                    ) : (
                      <><XCircle className="w-3.5 h-3.5 text-bad" /> Missing</>
                    )}
                  </span>
                  {manifest?.robots_txt_content && (
                    <button
                      type="button"
                      onClick={() => setShowRobotsRaw((v) => !v)}
                      className="text-[11px] text-pine underline font-mono"
                    >
                      {showRobotsRaw ? 'Hide' : 'View'}
                    </button>
                  )}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono text-ink-500 uppercase">XML Sitemap</div>
                <div className="mt-1 text-xs font-bold text-ink flex items-center gap-1">
                  {manifest?.sitemap_found ? (
                    <><CheckCircle2 className="w-3.5 h-3.5 text-good" /> Ingested</>
                  ) : (
                    <><XCircle className="w-3.5 h-3.5 text-bad" /> Missing</>
                  )}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono text-ink-500 uppercase">/llms.txt</div>
                <div className="mt-1 text-xs font-bold text-ink flex items-center gap-1">
                  {llmsTxtFound === true ? (
                    <><CheckCircle2 className="w-3.5 h-3.5 text-good" /> Ingested</>
                  ) : llmsTxtFound === false ? (
                    <><XCircle className="w-3.5 h-3.5 text-warn" /> Missing</>
                  ) : (
                    <span className="text-ink-400">Not checked</span>
                  )}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono text-ink-500 uppercase">Avg TTFB</div>
                <div className="mt-1 text-xs font-mono font-bold text-ink">
                  {avgTtfb != null ? `${avgTtfb} ms` : '—'}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono text-ink-500 uppercase">Schemas Detected</div>
                <div className="mt-1 text-xs font-mono font-bold text-ink">
                  {uniqueSchemas.length > 0 ? `${uniqueSchemas.length} types` : 'None'}
                </div>
              </div>
            </div>

            {showRobotsRaw && manifest?.robots_txt_content && (
              <pre className="p-3 rounded-lg border border-line bg-paper-100 text-[11px] font-mono text-ink-700 overflow-x-auto max-h-48">
                {manifest.robots_txt_content}
              </pre>
            )}

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="text-xs font-semibold text-ink">
                Ingested URL Corpus ({filteredPages.length})
              </div>
              <div className="relative w-full sm:w-72">
                <Search className="w-3.5 h-3.5 text-ink-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={urlSearch}
                  onChange={(e) => setUrlSearch(e.target.value)}
                  placeholder="Filter ingested URLs, titles, or page types..."
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-paper-50 border border-line rounded-lg text-ink focus:outline-none focus:ring-1 focus:ring-pine"
                />
              </div>
            </div>

            <div className="overflow-x-auto border border-line rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-paper-50 border-b border-line text-ink-500 uppercase font-mono text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">URL</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Words</th>
                    <th className="py-2.5 px-3">TTFB</th>
                    <th className="py-2.5 px-3">Schemas</th>
                    <th className="py-2.5 px-3">Canonical</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {filteredPages.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-ink-500">
                        No ingested pages match your filter.
                      </td>
                    </tr>
                  ) : (
                    filteredPages.slice(0, 50).map((p, idx) => {
                      const ok = (p.status_code || 200) < 400;
                      return (
                        <tr key={p.url || idx} className="hover:bg-paper-50/80 transition-colors">
                          <td className="py-2 px-3 font-mono text-ink max-w-xs truncate" title={p.url}>
                            <a
                              href={p.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 hover:text-pine"
                            >
                              {(p.url || '').replace(/^https?:\/\/[^/]+/, '') || '/'}
                              <ArrowUpRight className="w-3 h-3 opacity-60 shrink-0" />
                            </a>
                          </td>
                          <td className="py-2 px-3">
                            <span className={`px-1.5 py-0.5 rounded font-mono text-[11px] font-bold ${ok ? 'bg-good/10 text-good' : 'bg-bad/10 text-bad'}`}>
                              {p.status_code || 200}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-mono text-[11px] text-ink-500">
                            {p.page_type || 'page'}
                          </td>
                          <td className="py-2 px-3 font-mono text-ink">
                            {(p.word_count || 0).toLocaleString()}
                          </td>
                          <td className="py-2 px-3 font-mono text-ink-500">
                            {p.ttfb_ms ? `${Math.round(p.ttfb_ms)}ms` : '—'}
                          </td>
                          <td className="py-2 px-3 text-[11px] text-ink-600 max-w-[180px] truncate" title={(p.schema_types || []).join(', ')}>
                            {(p.schema_types || []).length > 0 ? p.schema_types.join(', ') : '—'}
                          </td>
                          <td className="py-2 px-3 font-mono text-[11px]">
                            {p.canonical_url ? (
                              <span className="text-good">Present</span>
                            ) : (
                              <span className="text-warn">Missing</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
            {filteredPages.length > 50 && (
              <div className="text-[11px] text-ink-500 flex items-center justify-between">
                <span>Showing first 50 of {filteredPages.length} ingested pages.</span>
                <button type="button" onClick={() => onSelectTab('pages')} className="text-pine underline font-semibold">
                  Inspect all pages in Page Inspector
                </button>
              </div>
            )}
          </div>
        )}

        {/* Sub-tab B: External Connectors & Telemetry */}
        {activeSubTab === 'connectors' && (
          <div className="p-5 grid gap-4 md:grid-cols-2">
            {[
              {
                key: 'google_search_console' as ConnectorType,
                title: 'Google Search Console (GSC)',
                state: gscState,
                detail: gscState === 'CONNECTED'
                  ? `Search queries, impressions, CTR, and average position ingested.`
                  : 'Not connected. Search query & indexation telemetry is currently unmeasured.',
              },
              {
                key: 'google_analytics_4' as ConnectorType,
                title: 'Google Analytics 4 (GA4)',
                state: ga4State,
                detail: ga4State === 'CONNECTED'
                  ? 'Landing page sessions, bounce rates, and conversion funnel events ingested.'
                  : 'Not connected. Conversion and dwell-time hypotheses remain unverified by first-party analytics.',
              },
              {
                key: 'dataforseo' as ConnectorType,
                title: 'External Authority (DNS / SSL / CrUX / SERP)',
                state: extAttached ? 'ATTACHED' : 'NOT_CONNECTED',
                detail: extAttached
                  ? 'External domain authority, DNS/SSL transport signals, and entity corroboration attached.'
                  : 'External authority enrichment not attached to this audit run.',
              },
              {
                key: 'crm' as ConnectorType,
                title: 'CRM & Lifecycle Revenue',
                state: crmAttached ? 'ATTACHED' : 'NOT_CONNECTED',
                detail: crmAttached
                  ? 'Pipeline attribution and lifecycle revenue signals ingested.'
                  : 'CRM pipeline attribution not connected.',
              },
            ].map((conn) => {
              const badge = connectorBadge(conn.state);
              return (
                <div key={conn.key} className="p-4 rounded-xl border border-line bg-paper-50 flex flex-col justify-between gap-3">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 font-semibold text-sm text-ink">
                        <PlugZap className="w-4 h-4 text-pine shrink-0" />
                        {conn.title}
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </div>
                    <p className="text-xs text-ink-500 leading-relaxed">{conn.detail}</p>
                  </div>
                  {!badge.ok && onOpenConnectors && (
                    <div>
                      <button
                        type="button"
                        onClick={() => onOpenConnectors(conn.key)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-pine text-white hover:bg-pine-700 transition-colors"
                      >
                        <Link2 className="w-3.5 h-3.5" />
                        Connect {conn.title.split(' ')[0]}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Sub-tab C: Evidence Graph & Cryptographic Provenance */}
        {activeSubTab === 'provenance' && (
          <div className="p-5 space-y-5">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono uppercase text-ink-500">Graph Nodes</div>
                <div className="text-xl font-bold text-ink mt-1">{evidenceNodes}</div>
              </div>
              <div className="p-3.5 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono uppercase text-ink-500">Graph Edges</div>
                <div className="text-xl font-bold text-ink mt-1">{evidenceEdges}</div>
              </div>
              <div className="p-3.5 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono uppercase text-ink-500">SHA-256 Sealed</div>
                <div className="text-xl font-bold text-pine mt-1">{shaVerifiedNodes}</div>
              </div>
              <div className="p-3.5 rounded-lg border border-line bg-paper-50">
                <div className="text-[11px] font-mono uppercase text-ink-500">DOM Selectors</div>
                <div className="text-xl font-bold text-ink mt-1">{domSelectorsCount}</div>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-line bg-paper-50 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                  <Network className="w-4 h-4 text-pine" />
                  Evidence Ledger Classification Breakdown
                </div>
                <button
                  type="button"
                  onClick={() => onSelectTab('findings')}
                  className="text-xs font-semibold text-pine underline"
                >
                  Open full Evidence Ledger
                </button>
              </div>
              {Object.keys(ledgerBreakdown).length === 0 ? (
                <p className="text-xs text-ink-500">
                  No structured evidence ledger entries recorded on this report snapshot.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(ledgerBreakdown).map(([cls, count]) => (
                    <span
                      key={cls}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-line bg-paper-100 text-xs font-mono text-ink"
                    >
                      <span>{cls}</span>
                      <span className="font-bold text-pine">{count}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Section 3: Enterprise Hypotheses Matrix */}
      <section className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-line bg-paper-50 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-pine font-semibold">
                <FlaskConical className="w-3.5 h-3.5" />
                Bayesian & Exploratory Verification
              </div>
              <h3 className="text-lg font-bold text-ink mt-0.5">
                Enterprise Hypotheses Matrix
              </h3>
              <p className="text-xs text-ink-500 mt-0.5 max-w-2xl">
                Falsifiable growth hypotheses tracked from initial prior probability through evidence-weighted posterior confidence. Unverified hypotheses are gated from executive scoring until corroborated.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono border border-line bg-paper-100 text-ink">
                Total: <strong>{hypCounts.total}</strong>
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono border border-good/30 bg-good/10 text-good">
                Validated: <strong>{hypCounts.validated}</strong>
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono border border-warn/30 bg-warn/10 text-warn">
                Inconclusive: <strong>{hypCounts.inconclusive}</strong>
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-mono border border-bad/30 bg-bad/10 text-bad">
                Falsified: <strong>{hypCounts.falsified}</strong>
              </span>
            </div>
          </div>

          {/* Matrix Filter Controls */}
          <div className="flex flex-col sm:flex-row gap-2.5">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-ink-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={hypSearch}
                onChange={(e) => setHypSearch(e.target.value)}
                placeholder="Search hypotheses by statement, ID, or domain..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-paper-100 border border-line rounded-lg text-ink focus:outline-none focus:ring-1 focus:ring-pine"
              />
            </div>
            <select
              aria-label="Filter by domain"
              value={hypDomainFilter}
              onChange={(e) => setHypDomainFilter(e.target.value)}
              className="px-3 py-1.5 text-xs bg-paper-100 border border-line rounded-lg text-ink"
            >
              {hypDomains.map((d) => (
                <option key={d} value={d}>
                  {d === 'ALL' ? 'All Domains' : d}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by status"
              value={hypStatusFilter}
              onChange={(e) => setHypStatusFilter(e.target.value)}
              className="px-3 py-1.5 text-xs bg-paper-100 border border-line rounded-lg text-ink"
            >
              <option value="ALL">All Statuses</option>
              <option value="validated">Validated (&ge;70%)</option>
              <option value="inconclusive">Inconclusive (31–69%)</option>
              <option value="falsified">Falsified (&le;30%)</option>
              <option value="untested">Untested</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-paper-50 border-b border-line text-ink-500 uppercase font-mono text-[11px]">
              <tr>
                <th className="py-3 px-4 w-8"></th>
                <th className="py-3 px-3">ID & Domain</th>
                <th className="py-3 px-4">Falsifiable Hypothesis</th>
                <th className="py-3 px-3">Prior &rarr; Posterior</th>
                <th className="py-3 px-3">Evidence Balance</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4">Verification Gate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filteredHypotheses.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-ink-500">
                    No hypotheses match the current filters.
                  </td>
                </tr>
              ) : (
                filteredHypotheses.map((h) => {
                  const isExpanded = expandedHypId === h.id;
                  const priorPct = Math.round(h.prior_probability * 100);
                  const postPct = Math.round(h.posterior_confidence * 100);
                  const deltaPct = Math.round(h.confidence_delta * 100);
                  const supportCount = h.supporting_evidence_refs.length;
                  const contraCount = h.contradicting_evidence_refs.length;

                  return (
                    <React.Fragment key={h.id}>
                      <tr
                        onClick={() => setExpandedHypId(isExpanded ? null : h.id)}
                        className="hover:bg-paper-50 cursor-pointer transition-colors"
                      >
                        <td className="py-3 px-4 text-ink-400">
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </td>
                        <td className="py-3 px-3 align-top">
                          <div className="font-mono text-[11px] font-semibold text-ink">{h.id}</div>
                          <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-paper-200 text-ink-700 border border-line">
                            {h.domain}
                          </span>
                        </td>
                        <td className="py-3 px-4 align-top max-w-md">
                          <p className="text-ink font-medium leading-snug">{h.statement}</p>
                          <span className="text-[10px] font-mono text-ink-400 mt-1 inline-block">
                            Source: {h.source.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-3 align-top min-w-[160px]">
                          <div className="flex items-center justify-between font-mono text-[11px]">
                            <span className="text-ink-500">{priorPct}% &rarr; <strong className="text-ink">{postPct}%</strong></span>
                            <span className={deltaPct > 0 ? 'text-good font-semibold' : deltaPct < 0 ? 'text-bad font-semibold' : 'text-ink-400'}>
                              {deltaPct > 0 ? `+${deltaPct}%` : `${deltaPct}%`}
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-paper-200 rounded-full overflow-hidden mt-1.5">
                            <div
                              className={`h-full rounded-full ${
                                postPct >= 70 ? 'bg-good' : postPct <= 30 ? 'bg-bad' : 'bg-warn'
                              }`}
                              style={{ width: `${Math.max(4, Math.min(100, postPct))}%` }}
                            />
                          </div>
                        </td>
                        <td className="py-3 px-3 align-top">
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            <span className="px-1.5 py-0.5 rounded bg-good/10 text-good border border-good/20">
                              +{supportCount}
                            </span>
                            <span className="px-1.5 py-0.5 rounded bg-bad/10 text-bad border border-bad/20">
                              -{contraCount}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-3 align-top">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase border ${statusPillClass(h.status)}`}>
                            {h.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 align-top">
                          <div className="flex flex-wrap gap-1">
                            {(h.required_telemetry || []).map((tel) => (
                              <span
                                key={tel}
                                className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-paper-100 border border-line text-ink-600"
                              >
                                {tel}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="bg-paper-50/70">
                          <td colSpan={7} className="px-6 py-4 border-t border-line/60">
                            <div className="grid gap-4 md:grid-cols-3 text-xs">
                              <div className="space-y-1.5">
                                <div className="font-mono text-[11px] uppercase text-good font-semibold flex items-center gap-1">
                                  <ShieldCheck className="w-3.5 h-3.5" />
                                  Supporting Evidence ({supportCount})
                                </div>
                                {(h.supporting_summaries || []).length > 0 ? (
                                  <ul className="list-disc pl-4 space-y-1 text-ink-700">
                                    {h.supporting_summaries!.map((s, idx) => (
                                      <li key={idx}>{s}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-ink-400">No supporting claims linked yet.</p>
                                )}
                              </div>

                              <div className="space-y-1.5">
                                <div className="font-mono text-[11px] uppercase text-bad font-semibold flex items-center gap-1">
                                  <ShieldAlert className="w-3.5 h-3.5" />
                                  Contradicting Evidence ({contraCount})
                                </div>
                                {(h.contradicting_summaries || []).length > 0 ? (
                                  <ul className="list-disc pl-4 space-y-1 text-ink-700">
                                    {h.contradicting_summaries!.map((s, idx) => (
                                      <li key={idx}>{s}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-ink-400">No contradicting claims recorded.</p>
                                )}
                              </div>

                              <div className="space-y-1.5">
                                <div className="font-mono text-[11px] uppercase text-pine font-semibold flex items-center gap-1">
                                  <Sparkles className="w-3.5 h-3.5" />
                                  Recommended Experiment / Action
                                </div>
                                <p className="text-ink-700 leading-relaxed">
                                  {h.recommended_action || 'Attach required first-party telemetry or run targeted remediation experiment to confirm.'}
                                </p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
