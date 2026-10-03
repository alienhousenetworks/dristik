import React, { useState } from 'react';
import { VisualUxInspectionReport, ViewportInspection } from '../types';

interface VisualUxInspectionViewProps {
  visualUx?: VisualUxInspectionReport;
  domain?: string;
}

function isCannedVisual(report?: VisualUxInspectionReport): boolean {
  if (!report) return true;
  const blob = JSON.stringify(report);
  return (
    blob.includes('REQUEST CUSTOM BUILD')
    || blob.includes('Enterprise AI & Website Intelligence')
    || blob.includes('Beyond Imagination')
  );
}

export function VisualUxInspectionView({ visualUx, domain }: VisualUxInspectionViewProps) {
  const measured = visualUx && !isCannedVisual(visualUx) && Object.keys(visualUx.viewports || {}).length > 0
    ? visualUx
    : null;
  const devices = measured ? (Object.keys(measured.viewports) as Array<'desktop' | 'tablet' | 'mobile'>) : [];
  const [activeDevice, setActiveDevice] = useState<'desktop' | 'tablet' | 'mobile'>(devices[0] || 'desktop');
  const current: ViewportInspection | undefined = measured?.viewports[activeDevice] || measured?.viewports[devices[0]];

  return (
    <div className="bg-paper-50 dark:bg-ink-950 border border-line rounded-xl p-5 shadow-xs space-y-4">
      <div>
        <span className="text-xs font-mono font-bold uppercase tracking-[0.04em] px-2 py-0.5 rounded bg-ink-800 text-white">
          Visual check
        </span>
        <h3 className="font-sans text-lg font-bold text-ink mt-2">
          Above-the-fold inspection
        </h3>
        <p className="text-xs text-ink-600 mt-1 max-w-2xl">
          Fold position, contrast, and layout shift appear only after a rendered screenshot of {domain || 'this site'}.
        </p>
      </div>

      {!measured || !current ? (
        <p className="text-sm text-ink-600">
          No desktop, tablet, or mobile render was captured. There is no visual score and no defect list for this audit.
        </p>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {devices.map((device) => (
              <button
                key={device}
                type="button"
                onClick={() => setActiveDevice(device)}
                className={`px-3 py-1.5 rounded-md font-mono text-xs font-bold border ${
                  activeDevice === device ? 'bg-ink text-paper-50 border-ink' : 'bg-paper-50 text-ink-600 border-line'
                }`}
              >
                {device} ({measured.viewports[device].width}×{measured.viewports[device].height})
              </button>
            ))}
            <span className="text-xs font-mono text-ink-500 self-center">
              Score: {measured.overall_visual_ux_score == null ? '—' : `${Math.round(measured.overall_visual_ux_score)}/100`}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
            {Object.entries(current.above_the_fold || {}).map(([dim, details]) => (
              <div key={dim} className="p-2.5 rounded bg-paper-50 border border-line">
                <span className="text-[10px] text-ink-400 uppercase">{dim.replace(/_/g, ' ')}</span>
                <div className="text-ink">{details?.label || details?.text || details?.status || '—'}</div>
              </div>
            ))}
          </div>
          {(measured.critical_visual_defects || []).length === 0 ? (
            <p className="text-xs text-ink-500">No visual defects were recorded.</p>
          ) : (
            <ul className="space-y-2 text-xs">
              {measured.critical_visual_defects.map((defect, i) => (
                <li key={i} className="p-3 bg-paper-50 border border-line rounded">
                  <span className="font-bold">{defect.defect}</span> [{defect.device}] {defect.evidence}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
