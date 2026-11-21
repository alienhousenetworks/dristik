import React, { useState } from 'react';
import { Card } from '../../ui';
import { CroEnterpriseBundle } from '../../../services/croApi';
import { CheckCircle2, FileEdit, ShoppingCart, ShieldCheck, Smartphone, MousePointerClick } from 'lucide-react';

interface CroExperienceCopyFormsViewProps {
  bundle: CroEnterpriseBundle;
  section: 'copy' | 'forms_cta' | 'ecommerce' | 'ux_mobile_trust';
}

export function CroExperienceCopyFormsView({ bundle, section }: CroExperienceCopyFormsViewProps) {
  const [approvedCopies, setApprovedCopies] = useState<Record<string, boolean>>({});
  const [editedCopies, setEditedCopies] = useState<Record<string, string>>({});
  const [ctaDeviceFilter, setCtaDeviceFilter] = useState('all');
  const [checkoutViewport, setCheckoutViewport] = useState<'desktop' | 'mobile'>('desktop');

  // Phase 30 — Side-by-side Landing Page & Responsible Copywriting Workspace
  if (section === 'copy') {
    const lp = bundle.department_artifacts?.landing_copy_workspace || {};
    const proposals: any[] = lp.copy_proposals || [];
    const wireframe = lp.proposed_wireframe;
    const messageMatch = lp.message_match;
    const objections: string[] = lp.unanswered_objections || [];

    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-ink flex items-center gap-2">
              <FileEdit className="w-4 h-4" /> Landing Page &amp; Copywriting Studio (Approval Required)
            </h3>
            <p className="text-xs text-ink-600">
              Review original vs proposed conversion copy grounded strictly in audited facts. Production copy is never changed without explicit user approval.
            </p>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 rounded bg-paper-200 text-ink">
            Message Match: {(messageMatch?.status || 'unmeasured').toUpperCase()}
          </span>
        </div>

        {messageMatch?.status === 'unmeasured' && (
          <Card className="p-3.5 bg-paper-50 text-xs text-ink-600">
            <strong>Message Match Disclosure:</strong> {messageMatch.reason}
          </Card>
        )}

        <div className="space-y-4">
          {proposals.map((prop) => {
            const pid = prop.proposal_id;
            const currentVal = editedCopies[pid] ?? prop.recommended_copy;
            const isApproved = !!approvedCopies[pid];
            return (
              <Card key={pid} className="p-5 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-xs font-bold uppercase text-ink-500">
                    {prop.section.replace(/_/g, ' ')} · {prop.page_url}
                  </span>
                  <button
                    type="button"
                    onClick={() => setApprovedCopies((prev) => ({ ...prev, [pid]: !prev[pid] }))}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold ${
                      isApproved ? 'bg-good text-white' : 'border border-ink text-ink hover:bg-paper-100'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {isApproved ? 'Approved for Implementation' : 'Approve Copy Proposal'}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-line p-3.5 bg-paper-50 space-y-1.5">
                    <p className="text-[11px] font-mono uppercase text-ink-500">Original Observed Copy</p>
                    <p className="text-sm font-medium text-ink">{prop.original_copy}</p>
                    <p className="text-xs text-warn pt-1"><strong>Identified problem:</strong> {prop.identified_problem}</p>
                  </div>
                  <div className="rounded-lg border border-good/40 p-3.5 bg-good/5 space-y-1.5">
                    <p className="text-[11px] font-mono uppercase text-good">Proposed Replacement Copy (Editable)</p>
                    <textarea
                      rows={3}
                      value={currentVal}
                      onChange={(e) => setEditedCopies((prev) => ({ ...prev, [pid]: e.target.value }))}
                      className="w-full rounded border border-line bg-surface p-2 text-xs text-ink"
                    />
                    <p className="text-[11px] text-ink-600">{prop.reason_for_change}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-ink-600 pt-1">
                  <div>
                    <strong className="text-ink">Supporting Source Facts:</strong> {(prop.supporting_source_facts || []).join(' · ')}
                  </div>
                  <div>
                    <strong className="text-ink">Risks &amp; Assumptions:</strong> {(prop.risks_and_assumptions || []).join(' ')}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {objections.length > 0 && (
          <Card className="p-4 space-y-2">
            <h4 className="text-xs font-bold uppercase font-mono text-ink-500">Unanswered Buyer Objections</h4>
            <div className="flex flex-wrap gap-2">
              {objections.map((obj) => (
                <span key={obj} className="px-2.5 py-1 text-xs rounded-full bg-warn/10 text-warn border border-warn/20">
                  {obj}
                </span>
              ))}
            </div>
          </Card>
        )}

        {wireframe && (
          <Card className="p-5 space-y-3 border-dashed">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-bold text-ink">Proposed Landing Page Wireframe</h4>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-warn/15 text-warn font-bold">
                Recommendation Only — Not a Live Implementation
              </span>
            </div>
            <p className="text-xs text-ink-500">{wireframe.disclosure}</p>
            <div className="space-y-2">
              {(wireframe.recommended_section_order || []).map((s: any) => (
                <div key={s.order} className="flex items-center gap-3 p-2.5 rounded border border-line bg-paper-50 text-xs">
                  <span className="font-mono font-bold text-ink-500">0{s.order}</span>
                  <span className="font-semibold text-ink w-56">{s.section}</span>
                  <span className="text-ink-600">{s.purpose}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    );
  }

  // Phase 31 — Connected Forms & CTA Explorers
  if (section === 'forms_cta') {
    const fc = bundle.department_artifacts?.forms_cta_workspace || {};
    const formsReg: any[] = fc.forms_registry || [];
    const ctas = bundle.ctas.filter((c) => ctaDeviceFilter === 'all' || c.device === ctaDeviceFilter);

    return (
      <div className="space-y-6">
        <Card className="p-5 space-y-3">
          <h3 className="text-sm font-bold text-ink">Form Intelligence Explorer ({formsReg.length} Form(s))</h3>
          <p className="text-xs text-ink-500">
            Balances form completion friction against sales qualification quality; never blindly recommends deleting mandatory qualification fields.
          </p>
          {formsReg.length === 0 ? (
            <p className="text-xs text-ink-500">No interactive forms detected in the audited pages.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[780px]">
                <thead>
                  <tr className="border-b border-line font-mono text-ink-500">
                    <th className="py-2 pr-3">Form ID</th>
                    <th className="py-2 pr-3">URL</th>
                    <th className="py-2 pr-3">Fields (Req)</th>
                    <th className="py-2 pr-3">Missing Labels</th>
                    <th className="py-2 pr-3">Validation</th>
                    <th className="py-2 pr-3">Submission Test</th>
                    <th className="py-2">Qualification Trade-Off Note</th>
                  </tr>
                </thead>
                <tbody>
                  {formsReg.map((f) => (
                    <tr key={f.element_id || f.form_id} className="border-b border-line align-top">
                      <td className="py-2.5 pr-3 font-mono font-semibold">{f.form_id}</td>
                      <td className="py-2.5 pr-3 font-mono truncate max-w-[180px]">{f.url}</td>
                      <td className="py-2.5 pr-3 font-mono">{f.field_count} ({f.required_fields})</td>
                      <td className={`py-2.5 pr-3 font-mono ${f.missing_labels > 0 ? 'text-bad font-bold' : 'text-good'}`}>{f.missing_labels}</td>
                      <td className="py-2.5 pr-3 font-mono uppercase">{f.validation_state}</td>
                      <td className="py-2.5 pr-3 font-mono uppercase">{f.submission_test_state}</td>
                      <td className="py-2.5 text-ink-600">{f.qualification_tradeoff_note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card className="p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-ink flex items-center gap-2">
              <MousePointerClick className="w-4 h-4" /> CTA Intelligence Registry ({ctas.length})
            </h3>
            <select
              value={ctaDeviceFilter}
              onChange={(e) => setCtaDeviceFilter(e.target.value)}
              className="px-2.5 py-1 text-xs rounded border border-line bg-surface"
            >
              <option value="all">All devices</option>
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[780px]">
              <thead>
                <tr className="border-b border-line font-mono text-ink-500">
                  <th className="py-2 pr-3">CTA Text</th>
                  <th className="py-2 pr-3">Hierarchy</th>
                  <th className="py-2 pr-3">Intent</th>
                  <th className="py-2 pr-3">Section</th>
                  <th className="py-2 pr-3">Destination</th>
                  <th className="py-2">Interaction Result</th>
                </tr>
              </thead>
              <tbody>
                {ctas.slice(0, 40).map((c, i) => (
                  <tr key={c.element_id || i} className="border-b border-line">
                    <td className="py-2 pr-3 font-semibold text-ink">{c.text || '(Unlabeled)'}</td>
                    <td className="py-2 pr-3 font-mono uppercase">{c.cta_hierarchy || 'secondary'}</td>
                    <td className="py-2 pr-3 font-mono">{c.intent_category || 'exploratory'}</td>
                    <td className="py-2 pr-3 font-mono">{c.section}</td>
                    <td className="py-2 pr-3 font-mono truncate max-w-[200px]">{c.destination || '—'}</td>
                    <td className={`py-2 font-mono font-bold ${c.clickable === false ? 'text-bad' : 'text-good'}`}>
                      {c.interaction_result}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }

  // Phase 32 — Ecommerce & Checkout Workspace
  if (section === 'ecommerce') {
    const ecom = bundle.department_artifacts?.ecommerce_audit || { applicable: false };
    return (
      <div className="space-y-5">
        <Card className="p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-bold text-ink flex items-center gap-2">
              <ShoppingCart className="w-4 h-4" /> Ecommerce Product, Cart &amp; Checkout Workspace
            </h3>
            <div className="flex gap-1.5">
              {(['desktop', 'mobile'] as const).map((vp) => (
                <button
                  key={vp}
                  type="button"
                  onClick={() => setCheckoutViewport(vp)}
                  className={`px-2.5 py-1 text-xs rounded border capitalize ${
                    checkoutViewport === vp ? 'bg-ink text-white border-ink' : 'border-line text-ink-600'
                  }`}
                >
                  {vp} checkout view
                </button>
              ))}
            </div>
          </div>
          {!ecom.applicable ? (
            <p className="text-xs text-ink-600">
              {ecom.reason || 'Ecommerce module is not applicable to the configured business model. Switch Business Profile to Ecommerce to inspect product/cart/checkout flows.'}
            </p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded border border-line"><p className="text-ink-500">Product Pages</p><p className="text-lg font-bold">{ecom.product_pages_count}</p></div>
              <div className="p-3 rounded border border-line"><p className="text-ink-500">Guest Checkout</p><p className="text-sm font-mono font-bold uppercase mt-1">{ecom.guest_checkout_status}</p></div>
              <div className="p-3 rounded border border-line"><p className="text-ink-500">Shipping Policy</p><p className="text-sm font-bold mt-1">{ecom.shipping_policy_detected ? 'Observed' : 'Missing'}</p></div>
              <div className="p-3 rounded border border-line"><p className="text-ink-500">Returns Policy</p><p className="text-sm font-bold mt-1">{ecom.returns_policy_detected ? 'Observed' : 'Missing'}</p></div>
              <div className="p-3 rounded border border-line col-span-2"><p className="text-ink-500">Payment Methods Observed ({checkoutViewport})</p><p className="text-xs font-mono mt-1">{(ecom.payment_methods_observed || []).join(', ') || 'None observed'}</p></div>
              <div className="p-3 rounded border border-line col-span-2"><p className="text-ink-500">Live Payment Testing Guardrail</p><p className="text-xs font-mono mt-1 text-warn">{ecom.live_payment_testing}</p></div>
            </div>
          )}
        </Card>
      </div>
    );
  }

  // UX, UI, Trust, Mobile, Accessibility & Performance combined deep-dive
  const ux = bundle.department_artifacts?.ux_mobile_a11y || {};
  const trust = bundle.department_artifacts?.trust_audit || {};
  const perf = bundle.department_artifacts?.performance_tech || {};
  const worst = perf.worst_metrics || {};

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="p-5 space-y-3">
        <h4 className="text-sm font-bold text-ink flex items-center gap-2">
          <Smartphone className="w-4 h-4" /> Mobile &amp; WCAG 2.2 AA Accessibility
        </h4>
        <div className="text-xs space-y-1.5 text-ink-600">
          <p>Overflow URLs: <strong className="text-ink">{(ux.mobile_overflow_urls || []).length}</strong></p>
          <p>Missing viewport meta: <strong className="text-ink">{(ux.missing_viewport_urls || []).length}</strong></p>
          <p>Undersized touch targets: <strong className="text-ink">{ux.small_touch_targets ?? 0}</strong></p>
          <p>Automated WCAG violations: <strong className="text-ink">{ux.wcag_summary?.total_violations_found ?? 0}</strong></p>
        </div>
        <p className="text-[11px] text-ink-500 border-t border-line pt-2">
          {ux.wcag_disclaimer || 'Automated accessibility screening is not proof of complete WCAG conformance; manual assistive-technology testing is required.'}
        </p>
      </Card>

      <Card className="p-5 space-y-3">
        <h4 className="text-sm font-bold text-ink flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" /> Trust, Proof &amp; Policy Transparency
        </h4>
        <div className="text-xs space-y-1.5 text-ink-600">
          {Object.entries(trust.coverage_map || {}).map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-line pb-1">
              <span className="capitalize">{k.replace(/_/g, ' ')}</span>
              <span className="font-mono font-semibold text-ink">{Array.isArray(v) ? v.length : String(v)}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-5 space-y-3">
        <h4 className="text-sm font-bold text-ink">Performance &amp; Interaction Quality</h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2.5 rounded border border-line"><p className="text-ink-500">LCP (ms)</p><p className="font-mono font-bold">{worst.lcp_ms ?? 'Unmeasured'}</p></div>
          <div className="p-2.5 rounded border border-line"><p className="text-ink-500">INP (ms)</p><p className="font-mono font-bold">{worst.inp_ms ?? 'Unmeasured'}</p></div>
          <div className="p-2.5 rounded border border-line"><p className="text-ink-500">CLS</p><p className="font-mono font-bold">{worst.cls_score ?? 'Unmeasured'}</p></div>
          <div className="p-2.5 rounded border border-line"><p className="text-ink-500">TTFB (ms)</p><p className="font-mono font-bold">{worst.ttfb_ms ?? 'Unmeasured'}</p></div>
        </div>
        <p className="text-[11px] text-ink-500">
          Console errors: {perf.console_errors_count ?? 0} · Render-blocking scripts: {perf.render_blocking_scripts_count ?? 0}. Lab measurements do not represent all visitors.
        </p>
      </Card>
    </div>
  );
}
