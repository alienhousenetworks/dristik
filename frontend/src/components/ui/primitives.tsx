import React from 'react';
import { cn } from '../../lib/cn';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
};

const buttonVariants = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  ghost: 'btn-ghost',
  danger: 'bg-bad text-white hover:opacity-90 rounded-md font-semibold',
};

const buttonSizes = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-3.5 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  children,
  disabled,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && (
        <span
          className="h-3.5 w-3.5 rounded-full border-2 border-current border-r-transparent animate-spin"
          aria-hidden
        />
      )}
      {children}
    </button>
  );
}

type FieldProps = {
  label: string;
  hint?: string;
  error?: string | null;
  id?: string;
};

export function Input({
  label,
  hint,
  error,
  id,
  className,
  ...props
}: FieldProps & React.InputHTMLAttributes<HTMLInputElement>) {
  const fieldId = id || props.name || label.toLowerCase().replace(/\s+/g, '-');
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;
  return (
    <label className="block" htmlFor={fieldId}>
      <span className="label block mb-1.5">{label}</span>
      <input
        id={fieldId}
        className={cn('field', error && 'border-bad', className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hintId, errorId].filter(Boolean).join(' ') || undefined}
        {...props}
      />
      {hint && (
        <span id={hintId} className="mt-1.5 block text-xs text-ink-400">
          {hint}
        </span>
      )}
      {error && (
        <span id={errorId} className="mt-1.5 block text-sm text-bad" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}

export function Select({
  label,
  hint,
  error,
  id,
  children,
  className,
  ...props
}: FieldProps & React.SelectHTMLAttributes<HTMLSelectElement>) {
  const fieldId = id || props.name || label.toLowerCase().replace(/\s+/g, '-');
  return (
    <label className="block" htmlFor={fieldId}>
      <span className="label block mb-1.5">{label}</span>
      <select id={fieldId} className={cn('field', className)} aria-invalid={error ? true : undefined} {...props}>
        {children}
      </select>
      {hint && <span className="mt-1.5 block text-xs text-ink-400">{hint}</span>}
      {error && (
        <span className="mt-1.5 block text-sm text-bad" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}

export function Textarea({
  label,
  hint,
  error,
  id,
  className,
  ...props
}: FieldProps & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const fieldId = id || props.name || label.toLowerCase().replace(/\s+/g, '-');
  return (
    <label className="block" htmlFor={fieldId}>
      <span className="label block mb-1.5">{label}</span>
      <textarea id={fieldId} className={cn('field min-h-[96px]', className)} aria-invalid={error ? true : undefined} {...props} />
      {hint && <span className="mt-1.5 block text-xs text-ink-400">{hint}</span>}
      {error && (
        <span className="mt-1.5 block text-sm text-bad" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}

const badgeTones = {
  neutral: 'bg-paper-200 text-ink-700 border-line',
  pine: 'bg-paper-200 text-ink-700 border-line',
  good: 'bg-good/10 text-good border-good/25',
  warn: 'bg-warn/10 text-warn border-warn/30',
  bad: 'bg-bad/10 text-bad border-bad/30',
};

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: React.ReactNode;
  tone?: keyof typeof badgeTones;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium',
        badgeTones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Avatar({ name, src, size = 'md' }: { name: string; src?: string; size?: 'sm' | 'md' }) {
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
  const dim = size === 'sm' ? 'h-7 w-7 text-[11px]' : 'h-8 w-8 text-xs';
  if (src) {
    return <img src={src} alt="" className={cn(dim, 'rounded-full object-cover')} />;
  }
  return (
    <span
      className={cn(dim, 'inline-flex items-center justify-center rounded-full bg-paper-200 text-ink-700 font-semibold')}
      aria-hidden
    >
      {initials || 'D'}
    </span>
  );
}

export function ScorePill({ score }: { score?: number | null }) {
  if (score == null || Number.isNaN(score)) {
    return <span className="score-pill text-ink-400">—</span>;
  }
  const n = Math.round(score);
  const tone = n >= 80 ? 'text-good bg-good/10' : n >= 60 ? 'text-warn bg-warn/10' : 'text-bad bg-bad/10';
  return <span className={cn('score-pill', tone)}>{n}</span>;
}

export function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: 'default' | 'good' | 'warn' | 'bad';
}) {
  const valueClass =
    tone === 'good' ? 'text-good' : tone === 'warn' ? 'text-warn' : tone === 'bad' ? 'text-bad' : 'text-ink';
  return (
    <div className="card p-4">
      <p className="label mb-1.5">{label}</p>
      <p className={cn('font-mono text-2xl font-semibold leading-none', valueClass)}>{value}</p>
      {hint && <p className="mt-2 text-xs text-ink-500 leading-relaxed">{hint}</p>}
    </div>
  );
}
