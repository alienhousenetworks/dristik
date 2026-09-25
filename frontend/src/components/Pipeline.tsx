import React from 'react';
import { AnalysisRun } from '../types';

const STAGES = [
  { key: 'ingesting', label: 'Crawl' },
  { key: 'deterministic_analysis', label: 'Evidence' },
  { key: 'planning', label: 'Plan' },
  { key: 'specialist_execution', label: 'Specialists' },
  { key: 'adversarial_verification', label: 'Verify' },
  { key: 'executive_synthesis', label: 'Narrative' },
  { key: 'scoring', label: 'Score' },
];

interface PipelineProps {
  run: AnalysisRun;
}

export function Pipeline({ run }: PipelineProps) {
  const order = STAGES.map((s) => s.key);
  const currentIndex = order.findIndex((key) => key === run.status);
  const done = run.status === 'completed';
  const failed = run.status === 'failed';

  return (
    <section className="card p-5 sm:p-6 space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="label">Progress</p>
          <p className="mt-1 text-ink-700">{run.current_step || 'Queued'}</p>
        </div>
        <p className="font-serif text-3xl text-ink leading-none">{run.progress_percentage}%</p>
      </div>

      <div className="h-1.5 bg-ink-300/40 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${failed ? 'bg-bad' : 'bg-pine'} transition-all duration-500`}
          style={{ width: `${Math.max(4, run.progress_percentage)}%` }}
        />
      </div>

      <ol className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {STAGES.map((stage, index) => {
          const passed = done || (currentIndex >= 0 && index < currentIndex);
          const current = !done && !failed && stage.key === run.status;
          return (
            <li
              key={stage.key}
              className={passed ? 'text-good' : current ? 'text-ink font-medium' : 'text-ink-300'}
            >
              {stage.label}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
