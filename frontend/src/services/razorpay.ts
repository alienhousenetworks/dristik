import { PaymentOrder, PaymentVoucher } from '../types';
import { api } from './http';

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (event: string, handler: (response: { error?: { description?: string } }) => void) => void;
    };
  }
}

export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export async function createPaymentOrder(params: {
  plan_id: string;
  target_url: string;
  customer_name?: string;
  customer_email?: string;
  company_name?: string;
  gstin?: string;
}): Promise<PaymentOrder> {
  return api<PaymentOrder>(
    '/api/v1/payments/create-order',
    { method: 'POST', body: JSON.stringify(params) },
    'Could not create the order',
  );
}

export async function verifyPaymentSignature(params: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  plan_id: string;
  target_url: string;
  customer_email?: string;
}): Promise<PaymentVoucher> {
  return api<PaymentVoucher>(
    '/api/v1/payments/verify-payment',
    { method: 'POST', body: JSON.stringify(params) },
    'Payment verification failed',
  );
}

export async function launchRazorpayCheckout(options: {
  order: PaymentOrder;
  customerName?: string;
  customerEmail?: string;
  customerPhone?: string;
  onSuccess: (voucher: PaymentVoucher) => void;
  onFailure: (error: string) => void;
  onDismiss?: () => void;
}) {
  const { order, customerName, customerEmail, customerPhone, onSuccess, onFailure, onDismiss } = options;
  const scriptLoaded = await loadRazorpayScript();

  if (!order.key_id) {
    onFailure('Payments are currently unavailable. Gateway credentials are not configured on the server.');
    return;
  }

  if (!scriptLoaded || !window.Razorpay) {
    onFailure('Payment checkout library could not be loaded. Please check your network connection and try again.');
    return;
  }

  try {
    const rzp = new window.Razorpay({
      key: order.key_id,
      amount: order.amount_paise,
      currency: order.currency,
      name: 'Dristik',
      description: order.plan_name,
      order_id: order.order_id,
      handler: async (response: {
        razorpay_payment_id: string;
        razorpay_order_id: string;
        razorpay_signature: string;
      }) => {
        try {
          const voucher = await verifyPaymentSignature({
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
            plan_id: order.plan_id,
            target_url: order.target_url,
            customer_email: customerEmail,
          });
          onSuccess(voucher);
        } catch (err: unknown) {
          onFailure(err instanceof Error ? err.message : 'Payment signature verification failed.');
        }
      },
      prefill: {
        name: customerName || '',
        email: customerEmail || '',
        contact: customerPhone || '',
      },
      notes: {
        plan_id: order.plan_id,
        target_url: order.target_url,
      },
      theme: {
        color: '#105c4c',
        backdrop_color: 'rgba(28, 25, 21, 0.45)',
      },
      modal: {
        ondismiss: () => onDismiss?.(),
      },
    });

    rzp.on('payment.failed', (response) => {
      onFailure(response.error?.description || 'Payment failed.');
    });
    rzp.open();
  } catch (err: unknown) {
    onFailure(err instanceof Error ? err.message : 'Unable to initialize Razorpay checkout.');
  }
}

