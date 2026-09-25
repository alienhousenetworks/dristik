import { useEffect, useState } from 'react';
import { OutcomeRecord } from '../types';

interface OutcomeTrackingViewProps {
  analysisId?: string;
}

export function OutcomeTrackingView({ analysisId }: OutcomeTrackingViewProps) {
  const [records, setRecords] = useState<OutcomeRecord[]>([]);
  const [jobs, setJobs] = useState<Array<{ horizon_days: number; status: string; due_at?: number }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;
    let cancelled = false;
    fetch(`/api/v1/outcomes/${analysisId}`, { credentials: 'include' })
      .then(async (res) => {
        if (!res.ok) return;
        const body = await res.json();
        if (cancelled) return;
        setRecords(body.records || []);
        setJobs(body.jobs || []);
      })
      .catch(() => {
        if (!cancelled) setError('Outcome feed unavailable');
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  return (
    <section className="border border-line rounded-lg p-5 space-y-3">
      <div>
        <p className="label">Outcome tracking (30 / 60 / 90 days)</p>
        <h3 className="font-serif text-2xl text-ink mt-1">Did the fix move a real metric?</h3>
        <p className="text-sm text-ink-600 mt-1">
          Rechecks original findings against a later crawl. A metric change after a fix is correlation, not proof of causation.
        </p>
      </div>
      {jobs.length > 0 && records.length === 0 && (
        <p className="text-sm text-ink-500">
          Rechecks scheduled at {jobs.map((j) => `${j.horizon_days}d (${j.status})`).join(', ')}.
        </p>
      )}
      {error && <p className="text-sm text-ink-500">{error}</p>}
      {records.length === 0 && jobs.length === 0 && (
        <p className="text-sm text-ink-500">No post-delivery recheck has been run yet.</p>
      )}
      {records.length > 0 && (
        <ul className="divide-y divide-line border-y border-line">
          {records.map((rec) => (
            <li key={`${rec.finding_id}-${rec.horizon_days}`} className="py-3 grid grid-cols-12 gap-2 text-sm">
              <span className="col-span-4 font-mono text-xs text-ink-500">{rec.finding_id}</span>
              <span className="col-span-4">
                {rec.evidence_condition_resolved ? 'Condition resolved' : 'Still open'}
                {rec.remediated ? ' · marked remediated' : ''}
              </span>
              <span className="col-span-2 text-xs uppercase">{rec.confidence_this_delta_is_attributable_to_the_fix}</span>
              <span className="col-span-2 text-ink-500 text-xs">{rec.observed_outcome.replace(/_/g, ' ')}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
