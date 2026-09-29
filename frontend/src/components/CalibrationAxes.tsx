import React from 'react';
import { Finding } from '../types';

function bandLabel(band: string | undefined): string {
  if (!band) return '—';
  if (band === 'HIGH') return 'High';
  if (band === 'MEDIUM') return 'Medium';
  if (band === 'LOW') return 'Low';
  return band;
}

export function CalibrationAxes({ finding, compact = false }: { finding: Finding; compact?: boolean }) {
  const calibrated = finding.calibrated_impact;
  if (!calibrated) return null;
  const blocking = calibrated.is_blocking || (calibrated.blocks?.length ?? 0) > 0;
  const cells = [
    ['Technical severity', calibrated.technical_severity],
    ['Business impact', calibrated.business_impact_label || calibrated.business_impact],
    ['Confidence', bandLabel(calibrated.confidence_band)],
    ['Blocking', blocking ? 'Yes' : 'No'],
  ];
  return (
    <dl className={`grid grid-cols-2 sm:grid-cols-4 gap-2 ${compact ? 'text-[10px]' : 'text-[11px]'}`}>
      {cells.map(([label, value]) => (
        <div key={label} className="rounded border border-line bg-paper-50 px-2 py-1">
          <dt className="font-mono uppercase tracking-wide text-ink-400 text-[9px]">{label}</dt>
          <dd className="font-semibold text-ink mt-0.5">{value}</dd>
        </div>
      ))}
      {blocking && calibrated.blocking_reason ? (
        <p className="col-span-2 sm:col-span-4 text-[10px] text-ink-600 leading-snug">
          {calibrated.blocking_reason}
        </p>
      ) : null}
    </dl>
  );
}

function rankValue(finding: Finding, axis: 'commercial' | 'technical'): number[] {
  const calibrated = finding.calibrated_impact;
  const sev: Record<string, number> = { INFO: 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 };
  const conf: Record<string, number> = { LOW: 0, MEDIUM: 1, HIGH: 2 };
  if (!calibrated) return [0, 0, 0, 0];
  const tech = sev[calibrated.technical_severity] ?? 0;
  const biz = sev[String(calibrated.business_impact).toUpperCase()] ?? 0;
  const band = conf[String(calibrated.confidence_band).toUpperCase()] ?? 0;
  const blocking = calibrated.is_blocking || (calibrated.blocks?.length ?? 0) > 0 ? 1 : 0;
  return axis === 'commercial' ? [blocking, biz, band, tech] : [tech, band, biz, 0];
}

function compare(a: number[], b: number[]): number {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return 0;
}

export function calibrationLeaders(findings: Finding[]): { commercial: Finding | null; technical: Finding | null } {
  const eligible = findings.filter((finding) => {
    if (!finding.calibrated_impact) return false;
    if (finding.confidence_rubric === 'GUESSING') return false;
    if (finding.held_from_executive && !finding.adversarial_reviewed) return false;
    return true;
  });
  if (eligible.length === 0) return { commercial: null, technical: null };
  const commercial = [...eligible].sort((a, b) => compare(rankValue(b, 'commercial'), rankValue(a, 'commercial')))[0];
  const technical = [...eligible].sort((a, b) => compare(rankValue(b, 'technical'), rankValue(a, 'technical')))[0];
  return { commercial, technical };
}

export function CalibrationLeaders({ findings }: { findings: Finding[] }) {
  const { commercial, technical } = calibrationLeaders(findings);
  if (!commercial && !technical) return null;
  const same = commercial && technical && commercial.finding_id === technical.finding_id;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {commercial ? (
        <div className="space-y-2">
          <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-500">
            Highest business impact
          </p>
          <p className="text-xs font-semibold text-ink">{commercial.title}</p>
          <CalibrationAxes finding={commercial} compact />
        </div>
      ) : null}
      {technical && !same ? (
        <div className="space-y-2">
          <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-500">
            Highest technical severity
          </p>
          <p className="text-xs font-semibold text-ink">{technical.title}</p>
          <CalibrationAxes finding={technical} compact />
        </div>
      ) : null}
    </div>
  );
}
