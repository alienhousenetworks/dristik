import React, { FormEvent, useState } from 'react';
import { AppView } from '../types';
import { forgotPassword, login, resetPassword, signup } from '../services/auth';

const fieldClass = 'field';

function Field({
  label,
  type = 'text',
  value,
  onChange,
  autoComplete,
  required = true,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="label block mb-2">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className={fieldClass}
      />
    </label>
  );
}

function AuthShell({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="max-w-md mx-auto space-y-8 pt-4">
      <div className="space-y-2">
        <p className="label">{kicker}</p>
        <h1 className="font-serif text-4xl leading-[1.12] text-ink tracking-tight">{title}</h1>
      </div>
      <div className="card p-6 sm:p-7 space-y-6">{children}</div>
    </div>
  );
}

export function LoginScreen({
  onAuthed,
  onView,
}: {
  onAuthed: () => void;
  onView: (view: AppView) => void;
}) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      onAuthed();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell kicker="Account" title="Sign in to Dristik.">
      <form className="space-y-6" onSubmit={submit}>
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
        {error && <p className="text-sm text-bad">{error}</p>}
        <button type="submit" disabled={busy} className="btn-primary px-5 py-2.5 text-sm tracking-wide disabled:opacity-50">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p className="text-sm text-ink-500 space-x-3">
        <button type="button" onClick={() => onView('signup')} className="text-ink hover:underline">
          Create an organization
        </button>
        <button type="button" onClick={() => onView('forgot')} className="hover:underline">
          Forgot password
        </button>
      </p>
    </AuthShell>
  );
}

export function SignupScreen({
  onAuthed,
  onView,
}: {
  onAuthed: () => void;
  onView: (view: AppView) => void;
}) {
  const [fullName, setFullName] = useState('');
  const [organization, setOrganization] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signup({
        full_name: fullName,
        organization_name: organization,
        email,
        password,
      });
      onAuthed();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell kicker="Organizations" title="Create your Dristik workspace.">
      <p className="text-ink-500 leading-relaxed">
        You become the organization owner. Admins and staff can be added after you sign in.
      </p>
      <form className="space-y-6" onSubmit={submit}>
        <Field label="Your name" value={fullName} onChange={setFullName} autoComplete="name" />
        <Field label="Organization" value={organization} onChange={setOrganization} autoComplete="organization" />
        <Field label="Work email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="new-password" />
        <p className="text-xs text-ink-400">At least 8 characters, with upper and lower case and a number.</p>
        {error && <p className="text-sm text-bad">{error}</p>}
        <button type="submit" disabled={busy} className="btn-primary px-5 py-2.5 text-sm tracking-wide disabled:opacity-50">
          {busy ? 'Creating…' : 'Create account'}
        </button>
      </form>
      <p className="text-sm text-ink-500">
        Already have an account?{' '}
        <button type="button" onClick={() => onView('login')} className="text-ink hover:underline">
          Sign in
        </button>
      </p>
    </AuthShell>
  );
}

export function ForgotScreen({ onView }: { onView: (view: AppView) => void }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [resetPath, setResetPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await forgotPassword(email);
      setMessage(res.message);
      setResetPath(res.reset_path || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start a reset.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell kicker="Password" title="Reset your password.">
      <form className="space-y-6" onSubmit={submit}>
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        {error && <p className="text-sm text-bad">{error}</p>}
        {message && <p className="text-sm text-ink-700">{message}</p>}
        {resetPath && (
          <p className="text-sm text-ink-500">
            Development reset link:{' '}
            <button type="button" className="text-ink underline" onClick={() => { window.location.hash = resetPath.replace(/^#/, ''); }}>
              open reset form
            </button>
          </p>
        )}
        <button type="submit" disabled={busy} className="btn-primary px-5 py-2.5 text-sm tracking-wide disabled:opacity-50">
          {busy ? 'Sending…' : 'Send reset link'}
        </button>
      </form>
      <button type="button" onClick={() => onView('login')} className="text-sm text-ink-500 hover:text-ink">
        Back to sign in
      </button>
    </AuthShell>
  );
}

export function ResetScreen({
  token,
  onView,
}: {
  token?: string;
  onView: (view: AppView) => void;
}) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError('This reset link is missing a token.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell kicker="Password" title="Choose a new password.">
      {done ? (
        <div className="space-y-4">
          <p className="text-ink-700">Password updated. Sign in with the new password.</p>
          <button type="button" onClick={() => onView('login')} className="btn-primary px-5 py-2.5 text-sm">
            Sign in
          </button>
        </div>
      ) : (
        <form className="space-y-6" onSubmit={submit}>
          <Field label="New password" type="password" value={password} onChange={setPassword} autoComplete="new-password" />
          {error && <p className="text-sm text-bad">{error}</p>}
          <button type="submit" disabled={busy} className="btn-primary px-5 py-2.5 text-sm tracking-wide disabled:opacity-50">
            {busy ? 'Saving…' : 'Update password'}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
