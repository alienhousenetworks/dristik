import React, { useState } from 'react';
import { Card } from '../../ui';
import { GEO_DEFAULT_REPORT_PROFILES, GeoEnterpriseBundle, geoApi } from '../../../services/geoApi';
import { Bell, BookOpen, Calendar, Download, FlaskConical, KeyRound, Plug, ShieldCheck } from 'lucide-react';

interface GeoOpsReportsWorkspaceProps {
  bundle: GeoEnterpriseBundle;
  mode: 'experiments' | 'monitoring' | 'history' | 'reports' | 'methodology' | 'connectors';
  onRefreshBundle: (auditId?: string) => Promise<void>;
}

export function GeoOpsReportsWorkspace({ bundle, mode, onRefreshBundle }: GeoOpsReportsWorkspaceProps) {
  const [expTitle, setExpTitle] = useState('');
  const [expHyp, setExpHyp] = useState('');
  const [cadence, setCadence] = useState<'daily' | 'weekly' | 'monthly'>('weekly');
  const [connPlatform, setConnPlatform] = useState('perplexity');
  const [connKey, setConnKey] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [reportBusy, setReportBusy] = useState<string | null>(null);

  if (mode === 'experiments') {
    const handleCreateExp = async () => {
      if (!expTitle.trim() || !expHyp.trim()) return;
      setStatusMsg(null);
      try {
        await geoApi.createExperiment({
          audit_id: bundle.audit.audit_id,
          title: expTitle.trim(),
          hypothesis: expHyp.trim(),
          target_urls: [bundle.audit.website_url],
        });
        setExpTitle('');
        setExpHyp('');
        setStatusMsg('Controlled GEO experiment created with baseline snapshot.');
        await onRefreshBundle(bundle.audit.audit_id);
      } catch (err: any) {
        setStatusMsg(err?.message || 'Could not create experiment.');
      }
    };
    return (
      <Card className="p-5 space-y-4">
        <div>
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-pine" /> Controlled GEO Experiments ({bundle.experiments.length})
          </h3>
          <p className="text-xs text-ink-500">
            Pins prompt suite versions and baseline snapshots for before/after evaluation without falsely claiming causation.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs bg-paper-50 p-3 rounded border border-line">
          <input value={expTitle} onChange={(e) => setExpTitle(e.target.value)} placeholder="Experiment title..." className="px-2.5 py-1.5 border border-line rounded bg-white" />
          <input value={expHyp} onChange={(e) => setExpHyp(e.target.value)} placeholder="Hypothesis (e.g. factual product table improves accuracy)..." className="px-2.5 py-1.5 border border-line rounded bg-white" />
          <button type="button" onClick={handleCreateExp} className="px-3 py-1.5 bg-pine text-white font-semibold rounded">
            Create Controlled Experiment
          </button>
        </div>
        {statusMsg && <p className="text-xs font-mono text-pine">{statusMsg}</p>}
        <div className="space-y-2.5">
          {bundle.experiments.map((e: any) => (
            <div key={e.experiment_id} className="p-3.5 rounded border border-line bg-white text-xs space-y-1">
              <div className="flex justify-between">
                <span className="font-bold text-ink">{e.title}</span>
                <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-paper-100">{e.status} · Suite v{e.baseline_prompt_suite_version}</span>
              </div>
              <p className="text-ink-700">{e.hypothesis}</p>
              <p className="text-[11px] text-warn italic">{e.causation_disclaimer}</p>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (mode === 'monitoring') {
    const schedules = bundle.monitoring_schedules || [];
    const alerts = bundle.monitoring_alerts || [];
    const handleCreateSched = async () => {
      setStatusMsg(null);
      try {
        await geoApi.createSchedule({ domain: bundle.audit.domain, brand_name: bundle.audit.brand_name, cadence });
        setStatusMsg(`Created ${cadence} GEO monitoring schedule.`);
        await onRefreshBundle(bundle.audit.audit_id);
      } catch (err: any) {
        setStatusMsg(err?.message || 'Could not create schedule.');
      }
    };
    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
              <Calendar className="w-4 h-4 text-pine" /> Scheduled GEO Monitoring ({schedules.length})
            </h3>
            <div className="flex gap-2 text-xs">
              <select value={cadence} onChange={(e) => setCadence(e.target.value as any)} className="px-2 py-1 border border-line rounded bg-white">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
              <button type="button" onClick={handleCreateSched} className="px-3 py-1 bg-pine text-white rounded font-semibold">
                Add Schedule
              </button>
            </div>
          </div>
          {statusMsg && <p className="text-xs font-mono text-pine">{statusMsg}</p>}
          {schedules.length === 0 ? (
            <p className="text-xs text-ink-500">No active schedules yet. Select cadence based on provider budget and business goals.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {schedules.map((s: any) => (
                <div key={s.schedule_id} className="p-3 rounded border border-line bg-paper-50 flex justify-between">
                  <span className="font-semibold text-ink">{s.domain} ({s.cadence})</span>
                  <span className="font-mono text-[10px]">Budget cap: ${s.max_budget_per_run_usd}/run</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card className="p-5 space-y-3">
          <h4 className="font-sans font-bold text-ink text-sm flex items-center gap-2">
            <Bell className="w-4 h-4 text-warn" /> Drift &amp; Misinformation Alerts ({alerts.length})
          </h4>
          {alerts.length === 0 ? (
            <p className="text-xs text-ink-500">No monitoring alerts fired yet.</p>
          ) : (
            alerts.map((a: any) => (
              <div key={a.alert_id} className="p-3 rounded border border-line bg-paper-50 text-xs">
                <div className="font-bold text-ink">[{a.alert_type}] {a.title}</div>
                <p className="text-ink-600">{a.description}</p>
              </div>
            ))
          )}
        </Card>
      </div>
    );
  }

  if (mode === 'history') {
    const hist = bundle.monitoring_history || [];
    return (
      <Card className="p-5 space-y-4">
        <h3 className="font-sans font-bold text-ink text-base">Audit History &amp; Methodology-Compatible Snapshots ({hist.length})</h3>
        {hist.length === 0 ? (
          <p className="text-xs text-ink-500">Historical comparison begins after multiple Enterprise GEO Audits are stored.</p>
        ) : (
          <div className="overflow-x-auto border border-line rounded">
            <table className="w-full text-xs text-left">
              <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
                <tr>
                  <th className="p-2.5">Audit ID</th>
                  <th className="p-2.5">Date</th>
                  <th className="p-2.5">Publication Status</th>
                  <th className="p-2.5">Observed Perf.</th>
                  <th className="p-2.5">Readiness</th>
                  <th className="p-2.5">Methodology</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {hist.map((h: any) => (
                  <tr key={h.audit_id}>
                    <td className="p-2.5 font-mono text-[10px]">{h.audit_id}</td>
                    <td className="p-2.5 font-mono text-[10px]">{String(h.created_at).slice(0, 19)}</td>
                    <td className="p-2.5 font-mono text-[10px]">{h.publication_status}</td>
                    <td className="p-2.5 font-mono">{h.observed_performance_score ?? 'Unmeasured'}</td>
                    <td className="p-2.5 font-mono">{h.readiness_score ?? 'Unmeasured'}</td>
                    <td className="p-2.5 font-mono text-[10px]">{h.methodology_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    );
  }

  if (mode === 'reports') {
    const profiles = bundle.report_profiles || GEO_DEFAULT_REPORT_PROFILES;
    const handleDownload = async (profileKey: string, fmt: 'pdf' | 'html' | 'json') => {
      setReportBusy(`${profileKey}:${fmt}`);
      setStatusMsg(null);
      try {
        const res = await geoApi.generateReport(bundle.audit.audit_id, profileKey, fmt);
        window.open(geoApi.reportDownloadUrl(res.report.report_id), '_blank', 'noopener');
        setStatusMsg(`Generated ${profileKey} (${fmt.toUpperCase()}) — QA passed: ${res.report.qa_passed}.`);
      } catch (err: any) {
        setStatusMsg(err?.message || 'Run an Enterprise GEO Audit first to export canonical reports.');
      } finally {
        setReportBusy(null);
      }
    };
    return (
      <Card className="p-5 space-y-4">
        <div>
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-pine" /> Canonical GEO Report Profiles (10 Dynamic Books · Same Dataset &amp; Methodology)
          </h3>
          <p className="text-xs text-ink-500">
            Every PDF, HTML, and JSON report binds strictly to Audit ID {bundle.audit.audit_id} ({bundle.audit.methodology_version}) and passes cross-system QA validation.
          </p>
        </div>
        {statusMsg && <p className="text-xs font-mono text-pine">{statusMsg}</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(profiles).map(([key, meta]) => (
            <div key={key} className="p-4 rounded border border-line bg-paper-50 flex items-center justify-between gap-3">
              <div>
                <div className="font-semibold text-sm text-ink">{meta.title}</div>
                <div className="text-[11px] text-ink-500">Audience: {meta.audience}</div>
              </div>
              <div className="flex gap-1.5">
                {(['pdf', 'html', 'json'] as const).map((fmt) => (
                  <button
                    key={fmt}
                    type="button"
                    disabled={reportBusy === `${key}:${fmt}`}
                    onClick={() => handleDownload(key, fmt)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-line bg-white hover:bg-paper-100 font-mono text-[10px] font-bold uppercase"
                  >
                    <Download className="w-3 h-3" /> {fmt}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (mode === 'methodology') {
    const qaChecks: Array<Record<string, any>> = bundle.qa_report?.checks || [];
    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-3">
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-pine" /> Scoring, Provenance &amp; Publication QA Transparency
          </h3>
          <p className="text-xs text-ink-700 leading-relaxed">{bundle.scorecard.methodology_disclosure}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 rounded border border-line bg-paper-50 space-y-1">
              <div className="font-mono font-bold text-[11px] uppercase">Non-Negotiable Measurement Rules</div>
              <ul className="list-disc pl-4 space-y-1 text-ink-700">
                <li>Missing API credentials are reported as NOT_CONFIGURED, never 0% visibility.</li>
                <li>Mentions, explicit recommendations, shortlists, and URL citations are tracked as distinct metrics.</li>
                <li>Branded prompts are separated from non-branded discovery prompts.</li>
                <li>API_MODEL_ONLY completions are never labeled as consumer ChatGPT/Google AI Overviews.</li>
              </ul>
            </div>
            <div className="p-3.5 rounded border border-line bg-paper-50 space-y-1">
              <div className="font-mono font-bold text-[11px] uppercase">Publication QA Gate ({bundle.qa_report?.qa_status || 'pending'})</div>
              {qaChecks.length === 0 ? (
                <p className="text-ink-500">QA checks execute automatically on every Enterprise GEO Audit.</p>
              ) : (
                <ul className="space-y-1 text-[11px]">
                  {qaChecks.slice(0, 8).map((c: any) => (
                    <li key={c.check_id} className="flex items-center justify-between">
                      <span>{c.check_id}: {c.check_name}</span>
                      <span className={`font-mono font-bold ${c.passed ? 'text-good' : 'text-bad'}`}>{c.passed ? 'PASS' : 'FAIL'}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // Connectors & Provider Capability Matrix
  const caps = bundle.capability_matrix || [];
  const handleConnect = async () => {
    if (!connKey.trim()) return;
    setStatusMsg(null);
    try {
      await geoApi.connectPlatform({ platform_id: connPlatform, api_key: connKey.trim() });
      setConnKey('');
      setStatusMsg(`Encrypted credential stored for ${connPlatform}. Secrets are never returned to the browser.`);
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (err: any) {
      setStatusMsg(err?.message || 'Connecting provider requires Admin/Owner permission.');
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-5 space-y-4">
        <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
          <Plug className="w-4 h-4 text-pine" /> AI Provider Connectors (Encrypted at Rest) &amp; Capability Matrix
        </h3>
        <div className="p-3 rounded border border-line bg-paper-50 flex flex-wrap gap-2 items-center text-xs">
          <KeyRound className="w-4 h-4 text-pine" />
          <select value={connPlatform} onChange={(e) => setConnPlatform(e.target.value)} className="px-2.5 py-1.5 border border-line rounded bg-white">
            <option value="chatgpt">ChatGPT (OpenAI)</option>
            <option value="gemini">Google Gemini</option>
            <option value="claude">Claude (Anthropic)</option>
            <option value="perplexity">Perplexity Pro</option>
            <option value="grok">Grok (xAI)</option>
            <option value="deepseek">DeepSeek</option>
            <option value="copilot">Microsoft Copilot</option>
          </select>
          <input
            type="password"
            value={connKey}
            onChange={(e) => setConnKey(e.target.value)}
            placeholder="Provider API key (Fernet encrypted at rest)..."
            className="flex-1 min-w-[200px] px-2.5 py-1.5 border border-line rounded bg-white"
          />
          <button type="button" onClick={handleConnect} className="px-3 py-1.5 bg-pine text-white font-semibold rounded">
            Save Encrypted Connection
          </button>
        </div>
        {statusMsg && <p className="text-xs font-mono text-pine">{statusMsg}</p>}

        {caps.length > 0 && (
          <div className="overflow-x-auto border border-line rounded">
            <table className="w-full text-xs text-left">
              <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
                <tr>
                  <th className="p-2.5">Provider</th>
                  <th className="p-2.5">Auth State</th>
                  <th className="p-2.5">Default Mode</th>
                  <th className="p-2.5">Search Grounded</th>
                  <th className="p-2.5">Citation Metadata</th>
                  <th className="p-2.5">Geo Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {caps.map((c: any) => (
                  <tr key={c.platform_id}>
                    <td className="p-2.5 font-semibold text-ink">{c.display_name}</td>
                    <td className="p-2.5 font-mono text-[10px]">{c.auth_state}</td>
                    <td className="p-2.5 font-mono text-[10px]">{c.default_testing_mode}</td>
                    <td className="p-2.5 font-mono text-[10px]">{c.search_grounded_response}</td>
                    <td className="p-2.5 font-mono text-[10px]">{c.citation_metadata}</td>
                    <td className="p-2.5 font-mono text-[10px]">{c.geographic_controls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
