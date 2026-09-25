import React from 'react';
import { ThreeWayComparison } from '../types';
import { display } from '../lib/format';

interface PerspectivesProps {
  comparison?: ThreeWayComparison;
}

export function Perspectives({ comparison }: PerspectivesProps) {
  const lenses = [
    { label: 'Human visitor', body: comparison?.human_visitor_perspective },
    { label: 'Search engine', body: comparison?.search_engine_perspective },
    { label: 'Answer engine', body: comparison?.ai_answer_engine_perspective },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
      {lenses.map((lens) => (
        <article key={lens.label}>
          <p className="label mb-3">{lens.label}</p>
          <p className="text-ink-700 leading-relaxed">{display(lens.body)}</p>
        </article>
      ))}
    </div>
  );
}
