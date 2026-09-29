import React, { useEffect, useState } from 'react';
import {
  connectExternalApiKey,
  disconnectExternal,
  fetchExternalHealth,
  saveExternalBrand,
  saveExternalCompetitors,
  saveExternalLocal,
  startExternalOAuth,
  syncExternal,
} from '../services/externalAuthority';

interface ConnectorRow {
  provider_id: string;
  provider: string;
  connection_status: string;
  status: string;
  account?: string | null;
  property?: string | null;
  last_successful_sync?: string | null;
  last_attempted_sync?: string | null;
  next_sync?: string | null;
  token_status?: string | null;
  quota_status?: string | null;
  error_message?: string | null;
  capabilities?: string[];
  auth_mode?: string;
}

export function ExternalAuthorityPanel({
  isOpen,
  onClose,
  domain,
}: {
  isOpen: boolean;
  onClose: () => void;
  domain: string;
}) {
  const [rows, setRows] = useState<ConnectorRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [providerForKey, setProviderForKey] = useState('ahrefs');
  const [brand, setBrand] = useState('');
  const [aliases, setAliases] = useState('');
  const [competitors, setCompetitors] = useState('');
  const [applicability, setApplicability] = useState('UNKNOWN');
  const [businessName, setBusinessName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [directories, setDirectories] = useState('');

  async function load() {
    const payload = await fetchExternalHealth();
    setRows((payload.connectors || []) as ConnectorRow[]);
  }

  useEffect(() => {
    if (!isOpen) return;
    load().catch((err: unknown) => setError(err instanceof Error ? err.message : 'Could not load connectors.'));
  }, [isOpen]);

  if (!isOpen) return null;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="scrim fixed inset-0 z-50 overflow-y-auto p-4">
      <div className="card max-w-3xl mx-auto p-5 sm:p-6 space-y-5 bg-paper">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="label">Integrations</p>
            <h2 className="section-title">External Authority</h2>
            <p className="text-sm text-ink-500 mt-1">OAuth uses a Connect button. API keys stay on the server. Missing providers stay unmeasured.</p>
          </div>
          <button type="button" className="btn-secondary px-3 py-1.5" onClick={onClose}>Close</button>
        </div>

        {error && <p className="text-sm text-bad">{error}</p>}

        <div className="space-y-3">
          {rows.map((row) => (
            <article key={row.provider_id} className="border border-line rounded-lg p-3 text-sm space-y-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold">{row.provider}</h3>
                <span className="font-mono text-xs">{row.connection_status} · {row.status}</span>
              </div>
              <p>Account: {row.account || '—'} · Property: {row.property || '—'}</p>
              <p>Last sync: {row.last_successful_sync || '—'} · Last attempt: {row.last_attempted_sync || '—'} · Next: {row.next_sync || '—'}</p>
              <p>Token: {row.token_status || '—'} · Quota: {row.quota_status || '—'}</p>
              <p>Capabilities: {(row.capabilities || []).join(', ') || '—'}</p>
              {row.error_message && <p className="text-bad">{row.error_message}</p>}
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  className="btn-primary px-3 py-1.5"
                  disabled={busy}
                  onClick={() => run(async () => {
                    const started = await startExternalOAuth(row.provider_id, domain);
                    window.location.assign(started.authorize_url);
                  })}
                >
                  Connect
                </button>
                <button
                  type="button"
                  className="btn-secondary px-3 py-1.5"
                  disabled={busy}
                  onClick={() => run(() => disconnectExternal(row.provider_id))}
                >
                  Disconnect
                </button>
              </div>
            </article>
          ))}
        </div>

        <form
          className="space-y-2 border border-line rounded-lg p-3"
          onSubmit={(event) => {
            event.preventDefault();
            run(() => connectExternalApiKey(providerForKey, domain, { api_key: apiKey }));
          }}
        >
          <h3 className="font-semibold text-sm">API key providers</h3>
          <p className="text-xs text-ink-500">Use this only when the provider does not offer OAuth. The key is encrypted and is not shown again.</p>
          <div className="flex flex-col sm:flex-row gap-2">
            <select className="field" value={providerForKey} onChange={(event) => setProviderForKey(event.target.value)}>
              {['ahrefs', 'semrush', 'majestic', 'dataforseo', 'serpapi', 'citations', 'brand_mentions'].map((id) => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
            <input className="field flex-1" type="password" autoComplete="off" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="API key" />
            <button className="btn-primary px-3 py-1.5" type="submit" disabled={busy || !apiKey}>Store key</button>
          </div>
        </form>

        <form
          className="grid sm:grid-cols-2 gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            run(async () => {
              await saveExternalBrand(brand, aliases.split(',').map((item) => item.trim()).filter(Boolean));
              await saveExternalCompetitors(
                competitors.split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
                  const [name, domainValue] = line.includes(',') ? line.split(',', 2) : [line, line];
                  return { name: name.trim(), domain: (domainValue || name).trim() };
                }),
              );
              await saveExternalLocal({
                applicability,
                name: businessName,
                phone,
                address,
                website: domain,
                expected_directories: directories.split(',').map((item) => item.trim()).filter(Boolean),
              });
            });
          }}
        >
          <label className="text-sm">Brand name<input className="field mt-1" value={brand} onChange={(event) => setBrand(event.target.value)} /></label>
          <label className="text-sm">Aliases<input className="field mt-1" value={aliases} onChange={(event) => setAliases(event.target.value)} placeholder="comma separated" /></label>
          <label className="text-sm sm:col-span-2">Competitors<textarea className="field mt-1" rows={3} value={competitors} onChange={(event) => setCompetitors(event.target.value)} placeholder="Name, competitor.com" /></label>
          <label className="text-sm">Local applicability
            <select className="field mt-1" value={applicability} onChange={(event) => setApplicability(event.target.value)}>
              <option value="UNKNOWN">Unknown</option>
              <option value="LOCAL_BUSINESS">Local business</option>
              <option value="NON_LOCAL_BUSINESS">Not a local business</option>
            </select>
          </label>
          <label className="text-sm">Business name<input className="field mt-1" value={businessName} onChange={(event) => setBusinessName(event.target.value)} /></label>
          <label className="text-sm">Phone<input className="field mt-1" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label className="text-sm">Address<input className="field mt-1" value={address} onChange={(event) => setAddress(event.target.value)} /></label>
          <label className="text-sm sm:col-span-2">Expected directories<input className="field mt-1" value={directories} onChange={(event) => setDirectories(event.target.value)} placeholder="comma separated hosts" /></label>
          <div className="sm:col-span-2 flex flex-wrap gap-2">
            <button className="btn-secondary px-3 py-1.5" type="submit" disabled={busy}>Save profile</button>
            <button className="btn-primary px-3 py-1.5" type="button" disabled={busy || !domain} onClick={() => run(() => syncExternal(domain))}>Sync connected providers</button>
          </div>
        </form>
      </div>
    </div>
  );
}
