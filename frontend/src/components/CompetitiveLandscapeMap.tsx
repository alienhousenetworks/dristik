import React, { useState } from 'react';
import { LandscapeCoordinates, CompetitorProfile } from '../types';
import { Card, Badge } from './ui';
import { Target, Info, Sparkles, Search, Compass, ShieldAlert } from 'lucide-react';

interface CompetitiveLandscapeMapProps {
  targetDomain: string;
  targetBrand: string;
  coordinates: Record<string, LandscapeCoordinates>;
  competitors: CompetitorProfile[];
}

export function CompetitiveLandscapeMap({
  targetDomain,
  targetBrand,
  coordinates,
  competitors,
}: CompetitiveLandscapeMapProps) {
  const [hoveredDomain, setHoveredDomain] = useState<string | null>(null);

  const targetCoords = coordinates[targetDomain] || {
    x: 0.5,
    y: 0.5,
    x_confidence: 'MEDIUM',
    y_confidence: 'MEDIUM',
  };

  // Convert (0.0 - 1.0) to SVG viewBox percentages (padding: 10% to 90%)
  const toSvgX = (x: number) => 10 + x * 80;
  // SVG Y is inverted (0 at top, 100 at bottom)
  const toSvgY = (y: number) => 90 - y * 80;

  return (
    <Card className="p-6 space-y-5 bg-card border border-border/70 rounded-xl shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-indigo-500" />
            <h3 className="font-serif text-lg font-semibold text-ink">
              Dynamic Competitive Landscape Map
            </h3>
            <Badge tone="pine" className="text-xs">
              Evidence-Derived
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            2D continuous positioning derived from measured Search Overlap (X) and GEO / AI Citation Retrieval (Y). Zero hardcoded coordinates.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block ring-2 ring-emerald-200 dark:ring-emerald-900" />
            <span className="text-ink font-medium">{targetBrand} (Target)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-indigo-500 inline-block" />
            <span className="text-muted-foreground">Discovered Competitors</span>
          </div>
        </div>
      </div>

      {/* 2D Landscape Scatter Canvas */}
      <div className="relative w-full aspect-[16/10] max-h-[460px] bg-slate-900/5 dark:bg-slate-950/60 rounded-xl border border-border p-4 overflow-hidden select-none">
        {/* Quadrant Background Watermarks */}
        <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 p-6 pointer-events-none text-muted-foreground/30 font-medium text-xs">
          <div className="border-r border-b border-border/40 flex flex-col justify-between p-3">
            <span className="text-sky-600/60 dark:text-sky-400/60 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> AI Engine Native
            </span>
            <span className="text-[10px] text-muted-foreground/50">High AI Citation · Lower Search</span>
          </div>
          <div className="border-b border-border/40 flex flex-col justify-between p-3 text-right">
            <span className="text-emerald-600/70 dark:text-emerald-400/70 font-semibold flex items-center justify-end gap-1">
              <Target className="w-3.5 h-3.5" /> Omni-Dominant
            </span>
            <span className="text-[10px] text-muted-foreground/50">Top Tier: Search + AI Dominance</span>
          </div>
          <div className="border-r border-border/40 flex flex-col justify-between p-3">
            <span className="text-slate-500/60">Emerging / Niche</span>
            <span className="text-[10px] text-muted-foreground/50">Early Search & AI Traction</span>
          </div>
          <div className="flex flex-col justify-between p-3 text-right">
            <span className="text-amber-600/60 dark:text-amber-400/60 flex items-center justify-end gap-1">
              <Search className="w-3.5 h-3.5" /> Legacy SERP Giant
            </span>
            <span className="text-[10px] text-muted-foreground/50">Strong Organic · Weak in AI Models</span>
          </div>
        </div>

        {/* SVG Plane */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {/* Axis Guidelines */}
          <line x1="50" y1="5" x2="50" y2="95" stroke="currentColor" strokeOpacity="0.15" strokeDasharray="2,2" strokeWidth="0.5" />
          <line x1="5" y1="50" x2="95" y2="50" stroke="currentColor" strokeOpacity="0.15" strokeDasharray="2,2" strokeWidth="0.5" />

          {/* Competitors Nodes */}
          {competitors.map((comp) => {
            const coords = coordinates[comp.canonical_domain] || { x: 0.4, y: 0.4, x_confidence: 'LOW', y_confidence: 'LOW' };
            const cx = toSvgX(coords.x);
            const cy = toSvgY(coords.y);
            const isHovered = hoveredDomain === comp.canonical_domain;
            const isUnmeasured = coords.x_confidence === 'UNMEASURED' || coords.y_confidence === 'UNMEASURED';

            return (
              <g
                key={comp.id}
                className="cursor-pointer transition-all duration-200"
                onMouseEnter={() => setHoveredDomain(comp.canonical_domain)}
                onMouseLeave={() => setHoveredDomain(null)}
              >
                {/* Confidence ring */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 4.5 : 3}
                  className={`${
                    isUnmeasured
                      ? 'stroke-slate-400 fill-slate-300 dark:fill-slate-800'
                      : 'stroke-indigo-400 fill-indigo-600/90'
                  } transition-all`}
                  strokeWidth={isUnmeasured ? 0.8 : 1.2}
                  strokeDasharray={isUnmeasured ? '1,1' : undefined}
                />
                {/* Label */}
                <text
                  x={cx}
                  y={cy - 3.5}
                  textAnchor="middle"
                  className="text-[3.2px] font-sans font-medium fill-slate-700 dark:fill-slate-200 pointer-events-none"
                >
                  {comp.company_name}
                </text>
              </g>
            );
          })}

          {/* Target Domain Node */}
          <g
            className="cursor-pointer"
            onMouseEnter={() => setHoveredDomain(targetDomain)}
            onMouseLeave={() => setHoveredDomain(null)}
          >
            {/* Halo pulse */}
            <circle
              cx={toSvgX(targetCoords.x)}
              cy={toSvgY(targetCoords.y)}
              r={hoveredDomain === targetDomain ? 5.5 : 4}
              className="fill-emerald-500/20 stroke-emerald-500 animate-pulse"
              strokeWidth="0.8"
            />
            <circle
              cx={toSvgX(targetCoords.x)}
              cy={toSvgY(targetCoords.y)}
              r="2.5"
              className="fill-emerald-600 dark:fill-emerald-400"
            />
            <text
              x={toSvgX(targetCoords.x)}
              y={toSvgY(targetCoords.y) - 4}
              textAnchor="middle"
              className="text-[3.4px] font-sans font-bold fill-emerald-700 dark:fill-emerald-300 pointer-events-none"
            >
              {targetBrand} (You)
            </text>
          </g>
        </svg>

        {/* Hover Inspection Tooltip */}
        {hoveredDomain && (
          <div className="absolute bottom-3 left-4 right-4 sm:right-auto sm:max-w-xs bg-popover/95 backdrop-blur-md border border-border p-3 rounded-lg shadow-lg text-xs z-20 space-y-1.5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-ink">
                {hoveredDomain === targetDomain ? `${targetBrand} (Target)` : hoveredDomain}
              </span>
              <Badge tone="neutral" className="text-[10px] capitalize">
                {hoveredDomain === targetDomain ? 'Target Site' : 'Competitor'}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-border/50">
              <div>
                <span className="text-muted-foreground block">Search Visibility:</span>
                <span className="font-semibold text-ink">
                  {Math.round((coordinates[hoveredDomain]?.x || 0) * 100)}%
                </span>
                <span className="text-[10px] text-muted-foreground block">
                  ({coordinates[hoveredDomain]?.x_confidence || 'UNMEASURED'})
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">GEO / AI Visibility:</span>
                <span className="font-semibold text-ink">
                  {Math.round((coordinates[hoveredDomain]?.y || 0) * 100)}%
                </span>
                <span className="text-[10px] text-muted-foreground block">
                  ({coordinates[hoveredDomain]?.y_confidence || 'UNMEASURED'})
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Axis Descriptions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-muted-foreground pt-1">
        <div className="flex items-start gap-2">
          <Search className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
          <span>
            <strong className="text-ink">X-Axis (Search Visibility)</strong>: Weighted keyword overlap, commercial intent coverage, and estimated organic CTR visibility.
          </span>
        </div>
        <div className="flex items-start gap-2">
          <Sparkles className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
          <span>
            <strong className="text-ink">Y-Axis (GEO Visibility)</strong>: AI prompt overlap, citation frequency, and answer engine inclusion rates across ChatGPT & Perplexity.
          </span>
        </div>
      </div>
    </Card>
  );
}
