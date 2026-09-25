import React, { useEffect, useState } from 'react';
import { PaymentVoucher, PricingPlan } from '../types';
import { getPlans } from '../services/api';
import { createPaymentOrder, launchRazorpayCheckout } from '../services/razorpay';

interface PricingModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetUrl: string;
  defaultPlanId?: string;
  onUnlocked: (planId: string, voucher: string, maxPages: number) => void;
}

export function PricingModal({
  isOpen,
  onClose,
  targetUrl,
  defaultPlanId = 'diagnostic',
  onUnlocked,
}: PricingModalProps) {
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [currency, setCurrency] = useState<'INR' | 'USD'>('INR');
  const [selected, setSelected] = useState<PricingPlan | null>(null);
  const [checkout, setCheckout] = useState(false);
  const [url, setUrl] = useState(targetUrl);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [gstin, setGstin] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voucher, setVoucher] = useState<PaymentVoucher | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setUrl(targetUrl);
    getPlans()
      .then((catalog) => {
        const all = [...(catalog.one_time_audits || []), ...(catalog.continuous_monitoring || [])];
        setPlans(all);
        const match = all.find((p) => p.id === defaultPlanId) || all.find((p) => p.id === 'diagnostic') || all[0] || null;
        setSelected(match);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Could not load plans.');
      });
  }, [isOpen, defaultPlanId, targetUrl]);

  if (!isOpen) return null;

  const pay = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    if (!url.trim()) {
      setError('Enter a website URL.');
      return;
    }

    if (selected.id === 'free_scan' || selected.price_inr === 0) {
      onUnlocked('free_scan', 'FREE_SCAN_ACTIVATED', 1);
      onClose();
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const order = await createPaymentOrder({
        plan_id: selected.id,
        target_url: url.trim(),
        customer_name: name.trim() || undefined,
        customer_email: email.trim() || undefined,
        company_name: company.trim() || undefined,
        gstin: gstin.trim() || undefined,
      });
      await launchRazorpayCheckout({
        order,
        customerName: name.trim() || undefined,
        customerEmail: email.trim() || undefined,
        onSuccess: (result) => {
          setBusy(false);
          setVoucher(result);
        },
        onFailure: (message) => {
          setBusy(false);
          setError(message);
        },
        onDismiss: () => setBusy(false),
      });
    } catch (err: unknown) {
      setBusy(false);
      setError(err instanceof Error ? err.message : 'Payment failed.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 scrim flex items-start justify-center overflow-y-auto p-4 sm:p-10" onClick={onClose}>
      <div className="sheet w-full max-w-3xl my-8 px-6 py-8 sm:px-10 rounded border border-line shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 border-b border-line pb-4">
          <div>
            <span className="label text-pine">Dristik AI Gateway · Direct Activation</span>
            <h2 className="font-serif text-3xl mt-1 text-ink">
              {voucher ? 'Diagnostic Sprint Unlocked' : checkout ? 'Complete Sprint Checkout' : 'Select an Intelligence Scope'}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="text-ink-500 hover:text-ink font-medium text-sm">
            ✕ Close
          </button>
        </div>

        {voucher && selected ? (
          <div className="mt-8 space-y-6 animate-fadeIn">
            <div className="p-4 bg-paper-100 rounded border border-good/40 text-good space-y-1">
              <p className="font-bold">✓ Payment verified & purchase receipt issued.</p>
              <p className="text-xs text-ink-700">Your voucher is active and ready to start the diagnostic crawl.</p>
            </div>
            <div>
              <span className="label text-ink-500">Authorization Code</span>
              <p className="font-mono text-xl text-ink font-bold mt-1">{voucher.voucher_code}</p>
            </div>
            <div>
              <span className="label text-ink-500">Authorized Target Domain</span>
              <p className="font-mono text-sm text-ink-700 mt-1">{displayUrl(voucher.target_url)}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                onUnlocked(selected.id, voucher.voucher_code, selected.limits?.max_pages || 15);
                onClose();
              }}
              className="btn-primary w-full py-3 text-sm font-bold rounded shadow"
            >
              Run Audit Now
            </button>
          </div>
        ) : checkout && selected ? (
          <form onSubmit={pay} className="mt-8 space-y-5 animate-fadeIn">
            <div className="flex items-baseline justify-between bg-paper-100 p-4 rounded border border-line">
              <div>
                <span className="label text-pine">{selected.badge || selected.tier}</span>
                <p className="font-serif text-2xl text-ink mt-0.5">{selected.name}</p>
                <p className="text-xs text-ink-600 mt-1">{selected.description}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="font-serif text-3xl text-ink">
                  {currency === 'INR' ? selected.price_display : `$${selected.price_usd}`}
                </p>
                <button
                  type="button"
                  onClick={() => setCheckout(false)}
                  className="text-xs text-pine underline mt-1 block"
                >
                  Change plan
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="block sm:col-span-2">
                <span className="label">Target Website URL *</span>
                <input
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://yourcompany.com"
                  className="mt-1 w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="label">Full Name</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  className="mt-1 w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="label">Work Email *</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="rahul@company.com"
                  className="mt-1 w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="label">Company / Legal Entity</span>
                <input
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Acme Technologies"
                  className="mt-1 w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="label">Billing Notes / PO (Optional)</span>
                <input
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value)}
                  placeholder="Optional reference or tax ID"
                  className="mt-1 w-full bg-paper-50 border border-line rounded px-3 py-2 text-sm text-ink font-mono focus:border-ink focus:outline-none"
                />
                <span className="text-[10px] text-ink-500 mt-0.5 block">
                  Flat transparent price · 0% added tax
                </span>
              </label>
            </div>

            {/* Indian Payment Methods Banner */}
            <div className="p-3 bg-paper-100 rounded border border-line text-xs text-ink-700 flex items-center justify-between">
              <span>Payment Methods: Instant UPI QR, NetBanking, Credit/Debit Cards</span>
              <span className="text-pine font-bold">0% Surcharge</span>
            </div>

            {error && <p className="text-sm text-bad font-medium">{error}</p>}

            <button
              type="submit"
              disabled={busy}
              className="btn-primary w-full py-3 text-sm font-bold rounded shadow disabled:opacity-50"
            >
              {busy ? 'Connecting to Razorpay Secure Gateway…' : `Pay ${currency === 'INR' ? selected.price_display : `$${selected.price_usd}`} & Launch Sprint`}
            </button>
          </form>
        ) : (
          <div className="mt-6 space-y-6">
            <div className="flex items-center justify-between">
              <p className="text-xs text-ink-600">Select a diagnostic scope to proceed to checkout.</p>
              <div className="flex gap-2 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setCurrency('INR')}
                  className={`px-2.5 py-1 rounded ${currency === 'INR' ? 'bg-pine text-paper-50' : 'bg-paper-100 text-ink-700'}`}
                >
                  ₹ INR
                </button>
                <button
                  type="button"
                  onClick={() => setCurrency('USD')}
                  className={`px-2.5 py-1 rounded ${currency === 'USD' ? 'bg-pine text-paper-50' : 'bg-paper-100 text-ink-700'}`}
                >
                  $ USD
                </button>
              </div>
            </div>

            {error && <p className="text-sm text-bad mb-4">{error}</p>}

            <ul className="divide-y divide-line border-y border-line">
              {plans.map((plan) => (
                <li key={plan.id} className="py-4 flex items-start justify-between gap-4 hover:bg-paper-100/50 p-2 rounded transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="font-serif text-xl text-ink">{plan.name}</p>
                      {plan.badge && (
                        <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase tracking-wider ${
                          plan.popular ? 'bg-pine text-paper-50' : 'bg-paper-300 text-ink-700'
                        }`}>
                          {plan.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-ink-600 max-w-md">{plan.description}</p>
                    <p className="text-[11px] text-ink-500 font-mono">
                      Crawl depth: {plan.limits?.max_pages || 5} pages · AI Scenarios: {plan.limits?.ai_scenarios || 3}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-serif text-2xl text-ink">
                      {currency === 'INR' ? plan.price_display : `$${plan.price_usd}`}
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setSelected(plan);
                        setCheckout(true);
                        setError(null);
                      }}
                      className="mt-1 px-3 py-1 bg-ink text-paper-50 hover:bg-pine rounded text-xs font-semibold transition-colors"
                    >
                      Select Plan
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function displayUrl(value?: string) {
  return value?.trim() ? value : '—';
}
