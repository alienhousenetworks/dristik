import React, { useState } from 'react';

interface GstInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  domain: string;
  planName?: string;
  amountInr?: number;
}

export function GstInvoiceModal({
  isOpen,
  onClose,
  domain,
  planName = 'Dristik Diagnostic Sprint',
  amountInr = 4999,
}: GstInvoiceModalProps) {
  const [customerName, setCustomerName] = useState('Founding Team');
  const [customerEmail, setCustomerEmail] = useState('finance@company.com');
  const [companyName, setCompanyName] = useState('Client Technologies');
  const [poRef, setPoRef] = useState('PO-2026-001');
  const [stateCode, setStateCode] = useState('General');
  const [invoice, setInvoice] = useState<any>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [paymentMode, setPaymentMode] = useState<'invoice' | 'upi'>('invoice');

  if (!isOpen) return null;

  const totalAmount = amountInr;

  const handleGenerateInvoice = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch('/api/v1/payments/invoice', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: `diagnostic_${domain.replace('.', '_')}`,
          customer_name: customerName,
          customer_email: customerEmail,
          company_name: companyName,
          gstin: poRef,
          state_code: stateCode,
          address: 'India',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setInvoice(data);
      }
    } catch (err) {
      console.error('Invoice error:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const upiIntent = `upi://pay?pa=dristik@icici&pn=Dristik+AI&am=${totalAmount}&cu=INR&tn=Dristik+Diagnostic+${domain}`;

  return (
    <div className="scrim fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
      <div className="sheet rounded-lg shadow-xl max-w-2xl w-full border border-line overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-line flex items-center justify-between bg-paper-50 text-ink">
          <div>
            <span className="label text-[10px] text-good">
              Direct Business Gateway
            </span>
            <h2 className="text-base font-sans font-bold text-ink">
              Commercial Purchase Receipt & UPI Checkout
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-400 hover:text-ink text-lg font-bold"
          >
            ✕
          </button>
        </div>

        {/* Tab Toggle */}
        <div className="flex border-b border-line bg-paper-100 text-xs">
          <button
            type="button"
            onClick={() => setPaymentMode('invoice')}
            className={`flex-1 py-2.5 text-center font-bold border-b-2 transition-colors ${
              paymentMode === 'invoice'
                ? 'border-line text-ink-700 bg-paper-50'
                : 'border-transparent text-ink-500 hover:text-ink'
            }`}
          >
            Commercial Purchase Receipt (0% Added Tax)
          </button>
          <button
            type="button"
            onClick={() => setPaymentMode('upi')}
            className={`flex-1 py-2.5 text-center font-bold border-b-2 transition-colors ${
              paymentMode === 'upi'
                ? 'border-line text-ink-700 bg-paper-50'
                : 'border-transparent text-ink-500 hover:text-ink'
            }`}
          >
            Instant UPI Payment (Flat ₹{totalAmount.toLocaleString('en-IN')})
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {paymentMode === 'invoice' ? (
            invoice ? (
              <div className="border border-line rounded-lg p-5 space-y-4 bg-paper-50 text-ink printable-invoice">
                <div className="flex justify-between items-start border-b border-line pb-3">
                  <div>
                    <h3 className="font-sans font-bold text-base text-ink">COMMERCIAL EXPENSE RECEIPT</h3>
                    <p className="text-[11px] text-ink-500">Business Expense Voucher · Original for Recipient</p>
                    <p className="font-mono text-xs font-semibold mt-1">{invoice.invoice_number}</p>
                    <p className="text-[11px] text-ink-500">Date: {invoice.invoice_date}</p>
                  </div>
                  <div className="text-right text-[11px] text-ink-700">
                    <p className="font-bold text-ink">{invoice.seller_details?.legal_name || 'Dristik AI'}</p>
                    <p className="text-good font-medium">Status: Standard Commercial Receipt</p>
                    <p>{invoice.seller_details?.address || 'Bangalore, India'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-[11px] sheet p-3 rounded border border-line">
                  <div>
                    <span className="label text-[10px] block">Billed To:</span>
                    <p className="font-semibold text-ink">{invoice.buyer_details?.company_name}</p>
                    <p>Attn: {invoice.buyer_details?.customer_name}</p>
                    <p>Reference: {invoice.buyer_details?.tax_id || invoice.buyer_details?.gstin}</p>
                    <p>Region: {invoice.buyer_details?.state_code}</p>
                  </div>
                  <div>
                    <span className="label text-[10px] block">Deliverable:</span>
                    <p className="font-semibold text-ink">{invoice.plan_name}</p>
                    <p>Domain: {domain}</p>
                    <p>Tax Treatment: Standard Commercial Receipt</p>
                  </div>
                </div>

                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-line text-ink-500 label text-[10px]">
                      <th className="py-1.5">Description</th>
                      <th className="py-1.5 text-right">Taxable Amount</th>
                      <th className="py-1.5 text-right">Tax Rate</th>
                      <th className="py-1.5 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    <tr>
                      <td className="py-2 font-medium">{invoice.plan_name}</td>
                      <td className="py-2 text-right">₹{invoice.base_amount_inr?.toLocaleString('en-IN')}</td>
                      <td className="py-2 text-right">0% (Nil)</td>
                      <td className="py-2 text-right font-bold text-ink">₹{invoice.total_amount_inr?.toLocaleString('en-IN')}</td>
                    </tr>
                  </tbody>
                </table>

                <div className="border-t border-line pt-3 flex justify-between items-center text-xs">
                  <span className="italic text-ink-500">{invoice.total_in_words}</span>
                  <span className="text-base font-sans font-bold text-ink">
                    Total: ₹{invoice.total_amount_inr?.toLocaleString('en-IN')}
                  </span>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="btn-primary font-semibold text-xs px-4 py-1.5 rounded"
                  >
                    Print / Save PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => setInvoice(null)}
                    className="border border-line sheet text-ink text-xs px-3 py-1.5 rounded hover:border-ink-400"
                  >
                    Edit Details
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-ink-700">
                  Enter your company details to generate an official commercial purchase receipt with order tracking for your company expense records:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="label text-[10px] block mb-1">Company / Entity Name</label>
                    <input
                      type="text"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="w-full text-xs p-2 border border-line rounded bg-paper-50 text-ink"
                    />
                  </div>
                  <div>
                    <label className="label text-[10px] block mb-1">Billing Reference / PO (Optional)</label>
                    <input
                      type="text"
                      value={poRef}
                      onChange={(e) => setPoRef(e.target.value)}
                      placeholder="e.g. PO-2026 or Org ID"
                      className="w-full text-xs font-mono p-2 border border-line rounded bg-paper-50 text-ink"
                    />
                  </div>
                  <div>
                    <label className="label text-[10px] block mb-1">Contact Name</label>
                    <input
                      type="text"
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      className="w-full text-xs p-2 border border-line rounded bg-paper-50 text-ink"
                    />
                  </div>
                  <div>
                    <label className="label text-[10px] block mb-1">Billing Email</label>
                    <input
                      type="email"
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                      className="w-full text-xs p-2 border border-line rounded bg-paper-50 text-ink"
                    />
                  </div>
                </div>

                <div className="bg-paper-50 p-3 rounded border border-line text-ink-700 flex justify-between items-center text-xs">
                  <span>
                    Flat Plan Price: ₹{amountInr.toLocaleString('en-IN')} (0% Added Tax)
                  </span>
                  <span className="font-bold text-sm text-ink font-sans">
                    Total: ₹{totalAmount.toLocaleString('en-IN')}
                  </span>
                </div>

                <button
                  type="button"
                  disabled={isGenerating}
                  onClick={handleGenerateInvoice}
                  className="w-full btn-primary font-semibold py-2 rounded text-xs transition-colors shadow-xs"
                >
                  {isGenerating ? 'Generating Commercial Receipt...' : 'Generate Commercial Purchase Receipt'}
                </button>
              </div>
            )
          ) : (
            <div className="text-center space-y-4 py-4">
              <div className="p-4 bg-paper-50 rounded-lg inline-block border border-line">
                <div className="w-40 h-40 bg-paper-50 border-2 border-line mx-auto flex items-center justify-center p-2 rounded shadow-2xs">
                  {/* Simulated UPI QR Graphic */}
                  <div className="text-center space-y-1">
                    <span className="text-2xl">📱</span>
                    <p className="text-[10px] font-mono text-ink-500 break-all">Scan with GPay / PhonePe / Paytm</p>
                    <p className="font-bold text-xs text-ink">dristik@icici</p>
                  </div>
                </div>
              </div>

              <div className="space-y-1 max-w-sm mx-auto">
                <p className="font-sans font-bold text-base text-ink">Amount: ₹{totalAmount.toLocaleString('en-IN')}</p>
                <p className="text-xs text-ink-500">Flat price · 0% added tax · Instant confirmation</p>
              </div>

              <div className="flex justify-center gap-3">
                <a
                  href={upiIntent}
                  className="btn-primary font-semibold text-xs px-5 py-2 rounded shadow transition-colors"
                >
                  Open UPI App (Mobile)
                </a>
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText('dristik@icici')}
                  className="border border-line sheet text-ink font-medium text-xs px-4 py-2 rounded hover:border-ink-400 transition-colors"
                >
                  Copy UPI ID (dristik@icici)
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
