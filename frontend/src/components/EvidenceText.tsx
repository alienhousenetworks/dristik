import React from 'react';

interface EvidenceTextProps {
  text: string;
  onSelectEvidence?: (evidenceId: string) => void;
  className?: string;
}

/**
 * Parses markdown or narrative text and transforms tokens like [ev_001], [ext_002]
 * into interactive, clickable audit evidence badges.
 */
export function EvidenceText({ text, onSelectEvidence, className = '' }: EvidenceTextProps) {
  if (!text) return null;

  // Regex matches [ev_001], [ev_12], [ext_003], etc.
  const parts = text.split(/(\[(?:ev|ext)_\d+\])/g);

  return (
    <span className={className}>
      {parts.map((part, i) => {
        const match = part.match(/^\[((?:ev|ext)_\d+)\]$/);
        if (match) {
          const evId = match[1];
          return (
            <button
              key={i}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (onSelectEvidence) {
                  onSelectEvidence(evId);
                }
              }}
              title={`Click to inspect verified snapshot & SHA-256 hash for ${evId}`}
              className="inline-flex items-center px-1.5 py-0.5 rounded font-mono text-[10px] font-bold bg-blue-100/80 hover:bg-blue-200 text-blue-900 border border-blue-300 hover:border-blue-400 transition-colors mx-0.5 align-baseline cursor-pointer"
            >
              [{evId}]
            </button>
          );
        }
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </span>
  );
}
