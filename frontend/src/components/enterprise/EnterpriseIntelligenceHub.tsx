import React, { useEffect, useState } from "react";

interface ReadinessItem {
  id: string;
  group: string;
  label: string;
  passed: boolean;
}

interface ReadinessPayload {
  total_criteria: number;
  completed_criteria: number;
  completion_pct: number;
  items: ReadinessItem[];
  note: string;
}

interface ConnectorHealthItem {
  provider: string;
  configured_in_env: boolean;
  status: string;
  freshness_status: string;
  last_sync_utc: string | null;
  required_env_vars: string[];
}

export const EnterpriseIntelligenceHub: React.FC<{ domain: string; apiBase?: string }> = ({
  domain,
  apiBase = "/api/v1/enterprise",
}) => {
  const [readiness, setReadiness] = useState<ReadinessPayload | null>(null);
  const [connectors, setConnectors] = useState<ConnectorHealthItem[]>([]);
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");
  const [heatmapLayer, setHeatmapLayer] = useState<"click" | "scroll" | "movement">("click");
  const [heatmap, setHeatmap] = useState<any>(null);
  const [aiReferrals, setAiReferrals] = useState<any>(null);

  useEffect(() => {
    const opts: RequestInit = { credentials: "include" };
    fetch(`${apiBase}/readiness-34`, opts).then((r) => (r.ok ? r.json() : null)).then(setReadiness).catch(() => {});
    fetch(`${apiBase}/ops/connectors-health`, opts)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setConnectors(d?.connectors || []))
      .catch(() => {});
    fetch(`${apiBase}/ai-referrals/${encodeURIComponent(domain)}`, opts)
      .then((r) => (r.ok ? r.json() : null))
      .then(setAiReferrals)
      .catch(() => {});
  }, [apiBase, domain]);

  useEffect(() => {
    fetch(`${apiBase}/cro/heatmaps/${encodeURIComponent(domain)}?page_url=/&device=${device}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setHeatmap)
      .catch(() => {});
  }, [apiBase, domain, device]);

  return (
    <div className="space-y-6 p-6 bg-slate-950 text-slate-100 rounded-xl border border-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold">Dristik Enterprise Intelligence Hub</h2>
          <p className="text-xs text-slate-400">Domain: {domain} · Zero-Fake-Evidence Governance Active</p>
        </div>
        {readiness && (
          <div className="text-right">
            <div className="text-2xl font-bold text-teal-400">{readiness.completion_pct}%</div>
            <div className="text-xs text-slate-400">
              {readiness.completed_criteria} / {readiness.total_criteria} Enterprise Criteria
            </div>
          </div>
        )}
      </div>

      {/* AI Referral Summary */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase">AI-Referred Sessions</div>
          <div className="text-2xl font-semibold mt-1">{aiReferrals?.ai_referred_sessions ?? "—"}</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase">AI-Attributed Conversions</div>
          <div className="text-2xl font-semibold mt-1">{aiReferrals?.ai_attributed_conversions ?? "—"}</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase">AI-Assisted Conversions</div>
          <div className="text-2xl font-semibold mt-1">{aiReferrals?.ai_assisted_conversions ?? "—"}</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase">Unobservable / Unknown Sessions</div>
          <div className="text-2xl font-semibold mt-1">{aiReferrals?.unknown_or_unobservable_sessions ?? "—"}</div>
        </div>
      </section>

      {/* Heatmap Page Overlay Viewer Controls */}
      <section className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Behavioral Heatmap Overlay Viewer</h3>
          <div className="flex gap-2 text-xs">
            {(["click", "scroll", "movement"] as const).map((layer) => (
              <button
                key={layer}
                onClick={() => setHeatmapLayer(layer)}
                className={`px-2.5 py-1 rounded ${heatmapLayer === layer ? "bg-teal-600 text-white" : "bg-slate-800 text-slate-300"}`}
              >
                {layer === "movement" ? "Movement (Cursor Concentration)" : layer.toUpperCase()}
              </button>
            ))}
            {(["desktop", "tablet", "mobile"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDevice(d)}
                className={`px-2.5 py-1 rounded ${device === d ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-300"}`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
        <div className="text-xs text-slate-400">
          Status: <strong>{heatmap?.status || "LOADING"}</strong> · Denominator:{" "}
          <strong>{heatmap?.denominator_sessions ?? 0}</strong> sessions ·{" "}
          {heatmap?.movement_concentration_label || "Estimated cursor/interaction concentration (NOT eye-tracking)"}
        </div>
      </section>

      {/* Connector Health Matrix */}
      <section className="p-4 rounded-lg bg-slate-900 border border-slate-800">
        <h3 className="text-sm font-semibold mb-3">Connector Health &amp; .env Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
          {connectors.map((c) => (
            <div key={c.provider} className="p-2.5 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
              <span className="font-mono">{c.provider}</span>
              <span className={c.configured_in_env ? "text-emerald-400" : "text-amber-400"}>{c.status}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default EnterpriseIntelligenceHub;
