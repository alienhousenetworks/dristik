import React, { useState } from 'react';
import { Card } from '../../ui';
import { CRO_REPORT_PROFILE_LIST, CroEnterpriseBundle, croApi } from '../../../services/croApi';
import { Bell, Download, FileText, History } from 'lucide-react';

interface CroMonitoringReportsViewProps {
  bundle: CroEnterpriseBundle;
  domain: string;
  websiteUrl: string;
  onRefreshBundle: (auditId?: string) => Promise<void>;
}

export function CroMonitoringReportsView({
  bundle,
  domain,
  websiteUrl,
  onRefreshBundle,
}: CroMonitoringReportsViewProps) {
  const [selectedProfile, setSelectedProfile] = useState<string>('complete_audit_book');
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'html' | 'json'>('pdf');
  const [generating, setGenerating] = useState(false);
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [cadence, setCadence] = useState('daily');

  const handlePublishReport = async () => {
    setGenerating(true);
    setStatusMsg(null);
    setDownloadLink(null);
    try {
      const res = await croApi.createReport({
        audit_id: bundle.audit.audit_id,
        profile: selectedProfile,
        format: selectedFormat,
      });
      setDownloadLink(res.download_url);
      setStatusMsg(`Published ${selectedProfile} (${selectedFormat.toUpperCase()}) with QA status: ${res.report?.qa_passed ? 'PASSED' : 'FLAGGED'}.`);
    } catch (e: any) {
      setStatusMsg(e?.message || 'Run an Enterprise CRO Audit first to publish profile PDFs.');
    } finally {
      setGenerating(false);
    }
  };

  const handleAddSchedule = async () => {
    setStatusMsg(null);
    try {
      await croApi.createSchedule({
        domain,
        target_urls: [websiteUrl || `https://${domain}/`],
        cadence,
      });
      setStatusMsg(`Continuous CRO monitoring schedule (${cadence}) activated for ${domain}.`);
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (e: any) {
      setStatusMsg(e?.message || 'Could not create monitoring schedule.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Phase 39 — 14 Audience-Specific CRO Report Profiles */}
      <Card className="p-5 space-y-4">
        <div>
          <h3 className="text-base font-bold text-ink flex items-center gap-2">
            <FileText className="w-4 h-4" /> CRO Report &amp; PDF Publishing Center (14 Profiles · 65-Section Book)
          </h3>
          <p className="text-xs text-ink-600">
            Every audience profile builds from the exact same canonical CRO audit snapshot ({bundle.audit.audit_id}), methodology ({bundle.audit.methodology_version}), and evidence ledger.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <label className="text-xs text-ink-600 space-y-1">
            <span className="font-semibold">Audience Report Profile</span>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="w-full rounded-md border border-line bg-surface px-2.5 py-2 text-xs text-ink"
            >
              {CRO_REPORT_PROFILE_LIST.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} — {p.audience}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-ink-600 space-y-1">
            <span className="font-semibold">Format</span>
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value as 'pdf' | 'html' | 'json')}
              className="w-full rounded-md border border-line bg-surface px-2.5 py-2 text-xs text-ink"
            >
              <option value="pdf">Publication PDF (.pdf)</option>
              <option value="html">Interactive HTML (.html)</option>
              <option value="json">Canonical Dataset (.json)</option>
            </select>
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={generating}
              onClick={handlePublishReport}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-ink text-white hover:opacity-90 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              {generating ? 'Publishing...' : 'Publish & Download'}
            </button>
            {downloadLink && (
              <a
                href={downloadLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-3 py-2 text-xs font-semibold rounded-md border border-good text-good"
              >
                Open File
              </a>
            )}
          </div>
        </div>
        {statusMsg && <p className="text-xs font-medium text-indigo-700">{statusMsg}</p>}
      </Card>

      {/* Phase 25 — Continuous CRO Monitoring & Alerts */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-ink flex items-center gap-2">
              <Bell className="w-4 h-4" /> Continuous CRO Monitoring &amp; Regression Alerts
            </h3>
            <p className="text-xs text-ink-500">
              Monitors forms, CTAs, checkout paths, conversion events, mobile regressions, and experiment guardrails.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={cadence}
              onChange={(e) => setCadence(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded border border-line bg-surface"
            >
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
            <button
              type="button"
              onClick={handleAddSchedule}
              className="px-3 py-1.5 text-xs font-semibold rounded bg-ink text-white"
            >
              Enable Schedule
            </button>
          </div>
        </div>

        {(bundle.alerts || []).length === 0 ? (
          <p className="text-xs text-ink-500">No active CRO regression alerts logged for {domain}.</p>
        ) : (
          <div className="space-y-2">
            {bundle.alerts.map((al: any) => (
              <div key={al.alert_id} className="p-3 rounded-lg border border-warn/30 bg-warn/5 text-xs space-y-1">
                <div className="flex justify-between font-mono">
                  <span className="font-bold text-warn uppercase">{al.severity} · {al.alert_type}</span>
                  <span className="text-ink-500">{al.created_at}</span>
                </div>
                <p className="font-semibold text-ink">{al.title}</p>
                <p className="text-ink-600">{al.description}</p>
                <p className="text-ink-700"><strong>Suggested action:</strong> {al.suggested_action}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Phase 35 — Methodology & Historical Disclosure */}
      <Card className="p-5 space-y-2">
        <h4 className="text-sm font-bold text-ink flex items-center gap-2">
          <History className="w-4 h-4" /> Audit History &amp; Methodology Comparison Rules
        </h4>
        <p className="text-xs text-ink-600 leading-relaxed">
          Historical comparisons explicitly disclose changes in methodology version ({bundle.audit.methodology_version}), sample scope coverage, connected data sources, and traffic/device mix so audit quality changes are never conflated with seasonal conversion shifts.
        </p>
      </Card>
    </div>
  );
}
