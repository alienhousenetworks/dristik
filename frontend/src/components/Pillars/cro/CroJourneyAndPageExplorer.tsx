import React, { useMemo, useState } from 'react';
import { Card } from '../../ui';
import { CroEnterpriseBundle, CroPageRecord } from '../../../services/croApi';
import { ArrowRight, CheckCircle2, AlertTriangle, HelpCircle, Layers, Search } from 'lucide-react';

interface CroJourneyAndPageExplorerProps {
  bundle: CroEnterpriseBundle;
  mode: 'journeys' | 'pages';
}

const PAGE_DETAIL_TABS = [
  'overview',
  'screenshot',
  'raw_html',
  'rendered_dom',
  'elements',
  'ctas',
  'forms',
  'ux',
  'ui',
  'analytics',
  'performance',
  'recommendations',
  'remediation',
  'history',
] as const;

export function CroJourneyAndPageExplorer({ bundle, mode }: CroJourneyAndPageExplorerProps) {
  const [deviceFilter, setDeviceFilter] = useState<'all' | 'desktop' | 'mobile'>('all');
  const [pageSearch, setPageSearch] = useState('');
  const [pageTypeFilter, setPageTypeFilter] = useState('all');
  const [selectedPageId, setSelectedPageId] = useState<string | null>(bundle.pages[0]?.page_id || null);
  const [detailTab, setDetailTab] = useState<(typeof PAGE_DETAIL_TABS)[number]>('overview');

  const filteredPages = useMemo(() => {
    return bundle.pages.filter((p) => {
      if (pageTypeFilter !== 'all' && p.page_type !== pageTypeFilter) return false;
      if (pageSearch && !p.url.toLowerCase().includes(pageSearch.toLowerCase()) && !(p.title || '').toLowerCase().includes(pageSearch.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [bundle.pages, pageSearch, pageTypeFilter]);

  const selectedPage: CroPageRecord | undefined =
    filteredPages.find((p) => p.page_id === selectedPageId) || filteredPages[0];

  if (mode === 'journeys') {
    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-ink">Conversion Journey Explorer</h3>
            <p className="text-xs text-ink-600 mt-0.5">
              Every journey step reports two strictly separated statuses: <strong>Technical Status</strong> (tested functionality) vs <strong>Behavioral Status</strong> (real visitor analytics).
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            {(['all', 'desktop', 'mobile'] as const).map((dev) => (
              <button
                key={dev}
                type="button"
                onClick={() => setDeviceFilter(dev)}
                className={`px-2.5 py-1 text-xs rounded-md border ${
                  deviceFilter === dev ? 'bg-ink text-white border-ink' : 'border-line text-ink-600'
                }`}
              >
                {dev === 'all' ? 'All Devices' : dev.charAt(0).toUpperCase() + dev.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {bundle.journeys.length === 0 ? (
          <Card className="p-6 text-sm text-ink-500">
            No conversion journeys mapped yet. Run an Enterprise CRO Audit to discover entry points and step dependencies.
          </Card>
        ) : (
          bundle.journeys.map((journey) => (
            <Card key={journey.journey_id} className="p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                <div>
                  <h4 className="text-sm font-bold text-ink">{journey.name}</h4>
                  <p className="text-xs text-ink-500">
                    Model: {journey.business_model} · Entry points: {journey.entry_points.join(', ') || 'None'}
                  </p>
                </div>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-paper-200 text-ink">
                    Technical: {journey.technical_health.toUpperCase()}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-700">
                    Behavioral: {journey.behavioral_health.toUpperCase()}
                    {journey.measured_completion_rate != null ? ` (${journey.measured_completion_rate}%)` : ''}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {journey.steps.map((step) => (
                  <div key={step.step_id} className="rounded-lg border border-line p-3.5 bg-paper-50 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-bold text-ink-500">
                        STEP {String(step.step_order).padStart(2, '0')} · {step.stage.toUpperCase()}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-ink-400" />
                    </div>
                    <p className="text-sm font-bold text-ink">{step.name}</p>
                    <p className="text-xs text-ink-600">{step.expected_interaction}</p>
                    {step.url && <p className="text-[11px] font-mono text-ink-500 truncate">{step.url}</p>}

                    <div className="pt-2 border-t border-line space-y-1.5">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-ink-600">Technical status</span>
                        <span
                          className={`inline-flex items-center gap-1 font-mono font-semibold ${
                            step.technical_status === 'passed'
                              ? 'text-good'
                              : step.technical_status === 'failed'
                              ? 'text-bad'
                              : 'text-warn'
                          }`}
                        >
                          {step.technical_status === 'passed' ? (
                            <CheckCircle2 className="w-3 h-3" />
                          ) : (
                            <AlertTriangle className="w-3 h-3" />
                          )}
                          {step.technical_status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-ink-600">Behavioral status</span>
                        <span
                          className={`inline-flex items-center gap-1 font-mono font-semibold ${
                            step.behavioral_status === 'measured_healthy'
                              ? 'text-good'
                              : step.behavioral_status === 'measured_high_dropoff'
                              ? 'text-bad'
                              : 'text-ink-500'
                          }`}
                        >
                          <HelpCircle className="w-3 h-3" />
                          {step.behavioral_status.replace(/_/g, ' ')}
                        </span>
                      </div>
                      {step.behavioral_metrics?.step_abandonment_rate_pct != null && (
                        <p className="text-[11px] font-mono text-bad">
                          Measured drop-off: {step.behavioral_metrics.step_abandonment_rate_pct}% ({step.behavioral_metrics.progressing_users}/{step.behavioral_metrics.eligible_users} users)
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-ink-500 italic">{journey.disclosure}</p>
            </Card>
          ))
        )}
      </div>
    );
  }

  // Phase 29: Page & Component CRO Explorer (14-tab detail view)
  const pageTypes = Array.from(new Set(bundle.pages.map((p) => p.page_type)));
  const pageFindings = selectedPage
    ? bundle.findings.filter((f) => f.affected_urls.includes(selectedPage.url))
    : [];
  const pageCtas = selectedPage ? bundle.ctas.filter((c) => c.url === selectedPage.url) : [];
  const pageForms = selectedPage ? bundle.forms.filter((f) => f.url === selectedPage.url) : [];
  const pageTasks = selectedPage
    ? (bundle.remediation_pack?.tasks || []).filter((t) => t.affected_urls.includes(selectedPage.url))
    : [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-ink flex items-center gap-2">
            <Layers className="w-4 h-4" /> Page &amp; Component CRO Inspector ({bundle.pages.length} Pages)
          </h3>
          <p className="text-xs text-ink-600">
            Select any audited URL to inspect elements, CTAs, forms, UX/UI findings, performance, and remediation tasks.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-ink-400" />
            <input
              type="text"
              value={pageSearch}
              onChange={(e) => setPageSearch(e.target.value)}
              placeholder="Filter URL..."
              className="pl-8 pr-3 py-1.5 text-xs rounded-md border border-line bg-surface text-ink"
            />
          </div>
          <select
            value={pageTypeFilter}
            onChange={(e) => setPageTypeFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-md border border-line bg-surface text-ink"
          >
            <option value="all">All page types</option>
            {pageTypes.map((pt) => (
              <option key={pt} value={pt}>
                {pt.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Page Inventory Table */}
      <Card className="p-4 overflow-x-auto">
        <table className="w-full text-left text-xs min-w-[820px]">
          <thead>
            <tr className="border-b border-line text-ink-500 font-mono">
              <th className="py-2 pr-3">URL</th>
              <th className="py-2 pr-3">Page Type</th>
              <th className="py-2 pr-3">Primary CTA</th>
              <th className="py-2 pr-3">Forms</th>
              <th className="py-2 pr-3">Devices</th>
              <th className="py-2 pr-3">Functional Test</th>
              <th className="py-2 pr-3">UX / UI Issues</th>
              <th className="py-2">Analytics</th>
            </tr>
          </thead>
          <tbody>
            {filteredPages.map((pg) => (
              <tr
                key={pg.page_id}
                onClick={() => setSelectedPageId(pg.page_id)}
                className={`border-b border-line cursor-pointer hover:bg-paper-100 ${
                  selectedPage?.page_id === pg.page_id ? 'bg-paper-100 font-semibold' : ''
                }`}
              >
                <td className="py-2.5 pr-3 font-mono text-ink truncate max-w-[260px]">{pg.url}</td>
                <td className="py-2.5 pr-3 capitalize">{pg.page_type.replace(/_/g, ' ')}</td>
                <td className="py-2.5 pr-3">{pg.primary_cta || 'None observed'}</td>
                <td className="py-2.5 pr-3 font-mono">{pg.forms_count}</td>
                <td className="py-2.5 pr-3 font-mono">{(pg.device_coverage || []).join(', ') || 'desktop'}</td>
                <td className="py-2.5 pr-3 font-mono uppercase">{pg.functional_test_status}</td>
                <td className="py-2.5 pr-3 font-mono">{pg.ux_findings_count} / {pg.ui_findings_count}</td>
                <td className="py-2.5 font-mono">{pg.analytics_coverage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* 14-Tab Page Detail Inspector */}
      {selectedPage && (
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-[11px] font-mono uppercase text-ink-500">{selectedPage.page_type.replace(/_/g, ' ')} · Importance: {selectedPage.importance}</p>
              <h4 className="text-sm font-bold text-ink">{selectedPage.url}</h4>
            </div>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-paper-200 text-ink">
              HTTP {selectedPage.http_status ?? 'N/A'} · {selectedPage.rendered_dom_verified ? 'Rendered DOM Verified' : 'Static DOM'}
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5 border-b border-line pb-3">
            {PAGE_DETAIL_TABS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setDetailTab(t)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md border capitalize ${
                  detailTab === t ? 'bg-ink text-white border-ink' : 'border-line text-ink-600 hover:bg-paper-100'
                }`}
              >
                {t.replace(/_/g, ' ')}
              </button>
            ))}
          </div>

          {detailTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded border border-line space-y-1">
                <p className="font-semibold text-ink">Business Purpose</p>
                <p className="text-ink-600">{selectedPage.business_purpose}</p>
                <p className="font-semibold text-ink pt-2">Conversion Objective</p>
                <p className="text-ink-600">{selectedPage.conversion_objective}</p>
              </div>
              <div className="p-3 rounded border border-line space-y-1">
                <p className="font-semibold text-ink">Headline (H1)</p>
                <p className="text-ink-600">{selectedPage.h1 || 'Missing H1'}</p>
                <p className="font-semibold text-ink pt-2">Subheadline</p>
                <p className="text-ink-600">{selectedPage.subheadline || 'None observed'}</p>
              </div>
            </div>
          )}

          {detailTab === 'ctas' && (
            <div className="space-y-2 text-xs">
              {pageCtas.length === 0 ? (
                <p className="text-ink-500">No CTAs extracted on this page.</p>
              ) : (
                pageCtas.map((c: any, idx: number) => (
                  <div key={c.element_id || idx} className="p-2.5 rounded border border-line flex flex-wrap justify-between gap-2">
                    <div>
                      <span className="font-semibold text-ink">{c.text || '(Unlabeled CTA)'}</span>{' '}
                      <span className="font-mono text-ink-500">[{c.cta_hierarchy || c.element_type}]</span>
                      <p className="text-[11px] font-mono text-ink-500">Target: {c.destination || 'None'}</p>
                    </div>
                    <span className={`font-mono text-[11px] font-bold ${c.clickable === false ? 'text-bad' : 'text-good'}`}>
                      {c.interaction_result || (c.clickable === false ? 'BROKEN' : 'OK')}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}

          {detailTab === 'forms' && (
            <div className="space-y-2 text-xs">
              {pageForms.length === 0 ? (
                <p className="text-ink-500">No forms detected on this page.</p>
              ) : (
                pageForms.map((f: any, idx: number) => (
                  <div key={f.element_id || idx} className="p-3 rounded border border-line space-y-1">
                    <p className="font-semibold text-ink">{f.text}</p>
                    <p className="font-mono text-[11px] text-ink-500">
                      Fields: {f.attributes?.field_count ?? 0} · Missing labels: {f.attributes?.missing_labels ?? 0} · Status: {f.interaction_result}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}

          {(detailTab === 'ux' || detailTab === 'ui' || detailTab === 'recommendations') && (
            <div className="space-y-2 text-xs">
              {pageFindings.length === 0 ? (
                <p className="text-ink-500">No page-specific findings logged for this URL.</p>
              ) : (
                pageFindings.map((f) => (
                  <div key={f.finding_id} className="p-3 rounded border border-line space-y-1">
                    <p className="font-semibold text-ink">{f.finding_id} · {f.title}</p>
                    <p className="text-ink-600">{f.description}</p>
                    <p className="text-ink-700"><strong>Fix:</strong> {f.recommendation}</p>
                  </div>
                ))
              )}
            </div>
          )}

          {detailTab === 'remediation' && (
            <div className="space-y-2 text-xs">
              {pageTasks.length === 0 ? (
                <p className="text-ink-500">No remediation tasks mapped to this URL.</p>
              ) : (
                pageTasks.map((t) => (
                  <div key={t.task_id} className="p-3 rounded border border-line flex justify-between gap-2">
                    <div>
                      <p className="font-semibold text-ink">{t.task_id} · {t.title}</p>
                      <p className="text-ink-600">{t.proposed_change}</p>
                    </div>
                    <span className="font-mono text-[11px] uppercase">{t.priority} · {t.status}</span>
                  </div>
                ))
              )}
            </div>
          )}

          {detailTab === 'performance' && (
            <pre className="p-3 rounded bg-paper-50 border border-line text-xs font-mono overflow-x-auto">
              {JSON.stringify(selectedPage.performance_metrics || { status: 'lab_trace_not_recorded' }, null, 2)}
            </pre>
          )}

          {(['screenshot', 'raw_html', 'rendered_dom', 'elements', 'analytics', 'history'] as const).includes(detailTab as any) && (
            <div className="p-3 rounded border border-line bg-paper-50 text-xs text-ink-600 space-y-1">
              <p className="font-semibold text-ink capitalize">{detailTab.replace(/_/g, ' ')} Evidence Reference</p>
              <p>
                Page ID: <span className="font-mono">{selectedPage.page_id}</span> · Rendered DOM verified:{' '}
                <span className="font-mono">{String(selectedPage.rendered_dom_verified)}</span> · CTAs: {pageCtas.length} · Forms: {pageForms.length}
              </p>
              <p className="text-ink-500">
                Snapshots and raw DOM blobs are stored immutably in Content-Addressable Storage (CAS) via `/api/v1/cro/audits/{bundle.audit.audit_id}/evidence`.
              </p>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
