import React, { useState } from 'react';
import { ExecutiveReport } from '../../types';
import { PillarShell } from '../ui';

interface BrandEntityIntelligenceViewProps {
  report: ExecutiveReport;
}

type BrandSubTab = 'graph' | 'schema' | 'conflicts' | 'trust';

export function BrandEntityIntelligenceView({ report }: BrandEntityIntelligenceViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<BrandSubTab>('graph');

  const profile = report.business_profile;
  const semantic = report.semantic_business;
  const contradictions = report.contradictions || (semantic?.contradiction ? [semantic.contradiction] : []);
  const schemaTypes = report.geo_readiness?.schema_types || [];
  const rawTrust = report.scores?.category_scores?.['TRUST_AUTHORITY']?.score;
  const trustScore = typeof rawTrust === 'number' ? Math.round(rawTrust) : null;

  return (
    <PillarShell
      kicker="Brand"
      title="Entity, schema, and trust"
      description="Whether the business is consistent, structured, and corroborated across the pages we crawled."
      scoreLabel="Authority"
      score={trustScore ?? '—'}
      metaLabel="Conflicts"
      meta={contradictions.length}
      tabs={[
        { id: 'graph', label: 'Entity' },
        { id: 'schema', label: `Schema (${schemaTypes.length})` },
        { id: 'conflicts', label: `Conflicts (${contradictions.length})` },
        { id: 'trust', label: 'Trust' },
      ]}
      activeTab={activeSubTab}
      onTab={(id) => setActiveSubTab(id as BrandSubTab)}
    >

      {/* SUB-VIEW 1: ENTITY GRAPH */}
      {activeSubTab === 'graph' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Discovered Business Entity Representation</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-paper-50 border border-line p-3.5 rounded-lg space-y-1">
              <span className="label text-[10px] block">Legal / Brand Entity</span>
              <span className="font-semibold text-ink text-sm block">
                {profile?.business_name || report.domain}
              </span>
            </div>
            <div className="bg-paper-50 border border-line p-3.5 rounded-lg space-y-1">
              <span className="label text-[10px] block">Industry Classification</span>
              <span className="font-semibold text-ink text-sm block">
                {profile?.industry || '—'}
              </span>
            </div>
            <div className="bg-paper-50 border border-line p-3.5 rounded-lg space-y-1">
              <span className="label text-[10px] block">Target Geography</span>
              <span className="font-semibold text-ink text-sm block">
                {profile?.geography || '—'}
              </span>
            </div>
            <div className="bg-paper-50 border border-line p-3.5 rounded-lg space-y-1">
              <span className="label text-[10px] block">Disambiguation Status</span>
              <span className="font-semibold text-ink text-sm block">
                {profile?.business_name ? 'Name found on the crawl' : 'Not confirmed'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: SCHEMA VALIDATION */}
      {activeSubTab === 'schema' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Structured Data & JSON-LD Schema Validation</h3>
          <div className="space-y-3">
            <span className="label text-[10px] block">Extracted Schema Types</span>
            <div className="flex flex-wrap gap-2">
              {schemaTypes.length > 0 ? (
                schemaTypes.map((st, i) => (
                  <span key={i} className="px-3 py-1 bg-paper-100 dark:bg-ink-800 border border-line rounded-md font-mono text-xs text-ink font-medium">
                    🏷️ {st}
                  </span>
                ))
              ) : (
                <p className="text-xs text-ink-500">No JSON-LD schemas discovered.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: CONTRADICTION RADAR */}
      {activeSubTab === 'conflicts' && (
        <div className="space-y-4">
          {contradictions.length > 0 ? (
            contradictions.map((c, idx) => (
              <div key={idx} className="bg-amber-50 dark:bg-amber-950/30 border-l-4 border-amber-500 p-6 rounded-r-lg space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-amber-800 uppercase">
                    ⚠️ {c.contradiction_type || 'Business Identity Conflict'}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-200 text-amber-900">
                    {typeof c.confidence === 'number' ? `Confidence: ${Math.round(c.confidence * 100)}%` : 'Confidence not scored'}
                  </span>
                </div>
                <p className="text-sm text-ink-800 leading-relaxed">{c.reason}</p>
              </div>
            ))
          ) : (
            <div className="sheet border border-line rounded-lg p-6 text-center space-y-2">
              <span className="text-3xl">✅</span>
              <h4 className="font-serif text-xl font-bold text-ink">No identity conflict was recorded</h4>
              <p className="text-xs text-ink-500 max-w-md mx-auto">
                This audit did not store a contradiction. That is not a proof that every claim on the site agrees.
              </p>
            </div>
          )}
        </div>
      )}

      {/* SUB-VIEW 4: TRUST & REPUTATION */}
      {activeSubTab === 'trust' && (
        <div className="sheet border border-line rounded-lg p-6 space-y-6">
          <h3 className="font-serif text-2xl text-ink font-bold">Trust, Social Proof & Reputation Footprint</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Trust Authority Score</span>
              <span className="font-serif text-3xl font-bold text-ink">{trustScore == null ? '—' : `${trustScore} / 100`}</span>
              <span className="text-xs text-ink-500 block">{trustScore == null ? 'Not scored' : 'From this audit'}</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Privacy & Legal Compliance</span>
              <span className="font-serif text-3xl font-bold text-ink">—</span>
              <span className="text-xs text-ink-500 block">Privacy and terms links were not scored here.</span>
            </div>
            <div className="border border-line p-4 rounded-lg bg-paper-50 space-y-1">
              <span className="label text-[10px] block">Contact Accessibility</span>
              <span className="font-serif text-3xl font-bold text-ink">—</span>
              <span className="text-xs text-ink-500 block">Address and email were not checked on this card.</span>
            </div>
          </div>
        </div>
      )}
    </PillarShell>
  );
}
