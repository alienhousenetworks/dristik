import React, { useState } from 'react';
import { CharacterSafeCopy } from '../types';

interface CharacterSafeCopyWidgetProps {
  initialCopy?: CharacterSafeCopy;
}

export function CharacterSafeCopyWidget({ initialCopy }: CharacterSafeCopyWidgetProps) {
  const [title, setTitle] = useState(initialCopy?.title || 'Dristik AI — Enterprise Web Intelligence & Audit Platform');
  const [meta, setMeta] = useState(
    initialCopy?.meta_description ||
      'Dristik investigates your website with verified DOM evidence, Theory of Constraints bottlenecks, and post-patch generative search citation readiness.'
  );
  const [headline, setHeadline] = useState(
    initialCopy?.hero_headline || 'Autonomous Website Intelligence for Generative Search'
  );
  const [subhead, setSubhead] = useState(
    initialCopy?.hero_subhead ||
      'Eliminate AI answer engine blindness. Dristik audits commercial clarity, generates developer-ready patch packs, and proves before-and-after citation readiness across ChatGPT, Perplexity, and Google.'
  );
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Live count computations
  const titleCount = title.length;
  const metaCount = meta.length;
  const heroWords = (headline + ' ' + subhead).trim().split(/\s+/).filter(Boolean).length;

  const getTitleBadge = () => {
    if (titleCount >= 50 && titleCount <= 60) {
      return { text: `${titleCount}/60 chars (Compliant)`, color: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
    }
    if (titleCount < 50) {
      return { text: `${titleCount}/60 chars (Too Short — Under 50)`, color: 'bg-amber-100 text-amber-800 border-amber-300' };
    }
    return { text: `${titleCount}/60 chars (Too Long — Truncated in SERPs)`, color: 'bg-red-100 text-red-800 border-red-300' };
  };

  const getMetaBadge = () => {
    if (metaCount >= 140 && metaCount <= 160) {
      return { text: `${metaCount}/160 chars (Compliant)`, color: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
    }
    if (metaCount < 140) {
      return { text: `${metaCount}/160 chars (Too Short — Under 140)`, color: 'bg-amber-100 text-amber-800 border-amber-300' };
    }
    return { text: `${metaCount}/160 chars (Too Long — Truncated in SERPs)`, color: 'bg-red-100 text-red-800 border-red-300' };
  };

  const getHeroBadge = () => {
    if (heroWords >= 40 && heroWords <= 60) {
      return { text: `${heroWords}/60 words (Compliant)`, color: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
    }
    if (heroWords < 40) {
      return { text: `${heroWords}/60 words (Too Brief — Under 40 words)`, color: 'bg-amber-100 text-amber-800 border-amber-300' };
    }
    return { text: `${heroWords}/60 words (Wordy — Over 60 words)`, color: 'bg-red-100 text-red-800 border-red-300' };
  };

  const copy = async (key: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(key);
    setTimeout(() => setCopiedField(null), 1800);
  };

  const titleBadge = getTitleBadge();
  const metaBadge = getMetaBadge();
  const heroBadge = getHeroBadge();

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <h3 className="text-lg font-bold text-slate-900">
              Character-Safe Copy Assistant (Live Enforced)
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Enforces strict bounds so headlines and metas never get truncated in Google SERPs or AI context windows.
          </p>
        </div>
        <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded">
          Agency Reseller Specification
        </span>
      </div>

      <div className="space-y-5">
        {/* Title Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Page Title (50–60 characters)
            </label>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${titleBadge.color}`}>
                {titleBadge.text}
              </span>
              <button
                type="button"
                onClick={() => copy('title', title)}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold"
              >
                {copiedField === 'title' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full text-xs font-mono p-2.5 border border-slate-300 rounded-md bg-white focus:outline-hidden focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        {/* Meta Description Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Meta Description (140–160 characters)
            </label>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${metaBadge.color}`}>
                {metaBadge.text}
              </span>
              <button
                type="button"
                onClick={() => copy('meta', meta)}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold"
              >
                {copiedField === 'meta' ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <textarea
            value={meta}
            onChange={(e) => setMeta(e.target.value)}
            rows={2}
            className="w-full text-xs font-mono p-2.5 border border-slate-300 rounded-md bg-white focus:outline-hidden focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        {/* Hero Section Copy */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Hero Section (Headline + Subhead: 40–60 words)
            </label>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${heroBadge.color}`}>
                {heroBadge.text}
              </span>
              <button
                type="button"
                onClick={() => copy('hero', `${headline}\n\n${subhead}`)}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold"
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
              className="w-full text-xs font-semibold p-2.5 border border-slate-300 rounded-md bg-white"
            />
            <textarea
              value={subhead}
              onChange={(e) => setSubhead(e.target.value)}
              placeholder="Hero Subheadline explaining non-fungible value proposition"
              rows={3}
              className="w-full text-xs p-2.5 border border-slate-300 rounded-md bg-white"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
