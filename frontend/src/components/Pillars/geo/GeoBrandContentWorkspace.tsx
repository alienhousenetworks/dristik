import React, { useState } from 'react';
import { Card } from '../../ui';
import { GeoEnterpriseBundle, GeoPageRecord, geoApi } from '../../../services/geoApi';
import { Building2, CheckCircle2, FileText, Globe, Lock, ShieldCheck } from 'lucide-react';

interface GeoBrandContentWorkspaceProps {
  bundle: GeoEnterpriseBundle;
  section: 'brand' | 'products' | 'content' | 'external_authority';
  onRefreshBundle: (auditId?: string) => Promise<void>;
}

export function GeoBrandContentWorkspace({ bundle, section, onRefreshBundle }: GeoBrandContentWorkspaceProps) {
  const [attrName, setAttrName] = useState('headquarters');
  const [attrValue, setAttrValue] = useState('');
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState<GeoPageRecord | null>(bundle.pages[0] || null);

  const handleApproveFact = async () => {
    if (!attrName.trim() || !attrValue.trim()) return;
    setSaveMsg(null);
    try {
      await geoApi.approveEntity({
        audit_id: bundle.audit.audit_id,
        entity_type: 'organization',
        entity_name: bundle.audit.brand_name,
        attribute: attrName.trim(),
        value: attrValue.trim(),
      });
      setAttrValue('');
      setSaveMsg('Official brand fact approved and locked against automatic AI overwrites.');
      await onRefreshBundle(bundle.audit.audit_id);
    } catch (err: any) {
      setSaveMsg(err?.message || 'Approval requires Reviewer/Admin permission.');
    }
  };

  if (section === 'brand') {
    const artA = bundle.department_artifacts?.department_a || {};
    const conflicts: Array<Record<string, any>> = [...(artA.inconsistencies || []), ...(artA.ai_conflicts || [])];
    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
                <Building2 className="w-4 h-4 text-pine" /> Brand Knowledge Profile &amp; Entity Consistency ({bundle.entities.length} Facts)
              </h3>
              <p className="text-xs text-ink-500">
                Approved facts are locked against AI overwrites. Conflicting AI responses open evidence-backed findings instead of mutating official records.
              </p>
            </div>
            <span className="font-mono text-xs font-bold px-2.5 py-1 rounded bg-paper-100 border border-line">
              Consistency: {artA.consistency_score != null ? `${artA.consistency_score}/100` : 'Unmeasured'}
            </span>
          </div>

          {/* Approve Official Fact Form */}
          <div className="p-3 rounded border border-line bg-paper-50 flex flex-wrap gap-2 items-center text-xs">
            <Lock className="w-4 h-4 text-pine shrink-0" />
            <input
              value={attrName}
              onChange={(e) => setAttrName(e.target.value)}
              placeholder="Attribute (e.g. founding_year, headquarters, pricing_model)"
              className="px-2.5 py-1.5 border border-line rounded bg-white w-56"
            />
            <input
              value={attrValue}
              onChange={(e) => setAttrValue(e.target.value)}
              placeholder="Verified official value..."
              className="px-2.5 py-1.5 border border-line rounded bg-white flex-1 min-w-[200px]"
            />
            <button type="button" onClick={handleApproveFact} className="px-3 py-1.5 bg-pine text-white font-semibold rounded">
              Approve Official Fact
            </button>
          </div>
          {saveMsg && <p className="text-xs font-mono text-pine">{saveMsg}</p>}

          <div className="overflow-x-auto border border-line rounded">
            <table className="w-full text-xs text-left">
              <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
                <tr>
                  <th className="p-2.5">Entity / Type</th>
                  <th className="p-2.5">Attribute</th>
                  <th className="p-2.5">Value</th>
                  <th className="p-2.5">Source</th>
                  <th className="p-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {bundle.entities.map((e) => (
                  <tr key={e.entity_id} className="hover:bg-paper-50">
                    <td className="p-2.5 font-semibold text-ink">{e.entity_name} <span className="font-mono text-[10px] text-ink-500">({e.entity_type})</span></td>
                    <td className="p-2.5 font-mono text-[11px]">{e.attribute}</td>
                    <td className="p-2.5 text-ink-700">{Array.isArray(e.value) ? e.value.join(', ') || '—' : String(e.value ?? '—')}</td>
                    <td className="p-2.5 font-mono text-[10px] text-ink-500">{e.source} ({e.source_ownership})</td>
                    <td className="p-2.5">
                      <span className={`font-mono text-[10px] uppercase px-1.5 py-0.5 rounded font-bold ${e.fact_status === 'confirmed' ? 'bg-good/10 text-good' : 'bg-warn/10 text-warn'}`}>
                        {e.fact_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {conflicts.length > 0 && (
          <Card className="p-5 space-y-2 border-l-4 border-l-bad">
            <h4 className="font-sans font-bold text-ink text-sm">Detected Entity &amp; AI Representation Conflicts ({conflicts.length})</h4>
            {conflicts.map((c, idx) => (
              <div key={idx} className="p-2.5 bg-bad/5 rounded text-xs text-ink-700">
                <strong>{c.title || c.platform_id || 'Conflict'}:</strong> {c.detail || c.note}
              </div>
            ))}
          </Card>
        )}
      </div>
    );
  }

  if (section === 'products') {
    const productEntities = bundle.entities.filter((e) => e.entity_type === 'product' || e.entity_type === 'service');
    const productMentions = bundle.mentions.filter((m) => m.entity_kind === 'product');
    return (
      <Card className="p-5 space-y-4">
        <h3 className="font-sans font-bold text-ink text-base">Product &amp; Service Entity Representation</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded border border-line bg-paper-50 space-y-2">
            <h4 className="font-mono text-xs uppercase font-bold text-ink-600">Registered Products &amp; Services ({productEntities.length})</h4>
            {productEntities.length === 0 ? (
              <p className="text-xs text-ink-500">Add products/services in GEO audit scope to evaluate product-level AI visibility.</p>
            ) : (
              <ul className="space-y-1.5 text-xs">
                {productEntities.map((pe) => (
                  <li key={pe.entity_id} className="flex items-center justify-between p-2 bg-white rounded border border-line">
                    <span className="font-semibold text-ink">{pe.entity_name}</span>
                    <span className="font-mono text-[10px] text-good uppercase">{pe.fact_status}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="p-4 rounded border border-line bg-paper-50 space-y-2">
            <h4 className="font-mono text-xs uppercase font-bold text-ink-600">Observed Product Mentions ({productMentions.length})</h4>
            {productMentions.length === 0 ? (
              <p className="text-xs text-ink-500">No product-specific mentions captured in live responses yet.</p>
            ) : (
              <ul className="space-y-1.5 text-xs">
                {productMentions.slice(0, 8).map((pm) => (
                  <li key={pm.mention_id} className="p-2 bg-white rounded border border-line">
                    <div className="font-semibold text-ink">{pm.entity_name} ({pm.platform_id})</div>
                    <p className="text-[11px] text-ink-600">{pm.context_snippet}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Card>
    );
  }

  if (section === 'external_authority') {
    return (
      <Card className="p-5 space-y-4">
        <div>
          <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
            <Globe className="w-4 h-4 text-pine" /> External Authority, Publications &amp; Reputation ({bundle.external_sources.length})
          </h3>
          <p className="text-xs text-ink-500">
            Independent third-party sources observed in AI citations and public references. Directory count is never turned into an artificial authority score.
          </p>
        </div>
        {bundle.external_sources.length === 0 ? (
          <p className="text-xs text-ink-500">No external sources observed in this run. Execute search-grounded AI tests to populate independent source provenance.</p>
        ) : (
          <div className="overflow-x-auto border border-line rounded">
            <table className="w-full text-xs text-left">
              <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
                <tr>
                  <th className="p-2.5">Domain / Publisher</th>
                  <th className="p-2.5">Category</th>
                  <th className="p-2.5">Independent</th>
                  <th className="p-2.5">Cited Count</th>
                  <th className="p-2.5">Brand Present</th>
                  <th className="p-2.5">Competitors</th>
                  <th className="p-2.5">Recommended Contribution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {bundle.external_sources.map((s) => (
                  <tr key={s.source_id} className="hover:bg-paper-50">
                    <td className="p-2.5 font-semibold text-ink">{s.domain}</td>
                    <td className="p-2.5 font-mono text-[10px]">{s.source_category}</td>
                    <td className="p-2.5 font-mono text-[10px]">{s.is_independent ? 'Yes' : 'No'}</td>
                    <td className="p-2.5 font-mono">{s.citation_count}</td>
                    <td className="p-2.5 font-mono text-[10px]">{s.brand_present ? 'Observed' : 'Absent'}</td>
                    <td className="p-2.5 text-[11px]">{s.competitors_present.join(', ') || '—'}</td>
                    <td className="p-2.5 text-[11px] text-ink-600">{s.potential_contribution}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    );
  }

  // Content Readiness Page Inventory + Detail Inspector
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="p-5 lg:col-span-2 space-y-3">
        <h3 className="font-sans font-bold text-ink text-base flex items-center gap-2">
          <FileText className="w-4 h-4 text-pine" /> Website Content &amp; Retrieval Readiness Inventory ({bundle.pages.length} Pages)
        </h3>
        <div className="overflow-x-auto border border-line rounded">
          <table className="w-full text-xs text-left">
            <thead className="bg-paper-100 font-mono text-[10px] uppercase text-ink-600 border-b border-line">
              <tr>
                <th className="p-2.5">URL</th>
                <th className="p-2.5">Type</th>
                <th className="p-2.5">Words</th>
                <th className="p-2.5">Readiness</th>
                <th className="p-2.5">Issues</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {bundle.pages.map((p) => (
                <tr
                  key={p.page_id}
                  onClick={() => setSelectedPage(p)}
                  className={`cursor-pointer hover:bg-paper-50 ${selectedPage?.page_id === p.page_id ? 'bg-pine/5' : ''}`}
                >
                  <td className="p-2.5 font-mono text-[11px] max-w-xs truncate text-pine">{p.url}</td>
                  <td className="p-2.5 font-mono text-[10px] uppercase">{p.page_type}</td>
                  <td className="p-2.5 font-mono">{p.word_count}</td>
                  <td className="p-2.5 font-mono font-bold">{p.overall_readiness_score != null ? `${p.overall_readiness_score}/100` : '—'}</td>
                  <td className="p-2.5 font-mono">{p.content_issues.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-5 space-y-3">
        <h4 className="font-sans font-bold text-ink text-sm flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-pine" /> Page Detail Inspector
        </h4>
        {selectedPage ? (
          <div className="space-y-3 text-xs">
            <div className="font-mono text-[11px] text-pine break-all">{selectedPage.url}</div>
            <div className="grid grid-cols-2 gap-2 font-mono text-[10px]">
              <div className="p-2 rounded bg-paper-50 border border-line">Clarity: {selectedPage.clarity_score ?? '—'}</div>
              <div className="p-2 rounded bg-paper-50 border border-line">Extractability: {selectedPage.extractability_score ?? '—'}</div>
              <div className="p-2 rounded bg-paper-50 border border-line">Freshness: {selectedPage.freshness_score ?? '—'}</div>
              <div className="p-2 rounded bg-paper-50 border border-line">Trust: {selectedPage.trust_score ?? '—'}</div>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase text-ink-500 font-bold mb-1">Schema Types</div>
              <p className="text-[11px]">{selectedPage.schema_types.join(', ') || 'None detected'}</p>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase text-ink-500 font-bold mb-1">Extracted Content Preview</div>
              <p className="p-2 bg-paper-50 border border-line rounded text-[11px] text-ink-700 max-h-32 overflow-y-auto">
                {selectedPage.extracted_text_preview || 'No text preview available.'}
              </p>
            </div>
            {selectedPage.recommendations.length > 0 && (
              <div>
                <div className="font-mono text-[10px] uppercase text-ink-500 font-bold mb-1">Proposed Changes</div>
                <ul className="list-disc pl-4 space-y-1 text-[11px] text-ink-700">
                  {selectedPage.recommendations.map((rec, i) => <li key={i}>{rec}</li>)}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-ink-500">Select a page row to inspect extracted content, schema, and recommendations.</p>
        )}
      </Card>
    </div>
  );
}
