import React, { useState } from 'react';
import { CharacterSafeCopy } from '../types';

interface CharacterSafeCopyWidgetProps {
  initialCopy?: CharacterSafeCopy;
}

export function CharacterSafeCopyWidget({ initialCopy }: CharacterSafeCopyWidgetProps) {
  const [title, setTitle] = useState(initialCopy?.title || '');
  const [meta, setMeta] = useState(initialCopy?.meta_description || '');
  const [headline, setHeadline] = useState(initialCopy?.hero_headline || '');
  const [subhead, setSubhead] = useState(initialCopy?.hero_subhead || '');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Live count computations
  const titleCount = title.length;
  const metaCount = meta.length;
  const heroWords = (headline + ' ' + subhead).trim().split(/\s+/).filter(Boolean).length;

  const countBadge = (text: string) => ({
    text,
    color: 'bg-paper-200 text-ink-700 border-line',
  });
  const titleBadge = countBadge(title ? `${titleCount} characters` : 'No title stored');
  const metaBadge = countBadge(meta ? `${metaCount} characters` : 'No meta stored');
  const heroBadge = countBadge(heroWords ? `${heroWords} words` : 'No hero stored');

  const copy = async (key: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(key);
    setTimeout(() => setCopiedField(null), 1800);
  };

  return (
    <div className="bg-paper-50 border border-line rounded-lg p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-good/10"></span>
            <h3 className="text-lg font-bold text-ink">
              Specialist copy
            </h3>
          </div>
          <p className="text-xs text-ink-500 mt-1">
            Character and word counts are measurements. A count is not a pass, a fail, or a required band.
          </p>
        </div>
        <span className="text-[11px] font-semibold text-ink-500 bg-paper-200 px-2.5 py-1 rounded">
          Unjudged until a specialist writes it
        </span>
      </div>

      <div className="space-y-5">
        {/* Title Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-ink-700 uppercase tracking-[0.04em]">
              Page title
            </label>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${titleBadge.color}`}>
                {titleBadge.text}
              </span>
              <button
                type="button"
                onClick={() => copy('title', title)}
                className="text-[11px] text-ink-700 hover:text-ink-700 font-semibold"
              >
                {copiedField === 'title' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full text-xs font-mono p-2.5 border border-line rounded-md bg-paper-50 focus:outline-hidden focus:ring-1 focus:ring-good/30"
          />
        </div>

        {/* Meta Description Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-ink-700 uppercase tracking-[0.04em]">
              Meta description
            </label>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${metaBadge.color}`}>
                {metaBadge.text}
              </span>
              <button
                type="button"
                onClick={() => copy('meta', meta)}
                className="text-[11px] text-ink-700 hover:text-ink-700 font-semibold"
              >
                {copiedField === 'meta' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <textarea
            value={meta}
            onChange={(e) => setMeta(e.target.value)}
            rows={2}
            className="w-full text-xs font-mono p-2.5 border border-line rounded-md bg-paper-50 focus:outline-hidden focus:ring-1 focus:ring-good/30"
          />
        </div>

        {/* Hero Section Copy */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-ink-700 uppercase tracking-[0.04em]">
              Hero headline and subhead
            </label>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${heroBadge.color}`}>
                {heroBadge.text}
              </span>
              <button
                type="button"
                onClick={() => copy('hero', `${headline}\n\n${subhead}`)}
                className="text-[11px] text-ink-700 hover:text-ink-700 font-semibold"
              >
                {copiedField === 'hero' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <div className="space-y-2">
            <input
              type="text"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              placeholder="Hero Headline"
              className="w-full text-xs font-semibold p-2.5 border border-line rounded-md bg-paper-50"
            />
            <textarea
              value={subhead}
              onChange={(e) => setSubhead(e.target.value)}
              placeholder="Hero Subheadline explaining non-fungible value proposition"
              rows={3}
              className="w-full text-xs p-2.5 border border-line rounded-md bg-paper-50"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
