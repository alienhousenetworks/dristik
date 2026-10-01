import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { cn } from '../../lib/cn';
import { Button } from './primitives';

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-paper-200', className)} aria-hidden />;
}

export function LoadingBlock({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite" aria-label={label}>
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-4 w-full max-w-xl" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card border-dashed px-6 py-10 text-center">
      <h2 className="font-serif text-2xl text-ink">{title}</h2>
      {description && <p className="mt-2 text-sm text-ink-500 max-w-md mx-auto leading-relaxed">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="card border-bad/30 px-6 py-8" role="alert">
      <h2 className="font-serif text-2xl text-ink">{title}</h2>
      {description && <p className="mt-2 text-sm text-ink-500 leading-relaxed">{description}</p>}
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

type ToastTone = 'info' | 'success' | 'warning' | 'danger';

export interface ToastInput {
  title: string;
  description?: string;
  tone?: ToastTone;
}

interface ToastItem extends ToastInput {
  id: string;
  tone: ToastTone;
}

const ToastContext = createContext<{ push: (toast: ToastInput) => void } | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  return ctx ?? { push: () => undefined };
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((toast: ToastInput) => {
    const item: ToastItem = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      tone: toast.tone || 'info',
      title: toast.title,
      description: toast.description,
    };
    setItems((current) => [...current.slice(-4), item]);
    window.setTimeout(() => {
      setItems((current) => current.filter((row) => row.id !== item.id));
    }, 4800);
  }, []);

  useEffect(() => {
    const onNotify = (event: Event) => {
      const detail = (event as CustomEvent<ToastInput>).detail;
      if (detail?.title) push(detail);
    };
    window.addEventListener('dristik:notify', onNotify);
    return () => window.removeEventListener('dristik:notify', onNotify);
  }, [push]);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-toast flex w-[min(100%-2rem,360px)] flex-col gap-2" aria-live="polite">
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              'card shadow-lg px-4 py-3 animate-slideIn border-l-4',
              item.tone === 'success' && 'border-l-good',
              item.tone === 'warning' && 'border-l-warn',
              item.tone === 'danger' && 'border-l-bad',
              item.tone === 'info' && 'border-l-pine',
            )}
            role={item.tone === 'danger' ? 'alert' : 'status'}
          >
            <p className="text-sm font-semibold text-ink">{item.title}</p>
            {item.description && <p className="mt-0.5 text-xs text-ink-500">{item.description}</p>}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function notify(toast: ToastInput) {
  window.dispatchEvent(new CustomEvent('dristik:notify', { detail: toast }));
}
