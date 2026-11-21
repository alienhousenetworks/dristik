import React from 'react';
import { Card } from '../../ui';
import { CroEnterpriseBundle } from '../../../services/croApi';
import { BarChart3, Plug, AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react';

interface CroAnalyticsAndFunnelsViewProps {
  bundle: CroEnterpriseBundle;
  onNavigateTab: (tab: string) => void;
}

export function CroAnalyticsAndFunnelsView({ bundle, onNavigateTab }: CroAnalyticsAndFunnelsViewProps) {
  const anl = bundle.department_artifacts?.analytics_intelligence || {};
  const measurementChecks: Array<{ check: string; status: string; detail: string }> =
    bundle.scorecard.measurement_checks || anl.measurement_checks || [];
  const events: any[] = bundle.events?.length ? bundle.events : anl.events || [];
  const funnels: any[] = bundle.funnels?.length ? bundle.funnels : anl.funnels || [];
  const connectors = bundle.connectors?.length ? bundle.connectors : anl.connectors || [];
  const scenario = anl.impact_scenario_estimate;

  return (
    <div className="space-y-6">
      {/* Measurement Readiness & Tracking Health */}
      <Card className="p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-ink flex items-center gap-2">
              <BarChart3 className="w-4 h-4" /> Analytics Configuration &amp; Tracking Health
            </h3>
            <p className="text-xs text-ink-500">
              Audit of tag installation, deduplication, consent mode, and conversion event accuracy. Broken tracking generates a data-quality finding rather than fabricated conversion diagnoses.
            </p>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 rounded bg-paper-200 text-ink">
            Measurement Score: {bundle.scorecard.measurement_score ?? 'Unmeasured'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {measurementChecks.map((mc) => (
            <div key={mc.check} className="p-3 rounded-lg border border-line space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-ink">{mc.check}</span>
                <span
                  className={`font-mono text-[10px] uppercase font-bold ${
                    mc.status === 'passed' ? 'text-good' : mc.status === 'failed' ? 'text-bad' : 'text-warn'
                  }`}
                >
                  {mc.status}
                </span>
              </div>
              <p className="text-[11px] text-ink-600">{mc.detail}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Funnel Step-by-Step Progression & Drop-Off */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-ink">Funnel Intelligence &amp; Step Abandonment</h3>
            <p className="text-xs text-ink-500">
              Counting unit and date range are explicitly stated for every funnel step; disconnected analytics stays DATA UNAVAILABLE.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab('remediation')}
            className="text-xs font-semibold text-ink underline inline-flex items-center gap-1"
          >
            Jump to linked remediation tasks <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {funnels.map((fnl: any) => (
          <div key={fnl.funnel_id} className="space-y-3">
            <div className="flex flex-wrap justify-between text-xs font-mono text-ink-500">
              <span>{fnl.name} · Source: {fnl.source}</span>
              <span>Unit: {fnl.counting_unit} · Completeness: {fnl.data_completeness}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[680px]">
                <thead>
                  <tr className="border-b border-line font-mono text-ink-500">
                    <th className="py-2 pr-3">Step</th>
                    <th className="py-2 pr-3">Event</th>
                    <th className="py-2 pr-3">Eligible</th>
                    <th className="py-2 pr-3">Progressing</th>
                    <th className="py-2 pr-3">Step Conversion</th>
                    <th className="py-2 pr-3">Abandonment</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(fnl.steps || []).map((st: any) => (
                    <tr key={st.funnel_step_id || st.step_order} className="border-b border-line">
                      <td className="py-2 pr-3 font-semibold text-ink">{st.step_order}. {st.step_name}</td>
                      <td className="py-2 pr-3 font-mono text-ink-500">{st.event_name || '—'}</td>
                      <td className="py-2 pr-3 font-mono">{st.eligible_count ?? 'Unavailable'}</td>
                      <td className="py-2 pr-3 font-mono">{st.progressing_count ?? 'Unavailable'}</td>
                      <td className="py-2 pr-3 font-mono">
                        {st.step_conversion_rate != null ? `${st.step_conversion_rate}%` : 'Unavailable'}
                      </td>
                      <td className={`py-2 pr-3 font-mono ${(st.step_abandonment_rate ?? 0) >= 50 ? 'text-bad font-bold' : ''}`}>
                        {st.step_abandonment_rate != null ? `${st.step_abandonment_rate}%` : 'Unavailable'}
                      </td>
                      <td className="py-2 font-mono uppercase text-[11px]">{st.measurement_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </Card>

      {/* Conversion Goal Event Validation Dictionary */}
      <Card className="p-5 space-y-3">
        <h3 className="text-sm font-bold text-ink">Conversion Event Dictionary &amp; Data Quality</h3>
        {events.length === 0 ? (
          <p className="text-xs text-ink-500">No conversion events recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[680px]">
              <thead>
                <tr className="border-b border-line font-mono text-ink-500">
                  <th className="py-2 pr-3">Event</th>
                  <th className="py-2 pr-3">Trigger</th>
                  <th className="py-2 pr-3">Required Params</th>
                  <th className="py-2 pr-3">Source</th>
                  <th className="py-2">Validation Status</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev: any) => (
                  <tr key={ev.event_record_id || ev.event_name} className="border-b border-line">
                    <td className="py-2 pr-3 font-mono font-semibold text-ink">{ev.event_name}</td>
                    <td className="py-2 pr-3 text-ink-600">{ev.trigger_description}</td>
                    <td className="py-2 pr-3 font-mono text-[11px]">{(ev.required_parameters || []).join(', ') || '—'}</td>
                    <td className="py-2 pr-3 font-mono uppercase">{ev.connector_type}</td>
                    <td className="py-2 font-mono uppercase font-semibold">{ev.validation_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Hypothetical Impact Scenario Disclaimer */}
      {scenario && (
        <Card className="p-4 bg-paper-50 space-y-1.5 border-dashed">
          <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase text-warn">
            <AlertTriangle className="w-4 h-4" />
            Business Impact Scenario ({scenario.label})
          </div>
          <p className="text-xs text-ink-600">{scenario.disclaimer}</p>
        </Card>
      )}

      {/* Phase 41 — Truthful Connector Capability Matrix */}
      <Card className="p-5 space-y-3">
        <div>
          <h3 className="text-sm font-bold text-ink flex items-center gap-2">
            <Plug className="w-4 h-4" /> CRO Connector Registry &amp; Capability Boundaries
          </h3>
          <p className="text-xs text-ink-500">
            Reports exact authentication status, supported telemetry, and explicit platform limitations. Credentials remain AES-GCM encrypted server-side.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {connectors.map((c: any) => (
            <div key={c.connector_id} className="p-3.5 rounded-lg border border-line space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-ink">{c.provider}</span>
                <span
                  className={`inline-flex items-center gap-1 font-mono text-[10px] uppercase px-2 py-0.5 rounded font-semibold ${
                    c.connection_status === 'connected' ? 'bg-good/10 text-good' : 'bg-paper-200 text-ink-600'
                  }`}
                >
                  {c.connection_status === 'connected' && <CheckCircle2 className="w-3 h-3" />}
                  {c.connection_status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-[11px] font-mono text-ink-500">
                Tier {c.priority_tier} · {c.category.replace(/_/g, ' ')}
              </p>
              <p className="text-[11px] text-ink-600">
                <strong>Supports:</strong> {(c.supported_data || []).slice(0, 5).join(', ')}
              </p>
              {c.unsupported_or_limited?.length > 0 && (
                <p className="text-[11px] text-ink-500 italic">{c.unsupported_or_limited[0]}</p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
